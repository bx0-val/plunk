"""Linux-only listener. Descriptor-relative operations prevent symlink traversal races."""
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import threading
import time
import unicodedata
import uuid
import warnings

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from server.auth import verify_password

register_heif_opener()
Image.MAX_IMAGE_PIXELS = 50_000_000

class BodyLimit:
    """Count streamed bytes too, before multipart spooling can fill the disk."""
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        total = 0
        async def limited_receive():
            nonlocal total
            message = await receive()
            if message['type'] == 'http.request':
                total += len(message.get('body', b''))
                if total > self.limit:
                    fail(413, 'This picture is larger than the server upload limit.')
            return message
        await self.app(scope, limited_receive, send)

def fail(status: int, message: str):
    raise HTTPException(status, message)

def filename(value: str) -> str:
    value = unicodedata.normalize('NFC', value.strip())
    if not value or value in ('.', '..') or any(c in '/\\' or unicodedata.category(c) == 'Cc' for c in value):
        fail(422, 'Give the picture a name without slashes or control characters.')
    if value.lower().endswith(('.jpg', '.jpeg')):
        value = value.rsplit('.', 1)[0]
    if not value or value in ('.', '..') or len((value + '.jpg').encode()) > 240:
        fail(422, 'Choose a shorter picture name (up to 236 UTF-8 bytes).')
    return value + '.jpg'

def components(path: str):
    if path == '':
        return []
    parts = path.split('/')
    if any(p in ('', '.', '..') or '\\' in p or '\x00' in p for p in parts):
        fail(403, 'That folder is outside the allowed location.')
    return parts

@contextlib.contextmanager
def directory(root: str, relative: str):
    """Never resolve a user path and later reopen it by its absolute name."""
    parts = components(relative)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)

def build_roots(raw):
    roots = {r['id']: dict(r) for r in raw}
    if not roots or len(roots) != len(raw):
        raise ValueError('Configure unique roots.')
    for root in roots.values():
        root['path'] = str(Path(root['path']).resolve(strict=True))
    return roots

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Permissions-Policy': 'camera=(self), microphone=(), geolocation=()',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self' https:; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
}
PAIR_ATTEMPTS = 5

