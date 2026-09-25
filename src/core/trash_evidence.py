"""Provenance for the existing trash move; no scanner, purge or duplicate store."""
import errno
import hashlib
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from core.evidence_settings import CompletionEvidenceError, _save
from lumos_board.evidence_policy import EvidencePolicy


def manifest(source):
    source = Path(source)
    entries = [source]
    if source.is_dir() and not source.is_symlink():
        entries += sorted(source.rglob('*'))
    result = []
    for entry in entries:
        before = entry.lstat()
        row = {'path': '.' if entry == source else entry.relative_to(source).as_posix()}
        if stat.S_ISLNK(before.st_mode):
            row.update(kind='symlink', target=os.readlink(entry))
        elif stat.S_ISDIR(before.st_mode):
            row.update(kind='directory')
        elif stat.S_ISREG(before.st_mode):
            digest = hashlib.sha256()
            with entry.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            row.update(kind='file', size=before.st_size, sha256=digest.hexdigest())
        else:
            raise OSError('Unsupported trash entry type')
        after = entry.lstat()
        if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
                after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode):
            raise OSError('Trash source changed during capture')
        result.append(row)
    return result


def move_with_evidence(base, source, destination):
    import shutil

    source, destination = Path(source), Path(destination)
    if destination.is_relative_to(source):
        raise OSError('Trash destination cannot be inside its source')
    snapshot = manifest(source)
    transaction = {
        'schema': 'lumos.wall.trash_move.v1', 'id': str(uuid4()),
        'source': str(source), 'destination': str(destination), 'entries': snapshot,
        'retention': EvidencePolicy().record_terms(datetime.now(timezone.utc),
                                                   kind='audit', severity='unknown'),
    }
    staging = Path(base) / 'evidence_archive' / 'trash_staging' / transaction['id'] / source.name
    transaction['staging'] = str(staging)
    # Persist intent before the existing mover can remove anything.
    _save(base, 'trash_moves', {**transaction, 'phase': 'before'})
    copied = False
    captured = destination
    try:
        os.rename(source, destination)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        # Across filesystems, keep the source until a durable copy is verified.
        staging.parent.mkdir(parents=True, mode=0o700)
        captured = staging
        try:
            if source.is_dir() and not source.is_symlink():
                shutil.copytree(source, captured, symlinks=True)
            else:
                shutil.copy2(source, captured, follow_symlinks=False)
        except OSError:
            _save(base, 'trash_moves', {**transaction, 'phase': 'copy_failed'})
            raise
        copied = True
    try:
        if manifest(captured) != snapshot or (copied and manifest(source) != snapshot):
            _save(base, 'trash_moves', {**transaction, 'phase': 'verification_failed'})
            raise OSError('Trash destination content does not match captured source')
        if copied:
            for row in snapshot:
                target = captured if row['path'] == '.' else captured / row['path']
                if row['kind'] == 'file':
                    with target.open('rb') as stream:
                        os.fsync(stream.fileno())
            for row in reversed(snapshot):
                if row['kind'] == 'directory':
                    target = captured if row['path'] == '.' else captured / row['path']
                    fd = os.open(target, os.O_RDONLY)
                    try:
                        os.fsync(fd)
                    finally:
                        os.close(fd)
            fd = os.open(captured.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            if manifest(source) != snapshot:
                _save(base, 'trash_moves', {**transaction, 'phase': 'source_changed'})
                raise OSError('Trash source changed before removal')
            # Only verified, durable content may appear as a completed trash item.
            if os.path.lexists(destination):
                raise FileExistsError(f'Trash target already exists: {destination}')
            os.rename(captured, destination)
            fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            if source.is_dir() and not source.is_symlink():
                shutil.rmtree(source)
            else:
                source.unlink()
        for parent in {source.parent, destination.parent}:
            fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        _save(base, 'trash_moves', {**transaction, 'phase': 'move_verified'})
    except OSError as exc:
        if not copied or not os.path.lexists(source):
            error = CompletionEvidenceError(
                f'Trash move applied; completion verification unavailable; '
                f'do not blindly retry; destination: {destination}'
            )
            error.destination = destination
            error.transaction_id = transaction['id']
            raise error from exc
        raise
    return destination
