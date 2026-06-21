"""CU4 confirmation_policy unit tests (PR-C1)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from policy.confirmation_policy import (
    BRIDGE_HIGH_RISK_ACTION,
    REASON_CONFIRMATION_DISABLED,
    REASON_CONFIRMATION_EXPIRED,
    REASON_CONFIRMATION_REQUIRED,
    REASON_SCOPE_MISMATCH,
    REQUIRES_CONFIRMATION_ACTIONS,
    attach_bridge_pending_confirmation,
    bridge_pending_cu4_fields,
    check_confirmation,
    consume_bridge_confirmation,
    consume_confirmation,
    ensure_delete_permanent_confirmation,
    ensure_cli_mutation_confirmation,
    ensure_panel_mutation_confirmation,
    is_confirmation_enabled,
    request_confirmation,
    requires_confirmation_for_action,
    validate_bridge_confirmation,
)


@pytest.fixture(autouse=True)
def _clear_confirmation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)


def test_disabled_default_passes_without_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not is_confirmation_enabled()
    result = check_confirmation("create_task", {"task_id": "t1"}, {})
    assert result.allowed
    assert result.reason == REASON_CONFIRMATION_DISABLED


def test_disabled_explicit_false_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "false")
    result = check_confirmation("delete_permanent", {"id": "x"}, {})
    assert result.allowed
    assert result.reason == REASON_CONFIRMATION_DISABLED


def test_registry_contains_delete_permanent() -> None:
    assert "delete_permanent" in REQUIRES_CONFIRMATION_ACTIONS
    assert requires_confirmation_for_action("delete_permanent")


def test_registry_contains_external_and_cu_actions() -> None:
    assert "external_write" in REQUIRES_CONFIRMATION_ACTIONS
    assert requires_confirmation_for_action("cu_act_click")


def test_enabled_requires_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"task_id": "abc", "op": "create"}
    result = check_confirmation("create_task", scope, {"base_dir": str(tmp_path)})
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_REQUIRED


def test_enabled_grant_allows_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"task_id": "abc", "op": "create"}
    pending = request_confirmation("create_task", scope, {"title": "Demo"}, base_dir=tmp_path)
    result = check_confirmation(
        "create_task",
        scope,
        {"confirmation_id": pending.confirmation_id, "base_dir": str(tmp_path)},
    )
    assert result.allowed
    assert result.reason == ""


def test_enabled_scope_mismatch_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    pending = request_confirmation("delete_task", {"id": "1"}, base_dir=tmp_path)
    result = check_confirmation(
        "delete_task",
        {"id": "2"},
        {"confirmation_id": pending.confirmation_id, "base_dir": str(tmp_path)},
    )
    assert not result.allowed
    assert result.reason == REASON_SCOPE_MISMATCH


def test_enabled_action_key_mismatch_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "1"}
    pending = request_confirmation("delete_task", scope, base_dir=tmp_path)
    result = check_confirmation(
        "complete_task",
        scope,
        {"confirmation_id": pending.confirmation_id, "base_dir": str(tmp_path)},
    )
    assert not result.allowed
    assert result.reason == REASON_SCOPE_MISMATCH


def test_enabled_expired_grant_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "exp"}
    pending = request_confirmation("delete_permanent", scope, base_dir=tmp_path, ttl_seconds=1)
    grant_path = tmp_path / "pending_confirmations" / f"{pending.confirmation_id}.json"
    data = json.loads(grant_path.read_text(encoding="utf-8"))
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    data["expires_at"] = past.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    grant_path.write_text(json.dumps(data), encoding="utf-8")
    result = check_confirmation(
        "delete_permanent",
        scope,
        {"confirmation_id": pending.confirmation_id, "base_dir": str(tmp_path)},
    )
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_EXPIRED


def test_consume_confirmation_single_use(tmp_path: Path) -> None:
    scope = {"id": "c1"}
    pending = request_confirmation("delete_permanent", scope, base_dir=tmp_path)
    assert consume_confirmation(pending.confirmation_id, pending.scope_hash, base_dir=tmp_path)
    assert not consume_confirmation(pending.confirmation_id, pending.scope_hash, base_dir=tmp_path)


def test_consume_wrong_scope_hash_fails(tmp_path: Path) -> None:
    pending = request_confirmation("external_write", {"target": "mail"}, base_dir=tmp_path)
    assert not consume_confirmation(pending.confirmation_id, "wrong-hash", base_dir=tmp_path)


def test_unknown_action_passes_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    result = check_confirmation("read_only_list", {}, {"base_dir": str(tmp_path)})
    assert result.allowed


def test_consumed_grant_blocks_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "used"}
    pending = request_confirmation("restore_task", scope, base_dir=tmp_path)
    assert consume_confirmation(pending.confirmation_id, pending.scope_hash, base_dir=tmp_path)
    result = check_confirmation(
        "restore_task",
        scope,
        {"confirmation_id": pending.confirmation_id, "base_dir": str(tmp_path)},
    )
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_REQUIRED


def test_ensure_delete_permanent_disabled_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    result = ensure_delete_permanent_confirmation({}, {"id": "x"}, legacy_confirm=False)
    assert result.allowed
    assert result.reason == REASON_CONFIRMATION_DISABLED


def test_ensure_delete_permanent_legacy_confirm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "dp1"}
    result = ensure_delete_permanent_confirmation({}, scope, base_dir=tmp_path, legacy_confirm=True)
    assert result.allowed


def test_ensure_delete_permanent_requires_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    result = ensure_delete_permanent_confirmation({}, {"id": "dp2"}, base_dir=tmp_path, legacy_confirm=False)
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_REQUIRED


def test_ensure_delete_permanent_confirmation_id_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "dp3"}
    pending = request_confirmation("delete_permanent", scope, base_dir=tmp_path)
    body = {"confirmation_id": pending.confirmation_id}
    result = ensure_delete_permanent_confirmation(body, scope, base_dir=tmp_path, legacy_confirm=False)
    assert result.allowed


def test_ensure_panel_mutation_disabled_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    result = ensure_panel_mutation_confirmation("create_task", {"title": "x"}, {})
    assert result.allowed
    assert result.reason == REASON_CONFIRMATION_DISABLED


def test_ensure_panel_mutation_requires_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"title": "Demo"}
    result = ensure_panel_mutation_confirmation("create_task", scope, {}, base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_REQUIRED


def test_ensure_panel_mutation_confirmation_id_consumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"title": "Onaylı"}
    pending = request_confirmation("create_task", scope, base_dir=tmp_path)
    body = {"confirmation_id": pending.confirmation_id}
    result = ensure_panel_mutation_confirmation("create_task", scope, body, base_dir=tmp_path)
    assert result.allowed
    retry = ensure_panel_mutation_confirmation("create_task", scope, body, base_dir=tmp_path)
    assert not retry.allowed


def test_ensure_cli_mutation_disabled_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    result = ensure_cli_mutation_confirmation("delete_task", {"id": "1"}, None)
    assert result.allowed
    assert result.reason == REASON_CONFIRMATION_DISABLED


def test_ensure_cli_mutation_confirmation_id_consumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "42"}
    pending = request_confirmation("delete_task", scope, base_dir=tmp_path)
    result = ensure_cli_mutation_confirmation(
        "delete_task",
        scope,
        pending.confirmation_id,
        base_dir=tmp_path,
    )
    assert result.allowed
    retry = ensure_cli_mutation_confirmation(
        "delete_task",
        scope,
        pending.confirmation_id,
        base_dir=tmp_path,
    )
    assert not retry.allowed


def test_bridge_shadow_grant_wrong_scope_hash_blocks_consume(tmp_path: Path) -> None:
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "bridge scope"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    assert not consume_confirmation(
        str(pending["confirmation_id"]),
        "deadbeefdeadbeef",
        base_dir=lumos,
    )


def test_check_confirmation_validate_only_does_not_consume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """check_confirmation doğrular; grant tüketmez (validate before consume)."""
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "validate-only"}
    pending = request_confirmation("delete_task", scope, base_dir=tmp_path)
    result = check_confirmation(
        "delete_task",
        scope,
        {"confirmation_id": pending.confirmation_id, "base_dir": str(tmp_path)},
    )
    assert result.allowed
    grant_path = tmp_path / "pending_confirmations" / f"{pending.confirmation_id}.json"
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    assert grant.get("consumed") is not True
    assert consume_confirmation(pending.confirmation_id, pending.scope_hash, base_dir=tmp_path)


def test_consume_confirmation_expired_grant_fails(tmp_path: Path) -> None:
    """Süresi dolmuş grant consume edilemez."""
    scope = {"id": "exp-consume"}
    pending = request_confirmation("delete_permanent", scope, base_dir=tmp_path, ttl_seconds=1)
    grant_path = tmp_path / "pending_confirmations" / f"{pending.confirmation_id}.json"
    data = json.loads(grant_path.read_text(encoding="utf-8"))
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    data["expires_at"] = past.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    grant_path.write_text(json.dumps(data), encoding="utf-8")
    assert not consume_confirmation(pending.confirmation_id, pending.scope_hash, base_dir=tmp_path)


def test_consume_confirmation_unaffected_by_env_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """consume_confirmation env gate'e bakmaz — doğrudan grant mutasyonu (W1-03 karakterizasyon)."""
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    assert not is_confirmation_enabled()
    pending = request_confirmation("external_write", {"target": "mail"}, base_dir=tmp_path)
    assert consume_confirmation(pending.confirmation_id, pending.scope_hash, base_dir=tmp_path)


