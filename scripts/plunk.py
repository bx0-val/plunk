#!/usr/bin/env python3
"""plunk: install the listener on this Linux server and choose where pictures can go.

  plunk install            one-time setup: deps, app, config, service, Tailscale HTTPS, pairing
  plunk here [--name N]    let the phone save into the current folder
  plunk add PATH [--name]  let the phone save into PATH
  plunk ls                 list destinations
  plunk rm NAME|PATH       stop offering a destination (files stay)
  plunk pair               show a QR code and one-time code to connect a phone
  plunk status | url | logs
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENV_PY = REPO / '.venv' / 'bin' / 'python'
HOME = Path.home()
CONFIG = Path(os.environ.get('PLUNK_CONFIG', HOME / '.config' / 'plunk' / 'config.json'))
STATE = HOME / '.local' / 'state' / 'plunk'
UNIT = HOME / '.config' / 'systemd' / 'user' / 'plunk.service'
BIN = HOME / '.local' / 'bin' / 'plunk'
PAIR_MINUTES = 10
TTY = sys.stdout.isatty()

# Prefer the project venv (it has qrcode); fall back to the system Python before install creates it.
if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve() and not os.environ.get('PLUNK_NO_REEXEC'):
    os.environ['PLUNK_NO_REEXEC'] = '1'
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


def paint(code, text):
    return f'\033[{code}m{text}\033[0m' if TTY else text


def ok(msg):
    print(f"  {paint('32', '✓')} {msg}")


def step(msg):
    print(paint('1', msg))


def die(msg, hint=None):
    print(f"{paint('31', 'plunk:')} {msg}", file=sys.stderr)
    if hint:
        print(f'       {hint}', file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def must(cmd, what, **kw):
    out = run(cmd, **kw)
    if out.returncode:
        tail = (out.stderr or out.stdout).strip().splitlines()[-15:]
        die(f'{what} failed:\n       ' + '\n       '.join(tail))
    return out


# ---------- config ----------

def load():
    if not CONFIG.exists():
        die('Plunk is not installed on this server yet.', 'Run: plunk install')
    return json.loads(CONFIG.read_text())


def save(config):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=CONFIG.parent, prefix='.config-')
    with os.fdopen(fd, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG)


def url(config):
    return config['origins'][0]


def slug(name, taken):
    base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'folder'
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f'{base}-{n}', n + 1
    return candidate


# ---------- tailscale ----------

def tailscale_host():
    if not shutil.which('tailscale'):
        die('Tailscale is not installed.', 'Install it from https://tailscale.com/download and run: sudo tailscale up')
    out = run(['tailscale', 'status', '--json'])
    try:
        status = json.loads(out.stdout)
        host = status['Self']['DNSName'].rstrip('.')
        ip = status['Self']['TailscaleIPs'][0]
    except (ValueError, KeyError, IndexError):
        die('Tailscale is not connected.', 'Run: sudo tailscale up')
    if not host.endswith('.ts.net'):
        die('MagicDNS is off, so there is no .ts.net name for HTTPS.', 'Turn on MagicDNS and HTTPS in the Tailscale admin console.')
    return host, ip


def serve_ports():
    """HTTPS ports already handled by Tailscale Serve, mapped to what they proxy."""
    out = run(['tailscale', 'serve', 'status', '--json'])
    try:
        data = json.loads(out.stdout or '{}')
    except ValueError:
        return {}
    used = {}
    for hostport, web in (data.get('Web') or {}).items():
        port = int(hostport.rsplit(':', 1)[1])
        used[port] = ', '.join(h.get('Proxy', '?') for h in (web.get('Handlers') or {}).values())
    for port in (data.get('TCP') or {}):
        used.setdefault(int(port), 'tcp')
    return used


def bindable(host, port):
    with socket.socket() as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def pick_https_port(ip):
    used = serve_ports()
    for port in [443, 8443, *range(7400, 7500)]:
        if port not in used and bindable(ip, port):
            return port
    die('No free HTTPS port found for Tailscale Serve. Pass one with --https-port.')


def pick_local_port():
    for port in range(8787, 8887):
        if bindable('127.0.0.1', port):
            return port
    die('No free local port between 8787 and 8886. Pass one with --local-port.')


# ---------- commands ----------

def cmd_install(a):
    step('Checking Tailscale')
    host, ip = tailscale_host()
    ok(host)

    step('Python environment')
    if shutil.which('uv'):
        if not VENV_PY.exists():
            must(['uv', 'venv', '--python', '3.12', str(REPO / '.venv')], 'Creating the venv')
        must(['uv', 'pip', 'install', '--python', str(VENV_PY), '-r', str(REPO / 'server/requirements.lock')], 'Installing Python packages')
    else:
        if not VENV_PY.exists():
            must([sys.executable, '-m', 'venv', str(REPO / '.venv')], 'Creating the venv')
        must([str(VENV_PY), '-m', 'pip', 'install', '-q', '-r', str(REPO / 'server/requirements.lock')], 'Installing Python packages')
    ok('packages installed in .venv')

    step('Phone app')
    dist = REPO / 'dist'
    if a.rebuild or not (dist / 'index.html').exists():
        if not shutil.which('corepack'):
            die('Building the app needs Node 22+ with corepack.', 'Install Node 22, then rerun plunk install.')
        env = dict(os.environ, COREPACK_ENABLE_DOWNLOAD_PROMPT='0', CI='1')
        must(['corepack', 'pnpm', 'install', '--frozen-lockfile'], 'Installing app dependencies', cwd=REPO, env=env)
        must(['corepack', 'pnpm', 'build'], 'Building the app', cwd=REPO, env=env)
        ok('built into dist/')
    else:
        ok('already built (use --rebuild after pulling changes)')

    step('Configuration')
    if CONFIG.exists():
        config = json.loads(CONFIG.read_text())
        ok(f'keeping {CONFIG}')
    else:
        imported = json.loads(Path(a.import_config).read_text()) if a.import_config else {}
        port = a.https_port or pick_https_port(ip)
        origin = f'https://{host}' + ('' if port == 443 else f':{port}')
        inbox = Path(a.inbox).expanduser().resolve()
        inbox.mkdir(parents=True, exist_ok=True)
        config = {
            'name': a.name or imported.get('name') or socket.gethostname(),
            'auth': imported.get('auth') if imported.get('auth', {}).get('mode') == 'bearer' else {'mode': 'bearer', 'token': secrets.token_urlsafe(32)},
            'origins': imported.get('origins') or [origin],
            'roots': [{'id': 'inbox', 'name': inbox.name, 'path': str(inbox)}],
            'state_dir': str(STATE),
            'max_upload_mb': 25,
            'file_mode': '0644',
            'install': {'https_port': port, 'local_port': a.local_port or pick_local_port()},
        }
        ok(f'created {CONFIG}' + (f' (token and app address kept from {a.import_config})' if imported else ''))
    config['static_dir'] = str(dist)
    config.setdefault('install', {})
    if a.https_port:
        config['install']['https_port'] = a.https_port
    if a.local_port:
        config['install']['local_port'] = a.local_port
    STATE.mkdir(parents=True, exist_ok=True)
    save(config)
    local, https = config['install']['local_port'], config['install']['https_port']

    step('Background service')
    UNIT.parent.mkdir(parents=True, exist_ok=True)
    UNIT.write_text(f"""[Unit]
