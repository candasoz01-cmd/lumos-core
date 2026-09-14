"""Credential access-decision audit — append-only JSONL, no secrets.

Writes ``<LUMOS_BASE_DIR>/logs/credential_access.jsonl``. Raises ``OSError``
on I/O failure so reuse / consequential callers can fail closed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.lumos_base_dir import lumos_base_dir

AUDIT_SCHEMA = "lumos.credential_access_audit.v1"
AUDIT_FILENAME = "credential_access.jsonl"
EVENT_CREDENTIAL_ACCESS = "credential_access_decision"

ALLOWED_ACTIONS = frozenset({"reuse", "reauthenticate", "approval_required", "deny"})
ALLOWED_KEYS = (
    "schema_version",
    "timestamp",
    "event",
    "owner_id",
    "provider",
    "account_id",
    "purpose_code",
    "action",
    "reason",
)
FORBIDDEN_KEY_TOKENS = frozenset(
    {
        "vault_ref",
        "secret",
        "secret_value",
        "secretvalue",
        "access_token",
        "refresh_token",
        "token",
        "password",
        "credential",
    }
)


def credential_access_audit_path(base_dir: Path | None = None) -> Path:
    root = Path(base_dir) if base_dir is not None else lumos_base_dir()
    return (root / "logs" / AUDIT_FILENAME).resolve()


def append_credential_access_audit(
    *,
    owner_id: str,
    provider: str,
    account_id: str,
    purpose_code: str,
    action: str,
    reason: str,
    timestamp: datetime | None = None,
    base_dir: Path | None = None,
) -> None:
    """Write one redacted access-decision line.

    Raises OSError on I/O failure. Never accepts or emits ``vault_ref`` or secret.
    """
    recorded_at = timestamp if timestamp is not None else datetime.now(timezone.utc)
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise ValueError("timestamp_must_be_timezone_aware")
    action_value = _require_text("action", action)
    if action_value not in ALLOWED_ACTIONS:
        raise ValueError("credential_access_action_unknown")
    entry: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA,
        "timestamp": _to_iso(recorded_at),
        "event": EVENT_CREDENTIAL_ACCESS,
        "owner_id": _require_text("owner_id", owner_id),
        "provider": _require_text("provider", provider),
        "account_id": _require_text("account_id", account_id),
        "purpose_code": _require_text("purpose_code", purpose_code),
        "action": action_value,
        "reason": _require_text("reason", reason),
    }
    _reject_forbidden_fields(entry)
    path = credential_access_audit_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    _reject_forbidden_payload(line)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def read_credential_access_audit(base_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load audit JSONL for tests."""
    path = credential_access_audit_path(base_dir)
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _require_text(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}_required")
    return value.strip()


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _reject_forbidden_fields(entry: dict[str, Any]) -> None:
    if tuple(entry) != ALLOWED_KEYS:
        raise ValueError("credential_audit_unexpected_fields")
    for key in entry:
        normalized = key.strip().lower().replace("-", "_")
        if normalized in FORBIDDEN_KEY_TOKENS or "vault_ref" in normalized:
            raise ValueError("credential_audit_forbidden_field")


def _reject_forbidden_payload(line: str) -> None:
    lowered = line.lower()
    if '"vault_ref"' in lowered or '"secret"' in lowered or '"secret_value"' in lowered:
        raise ValueError("credential_audit_forbidden_field")
