"""L2: the session file correlates a live unlock. It never grants one."""
from __future__ import annotations

import inspect
import json
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from security.lock import LockState
from security.session_record import (
    SESSION_RECORD_TTL_SECONDS,
    assess_session_record,
    bind_live_session,
    build_session_record,
    discard_live_sessions,
    invalidate_live_session,
    record_grants_unlock,
    remove_session_record,
    validate_session_record,
    write_session_record,
)

_PASSPHRASE = "correct-horse-battery-passphrase"
_STAMP = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
_FIELDS = {"unlocked", "updated_at", "expires_at", "pid", "session_id", "generation"}


def _open(now: datetime = _STAMP) -> tuple[LockState, object]:
    state = LockState()
    state.unlock(b"\x03" * 32)
    return state, bind_live_session(state)


def test_record_carries_expiry_and_process_correlation(tmp_path: Path):
    state, live = _open()
    payload = write_session_record(tmp_path, True, live=live, now=_STAMP)
    assert set(payload) == _FIELDS
    assert payload["unlocked"] is True
    assert payload["updated_at"] == "2026-11-20T12:00:00Z"
    assert payload["expires_at"] == "2026-11-20T12:02:00Z"
    assert payload["pid"] == os.getpid()
    assert payload["generation"] == 1
    raw = (tmp_path / "session_record.json").read_text(encoding="utf-8")
    assert json.loads(raw) == payload
    assert _PASSPHRASE not in raw
    assert b"\x03" not in (tmp_path / "session_record.json").read_bytes()
    shifted = build_session_record(
        True,
        live=live,
        now=datetime(2026, 11, 20, 15, 0, tzinfo=timezone(timedelta(hours=3))),
    )
    assert shifted["updated_at"] == "2026-11-20T12:00:00Z"
    assert assess_session_record(tmp_path, lock_state=state, now=_STAMP) == "observed_current"
    assert record_grants_unlock(payload, lock_state=state) is False
    assert "return True" not in inspect.getsource(record_grants_unlock)


def test_record_file_mode_is_owner_only(tmp_path: Path):
    _state, live = _open()
    old = os.umask(0)
    try:
        write_session_record(tmp_path, True, live=live, now=_STAMP)
    finally:
        os.umask(old)
    path = tmp_path / "session_record.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not path.with_name(path.name + ".tmp").exists()


def test_non_bool_and_secret_fields_are_rejected():
    _state, live = _open()
    for value in (1, "true", None):
        with pytest.raises(TypeError):
            build_session_record(value, live=live, now=_STAMP)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_session_record({"unlocked": True, "updated_at": "2026-11-20T12:00:00Z"})
    with pytest.raises(RuntimeError):
        build_session_record(True, live=None, now=_STAMP)
    with pytest.raises(RuntimeError):
        build_session_record(False, live=live, now=_STAMP)


def test_symlink_record_is_not_followed(tmp_path: Path):
    _state, live = _open()
    outside = tmp_path / "outside.json"
    outside.write_text("original", encoding="utf-8")
    base = tmp_path / "workspace"
    base.mkdir()
    record = base / "session_record.json"
    record.symlink_to(outside)
    with pytest.raises(OSError, match="must not be a symlink"):
        write_session_record(base, True, live=live, now=_STAMP)
    assert outside.read_text(encoding="utf-8") == "original"
    assert assess_session_record(base, lock_state=_state, now=_STAMP) == "corrupt"
    remove_session_record(base)
    assert outside.read_text(encoding="utf-8") == "original"
    assert not record.exists()


def test_file_alone_does_not_unlock(tmp_path: Path):
    state, live = _open()
    write_session_record(tmp_path, True, live=live, now=_STAMP)
    fresh = LockState()
    assert record_grants_unlock(tmp_path, lock_state=fresh) is False
    assert fresh.unlocked is False
    assert assess_session_record(tmp_path, lock_state=fresh, now=_STAMP) == "superseded"
    assert state.unlocked is True


def test_expired_record_is_not_authority(tmp_path: Path):
    state, live = _open()
    write_session_record(tmp_path, True, live=live, now=_STAMP)
    later = _STAMP + timedelta(seconds=SESSION_RECORD_TTL_SECONDS)
    assert assess_session_record(tmp_path, lock_state=state, now=later) == "expired"
    assert state.unlocked is True
    assert record_grants_unlock(lock_state=state) is False
    fresh = LockState()
    assert fresh.unlocked is False


def test_corrupt_and_legacy_records_are_not_authority(tmp_path: Path):
    fresh = LockState()
    (tmp_path / "session_record.json").write_text("{", encoding="utf-8")
    assert assess_session_record(tmp_path, lock_state=fresh, now=_STAMP) == "corrupt"
    (tmp_path / "session_record.json").write_text(
        json.dumps({"unlocked": True, "updated_at": "2026-11-20T12:00:00Z"}),
        encoding="utf-8",
    )
    assert assess_session_record(tmp_path, lock_state=fresh, now=_STAMP) == "corrupt"
    assert fresh.unlocked is False
    assert record_grants_unlock() is False


