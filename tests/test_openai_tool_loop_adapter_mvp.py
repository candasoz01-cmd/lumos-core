"""PR-RB-07 — OpenAI tool-loop adapter MVP end-to-end (CI-safe, no network)."""
from __future__ import annotations

import json
import socket
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from kando_bridge.lan_relay import RELAY_TOKEN_HEADER, LanRelayServer, RelayConfig
from kando_bridge.mobile_approval_client import approve_pending
from kando_bridge.openai_tool_adapter import (
    approve_and_reexecute,
    dev_auto_approve_allowed,
    mock_openai_response_payload,
    mock_pc_open_url_response,
    parse_openai_tool_calls,
    post_tools_execute,
    run_openai_response_loop,
    run_tool_call_loop,
    tool_call_to_execute_body,
)
from kando_bridge.pc_remote_tools import CMD_OPEN_URL
from kando_bridge.pending_approvals import STATUS_APPROVED, find_pending_by_approval_id


def _bridge_handler_stub(*, body: dict[str, Any]) -> Any:
    from kando_bridge.server import BridgeHandler

    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = {"Content-Length": str(len(raw))}
    handler.rfile = BytesIO(raw)
    handler.reject = None
    handler.last_json: tuple[int, dict[str, Any]] | None = None
    handler.client_address = ("127.0.0.1", 12345)

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._reject = _reject
    handler._send_json = _send_json
    return handler


def _dispatch_http(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, Any]:
    from kando_bridge.server import BridgeHandler, build_pending_approvals_list

    del query
    if method == "GET" and path == "/pending_approvals":
        return 200, build_pending_approvals_list()

    if method == "POST" and path == "/approve":
        handler = _bridge_handler_stub(body=body or {})
        BridgeHandler._handle_approve(handler)
        assert handler.last_json is not None
        return handler.last_json

    if method == "POST" and path == "/tools/execute":
        handler = _bridge_handler_stub(body=body or {})
        handler.headers["X-Kando-Token"] = "test-secret"
        BridgeHandler._handle_tools_execute(handler)
        assert handler.last_json is not None
        return handler.last_json

    raise AssertionError(f"unexpected dispatch: {method} {path}")


@pytest.fixture
def adapter_bridge_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    import kando_bridge.server as srv

    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pending_dir)
    monkeypatch.setenv("KANDO_BRIDGE_SECRET", "test-secret")

    def _fake_http(
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, Any]:
        del timeout
        return _dispatch_http(method, path, body=body, query=query)

    monkeypatch.setattr("kando_bridge.openai_tool_adapter.http_json", _fake_http)
    monkeypatch.setattr("kando_bridge.mobile_approval_client.http_json", _fake_http)
    return tmp_path


def test_parse_mock_pc_open_url_shapes() -> None:
    item = mock_pc_open_url_response()
    calls = parse_openai_tool_calls(item)
    assert len(calls) == 1
    assert calls[0].name == CMD_OPEN_URL
    assert calls[0].arguments["url"] == "https://example.com"

    wrapped = mock_openai_response_payload()
    calls2 = parse_openai_tool_calls(wrapped)
    assert len(calls2) == 1
    assert calls2[0].name == CMD_OPEN_URL

    chat_style = {
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": CMD_OPEN_URL,
                    "arguments": json.dumps({"url": "https://chat.example.com"}),
                },
            }
        ]
    }
    calls3 = parse_openai_tool_calls(chat_style)
    assert calls3[0].arguments["url"] == "https://chat.example.com"


def test_tool_call_to_execute_body() -> None:
    calls = parse_openai_tool_calls(mock_pc_open_url_response(url="https://a.example"))
    body = tool_call_to_execute_body(calls[0])
    assert body["command"] == CMD_OPEN_URL
    assert body["arguments"]["url"] == "https://a.example"
    assert body["requested_by"] == "openai_tool_adapter"