def test_consume_confirmation_unknown_id_fails(tmp_path: Path) -> None:
    assert not consume_confirmation("missing-id", "deadbeef", base_dir=tmp_path)


def test_bridge_shadow_grant_expired_blocks_check_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "exp bridge"}
    attach_bridge_pending_confirmation(
        pending,
        base_dir=lumos,
        risk="high",
        source="lumos_gate",
    )
    grant_path = lumos / "pending_confirmations" / f"{pending['confirmation_id']}.json"
    data = json.loads(grant_path.read_text(encoding="utf-8"))
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    data["expires_at"] = past.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    grant_path.write_text(json.dumps(data), encoding="utf-8")
    scope = data["scope"]
    result = check_confirmation(
        BRIDGE_HIGH_RISK_ACTION,
        scope,
        {"confirmation_id": pending["confirmation_id"], "base_dir": str(lumos)},
    )
    assert not result.allowed
    assert result.reason == REASON_CONFIRMATION_EXPIRED


def test_bridge_pending_cu4_fields_missing_returns_none() -> None:
    assert bridge_pending_cu4_fields({}) is None
    assert bridge_pending_cu4_fields({"confirmation_id": "abc"}) is None


def test_validate_bridge_confirmation_disabled_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "noop"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    result = validate_bridge_confirmation(pending, base_dir=lumos)
    assert result.allowed
    assert result.reason == REASON_CONFIRMATION_DISABLED


