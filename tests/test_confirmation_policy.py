"""CU4 confirmation_policy unit tests (PR-C1)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from policy.confirmation_policy import (
    REASON_CONFIRMATION_DISABLED,
    REASON_CONFIRMATION_EXPIRED,
    REASON_CONFIRMATION_REQUIRED,
    REASON_SCOPE_MISMATCH,
    REQUIRES_CONFIRMATION_ACTIONS,
    check_confirmation,
    consume_confirmation,
    ensure_delete_permanent_confirmation,
    ensure_cli_mutation_confirmation,
    ensure_panel_mutation_confirmation,
    is_confirmation_enabled,
    request_confirmation,
    requires_confirmation_for_action,
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
