"""Start a loopback-only Linux test listener with a workspace-local config."""
import json
from pathlib import Path
import uvicorn
from server.app import create_app

base = Path(__file__).resolve().parents[1] / '.local'
root = base / 'uploads'
(root / 'next-big-thing').mkdir(parents=True, exist_ok=True)
(root / 'hardware').mkdir(exist_ok=True)
config = {'name': 'Home lab', 'auth': {'mode': 'none'}, 'origins': ['http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:4173', 'http://localhost:4173'], 'roots': [{'id':'projects','name':'Projects','path':str(root)}], 'state_dir':str(base/'state')}
if __name__ == '__main__':
    uvicorn.run(create_app(config), host='127.0.0.1', port=8741, access_log=False)
