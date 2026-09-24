import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.evidence_settings import archive_deleted_content, read_policy, set_capture
from core.workspace_contract import save_trash_record_json


def test_internal_cannot_disable_even_if_customer_file_exists(tmp_path, monkeypatch):
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    set_capture(tmp_path, False)
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'internal')
    assert read_policy(tmp_path).capture_deleted_content
    assert not read_policy(tmp_path).view()['toggle_visible']
    with pytest.raises(ValueError):
        set_capture(tmp_path, False)


def test_customer_switch_only_affects_future_archive_copies(tmp_path, monkeypatch):
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    first = archive_deleted_content(tmp_path, {'id': 'first'})
    original = first.read_bytes()
    set_capture(tmp_path, False)
    assert archive_deleted_content(tmp_path, {'id': 'second'}) is None
    assert first.read_bytes() == original
    set_capture(tmp_path, True)
    assert archive_deleted_content(tmp_path, {'id': 'third'}).exists()
    assert len(list((tmp_path / 'evidence_archive/preferences').glob('*.json'))) == 2
    terms = json.loads(original)['retention']
    assert terms['classification_hold'] is True
    assert terms['default_retention'] == 'indefinite'


def test_corrupt_preferences_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    set_capture(tmp_path, False)
    file = next((tmp_path / 'evidence_archive/preferences').glob('*.json'))
    file.write_text('invalid')
    with pytest.raises(ValueError):
        archive_deleted_content(tmp_path, {'id': 'blocked'})


def test_trash_sink_archives_before_source_can_be_removed(tmp_path, monkeypatch):
    monkeypatch.delenv('LUMOS_DEPLOYMENT_PROFILE', raising=False)
    target = tmp_path / 'trash/task.json'
    save_trash_record_json(tmp_path, target, {'id': 'preserved'})
    archives = list((tmp_path / 'evidence_archive/deleted_content').glob('*.json'))
    assert len(archives) == 1
    assert json.loads(archives[0].read_text())['content'] == {'id': 'preserved'}
    target.unlink()  # Simulate consumption of undo copy; durable archive survives.
    assert archives[0].exists()


def test_parallel_capture_does_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.delenv('LUMOS_DEPLOYMENT_PROFILE', raising=False)
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(lambda n: archive_deleted_content(tmp_path, {'id': n}), range(32)))
    assert len(set(paths)) == 32
    assert {json.loads(p.read_text())['content']['id'] for p in paths} == set(range(32))


def test_panel_write_stops_when_journal_unavailable(tmp_path, monkeypatch):
    import panel_tasks_server as pts
    monkeypatch.setenv('LUMOS_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(pts, 'append_evidence_event', lambda *a, **kw: {'appended': False})
    with pytest.raises(OSError, match='mutation blocked'):
        pts._write_doc({'tasks': []}, evidence={
            'operation': 'panel.task.create', 'mutation': 'create', 'entity_id': 'one',
        })
    assert not (tmp_path / 'tasks.json').exists()


@pytest.mark.parametrize('profile', ['internal', 'customer'])
def test_settings_real_http_auth_lock_and_origin(tmp_path, monkeypatch, profile):
    import threading
    import urllib.request
    import urllib.error
    from http.server import HTTPServer
    import panel_tasks_server as pts

    monkeypatch.setenv('LUMOS_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', profile)
    monkeypatch.setenv('LUMOS_PANEL_TASKS_SECRET', 'test-retention-secret')
    # Handler obtains its auth from the module's normal factory/environment.
    server = HTTPServer(('127.0.0.1', 0), pts.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/evidence/settings'
    def request(body=None, token=True, origin='http://localhost:4321'):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None)
        req.add_header('Origin', origin)
        req.add_header('Content-Type', 'application/json')
        if token:
            req.add_header('X-Kando-Token', 'test-retention-secret')
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)
    try:
        options = urllib.request.Request(url, method='OPTIONS', headers={
            'Origin': 'http://localhost:4321',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,x-kando-token',
        })
        with urllib.request.urlopen(options, timeout=3) as response:
            assert response.headers['Access-Control-Allow-Origin'] == 'http://localhost:4321'
        assert request(token=False)[0] == 401
        assert request(origin='https://untrusted.invalid')[0] == 403
        code, view = request()
        assert code == 200
        assert view['toggle_visible'] == (profile == 'customer')
        assert request({'profile': 'customer', 'capture_deleted_content': False})[0] == 400
        code, _ = request({'capture_deleted_content': False})
        assert code == (200 if profile == 'customer' else 409)
        assert request()[1]['capture_deleted_content'] == (profile == 'internal')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
