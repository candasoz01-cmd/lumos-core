"""PR-W1-03: köprü consume/validate akış karakterizasyonu (test-only).

Kritik akış (mevcut runtime — wiring yok):
  attach_bridge_pending_confirmation → shadow grant yazar
  BridgeHandler._handle_approve → approval_token doğrula → validate → unlink → execute
  consume_confirmation / check_confirmation approve handler'da çağrılmaz (td-02 gap)

Side-effect sırası: validate önce; consume yalnızca ayrı çağrıda; env off → check no-op.
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from policy.confirmation_policy import (
    BRIDGE_HIGH_RISK_ACTION,
    attach_bridge_pending_confirmation,
    check_confirmation,
    consume_confirmation,
)


def _bridge_handler_stub(*, body: dict[str, Any]) -> Any:
    from kando_bridge.server import BridgeHandler

    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = {"Content-Length": str(len(raw))}
    handler.rfile = BytesIO(raw)
    handler.reject: tuple[int, str] | None = None
    handler.last_json: tuple[int, dict[str, Any]] | None = None

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._reject = _reject
    handler._send_json = _send_json
    handler.pipeline_out: dict[str, Any] | None = None

    def _capture_pipeline(out: dict[str, Any], *, approval_path: Path | None = None) -> None:
        handler.pipeline_out = out
        handler._send_json(200, {"accepted": True, "applied": True, "lumos_gate": out})

    handler._send_lumos_pipeline_out = _capture_pipeline  # type: ignore[method-assign]
    return handler


def _invoke_handle_approve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: dict[str, Any],
) -> tuple[int, dict[str, Any]] | tuple[int, str]:
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler

    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pending_dir)

    handler = _bridge_handler_stub(body=body)
    BridgeHandler._handle_approve(handler)
    if handler.reject is not None:
        status, msg = handler.reject
        return status, msg
    assert handler.last_json is not None
    return handler.last_json


def _write_high_risk_pending(
    tmp_path: Path,
    *,
    token: str = "tok-hr-w103",
    policy_ok: bool = True,
) -> tuple[Path, dict[str, Any]]:
    lumos = tmp_path / ".lumos"
    pending_dir = lumos / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    rel = ".lumos/pending_approvals/hr_w103.json"
    rec: dict[str, Any] = {
        "schema_version": "lumos.pending_approval.v1",
        "created_at": "2026-06-21T00:00:00+00:00",
        "approval_file": rel,
        "approval_token": token,
        "risk_level": "high",
        "execution_mode": "pending_approval",
        "final_decision": "await_user_approval",
        "policy_ok": policy_ok,
        "original_payload": "TARGET: x.py\npatch\n",
        "title": "yüksek risk patch",
        "mode": "direct_patch",
        "normalized_task": {"target_rel": "x.py", "target_body": "patch"},
        "execution_plan": {"steps": [{"type": "patch", "file": "x.py", "content": "patched\n"}]},
        "reasoning_snapshot": {"source": "heuristic", "summary": "test"},
        "used": False,
    }
    attach_bridge_pending_confirmation(rec, base_dir=lumos, risk="high", source="lumos_gate")
    path = pending_dir / "hr_w103.json"
    path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return path, rec


def _write_dispatch_pending(tmp_path: Path, *, token: str = "tok-d-w103") -> tuple[Path, dict[str, Any]]:
    from kando_runtime.task_dispatch import attach_execution_dispatch_to_out

    out: dict[str, Any] = {
        "execution_mode": "restricted",
        "policy_ok": True,
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "medium",
            "normalized_task": {"target_body": "w103.txt oluştur"},
        },
    }
    attach_execution_dispatch_to_out(out, repo_root=tmp_path)
    pr = out["pending_approval_record"]
    assert isinstance(pr, dict)
    pr["approval_token"] = token
    pr["used"] = False
    rel = str(out.get("approval_file") or "")
    path = tmp_path / rel
    path.write_text(json.dumps(pr, ensure_ascii=False), encoding="utf-8")
    return path, pr


def _grant_unconsumed(grant_path: Path) -> None:
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    assert grant.get("consumed") is not True


def test_bridge_server_has_no_consume_confirmation_import() -> None:
    """Köprü approve handler CU4 consume kullanmaz (grep sözleşmesi)."""
    import kando_bridge.server as srv

    src = Path(srv.__file__).read_text(encoding="utf-8")
    assert "consume_confirmation" not in src
    assert "check_confirmation" not in src


def test_high_risk_approve_token_path_leaves_shadow_grant_unconsumed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """High-risk legacy token onayı kabul edilir; shadow CU4 grant tüketilmez."""
    path, rec = _write_high_risk_pending(tmp_path)
    cid = str(rec["confirmation_id"])
    scope_hash = str(rec["confirmation_scope_hash"])
    grant_path = tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json"

    status, payload = _invoke_handle_approve(
        tmp_path,
        monkeypatch,
        {
            "approval_file": ".lumos/pending_approvals/hr_w103.json",
            "approval_token": "tok-hr-w103",
            "approved": True,
        },
    )
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("accepted") is True
    assert not path.is_file()
    _grant_unconsumed(grant_path)
    assert consume_confirmation(cid, scope_hash, base_dir=tmp_path / ".lumos")


def test_high_risk_validate_failure_preserves_pending_and_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate hatası: pending dosyası kalır, shadow grant tüketilmez."""
    path, rec = _write_high_risk_pending(tmp_path, policy_ok=False)
    cid = str(rec["confirmation_id"])
    grant_path = tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json"

    status, payload = _invoke_handle_approve(
        tmp_path,
        monkeypatch,
        {
            "approval_file": ".lumos/pending_approvals/hr_w103.json",
            "approval_token": "tok-hr-w103",
            "approved": True,
        },
    )
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("accepted") is False
    assert "policy_ok" in str(payload.get("error") or "")
    assert path.is_file()
    _grant_unconsumed(grant_path)


