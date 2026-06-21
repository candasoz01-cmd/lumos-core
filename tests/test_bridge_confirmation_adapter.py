"""PR-C6: köprü pending_approval → CU4 confirmation namespace adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from policy.confirmation_policy import (
    BRIDGE_HIGH_RISK_ACTION,
    BRIDGE_MEDIUM_DISPATCH_ACTION,
    REASON_CONFIRMATION_DISABLED,
    REASON_CONFIRMATION_EXPIRED,
    REASON_CONFIRMATION_REQUIRED,
    SCHEMA_VERSION,
    attach_bridge_pending_confirmation,
    bridge_approve_validate_legacy_pending,
    bridge_pending_action_key,
    bridge_pending_confirmation_spec,
    check_confirmation,
    consume_bridge_confirmation,
    consume_confirmation,
    is_confirmation_enabled,
    requires_confirmation_for_action,
    validate_bridge_confirmation,
)


def test_bridge_action_keys_registered() -> None:
    assert requires_confirmation_for_action(BRIDGE_HIGH_RISK_ACTION)
    assert requires_confirmation_for_action(BRIDGE_MEDIUM_DISPATCH_ACTION)


def test_bridge_pending_action_key_mapping() -> None:
    assert bridge_pending_action_key(risk="high", source="lumos_gate") == BRIDGE_HIGH_RISK_ACTION
    assert (
        bridge_pending_action_key(risk="medium", source="lumos_gate")
        == BRIDGE_MEDIUM_DISPATCH_ACTION
    )
    assert (
        bridge_pending_action_key(risk="high", source="task_dispatch")
        == BRIDGE_MEDIUM_DISPATCH_ACTION
    )


def test_attach_bridge_pending_confirmation_writes_cu4_record(tmp_path: Path) -> None:
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending = {
        "schema_version": "lumos.pending_approval.v1",
        "title": "dosyayı sil",
        "normalized_task": {"target_rel": "src/a.py", "target_body": "sil"},
        "original_payload": "TARGET: src/a.py\nsil",
    }
    cid = attach_bridge_pending_confirmation(
        pending,
        base_dir=lumos,
        risk="high",
        source="lumos_gate",
    )
    assert cid
    assert pending["confirmation_id"] == cid
    assert pending["confirmation_action_key"] == BRIDGE_HIGH_RISK_ACTION
    assert pending["confirmation_namespace"] == SCHEMA_VERSION

    grant_path = lumos / "pending_confirmations" / f"{cid}.json"
    assert grant_path.is_file()
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    assert grant["schema_version"] == SCHEMA_VERSION
    assert grant["action_key"] == BRIDGE_HIGH_RISK_ACTION
    assert grant["scope"]["bridge_source"] == "lumos_gate"
    assert grant["scope"]["target"] == "src/a.py"
    assert grant["preview"]["effect"] == "bridge_execute_after_approval"


def test_bridge_pending_confirmation_spec_dispatch_medium() -> None:
    pending = {
        "schema_version": "lumos.dispatch_pending_approval.v1",
        "title": "shell komutu",
        "task_id": "tsk_42",
    }
    action_key, scope, preview = bridge_pending_confirmation_spec(
        pending, risk="medium", source="task_dispatch"
    )
    assert action_key == BRIDGE_MEDIUM_DISPATCH_ACTION
    assert scope["task_id"] == "tsk_42"
    assert scope["legacy_schema"] == "lumos.dispatch_pending_approval.v1"
    assert preview["risk_level"] == "medium"


def test_attach_bridge_does_not_require_confirmation_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    pending = {"title": "test", "schema_version": "lumos.pending_approval.v1"}
    cid = attach_bridge_pending_confirmation(
        pending,
        base_dir=tmp_path / ".lumos",
        risk="medium",
        source="task_dispatch",
    )
    assert cid
    assert (tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json").is_file()


def test_lumos_gate_high_risk_pending_links_confirmation_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_lumos_gate high risk → pending_approval_record + CU4 shadow kayıt."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "del_me.txt"
    fp.write_text("x\n", encoding="utf-8")
    from kando_runtime.lumos_gate import run_lumos_gate

    out = run_lumos_gate(
        "direct_patch",
        "TARGET: del_me.txt\nbu dosyayı sil\n",
        repo_root=tmp_path,
    )
    assert out.get("execution_mode") == "pending_approval"
    pr = out.get("pending_approval_record")
    assert isinstance(pr, dict)
    cid = str(pr.get("confirmation_id") or "")
    assert cid
    assert pr.get("confirmation_action_key") == BRIDGE_HIGH_RISK_ACTION
    assert (tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json").is_file()


def test_shadow_grant_scope_hash_matches_pending_record(tmp_path: Path) -> None:
    """CU4 shadow grant scope_hash pending kaydındaki confirmation_scope_hash ile eşleşir."""
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {
        "schema_version": "lumos.pending_approval.v1",
        "title": "scope probe",
        "normalized_task": {"target_rel": "src/b.py"},
    }
    cid = attach_bridge_pending_confirmation(
        pending,
        base_dir=lumos,
        risk="high",
        source="lumos_gate",
    )
    assert cid
    grant = json.loads((lumos / "pending_confirmations" / f"{cid}.json").read_text(encoding="utf-8"))
    assert pending["confirmation_scope_hash"] == grant["scope_hash"]
    assert pending["confirmation_id"] == grant["confirmation_id"]


def test_high_vs_medium_risk_shadow_action_keys_differ(tmp_path: Path) -> None:
    """High lumos_gate vs medium task_dispatch → farklı CU4 action_key."""
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    high: dict = {"schema_version": "lumos.pending_approval.v1", "title": "hr"}
    medium: dict = {
        "schema_version": "lumos.dispatch_pending_approval.v1",
        "title": "med",
        "task_id": "tsk_1",
    }
    attach_bridge_pending_confirmation(high, base_dir=lumos, risk="high", source="lumos_gate")
    attach_bridge_pending_confirmation(medium, base_dir=lumos, risk="medium", source="task_dispatch")
    assert high["confirmation_action_key"] == BRIDGE_HIGH_RISK_ACTION
    assert medium["confirmation_action_key"] == BRIDGE_MEDIUM_DISPATCH_ACTION
    high_grant = json.loads(
        (lumos / "pending_confirmations" / f"{high['confirmation_id']}.json").read_text(encoding="utf-8")
    )
    med_grant = json.loads(
        (lumos / "pending_confirmations" / f"{medium['confirmation_id']}.json").read_text(encoding="utf-8")
    )
    assert high_grant["scope"]["bridge_source"] == "lumos_gate"
    assert med_grant["scope"]["bridge_source"] == "task_dispatch"
    assert med_grant["scope"]["legacy_schema"] == "lumos.dispatch_pending_approval.v1"


def test_shadow_grant_second_consume_fails(tmp_path: Path) -> None:
    """Shadow grant tek kullanımlık — ikinci consume False (approve wiring öncesi karakterizasyon)."""
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "once"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="medium", source="task_dispatch")
    cid = str(pending["confirmation_id"])
    sh = str(pending["confirmation_scope_hash"])
    assert consume_confirmation(cid, sh, base_dir=lumos)
    assert not consume_confirmation(cid, sh, base_dir=lumos)


def test_shadow_grant_check_noop_when_env_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LUMOS_CONFIRMATION_ENABLED=false → check_confirmation no-op; attach yine yazar."""
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    assert not is_confirmation_enabled()
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "env off"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    grant = json.loads(
        (lumos / "pending_confirmations" / f"{pending['confirmation_id']}.json").read_text(encoding="utf-8")
    )
    result = check_confirmation(
        BRIDGE_HIGH_RISK_ACTION,
        grant["scope"],
        {"confirmation_id": pending["confirmation_id"], "base_dir": str(lumos)},
    )
    assert result.allowed
    assert result.reason == REASON_CONFIRMATION_DISABLED


