"""Mobile approval MVP — direct bridge pc_remote flow (baseline for LAN relay)."""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from kando_bridge.pc_remote_tools import CMD_OPEN_APP, execute_tool_stub
from kando_bridge.server import BridgeHandler


def _bridge_handler_stub(*, body: dict[str, Any]) -> BridgeHandler:
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


def test_mobile_approval_mvp_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pending → approve on bridge → stub re-execute (no LAN relay)."""
    import kando_bridge.server as srv

    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pending_dir)

    pending = execute_tool_stub(
        CMD_OPEN_APP,
        {"app_name": "Safari"},
        repo_root=tmp_path,
    )
    assert pending["status"] == "pending_approval"

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
    BridgeHandler._handle_tools_execute(exec_handler)
    assert exec_handler.last_json is not None
    _, exec_payload = exec_handler.last_json
    assert exec_payload["status"] == "stub"
    assert exec_payload["ok"] is True
