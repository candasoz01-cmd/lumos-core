from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from integrations.vault.access import (
    CredentialAccessDecision,
    CredentialAccessRequest,
    CredentialBinding,
    CredentialBindingKey,
    CredentialBindingStatus,
    evaluate_credential_access,
)


class CredentialBindingRegistry:
    """Secret içermeyen doğrulanmış hesap bağları için yerel kayıt deposu."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def upsert(self, binding: CredentialBinding) -> bool:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                INSERT INTO credential_bindings (
                    owner_id,
                    provider,
                    account_id,
                    purpose_code,
                    vault_ref,
                    granted_scopes,
                    verified_at,
                    expires_at,
                    verification_source,
                    status,
                    revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, provider, account_id, purpose_code) DO UPDATE SET
                    vault_ref = excluded.vault_ref,
                    granted_scopes = excluded.granted_scopes,
                    verified_at = excluded.verified_at,
                    expires_at = excluded.expires_at,
                    verification_source = excluded.verification_source,
                    status = excluded.status,
                    revoked_at = excluded.revoked_at
                WHERE excluded.verified_at > credential_bindings.verified_at
                   OR (
                       excluded.verified_at = credential_bindings.verified_at
                       AND excluded.vault_ref = credential_bindings.vault_ref
                   )
                """,
                (
                    binding.key.owner_id,
                    binding.key.provider,
                    binding.key.account_id,
                    binding.key.purpose_code,
                    binding.vault_ref,
                    json.dumps(sorted(binding.granted_scopes), separators=(",", ":")),
                    _to_storage_datetime(binding.verified_at),
                    _to_storage_datetime(binding.expires_at),
                    binding.verification_source,
                    binding.status.value,
                    _to_storage_datetime(binding.revoked_at) if binding.revoked_at else None,
                ),
            )
            return cursor.rowcount == 1

    def get(self, key: CredentialBindingKey) -> CredentialBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    vault_ref,
                    granted_scopes,
                    verified_at,
                    expires_at,
                    verification_source,
                    status,
                    revoked_at
                FROM credential_bindings
                WHERE owner_id = ? AND provider = ? AND account_id = ? AND purpose_code = ?
                """,
                (key.owner_id, key.provider, key.account_id, key.purpose_code),
            ).fetchone()
        if row is None:
            return None
        return CredentialBinding(
            key=key,
            vault_ref=str(row["vault_ref"]),
            granted_scopes=_parse_scopes(str(row["granted_scopes"])),
            verified_at=_parse_storage_datetime(str(row["verified_at"])),
            expires_at=_parse_storage_datetime(str(row["expires_at"])),
            verification_source=str(row["verification_source"]),
            status=CredentialBindingStatus(str(row["status"])),
            revoked_at=(
                _parse_storage_datetime(str(row["revoked_at"]))
                if row["revoked_at"] is not None
                else None
            ),
        )

    def evaluate(
        self,
        request: CredentialAccessRequest,
        *,
        now: datetime | None = None,
    ) -> CredentialAccessDecision:
        return evaluate_credential_access(self.get(request.key), request, now=now)

    def revoke(self, key: CredentialBindingKey, *, revoked_at: datetime | None = None) -> bool:
        effective_at = revoked_at or datetime.now(timezone.utc)
        if effective_at.tzinfo is None or effective_at.utcoffset() is None:
            raise ValueError("revoked_at_must_be_timezone_aware")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE credential_bindings
                SET status = ?, revoked_at = ?
                WHERE owner_id = ? AND provider = ? AND account_id = ? AND purpose_code = ?
                """,
                (
                    CredentialBindingStatus.REVOKED.value,
                    _to_storage_datetime(effective_at),
                    key.owner_id,
                    key.provider,
                    key.account_id,
                    key.purpose_code,
                ),
            )
            return cursor.rowcount == 1

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS credential_bindings (
                    owner_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    purpose_code TEXT NOT NULL,
                    vault_ref TEXT NOT NULL,
                    granted_scopes TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    verification_source TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    revoked_at TEXT,
                    PRIMARY KEY (owner_id, provider, account_id, purpose_code)
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_credential_binding_identity
                ON credential_bindings (owner_id, provider, account_id, purpose_code)
                """
            )
            connection.execute("PRAGMA journal_mode = WAL")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection


def _to_storage_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_storage_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored_datetime_must_be_timezone_aware")
    return parsed


def _parse_scopes(value: str) -> frozenset[str]:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("stored_scopes_invalid") from exc
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise ValueError("stored_scopes_invalid")
    return frozenset(decoded)