def test_openai_tool_loop_adapter_mvp_e2e(adapter_bridge_env: Path) -> None:
    """Mock OpenAI → bridge pending → manual approve → stub execute → used=true."""
    repo = adapter_bridge_env
    payload = mock_openai_response_payload(url="https://example.com")

    results = run_openai_response_loop(payload)
    assert len(results) == 1
    result = results[0]
    assert result["stage"] == "pending"
    assert result["pending"]["status"] == "pending_approval"

    pending = result["pending"]
    calls = parse_openai_tool_calls(payload)
    approve_out = approve_pending(pending["approval_id"], pending["approval_token"])
    assert approve_out.get("accepted") is True

    exec_status, loop_out = approve_and_reexecute(calls[0], pending)
    assert loop_out["ok"] is True
    assert loop_out["stage"] == "executed"

    execute = loop_out["execute"]
    assert execute["status"] == "stub"
    assert execute["simulated"]["url"] == "https://example.com"

    approval_id = pending["approval_id"]
    disk = find_pending_by_approval_id(repo, approval_id)
    assert disk is not None
    assert disk[1]["used"] is True


def test_openai_tool_loop_default_stays_pending(adapter_bridge_env: Path) -> None:
    """Default auto_approve=False — pending stays until explicit approve."""
    calls = parse_openai_tool_calls(mock_pc_open_url_response())
    result = run_tool_call_loop(calls[0])
    assert result["stage"] == "pending"
    assert result["pending"]["status"] == "pending_approval"
    assert result.get("ok") is False


def test_openai_tool_loop_pending_without_auto_approve(adapter_bridge_env: Path) -> None:
    calls = parse_openai_tool_calls(mock_pc_open_url_response())
    result = run_tool_call_loop(calls[0], auto_approve=False)
    assert result["stage"] == "pending"
    assert result["pending"]["status"] == "pending_approval"


