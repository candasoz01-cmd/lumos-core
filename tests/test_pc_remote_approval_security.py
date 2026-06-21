"""PC remote approval security — replay, expiry, reject, concurrent execute (MVP)."""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kando_bridge.pc_remote_tools import (
    CMD_OPEN_URL,
    approve_pc_remote_pending,
    execute_tool_stub,
)
from kando_bridge.pending_approvals import (
    PC_REMOTE_PENDING_SCHEMA,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    find_pending_by_approval_id,
    write_pending_approval,
)


def _approve_pending(tmp_path: Path, pending: dict[str, object]) -> None:
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)


def test_double_execute_replay_rejected(tmp_path: Path) -> None:
    """Second stub execute with same token → approval_already_used."""
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    _approve_pending(tmp_path, pending)
    first = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=str(pending["approval_token"]),
        approval_id=str(pending["approval_id"]),
        repo_root=tmp_path,
    )
    assert first["ok"] is True
    assert first["status"] == "stub"

    second = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=str(pending["approval_token"]),
        approval_id=str(pending["approval_id"]),
        repo_root=tmp_path,
    )
    assert second["ok"] is False
    assert second["error"] == "approval_already_used"


def test_expired_approved_token_rejected(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    record = {
        "schema_version": PC_REMOTE_PENDING_SCHEMA,
        "source": "pc_remote",
        "approval_id": "pc_remote_expired_exec",
        "approval_file": ".lumos/pending_approvals/pc_remote_expired_exec.json",
        "approval_token": "expired-exec-token",
        "command": CMD_OPEN_URL,
        "arguments": {"url": "https://example.com"},
        "arguments_preview": {"url": "https://example.com"},
        "requested_by": "test",
        "target_device": "local",
        "created_at": now.isoformat(),
        "expires_at": (now - timedelta(minutes=1)).isoformat(),
        "risk_level": "medium",
        "required_user_action": "test",
        "status": STATUS_APPROVED,
        "used": False,
        "stub_only": True,
    }
    write_pending_approval(record, tmp_path)
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token="expired-exec-token",
        approval_id="pc_remote_expired_exec",
        repo_root=tmp_path,
    )
    assert out["status"] == "rejected"
    assert out["error"] == "approval_expired"


def test_reject_then_reexecute_fails(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=False, repo_root=tmp_path)

    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=str(pending["approval_token"]),
        approval_id=str(pending["approval_id"]),
        repo_root=tmp_path,
    )
    assert out["status"] == "rejected"
    assert out["error"] == "approval_rejected"

    disk = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert disk is not None
    assert disk[1]["status"] == STATUS_REJECTED


def test_concurrent_execute_one_wins(tmp_path: Path) -> None:
    """
    Two threads race the same approved token — exactly one stub succeeds.

    MVP uses fcntl on Unix; without lock both could succeed (documented gap on Windows).
    """
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    _approve_pending(tmp_path, pending)
    token = str(pending["approval_token"])
    aid = str(pending["approval_id"])
    results: list[dict] = []
    barrier = threading.Barrier(2)

    def _run() -> None:
        barrier.wait()
        results.append(
            execute_tool_stub(
                CMD_OPEN_URL,
                {"url": "https://example.com"},
                approval_token=token,
                approval_id=aid,
                repo_root=tmp_path,
            )
        )

    threads = [threading.Thread(target=_run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(results) == 2
    stubs = [r for r in results if r.get("status") == "stub"]
    already_used = [r for r in results if r.get("error") == "approval_already_used"]
    assert len(stubs) == 1
    assert len(already_used) == 1


def test_pending_disk_has_no_used_before_execute(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    disk = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert disk is not None
    assert disk[1]["status"] == STATUS_PENDING
    assert disk[1]["used"] is False
