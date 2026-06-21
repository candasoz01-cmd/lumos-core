"""Lumos PC remote bridge — stub tool schemas, approval gate, HTTP handlers."""
from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pytest

from kando_bridge.pc_remote_tools import (
    CMD_OPEN_APP,
    CMD_OPEN_URL,
    CMD_READ_SCREEN,
    CMD_SUGGEST_CLICK,
    CMD_TYPE_TEXT,
    ALL_COMMANDS,
    check_approval_gate,
    execute_tool_stub,
    handle_tools_execute_body,
    openai_tool_definitions,
    tools_schema_payload,
    validate_command_arguments,
)


def test_all_commands_count() -> None:
    assert len(ALL_COMMANDS) == 7


def test_openai_tool_definitions_count() -> None:
    assert len(openai_tool_definitions()) == 7


def test_tools_schema_payload_stub_only() -> None:
    payload = tools_schema_payload()
    assert payload["stub_only"] is True
    assert len(payload["commands"]) == 7
    assert payload["schema_version"] == "lumos.pc_remote_tools.v1"


def test_read_screen_no_approval_stub() -> None:
    gate = check_approval_gate(CMD_READ_SCREEN)
    assert gate.allowed is True
    assert gate.approval_required is False
    out = execute_tool_stub(CMD_READ_SCREEN, {"scope": "active_window"})
    assert out["ok"] is True
    assert out["status"] == "stub"
    assert out["simulated"]["snapshot"]["stub"] is True


def test_open_url_requires_approval_pending() -> None:
    gate = check_approval_gate(CMD_OPEN_URL)
    assert gate.allowed is False
    assert gate.approval_required is True
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_granted=False,
    )
    assert out["status"] == "pending_approval"
    assert out["approval_required"] is True
    assert out["approval_token"]


def test_open_url_with_approval_stub() -> None:
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_granted=True,
    )
    assert out["ok"] is True
    assert out["status"] == "stub"
    assert out["simulated"]["url"] == "https://example.com"


def test_suggest_click_never_auto_clicks() -> None:
    out = execute_tool_stub(
        CMD_SUGGEST_CLICK,
        {"target_description": "Tamam düğmesi", "x": 100, "y": 200},
        approval_granted=True,
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


def test_handle_tools_execute_body_pending() -> None:
    status, out = handle_tools_execute_body(
        {
            "command": CMD_OPEN_APP,
            "arguments": {"app_name": "Safari"},
        }
    )
    assert status == 200
    assert out["status"] == "pending_approval"


def test_handle_tools_execute_body_unknown_command() -> None:
    status, out = handle_tools_execute_body(
        {"command": "pc_unknown", "arguments": {}}
    )
    assert status == 400
    assert out["error"] == "unknown_command"


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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kando_bridge.server import BridgeHandler

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
