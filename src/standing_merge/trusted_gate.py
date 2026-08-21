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


def _arg(argv: list[str], name: str) -> str:
    """Minimal, flag-injection-safe argument reader.

    Deliberately not argparse: this module is invoked by CI and must never be
    steerable by anything that looks like a flag but is not one of these three.
    """
    token = f"--{name}"
    for index, item in enumerate(argv):
        if item == token and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith(f"{token}="):
            return item.split("=", 1)[1]
    return ""


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for CI.

    Fail-closed by construction: any missing argument, any missing trusted
    blob, and any extraction failure returns a non-zero exit. There is no
    code path that returns 0 without a materialized classifier on disk.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = _arg(argv, "repo") or "."
    base_sha = _arg(argv, "base-sha")
    dest = _arg(argv, "dest")
    if not base_sha or not dest:
        sys.stderr.write(
            "usage: python -m standing_merge.trusted_gate "
            "--repo DIR --base-sha SHA --dest DIR\n"
        )
        return gate_exit_for_missing_base()
    try:
        trusted_src = materialize_trusted_classifier(
            Path(repo), base_sha, Path(dest)
        )
    except TrustedClassifierMissing as exc:
        sys.stderr.write(f"::error::{exc}\n")
        sys.stderr.write(
            "::error::Fail-closed: refusing to grade this PR with its own code.\n"
        )
        return gate_exit_for_missing_base()
    except (subprocess.CalledProcessError, OSError) as exc:
        sys.stderr.write(f"::error::trusted classifier extraction failed: {exc}\n")
        return gate_exit_for_missing_base()
    # Never report success without the artefacts actually present.
    for blob in REQUIRED_BLOBS:
        if not (Path(dest) / blob).is_file():
            sys.stderr.write(f"::error::extracted tree is missing {blob}\n")
            return gate_exit_for_missing_base()
    sys.stdout.write(f"{trusted_src}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
