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



def test_interrupted_preference_write_preserves_previous_policy(tmp_path, monkeypatch):
    import core.evidence_settings as settings
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    set_capture(tmp_path, False)
    directory = tmp_path / 'evidence_archive/preferences'
    previous = {p.name: p.read_bytes() for p in directory.glob('*.json')}
    with monkeypatch.context() as crash:
        def fail_sync(fd):
            raise OSError('simulated storage interruption')
        crash.setattr(settings.os, 'fsync', fail_sync)
        with pytest.raises(OSError):
            set_capture(tmp_path, True)
    assert read_policy(tmp_path).capture_deleted_content is False
    assert {p.name: p.read_bytes() for p in directory.glob('*.json')} == previous
    assert len(list(directory.glob('*.pending'))) == 2
    assert set_capture(tmp_path, True).capture_deleted_content is True
    assert read_policy(tmp_path).capture_deleted_content is True


@pytest.mark.parametrize('operation', ['move_to_trash', 'delete'])
def test_engine_deletion_preserves_full_content_and_blocks_on_archive_failure(tmp_path, monkeypatch, operation):
    import core.evidence_settings as settings
    from task_engine.engine import TaskStore
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'internal')
    store = TaskStore(tmp_path)
    task = store.create('Recover this', 'full original description', 'guvenli_yurut')
    original = task.to_dict()
    def remove():
        if operation == 'delete':
            return store.delete(task.task_id, user_initiated=True)
        return store.move_to_trash(task.task_id)
    with monkeypatch.context() as broken:
        def fail(*args, **kwargs):
            raise OSError('archive unavailable')
        broken.setattr(settings, '_save', fail)
        with pytest.raises(OSError):
            remove()
    assert store.get(task.task_id).to_dict() == original
    assert TaskStore(tmp_path).get(task.task_id).to_dict() == original
    assert remove() is True
    archive = list((tmp_path / 'evidence_archive/deleted_content').glob('*.json'))
    assert len(archive) == 1
    assert json.loads(archive[0].read_text())['content']['payload'] == original


@pytest.mark.parametrize('operation', ['move_to_trash', 'delete'])
def test_engine_reads_workspace_capture_preference(tmp_path, monkeypatch, operation):
    from task_engine.engine import TaskStore
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    set_capture(tmp_path, False)
    store = TaskStore(tmp_path / 'tasks')
    task = store.create('Customer preference', 'content', 'guvenli_yurut')
    if operation == 'delete':
        assert store.delete(task.task_id, user_initiated=True)
    else:
        assert store.move_to_trash(task.task_id)
    assert not list(tmp_path.rglob('deleted_content/*.json'))


@pytest.mark.parametrize('operation', ['move_to_trash', 'delete'])
@pytest.mark.parametrize('capture', [True, False])
@pytest.mark.parametrize('layout', ['implicit_tasks', 'explicit_live', 'custom'])
def test_sandbox_archive_isolated_but_reads_live_preference(tmp_path, monkeypatch, operation, capture, layout):
    from core.workspace_contract import CoreWriteForbidden
    from task_engine.engine import TaskStore
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    live = tmp_path / 'live'
    if layout == 'implicit_tasks':
        base, explicit = live / 'tasks', None
    elif layout == 'explicit_live':
        base, explicit = tmp_path / 'execution' / 'tasks', live
    else:
        base, explicit = live, None
    set_capture(live, capture)
    source = TaskStore(base)
    task = source.create('Sandbox content', 'private sandbox payload', 'guvenli_yurut')
    preference_bytes = {p.name: p.read_bytes() for p in (live / 'evidence_archive/preferences').glob('*.json')}
    store = TaskStore(base, sandbox_mode=True, live_base_dir=explicit)
    try:
        if operation == 'delete':
            store.delete(task.task_id, user_initiated=True)
        else:
            store.move_to_trash(task.task_id)
    except CoreWriteForbidden:
        # A live task store itself remains protected, including after the
        # archive attempt. This path previously leaked before that rejection.
        assert TaskStore(base).get(task.task_id) is not None
    assert not (live / 'evidence_archive/deleted_content').exists()
    copies = list((live / 'sandbox/evidence_archive/deleted_content').glob('*.json'))
    assert len(copies) == (1 if capture else 0)
    assert {p.name: p.read_bytes() for p in (live / 'evidence_archive/preferences').glob('*.json')} == preference_bytes


