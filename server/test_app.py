import base64
import errno
import io
import json
import os
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from server.app import create_app
from server.auth import hash_password

@pytest.fixture
def env(tmp_path):
    root = tmp_path / 'pictures'
    root.mkdir()
    (root / 'project').mkdir()
    config = {'name': 'Test Linux', 'origins': ['http://localhost:5173'], 'roots': [{'id': 'pictures', 'name': 'Pictures', 'path': str(root)}], 'state_dir': str(tmp_path / 'state'), 'auth': {'mode': 'none'}, 'max_upload_mb': 1}
    return config, root

def picture(fmt='PNG'):
    buffer = io.BytesIO()
    image = Image.new('RGB', (120, 80), '#f56532')
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = 'Private metadata'
    image.save(buffer, format=fmt, exif=exif.tobytes())
    return buffer.getvalue()

def send(client, content=None, **changes):
    data = {'root': 'pictures', 'path': 'project', 'name': 'the-plan', 'request_id': str(uuid.uuid4())}
    data.update(changes)
    return client.post('/api/v1/uploads', data=data, files={'image': ('photo', picture() if content is None else content, 'application/octet-stream')})

@pytest.mark.parametrize('mode', ['none', 'bearer', 'basic'])
def test_auth_and_cors(env, mode):
    config, root = env
    config['auth'] = {'mode': mode, 'token': 'a' * 40, 'username': 'bryan', 'password_hash': hash_password('secret')}
    client = TestClient(create_app(config))
    assert client.get('/api/v1/info').json()['auth'] == mode
    assert client.get('/api/v1/directories').status_code == (200 if mode == 'none' else 401)
    assert send(client).status_code == (200 if mode == 'none' else 401)
    if mode != 'none':
        client.headers['Authorization'] = 'Bearer wrong'
        assert client.get('/api/v1/directories').status_code == 401
    client.headers['Authorization'] = 'Bearer ' + 'a' * 40 if mode == 'bearer' else 'Basic ' + base64.b64encode(b'bryan:secret').decode()
    assert client.get('/api/v1/directories').status_code == 200
    assert send(client, name='auth-test').status_code == 200
    preflight = client.options('/api/v1/uploads', headers={'Origin': config['origins'][0], 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization,content-type'})
    assert preflight.status_code == 200
    assert preflight.headers['access-control-allow-origin'] == config['origins'][0]
    client.headers['Origin'] = 'https://hostile.example'
    assert send(client, name='hostile').status_code == 403
    assert not (root / 'project/hostile.jpg').exists()

@pytest.mark.parametrize('fmt', ['JPEG', 'PNG', 'HEIF'])
def test_conversion_orientation_and_metadata(env, fmt):
    config, root = env
    response = send(TestClient(create_app(config)), picture(fmt), name='café plan.jpg')
    assert response.status_code == 200, response.text
    output = root / 'project/café plan.jpg'
    with Image.open(output) as image:
        assert image.format == 'JPEG'
        assert image.mode == 'RGB'
        assert image.size == (80, 120)
        assert len(image.getexif()) == 0
    assert response.json()['width'] == 80
    assert output.stat().st_mode & 0o777 == 0o644
    assert not list(root.glob('project/.plunk-*'))

@pytest.mark.parametrize('path', ['..', '../outside', '/tmp', 'project/../../outside', 'project//bad', 'project\\bad'])
def test_path_boundaries(env, path):
    config, root = env
    client = TestClient(create_app(config))
    assert send(client, path=path).status_code == 403
    assert client.get('/api/v1/directories', params={'root':'pictures', 'path':path}).status_code == 403

def test_symlink_and_browsing(env, tmp_path):
    config, root = env
    outside = tmp_path / 'outside'
    outside.mkdir()
    (root / 'escape').symlink_to(outside, target_is_directory=True)
    client = TestClient(create_app(config))
    listing = client.get('/api/v1/directories', params={'root': 'pictures'}).json()
    assert listing['directories'] == ['project']
    assert send(client, path='escape').status_code == 403
    assert send(client, root='unknown').status_code == 404
    assert send(client, path='missing').status_code == 403
    assert not list(outside.iterdir())

@pytest.mark.parametrize('name', ['', '..', '.', 'a/b', 'a\\b', 'a\x00b', 'a\nb', '界'*100, '.jpg'])
def test_invalid_names(env, name):
    config, _ = env
    assert send(TestClient(create_app(config)), name=name).status_code == 422

def test_duplicate_and_persistent_retry(env):
    config, root = env
    client = TestClient(create_app(config))
    rid = str(uuid.uuid4())
    first = send(client, request_id=rid)
    assert first.status_code == 200
    original = (root / 'project/the-plan.jpg').read_bytes()
    assert send(client).status_code == 409
    retry = send(TestClient(create_app(config)), request_id=rid)
    assert retry.json() == first.json()
    assert send(client, request_id=rid, name='different').status_code == 409
    assert (root / 'project/the-plan.jpg').read_bytes() == original
    assert len(list((root / 'project').iterdir())) == 1

def test_corrupt_and_limit(env):
    config, root = env
    client = TestClient(create_app(config))
    assert send(client, b'not an image').status_code == 422
    assert send(client, b'x' * (1024*1024 + 1)).status_code == 413
    assert not list((root / 'project').iterdir())

def test_recover_crash_after_publication(env):
    config, root = env
    client = TestClient(create_app(config))
    rid = str(uuid.uuid4())
    receipt = send(client, request_id=rid).json()
    # Simulate durable pending journal + atomic link, but no done commit.
    os.link(root / 'project/the-plan.jpg', root / 'project/.plunk-recovery')
    with sqlite3.connect(config['state_dir'] + '/receipts.sqlite3') as db:
        db.execute("UPDATE receipts SET status='pending', temp='.plunk-recovery' WHERE id=?", (rid,))
    assert send(TestClient(create_app(config)), request_id=rid).json() == receipt
    assert not (root / 'project/.plunk-recovery').exists()

def test_concurrent_retry(env):
    config, root = env
    client = TestClient(create_app(config))
    rid = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: send(client, request_id=rid), range(4)))
    assert all(r.status_code == 200 for r in results)
    assert all(r.json() == results[0].json() for r in results)
    assert len(list((root / 'project').iterdir())) == 1

def test_disk_full_preserves_no_partial_image(env, monkeypatch):
    config, root = env
    client = TestClient(create_app(config))
    def no_space(*args, **kwargs):
        raise OSError(errno.ENOSPC, 'disk full')
    monkeypatch.setattr(os, 'fsync', no_space)
    assert send(client).status_code == 507
    assert not list((root / 'project').iterdir())

def test_chunked_limit_and_incomplete_multipart(env):
    config, root = env
    client = TestClient(create_app(config))
    header = b'--test\r\nContent-Disposition: form-data; name="image"; filename="photo.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
    response = client.post('/api/v1/uploads', content=iter([header, b'x'*(2*1024*1024)]), headers={'Content-Type':'multipart/form-data; boundary=test'})
    assert response.status_code == 413
    response = client.post('/api/v1/uploads', content=header + picture()[:20], headers={'Content-Type':'multipart/form-data; boundary=test'})
    assert response.status_code == 422
    assert not list((root / 'project').iterdir())

def test_unwritable_directory(env, monkeypatch):
    config, _ = env
    client = TestClient(create_app(config))
    real_open = os.open
    def denied(path, flags, *args, **kwargs):
        if flags & os.O_CREAT:
            raise PermissionError(errno.EACCES, 'read-only folder')
        return real_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', denied)
    assert send(client).status_code == 403
