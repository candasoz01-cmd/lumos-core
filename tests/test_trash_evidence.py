import json
import shutil
from pathlib import Path

import pytest

from core.workspace_contract import move_to_trash
from core.trash_evidence import manifest


def test_directory_content_and_original_context_can_be_recovered(tmp_path):
    source = tmp_path / 'original' / 'screenshots'
    source.mkdir(parents=True)
    (source / 'image.png').write_bytes(bytes(range(256)))
    (source / 'notes.txt').write_text('Original context\n')
    (source / 'nested').mkdir()
    (source / 'nested/link').symlink_to('../notes.txt')
    before = manifest(source)
    base = tmp_path / 'workspace'
    destination = move_to_trash(base, source)
    assert not source.exists()
    records = [json.loads(p.read_text()) for p in (base / 'evidence_archive/trash_moves').glob('*.json')]
    assert {r['phase'] for r in records} == {'before', 'move_verified'}
    assert len({r['id'] for r in records}) == 1
    assert all(r['source'] == str(source.resolve()) and r['entries'] == before for r in records)
    restored = tmp_path / 'restore'
    shutil.copytree(destination, restored, symlinks=True)
    assert manifest(restored) == before
    assert (restored / 'image.png').read_bytes() == bytes(range(256))


def test_archive_write_failure_leaves_source_in_place(tmp_path, monkeypatch):
    import core.trash_evidence as te
    source = tmp_path / 'source.txt'
    source.write_text('Do not lose this')
    def fail(*a, **k):
        raise OSError('archive unavailable')
    monkeypatch.setattr(te, '_save', fail)
    with pytest.raises(OSError, match='archive unavailable'):
        move_to_trash(tmp_path / 'workspace', source)
    assert source.read_text() == 'Do not lose this'


def test_corrupt_move_is_never_reported_verified(tmp_path, monkeypatch):
    source = tmp_path / 'source.txt'
    source.write_text('original')
    import errno
    import core.trash_evidence as te
    rename = te.os.rename
    def different_device(src, dst, **kwargs):
        if Path(src).parent == tmp_path:
            raise OSError(errno.EXDEV, 'different device')
        return rename(src, dst, **kwargs)
    def corrupt(src, dst, **kwargs):
        Path(dst).write_text('changed')
    monkeypatch.setattr(te.os, 'rename', different_device)
    monkeypatch.setattr(shutil, 'copy2', corrupt)
    base = tmp_path / 'workspace'
    with pytest.raises(OSError, match='does not match'):
        move_to_trash(base, source)
    records = [json.loads(p.read_text()) for p in (base / 'evidence_archive/trash_moves').glob('*.json')]
    assert {r['phase'] for r in records} == {'before', 'verification_failed'}
    assert source.read_text() == 'original'


def test_sandbox_move_evidence_stays_in_sandbox(tmp_path):
    base = tmp_path / 'workspace'
    source = tmp_path / 'source.txt'
    source.write_text('sandbox')
    move_to_trash(base, source, is_sandbox_mode=True)
    assert not (base / 'evidence_archive').exists()
    assert len(list((base / 'sandbox/evidence_archive/trash_moves').glob('*.json'))) == 2



def test_cross_device_copy_verified_before_source_removal(tmp_path, monkeypatch):
    import errno
    import core.trash_evidence as te
    rename = te.os.rename
    def different_device(src, dst, **kwargs):
        if Path(src).parent == tmp_path:
            raise OSError(errno.EXDEV, 'different device')
        return rename(src, dst, **kwargs)
    monkeypatch.setattr(te.os, 'rename', different_device)
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'original.bin').write_bytes(bytes(range(256)))
    before = manifest(source)
    destination = move_to_trash(tmp_path / 'workspace', source)
    assert not source.exists()
    assert manifest(destination) == before


@pytest.mark.parametrize('relative', ['tasks.json', 'evidence_archive/retained.json'])
def test_sandbox_cannot_move_live_core_source(tmp_path, relative):
    from core.workspace_contract import CoreWriteForbidden
    source = tmp_path / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('live content')
    with pytest.raises(CoreWriteForbidden):
        move_to_trash(tmp_path, source, is_sandbox_mode=True)
    assert source.read_text() == 'live content'


