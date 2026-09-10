"""F10: credential access/reuse decisions must leave a redacted audit trail.

On origin/main (9691c8a4) evaluate_credential_access and registry.evaluate
returned REUSE / REAUTHENTICATE / APPROVAL_REQUIRED / DENY with no JSONL and
no logs. After this patch they must record owner/provider/account/purpose,
action, reason, and timestamp — never vault_ref or secret.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.vault.access import (
    CredentialAccessAction,
    CredentialAccessRequest,
    CredentialBinding,
    CredentialBindingKey,
    CredentialBindingStatus,
    evaluate_credential_access,
)
from integrations.vault.access_audit import (
    ALLOWED_KEYS,
    AUDIT_SCHEMA,
    EVENT_CREDENTIAL_ACCESS,
    append_credential_access_audit,
    credential_access_audit_path,
    read_credential_access_audit,
)
from integrations.vault.purpose_codes import PURPOSE_GITHUB_METADATA_READ
from integrations.vault.registry import CredentialBindingRegistry

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
OWNER_ID = "lumos-owner-1"
READ_SCOPE = "github.repository.metadata.read"
VAULT_REF_CANARY = "opaque-ref-MUST-NOT-APPEAR-IN-AUDIT"
SECRET_CANARY = "ghu_SECRET_MUST_NOT_LEAK_123456"


@pytest.fixture(autouse=True)
def _isolate_audit_home(tmp_path, monkeypatch):
    base = tmp_path / ".lumos"
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    return base


def _key(*, owner_id: str = OWNER_ID, account_id: str = "account-1") -> CredentialBindingKey:
    return CredentialBindingKey(
        owner_id=owner_id,
        provider="github",
        account_id=account_id,
        purpose_code=PURPOSE_GITHUB_METADATA_READ,
    )


def _binding(
    *,
    account_id: str = "account-1",
    vault_ref: str = VAULT_REF_CANARY,
    verified_at: datetime = NOW,
    scopes: frozenset[str] = frozenset({READ_SCOPE}),
    status: CredentialBindingStatus = CredentialBindingStatus.ACTIVE,
    revoked_at: datetime | None = None,
) -> CredentialBinding:
    return CredentialBinding(
        key=_key(account_id=account_id),
        vault_ref=vault_ref,
        granted_scopes=scopes,
        verified_at=verified_at,
        expires_at=verified_at + timedelta(hours=8),
        verification_source="github_authenticated_user",
        status=status,
        revoked_at=revoked_at,
    )


def _request(
    *,
    account_id: str = "account-1",
    scopes: frozenset[str] = frozenset({READ_SCOPE}),
    consequential: bool = False,
) -> CredentialAccessRequest:
    return CredentialAccessRequest(
        key=_key(account_id=account_id),
        required_scopes=scopes,
        consequential=consequential,
    )


def _block_audit_log_dir(base: Path) -> None:
    logs = base / "logs"
    if logs.is_dir():
        for child in logs.iterdir():
            if child.is_file():
                child.unlink()
        logs.rmdir()
    logs.write_text("not-a-directory", encoding="utf-8")


def _assert_no_secret_leak(payload: object) -> None:
    blob = json.dumps(payload, default=str)
    assert VAULT_REF_CANARY not in blob
    assert SECRET_CANARY not in blob
    rows = payload if isinstance(payload, list) else [payload]
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = {str(key).lower() for key in row}
        assert "vault_ref" not in keys
        assert "secret" not in keys
        assert "secret_value" not in keys


def test_all_four_decisions_are_audited_with_identity_reason_and_time(_isolate_audit_home):
    cases = [
        (
            _binding(),
            _request(),
            NOW + timedelta(minutes=5),
            CredentialAccessAction.REUSE,
            "verified_context_reused",
        ),
        (
            None,
            _request(),
            NOW,
            CredentialAccessAction.REAUTHENTICATE,
            "credential_binding_missing",
        ),
        (
            _binding(account_id="account-1"),
            _request(account_id="account-2"),
            NOW + timedelta(minutes=1),
            CredentialAccessAction.DENY,
            "credential_binding_mismatch",
        ),
        (
            _binding(),
            _request(consequential=True),
            NOW + timedelta(minutes=1),
            CredentialAccessAction.APPROVAL_REQUIRED,
            "consequential_action_required",
        ),
    ]

    for binding, request, checked_at, action, reason in cases:
        evaluate_credential_access(binding, request, now=checked_at)

    records = read_credential_access_audit()
    assert len(records) == 4
    observed = [(row["action"], row["reason"]) for row in records]
    assert observed == [
        ("reuse", "verified_context_reused"),
        ("reauthenticate", "credential_binding_missing"),
        ("deny", "credential_binding_mismatch"),
        ("approval_required", "consequential_action_required"),
    ]
    for row, (_binding_arg, request, checked_at, action, reason) in zip(
        records, cases, strict=True
    ):
        assert tuple(row) == ALLOWED_KEYS
        assert row["schema_version"] == AUDIT_SCHEMA
        assert row["event"] == EVENT_CREDENTIAL_ACCESS
        assert row["owner_id"] == request.key.owner_id
        assert row["provider"] == request.key.provider
        assert row["account_id"] == request.key.account_id
        assert row["purpose_code"] == request.key.purpose_code
        assert row["action"] == action.value
        assert row["reason"] == reason
        assert row["timestamp"] == (
            checked_at.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        _assert_no_secret_leak(row)


def test_audit_record_never_contains_vault_ref_or_secret(_isolate_audit_home):
    evaluate_credential_access(
        _binding(vault_ref=VAULT_REF_CANARY),
        _request(),
        now=NOW + timedelta(minutes=5),
    )
    path = credential_access_audit_path()
    raw = path.read_text(encoding="utf-8")
    records = read_credential_access_audit()
    assert records
    _assert_no_secret_leak(records)
    assert VAULT_REF_CANARY not in raw
    assert SECRET_CANARY not in raw
    parsed = json.loads(raw.strip())
    assert "vault_ref" not in parsed
    assert "secret" not in parsed


def test_append_rejects_unexpected_secret_kwargs():
    with pytest.raises(TypeError):
        append_credential_access_audit(
            owner_id=OWNER_ID,
            provider="github",
            account_id="account-1",
            purpose_code=PURPOSE_GITHUB_METADATA_READ,
            action="reuse",
            reason="verified_context_reused",
            vault_ref=VAULT_REF_CANARY,
        )


def test_registry_evaluate_reuse_writes_the_same_audit_trail(tmp_path, _isolate_audit_home):
    registry = CredentialBindingRegistry(tmp_path / "bindings.sqlite3")
    assert registry.upsert(_binding()) is True
    decision = registry.evaluate(_request(), now=NOW + timedelta(minutes=5))
    records = read_credential_access_audit()
    assert decision.action is CredentialAccessAction.REUSE
    assert len(records) == 1
    assert records[0]["action"] == "reuse"
    assert records[0]["owner_id"] == OWNER_ID
    assert records[0]["account_id"] == "account-1"
    assert records[0]["purpose_code"] == PURPOSE_GITHUB_METADATA_READ
    _assert_no_secret_leak(records)
    with sqlite3.connect(tmp_path / "bindings.sqlite3") as connection:
        stored_ref = connection.execute("SELECT vault_ref FROM credential_bindings").fetchone()[0]
    assert stored_ref == VAULT_REF_CANARY
    assert stored_ref not in json.dumps(records)


def test_reuse_fail_closed_when_audit_io_fails(_isolate_audit_home):
    _block_audit_log_dir(_isolate_audit_home)
    with pytest.raises(OSError):
        evaluate_credential_access(_binding(), _request(), now=NOW + timedelta(minutes=5))
    assert read_credential_access_audit() == []


def test_consequential_access_fail_closed_when_audit_io_fails(_isolate_audit_home):
    _block_audit_log_dir(_isolate_audit_home)
    with pytest.raises(OSError):
        evaluate_credential_access(
            _binding(),
            _request(consequential=True),
            now=NOW + timedelta(minutes=1),
        )
    assert read_credential_access_audit() == []


def test_deny_and_reauthenticate_still_return_when_audit_io_fails(_isolate_audit_home):
    _block_audit_log_dir(_isolate_audit_home)
    denied = evaluate_credential_access(
        _binding(),
        _request(account_id="account-2"),
        now=NOW + timedelta(minutes=1),
    )
    missing = evaluate_credential_access(None, _request(), now=NOW)
    assert denied.action is CredentialAccessAction.DENY
    assert denied.reason == "credential_binding_mismatch"
    assert missing.action is CredentialAccessAction.REAUTHENTICATE
    assert missing.reason == "credential_binding_missing"
    assert read_credential_access_audit() == []


def test_non_consequential_approval_required_still_returns_when_audit_io_fails(_isolate_audit_home):
    _block_audit_log_dir(_isolate_audit_home)
    decision = evaluate_credential_access(
        _binding(),
        _request(scopes=frozenset({READ_SCOPE, "github.repository.contents.write"})),
        now=NOW + timedelta(minutes=1),
    )
    assert decision.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert decision.reason == "scope_expansion_required"
    assert read_credential_access_audit() == []
