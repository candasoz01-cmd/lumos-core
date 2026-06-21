"""PR-W1-01: köprü approve sözleşme matrisi — legacy approval_token, shadow CU4 korelasyonu.

Karakterizasyon only: mevcut runtime davranışını sabitler (consume_confirmation approve'da yok).
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from kando_runtime.task_dispatch import (
    DISPATCH_PENDING_APPROVAL_SCHEMA,
    attach_execution_dispatch_to_out,
)
from policy.confirmation_policy import (
    BRIDGE_HIGH_RISK_ACTION,
    BRIDGE_MEDIUM_DISPATCH_ACTION,
    attach_bridge_pending_confirmation,
    bridge_approve_validate_legacy_pending,
    consume_bridge_confirmation,
    consume_confirmation,
    validate_bridge_confirmation,
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
    token: str = "tok-high-1",
    used: bool = False,
    with_shadow: bool = True,
) -> tuple[Path, dict[str, Any]]:
    lumos = tmp_path / ".lumos"
    pending_dir = lumos / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    rel = ".lumos/pending_approvals/hr1.json"
    rec: dict[str, Any] = {
        "schema_version": "lumos.pending_approval.v1",
        "created_at": "2026-06-21T00:00:00+00:00",
        "approval_file": rel,
        "approval_token": token,
        "risk_level": "high",
        "execution_mode": "pending_approval",
        "final_decision": "await_user_approval",
        "policy_ok": True,
        "original_payload": "TARGET: x.py\npatch\n",
        "title": "yüksek risk patch",
        "mode": "direct_patch",
        "normalized_task": {"target_rel": "x.py", "target_body": "patch"},
        "execution_plan": {"steps": [{"type": "patch", "file": "x.py", "content": "patch"}]},
        "reasoning_snapshot": {"source": "heuristic", "summary": "test"},
        "used": used,
    }
    if with_shadow:
        attach_bridge_pending_confirmation(
            rec,
            base_dir=lumos,
            risk="high",
            source="lumos_gate",
        )
    path = pending_dir / "hr1.json"
    path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return path, rec


def _write_dispatch_pending(tmp_path: Path, *, token: str = "tok-disp-1", used: bool = False) -> tuple[Path, dict[str, Any]]:
    out: dict[str, Any] = {
        "execution_mode": "restricted",
        "policy_ok": True,
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "medium",
            "normalized_task": {"target_body": "apr.txt oluştur"},
        },
    }
    attach_execution_dispatch_to_out(out, repo_root=tmp_path)
    pr = out["pending_approval_record"]
    assert isinstance(pr, dict)
    pr["approval_token"] = token
    pr["used"] = used
    rel = str(out.get("approval_file") or "")
    path = tmp_path / rel
    path.write_text(json.dumps(pr, ensure_ascii=False), encoding="utf-8")
    return path, pr


@pytest.mark.parametrize(
    "token_value,used,expected_error",
    [
        (None, False, "token gerekli"),
        ("", False, "token gerekli"),
        ("wrong-token", False, "geçersiz token"),
        ("tok-high-1", True, "zaten kullanıldı"),
    ],
)
def test_legacy_approval_token_rejection_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    token_value: str | None,
    used: bool,
    expected_error: str,
) -> None:
    """Legacy approval_token doğrulama matrisi (td-02 geriye uyumluluk)."""
    _write_high_risk_pending(tmp_path, token="tok-high-1", used=used)
    body: dict[str, Any] = {
        "approval_file": ".lumos/pending_approvals/hr1.json",
        "approved": True,
    }
    if token_value is not None:
        body["approval_token"] = token_value
    status, payload = _invoke_handle_approve(tmp_path, monkeypatch, body)
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("accepted") is False
    assert payload.get("error") == expected_error


def test_legacy_approve_false_closes_without_execute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, _rec = _write_high_risk_pending(tmp_path)
    status, payload = _invoke_handle_approve(
        tmp_path,
        monkeypatch,
        {
            "approval_file": ".lumos/pending_approvals/hr1.json",
            "approval_token": "tok-high-1",
            "approved": False,
        },
    )
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("accepted") is True
    assert payload.get("closed") is True
    assert payload.get("applied") is False
    assert not path.is_file()


def test_dispatch_approve_valid_token_executes_without_cu4_consume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Medium dispatch: legacy token yolu çalışır; shadow grant tüketilmez (PR-C6 gap karakterizasyonu)."""
    _path, rec = _write_dispatch_pending(tmp_path, token="tok-disp-1")
    cid = str(rec.get("confirmation_id") or "")
    scope_hash = str(rec.get("confirmation_scope_hash") or "")
    assert cid and scope_hash
    grant_path = tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json"
    assert grant_path.is_file()

    status, payload = _invoke_handle_approve(
        tmp_path,
        monkeypatch,
        {
            "approval_file": str(rec.get("approval_file") or ""),
            "approval_token": "tok-disp-1",
            "approved": True,
        },
    )
    assert status == 200
    assert isinstance(payload, dict)
    assert payload.get("accepted") is True
    assert payload.get("applied") is True
    assert (tmp_path / "workspace" / "apr.txt").is_file()

    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    assert grant.get("consumed") is False
    assert consume_confirmation(cid, scope_hash, base_dir=tmp_path / ".lumos")
    grant_after = json.loads(grant_path.read_text(encoding="utf-8"))
    assert grant_after.get("consumed") is True


def test_high_risk_pending_schema_distinct_from_dispatch(
    tmp_path: Path,
) -> None:
    """İki pending şeması: high lumos.pending_approval.v1 vs medium dispatch."""
    _hr_path, hr = _write_high_risk_pending(tmp_path)
    _dp_path, dp = _write_dispatch_pending(tmp_path)
    assert hr["schema_version"] == "lumos.pending_approval.v1"
    assert dp["schema_version"] == DISPATCH_PENDING_APPROVAL_SCHEMA
    assert hr.get("confirmation_action_key") == BRIDGE_HIGH_RISK_ACTION
    assert dp.get("confirmation_action_key") == BRIDGE_MEDIUM_DISPATCH_ACTION
    assert hr.get("risk_level") == "high"
    assert dp.get("risk_level") == "medium"


def test_cross_store_confirmation_id_and_scope_hash_correlate(
    tmp_path: Path,
) -> None:
    """pending_approvals kaydı ile pending_confirmations grant aynı id/hash taşır."""
    _path, rec = _write_high_risk_pending(tmp_path)
    cid = str(rec["confirmation_id"])
    scope_hash = str(rec["confirmation_scope_hash"])
    grant = json.loads(
        (tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json").read_text(encoding="utf-8")
    )
    assert grant["confirmation_id"] == cid
    assert grant["scope_hash"] == scope_hash
    assert grant["action_key"] == rec["confirmation_action_key"]


def test_w103_bridge_helpers_importable_from_policy() -> None:
    """PR-W1-03 yardımcı sınırı policy modülünden dışa açık."""
    assert callable(validate_bridge_confirmation)
    assert callable(consume_bridge_confirmation)
    assert callable(bridge_approve_validate_legacy_pending)


def test_bridge_server_delegates_legacy_validate_not_cu4_consume() -> None:
    """server.py legacy validate delegasyonu var; doğrudan consume_confirmation/check yok."""
    import kando_bridge.server as srv

    src = Path(srv.__file__).read_text(encoding="utf-8")
    assert "bridge_approve_validate_legacy_pending" in src
    assert "consume_confirmation" not in src
    assert "check_confirmation" not in src
    assert "consume_bridge_confirmation" not in src
    assert "validate_bridge_confirmation" not in src