def create_app(config=None, config_path=None):
    if os.name != 'posix':
        raise RuntimeError('Run the Plunk listener on Linux (or WSL).')
    if config is None:
        config_path = Path(os.environ.get('PLUNK_CONFIG', 'config.json'))
        config = json.loads(config_path.read_text())
    live = {'roots': build_roots(config['roots']), 'mtime': config_path.stat().st_mtime if config_path else None}

    def current_roots():
        # `plunk add` edits the config file; pick up destination changes without a restart.
        if config_path:
            try:
                mtime = config_path.stat().st_mtime
                if mtime != live['mtime']:
                    live['roots'] = build_roots(json.loads(config_path.read_text())['roots'])
                    live['mtime'] = mtime
            except (OSError, ValueError, KeyError) as error:
                print(f'kept previous destinations; config reload failed: {error}', flush=True)
        return live['roots']
    auth = config.get('auth', {'mode': 'none'})
    mode = auth['mode']
    if mode not in ('none', 'bearer', 'basic'):
        raise ValueError('Unknown authentication mode')
    if mode == 'bearer' and (len(auth.get('token', '')) < 32 or auth['token'].startswith('REPLACE_')):
        raise ValueError('Set a random bearer token of at least 32 characters.')
    if mode == 'basic' and (not auth.get('username') or not auth.get('password_hash', '').startswith('scrypt$')):
        raise ValueError('Basic authentication needs username and scrypt password_hash.')
    origins = config['origins']
    if not origins or '*' in origins:
        raise ValueError('Configure exact allowed app origins.')
    limit = int(config.get('max_upload_mb', 25)) * 1024 * 1024
    if limit <= 0:
        raise ValueError('Upload limit must be positive.')
    file_mode = config.get('file_mode', '0644')
    if file_mode not in ('0600', '0640', '0644'):
        raise ValueError('file_mode must be 0600, 0640, or 0644.')
    state = Path(config['state_dir'])
    state.mkdir(parents=True, exist_ok=True)
    db_path = state / 'receipts.sqlite3'
    pair_path = state / 'pairing.json'
    pair_lock = threading.Lock()
    static_dir = Path(config['static_dir']).resolve(strict=True) if config.get('static_dir') else None

    def connect():
        db = sqlite3.connect(db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        return db

    with contextlib.closing(connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, binding TEXT NOT NULL, status TEXT NOT NULL, temp TEXT, receipt TEXT NOT NULL)')
        db.commit()
    app = FastAPI(title='Plunk listener', version='0.1.0', docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit, limit=limit + 128 * 1024)

    @app.middleware('http')
    async def guard(request: Request, call_next):
        # CORS alone does not prevent cross-origin writes to a no-auth listener.
        origin = request.headers.get('origin')
        if origin and origin not in origins:
            return JSONResponse({'detail': 'App origin is not allowed.'}, 403)
        api = request.url.path.startswith('/api/')
        if api and request.url.path not in ('/api/v1/info', '/api/v1/pair') and request.method != 'OPTIONS':
            header = request.headers.get('authorization', '')
            valid = mode == 'none'
            if mode == 'bearer':
                scheme, _, given = header.partition(' ')
                valid = scheme.lower() == 'bearer' and secrets.compare_digest(given.strip().encode(), auth['token'].encode())
                if not valid:
                    # Diagnostics only: shape of what arrived, never its value.
                    print(f"auth rejected: scheme={scheme[:10]!r} token_len={len(given.strip())} expected_len={len(auth['token'])} padded={given != given.strip()}", flush=True)
            elif mode == 'basic':
                try:
                    scheme, credentials = header.split(' ', 1)
                    user, password = base64.b64decode(credentials, validate=True).decode('utf-8').split(':', 1)
                    valid = scheme.lower() == 'basic' and secrets.compare_digest(user.encode(), auth['username'].encode()) and verify_password(password, auth['password_hash'])
                except (ValueError, UnicodeError):
                    valid = False
            if not valid:
                return JSONResponse({'detail': 'Check the saved credentials for this server.'}, 401)
        try:
            if int(request.headers.get('content-length', '0')) > limit + 128 * 1024:
                return JSONResponse({'detail': 'This picture is larger than the server upload limit.'}, 413)
        except ValueError:
            return JSONResponse({'detail': 'Invalid content length.'}, 400)
        response = await call_next(request)
        if api:
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
        else:
            response.headers.update(SECURITY_HEADERS)
        return response

    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Authorization', 'Content-Type'], max_age=600)

    @app.exception_handler(OSError)
    async def filesystem_error(request, error):
        if error.errno == 28:
            return JSONResponse({'detail': 'The server is out of space. Your picture is still on the phone.'}, 507)
        return JSONResponse({'detail': 'This folder is unavailable or not writable. Choose another folder.'}, 403)

    def root_path(root):
        roots = current_roots()
        if root not in roots:
            fail(404, 'This saved root is no longer available. Choose another location.')
        return roots[root]['path']

    @app.get('/api/v1/info')
    def info():
        return {'name': config['name'], 'auth': mode, 'max_upload_bytes': limit, 'version': 1}

    @app.get('/api/v1/directories')
    def directories(root: str | None = None, path: str = ''):
        if root is None:
            return {'roots': [{'id': r['id'], 'name': r['name']} for r in current_roots().values()]}
        with directory(root_path(root), path) as fd:
            with os.scandir(fd) as entries:
                children = sorted([e.name for e in entries if e.is_dir(follow_symlinks=False)], key=str.casefold)
        return {'root': root, 'path': path, 'directories': children}

    @app.post('/api/v1/uploads')
    def upload(image: UploadFile = File(), name: str = Form(), root: str = Form(), path: str = Form(''), request_id: str = Form()):
        try:
            uuid.UUID(request_id)
        except ValueError:
            fail(422, 'Invalid upload request identifier.')
        target = filename(name)
        root_dir = root_path(root)
        components(path)
        data = image.file.read(limit + 1)
        if len(data) > limit:
            fail(413, 'This picture is larger than the server upload limit.')
        binding = hashlib.sha256(json.dumps([root_dir, path, target, hashlib.sha256(data).hexdigest()], ensure_ascii=False).encode()).hexdigest()
        with directory(root_dir, path) as fd, contextlib.closing(connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM receipts WHERE id=?', (request_id,)).fetchone()
            if row and row['binding'] != binding:
                fail(409, 'This request identifier belongs to a different upload.')
            if row and row['status'] == 'done':
                return json.loads(row['receipt'])
            if not row:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('error', Image.DecompressionBombWarning)
                        with Image.open(io.BytesIO(data)) as source:
                            source.load()
                            upright = ImageOps.exif_transpose(source)
                            if upright.mode in ('RGBA', 'LA') or 'transparency' in upright.info:
                                rgba = upright.convert('RGBA')
                                rgb = Image.new('RGB', rgba.size, 'white')
                                rgb.paste(rgba, mask=rgba.getchannel('A'))
                            else:
                                rgb = upright.convert('RGB')
                            clean = Image.new('RGB', rgb.size)
                            clean.paste(rgb)
                            output = io.BytesIO()
                            clean.save(output, format='JPEG', quality=95)
                except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
                    fail(422, 'This image could not be read. Choose a JPEG, PNG, or HEIC picture.')
                temp = '.plunk-' + uuid.uuid4().hex
                try:
                    temp_fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                    with os.fdopen(temp_fd, 'wb') as stream:
                        stream.write(output.getvalue())
                        stream.flush()
                        os.fchmod(stream.fileno(), int(file_mode, 8))
                        os.fsync(stream.fileno())
                    os.fsync(fd)
                    receipt = {'server': config['name'], 'root': root, 'folder': '/'.join(filter(None, [current_roots()[root]['name'], path])), 'filename': target, 'bytes': output.tell(), 'width': clean.width, 'height': clean.height, 'request_id': request_id}
                    db.execute('INSERT INTO receipts VALUES (?,?,?,?,?)', (request_id, binding, 'pending', temp, json.dumps(receipt)))
                    db.commit()
                except BaseException:
                    with contextlib.suppress(OSError):
                        os.unlink(temp, dir_fd=fd)
                    raise
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM receipts WHERE id=?', (request_id,)).fetchone()
                if row['status'] == 'done':
                    return json.loads(row['receipt'])
            temp = row['temp']
            try:
                # Hard-link publishes a complete file atomically and never replaces a name.
                os.link(temp, target, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                os.fsync(fd)
            except FileExistsError:
                a = os.stat(temp, dir_fd=fd, follow_symlinks=False)
                b = os.stat(target, dir_fd=fd, follow_symlinks=False)
                if not (stat.S_ISREG(b.st_mode) and (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)):
                    os.unlink(temp, dir_fd=fd)
                    db.execute('DELETE FROM receipts WHERE id=?', (request_id,))
                    db.commit()
                    fail(409, 'That filename already exists. Try a different name.')
            db.execute('UPDATE receipts SET status=? WHERE id=?', ('done', request_id))
            db.commit()
            with contextlib.suppress(OSError):
                os.unlink(temp, dir_fd=fd)
            return json.loads(row['receipt'])

    @app.post('/api/v1/pair')
    async def pair(request: Request):
        """Trade a short-lived code from `plunk pair` for the bearer token. Single use, few attempts."""
        if mode != 'bearer':
            fail(404, 'Pairing is only available for token authentication.')
        try:
            code = str((await request.json()).get('code', '')).replace(' ', '')
        except (ValueError, AttributeError):
            fail(422, 'Send the pairing code.')
        with pair_lock:
            try:
                pending = json.loads(pair_path.read_text())
            except (OSError, ValueError):
                pending = None
            if not pending or pending.get('expires', 0) < time.time():
                with contextlib.suppress(OSError):
                    pair_path.unlink()
                fail(410, 'No active pairing code. Run plunk pair on the server for a new one.')
            if secrets.compare_digest(hashlib.sha256(code.encode()).hexdigest(), pending['code_sha256']):
                pair_path.unlink()
                return {'name': config['name'], 'auth': 'bearer', 'token': auth['token']}
            pending['attempts'] = pending.get('attempts', 0) + 1
            if pending['attempts'] >= PAIR_ATTEMPTS:
                pair_path.unlink()
                fail(429, 'Too many wrong codes. Run plunk pair on the server for a new one.')
            pair_path.write_text(json.dumps(pending))
        fail(401, 'That code is not right. Check the code on the server.')

    if static_dir:
        # Native installs serve the app themselves; Docker installs use Caddy instead.
        @app.get('/{asset:path}', include_in_schema=False)
        def static(asset: str):
            if asset.startswith('api/'):
                fail(404, 'Not found.')
            candidate = (static_dir / asset).resolve()
            if asset and candidate.is_file() and candidate.is_relative_to(static_dir):
                cache = 'public, max-age=31536000, immutable' if asset.startswith('assets/') else 'no-cache'
                return FileResponse(candidate, headers={'Cache-Control': cache})
            return FileResponse(static_dir / 'index.html', headers={'Cache-Control': 'no-cache'})
    return app
