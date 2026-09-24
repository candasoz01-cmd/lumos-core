"""Append-only standing attestation ledger.

A factual/normative judgement is not standing authority until it is bound to
an actor, a head SHA, and the classified path set. CI never writes this
ledger and never invents the judgement (see standing-class.yml).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_SCHEMA = "lumos.standing_attestation.v1"
AUDIT_FILENAME = "standing_attestation.jsonl"
EVENT_STANDING_ATTESTATION = "standing_attestation"

ALLOWED_KEYS = (
    "schema_version",
    "timestamp",
    "event",
    "attest_by",
    "head_sha",
    "attest_sha",
    "verdict",
    "class",
    "standing_merge",
    "paths",
    "reasons",
)


def standing_attestation_log_path(base_dir: Path | None = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _lumos_base_dir()
    return (root / "logs" / AUDIT_FILENAME).resolve()


def append_standing_attestation(
    *,
    attest_by: str,
    head_sha: str,
    attest_sha: str,
    verdict: str,
    standing_class: str,
    paths: list[str] | tuple[str, ...],
    reasons: list[str] | tuple[str, ...] | None = None,
    standing_merge: bool,
    timestamp: datetime | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Append one attestation line. Raises OSError on I/O failure."""
    recorded_at = timestamp if timestamp is not None else datetime.now(timezone.utc)
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise ValueError("timestamp_must_be_timezone_aware")
    entry: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA,
        "timestamp": _to_iso(recorded_at),
        "event": EVENT_STANDING_ATTESTATION,
        "attest_by": _require_text("attest_by", attest_by),
        "head_sha": _require_text("head_sha", head_sha).lower(),
        "attest_sha": _require_text("attest_sha", attest_sha).lower(),
        "verdict": _require_text("verdict", verdict),
        "class": _require_text("class", standing_class),
        "standing_merge": bool(standing_merge),
        "paths": [str(item) for item in paths],
        "reasons": [str(item) for item in (reasons or ())],
    }
    if tuple(entry) != ALLOWED_KEYS:
        raise ValueError("standing_attestation_unexpected_fields")
    path = standing_attestation_log_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
    return entry


def read_standing_attestations(base_dir: Path | None = None) -> list[dict[str, Any]]:
    path = standing_attestation_log_path(base_dir)
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


def _lumos_base_dir() -> Path:
    raw = (os.environ.get("LUMOS_BASE_DIR") or ".lumos").strip()
    if not raw:
        raw = ".lumos"
    return Path(raw).expanduser().resolve()


def _require_text(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}_required")
    return value.strip()


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
