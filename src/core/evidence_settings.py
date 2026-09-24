"""Deployment-owned retention settings and durable, non-expiring local copies.

The authenticated panel may change customer capture only. Existing archives
are never removed, and audit capture cannot be disabled through this API.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from core.workspace_contract import CoreWriteForbidden, allow_write_to_core
from lumos_board.evidence_policy import EvidencePolicy


def _directory(base):
    return Path(base) / "evidence_archive"


def read_policy(base):
    profile = os.environ.get("LUMOS_DEPLOYMENT_PROFILE", "internal")
    policy = EvidencePolicy(profile=profile)
    if profile == "internal":
        return policy
    settings = _directory(base) / "preferences"
    if not settings.exists():
        return policy
    events = sorted(settings.glob("*.json"))
    if events:
        event = json.loads(events[-1].read_text(encoding="utf-8"))
        policy = policy.set_capture(event["capture_deleted_content"])
    return policy


def _save(base, category, record):
    directory = _directory(base) / category
    if not allow_write_to_core(base, directory, is_sandbox_mode=False):
        raise CoreWriteForbidden("Evidence archive write forbidden")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "-" + uuid4().hex + ".json"
    path = directory / name
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def set_capture(base, enabled):
    policy = read_policy(base).set_capture(enabled)
    _save(base, "preferences", {
        "schema": "lumos.wall.capture_preference.v1",
        "capture_deleted_content": policy.capture_deleted_content,
        "retention": policy.record_terms(datetime.now(timezone.utc), kind="audit", severity="ordinary"),
    })
    return policy


def archive_deleted_content(base, record):
    policy = read_policy(base)
    terms = policy.record_terms(datetime.now(timezone.utc), kind="deleted_content", severity="unknown")
    if terms is None:
        return None
    return _save(base, "deleted_content", {"retention": terms, "content": record})
