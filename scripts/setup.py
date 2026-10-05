"""One-time Tailscale configuration. Standard-library Python; never overwrites files."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess

BASE = Path(__file__).resolve().parents[1]

def tailscale_hostname():
    try:
        result = subprocess.run(['tailscale', 'status', '--json'], check=True, capture_output=True, text=True, timeout=10)
        return json.loads(result.stdout)['Self']['DNSName'].rstrip('.')
    except (OSError, subprocess.SubprocessError, KeyError, ValueError):
        return ''

def configuration(host, name, upload_path, port=443):
    host = host.lower().strip().rstrip('.')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.ts\.net', host) or '..' in host:
        raise ValueError('Enter the full Tailscale DNS name, like my-server.tail1234.ts.net (without https://).')
    if port not in (443, 8443):
        raise ValueError('Choose HTTPS port 443 or 8443.')
    path = str(Path(upload_path).expanduser())
    if not Path(path).is_absolute() or any(c in path for c in ('\n', '\r', "'", '$', ':', '\\')):
        raise ValueError('Choose an absolute Linux folder path without quotes, dollar signs, colons, or newlines.')
    origin = 'https://' + host + (':8443' if port == 8443 else '')
    config = {'name': name.strip() or 'My server', 'auth': {'mode': 'bearer', 'token': secrets.token_urlsafe(32)}, 'origins': [origin], 'roots': [{'id': 'pictures', 'name': 'Pictures', 'path': '/uploads'}], 'state_dir': '/state', 'max_upload_mb': 25, 'file_mode': '0644'}
    env = f"COMPOSE_FILE=compose.tailscale.yaml\nPLUNK_UPLOADS='{path}'\nPLUNK_URL={origin}\nPLUNK_HTTPS_PORT={port}\n"
    return config, env

def write_configuration(base, config, env):
    if any((base / p).exists() for p in ('config.json', '.env')):
        raise ValueError('config.json or .env already exists. Nothing was changed. Edit your existing configuration instead.')
    written = []
    try:
        for name, data in (('config.json', json.dumps(config, indent=2) + '\n'), ('.env', env)):
            fd = os.open(base / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            written.append(base / name)
            with os.fdopen(fd, 'w') as stream:
                stream.write(data)
    except BaseException:
        for path in written:
            path.unlink()
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--show-token', action='store_true', help='Display the saved token for copying into your phone.')
    args = parser.parse_args()
    if args.show_token:
        print(json.loads((BASE / 'config.json').read_text())['auth']['token'])
        return
    if any((BASE / p).exists() for p in ('config.json', '.env')):
        raise ValueError('Configuration already exists. Nothing changed. Use --show-token or edit the existing files.')
    print('Plunk + Tailscale. This creates configuration only; it does not start services.')
    detected = tailscale_hostname()
    host = input(f'Tailscale DNS name [{detected}]: ').strip() or detected
    port = int(input('HTTPS port [443] (use 8443 if Serve already uses 443): ').strip() or '443')
    name = input('Server name [My server]: ').strip() or 'My server'
    path = input('New picture folder [/srv/plunk/pictures]: ').strip() or '/srv/plunk/pictures'
    config, env = configuration(host, name, path, port)
    write_configuration(BASE, config, env)
    path = str(Path(path).expanduser())
    print('\nConfiguration saved. Run these from the Plunk repository:')
    print('sudo chgrp 10001 config.json')
    print('chmod 640 config.json')
    if Path(path).exists():
        print('# This picture folder already exists. Grant UID 10001 access using your normal group/ACL policy; do not change ownership blindly.')
    else:
        print('# Create your new dedicated picture directory:')
        print(f'sudo install -d -o 10001 -g 10001 -m 755 {shlex.quote(path)}')
    print('sudo docker compose up -d --build')
    print(f'sudo tailscale serve --bg --https={port} http://127.0.0.1:8787')
    print('\nPhone address: ' + config['origins'][0] + '/app')
    print('Show the token when ready: python3 scripts/setup.py --show-token')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
