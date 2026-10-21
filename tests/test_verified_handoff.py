import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('handoff', Path(__file__).parents[1] / 'scripts/verified_handoff.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


def run(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    run(repo, 'init')
    run(repo, 'config', 'user.name', 'Test')
    run(repo, 'config', 'user.email', 'test@example.invalid')
    (repo / 'file').write_text('original\n')
    run(repo, 'add', '.')
    run(repo, 'commit', '-m', 'initial')
    return repo


def delivered(repo, tmp_path):
    package, archive = tmp_path / 'package', tmp_path / 'archive'
    handoff.pack(repo, package)
    handoff.receive(package, archive)
    return package, archive


def test_restore_without_original_repo(repo, tmp_path):
    package, archive = delivered(repo, tmp_path)
    repo.rename(tmp_path / 'original-unavailable')
    package.rename(tmp_path / 'sender-unavailable')
    assert run(archive / 'restored.git', 'show', 'HEAD:file') == b'original\n'
    assert handoff.digest(archive / 'source.bundle') == json.loads((archive / 'receipt.json').read_text())['bundle_sha256']


def history(repo):
    (repo / 'file').write_text('second\n')
    run(repo, 'commit', '-am', 'second')
    return run(repo, 'rev-parse', 'HEAD').decode().strip()


def test_shallow_clone_blocks_before_any_package_output(repo, tmp_path):
    history(repo)
    shallow = tmp_path / 'shallow'
    run(tmp_path, 'clone', '--depth', '1', repo.as_uri(), str(shallow))
    package = tmp_path / 'package'
    with pytest.raises(ValueError, match='SHALLOW'):
        handoff.pack(shallow, package)
    assert not package.exists()
    cli = subprocess.run([sys.executable, spec.origin, 'pack', '--repo', str(shallow), '--out', str(package)],
                         capture_output=True, text=True)
    assert cli.returncode == 2
    assert cli.stderr.startswith('DELIVERY_BLOCKED: SHALLOW')
    assert not package.exists()


def test_full_history_clone_is_delivered(repo, tmp_path):
    head = history(repo)
    full = tmp_path / 'full'
    run(tmp_path, 'clone', repo.as_uri(), str(full))
    _, archive = delivered(full, tmp_path)
    assert handoff.check(full, archive) == dict(status='DELIVERY_VERIFIED', head=head, archive=str(archive))
    assert run(archive / 'restored.git', 'rev-list', '--count', 'HEAD') == b'2\n'


def test_dirty_and_untracked_block(repo, tmp_path):
    (repo / 'untracked').write_text('must not lose this')
    with pytest.raises(ValueError, match='DIRTY'):
        handoff.pack(repo, tmp_path / 'package')


def test_corrupt_transfer_has_no_receipt(repo, tmp_path):
    package = tmp_path / 'package'
    handoff.pack(repo, package)
    with (package / 'source.bundle').open('ab') as f:
        f.write(b'corruption')
    with pytest.raises(ValueError, match='HASH_MISMATCH'):
        handoff.receive(package, tmp_path / 'archive')
    assert not (tmp_path / 'archive/receipt.json').exists()


def test_stale_receipt_blocks(repo, tmp_path):
    _, archive = delivered(repo, tmp_path)
    assert handoff.check(repo, archive)['status'] == 'DELIVERY_VERIFIED'
    (repo / 'file').write_text('changed')
    run(repo, 'commit', '-am', 'next')
    with pytest.raises(ValueError, match='STALE'):
        handoff.check(repo, archive)


def test_missing_receipt_and_overwrite_block(repo, tmp_path):
    package = tmp_path / 'package'
    handoff.pack(repo, package)
    with pytest.raises(FileNotFoundError):
        handoff.check(repo, package)
    with pytest.raises(FileExistsError):
        handoff.pack(repo, package)


def test_changed_manifest_blocks(repo, tmp_path):
    _, archive = delivered(repo, tmp_path)
    with (archive / 'manifest.json').open('a') as f:
        f.write(' ')
    with pytest.raises(ValueError, match='MANIFEST_CHANGED'):
        handoff.check(repo, archive)


@pytest.mark.parametrize('variable', ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_CONFIG_COUNT'])
def test_ambient_git_environment_cannot_redirect_handoff(repo, tmp_path, monkeypatch, variable):
    expected = run(repo, 'rev-parse', 'HEAD').decode().strip()
    monkeypatch.setenv(variable, '1' if variable == 'GIT_CONFIG_COUNT' else str(tmp_path / 'not-the-source'))
    package, archive = delivered(repo, tmp_path)
    assert json.loads((package / 'manifest.json').read_text())['head'] == expected
    assert handoff.check(repo, archive)['head'] == expected