@pytest.mark.parametrize('failure', ['corrupt', 'exception'])
def test_failed_copy_preserved_outside_trash_and_retry_succeeds(tmp_path, monkeypatch, failure):
    import errno
    import core.trash_evidence as te
    source = tmp_path / 'source.txt'
    source.write_text('original')
    rename, copy = te.os.rename, shutil.copy2
    def cross_device(src, dst, **kwargs):
        if Path(src) == source:
            raise OSError(errno.EXDEV, 'different device')
        return rename(src, dst, **kwargs)
    def failed_copy(src, dst, **kwargs):
        Path(dst).write_text('partial')
        if failure == 'exception':
            raise OSError('copy interrupted')
    monkeypatch.setattr(te.os, 'rename', cross_device)
    monkeypatch.setattr(shutil, 'copy2', failed_copy)
    base = tmp_path / 'workspace'
    with pytest.raises(OSError):
        move_to_trash(base, source)
    assert source.read_text() == 'original'
    assert not list((base / 'trash').iterdir())
    pending = list((base / 'evidence_archive/trash_staging').glob('*/source.txt'))
    assert len(pending) == 1 and pending[0].read_text() == 'partial'
    monkeypatch.setattr(shutil, 'copy2', copy)
    destination = move_to_trash(base, source)
    assert destination.read_text() == 'original'
    assert not source.exists()
    assert pending[0].read_text() == 'partial'


@pytest.mark.parametrize('failure', ['final_record', 'parent_fsync', 'verification'])
def test_rename_completion_failure_reports_applied_destination(tmp_path, monkeypatch, failure):
    import core.trash_evidence as te
    from core.evidence_settings import CompletionEvidenceError
    source = tmp_path / 'source.txt'
    source.write_bytes(b'original bytes')
    base = tmp_path / 'workspace'
    save, fsync, capture = te._save, te.os.fsync, te.manifest

    def failing_save(base, kind, record):
        if record['phase'] == 'move_verified':
            raise OSError('completion journal unavailable')
        return save(base, kind, record)

    def failing_fsync(fd):
        if not source.exists():
            raise OSError('parent fsync unavailable')
        return fsync(fd)

    def failing_capture(path):
        if Path(path) != source:
            raise OSError('verification unavailable')
        return capture(path)

    if failure == 'final_record':
        monkeypatch.setattr(te, '_save', failing_save)
    elif failure == 'parent_fsync':
        monkeypatch.setattr(te.os, 'fsync', failing_fsync)
    else:
        monkeypatch.setattr(te, 'manifest', failing_capture)
    with pytest.raises(CompletionEvidenceError, match='do not blindly retry') as result:
        move_to_trash(base, source)
    assert result.value.mutation_applied is True
    assert result.value.destination.read_bytes() == b'original bytes'
    assert not source.exists()
    intent = json.loads(next((base / 'evidence_archive/trash_moves').glob('*.json')).read_text())
    assert intent['id'] == result.value.transaction_id
    assert intent['destination'] == str(result.value.destination)


@pytest.mark.parametrize('failure', ['destination_fsync', 'source_unlink'])
def test_cross_device_published_destination_reports_partial_completion(tmp_path, monkeypatch, failure):
    import errno
    import core.trash_evidence as te
    from core.evidence_settings import CompletionEvidenceError
    source = tmp_path / 'source.txt'
    source.write_bytes(b'preserve both copies')
    base = tmp_path / 'workspace'
    destination = base / 'trash/source.txt'
    rename, fsync, unlink = te.os.rename, te.os.fsync, Path.unlink

    def cross_device(src, dst):
        if Path(src) == source:
            raise OSError(errno.EXDEV, 'cross device')
        return rename(src, dst)

    def fail_fsync(fd):
        if failure == 'destination_fsync' and destination.exists():
            raise OSError('destination parent fsync failed')
        return fsync(fd)

    def fail_unlink(path, *args, **kwargs):
        if failure == 'source_unlink' and path == source:
            raise OSError('source removal failed')
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(te.os, 'rename', cross_device)
    monkeypatch.setattr(te.os, 'fsync', fail_fsync)
    monkeypatch.setattr(Path, 'unlink', fail_unlink)
    with pytest.raises(CompletionEvidenceError, match='do not blindly retry') as error:
        move_to_trash(base, source)
    assert error.value.mutation_applied is True
    assert error.value.destination == destination
    assert destination.read_bytes() == source.read_bytes() == b'preserve both copies'
    records = [json.loads(p.read_text()) for p in (base / 'evidence_archive/trash_moves').glob('*.json')]
    assert all(r['id'] == error.value.transaction_id for r in records)
    assert not any(r['phase'] == 'move_verified' for r in records)
