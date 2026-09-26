import base64
import json
from types import SimpleNamespace

import pytest

from core.bridge_evidence import BridgeEvidenceError
from kando_bridge import server


@pytest.fixture
def folders(tmp_path, monkeypatch):
    base = tmp_path / '.lumos'
    bridge = base / 'cursor_bridge'
    outbox = base / 'outbox'
    bridge.mkdir(parents=True)
    outbox.mkdir()
    monkeypatch.setattr(server, 'ROOT', tmp_path)
    monkeypatch.setattr(server, 'CURSOR_BRIDGE_DIR', bridge)
    monkeypatch.setattr(server, 'OUTBOX_DIR', outbox)
    monkeypatch.setattr(server, 'LAST_EXECUTION_FILE', outbox / 'last_execution.json')
    monkeypatch.setattr(server, 'LAST_RESULT_FILE', outbox / 'last_result.json')
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'internal')
    return base, bridge, outbox


def archived(base):
    return [base64.b64decode(json.loads(p.read_text())['content']['data'])
            for p in (base / 'evidence_archive/deleted_content').glob('*.json')]


def test_prelaunch_retains_all_old_inputs_and_outputs(folders, monkeypatch):
    base, bridge, _ = folders
    old = [b'old command\r\n', b'old result', b'old execution']
    for name, raw in zip(('command.json', 'last_result.json', 'last_execution.json'), old):
        (bridge / name).write_bytes(raw)
    def launch(*args, **kwargs):
        assert sorted(archived(base)) == sorted(old)
        assert not (bridge / 'last_execution.json').exists()
        return SimpleNamespace(returncode=0, stderr='', stdout='')
    monkeypatch.setattr(server.subprocess, 'run', launch)
    assert server._run_cursor_bridge('new command')[0] == 0


def test_prelaunch_archive_failure_blocks_execution_and_mutation(folders, monkeypatch):
    import core.evidence_settings as settings
    _, bridge, _ = folders
    for name in ('command.json', 'last_result.json', 'last_execution.json'):
        (bridge / name).write_bytes(b'old')
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')
    monkeypatch.setattr(settings, '_save', fail)
    monkeypatch.setattr(server.subprocess, 'run', lambda *a, **k: pytest.fail('must not execute'))
    with pytest.raises(BridgeEvidenceError):
        server._run_cursor_bridge('new command')
    assert all(p.read_bytes() == b'old' for p in bridge.iterdir())


@pytest.mark.parametrize('writer', ['copy', 'gate', 'snapshot'])
def test_outbox_writers_preserve_old_pair(folders, writer):
    base, bridge, outbox = folders
    for name in ('last_execution.json', 'last_result.json'):
        (outbox / name).write_bytes(name.encode())
        (bridge / name).write_text('{}')
    if writer == 'copy':
        server._copy_bridge_outputs_to_outbox()
    elif writer == 'gate':
        server.persist_last_result_from_out({'last_execution': {}, 'last_result': {}})
    else:
        server.persist_post_task_outbox_snapshots({}, None)
    assert sorted(archived(base)) == [b'last_execution.json', b'last_result.json']


@pytest.mark.parametrize('writer', ['copy', 'gate', 'snapshot'])
def test_outbox_archive_failure_is_not_swallowed(folders, monkeypatch, writer):
    import core.evidence_settings as settings
    _, bridge, outbox = folders
    for name in ('last_execution.json', 'last_result.json'):
        (outbox / name).write_bytes(b'old')
        (bridge / name).write_text('{}')
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')
    monkeypatch.setattr(settings, '_save', fail)
    with pytest.raises(BridgeEvidenceError):
        if writer == 'copy':
            server._copy_bridge_outputs_to_outbox()
        elif writer == 'gate':
            server.persist_last_result_from_out({'last_execution': {}, 'last_result': {}})
        else:
            server.persist_post_task_outbox_snapshots({}, None)
    assert all(p.read_bytes() == b'old' for p in outbox.iterdir())


@pytest.mark.parametrize('clear', [True, False])
def test_direct_patch_metadata_retained_before_change(folders, monkeypatch, clear):
    base, bridge, _ = folders
    target = bridge / 'direct_patch_meta.json'
    old = b'{ "auto_approve_safe": true, "legacy": 3 }\r\n'
    target.write_bytes(old)
    monkeypatch.setattr(server, 'DIRECT_PATCH_META_FILE', target)
    if clear:
        server._clear_direct_patch_meta()
        assert not target.exists()
    else:
        server._persist_direct_patch_meta({'auto_approve_safe': False})
        assert json.loads(target.read_text()) == {'auto_approve_safe': False}
    assert archived(base) == [old]


@pytest.mark.parametrize('clear', [True, False])
def test_metadata_archive_failure_propagates(folders, monkeypatch, clear):
    import core.evidence_settings as settings
    _, bridge, _ = folders
    target = bridge / 'direct_patch_meta.json'
    target.write_bytes(b'old')
    monkeypatch.setattr(server, 'DIRECT_PATCH_META_FILE', target)
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')
    monkeypatch.setattr(settings, '_save', fail)
    with pytest.raises(BridgeEvidenceError):
        if clear:
            server._clear_direct_patch_meta()
        else:
            server._persist_direct_patch_meta({'auto_approve_safe': False})
    assert target.read_bytes() == b'old'