Description=Plunk listener (pictures from your phone into your folders)
After=network.target

[Service]
Type=simple
WorkingDirectory={REPO}
Environment=PLUNK_CONFIG={CONFIG}
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart={REPO}/.venv/bin/uvicorn server.app:create_app --factory --host 127.0.0.1 --port {local} --no-access-log --limit-concurrency 16
Restart=on-failure
RestartSec=2
NoNewPrivileges=true

[Install]
WantedBy=default.target
""")
    must(['systemctl', '--user', 'daemon-reload'], 'Reloading systemd')
    must(['systemctl', '--user', 'enable', 'plunk.service'], 'Enabling the service')
    must(['systemctl', '--user', 'restart', 'plunk.service'], 'Starting the service')
    for _ in range(40):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{local}/api/v1/info', timeout=1) as r:
                if r.status == 200:
                    break
        except OSError:
            time.sleep(0.25)
    else:
        die('The service did not come up.', 'See: plunk logs')
    ok(f'running on 127.0.0.1:{local}')
    linger = run(['loginctl', 'show-user', os.environ.get('USER', ''), '-p', 'Linger']).stdout.strip()
    if linger != 'Linger=yes':
        print(f"  {paint('33', '!')} It stops when you log out. To keep it running: sudo loginctl enable-linger $USER")

    step('Tailscale HTTPS')
    current = serve_ports().get(https)
    target = f'http://127.0.0.1:{local}'
    if current and target not in current:
        die(f'Tailscale Serve already uses port {https} for {current}.', 'Pick another with: plunk install --https-port PORT')
    out = run(['tailscale', 'serve', '--bg', f'--https={https}', target])
    if out.returncode:
        msg = (out.stderr or out.stdout).strip()
        hint = 'Allow your user to manage Serve: sudo tailscale set --operator=$USER' if 'denied' in msg.lower() or 'permission' in msg.lower() else msg
        die('Tailscale Serve could not be set up.', hint)
    ok(url(config))

    step('Command')
    if not BIN.exists() or BIN.resolve() != Path(__file__).resolve():
        BIN.parent.mkdir(parents=True, exist_ok=True)
        if BIN.is_symlink() or BIN.exists():
            BIN.unlink()
        BIN.symlink_to(Path(__file__).resolve())
    ok(f'plunk → {BIN}')
    if str(BIN.parent) not in os.environ.get('PATH', '').split(':'):
        print(f"  {paint('33', '!')} Add {BIN.parent} to your PATH to run plunk from anywhere.")

    print()
    cmd_pair(a)


def cmd_pair(a):
    config = load()
    if config['auth']['mode'] != 'bearer':
        die('Pairing needs token authentication.')
    code = f'{secrets.randbelow(10 ** 6):06d}'
    STATE.mkdir(parents=True, exist_ok=True)
    path = Path(config.get('state_dir', STATE)) / 'pairing.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'code_sha256': hashlib.sha256(code.encode()).hexdigest(), 'expires': time.time() + PAIR_MINUTES * 60}, f)
    link = f'{url(config)}/app#pair={code}'
    try:
        import qrcode
        qr = qrcode.QRCode(border=2)
        qr.add_data(link)
        qr.print_ascii(invert=True)
    except ImportError:
        pass
    pretty = f'{code[:3]} {code[3:]}'
    print(paint('1', f'  Pairing code: {pretty}') + paint('2', f'   (works once, expires in {PAIR_MINUTES} minutes)'))
    print(f"""
  1. Scan the code with your iPhone camera (Tailscale connected), or open {url(config)}/app
  2. In Safari: Share → Add to Home Screen, then open Plunk from the icon
  3. Enter {pretty} when Plunk asks. Done.""")


def cmd_add(a, path=None):
    config = load()
    target = Path(path or a.path).expanduser().resolve()
    if not target.is_dir():
        die(f'{target} is not a folder.')
    if not os.access(target, os.W_OK | os.X_OK):
        die(f'You cannot write to {target}, so Plunk cannot either.')
    for r in config['roots']:
        if Path(r['path']) == target:
            ok(f"already a destination: {r['name']} → {target}")
            return
    name = (a.name or target.name).strip()
    root = {'id': slug(name, {r['id'] for r in config['roots']}), 'name': name, 'path': str(target)}
    config['roots'].append(root)
    save(config)
    ok(f"{paint('1', name)} → {target}")
    print(paint('2', '    It shows up in the phone app under Choose a location.'))


def cmd_here(a):
    cmd_add(a, path=os.getcwd())


def find_root(config, needle):
    as_path = Path(needle).expanduser()
    for r in config['roots']:
        if needle in (r['id'], r['name']) or (as_path.exists() and Path(r['path']) == as_path.resolve()):
            return r
    die(f'No destination called {needle}.', 'See them with: plunk ls')


def cmd_rm(a):
    config = load()
    r = find_root(config, a.target)
    if len(config['roots']) == 1:
        die('That is the only destination. Add another before removing it.')
    config['roots'].remove(r)
    save(config)
    ok(f"removed {r['name']} (its files are untouched)")


def cmd_ls(a):
    config = load()
    width = max(len(r['name']) for r in config['roots'])
    for r in config['roots']:
        missing = '' if Path(r['path']).is_dir() else paint('31', '  (folder missing)')
        print(f"  {r['name']:<{width}}  {paint('2', r['path'])}{missing}")


def cmd_status(a):
    config = load()
    local = config.get('install', {}).get('local_port')
    active = run(['systemctl', '--user', 'is-active', 'plunk.service']).stdout.strip()
    healthy = False
    if local:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{local}/api/v1/info', timeout=2) as r:
                healthy = r.status == 200
        except OSError:
            pass
    print(f"  service       {paint('32' if active == 'active' else '31', active)}{'' if healthy else paint('31', ' (not answering)')}")
    print(f'  app           {url(config)}/app')
    print(f"  destinations  {len(config['roots'])}  (plunk ls)")


def cmd_url(a):
    print(f'{url(load())}/app')


def cmd_logs(a):
    os.execvp('journalctl', ['journalctl', '--user', '-u', 'plunk.service', '-n', str(a.lines), '--no-pager'])


def main():
    ap = argparse.ArgumentParser(prog='plunk', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('install', help='one-time setup on this server')
    p.add_argument('--name', help='server name shown on the phone')
    p.add_argument('--https-port', type=int, help='Tailscale HTTPS port (default: first free of 443, 8443, 7400+)')
    p.add_argument('--local-port', type=int, help='loopback port for the service (default: first free from 8787)')
    p.add_argument('--inbox', default='~/Plunk', help='first destination folder (default: ~/Plunk)')
    p.add_argument('--import-config', metavar='PATH', help="reuse the token and app address from a Docker install's config.json")
    p.add_argument('--rebuild', action='store_true', help='rebuild the phone app')
    p.set_defaults(fn=cmd_install)
    sub.add_parser('pair', help='connect a phone').set_defaults(fn=cmd_pair)
    p = sub.add_parser('add', help='add a destination folder')
    p.add_argument('path')
    p.add_argument('--name')
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser('here', help='add the current folder')
    p.add_argument('--name')
    p.set_defaults(fn=cmd_here)
    p = sub.add_parser('rm', help='remove a destination')
    p.add_argument('target', help='name or path')
    p.set_defaults(fn=cmd_rm)
    sub.add_parser('ls', help='list destinations').set_defaults(fn=cmd_ls)
    sub.add_parser('status', help='service status').set_defaults(fn=cmd_status)
    sub.add_parser('url', help='print the app address').set_defaults(fn=cmd_url)
    p = sub.add_parser('logs', help='recent service logs')
    p.add_argument('-n', '--lines', type=int, default=50)
    p.set_defaults(fn=cmd_logs)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
