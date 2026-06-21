"""PR-RB-05 — mobile approval poll client MVP end-to-end."""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from kando_bridge.mobile_approval_client import (
    approve_pending,
    find_record_by_ref,
    list_pending_pc_remote,
    reject_pending,
    validate_token_for_record,
)
from kando_bridge.pc_remote_tools import CMD_OPEN_URL, execute_tool_stub
from kando_bridge.pending_approvals import STATUS_APPROVED, STATUS_PENDING, find_pending_by_approval_id


def _bridge_handler_stub(*, body: dict[str, Any]) -> Any:
    from kando_bridge.server import BridgeHandler

    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = {"Content-Length": str(len(raw))}
    handler.rfile = BytesIO(raw)
    handler.reject: tuple[int, str] | None = None
    handler.last_json: tuple[int, dict[str, Any]] | None = None
    handler.last_bytes: bytes | None = None
    handler.client_address = ("127.0.0.1", 12345)

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    def _send_pending_approvals_array_response(*, source_filter: str | None = None) -> None:
        from kando_bridge.server import build_pending_approvals_list

        arr = build_pending_approvals_list(
            source_filter=source_filter,
            include_approval_token=True,
        )
        handler.last_bytes = json.dumps(arr, ensure_ascii=False).encode("utf-8")

    handler._reject = _reject
    handler._send_json = _send_json
    handler._send_pending_approvals_array_response = _send_pending_approvals_array_response
    return handler


def _dispatch_http(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    tmp_path: Path,
) -> tuple[int, Any]:
    """Route mobile client HTTP to BridgeHandler stubs (no live server)."""
    from kando_bridge.server import BridgeHandler

    if method == "GET" and path == "/pending_approvals":
        from kando_bridge.server import build_pending_approvals_list

        source_filter = (query or {}).get("source") or None
        include_tokens = (query or {}).get("include_tokens", "").lower() in ("1", "true", "yes")
        arr = build_pending_approvals_list(
            source_filter=source_filter,
            include_approval_token=include_tokens,
        )
        return 200, arr

    if method == "POST" and path == "/approve":
        handler = _bridge_handler_stub(body=body or {})
        BridgeHandler._handle_approve(handler)
        assert handler.last_json is not None
        status, payload = handler.last_json
        return status, payload

    if method == "POST" and path == "/tools/execute":
        handler = _bridge_handler_stub(body=body or {})
        handler.headers["X-Kando-Token"] = "test-secret"
        BridgeHandler._handle_tools_execute(handler)
        assert handler.last_json is not None
        status, payload = handler.last_json
        return status, payload

    raise AssertionError(f"unexpected dispatch: {method} {path}")


@pytest.fixture
def bridge_client_env(
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
        return _dispatch_http(method, path, body=body, query=query, tmp_path=tmp_path)

    monkeypatch.setattr(
        "kando_bridge.mobile_approval_client.http_json",
        _fake_http,
    )
    return tmp_path


def test_mobile_approval_mvp_e2e_pc_open_url(bridge_client_env: Path) -> None:
    """Pending → poll → approve → execute stub → used=true."""
    repo = bridge_client_env

    status, pending = _dispatch_http(
        "POST",
        "/tools/execute",
        body={
            "command": CMD_OPEN_URL,
            "arguments": {"url": "https://example.com"},
        },
        tmp_path=repo,
    )
    assert status == 200
    assert pending["status"] == "pending_approval"
    approval_id = pending["approval_id"]
    approval_token = pending["approval_token"]

    listed = list_pending_pc_remote(status=STATUS_PENDING)
    assert len(listed) == 1
    assert listed[0]["approval_id"] == approval_id
    assert listed[0]["command"] == CMD_OPEN_URL
    assert listed[0]["source"] == "pc_remote"

    found = find_record_by_ref(approval_id, items=listed)
    assert found is not None
    assert validate_token_for_record(found, approval_token)

    approve_out = approve_pending(approval_id, approval_token)
    assert approve_out.get("accepted") is True
    assert approve_out.get("pc_remote_approval", {}).get("status") == STATUS_APPROVED

    disk = find_pending_by_approval_id(repo, approval_id)
    assert disk is not None
    _, record = disk
    assert record["status"] == STATUS_APPROVED
    assert record["used"] is False

    exec_status, exec_out = _dispatch_http(
        "POST",
        "/tools/execute",
        body={
            "command": CMD_OPEN_URL,
            "arguments": {"url": "https://example.com"},
            "approval_id": approval_id,
            "approval_token": approval_token,
        },
        tmp_path=repo,
    )
    assert exec_status == 200
    assert exec_out["ok"] is True
    assert exec_out["status"] == "stub"
    assert exec_out["simulated"]["url"] == "https://example.com"

    disk_after = find_pending_by_approval_id(repo, approval_id)
    assert disk_after is not None
    assert disk_after[1]["used"] is True


def test_mobile_approval_reject_flow(bridge_client_env: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://reject.example.com"},
        repo_root=bridge_client_env,
    )
    aid = pending["approval_id"]
    tok = pending["approval_token"]

    reject_out = reject_pending(aid, tok)
    assert reject_out.get("accepted") is True
    assert reject_out.get("closed") is True

    listed = list_pending_pc_remote(status=STATUS_PENDING)
    assert not any(x.get("approval_id") == aid for x in listed)


def test_mobile_approval_invalid_token_rejected(bridge_client_env: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://bad-token.example.com"},
        repo_root=bridge_client_env,
    )
    out = approve_pending(pending["approval_id"], "wrong-token-hex")
    assert out.get("accepted") is False
    assert out.get("error") == "invalid_approval_token"


def test_get_pending_approvals_source_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /pending_approvals?source=pc_remote excludes legacy task pending."""
    import kando_bridge.server as srv
    from kando_bridge.server import build_pending_approvals_list

    pdir = tmp_path / ".lumos" / "pending_approvals"
    pdir.mkdir(parents=True)
    legacy = {
        "schema_version": "lumos.pending_approval.v1",
        "approval_token": "legacy-tok",
        "status": "pending",
        "original_payload": "README fix",
    }
    pc_remote = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://filter.example.com"},
        repo_root=tmp_path,
    )
    (pdir / "legacy.json").write_text(json.dumps(legacy), encoding="utf-8")
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pdir)

    all_items = build_pending_approvals_list()
    assert len(all_items) == 2

    pc_items = build_pending_approvals_list(source_filter="pc_remote")
    assert len(pc_items) == 1
    assert pc_items[0]["approval_id"] == pc_remote["approval_id"]
    assert pc_items[0]["source"] == "pc_remote"