def test_shadow_grant_consumed_blocks_check_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tüketilmiş shadow grant → check_confirmation blocked (enabled env)."""
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "consumed"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    cid = str(pending["confirmation_id"])
    sh = str(pending["confirmation_scope_hash"])
    grant = json.loads((lumos / "pending_confirmations" / f"{cid}.json").read_text(encoding="utf-8"))
    assert consume_confirmation(cid, sh, base_dir=lumos)
    result = check_confirmation(
        BRIDGE_HIGH_RISK_ACTION,
        grant["scope"],
        {"confirmation_id": cid, "base_dir": str(lumos)},
    )
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_REQUIRED


def test_validate_bridge_confirmation_high_risk_shadow_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {
        "schema_version": "lumos.pending_approval.v1",
        "title": "hr validate",
        "normalized_task": {"target_rel": "src/c.py"},
    }
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    result = validate_bridge_confirmation(pending, base_dir=lumos)
    assert result.allowed
    assert pending["confirmation_action_key"] == BRIDGE_HIGH_RISK_ACTION


def test_consume_bridge_confirmation_medium_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {
        "schema_version": "lumos.dispatch_pending_approval.v1",
        "title": "med consume",
        "task_id": "tsk_med",
    }
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="medium", source="task_dispatch")
    assert pending["confirmation_action_key"] == BRIDGE_MEDIUM_DISPATCH_ACTION
    assert consume_bridge_confirmation(pending, base_dir=lumos)
    grant = json.loads(
        (lumos / "pending_confirmations" / f"{pending['confirmation_id']}.json").read_text(encoding="utf-8")
    )
    assert grant.get("consumed") is True


def test_validate_bridge_expired_blocks_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import datetime, timedelta, timezone

    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "exp"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    grant_path = lumos / "pending_confirmations" / f"{pending['confirmation_id']}.json"
    data = json.loads(grant_path.read_text(encoding="utf-8"))
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    data["expires_at"] = past.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    grant_path.write_text(json.dumps(data), encoding="utf-8")
    result = validate_bridge_confirmation(pending, base_dir=lumos)
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_EXPIRED


def test_bridge_approve_validate_legacy_pending_delegates_high_risk(
    tmp_path: Path,
) -> None:
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {
        "schema_version": "lumos.pending_approval.v1",
        "title": "ok",
        "policy_ok": True,
        "final_decision": "await_user_approval",
        "risk_level": "high",
        "execution_mode": "pending_approval",
        "execution_plan": {"steps": [{"type": "patch", "file": "x.py", "content": "x"}]},
        "reasoning_snapshot": {"source": "test"},
        "normalized_task": {"target_rel": "x.py"},
    }
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    bridge_approve_validate_legacy_pending(pending, is_dispatch=False)


def test_bridge_approve_validate_legacy_pending_rejects_bad_policy(
    tmp_path: Path,
) -> None:
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {
        "schema_version": "lumos.pending_approval.v1",
        "title": "bad",
        "policy_ok": False,
        "final_decision": "await_user_approval",
        "risk_level": "high",
        "execution_mode": "pending_approval",
        "execution_plan": {"steps": [{"type": "patch", "file": "x.py", "content": "x"}]},
        "reasoning_snapshot": {"source": "test"},
        "normalized_task": {"target_rel": "x.py"},
    }
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    with pytest.raises(ValueError, match="policy_ok"):
        bridge_approve_validate_legacy_pending(pending, is_dispatch=False)
