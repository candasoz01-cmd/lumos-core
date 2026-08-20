import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
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
from integrations.vault.purpose_codes import PURPOSE_GITHUB_METADATA_READ
from integrations.vault.registry import CredentialBindingRegistry

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
OWNER_ID = "lumos-owner-1"
READ_SCOPE = "github.repository.metadata.read"


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
    vault_ref: str = "opaque-ref-1",
    verified_at: datetime = NOW,
    scopes: frozenset[str] = frozenset({READ_SCOPE}),
) -> CredentialBinding:
    return CredentialBinding(
        key=_key(account_id=account_id),
        vault_ref=vault_ref,
        granted_scopes=scopes,
        verified_at=verified_at,
        expires_at=verified_at + timedelta(hours=8),
        verification_source="github_authenticated_user",
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


def test_valid_low_risk_binding_is_reused_without_reauthentication():
    decision = evaluate_credential_access(_binding(), _request(), now=NOW + timedelta(minutes=5))

    assert decision.action is CredentialAccessAction.REUSE
    assert decision.reusable is True
    assert decision.reason == "verified_context_reused"


def test_two_accounts_at_same_provider_do_not_collide():
    first = _binding(account_id="account-1")
    second_request = _request(account_id="account-2")

    decision = evaluate_credential_access(first, second_request, now=NOW + timedelta(minutes=1))

    assert first.key != second_request.key
    assert decision.action is CredentialAccessAction.DENY
    assert decision.reason == "credential_binding_mismatch"


def test_missing_or_expired_binding_requires_reauthentication():
    missing = evaluate_credential_access(None, _request(), now=NOW)
    expired = evaluate_credential_access(_binding(), _request(), now=NOW + timedelta(hours=9))

    assert missing.action is CredentialAccessAction.REAUTHENTICATE
    assert missing.reason == "credential_binding_missing"
    assert expired.action is CredentialAccessAction.REAUTHENTICATE
    assert expired.reason == "credential_expired"


def test_scope_expansion_and_consequential_action_require_approval():
    expanded = evaluate_credential_access(
        _binding(),
        _request(scopes=frozenset({READ_SCOPE, "github.repository.contents.write"})),
        now=NOW + timedelta(minutes=1),
    )
    consequential = evaluate_credential_access(
        _binding(),
        _request(consequential=True),
        now=NOW + timedelta(minutes=1),
    )

    assert expanded.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert expanded.reason == "scope_expansion_required"
    assert consequential.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert consequential.reason == "consequential_action_required"


def test_public_metadata_never_exposes_vault_reference():
    binding = _binding(vault_ref="opaque-ref-must-stay-hidden")

    metadata = binding.public_metadata()

    assert "vault_ref" not in metadata
    assert "secret" not in str(metadata).lower()
    assert binding.vault_ref not in str(metadata)
    assert metadata["status"] == "active"


def test_binding_requires_timezone_aware_verification_dates():
    with pytest.raises(ValueError, match="verified_at_must_be_timezone_aware"):
        CredentialBinding(
            key=_key(),
            vault_ref="opaque-ref-1",
            granted_scopes=frozenset({READ_SCOPE}),
            verified_at=datetime(2026, 8, 20, 12, 0),
            expires_at=NOW + timedelta(hours=1),
            verification_source="github_authenticated_user",
        )


def test_registry_persists_and_separates_multiple_accounts(tmp_path):
    registry = CredentialBindingRegistry(tmp_path / "bindings.sqlite3")
    assert registry.upsert(_binding(account_id="account-1", vault_ref="opaque-ref-account-1"))
    assert registry.upsert(_binding(account_id="account-2", vault_ref="opaque-ref-account-2"))

    first = registry.get(_key(account_id="account-1"))
    second = registry.get(_key(account_id="account-2"))
    reopened = CredentialBindingRegistry(tmp_path / "bindings.sqlite3")

    assert first is not None
    assert second is not None
    assert first.vault_ref == "opaque-ref-account-1"
    assert second.vault_ref == "opaque-ref-account-2"
    assert reopened.evaluate(_request(account_id="account-1"), now=NOW).reusable is True


def test_registry_schema_has_no_raw_secret_or_token_column(tmp_path):
    CredentialBindingRegistry(tmp_path / "bindings.sqlite3")

    with sqlite3.connect(tmp_path / "bindings.sqlite3") as connection:
        columns = [
            str(row[1]).lower()
            for row in connection.execute("PRAGMA table_info(credential_bindings)")
        ]

    assert "secret" not in columns
    assert "secret_value" not in columns
    assert "access_token" not in columns
    assert "refresh_token" not in columns
    assert "vault_ref" in columns


def test_registry_has_named_unique_identity_index(tmp_path):
    CredentialBindingRegistry(tmp_path / "bindings.sqlite3")

    with sqlite3.connect(tmp_path / "bindings.sqlite3") as connection:
        indexes = list(connection.execute("PRAGMA index_list(credential_bindings)"))
        unique_names = {str(row[1]) for row in indexes if row[2]}
        columns = [
            str(row[2])
            for row in connection.execute(
                "PRAGMA index_info(uq_credential_binding_identity)"
            )
        ]

    assert "uq_credential_binding_identity" in unique_names
    assert columns == ["owner_id", "provider", "account_id", "purpose_code"]


def test_concurrent_upserts_keep_one_row_and_newest_verification(tmp_path):
    registry = CredentialBindingRegistry(tmp_path / "bindings.sqlite3")

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(
            executor.map(
                lambda index: registry.upsert(
                    _binding(
                        vault_ref=f"opaque-ref-{index}",
                        verified_at=NOW + timedelta(seconds=index),
                    )
                ),
                range(20),
            )
        )

    stored = registry.get(_key())
    with sqlite3.connect(tmp_path / "bindings.sqlite3") as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM credential_bindings").fetchone()[0]

    assert row_count == 1
    assert stored is not None
    assert stored.vault_ref == "opaque-ref-19"
    assert stored.verified_at == NOW + timedelta(seconds=19)


def test_revoked_binding_requires_fresh_approval(tmp_path):
    registry = CredentialBindingRegistry(tmp_path / "bindings.sqlite3")
    assert registry.upsert(_binding()) is True

    assert registry.revoke(_key(), revoked_at=NOW) is True
    stored = registry.get(_key())
    decision = registry.evaluate(_request(), now=NOW + timedelta(minutes=1))

    assert stored is not None
    assert stored.status is CredentialBindingStatus.REVOKED
    assert decision.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert decision.reason == "credential_revoked_approval_required"