def test_auto_approve_blocked_without_dev_env(
    adapter_bridge_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """auto_approve=True without LUMOS_DEV_AUTO_APPROVE must not silently execute."""
    monkeypatch.delenv("LUMOS_DEV_AUTO_APPROVE", raising=False)
    calls = parse_openai_tool_calls(mock_pc_open_url_response())
    assert dev_auto_approve_allowed() is False
    result = run_tool_call_loop(calls[0], auto_approve=True)
    assert result["stage"] == "pending"
    assert result.get("dev_auto_approve_blocked") is True
    assert result["pending"]["status"] == "pending_approval"


def test_auto_approve_works_with_dev_env(
    adapter_bridge_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LUMOS_DEV_AUTO_APPROVE", "1")
    calls = parse_openai_tool_calls(mock_pc_open_url_response())
    result = run_tool_call_loop(calls[0], auto_approve=True)
    assert result["stage"] == "executed"
    assert result["ok"] is True


def test_openai_tool_loop_post_tools_execute_pending(adapter_bridge_env: Path) -> None:
    calls = parse_openai_tool_calls(mock_pc_open_url_response())
    body = tool_call_to_execute_body(calls[0])
    status, out = post_tools_execute(body)
    assert status == 200
    assert out["status"] == "pending_approval"
    assert out["approval_token"]


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _make_mock_bridge_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler, build_pending_approvals_list

    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pending_dir)
    monkeypatch.setenv("KANDO_BRIDGE_SECRET", "bridge-test-secret")

    def bridge_request(
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> tuple[int, dict[str, Any]]:
        if method.upper() == "GET" and path == "/pending_approvals":
            return 200, {"items": build_pending_approvals_list()}
        if method.upper() == "POST" and path == "/tools/execute":
            obj = json.loads((body or b"{}").decode("utf-8"))
            handler = _bridge_handler_stub(body=obj)
            handler.headers["X-Kando-Token"] = headers.get("X-Kando-Token", "bridge-test-secret")
            BridgeHandler._handle_tools_execute(handler)
            assert handler.last_json is not None
            return handler.last_json
        if method.upper() == "POST" and path == "/approve":
            obj = json.loads((body or b"{}").decode("utf-8"))
            handler = _bridge_handler_stub(body=obj)
            BridgeHandler._handle_approve(handler)
            assert handler.last_json is not None
            return handler.last_json
        return 404, {"error": "not_found"}

    return bridge_request


def _relay_post(
    port: int,
    path: str,
    body: dict[str, Any],
    *,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers[RELAY_TOKEN_HEADER] = token
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raw = e.read().decode("utf-8")
        payload = json.loads(raw) if raw.strip() else {"error": str(e)}
        return e.code, payload if isinstance(payload, dict) else {"error": str(payload)}


@pytest.fixture
def relay_with_adapter_bridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, str, Any]:
    port = _free_port()
    bridge_request = _make_mock_bridge_request(tmp_path, monkeypatch)
    config = RelayConfig(
        host="127.0.0.1",
        port=port,
        bridge_url="http://127.0.0.1:8765",
        bridge_secret="bridge-test-secret",
        enable_beacon=False,
        bridge_request=bridge_request,
    )
    server = LanRelayServer(config)
    thread = threading.Thread(target=server.start, kwargs={"block": True}, daemon=True)
    thread.start()
    time.sleep(0.15)
    assert config.state is not None
    _, pair_payload = _relay_post(
        port,
        "/relay/pair",
        {"pairing_code": config.state.pairing_id},
    )
    relay_token = pair_payload["relay_token"]
    return port, relay_token, bridge_request


def test_openai_tool_loop_via_lan_relay_approve(
    relay_with_adapter_bridge: tuple[int, str, Any],
    tmp_path: Path,
) -> None:
    """Adapter pending → approve via LAN relay proxy → adapter re-execute stub."""
    port, relay_token, bridge_request = relay_with_adapter_bridge

    calls = parse_openai_tool_calls(mock_pc_open_url_response(url="https://relay.example.com"))
    body = tool_call_to_execute_body(calls[0])
    status, pending_out = bridge_request(
        "POST",
        "/tools/execute",
        {"Content-Type": "application/json"},
        json.dumps(body, ensure_ascii=False).encode("utf-8"),
    )
    assert status == 200
    assert pending_out["status"] == "pending_approval"

    _, approve_payload = _relay_post(
        port,
        "/relay/approve",
        {
            "approval_file": pending_out["approval_file"],
            "approval_token": pending_out["approval_token"],
        },
        token=relay_token,
    )
    assert approve_payload.get("accepted") is True
    assert approve_payload.get("pc_remote_approval", {}).get("status") == STATUS_APPROVED

    exec_body = tool_call_to_execute_body(
        calls[0],
        approval_token=pending_out["approval_token"],
        approval_id=pending_out["approval_id"],
    )
    exec_status, exec_out = bridge_request(
        "POST",
        "/tools/execute",
        {"Content-Type": "application/json"},
        json.dumps(exec_body, ensure_ascii=False).encode("utf-8"),
    )
    assert exec_status == 200
    assert exec_out["ok"] is True
    assert exec_out["status"] == "stub"

    disk = find_pending_by_approval_id(tmp_path, pending_out["approval_id"])
    assert disk is not None
    assert disk[1]["used"] is True


def test_openai_tool_loop_manual_approve_path(adapter_bridge_env: Path) -> None:
    calls = parse_openai_tool_calls(mock_pc_open_url_response())
    pending_result = run_tool_call_loop(calls[0], auto_approve=False)
    pending = pending_result["pending"]
    approve_out = approve_pending(pending["approval_id"], pending["approval_token"])
    assert approve_out.get("accepted") is True

    exec_status, exec_out = post_tools_execute(
        tool_call_to_execute_body(
            calls[0],
            approval_token=pending["approval_token"],
            approval_id=pending["approval_id"],
        )
    )
    assert exec_status == 200
    assert exec_out["status"] == "stub"
