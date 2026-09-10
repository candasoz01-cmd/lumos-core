"""F7: granted_by must come from a trusted actor, not client/disk spoof.

Characterization: these tests fail on origin/main (consume omits actor and
preserves a spoofed granted_by already sitting on the grant JSON).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from policy.confirmation_policy import (
    GRANTED_BY_BRIDGE,
    GRANTED_BY_CLI,
    GRANTED_BY_PANEL,
    consume_confirmation,
    ensure_cli_mutation_confirmation,
    ensure_panel_mutation_confirmation,
    request_confirmation,
)


def _grant_path(base: Path, confirmation_id: str) -> Path:
    return base / "pending_confirmations" / f"{confirmation_id}.json"


def _read_grant(base: Path, confirmation_id: str) -> dict:
    return json.loads(_grant_path(base, confirmation_id).read_text(encoding="utf-8"))


def test_request_records_granted_by_none(tmp_path: Path) -> None:
    pending = request_confirmation("create_task", {"title": "x"}, base_dir=tmp_path)
    grant = _read_grant(tmp_path, pending.confirmation_id)
    assert grant.get("granted_by") is None
    assert grant.get("consumed") is False


def test_consume_omitted_granted_by_fail_closed(tmp_path: Path) -> None:
    pending = request_confirmation("delete_task", {"id": "1"}, base_dir=tmp_path)
    assert consume_confirmation(
        pending.confirmation_id,
        pending.scope_hash,
        base_dir=tmp_path,
    ) is False
    grant = _read_grant(tmp_path, pending.confirmation_id)
    assert grant.get("consumed") is False
    assert grant.get("granted_by") is None


def test_consume_client_spoofed_granted_by_rejected(tmp_path: Path) -> None:
    pending = request_confirmation("delete_task", {"id": "1"}, base_dir=tmp_path)
    assert consume_confirmation(
        pending.confirmation_id,
        pending.scope_hash,
        base_dir=tmp_path,
        granted_by="founder",
    ) is False
    grant = _read_grant(tmp_path, pending.confirmation_id)
    assert grant.get("consumed") is False
    assert grant.get("granted_by") is None


def test_disk_spoofed_granted_by_is_overwritten_not_trusted(tmp_path: Path) -> None:
    pending = request_confirmation("create_task", {"title": "x"}, base_dir=tmp_path)
    path = _grant_path(tmp_path, pending.confirmation_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["granted_by"] = "founder"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert consume_confirmation(
        pending.confirmation_id,
        pending.scope_hash,
        base_dir=tmp_path,
        granted_by=GRANTED_BY_CLI,
    ) is True
    grant = _read_grant(tmp_path, pending.confirmation_id)
    assert grant.get("consumed") is True
    assert grant.get("granted_by") == GRANTED_BY_CLI
    assert grant.get("granted_by") != "founder"


def test_panel_body_granted_by_is_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"title": "x"}
    pending = request_confirmation("create_task", scope, base_dir=tmp_path)
    result = ensure_panel_mutation_confirmation(
        "create_task",
        scope,
        {
            "confirmation_id": pending.confirmation_id,
            "granted_by": "founder",
        },
        base_dir=tmp_path,
    )
    assert result.allowed
    grant = _read_grant(tmp_path, pending.confirmation_id)
    assert grant.get("granted_by") == GRANTED_BY_PANEL


def test_cli_consume_records_cli_confirm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "7"}
    pending = request_confirmation("delete_task", scope, base_dir=tmp_path)
    result = ensure_cli_mutation_confirmation(
        "delete_task",
        scope,
        pending.confirmation_id,
        base_dir=tmp_path,
    )
    assert result.allowed
    grant = _read_grant(tmp_path, pending.confirmation_id)
    assert grant.get("granted_by") == GRANTED_BY_CLI


def test_trusted_consume_sets_granted_by(tmp_path: Path) -> None:
    pending = request_confirmation("external_write", {"target": "mail"}, base_dir=tmp_path)
    assert consume_confirmation(
        pending.confirmation_id,
        pending.scope_hash,
        base_dir=tmp_path,
        granted_by=GRANTED_BY_BRIDGE,
    ) is True
    grant = _read_grant(tmp_path, pending.confirmation_id)
    assert grant.get("granted_by") == GRANTED_BY_BRIDGE
    assert grant.get("consumed") is True
