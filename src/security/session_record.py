"""CLI session observation. The file is not an unlock capability.

A matching, unexpired record still does not unlock. Only ``LockState.unlock``
with the root key changes the live session. The on-disk fields are a
correlation of that live session: expiry, pid, and an in-memory session id.
When the process dies, the witness is gone, or the lock write fails, the
file is not a current observation and it still grants nothing.
"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RECORD_NAME = "session_record.json"
SESSION_RECORD_TTL_SECONDS = 120
_FIELDS = ("unlocked", "updated_at", "expires_at", "pid", "session_id", "generation")
_FORBIDDEN = (
    "passphrase",
    "password",
    "secret",
    "token",
    "root_key",
    "private_key",
    "credential",
)
_CLOSED_SESSION_ID = "0" * 32

_WITNESSES: dict[int, "LiveSession"] = {}


@dataclass(frozen=True)
class LiveSession:
    """In-memory correlation for one unlocked LockState. Not a grant."""

    session_id: str
    pid: int
    generation: int
    bound_to: int


def bind_live_session(lock_state: Any) -> LiveSession:
    """Issue a new witness after a real unlock. A locked state cannot bind."""
    if not getattr(lock_state, "unlocked", False):
        raise RuntimeError("live session requires an unlocked LockState")
    previous = _WITNESSES.get(id(lock_state))
    generation = 1 if previous is None else previous.generation + 1
    live = LiveSession(
        session_id=secrets.token_hex(16),
        pid=os.getpid(),
        generation=generation,
        bound_to=id(lock_state),
    )
    _WITNESSES[id(lock_state)] = live
    return live


def invalidate_live_session(lock_state: Any) -> None:
    """Drop the witness before a lock file write. Failure to write cannot restore it."""
    _WITNESSES.pop(id(lock_state), None)


def discard_live_sessions() -> None:
    """Drop every witness. Used when the process image is gone."""
    _WITNESSES.clear()


def live_session_for(lock_state: Any) -> LiveSession | None:
    if lock_state is None or not getattr(lock_state, "unlocked", False):
        return None
    live = _WITNESSES.get(id(lock_state))
    if live is None or live.bound_to != id(lock_state) or live.pid != os.getpid():
        return None
    return live


def session_record_path(base_dir: str | Path) -> Path:
    base = Path(base_dir).resolve()
    path = base / RECORD_NAME
    if path.parent != base:
        raise ValueError("session record must stay inside the workspace")
    if path.is_symlink():
        raise OSError("session record path must not be a symlink")
    return path


def _stamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("updated_at requires a timezone")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_stamp(value: str) -> datetime:
    if len(value) != 20 or not value.endswith("Z"):
        raise ValueError("updated_at must be a UTC timestamp")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def build_session_record(
    unlocked: bool,
    *,
    live: LiveSession | None = None,
    now: datetime | None = None,
) -> dict[str, bool | str | int]:
    if type(unlocked) is not bool:
        raise TypeError("unlocked must be bool")
    moment = now if now is not None else datetime.now(timezone.utc)
    updated_at = _stamp(moment)
    if unlocked:
        if live is None or live.pid != os.getpid():
            raise RuntimeError("unlocked record requires the live process session")
        session_id = live.session_id
        pid = live.pid
        generation = live.generation
        expires = moment.astimezone(timezone.utc) + timedelta(seconds=SESSION_RECORD_TTL_SECONDS)
    else:
        if live is not None:
            raise RuntimeError("locked record must not carry a live session")
        session_id = _CLOSED_SESSION_ID
        pid = os.getpid()
        generation = 0
        expires = moment.astimezone(timezone.utc)
    return {
        "unlocked": unlocked,
        "updated_at": updated_at,
        "expires_at": _stamp(expires),
        "pid": pid,
        "session_id": session_id,
        "generation": generation,
    }


def validate_session_record(payload: dict) -> dict[str, bool | str | int]:
    if set(payload) != set(_FIELDS):
        raise ValueError("session record fields are not the observation schema")
    if type(payload["unlocked"]) is not bool:
        raise TypeError("unlocked must be bool")
    updated_at = payload["updated_at"]
    expires_at = payload["expires_at"]
    if type(updated_at) is not str or type(expires_at) is not str:
        raise ValueError("updated_at must be a UTC timestamp")
    _parse_stamp(updated_at)
    _parse_stamp(expires_at)
    pid = payload["pid"]
    generation = payload["generation"]
    session_id = payload["session_id"]
    if type(pid) is not int or isinstance(pid, bool) or pid <= 0:
        raise TypeError("pid must be a process id")
    if type(generation) is not int or isinstance(generation, bool) or generation < 0:
        raise TypeError("generation must be an integer")
    if type(session_id) is not str or len(session_id) != 32 or any(c not in "0123456789abcdef" for c in session_id):
        raise ValueError("session_id must be a correlation id")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    lowered = blob.lower()
    if any(word in lowered for word in _FORBIDDEN):
        raise ValueError("session record refused secret-like content")
    return {
        "unlocked": payload["unlocked"],
        "updated_at": updated_at,
        "expires_at": expires_at,
        "pid": pid,
        "session_id": session_id,
        "generation": generation,
    }


def record_grants_unlock(*_args: Any, **_kwargs: Any) -> bool:
    """The session file is never an unlock capability."""
    return False


def assess_session_record(
    base_dir: str | Path,
    *,
    lock_state: Any = None,
    now: datetime | None = None,
) -> str:
    """Classify the file. No result unlocks a LockState."""
    path = session_record_path(base_dir) if not (Path(base_dir).resolve() / RECORD_NAME).is_symlink() else None
    candidate = Path(base_dir).resolve() / RECORD_NAME
    if candidate.is_symlink() or path is None:
        return "corrupt"
    if not candidate.is_file():
        return "absent"
    try:
        payload = validate_session_record(json.loads(candidate.read_text(encoding="utf-8")))
        expires_at = _parse_stamp(str(payload["expires_at"]))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return "corrupt"
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("updated_at requires a timezone")
    if expires_at <= moment.astimezone(timezone.utc):
        return "expired"
    if payload["pid"] != os.getpid():
        return "foreign_process"
    live = live_session_for(lock_state)
    matches = (
        live is not None
        and live.session_id == payload["session_id"]
        and live.generation == payload["generation"]
        and live.pid == payload["pid"]
    )
    if not matches:
        if payload["unlocked"] is True and (lock_state is None or not getattr(lock_state, "unlocked", False)):
            return "superseded"
        return "foreign_process"
    if payload["unlocked"] is not True:
        return "not_current"
    return "observed_current"


def write_session_record(
    base_dir: str | Path,
    unlocked: bool,
    *,
    live: LiveSession | None = None,
    now: datetime | None = None,
) -> dict[str, bool | str | int]:
    payload = validate_session_record(build_session_record(unlocked, live=live, now=now))
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path = session_record_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.is_symlink():
        raise OSError("session record temp path must not be a symlink")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    return payload


def remove_session_record(base_dir: str | Path) -> None:
    """Unlink the record name. A symlink is removed without following it."""
    path = Path(base_dir).resolve() / RECORD_NAME
    if path.is_symlink() or path.exists():
        os.unlink(path)
