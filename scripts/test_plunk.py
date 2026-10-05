"""Native CLI regressions. All configuration and destinations are temporary."""
import hashlib
import io
import json
from types import SimpleNamespace
import pytest
from scripts import plunk
from scripts.plunk_ui import Terminal


@pytest.fixture
def config(tmp_path, monkeypatch):
    path = tmp_path / 'config.json'
    value = {'name': 'Home lab', 'origins': ['https://lab.example:8443'],
             'auth': {'mode': 'bearer', 'token': 'test-secret-not-for-display'},
             'roots': [{'id': 'a', 'name': 'Project', 'path': str(tmp_path)}],
             'state_dir': str(tmp_path / 'custom-state')}
    path.write_text(json.dumps(value))
    monkeypatch.setattr(plunk, 'CONFIG', path)
    monkeypatch.setattr(plunk, 'UI', Terminal('never', io.StringIO()))
    return value


def test_pair_uses_configured_state_and_never_displays_token(config, monkeypatch):
    monkeypatch.setattr(plunk.secrets, 'randbelow', lambda _: 123456)
    plunk.cmd_pair(None)
    record = plunk.Path(config['state_dir']) / 'pairing.json'
    data = json.loads(record.read_text())
    assert data['code_sha256'] == hashlib.sha256(b'123456').hexdigest()
    assert record.stat().st_mode & 0o777 == 0o600
    output = plunk.UI.stream.getvalue()
    assert '123  456' in output
    assert 'https://lab.example:8443/app#pair=123456' in output
    assert config['auth']['token'] not in output
    assert '\x1b' not in output


def test_pair_failure_preserves_previous_code(config, monkeypatch):
    plunk.cmd_pair(None)
    path = plunk.Path(config['state_dir']) / 'pairing.json'
    original = path.read_bytes()
    def interrupted(*_):
        raise OSError('disk unavailable')
    monkeypatch.setattr(plunk.os, 'replace', interrupted)
    with pytest.raises(OSError):
        plunk.cmd_pair(None)
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


def test_ambiguous_display_names_need_an_id(config):
    config['roots'].append({'id': 'b', 'name': 'Project', 'path': '/another'})
    with pytest.raises(SystemExit):
        plunk.find_root(config, 'Project')
    assert plunk.find_root(config, 'b')['path'] == '/another'


def test_here_can_rename_existing_destination(config):
    plunk.cmd_add(SimpleNamespace(name='Better name'), path=config['roots'][0]['path'])
    roots = plunk.load()['roots']
    assert len(roots) == 1
    assert roots[0]['name'] == 'Better name'
    assert roots[0]['id'] == 'a'


def test_endpoint_change_updates_pair_address_preserving_extra_origins(config, monkeypatch):
    config['install'] = {'https_port': 8443, 'local_port': 8787}
    config['origins'].append('https://phone.example')
    monkeypatch.setattr(plunk, 'pick_local_port', lambda: pytest.fail('Existing port must be reused'))
    plunk.update_endpoint(config, 'lab.example', 7400)
    assert plunk.url(config) == 'https://lab.example:7400'
    assert 'https://phone.example' in config['origins']
    assert config['install']['local_port'] == 8787


def test_imported_endpoint_uses_its_port(config, monkeypatch):
    monkeypatch.setattr(plunk, 'pick_local_port', lambda: 8790)
    plunk.update_endpoint(config, 'lab.example')
    assert plunk.url(config) == 'https://lab.example:8443'
    assert config['install'] == {'https_port': 8443, 'local_port': 8790}


def test_color_and_terminal_control_safety(monkeypatch):
    monkeypatch.setenv('NO_COLOR', '1')
    monkeypatch.setenv('FORCE_COLOR', '1')
    assert not Terminal(stream=io.StringIO()).color
    terminal = Terminal('always', io.StringIO())
    assert '\x1b[38;5;208m' in terminal.paint('orange', 'plunk')
    assert '\x1b[2J' not in terminal.paint('orange', 'bad\x1b[2Jname')
    assert '\x1b' not in Terminal('never').paint('orange', 'plunk')


def test_pair_link_remains_copyable_in_narrow_terminal():
    terminal = Terminal('never', io.StringIO())
    terminal.width = 32
    base = 'https://very-long-server-name.tail123456.ts.net:8443'
    terminal.pairing('Home lab', base, '123456', 10)
    assert f'{base}/app#pair=123456' in terminal.stream.getvalue()


def test_url_is_plain_for_pipes(config, capsys):
    plunk.cmd_url(None)
    assert capsys.readouterr().out == 'https://lab.example:8443/app\n'
