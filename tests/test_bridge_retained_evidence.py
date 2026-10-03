import base64
import json
from types import SimpleNamespace

import pytest

from core.bridge_evidence import BridgeEvidenceError
from kando import cursor_bridge as bridge


def packet(value):
    return SimpleNamespace(to_json_dict=lambda: {'value': value})


def test_replacement_preserves_exact_legacy_pair(tmp_path):
    folder = tmp_path / 'cursor_bridge'
    folder.mkdir()
    old = [b'{ "legacy": "execution", "unknown": 3 }\n', b'{"legacy":"result"}\n']
    for name, raw in zip(('last_execution.json', 'last_result.json'), old):
        (folder / name).write_bytes(raw)
    paths = bridge.persist_cursor_bridge(tmp_path, packet('new execution'), packet('new result'))
    copies = list((tmp_path / 'evidence_archive/deleted_content').glob('*.json'))
    assert sorted(base64.b64decode(json.loads(p.read_text())['content']['data']) for p in copies) == sorted(old)
    assert [json.loads(p.read_text())['value'] for p in paths] == ['new execution', 'new result']


def test_archive_failure_preserves_both_views(tmp_path, monkeypatch):
    import core.evidence_settings as settings
    folder = tmp_path / 'cursor_bridge'
    folder.mkdir()
    for name in ('last_execution.json', 'last_result.json'):
        (folder / name).write_bytes(b'original')
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')
    monkeypatch.setattr(settings, '_save', fail)
    with pytest.raises(BridgeEvidenceError, match='do not replay'):
        bridge.persist_cursor_bridge(tmp_path, packet('new'), packet('new'))
    assert all(p.read_bytes() == b'original' for p in folder.iterdir())


def test_emergency_path_does_not_bypass_archive_failure(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise BridgeEvidenceError('archive unavailable')
    monkeypatch.setattr(bridge, 'persist_cursor_bridge', fail)
    monkeypatch.setattr(bridge, '_append_patch_apply_log', lambda *a: None)
    with pytest.raises(BridgeEvidenceError):
        bridge._write_emergency_bridge_files(tmp_path, 'goal', permission_profile='test',
                                            general_approval=False, brain_success=False, task=None)
    assert not (tmp_path / 'cursor_bridge/last_execution.json').exists()


def test_runner_does_not_enter_execution_fallback_after_archive_failure(tmp_path, monkeypatch):
    import core.brain
    monkeypatch.setenv('LUMOS_BASE_DIR', str(tmp_path))
    result = SimpleNamespace(task_id=0, success=True, pipeline={})
    monkeypatch.setattr(core.brain, 'run', lambda *a, **k: result)
    def fail(*args, **kwargs):
        raise BridgeEvidenceError('do not replay')
    monkeypatch.setattr(bridge, 'persist_bridge_after_brain', fail)
    def unexpected(*args, **kwargs):
        pytest.fail('Execution fallback must not run after archive failure')
    monkeypatch.setattr(bridge, '_write_minimal_bridge_files', unexpected)
    monkeypatch.setattr(bridge, '_write_emergency_bridge_files', unexpected)
    with pytest.raises(BridgeEvidenceError):
        bridge.run_brain_and_persist_bridge('goal', permission_profile='test', general_approval=False)


def test_customer_capture_off_keeps_audit_without_content_copy(tmp_path, monkeypatch):
    from core.evidence_settings import set_capture
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    set_capture(tmp_path, False)
    bridge.persist_cursor_bridge(tmp_path, packet('old'), packet('old'))
    bridge.persist_cursor_bridge(tmp_path, packet('new'), packet('new'))
    assert len(list((tmp_path / 'evidence_archive/removal_evidence').glob('*.json'))) == 2
    assert not (tmp_path / 'evidence_archive/deleted_content').exists()


def test_brain_propagates_archive_error_after_execution(tmp_path, monkeypatch):
    from core.brain import run
    from task_engine import TaskStore, PROFILE_GUVENLI_YURUT
    monkeypatch.setenv('LUMOS_BASE_DIR', str(tmp_path))
    def fail(*args, **kwargs):
        raise BridgeEvidenceError('do not replay')
    monkeypatch.setattr(bridge, 'persist_bridge_after_brain', fail)
    store = TaskStore(tmp_path / 'tasks')
    with pytest.raises(BridgeEvidenceError):
        run('görevi analiz et', store, tmp_path / 'tasks', PROFILE_GUVENLI_YURUT, True)
    assert len(store.list_all()) == 1


def test_executor_summary_retains_exact_previous_content(tmp_path):
    from kando.cursor_executor import run_after_bridge
    folder = tmp_path / 'cursor_bridge'
    folder.mkdir()
    target = folder / 'last_cursor_executor.json'
    old = b'{ "legacy": [1, 2], "unknown": true }\n'
    target.write_bytes(old)
    run_after_bridge(tmp_path, SimpleNamespace(execution_mode='task', constraints={}))
    copies = list((tmp_path / 'evidence_archive/deleted_content').glob('*.json'))
    assert len(copies) == 1
    assert base64.b64decode(json.loads(copies[0].read_text())['content']['data']) == old
    assert json.loads(target.read_text())['execution_mode'] == 'task'


def test_executor_summary_archive_failure_keeps_previous_content(tmp_path, monkeypatch):
    from kando.cursor_executor import run_after_bridge
    import core.evidence_settings as settings
    folder = tmp_path / 'cursor_bridge'
    folder.mkdir()
    target = folder / 'last_cursor_executor.json'
    target.write_bytes(b'previous summary')
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')
    monkeypatch.setattr(settings, '_save', fail)
    with pytest.raises(BridgeEvidenceError):
        run_after_bridge(tmp_path, SimpleNamespace(execution_mode='patch', constraints={}))
    assert target.read_bytes() == b'previous summary'


def test_brain_propagates_executor_summary_archive_error(tmp_path, monkeypatch):
    from core.brain import run
    from task_engine import TaskStore, PROFILE_GUVENLI_YURUT
    import kando.cursor_executor as executor
    monkeypatch.setenv('LUMOS_BASE_DIR', str(tmp_path))
    def fail(*args, **kwargs):
        raise BridgeEvidenceError('summary archive unavailable; do not replay')
    monkeypatch.setattr(executor, 'run_after_bridge', fail)
    store = TaskStore(tmp_path / 'tasks')
    with pytest.raises(BridgeEvidenceError, match='summary archive'):
        run('görevi analiz et', store, tmp_path / 'tasks', PROFILE_GUVENLI_YURUT, True)
    assert len(store.list_all()) == 1
