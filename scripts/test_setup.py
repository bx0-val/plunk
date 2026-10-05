import json
import pytest
from scripts.setup import configuration, write_configuration

def test_tailscale_config(tmp_path):
    config, env = configuration('home.tail123.ts.net.', 'Home lab', '/srv/plunk/pictures')
    assert config['origins'] == ['https://home.tail123.ts.net']
    assert len(config['auth']['token']) >= 32
    assert "COMPOSE_FILE=compose.tailscale.yaml" in env
    write_configuration(tmp_path, config, env)
    assert json.loads((tmp_path / 'config.json').read_text()) == config
    assert (tmp_path / 'config.json').stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError):
        write_configuration(tmp_path, config, env)
    assert json.loads((tmp_path / 'config.json').read_text()) == config

def test_alternate_port():
    config, env = configuration('home.tail123.ts.net', 'Home', '/srv/my pictures', 8443)
    assert config['origins'] == ['https://home.tail123.ts.net:8443']
    assert "PLUNK_UPLOADS='/srv/my pictures'" in env

@pytest.mark.parametrize('host', ['http://home.tail123.ts.net', 'localhost', 'home.tail123.ts.net/bad', 'a..ts.net', 'home.ts.net\nINJECT=1'])
def test_bad_host(host):
    with pytest.raises(ValueError):
        configuration(host, 'Home', '/srv/plunk')

@pytest.mark.parametrize('path', ['relative', '/srv/bad\npath', '/srv/${HOME}', "/srv/a'b"])
def test_bad_path(path):
    with pytest.raises(ValueError):
        configuration('home.tail123.ts.net', 'Home', path)