@pytest.mark.parametrize('operation', ['restore', 'delete_permanent'])
@pytest.mark.parametrize('archive_fails', [False, True])
def test_panel_legacy_trash_bytes_preserved_before_removal(tmp_path, monkeypatch, operation, archive_fails):
    import base64
    import core.evidence_settings as settings
    import panel_tasks_server as pts
    monkeypatch.setenv('LUMOS_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'internal')
    monkeypatch.setenv('LUMOS_CONFIRMATION_ENABLED', 'false')
    monkeypatch.setattr(pts, '_task_action_gate', lambda *a, **k: {'enabled': True})
    monkeypatch.setattr(pts, '_enforce_panel_mutation_confirmation', lambda *a, **k: None)
    monkeypatch.setattr(pts, '_is_sandbox_mode', lambda: False)
    path = tmp_path / 'trash/legacy.json'
    path.parent.mkdir()
    raw = b'{ "id": "legacy", "payload": {"id":"legacy", "title":"Original"}, "unknown_legacy_context": [1, 2, 3] }\n'
    path.write_bytes(raw)
    handler = object.__new__(pts.Handler)
    handler._read_json_body = lambda: {'id': 'legacy', 'confirm': True}
    replies = []
    monkeypatch.setattr(pts, '_send_json', lambda handler, code, body: replies.append((code, body)))
    if archive_fails:
        def fail(*a, **k):
            raise OSError('no archive storage')
        monkeypatch.setattr(settings, '_save', fail)
    getattr(handler, '_post_' + operation)()
    if archive_fails:
        assert replies[-1][0] == 500
        assert path.read_bytes() == raw
        assert not (tmp_path / 'tasks.json').exists()
    else:
        assert replies[-1][0] == 200
        assert not path.exists()
        copies = list((tmp_path / 'evidence_archive/deleted_content').glob('*.json'))
        assert len(copies) == 1
        content = json.loads(copies[0].read_text())['content']
        assert base64.b64decode(content['data']) == raw
        assert len(list((tmp_path / 'evidence_archive/removal_evidence').glob('*.json'))) == 1


def test_legacy_store_write_always_has_correlated_audit(tmp_path):
    from core.workspace_contract import save_task_store_json
    from core.evidence_continuity import evidence_continuity_path
    save_task_store_json(tmp_path / 'tasks', {'tasks': []}, sandbox_mode=False)
    records = [json.loads(line) for line in evidence_continuity_path(tmp_path).read_text().splitlines()]
    assert len(records) == 2
    assert [r['phase'] for r in records] == ['before', 'after']
    assert records[0]['correlation_id'] == records[1]['correlation_id']
    assert all(r['mutation'] == 'update' for r in records)


def test_legacy_store_write_audit_failure_preserves_existing_bytes(tmp_path, monkeypatch):
    import core.evidence_continuity as ec
    from core.workspace_contract import save_task_store_json
    target = tmp_path / 'tasks/tasks.json'
    target.parent.mkdir()
    target.write_bytes(b'{"tasks": [], "custom": "preserve me"}\n')
    before = target.read_bytes()
    monkeypatch.setattr(ec, 'append_evidence_event', lambda *a, **k: {'appended': False})
    with pytest.raises(OSError, match='mutation blocked'):
        save_task_store_json(target.parent, {'tasks': [{'task_id': 1}]}, sandbox_mode=False)
    assert target.read_bytes() == before
