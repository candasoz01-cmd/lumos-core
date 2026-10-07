#!/usr/bin/env python3
"""Offline handoff: self-contained bundle + receiver restore proof. No push/delete.

pack --repo REPO --out NEW_DIRECTORY
receive --package DIRECTORY --out NEW_ARCHIVE_DIRECTORY
check --repo REPO --archive ARCHIVE_DIRECTORY

A local receipt is evidence of restore, not a signature or provider retention promise.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lumos_board.evidence_policy import EvidencePolicy  # noqa: E402


def git_environment():
    # A handoff must describe the requested repository, never an ambient one.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    return env


def git(repo, *args):
    return subprocess.check_output(
        ['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args],
        stderr=subprocess.PIPE, env=git_environment(),
    ).decode().strip()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def record(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def now():
    return datetime.now(timezone.utc).isoformat()


def identity(repo):
    if git(repo, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('DIRTY: commit edilmemiş veya izlenmeyen dosyalar teslim dışı kalamaz')
    return git(repo, 'rev-parse', 'HEAD'), git(repo, 'rev-parse', 'HEAD^{tree}')


def newdir(path):
    path = Path(path).resolve()
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    return path


def pack(repo, out):
    repo = Path(repo).resolve()
    head, tree = identity(repo)
    # A shallow clone bundles commits whose parents it lacks; stop before any output.
    if git(repo, 'rev-parse', '--is-shallow-repository') != 'false':
        raise ValueError('SHALLOW: tam geçmiş olmadan paket üretilmez')
    out = Path(out).resolve()
    if out.is_relative_to(repo):
        raise ValueError('Paket çalışma ağacının dışında olmalı')
    out = newdir(out)
    git(repo, 'bundle', 'create', str(out / 'source.bundle'), 'HEAD')
    # Guard concurrent changes during capture.
    if identity(repo) != (head, tree):
        raise ValueError('SOURCE_CHANGED: manifest oluşturulmadı')
    data = dict(version=1, head=head, tree=tree, bundle_sha256=digest(out / 'source.bundle'),
                created_at=now(), source_host=platform.node(), source_repo=str(repo),
                status='PACKAGED_NOT_DELIVERED',
                retention=EvidencePolicy().record_terms(datetime.now(timezone.utc),
                    kind='audit', severity='unknown'))
    record(out / 'manifest.json', data)
    return data


def restore(package, target):
    manifest = json.loads((package / 'manifest.json').read_text())
    if manifest.get('version') != 1:
        raise ValueError('Desteklenmeyen manifest')
    bundle = package / 'source.bundle'
    if digest(bundle) != manifest['bundle_sha256']:
        raise ValueError('HASH_MISMATCH')
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--bare',
                    str(bundle), str(target)], check=True, capture_output=True, env=git_environment())
    git(target, 'fsck', '--full', '--strict')
    if (git(target, 'rev-parse', 'HEAD'), git(target, 'rev-parse', 'HEAD^{tree}')) != (
            manifest['head'], manifest['tree']):
        raise ValueError('RESTORE_MISMATCH')
    return manifest


def receive(package, out):
    import shutil
    package = Path(package).resolve()
    out = newdir(out)
    # Keep received bytes, not just a path to the producer's copy.
    for name in ('source.bundle', 'manifest.json'):
        with (package / name).open('rb') as src, (out / name).open('xb') as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
    manifest = restore(out, out / 'restored.git')
    receipt = dict(version=1, status='RESTORE_VERIFIED', verified_at=now(),
                   receiver_host=platform.node(), archive=str(out),
                   manifest_sha256=digest(out / 'manifest.json'),
                   head=manifest['head'], tree=manifest['tree'],
                   bundle_sha256=manifest['bundle_sha256'],
                   retention=EvidencePolicy().record_terms(datetime.now(timezone.utc),
                       kind='audit', severity='unknown'))
    record(out / 'receipt.json', receipt)
    return receipt


def check(repo, archive):
    archive = Path(archive).resolve()
    receipt = json.loads((archive / 'receipt.json').read_text())
    manifest = json.loads((archive / 'manifest.json').read_text())
    head, tree = identity(repo)
    if receipt.get('status') != 'RESTORE_VERIFIED' or receipt.get('version') != 1:
        raise ValueError('VERIFIED_RECEIPT_REQUIRED')
    if receipt['manifest_sha256'] != digest(archive / 'manifest.json'):
        raise ValueError('MANIFEST_CHANGED')
    for key, value in [('head', head), ('tree', tree),
                       ('bundle_sha256', digest(archive / 'source.bundle'))]:
        if receipt[key] != value or manifest[key] != value:
            raise ValueError('STALE_OR_CORRUPT_RECEIPT: ' + key)
    git(archive / 'restored.git', 'fsck', '--full', '--strict')
    if git(archive / 'restored.git', 'rev-parse', 'HEAD') != head:
        raise ValueError('RESTORED_HEAD_CHANGED')
    return dict(status='DELIVERY_VERIFIED', head=head, archive=str(archive))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('pack')
    p.add_argument('--repo', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('receive')
    p.add_argument('--package', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('check')
    p.add_argument('--repo', required=True)
    p.add_argument('--archive', required=True)
    args = vars(parser.parse_args())
    command = args.pop('command')
    try:
        print(json.dumps(globals()[command](**args), ensure_ascii=False))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print('DELIVERY_BLOCKED: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
