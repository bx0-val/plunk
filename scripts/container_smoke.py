"""CI-only smoke test for the exact Docker images and Tailscale loopback topology."""
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid
import httpx
from PIL import Image

if os.environ.get('CI') != 'true':
    raise SystemExit('Run this only in the disposable CI workspace.')
config_path = Path('config.json')
if config_path.exists():
    raise SystemExit('Refusing to replace an existing configuration.')
destination = Path('.local/container-uploads').resolve()
destination.mkdir(parents=True)
subprocess.run(['sudo', 'chown', '10001:10001', str(destination)], check=True)
token = secrets.token_urlsafe(32)
config = {'name':'Container check','auth':{'mode':'bearer','token':token},'origins':['https://test.tail123.ts.net'],'roots':[{'id':'pictures','name':'Pictures','path':'/uploads'}],'state_dir':'/state'}
config_path.write_text(json.dumps(config))
subprocess.run(['sudo','chgrp','10001',str(config_path)],check=True)
config_path.chmod(0o640)
env = {**os.environ, 'PLUNK_UPLOADS':str(destination)}
compose = ['docker','compose','-p','plunk-smoke','-f','compose.tailscale.yaml']
try:
    subprocess.run(compose + ['up','-d','--wait','--wait-timeout','90'],env=env,check=True)
    with httpx.Client(base_url='http://127.0.0.1:8787', timeout=10) as client:
        for attempt in range(30):
            try:
                response = client.get('/api/v1/info')
                if response.status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError('Listener did not become ready')
        assert response.json()['auth'] == 'bearer'
        assert client.get('/').status_code == 200
        assert 'Tailscale' in client.get('/setup.html').text
        assert client.get('/api/v1/directories').status_code == 401
        client.headers['Authorization'] = 'Bearer ' + token
        assert client.get('/api/v1/directories').status_code == 200
        data = io.BytesIO()
        Image.new('RGB',(40,30),'orange').save(data,format='PNG')
        rid = str(uuid.uuid4())
        fields = {'root':'pictures','path':'','name':'container-check','request_id':rid}
        response = client.post('/api/v1/uploads',data=fields,files={'image':('photo.png',data.getvalue(),'image/png')})
        assert response.status_code == 200, response.text
        assert (destination/'container-check.jpg').is_file()
        with Image.open(destination/'container-check.jpg') as saved:
            assert saved.format == 'JPEG' and saved.size == (40,30)
        retry = client.post('/api/v1/uploads',data=fields,files={'image':('photo.png',data.getvalue(),'image/png')})
        assert retry.json() == response.json()
    print('Container smoke passed: frontend, guide, authentication, JPEG upload, and retry.')
finally:
    subprocess.run(compose + ['logs','--tail','40'],env=env)
    subprocess.run(compose + ['down','-v'],env=env)
