"""PC remote audit JSONL contract tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from kando_bridge.pc_remote_audit import (
    AUDIT_SCHEMA,
    EVENT_APPROVAL_DENIED,
    EVENT_EXECUTE_REJECTED,
    EVENT_PENDING_APPROVED,
    EVENT_PENDING_CREATED,
    EVENT_PENDING_EXPIRED,
    EVENT_PENDING_REJECTED,
    EVENT_STUB_EXECUTED,
    append_pc_remote_audit,
    audit_events_path,
    read_audit_events,
)
from kando_bridge.pc_remote_tools import CMD_OPEN_URL, approve_pc_remote_pending, execute_tool_stub
from kando_bridge.pending_approvals import (
    PC_REMOTE_PENDING_SCHEMA,
    STATUS_PENDING,
    find_pending_by_approval_id,
    mark_expired_if_needed,
    write_pending_approval,
)


def test_append_pc_remote_audit_writes_jsonl(tmp_path: Path) -> None:
    append_pc_remote_audit(
        tmp_path,
        EVENT_PENDING_CREATED,
        approval_id="pc_remote_test_1",
        command=CMD_OPEN_URL,
        status="pending",
        requested_by="test",
    )
    path = audit_events_path(tmp_path)
    assert path.is_file()
    events = read_audit_events(tmp_path)
    assert len(events) == 1
    assert events[0]["schema_version"] == AUDIT_SCHEMA
    assert events[0]["event"] == EVENT_PENDING_CREATED
    assert events[0]["approval_id"] == "pc_remote_test_1"
    assert "url" not in str(events[0]).lower() or "command" in events[0]


def test_audit_trail_on_pending_approve_execute(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://secret-user-content.example.com"},
        repo_root=tmp_path,
        requested_by="openai_tool_adapter",
    )
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://secret-user-content.example.com"},
        approval_token=str(pending["approval_token"]),
        approval_id=str(pending["approval_id"]),
        repo_root=tmp_path,
    )
    events = read_audit_events(tmp_path)
    kinds = {e["event"] for e in events}
    assert EVENT_PENDING_CREATED in kinds
    assert EVENT_PENDING_APPROVED in kinds
    assert EVENT_STUB_EXECUTED in kinds
    blob = "\n".join(str(e) for e in events)
    assert "secret-user-content" not in blob


def test_audit_reject_event(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=False, repo_root=tmp_path)
    kinds = {e["event"] for e in read_audit_events(tmp_path)}
    assert EVENT_PENDING_REJECTED in kinds


def test_audit_expired_event(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    record = {
        "schema_version": PC_REMOTE_PENDING_SCHEMA,
        "source": "pc_remote",
        "approval_id": "pc_remote_expire_audit",
        "approval_file": ".lumos/pending_approvals/pc_remote_expire_audit.json",
        "approval_token": "expire-audit-token",
        "command": CMD_OPEN_URL,
        "arguments": {"url": "https://example.com"},
        "arguments_preview": {"url": "https://example.com"},
        "requested_by": "test",
        "target_device": "local",
        "created_at": now.isoformat(),
        "expires_at": (now - timedelta(minutes=1)).isoformat(),
        "risk_level": "medium",
        "required_user_action": "test",
        "status": STATUS_PENDING,
        "used": False,
        "stub_only": True,
    }
    write_pending_approval(record, tmp_path)
    data = find_pending_by_approval_id(tmp_path, "pc_remote_expire_audit")
    assert data is not None
    mark_expired_if_needed(data[0], data[1])
    kinds = {e["event"] for e in read_audit_events(tmp_path)}
    assert EVENT_PENDING_EXPIRED in kinds


def test_audit_execute_rejected_on_replay(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    token = str(pending["approval_token"])
    aid = str(pending["approval_id"])
    execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=token,
        approval_id=aid,
        repo_root=tmp_path,
    )
    execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=token,
        approval_id=aid,
        repo_root=tmp_path,
    )
    rejected = [
        e for e in read_audit_events(tmp_path) if e["event"] == EVENT_EXECUTE_REJECTED
    ]
    assert len(rejected) >= 1
    assert rejected[-1]["error"] == "approval_already_used"


def test_audit_execute_rejected_on_bad_token(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token="not-the-real-token",
        approval_id=str(pending["approval_id"]),
        repo_root=tmp_path,
    )
    events = read_audit_events(tmp_path)
    assert any(
        e["event"] == EVENT_EXECUTE_REJECTED and e["error"] == "invalid_approval_token"
        for e in events
    )

def test_audit_approval_denied_on_invalid_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import kando_bridge.server as srv
    from io import BytesIO

    from kando_bridge.server import BridgeHandler

    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pending_dir)

    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    raw = __import__("json").dumps(
        {
            "approval_file": pending["approval_file"],
            "approval_token": "wrong-token",
            "approved": True,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = {"Content-Length": str(len(raw))}
    handler.rfile = BytesIO(raw)
    handler.client_address = ("127.0.0.1", 12345)
    handler.last_json = None

    def _reject(status: int, msg: str) -> None:
        raise AssertionError(msg)

    handler._reject = _reject
    handler._send_json = lambda status, payload: setattr(handler, "last_json", (status, payload))
    BridgeHandler._handle_approve(handler)
    assert handler.last_json is not None
    _, payload = handler.last_json
    assert payload.get("accepted") is False
    denied = [e for e in read_audit_events(tmp_path) if e["event"] == EVENT_APPROVAL_DENIED]
    assert len(denied) == 1
