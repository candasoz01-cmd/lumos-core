"""Duvar onay şeması v1 kayıt deposu testleri (lumos-wall-v1 § Onay şeması v1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lumos_board.claim_cli import main as claim_cli_main
from lumos_board.founder_approval import (
    FOUNDER_APPROVAL_EVENT_SCHEMA,
    FOUNDER_APPROVER_REGISTRY_SCHEMA,
    FounderApprovalStore,
    FounderApproverRegistry,
)
from lumos_board.task_claim import ClaimError, ClaimStoreCorrupt


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
KEY = {
    "task": "TD-EX-01",
    "gate": "FOUNDER_REVIEW",
    "action": "merge PR #999",
    "head_sha": "a" * 40,
}


def _registry(tmp_path: Path, *approver_ids: str) -> FounderApproverRegistry:
    path = tmp_path / "founder_approvers.json"
    path.write_text(
        json.dumps(
            {
                "schema": FOUNDER_APPROVER_REGISTRY_SCHEMA,
                "approvers": [
                    {
                        "approver_id": approver_id,
                        "enabled": True,
                        "valid_until": "2027-01-01T00:00:00Z",
                    }
                    for approver_id in (approver_ids or ("candasoz",))
                ],
            }
        ),
        encoding="utf-8",
    )
    return FounderApproverRegistry.from_registry_file(path)


def _store(tmp_path: Path, registry: FounderApproverRegistry | None = None) -> FounderApprovalStore:
    return FounderApprovalStore(tmp_path / "board", clock=lambda: NOW, registry=registry)


def test_request_creates_pending_record_with_all_six_fields(tmp_path: Path) -> None:
    store = _store(tmp_path)
    approval = store.request(**KEY)
    record = approval.to_dict()
    for field in ("approval_id", "task", "gate", "action", "head_sha", "approved_by"):
        assert field in record, field
    assert approval.approved_by is None
    assert not approval.is_approved


def test_grant_requires_fail_closed_registry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    approval = store.request(**KEY)
    with pytest.raises(ClaimError, match="registry yapılandırılmamış"):
        store.grant(approval.approval_id, approved_by="candasoz")
    assert store.check(**KEY) is None


def test_grant_records_human_approval_and_check_finds_it(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    granted = store.grant(approval.approval_id, approved_by="candasoz")
    assert granted.approved_by == "candasoz"
    assert granted.approved_at == NOW
    found = store.check(**KEY)
    assert found is not None and found.approval_id == approval.approval_id


def test_same_valid_approval_is_not_asked_again(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    store.grant(approval.approval_id, approved_by="candasoz")
    again = store.request(**KEY)
    assert again.approval_id == approval.approval_id
    assert again.is_approved


def test_new_head_sha_resets_the_approval(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    store.grant(approval.approval_id, approved_by="candasoz")
    new_key = {**KEY, "head_sha": "b" * 40}
    assert store.check(**new_key) is None
    fresh = store.request(**new_key)
    assert fresh.approval_id != approval.approval_id
    assert not fresh.is_approved


def test_different_gate_or_action_is_a_new_record(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    store.grant(approval.approval_id, approved_by="candasoz")
    assert store.check(**{**KEY, "action": "deploy"}) is None
    assert store.check(**{**KEY, "gate": "merge-gate-3"}) is None


def test_bot_and_app_identities_cannot_fill_approved_by(tmp_path: Path) -> None:
    registry = _registry(tmp_path, "candasoz", "release[bot]", "app/lumos-approver")
    store = _store(tmp_path, registry)
    for fake_human in ("release[bot]", "app/lumos-approver"):
        approval = store.request(**{**KEY, "task": f"TD-{fake_human}"})
        with pytest.raises(ClaimError, match="bot/App kimliği kabul edilmez"):
            store.grant(approval.approval_id, approved_by=fake_human)


def test_non_allowlisted_or_expired_approver_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    with pytest.raises(ClaimError, match="allowlist"):
        store.grant(approval.approval_id, approved_by="someone-else")
    expired_path = tmp_path / "expired.json"
    expired_path.write_text(
        json.dumps(
            {
                "schema": FOUNDER_APPROVER_REGISTRY_SCHEMA,
                "approvers": [
                    {"approver_id": "candasoz", "enabled": True, "valid_until": "2026-01-01T00:00:00Z"}
                ],
            }
        ),
        encoding="utf-8",
    )
    expired_store = FounderApprovalStore(
        tmp_path / "board",
        clock=lambda: NOW,
        registry=FounderApproverRegistry.from_registry_file(expired_path),
    )
    with pytest.raises(ClaimError, match="allowlist"):
        expired_store.grant(approval.approval_id, approved_by="candasoz")


def test_granted_record_cannot_be_granted_again(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    store.grant(approval.approval_id, approved_by="candasoz")
    with pytest.raises(ClaimError, match="zaten kapatılmış"):
        store.grant(approval.approval_id, approved_by="candasoz")


def test_audit_trail_is_append_only_and_survives_reload(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    store.grant(approval.approval_id, approved_by="candasoz")
    events = [
        json.loads(line)
        for line in store.audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event"] for event in events] == ["APPROVAL_REQUESTED", "APPROVAL_GRANTED"]
    assert all(event["schema"] == FOUNDER_APPROVAL_EVENT_SCHEMA for event in events)
    reloaded = FounderApprovalStore(tmp_path / "board", clock=lambda: NOW)
    found = reloaded.check(**KEY)
    assert found is not None and found.approved_by == "candasoz"


def test_failed_grant_leaves_no_audit_trace(tmp_path: Path) -> None:
    store = _store(tmp_path, _registry(tmp_path, "candasoz"))
    approval = store.request(**KEY)
    with pytest.raises(ClaimError):
        store.grant(approval.approval_id, approved_by="someone-else")
    events = store.audit_path.read_text(encoding="utf-8").splitlines()
    assert len(events) == 1  # yalnız APPROVAL_REQUESTED


def test_corrupt_store_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.request(**KEY)
    store.state_path.write_text("{bozuk", encoding="utf-8")
    with pytest.raises(ClaimStoreCorrupt):
        store.check(**KEY)


def test_empty_registry_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(
        json.dumps({"schema": FOUNDER_APPROVER_REGISTRY_SCHEMA, "approvers": []}),
        encoding="utf-8",
    )
    with pytest.raises(ClaimError, match="boş olamaz"):
        FounderApproverRegistry.from_registry_file(path)


def test_cli_real_flow_request_check_grant(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_arg = ["--store", str(tmp_path / "board")]
    key_args = [
        "--task", "TD-EX-01",
        "--gate", "FOUNDER_REVIEW",
        "--action", "merge PR #999",
        "--head-sha", "a" * 40,
    ]
    assert claim_cli_main([*store_arg, "approval", "request", *key_args]) == 0
    requested = json.loads(capsys.readouterr().out)
    assert requested["already_approved"] is False
    approval_id = requested["approval"]["approval_id"]

    # Onay yokken check fail-closed exit 2 döner.
    assert claim_cli_main([*store_arg, "approval", "check", *key_args]) == 2
    assert json.loads(capsys.readouterr().out) == {"approved": False}

    # Registry env'i yokken grant reddedilir.
    monkeypatch.delenv("LUMOS_FOUNDER_APPROVER_REGISTRY", raising=False)
    assert claim_cli_main([*store_arg, "approval", "grant", approval_id, "--approved-by", "candasoz"]) == 2
    assert "error" in json.loads(capsys.readouterr().out)

    registry_path = tmp_path / "founder_approvers.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema": FOUNDER_APPROVER_REGISTRY_SCHEMA,
                "approvers": [
                    {"approver_id": "candasoz", "enabled": True, "valid_until": "2027-01-01T00:00:00Z"}
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LUMOS_FOUNDER_APPROVER_REGISTRY", str(registry_path))
    assert claim_cli_main([*store_arg, "approval", "grant", approval_id, "--approved-by", "candasoz"]) == 0
    granted = json.loads(capsys.readouterr().out)
    assert granted["approved_by"] == "candasoz"

    assert claim_cli_main([*store_arg, "approval", "check", *key_args]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["approved"] is True
    assert checked["approval"]["approval_id"] == approval_id

    # Aynı geçerli onay tekrar sorulmaz: request mevcut kaydı döndürür.
    assert claim_cli_main([*store_arg, "approval", "request", *key_args]) == 0
    again = json.loads(capsys.readouterr().out)
    assert again["already_approved"] is True
    assert again["approval"]["approval_id"] == approval_id

    assert claim_cli_main([*store_arg, "approval", "list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert len(listed["approvals"]) == 1
