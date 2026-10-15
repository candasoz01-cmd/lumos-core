"""A changed target or operation scope kills the old approval."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kando_bridge.pc_remote_tools import (
    CMD_OPEN_URL,
    approve_pc_remote_pending,
    execute_tool_stub,
)
from kando_bridge.pending_approvals import (
    find_pending_by_approval_id,
    stored_approval_token,
)
from kando_bridge.server import task_pipeline_result_for_chat
from policy.confirmation_policy import (
    REASON_REVOKED_SCOPE,
    REASON_SCOPE_MISMATCH,
    check_confirmation,
    request_confirmation,
)
from policy.task_execution_grant import (
    REASON_MISMATCH,
    REASON_REVOKED_SCOPE as GRANT_REVOKED,
    ExecutionBinding,
    accept_execution_task,
    consume_task_execution_grant,
)


def _binding(**overrides: str) -> ExecutionBinding:
    data = {
        "subject_id": "user:X",
        "agent_id": "agent:kando",
        "session_id": "session:s1",
        "task_id": "G-revoke",
        "action_key": "file_read",
        "resource": "notes/fileA.md",
        "permission": "read",
    }
    data.update(overrides)
    return ExecutionBinding(**data)


def test_confirmation_scope_change_revokes_original(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "task-1"}
    pending = request_confirmation("delete_task", scope, base_dir=tmp_path)
    ctx = {"confirmation_id": pending.confirmation_id, "base_dir": str(tmp_path)}
    drifted = check_confirmation("delete_task", {"id": "task-2"}, ctx)
    assert drifted.allowed is False
    assert drifted.reason == REASON_SCOPE_MISMATCH
    grant_path = tmp_path / "pending_confirmations" / f"{pending.confirmation_id}.json"
    stored = json.loads(grant_path.read_text(encoding="utf-8"))
    assert stored["revoked_reason"] == "scope_change"
    assert stored["consumed"] is True
    original = check_confirmation("delete_task", scope, ctx)
    assert original.allowed is False
    assert original.reason == REASON_REVOKED_SCOPE


def test_task_grant_scope_change_revokes_original(tmp_path: Path) -> None:
    binding = _binding()
    issued = accept_execution_task(binding, base_dir=tmp_path)
    mail = consume_task_execution_grant(
        issued.token,
        _binding(action_key="mail_send", permission="send"),
        base_dir=tmp_path,
    )
    assert mail.allowed is False
    assert mail.reason == REASON_MISMATCH
    original = consume_task_execution_grant(issued.token, binding, base_dir=tmp_path)
    assert original.allowed is False
    assert original.reason == GRANT_REVOKED


def test_pc_remote_url_change_revokes_and_hides_token(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.invalid/a"},
        repo_root=tmp_path,
    )
    assert pending["status"] == "pending_approval"
    assert "approval_token" not in pending
    token = stored_approval_token(tmp_path, pending["approval_id"])
    assert token
    assert token not in json.dumps(pending)
    found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
    assert found is not None
    ok, reason, _ = approve_pc_remote_pending(
        found[0], found[1], approved=True, repo_root=tmp_path,
    )
    assert ok, reason

    drifted = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.invalid/b"},
        approval_id=pending["approval_id"],
        approval_token=token,
        repo_root=tmp_path,
    )
    assert drifted["error"] == "approval_request_mismatch"
    original = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.invalid/a"},
        approval_id=pending["approval_id"],
        approval_token=token,
        repo_root=tmp_path,
    )
    assert original["error"] == "approval_revoked_scope_change"


def test_human_approved_client_retries_with_id_only(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.invalid/a"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    executed = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.invalid/a"},
        approval_id=pending["approval_id"],
        repo_root=tmp_path,
    )
    assert executed["ok"] is True
    assert executed["status"] == "stub"
    replay = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.invalid/a"},
        approval_id=pending["approval_id"],
        repo_root=tmp_path,
    )
    assert replay["error"] == "approval_already_used"


def test_chat_pipeline_view_omits_approval_token() -> None:
    view = task_pipeline_result_for_chat(
        {
            "execution_mode": "pending_approval",
            "approval_token": "secret-token",
            "approval_file": ".lumos/pending_approvals/example.json",
            "pending_approval_record": {
                "approval_id": "example",
                "approval_token": "secret-token",
            },
        }
    )
    assert view["requires_approval"] is True
    assert "approval_token" not in view
    assert "approval_token" not in view["pending_approval_record"]
    assert "secret-token" not in json.dumps(view)
