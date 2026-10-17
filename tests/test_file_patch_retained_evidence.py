import base64
import json

import pytest

from kando import file_patch_executor as executor


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('LUMOS_BASE_DIR', str(tmp_path / '.lumos'))
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'internal')
    return tmp_path


def contents(root):
    return [base64.b64decode(json.loads(p.read_text())['content']['data'])
            for p in (root / '.lumos/evidence_archive/deleted_content').glob('*.json')]


def test_repeated_patch_keeps_target_and_previous_backup_bytes(workspace):
    target = workspace / 'a.txt'
    target.write_bytes(b'first\r\n')
    (workspace / 'a.txt.bak').write_bytes(b'older\r\n')
    for body in ('second', 'third'):
        assert executor.run({'instruction': f'TARGET:a.txt\n{body}'})['execution_result'] == 'patch_applied'
    assert b'first\r\n' in contents(workspace)
    assert b'older\r\n' in contents(workspace)
    assert b'second' in contents(workspace)
    assert target.read_text() == 'third'


def test_rollback_archives_replaced_target(workspace):
    (workspace / 'a.txt').write_bytes(b'latest\r\n')
    (workspace / 'a.txt.bak').write_text('previous')
    assert executor.run({'instruction': 'TARGET:a.txt\nROLLBACK'})['execution_result'] == 'rollback_applied'
    assert b'latest\r\n' in contents(workspace)
    assert (workspace / 'a.txt').read_text() == 'previous'


def test_archive_failure_prevents_target_and_backup_changes(workspace, monkeypatch):
    import core.evidence_settings as settings
    (workspace / 'a.txt').write_bytes(b'first')
    (workspace / 'a.txt.bak').write_bytes(b'older')
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')
    monkeypatch.setattr(settings, '_save', fail)
    with pytest.raises(OSError, match='archive unavailable'):
        executor.run({'instruction': 'TARGET:a.txt\nnew'})
    assert (workspace / 'a.txt').read_bytes() == b'first'
    assert (workspace / 'a.txt.bak').read_bytes() == b'older'


@pytest.mark.parametrize('prefix', ['TARGETS:', 'TARGET:'])
def test_multi_rollback_keeps_intermediate_version(workspace, prefix):
    (workspace / 'a.txt').write_text('first')
    result = executor.run({'instruction': f'{prefix}a.txt,missing.txt\nintermediate'})
    assert result['execution_result'] == 'rolled_back'
    assert (workspace / 'a.txt').read_text() == 'first'
    assert b'intermediate' in contents(workspace)


def test_customer_capture_off_keeps_mandatory_audit(workspace, monkeypatch):
    from core.evidence_settings import set_capture
    monkeypatch.setenv('LUMOS_DEPLOYMENT_PROFILE', 'customer')
    set_capture(workspace / '.lumos', False)
    (workspace / 'a.txt').write_text('first')
    executor.run({'instruction': 'TARGET:a.txt\nsecond'})
    assert not contents(workspace)
    assert list((workspace / '.lumos/evidence_archive/removal_evidence').glob('*.json'))


def test_multi_failure_does_not_restore_outside_root(workspace, monkeypatch):
    outside = workspace.parent / (workspace.name + '-outside.txt')
    outside.write_text('outside')
    (workspace / 'a.txt').write_text('first')
    writes = []
    original = executor._retained_write
    def track(path, text, **kwargs):
        writes.append(path)
        return original(path, text, **kwargs)
    monkeypatch.setattr(executor, '_retained_write', track)
    result = executor.run({'instruction': f'TARGETS:a.txt,../{outside.name}\nnew'})
    assert result['execution_result'] == 'rolled_back'
    assert outside not in writes
    assert outside.read_text() == 'outside'