def test_validate_bridge_confirmation_legacy_no_shadow_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    legacy = {"schema_version": "lumos.pending_approval.v1", "title": "legacy only"}
    result = validate_bridge_confirmation(legacy, base_dir=tmp_path / ".lumos")
    assert result.allowed
    assert result.reason == ""


def test_validate_bridge_confirmation_enabled_valid_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "valid"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    result = validate_bridge_confirmation(pending, base_dir=lumos)
    assert result.allowed
    grant_path = lumos / "pending_confirmations" / f"{pending['confirmation_id']}.json"
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    assert grant.get("consumed") is not True


def test_validate_bridge_confirmation_does_not_consume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """validate before consume: validate_bridge_confirmation grant tüketmez."""
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "order"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    assert validate_bridge_confirmation(pending, base_dir=lumos).allowed
    cid = str(pending["confirmation_id"])
    grant_path = lumos / "pending_confirmations" / f"{cid}.json"
    assert json.loads(grant_path.read_text(encoding="utf-8")).get("consumed") is not True
    assert consume_bridge_confirmation(pending, base_dir=lumos)
    assert json.loads(grant_path.read_text(encoding="utf-8")).get("consumed") is True
    assert not consume_bridge_confirmation(pending, base_dir=lumos)


def test_consume_bridge_confirmation_unaffected_by_env_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "env off consume"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="medium", source="task_dispatch")
    assert consume_bridge_confirmation(pending, base_dir=lumos)
    grant_path = lumos / "pending_confirmations" / f"{pending['confirmation_id']}.json"
    assert json.loads(grant_path.read_text(encoding="utf-8")).get("consumed") is True


def test_consume_bridge_confirmation_wrong_scope_hash_fails(tmp_path: Path) -> None:
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    pending: dict = {"schema_version": "lumos.pending_approval.v1", "title": "bad hash"}
    attach_bridge_pending_confirmation(pending, base_dir=lumos, risk="high", source="lumos_gate")
    pending["confirmation_scope_hash"] = "deadbeefdeadbeef"
    assert not consume_bridge_confirmation(pending, base_dir=lumos)
