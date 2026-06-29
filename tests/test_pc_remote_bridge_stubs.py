"""Lumos PC remote bridge — stub tool schemas, approval gate, HTTP handlers."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from kando_bridge.pc_remote_tools import (
    CMD_OPEN_APP,
    CMD_OPEN_URL,
    CMD_READ_SCREEN,
    CMD_REQUEST_FILE_PICKER,
    CMD_SUGGEST_CLICK,
    CMD_TYPE_TEXT,
    ALL_COMMANDS,
    approve_pc_remote_pending,
    check_approval_gate,
    execute_tool_stub,
    handle_tools_execute_body,
    openai_tool_definitions,
    tools_schema_payload,
    validate_command_arguments,
)
from kando_bridge.pending_approvals import (
    PC_REMOTE_PENDING_SCHEMA,
    STATUS_APPROVED,
    STATUS_PENDING,
    find_pending_by_approval_id,
    pending_approvals_dir,
    write_pending_approval,
)

APPROVAL_COMMANDS = frozenset({
    CMD_OPEN_APP,
    CMD_OPEN_URL,
    CMD_TYPE_TEXT,
    CMD_SUGGEST_CLICK,
    CMD_REQUEST_FILE_PICKER,
})


def test_all_commands_count() -> None:
    assert len(ALL_COMMANDS) == 7


def test_openai_tool_definitions_count() -> None:
    assert len(openai_tool_definitions()) == 7


def test_tools_schema_payload_stub_only() -> None:
    payload = tools_schema_payload()
    assert payload["stub_only"] is True
    assert len(payload["commands"]) == 7
    assert payload["schema_version"] == "lumos.pc_remote_tools.v1"


def test_read_screen_no_approval_stub(tmp_path: Path) -> None:
    gate = check_approval_gate(CMD_READ_SCREEN)
    assert gate.allowed is True
    assert gate.approval_required is False
    out = execute_tool_stub(
        CMD_READ_SCREEN,
        {"scope": "active_window"},
        repo_root=tmp_path,
    )
    assert out["ok"] is True
    assert out["status"] == "stub"
    assert out["simulated"]["snapshot"]["stub"] is True


def test_open_url_requires_approval_pending(tmp_path: Path) -> None:
    gate = check_approval_gate(CMD_OPEN_URL, repo_root=tmp_path)
    assert gate.allowed is False
    assert gate.approval_required is True
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    assert out["status"] == "pending_approval"
    assert out["approval_required"] is True
    assert out["approval_token"]
    assert out["approval_id"]
    assert out["approval_file"]
    pending_dir = pending_approvals_dir(tmp_path)
    files = list(pending_dir.glob("*.json"))
    assert len(files) == 1
    disk = json.loads(files[0].read_text(encoding="utf-8"))
    assert disk["schema_version"] == PC_REMOTE_PENDING_SCHEMA
    assert disk["status"] == STATUS_PENDING
    assert disk["command"] == CMD_OPEN_URL
    assert disk["approval_token"] == out["approval_token"]


def test_approval_granted_flag_ignored_without_token(tmp_path: Path) -> None:
    """approval_granted tek başına stub yürütmeye yetmez."""
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    token = out["approval_token"]
    aid = out["approval_id"]
    found = find_pending_by_approval_id(tmp_path, aid)
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    bad = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    assert bad["status"] == "pending_approval"
    ok = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=token,
        approval_id=aid,
        repo_root=tmp_path,
    )
    assert ok["ok"] is True
    assert ok["status"] == "stub"


def test_open_url_with_approval_stub(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=pending["approval_token"],
        approval_id=pending["approval_id"],
        repo_root=tmp_path,
    )
    assert out["ok"] is True
    assert out["status"] == "stub"
    assert out["simulated"]["url"] == "https://example.com"


def test_suggest_click_never_auto_clicks(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_SUGGEST_CLICK,
        {"target_description": "Tamam düğmesi", "x": 100, "y": 200},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    out = execute_tool_stub(
        CMD_SUGGEST_CLICK,
        {"target_description": "Tamam düğmesi", "x": 100, "y": 200},
        approval_token=pending["approval_token"],
        approval_id=pending["approval_id"],
        repo_root=tmp_path,
    )
    assert out["simulated"]["auto_click"] is False


def test_type_text_blocked_surface() -> None:
    err = validate_command_arguments(CMD_TYPE_TEXT, {"text": "run bash terminal"})
    assert err == "surface_blocked"


def test_open_app_invalid_without_name() -> None:
    err = validate_command_arguments(CMD_OPEN_APP, {"app_name": ""})
    assert err == "app_name_required"


def test_open_url_invalid_scheme() -> None:
    err = validate_command_arguments(CMD_OPEN_URL, {"url": "ftp://bad"})
    assert err == "invalid_url"


def test_handle_tools_execute_body_pending(tmp_path: Path) -> None:
    status, out = handle_tools_execute_body(
        {
            "command": CMD_OPEN_APP,
            "arguments": {"app_name": "Safari"},
        },
        repo_root=tmp_path,
    )
    assert status == 200
    assert out["status"] == "pending_approval"


def test_handle_tools_execute_body_unknown_command(tmp_path: Path) -> None:
    status, out = handle_tools_execute_body(
        {"command": "pc_unknown", "arguments": {}},
        repo_root=tmp_path,
    )
    assert status == 400
    assert out["error"] == "unknown_command"


def test_expired_pending_rejected(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    created = now.isoformat()
    expired = (now - timedelta(minutes=5)).isoformat()
    record = {
        "schema_version": PC_REMOTE_PENDING_SCHEMA,
        "source": "pc_remote",
        "approval_id": "pc_remote_expired_test",
        "approval_file": ".lumos/pending_approvals/pc_remote_expired_test.json",
        "approval_token": "expired-token-hex",
        "command": CMD_OPEN_APP,
        "arguments": {"app_name": "Safari"},
        "arguments_preview": {"app_name": "Safari"},
        "requested_by": "test",
        "target_device": "local",
        "created_at": created,
        "expires_at": expired,
        "risk_level": "high",
        "required_user_action": "test",
        "status": STATUS_APPROVED,
        "used": False,
        "stub_only": True,
    }
    write_pending_approval(record, tmp_path)
    out = execute_tool_stub(
        CMD_OPEN_APP,
        {"app_name": "Safari"},
        approval_token="expired-token-hex",
        approval_id="pc_remote_expired_test",
        repo_root=tmp_path,
    )
    assert out["status"] == "rejected"
    assert out["error"] == "approval_expired"


@pytest.mark.parametrize("command,arguments", [
    (CMD_OPEN_APP, {"app_name": "Safari"}),
    (CMD_OPEN_URL, {"url": "https://example.com"}),
    (CMD_TYPE_TEXT, {"text": "hello"}),
    (CMD_SUGGEST_CLICK, {"target_description": "OK"}),
    (CMD_REQUEST_FILE_PICKER, {"purpose": "upload"}),
])
def test_all_five_approval_commands_create_pending(
    tmp_path: Path,
    command: str,
    arguments: dict[str, str],
) -> None:
    assert command in APPROVAL_COMMANDS
    out = execute_tool_stub(command, arguments, repo_root=tmp_path)
    assert out["status"] == "pending_approval"
    assert out["approval_id"]
    assert out["approval_token"]
    disk = json.loads(
        (pending_approvals_dir(tmp_path) / f"{out['approval_id']}.json").read_text(
            encoding="utf-8"
        )
    )
    assert disk["command"] == command
    assert disk["status"] == STATUS_PENDING


def _bridge_handler_stub(*, body: dict[str, Any]) -> Any:
    from kando_bridge.server import BridgeHandler

    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = {"Content-Length": str(len(raw))}
    handler.rfile = BytesIO(raw)
    handler.reject: tuple[int, str] | None = None
    handler.last_json: tuple[int, dict[str, Any]] | None = None
    handler.client_address = ("127.0.0.1", 12345)

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._reject = _reject
    handler._send_json = _send_json
    return handler


def test_server_tools_execute_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler

    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setenv("KANDO_BRIDGE_SECRET", "test-secret-tools")
    handler = _bridge_handler_stub(
        body={
            "command": CMD_READ_SCREEN,
            "arguments": {},
        }
    )
    handler.headers["X-Kando-Token"] = "test-secret-tools"
    BridgeHandler._handle_tools_execute(handler)
    assert handler.last_json is not None
    status, payload = handler.last_json
    assert status == 200
    assert payload["status"] == "stub"


def test_server_approve_pc_remote_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler

    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pending_dir)

    pending = execute_tool_stub(
        CMD_OPEN_APP,
        {"app_name": "Safari"},
        repo_root=tmp_path,
    )
    handler = _bridge_handler_stub(
        body={
            "approval_file": pending["approval_file"],
            "approval_token": pending["approval_token"],
            "approved": True,
        }
    )
    BridgeHandler._handle_approve(handler)
    assert handler.last_json is not None
    status, payload = handler.last_json
    assert status == 200
    assert payload["accepted"] is True
    assert payload.get("pc_remote_approval", {}).get("status") == "approved"

    exec_handler = _bridge_handler_stub(
        body={
            "command": CMD_OPEN_APP,
            "arguments": {"app_name": "Safari"},
            "approval_token": pending["approval_token"],
            "approval_id": pending["approval_id"],
        }
    )
    exec_handler.headers["X-Kando-Token"] = "unused"
    BridgeHandler._handle_tools_execute(exec_handler)
    assert exec_handler.last_json is not None
    _, exec_payload = exec_handler.last_json
    assert exec_payload["status"] == "stub"


def test_server_tools_schema_requires_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kando_bridge.server import BridgeHandler

    monkeypatch.delenv("KANDO_BRIDGE_SECRET", raising=False)
    handler = BridgeHandler.__new__(BridgeHandler)
    handler.client_address = ("127.0.0.1", 12345)
    handler.reject = None
    handler.last_json = None

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._reject = _reject
    handler._send_json = _send_json
    handler.path = "/tools/schema"
    handler.headers = {}
    BridgeHandler.do_GET(handler)
    assert handler.reject is not None
    assert handler.reject[0] == 401


def test_execute_without_token_after_approve_creates_new_pending(tmp_path: Path) -> None:
    """Approved disk record alone cannot stub-execute — new pending without token."""
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    again = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    assert again["status"] == "pending_approval"
    assert again["approval_id"] != pending["approval_id"]


def test_execute_with_wrong_token_rejected(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token="wrong-token-value",
        approval_id=pending["approval_id"],
        repo_root=tmp_path,
    )
    assert out["status"] == "rejected"
    assert out["error"] == "invalid_approval_token"


def test_handle_tools_execute_ignores_approval_granted_flag(tmp_path: Path) -> None:
    """Body approval_granted=true must not bypass token consume."""
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    status, out = handle_tools_execute_body(
        {
            "command": CMD_OPEN_URL,
            "arguments": {"url": "https://example.com"},
            "approval_granted": True,
        },
        repo_root=tmp_path,
    )
    assert status == 200
    assert out["status"] == "pending_approval"


def test_all_approval_commands_blocked_without_consume(tmp_path: Path) -> None:
    for command, arguments in [
        (CMD_OPEN_APP, {"app_name": "Safari"}),
        (CMD_OPEN_URL, {"url": "https://example.com"}),
        (CMD_TYPE_TEXT, {"text": "hi"}),
        (CMD_SUGGEST_CLICK, {"target_description": "OK"}),
        (CMD_REQUEST_FILE_PICKER, {"purpose": "upload"}),
    ]:
        pending = execute_tool_stub(command, arguments, repo_root=tmp_path)
        found = find_pending_by_approval_id(tmp_path, pending["approval_id"])
        assert found is not None
        approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
        blocked = execute_tool_stub(command, arguments, repo_root=tmp_path)
        assert blocked["status"] == "pending_approval", command