def test_other_process_record_is_not_authority(tmp_path: Path):
    state, live = _open()
    planted = {
        "unlocked": True,
        "updated_at": "2026-11-20T12:00:00Z",
        "expires_at": "2026-11-20T12:02:00Z",
        "pid": os.getpid() + 1,
        "session_id": live.session_id,
        "generation": live.generation,
    }
    (tmp_path / "session_record.json").write_text(json.dumps(planted), encoding="utf-8")
    assert assess_session_record(tmp_path, lock_state=state, now=_STAMP) == "foreign_process"
    assert state.unlocked is True
    assert record_grants_unlock(planted, lock_state=state) is False


def test_restart_leaves_the_old_unlocked_file_untrusted(tmp_path: Path):
    state, live = _open()
    write_session_record(tmp_path, True, live=live, now=_STAMP)
    discard_live_sessions()
    restarted = LockState()
    assert restarted.unlocked is False
    assert json.loads((tmp_path / "session_record.json").read_text(encoding="utf-8"))["unlocked"] is True
    assert assess_session_record(tmp_path, lock_state=restarted, now=_STAMP) == "superseded"
    assert record_grants_unlock(lock_state=restarted) is False


def test_panel_does_not_read_the_session_record():
    root = Path(__file__).resolve().parent.parent
    paths = (
        root / "src/core/panel_runtime_lock.py",
        root / "src/core/panel_bridge_state.py",
        root / "panel/scripts/panel_tasks_server.py",
        root / "src/policy/action_policy.py",
    )
    runtime = (root / "src/core/lumos_runtime.py").read_text(encoding="utf-8")
    assert "record_grants_unlock" not in runtime
    assert "assess_session_record" not in runtime
    for path in paths:
        assert "session_record" not in path.read_text(encoding="utf-8")


def _start_cli(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LUMOS_MODE", "offline")
    monkeypatch.delenv("LUMOS_UI", raising=False)
    monkeypatch.delenv("LUMOS_PASSPHRASE", raising=False)
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: "cik")
    from security.keystore import FileKeyStore

    FileKeyStore(base_dir=".lumos", is_sandbox_mode=False).init(_PASSPHRASE)
    from core.lumos_runtime import create_runtime

    runtime = create_runtime(sandbox_mode=False)
    assert runtime.router_ctx is not None
    return runtime


def test_cli_lock_menu_writes_observation_without_granting_from_the_file(tmp_path: Path, monkeypatch):
    discard_live_sessions()
    runtime = _start_cli(tmp_path, monkeypatch)
    record = tmp_path / ".lumos" / "session_record.json"
    monkeypatch.setattr("core.lumos_runtime.getpass", lambda *_args, **_kwargs: "wrong-passphrase")
    runtime.router_ctx.on_lock_menu(["ac"])
    assert not record.exists()
    assert runtime.router_ctx.ctx.state.is_locked() is True

    monkeypatch.setattr("core.lumos_runtime.getpass", lambda *_args, **_kwargs: _PASSPHRASE)
    runtime.router_ctx.on_lock_menu(["ac"])
    text = record.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["unlocked"] is True
    assert set(payload) == _FIELDS
    assert _PASSPHRASE not in text
    assert record_grants_unlock(payload) is False
    state = runtime.router_ctx.ctx.state._lumos.lock_state
    assert assess_session_record(tmp_path / ".lumos", lock_state=state) == "observed_current"

    runtime.router_ctx.on_lock_menu(["kapat"])
    closed = json.loads(record.read_text(encoding="utf-8"))
    assert closed["unlocked"] is False
    assert runtime.router_ctx.ctx.state.is_locked() is True
    assert "LUMOS_PASSPHRASE" not in os.environ
    assert assess_session_record(tmp_path / ".lumos", lock_state=state) != "observed_current"
    assert record_grants_unlock(closed) is False


def test_lock_write_failure_does_not_trust_the_old_unlocked_file(tmp_path: Path, monkeypatch):
    discard_live_sessions()
    runtime = _start_cli(tmp_path, monkeypatch)
    monkeypatch.setattr("core.lumos_runtime.getpass", lambda *_args, **_kwargs: _PASSPHRASE)
    runtime.router_ctx.on_lock_menu(["ac"])
    record = tmp_path / ".lumos" / "session_record.json"
    before = record.read_text(encoding="utf-8")
    assert json.loads(before)["unlocked"] is True
    state = runtime.router_ctx.ctx.state._lumos.lock_state

    def _fail(*_args, **_kwargs):
        raise OSError("session record write failed")

    monkeypatch.setattr("core.lumos_runtime.write_session_record", _fail)
    monkeypatch.setattr("core.lumos_runtime.remove_session_record", _fail)
    runtime.router_ctx.on_lock_menu(["kapat"])
    assert runtime.router_ctx.ctx.state.is_locked() is True
    assert "LUMOS_PASSPHRASE" not in os.environ
    assert record.read_text(encoding="utf-8") == before
    assert assess_session_record(tmp_path / ".lumos", lock_state=state) == "superseded"
    assert record_grants_unlock(json.loads(before), lock_state=state) is False
    invalidate_live_session(state)
