"""Commit-bound claim-guard: later claims cannot authorize earlier commits."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lumos_board.claim_cli import main as claim_cli_main
from lumos_board.write_attestation import (
    ATTESTATION_TRAILER,
    REASON_MISSING,
    REASON_OK,
    REASON_REUSED,
    REASON_TIME,
    REASON_UNCONFIGURED,
    ClaimGuard,
)
from lumos_board.claim_guard_trust import (
    TrustedClaimGuardMissing,
    gate_exit_for_missing_base,
    materialize_trusted_claim_guard,
)
from lumos_board.task_claim import ClaimError, TaskClaimStore
from lumos_board.write_gate import WriteGate

SECRET = "b" * 32


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    merged = os.environ.copy()
    merged.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
        }
    )
    if env:
        merged.update(env)
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=merged,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "keep.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "keep.txt")
    _git(repo, "commit", "-m", "base")
    return repo


def _commit(repo: Path, rel: str, body: str, message: str, *, when: str | None = None) -> str:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    _git(repo, "add", rel)
    env = {}
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    _git(repo, "commit", "-m", message, env=env)
    return _git(repo, "rev-parse", "HEAD")


def _claim_and_token(store_dir: Path, *, owner: str, scope: str) -> tuple[str, str, str]:
    claims = TaskClaimStore(store_dir)
    result = claims.claim(
        task_id="KA-003-CLAIM-GUARD",
        repo="lumos-core",
        branch="x",
        worktree="/w",
        owner=owner,
        scopes=[scope],
    )
    assert result.claim is not None
    token = WriteGate(claims, secret=SECRET).issue(result.claim)
    return result.claim.claim_id, token, result.claim.task_id


def test_missing_secret_fail_closed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    verdict = ClaimGuard(secret=None).verify_range(repo, base=head, head=head)
    assert verdict.allowed is False
    assert verdict.reason == REASON_UNCONFIGURED


def test_unattested_commit_fails_and_later_attested_commit_does_not_save_it(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "src/a.py", "a\n", "unauthorized")
    store = tmp_path / "board"
    claim_id, token, task_id = _claim_and_token(store, owner="cursor", scope="src")
    gate = WriteGate(TaskClaimStore(store), secret=SECRET)
    guard = ClaimGuard(secret=SECRET)
    parent = _git(repo, "rev-parse", "HEAD")
    attestation = guard.attest(
        write_gate=gate,
        token=token,
        owner="cursor",
        paths=["src/b.py"],
        parent_sha=parent,
        claim_id=claim_id,
        task_id=task_id,
        scopes=["src"],
    )
    _commit(
        repo,
        "src/b.py",
        "b\n",
        f"authorized\n\n{ATTESTATION_TRAILER}: {attestation}\n",
    )
    head = _git(repo, "rev-parse", "HEAD")
    verdict = guard.verify_range(repo, base=base, head=head)
    assert verdict.allowed is False
    assert verdict.reason == REASON_MISSING
    assert verdict.commits[0].allowed is False
    assert verdict.commits[1].allowed is True


def test_attested_commit_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    store = tmp_path / "board"
    claim_id, token, task_id = _claim_and_token(store, owner="cursor", scope="src")
    parent = _git(repo, "rev-parse", "HEAD")
    guard = ClaimGuard(secret=SECRET)
    attestation = guard.attest(
        write_gate=WriteGate(TaskClaimStore(store), secret=SECRET),
        token=token,
        owner="cursor",
        paths=["src/ok.py"],
        parent_sha=parent,
        claim_id=claim_id,
        task_id=task_id,
        scopes=["src"],
    )
    _commit(repo, "src/ok.py", "ok\n", f"ok\n\n{ATTESTATION_TRAILER}: {attestation}\n")
    head = _git(repo, "rev-parse", "HEAD")
    verdict = guard.verify_range(repo, base=base, head=head)
    assert verdict.allowed is True
    assert verdict.reason == REASON_OK


def test_issued_after_commit_is_rejected(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    store = tmp_path / "board"
    claim_id, token, task_id = _claim_and_token(store, owner="cursor", scope="src")
    parent = _git(repo, "rev-parse", "HEAD")
    future = datetime.now(timezone.utc) + timedelta(days=1)
    attestation = ClaimGuard(secret=SECRET).attest(
        write_gate=WriteGate(TaskClaimStore(store), secret=SECRET),
        token=token,
        owner="cursor",
        paths=["src/late.py"],
        parent_sha=parent,
        claim_id=claim_id,
        task_id=task_id,
        scopes=["src"],
        issued_at=future,
    )
    past = "2020-01-01T00:00:00+00:00"
    _commit(
        repo,
        "src/late.py",
        "late\n",
        f"late\n\n{ATTESTATION_TRAILER}: {attestation}\n",
        when=past,
    )
    head = _git(repo, "rev-parse", "HEAD")
    verdict = ClaimGuard(secret=SECRET).verify_range(repo, base=base, head=head)
    assert verdict.allowed is False
    assert verdict.reason == REASON_TIME


def test_write_token_cannot_attest_twice(tmp_path: Path) -> None:
    store = tmp_path / "board"
    claim_id, token, task_id = _claim_and_token(store, owner="cursor", scope="src")
    gate = WriteGate(TaskClaimStore(store), secret=SECRET)
    guard = ClaimGuard(secret=SECRET)
    first = guard.attest(
        write_gate=gate,
        token=token,
        owner="cursor",
        paths=["src/a.py"],
        parent_sha="0" * 40,
        claim_id=claim_id,
        task_id=task_id,
        scopes=["src"],
    )
    assert first
    try:
        guard.attest(
            write_gate=gate,
            token=token,
            owner="cursor",
            paths=["src/b.py"],
            parent_sha="0" * 40,
            claim_id=claim_id,
            task_id=task_id,
            scopes=["src"],
        )
    except ClaimError as exc:
        assert "WRITE_TOKEN_CONSUMED" in str(exc)
    else:
        raise AssertionError("reused write token must not mint a second attestation")


def test_copied_trailer_is_rejected_as_reuse(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    store = tmp_path / "board"
    claim_id, token, task_id = _claim_and_token(store, owner="cursor", scope="src")
    parent = _git(repo, "rev-parse", "HEAD")
    guard = ClaimGuard(secret=SECRET)
    attestation = guard.attest(
        write_gate=WriteGate(TaskClaimStore(store), secret=SECRET),
        token=token,
        owner="cursor",
        paths=["src/ok.py"],
        parent_sha=parent,
        claim_id=claim_id,
        task_id=task_id,
        scopes=["src"],
    )
    _commit(repo, "src/ok.py", "ok\n", f"ok\n\n{ATTESTATION_TRAILER}: {attestation}\n")
    _commit(repo, "src/copy.py", "copy\n", f"copy\n\n{ATTESTATION_TRAILER}: {attestation}\n")
    head = _git(repo, "rev-parse", "HEAD")
    verdict = guard.verify_range(repo, base=base, head=head)
    assert verdict.allowed is False
    assert verdict.reason == REASON_REUSED
    assert verdict.commits[0].allowed is True
    assert verdict.commits[1].reason == REASON_REUSED


def test_workflow_is_pull_request_target_and_secret_stays_on_trusted_step() -> None:
    import re

    text = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "claim-guard.yml"
    ).read_text(encoding="utf-8")
    assert "python -m lumos_board.claim_guard" in text
    assert "lumos_board.write_attestation" in text
    assert "lumos_board.claim_guard_trust" in text
    assert text.count("secrets.LUMOS_WRITE_GATE_SECRET") == 1
    secret_at = text.index("secrets.LUMOS_WRITE_GATE_SECRET")
    hmac_job = text.index("write-attestation:")
    board_job = text.index("claim-guard:")
    assert board_job < hmac_job < secret_at
    assert "pull_request_target" in text
    board_check = text.index("Check PR writes against central claims")
    assert "LUMOS_WRITE_GATE_SECRET" not in text[board_check:hmac_job]


def test_board_trailers_do_not_satisfy_hmac(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _commit(
        repo,
        "src/x.py",
        "x\n",
        "board only\n\nLumos-Claim: 00000000-0000-4000-8000-000000000000\nLumos-Agent: cursor\n",
    )
    head = _git(repo, "rev-parse", "HEAD")
    verdict = ClaimGuard(secret=SECRET).verify_range(repo, base=base, head=head)
    assert verdict.allowed is False
    assert verdict.reason == REASON_MISSING


def test_missing_claim_guard_on_base_is_fail_closed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    try:
        materialize_trusted_claim_guard(repo, base, tmp_path / "trusted")
    except TrustedClaimGuardMissing:
        pass
    else:
        raise AssertionError("missing base verifier must fail closed")
    assert gate_exit_for_missing_base() == 2


def test_trojaned_pr_claim_guard_is_not_materialized(tmp_path: Path) -> None:
    import shutil

    repo = _init_repo(tmp_path)
    src = Path(__file__).resolve().parents[1] / "src" / "lumos_board"
    dest = repo / "src" / "lumos_board"
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
    _git(repo, "add", "src/lumos_board")
    _git(repo, "commit", "-m", "trusted verifier")
    base = _git(repo, "rev-parse", "HEAD")
    (dest / "write_attestation.py").write_text(
        "def verify_range(*args, **kwargs):\n    raise SystemExit('pr tree ran')\n",
        encoding="utf-8",
    )
    _git(repo, "add", "src/lumos_board/write_attestation.py")
    _git(repo, "commit", "-m", "trojan")
    extracted = materialize_trusted_claim_guard(repo, base, tmp_path / "trusted")
    trusted = (extracted / "lumos_board" / "write_attestation.py").read_text(encoding="utf-8")
    assert "pr tree ran" not in trusted
    assert "class ClaimGuard" in trusted


def test_cli_verify_exit_code(tmp_path: Path, monkeypatch: object) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "src/x.py", "x\n", "no trailer")
    head = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)
    monkeypatch.setenv("LUMOS_BOARD_DIR", str(tmp_path / "board"))
    code = claim_cli_main(
        ["write-attest", "verify", "--repo", str(repo), "--base", base, "--head", head]
    )
    assert code == 2
