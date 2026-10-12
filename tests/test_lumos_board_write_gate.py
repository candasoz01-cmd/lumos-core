"""KA-003 write gate: HMAC identity + ACTIVE claim before write."""

from __future__ import annotations

from pathlib import Path

from lumos_board.claim_cli import main as claim_cli_main
from lumos_board.task_claim import TaskClaimStore
from lumos_board.write_gate import (
    REASON_ALLOWED,
    REASON_IDENTITY,
    REASON_NO_CLAIM,
    REASON_NO_CREDENTIAL,
    REASON_SCOPE,
    REASON_UNCONFIGURED,
    REASON_UNAUTHORIZED,
    WriteGate,
)

SECRET = "a" * 32


def _claim(store: Path, *, task: str, owner: str, scope: str) -> dict[str, object]:
    import json
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = claim_cli_main(
            [
                "--store",
                str(store),
                "claim",
                "--task",
                task,
                "--repo",
                "lumos-core",
                "--branch",
                "cursor/ka-003-write-gate",
                "--worktree",
                "/workspace",
                "--owner",
                owner,
                "--scope",
                scope,
            ]
        )
    payload = json.loads(buf.getvalue())
    assert code == 0, payload
    return payload


def test_write_check_fail_closed_without_secret(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.delenv("LUMOS_WRITE_GATE_SECRET", raising=False)
    claims = TaskClaimStore(tmp_path)
    gate = WriteGate(claims, secret=None)
    decision = gate.check(token="x.y", owner="claude", paths=["src/lumos_board/write_gate.py"])
    assert decision.allowed is False
    assert decision.reason == REASON_UNCONFIGURED


def test_missing_token_is_denied_when_configured(tmp_path: Path) -> None:
    claims = TaskClaimStore(tmp_path)
    claim = claims.claim(
        task_id="KA-003-WRITE-GATE",
        repo="lumos-core",
        branch="x",
        worktree="/w",
        owner="claude",
        scopes=["src/lumos_board"],
    ).claim
    assert claim is not None
    gate = WriteGate(claims, secret=SECRET)
    gate.issue(claim)
    decision = gate.check(token=None, owner="claude", paths=["src/lumos_board/write_gate.py"])
    assert decision.allowed is False
    assert decision.reason == REASON_NO_CREDENTIAL


def test_forged_token_and_wrong_owner_are_denied(tmp_path: Path) -> None:
    claims = TaskClaimStore(tmp_path)
    claim = claims.claim(
        task_id="KA-003-WRITE-GATE",
        repo="lumos-core",
        branch="x",
        worktree="/w",
        owner="claude",
        scopes=["src/lumos_board"],
    ).claim
    assert claim is not None
    gate = WriteGate(claims, secret=SECRET)
    token = gate.issue(claim)
    assert gate.check(token="not-a-token", owner="claude", paths=["src/lumos_board/write_gate.py"]).reason == (
        REASON_UNAUTHORIZED
    )
    cursor = gate.check(token=token, owner="cursor", paths=["src/lumos_board/write_gate.py"])
    assert cursor.allowed is False
    assert cursor.reason == REASON_IDENTITY


def test_scope_outside_claim_is_denied(tmp_path: Path) -> None:
    claims = TaskClaimStore(tmp_path)
    claim = claims.claim(
        task_id="KA-003-WRITE-GATE",
        repo="lumos-core",
        branch="x",
        worktree="/w",
        owner="claude",
        scopes=["src/lumos_board"],
    ).claim
    assert claim is not None
    gate = WriteGate(claims, secret=SECRET)
    token = gate.issue(claim)
    decision = gate.check(token=token, owner="claude", paths=["docs/CONSTITUTION.md"])
    assert decision.allowed is False
    assert decision.reason == REASON_SCOPE


def test_valid_token_and_claim_allows_in_scope_path(tmp_path: Path) -> None:
    claims = TaskClaimStore(tmp_path)
    claim = claims.claim(
        task_id="KA-003-WRITE-GATE",
        repo="lumos-core",
        branch="x",
        worktree="/w",
        owner="claude",
        scopes=["src/lumos_board"],
    ).claim
    assert claim is not None
    gate = WriteGate(claims, secret=SECRET)
    token = gate.issue(claim)
    decision = gate.check(
        token=token, owner="claude", paths=["src/lumos_board/write_gate.py"]
    )
    assert decision.allowed is True
    assert decision.reason == REASON_ALLOWED
    assert decision.claim_id == claim.claim_id


def test_release_revokes_write_token(tmp_path: Path) -> None:
    claims = TaskClaimStore(tmp_path)
    claim = claims.claim(
        task_id="KA-003-WRITE-GATE",
        repo="lumos-core",
        branch="x",
        worktree="/w",
        owner="claude",
        scopes=["src/lumos_board"],
    ).claim
    assert claim is not None
    gate = WriteGate(claims, secret=SECRET)
    token = gate.issue(claim)
    claims.release(claim.claim_id, owner="claude")
    gate.revoke(claim.claim_id)
    decision = gate.check(token=token, owner="claude", paths=["src/lumos_board/write_gate.py"])
    assert decision.allowed is False
    assert decision.reason in {REASON_NO_CLAIM, REASON_NO_CREDENTIAL}


def test_cli_write_check_exit_codes(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)
    payload = _claim(tmp_path, task="KA-003-A", owner="claude", scope="src/lumos_board")
    token = payload["write_token"]
    assert isinstance(token, str) and token
    assert (
        claim_cli_main(
            [
                "--store",
                str(tmp_path),
                "write-check",
                "--token",
                token,
                "--owner",
                "claude",
                "--path",
                "src/lumos_board/write_gate.py",
            ]
        )
        == 0
    )
    assert (
        claim_cli_main(
            [
                "--store",
                str(tmp_path),
                "write-check",
                "--owner",
                "claude",
                "--path",
                "src/lumos_board/write_gate.py",
            ]
        )
        == 2
    )
    assert (
        claim_cli_main(
            [
                "--store",
                str(tmp_path),
                "write-check",
                "--token",
                token,
                "--owner",
                "cursor",
                "--path",
                "src/lumos_board/write_gate.py",
            ]
        )
        == 2
    )
