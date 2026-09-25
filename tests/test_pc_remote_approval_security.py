"""PC remote approval security — replay, expiry, reject, concurrent execute (MVP)."""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

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

    Unix'te fcntl; fcntl yoksa O_EXCL kilit dosyası (bkz. *_without_fcntl testleri).
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


def test_concurrent_execute_many_losers_all_already_used(tmp_path: Path) -> None:
    """
    Eight threads race one approved token — losers must ALL see approval_already_used.

    Regression: in-place truncate+write let unlocked readers observe empty/partial
    JSON, so a loser could get approval_not_found instead (flaky CI on PR #731).
    Atomic os.replace writes make the loser outcome deterministic.
    """
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    _approve_pending(tmp_path, pending)
    token = str(pending["approval_token"])
    aid = str(pending["approval_id"])
    n = 8
    results: list[dict] = []
    lock = threading.Lock()
    barrier = threading.Barrier(n)

    def _run() -> None:
        barrier.wait()
        r = execute_tool_stub(
            CMD_OPEN_URL,
            {"url": "https://example.com"},
            approval_token=token,
            approval_id=aid,
            repo_root=tmp_path,
        )
        with lock:
            results.append(r)

    threads = [threading.Thread(target=_run) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(results) == n
    errors = sorted(str(r.get("error")) for r in results if r.get("status") != "stub")
    assert [r.get("status") for r in results].count("stub") == 1
    assert errors == ["approval_already_used"] * (n - 1)


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


def test_try_consume_approval_token_marks_used(tmp_path: Path) -> None:
    from kando_bridge.pending_approvals import try_consume_approval_token

    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    _approve_pending(tmp_path, pending)
    ok, reason, rec = try_consume_approval_token(
        tmp_path,
        str(pending["approval_id"]),
        str(pending["approval_token"]),
    )
    assert ok is True
    assert reason == ""
    assert rec is not None
    assert rec["used"] is True
    ok2, reason2, _ = try_consume_approval_token(
        tmp_path,
        str(pending["approval_id"]),
        str(pending["approval_token"]),
    )
    assert ok2 is False
    assert reason2 == "approval_already_used"


def test_try_consume_rejects_expired_approved(tmp_path: Path) -> None:
    from kando_bridge.pending_approvals import try_consume_approval_token

    now = datetime.now(timezone.utc)
    record = {
        "schema_version": PC_REMOTE_PENDING_SCHEMA,
        "source": "pc_remote",
        "approval_id": "pc_remote_try_consume_exp",
        "approval_file": ".lumos/pending_approvals/pc_remote_try_consume_exp.json",
        "approval_token": "try-consume-exp-token",
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
    ok, reason, _ = try_consume_approval_token(
        tmp_path,
        "pc_remote_try_consume_exp",
        "try-consume-exp-token",
    )
    assert ok is False
    assert reason == "approval_expired"


def test_concurrent_execute_many_losers_without_fcntl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """fcntl yok (Windows yolu): O_EXCL kilit dosyası yarışı yine tek kazanana indirir."""
    import kando_bridge.pending_approvals as pa

    monkeypatch.setattr(pa, "_import_fcntl", lambda: None)
    pending = execute_tool_stub(CMD_OPEN_URL, {"url": "https://example.com"}, repo_root=tmp_path)
    _approve_pending(tmp_path, pending)
    n = 8
    results: list[dict] = []
    lock = threading.Lock()
    barrier = threading.Barrier(n)

    def _run() -> None:
        barrier.wait()
        r = execute_tool_stub(
            CMD_OPEN_URL,
            {"url": "https://example.com"},
            approval_token=str(pending["approval_token"]),
            approval_id=str(pending["approval_id"]),
            repo_root=tmp_path,
        )
        with lock:
            results.append(r)

    threads = [threading.Thread(target=_run) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert [r.get("status") for r in results].count("stub") == 1
    errors = sorted(str(r.get("error")) for r in results if r.get("status") != "stub")
    assert errors == ["approval_already_used"] * (n - 1)
    assert not list(tmp_path.rglob("*.excl"))


def test_consume_lock_timeout_fails_closed_without_fcntl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kilit alınamazsa kilitsiz tüketime düşülmez; kayıt kullanılmamış kalır."""
    import kando_bridge.pending_approvals as pa

    monkeypatch.setattr(pa, "_import_fcntl", lambda: None)
    monkeypatch.setattr(pa, "_EXCL_LOCK_TIMEOUT_SECONDS", 0.05)
    pending = execute_tool_stub(CMD_OPEN_URL, {"url": "https://example.com"}, repo_root=tmp_path)
    _approve_pending(tmp_path, pending)
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    held = found[0].with_name(f"{found[0].name}.lock.excl")
    held.write_text("", encoding="utf-8")  # başka süreç kilidi tutuyor

    ok, reason, _ = pa.try_consume_approval_token(
        tmp_path, str(pending["approval_id"]), str(pending["approval_token"])
    )
    assert (ok, reason) == (False, "approval_lock_timeout")
    again = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert again is not None and again[1].get("used") is False
    assert held.exists()  # başkasının kilidine dokunulmaz


def test_stale_excl_lock_is_recovered_without_fcntl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    import kando_bridge.pending_approvals as pa

    monkeypatch.setattr(pa, "_import_fcntl", lambda: None)
    pending = execute_tool_stub(CMD_OPEN_URL, {"url": "https://example.com"}, repo_root=tmp_path)
    _approve_pending(tmp_path, pending)
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    stale = found[0].with_name(f"{found[0].name}.lock.excl")
    stale.write_text("", encoding="utf-8")
    old = datetime.now().timestamp() - (pa._EXCL_LOCK_STALE_SECONDS + 5)
    os.utime(stale, (old, old))

    ok, reason, rec = pa.try_consume_approval_token(
        tmp_path, str(pending["approval_id"]), str(pending["approval_token"])
    )
    assert ok is True, reason
    assert rec is not None and rec["used"] is True
    assert not stale.exists()


def test_double_approve_is_idempotent_and_does_not_rewrite(tmp_path: Path) -> None:
    pending = execute_tool_stub(CMD_OPEN_URL, {"url": "https://example.com"}, repo_root=tmp_path)
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    ok, err, first = approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    assert ok is True, err
    after_first = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert after_first is not None
    approved_at = after_first[1]["approved_at"]
    audit = tmp_path / ".lumos" / "logs" / "audit_events.jsonl"
    audit_lines = audit.read_text(encoding="utf-8").splitlines() if audit.exists() else []

    ok2, err2, second = approve_pc_remote_pending(
        after_first[0], after_first[1], approved=True, repo_root=tmp_path
    )
    assert ok2 is True, err2
    assert second is not None and second["already_approved"] is True
    again = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert again is not None and again[1]["approved_at"] == approved_at
    now_lines = audit.read_text(encoding="utf-8").splitlines() if audit.exists() else []
    assert now_lines == audit_lines


def test_approve_after_reject_is_refused(tmp_path: Path) -> None:
    pending = execute_tool_stub(CMD_OPEN_URL, {"url": "https://example.com"}, repo_root=tmp_path)
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    ok, _, _ = approve_pc_remote_pending(found[0], found[1], approved=False, repo_root=tmp_path)
    assert ok is True
    rejected = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert rejected is not None and rejected[1]["status"] == STATUS_REJECTED
    ok2, err2, _ = approve_pc_remote_pending(
        rejected[0], rejected[1], approved=True, repo_root=tmp_path
    )
    assert (ok2, err2) == (False, "approval_not_pending")
