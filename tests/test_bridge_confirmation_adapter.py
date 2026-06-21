"""PR-C6: köprü pending_approval → CU4 confirmation namespace adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from policy.confirmation_policy import (
    BRIDGE_HIGH_RISK_ACTION,
    BRIDGE_MEDIUM_DISPATCH_ACTION,
    SCHEMA_VERSION,
    attach_bridge_pending_confirmation,
    bridge_pending_action_key,
    bridge_pending_confirmation_spec,
    consume_confirmation,
    requires_confirmation_for_action,
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
