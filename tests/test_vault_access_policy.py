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
from integrations.vault.registry import CredentialBindingRegistry


NOW = datetime(2026, 7, 19, 14, 0, tzinfo=timezone.utc)


def _key(*, account_id: str = "account-1", owner_id: str = "lumos-user-1") -> CredentialBindingKey:
    return CredentialBindingKey(
        owner_id=owner_id,
        provider="github",
        account_id=account_id,
        purpose_code="integration.github.repo.read",
    )


def _binding(*, account_id: str = "account-1", owner_id: str = "lumos-user-1") -> CredentialBinding:
    return CredentialBinding(
        key=_key(account_id=account_id, owner_id=owner_id),
        vault_ref=f"opaque-ref-{account_id}",
        granted_scopes=frozenset({"repo.read", "profile.read"}),
        verified_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=1),
        verification_source="oauth_callback",
    )


def _request(
    *,
    account_id: str = "account-1",
    owner_id: str = "lumos-user-1",
    scopes: frozenset[str] = frozenset({"repo.read"}),
    consequential: bool = False,
) -> CredentialAccessRequest:
    return CredentialAccessRequest(
        key=_key(account_id=account_id, owner_id=owner_id),
        required_scopes=scopes,
        consequential=consequential,
    )


def test_valid_low_risk_binding_is_reused_without_reauthentication():
    decision = evaluate_credential_access(_binding(), _request(), now=NOW)

    assert decision.action is CredentialAccessAction.REUSE
    assert decision.reusable is True
    assert decision.reason == "verified_context_reused"


def test_two_accounts_at_same_provider_do_not_collide():
    first = _binding(account_id="account-1")
    second = _binding(account_id="account-2")

    assert first.key != second.key
    decision = evaluate_credential_access(first, _request(account_id="account-2"), now=NOW)
    assert decision.action is CredentialAccessAction.DENY
    assert decision.reason == "credential_binding_mismatch"


def test_missing_or_expired_binding_requires_reauthentication():
    missing = evaluate_credential_access(None, _request(), now=NOW)
    expired_binding = CredentialBinding(
        key=_key(),
        vault_ref="opaque-ref-expired",
        granted_scopes=frozenset({"repo.read"}),
        verified_at=NOW - timedelta(hours=2),
        expires_at=NOW - timedelta(hours=1),
        verification_source="oauth_callback",
    )
    expired = evaluate_credential_access(expired_binding, _request(), now=NOW)

    assert missing.action is CredentialAccessAction.REAUTHENTICATE
    assert expired.action is CredentialAccessAction.REAUTHENTICATE
    assert expired.reason == "credential_expired"


def test_scope_expansion_and_consequential_action_require_approval():
    expanded = evaluate_credential_access(
        _binding(),
        _request(scopes=frozenset({"repo.read", "workflow.write"})),
        now=NOW,
    )
    consequential = evaluate_credential_access(
        _binding(),
        _request(consequential=True),
        now=NOW,
    )

    assert expanded.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert expanded.reason == "scope_expansion_required"
    assert consequential.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert consequential.reason == "consequential_action_required"


def test_public_metadata_never_exposes_vault_reference():
    binding = _binding()
    metadata = binding.public_metadata()

    assert "vault_ref" not in metadata
    assert "secret" not in str(metadata).lower()
    assert binding.vault_ref not in str(metadata)


def test_binding_requires_timezone_aware_verification_dates():
    with pytest.raises(ValueError, match="verified_at_must_be_timezone_aware"):
        CredentialBinding(
            key=_key(),
            vault_ref="opaque-ref",
            granted_scopes=frozenset({"repo.read"}),
            verified_at=datetime(2026, 7, 19, 14, 0),
            expires_at=NOW + timedelta(hours=1),
            verification_source="oauth_callback",
        )


def test_registry_persists_and_separates_multiple_accounts(tmp_path):
    database_path = tmp_path / "verified-context.sqlite3"
    registry = CredentialBindingRegistry(database_path)
    registry.upsert(_binding(account_id="account-1"))
    registry.upsert(_binding(account_id="account-2"))

    reopened = CredentialBindingRegistry(database_path)
    first = reopened.get(_key(account_id="account-1"))
    second = reopened.get(_key(account_id="account-2"))

    assert first is not None
    assert second is not None
    assert first.vault_ref == "opaque-ref-account-1"
    assert second.vault_ref == "opaque-ref-account-2"
    assert reopened.evaluate(_request(account_id="account-1"), now=NOW).reusable is True


def test_registry_schema_has_no_raw_secret_or_token_column(tmp_path):
    import sqlite3

    database_path = tmp_path / "verified-context.sqlite3"
    CredentialBindingRegistry(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(credential_bindings)").fetchall()
        }

    assert "secret" not in columns
    assert "secret_value" not in columns
    assert "access_token" not in columns
    assert "refresh_token" not in columns


def test_registry_has_named_unique_identity_index(tmp_path):
    import sqlite3

    database_path = tmp_path / "verified-context.sqlite3"
    CredentialBindingRegistry(database_path)

    with sqlite3.connect(database_path) as connection:
        indexes = connection.execute("PRAGMA index_list(credential_bindings)").fetchall()
        unique_names = {str(row[1]) for row in indexes if int(row[2]) == 1}
        columns = [
            str(row[2])
            for row in connection.execute(
                "PRAGMA index_info(uq_credential_binding_identity)"
            ).fetchall()
        ]

    assert "uq_credential_binding_identity" in unique_names
    assert columns == ["owner_id", "provider", "account_id", "purpose_code"]


def test_concurrent_upserts_keep_one_row_and_newest_verification(tmp_path):
    import sqlite3

    database_path = tmp_path / "verified-context.sqlite3"
    CredentialBindingRegistry(database_path)

    def write_binding(offset: int) -> bool:
        binding = CredentialBinding(
            key=_key(),
            vault_ref=f"opaque-ref-{offset}",
            granted_scopes=frozenset({"repo.read"}),
            verified_at=NOW + timedelta(seconds=offset),
            expires_at=NOW + timedelta(hours=2, seconds=offset),
            verification_source="oauth_callback",
        )
        return CredentialBindingRegistry(database_path).upsert(binding)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_binding, reversed(range(20))))

    registry = CredentialBindingRegistry(database_path)
    stored = registry.get(_key())
    with sqlite3.connect(database_path) as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM credential_bindings").fetchone()[0]

    assert row_count == 1
    assert stored is not None
    assert stored.vault_ref == "opaque-ref-19"
    assert stored.verified_at == NOW + timedelta(seconds=19)


def test_revoked_binding_requires_fresh_approval(tmp_path):
    registry = CredentialBindingRegistry(tmp_path / "verified-context.sqlite3")
    registry.upsert(_binding())
    assert registry.revoke(_key(), revoked_at=NOW) is True

    stored = registry.get(_key())
    decision = registry.evaluate(_request(), now=NOW)

    assert stored is not None
    assert stored.status is CredentialBindingStatus.REVOKED
    assert decision.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert decision.reason == "credential_revoked_approval_required"