def test_dispatch_validate_failure_preserves_pending_and_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dispatch validate hatası: pending + shadow grant dokunulmaz."""
    path, rec = _write_dispatch_pending(tmp_path)
    rec["policy_ok"] = False
    path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    cid = str(rec["confirmation_id"])
    grant_path = tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json"

    status, payload = _invoke_handle_approve(
        tmp_path,
        monkeypatch,
        {
            "approval_file": str(rec.get("approval_file") or ""),
            "approval_token": "tok-d-w103",
            "approved": True,
        },
    )
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("accepted") is False
    assert path.is_file()
    _grant_unconsumed(grant_path)


def test_dispatch_execute_exception_preserves_shadow_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute exception: pending silinmiş olsa bile shadow grant tüketilmez."""
    path, rec = _write_dispatch_pending(tmp_path)
    cid = str(rec["confirmation_id"])
    scope_hash = str(rec["confirmation_scope_hash"])
    grant_path = tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json"

    import kando_bridge.server as srv

    def _boom(_loaded: dict[str, Any], *, repo_root: Path | None = None) -> dict[str, Any]:
        raise RuntimeError("simulated executor failure")

    monkeypatch.setattr(
        "kando_runtime.task_dispatch.execute_approved_dispatch_pending",
        _boom,
    )
    monkeypatch.setattr(srv, "ROOT", tmp_path)

    status, payload = _invoke_handle_approve(
        tmp_path,
        monkeypatch,
        {
            "approval_file": str(rec.get("approval_file") or ""),
            "approval_token": "tok-d-w103",
            "approved": True,
        },
    )
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("accepted") is False
    assert "simulated executor failure" in str(payload.get("error") or "")
    assert not path.is_file()
    _grant_unconsumed(grant_path)
    assert consume_confirmation(cid, scope_hash, base_dir=tmp_path / ".lumos")


def test_shadow_grant_check_validate_before_consume_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """check_confirmation shadow grant doğrular; consume ayrı adım (validate before consume)."""
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict[str, Any] = {
        "schema_version": "lumos.pending_approval.v1",
        "title": "validate order",
        "normalized_task": {"target_rel": "a.py"},
    }
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    cid = str(pending["confirmation_id"])
    scope_hash = str(pending["confirmation_scope_hash"])
    grant_path = lumos / "pending_confirmations" / f"{cid}.json"
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    scope = grant["scope"]

    result = check_confirmation(
        BRIDGE_HIGH_RISK_ACTION,
        scope,
        {"confirmation_id": cid, "base_dir": str(lumos)},
    )
    assert result.allowed
    _grant_unconsumed(grant_path)
    assert consume_confirmation(cid, scope_hash, base_dir=lumos)
