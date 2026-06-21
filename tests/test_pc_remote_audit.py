"""PC remote audit JSONL contract tests."""
from __future__ import annotations

from pathlib import Path

from kando_bridge.pc_remote_audit import (
    AUDIT_SCHEMA,
    EVENT_PENDING_APPROVED,
    EVENT_PENDING_CREATED,
    EVENT_STUB_EXECUTED,
    append_pc_remote_audit,
    audit_events_path,
    read_audit_events,
)
from kando_bridge.pc_remote_tools import CMD_OPEN_URL, approve_pc_remote_pending, execute_tool_stub
from kando_bridge.pending_approvals import find_pending_by_approval_id


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
