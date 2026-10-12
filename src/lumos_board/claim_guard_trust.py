"""Materialize claim-guard from a trusted PR base SHA.

The PR worktree is never the trust root. CI extracts ``src/lumos_board``
from ``github.event.pull_request.base.sha`` into a separate directory and
runs that copy. The signing secret is bound only to that trusted copy.

If ``claim_guard.py`` is missing on the base SHA, the gate fail-closes with
exit 2 — no fallback to the PR tree. The introducing PR therefore cannot
prove itself; that is bootstrap, not a bypass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REQUIRED_BLOBS = (
    "src/lumos_board/__init__.py",
    "src/lumos_board/claim_guard.py",
    "src/lumos_board/write_attestation.py",
    "src/lumos_board/write_gate.py",
    "src/lumos_board/task_claim.py",
    "src/lumos_board/central_store.py",
)


class TrustedClaimGuardMissing(RuntimeError):
    """Base SHA does not contain claim-guard; fail-closed."""


def blob_exists(repo: Path, sha: str, path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{sha}:{path}"],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def materialize_trusted_claim_guard(repo: Path, base_sha: str, dest: Path) -> Path:
    missing = [path for path in REQUIRED_BLOBS if not blob_exists(repo, base_sha, path)]
    if missing:
        raise TrustedClaimGuardMissing(
            f"trusted claim-guard missing at {base_sha}: {', '.join(missing)}"
        )
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", base_sha, "src/lumos_board"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return dest / "src"


def gate_exit_for_missing_base() -> int:
    return 2


def _arg(argv: list[str], name: str) -> str:
    token = f"--{name}"
    for index, item in enumerate(argv):
        if item == token and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith(f"{token}="):
            return item.split("=", 1)[1]
    return ""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = _arg(argv, "repo") or "."
    base_sha = _arg(argv, "base-sha")
    dest = _arg(argv, "dest")
    if not base_sha or not dest:
        sys.stderr.write(
            "usage: python -m lumos_board.claim_guard_trust "
            "--repo DIR --base-sha SHA --dest DIR\n"
        )
        return gate_exit_for_missing_base()
    try:
        trusted_src = materialize_trusted_claim_guard(Path(repo), base_sha, Path(dest))
    except TrustedClaimGuardMissing as exc:
        sys.stderr.write(f"::error::{exc}\n")
        sys.stderr.write(
            "::error::Fail-closed: refusing to grade this PR with its own code.\n"
        )
        return gate_exit_for_missing_base()
    except (subprocess.CalledProcessError, OSError) as exc:
        sys.stderr.write(f"::error::trusted claim-guard extraction failed: {exc}\n")
        return gate_exit_for_missing_base()
    for blob in REQUIRED_BLOBS:
        if not (Path(dest) / blob).is_file():
            sys.stderr.write(f"::error::extracted tree is missing {blob}\n")
            return gate_exit_for_missing_base()
    sys.stdout.write(f"{trusted_src}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
