"""
PC remote bridge audit events — append-only ``.lumos/logs/audit_events.jsonl``.

No user content (URLs, typed text, file paths) — approval metadata only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_SCHEMA = "lumos.pc_remote_audit.v1"
AUDIT_FILENAME = "audit_events.jsonl"

EVENT_PENDING_CREATED = "pending_created"
EVENT_PENDING_APPROVED = "pending_approved"
EVENT_PENDING_REJECTED = "pending_rejected"
EVENT_STUB_EXECUTED = "stub_executed"
EVENT_PENDING_EXPIRED = "pending_expired"


def audit_events_path(repo_root: Path) -> Path:
    return (repo_root / ".lumos" / "logs" / AUDIT_FILENAME).resolve()


def append_pc_remote_audit(
    repo_root: Path,
    event: str,
    *,
    approval_id: str = "",
    command: str = "",
    status: str = "",
    error: str = "",
    requested_by: str = "",
    target_device: str = "",
    risk_level: str = "",
) -> None:
    """Write one redacted audit line; never raises on I/O failure."""
    entry: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": str(event or "").strip(),
        "approval_id": str(approval_id or "").strip(),
        "command": str(command or "").strip(),
        "status": str(status or "").strip(),
        "stub_only": True,
    }
    if error:
        entry["error"] = str(error)[:200]
    if requested_by:
        entry["requested_by"] = str(requested_by)[:120]
    if target_device:
        entry["target_device"] = str(target_device)[:64]
    if risk_level:
        entry["risk_level"] = str(risk_level)[:32]
    try:
        path = audit_events_path(repo_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        return


def read_audit_events(repo_root: Path) -> list[dict[str, Any]]:
    """Load audit JSONL for tests."""
    path = audit_events_path(repo_root)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except OSError:
        return []
    return out
