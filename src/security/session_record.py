"""CLI session record: unlocked flag and timestamp only.

The panel does not read this file. The record never carries a passphrase,
root key, or any other secret.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

RECORD_NAME = "session_record.json"
_FIELDS = ("unlocked", "updated_at")
_FORBIDDEN = (
    "passphrase",
    "password",
    "secret",
    "token",
    "root_key",
    "private_key",
    "credential",
)


def session_record_path(base_dir: str | Path) -> Path:
    base = Path(base_dir).resolve()
    path = base / RECORD_NAME
    if path.parent != base:
        raise ValueError("session record must stay inside the workspace")
    if path.is_symlink():
        raise OSError("session record path must not be a symlink")
    return path


def build_session_record(unlocked: bool, *, now: datetime | None = None) -> dict[str, bool | str]:
    if type(unlocked) is not bool:
        raise TypeError("unlocked must be bool")
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("updated_at requires a timezone")
    stamp = moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"unlocked": unlocked, "updated_at": stamp}


def validate_session_record(payload: dict) -> dict[str, bool | str]:
    if set(payload) != set(_FIELDS):
        raise ValueError("session record allows only unlocked and updated_at")
    if type(payload["unlocked"]) is not bool:
        raise TypeError("unlocked must be bool")
    stamp = payload["updated_at"]
    if type(stamp) is not str or not stamp.endswith("Z"):
        raise ValueError("updated_at must be a UTC timestamp")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    lowered = blob.lower()
    if any(word in lowered for word in _FORBIDDEN):
        raise ValueError("session record refused secret-like content")
    return {"unlocked": payload["unlocked"], "updated_at": stamp}


def write_session_record(
    base_dir: str | Path,
    unlocked: bool,
    *,
    now: datetime | None = None,
) -> dict[str, bool | str]:
    payload = validate_session_record(build_session_record(unlocked, now=now))
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path = session_record_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.is_symlink():
        raise OSError("session record temp path must not be a symlink")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    return payload
