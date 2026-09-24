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
    def different_device(*a, **k):
        raise OSError(errno.EXDEV, 'different device')
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
    def different_device(*a, **k):
        raise OSError(errno.EXDEV, 'different device')
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
