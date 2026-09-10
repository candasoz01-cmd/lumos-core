"""F8: audit I/O failure must fail-close approval-gated / consequential ops.

Characterization: these tests fail on origin/main (append swallows OSError
and callers still return success). After the fix they must pass.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from kando_bridge.pc_remote_audit import (
    EVENT_PENDING_CREATED,
    EVENT_STUB_EXECUTED,
    append_pc_remote_audit,
)
from kando_bridge.pc_remote_tools import CMD_OPEN_URL, approve_pc_remote_pending, execute_tool_stub
from kando_bridge.pending_approvals import find_pending_by_approval_id


def _block_audit_log_dir(repo_root: Path) -> None:
    """Make `.lumos/logs` a file so mkdir/open for audit JSONL raises OSError."""
    logs = repo_root / ".lumos" / "logs"
    logs.parent.mkdir(parents=True, exist_ok=True)
    if logs.is_dir():
        for child in logs.iterdir():
            if child.is_file():
                child.unlink()
        logs.rmdir()
    logs.write_text("not-a-directory", encoding="utf-8")


def _bridge_handler_stub() -> Any:
    from kando_bridge.server import BridgeHandler

    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = {}
    handler.client_address = ("127.0.0.1", 0)
    handler.last_json: tuple[int, dict[str, Any]] | None = None

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._send_json = _send_json
    return handler


def test_append_pc_remote_audit_raises_oserror_when_logs_not_writable(tmp_path: Path) -> None:
    _block_audit_log_dir(tmp_path)
    raised = False
    try:
        append_pc_remote_audit(
            tmp_path,
            EVENT_PENDING_CREATED,
            approval_id="pc_remote_f8_io",
            command=CMD_OPEN_URL,
            status="pending",
        )
    except OSError:
        raised = True
    assert raised is True


def test_approved_stub_execute_fail_closed_when_audit_io_fails(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    approve_pc_remote_pending(found[0], found[1], approved=True, repo_root=tmp_path)
    _block_audit_log_dir(tmp_path)
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        approval_token=str(pending["approval_token"]),
        approval_id=str(pending["approval_id"]),
        repo_root=tmp_path,
    )
    assert out.get("ok") is False
    assert out.get("error") == "audit_write_failed"
    assert out.get("status") != "stub"


def test_new_pending_fail_closed_when_audit_io_fails(tmp_path: Path) -> None:
    _block_audit_log_dir(tmp_path)
    out = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    assert out.get("ok") is False
    assert out.get("error") == "audit_write_failed"
    assert out.get("status") != "pending_approval"
    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    leftovers = list(pending_dir.glob("*.json")) if pending_dir.is_dir() else []
    assert leftovers == []


def test_approve_fail_closed_when_audit_io_fails(tmp_path: Path) -> None:
    pending = execute_tool_stub(
        CMD_OPEN_URL,
        {"url": "https://example.com"},
        repo_root=tmp_path,
    )
    found = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert found is not None
    _block_audit_log_dir(tmp_path)
    ok, err, result = approve_pc_remote_pending(
        found[0],
        found[1],
        approved=True,
        repo_root=tmp_path,
    )
    assert ok is False
    assert err == "audit_write_failed"
    assert result is None
    still = find_pending_by_approval_id(tmp_path, str(pending["approval_id"]))
    assert still is not None
    assert still[1].get("status") != "approved"


def test_pipeline_pending_fail_closed_when_audit_io_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler

    def _boom(*_a: Any, **_k: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr("kando_runtime.lumos_audit.append_audit_log", _boom)
    handler = _bridge_handler_stub()
    BridgeHandler._send_lumos_pipeline_out(
        handler,
        {
            "execution_mode": "pending_approval",
            "lumos_audit_log": {
                "schema_version": "lumos.audit_log.v1",
                "log_id": "f8-pending",
            },
            "http_status": 200,
            "http_body": {},
        },
    )
    assert handler.last_json is not None
    status, body = handler.last_json
    assert status == 503
    assert body.get("accepted") is False
    assert body.get("error") == "audit_write_failed"


def test_pipeline_run_fail_closed_when_audit_io_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler

    def _boom(*_a: Any, **_k: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr("kando_runtime.lumos_audit.append_audit_log", _boom)
    handler = _bridge_handler_stub()
    BridgeHandler._send_lumos_pipeline_out(
        handler,
        {
            "policy_ok": True,
            "execution_mode": "run",
            "lumos_audit_log": {
                "schema_version": "lumos.audit_log.v1",
                "log_id": "f8-run",
            },
            "http_status": 200,
            "http_body": {"mode": "direct_patch", "accepted": True},
        },
    )
    assert handler.last_json is not None
    status, body = handler.last_json
    assert status == 503
    assert body.get("accepted") is False
    assert body.get("error") == "audit_write_failed"


def test_pipeline_policy_block_still_403_when_audit_io_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deny path stays deny; audit I/O must not convert a block into 503."""
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler

    def _boom(*_a: Any, **_k: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr("kando_runtime.lumos_audit.append_audit_log", _boom)
    handler = _bridge_handler_stub()
    BridgeHandler._send_lumos_pipeline_out(
        handler,
        {
            "policy_ok": False,
            "http_status": 403,
            "lumos_audit_log": {
                "schema_version": "lumos.audit_log.v1",
                "log_id": "f8-block",
                "blocked": True,
            },
        },
    )
    assert handler.last_json is not None
    status, body = handler.last_json
    assert status == 403
    assert body.get("accepted") is False
    assert body.get("error") == "blocked by lumos"


def test_append_still_writes_when_logs_writable(tmp_path: Path) -> None:
    append_pc_remote_audit(
        tmp_path,
        EVENT_STUB_EXECUTED,
        approval_id="pc_remote_f8_ok",
        command=CMD_OPEN_URL,
        status="stub",
    )
    path = tmp_path / ".lumos" / "logs" / "audit_events.jsonl"
    assert path.is_file()
    assert "stub_executed" in path.read_text(encoding="utf-8")
