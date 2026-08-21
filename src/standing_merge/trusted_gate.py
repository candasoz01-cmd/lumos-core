"""Materialize the standing-class classifier from a trusted base SHA.

The PR worktree is never the trust root. CI extracts ``src/standing_merge``
from ``github.event.pull_request.base.sha`` into a separate directory and
runs that copy. If the blobs are missing on the base SHA, the gate
fail-closes with exit 2 — no fallback to the PR tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REQUIRED_BLOBS = (
    "src/standing_merge/__init__.py",
    "src/standing_merge/classify.py",
    "src/standing_merge/excluded_paths.json",
)


class TrustedClassifierMissing(RuntimeError):
    """Base SHA does not contain the classifier; fail-closed."""


def blob_exists(repo: Path, sha: str, path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{sha}:{path}"],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def materialize_trusted_classifier(repo: Path, base_sha: str, dest: Path) -> Path:
    missing = [path for path in REQUIRED_BLOBS if not blob_exists(repo, base_sha, path)]
    if missing:
        raise TrustedClassifierMissing(
            f"trusted classifier missing at {base_sha}: {', '.join(missing)}"
        )
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", base_sha, "src/standing_merge"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return dest / "src"


def write_nul_paths(path: Path, names: list[str]) -> None:
    encoded = [name.encode("utf-8", errors="surrogateescape") for name in names]
    data = b"\0".join(encoded)
    if encoded:
        data += b"\0"
    path.write_bytes(data)


def run_trusted_classify(
    trusted_src: Path,
    paths_nul: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(trusted_src.resolve())
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "standing_merge.classify",
            "--paths-nul",
            str(paths_nul.resolve()),
            "--",
        ],
        cwd=str(trusted_src.resolve().parent),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def gate_exit_for_missing_base() -> int:
    return 2
