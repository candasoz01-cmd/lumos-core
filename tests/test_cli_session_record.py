"""L2: the CLI writes {unlocked, updated_at} and nothing else."""
from __future__ import annotations

import inspect
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from security.keystore import FileKeyStore
from security.session_record import (
    build_session_record,
    validate_session_record,
    write_session_record,
)

_PASSPHRASE = "correct-horse-battery-passphrase"
_FORBIDDEN = (
    "passphrase",
    "password",
    "secret",
    "token",
    "root_key",
    "private_key",
    "credential",
)
_STAMP = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def test_record_has_only_unlocked_and_updated_at(tmp_path: Path):
    payload = write_session_record(tmp_path, True, now=_STAMP)
    assert payload == {"unlocked": True, "updated_at": "2026-11-20T12:00:00Z"}
    path = tmp_path / "session_record.json"
    raw = path.read_text(encoding="utf-8")
    assert json.loads(raw) == payload
    assert set(json.loads(raw)) == {"unlocked", "updated_at"}
    assert raw == json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    locked = write_session_record(tmp_path, False, now=_STAMP)
    assert locked == {"unlocked": False, "updated_at": "2026-11-20T12:00:00Z"}
    shifted = build_session_record(
        True, now=datetime(2026, 11, 20, 15, 0, tzinfo=timezone(timedelta(hours=3)))
    )
    assert shifted["updated_at"] == "2026-11-20T12:00:00Z"


def test_record_file_mode_is_owner_only(tmp_path: Path):
    write_session_record(tmp_path, False, now=_STAMP)
    path = tmp_path / "session_record.json"
    assert path.is_file()
    assert (path.stat().st_mode & 0o777) == 0o600
    assert not path.with_name(path.name + ".tmp").exists()


def test_non_bool_unlock_flag_is_rejected():
    for value in (1, "true", None, 1.0):
        with pytest.raises(TypeError, match="unlocked must be bool"):
            build_session_record(value)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="unlocked must be bool"):
            validate_session_record(
                {"unlocked": value, "updated_at": "2026-11-20T12:00:00Z"}
            )


def test_extra_or_secret_fields_are_rejected():
    base = {"unlocked": True, "updated_at": "2026-11-20T12:00:00Z"}
    with pytest.raises(ValueError, match="only unlocked and updated_at"):
        validate_session_record({**base, "note": "extra"})
    with pytest.raises(ValueError, match="only unlocked and updated_at"):
        validate_session_record({**base, "passphrase": "secret-value"})
    with pytest.raises(ValueError, match="only unlocked and updated_at"):
        validate_session_record({"unlocked": True})
    with pytest.raises(ValueError, match="UTC timestamp"):
        validate_session_record({"unlocked": True, "updated_at": "2026-11-20T12:00:00+00:00"})
    with pytest.raises(ValueError, match="secret-like content"):
        validate_session_record(
            {"unlocked": True, "updated_at": "2026-11-20T12:00:00secretZ"}
        )
    with pytest.raises(ValueError, match="timezone"):
        build_session_record(True, now=datetime(2026, 11, 20, 12, 0))


def test_symlink_record_is_not_followed(tmp_path: Path):
    outside = tmp_path / "outside.json"
    outside.write_text("original", encoding="utf-8")
    base = tmp_path / "workspace"
    base.mkdir()
    record = base / "session_record.json"
    record.symlink_to(outside)
    with pytest.raises(OSError, match="must not be a symlink"):
        write_session_record(base, True, now=_STAMP)
    assert outside.read_text(encoding="utf-8") == "original"
    assert record.is_symlink()

    record.unlink()
    temp = base / "session_record.json.tmp"
    temp.symlink_to(outside)
    with pytest.raises(OSError, match="temp path must not be a symlink"):
        write_session_record(base, False, now=_STAMP)
    assert outside.read_text(encoding="utf-8") == "original"
    assert not record.exists()


def test_builder_cannot_carry_a_secret():
    source = inspect.getsource(build_session_record).lower()
    payload = build_session_record(True, now=_STAMP)
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).lower()
    for word in _FORBIDDEN:
        assert word not in source
        assert word not in blob
    assert set(payload) == {"unlocked", "updated_at"}
    with pytest.raises(TypeError):
        build_session_record(True, passphrase="secret-value")  # type: ignore[call-arg]


def test_panel_does_not_read_the_session_record():
    root = Path(__file__).resolve().parent.parent
    paths = (
        root / "src/core/panel_runtime_lock.py",
        root / "src/core/panel_bridge_state.py",
        root / "panel/scripts/panel_tasks_server.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "session_record" not in text


def _start_cli(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LUMOS_MODE", "offline")
    monkeypatch.delenv("LUMOS_UI", raising=False)
    monkeypatch.delenv("LUMOS_PASSPHRASE", raising=False)
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: "cik")
    store = FileKeyStore(base_dir=".lumos", is_sandbox_mode=False)
    store.init(_PASSPHRASE)
    from core.lumos_runtime import create_runtime

    runtime = create_runtime(sandbox_mode=False)
    assert runtime.router_ctx is not None
    return runtime


def _record(tmp_path: Path) -> Path:
    return tmp_path / ".lumos" / "session_record.json"


def test_cli_lock_menu_writes_record_without_the_passphrase(tmp_path: Path, monkeypatch):
    runtime = _start_cli(tmp_path, monkeypatch)
    record = _record(tmp_path)
    monkeypatch.setattr("core.lumos_runtime.getpass", lambda *_args, **_kwargs: "wrong-passphrase")
    runtime.router_ctx.on_lock_menu(["ac"])
    assert not record.exists()
    assert runtime.router_ctx.ctx.state.is_locked() is True

    monkeypatch.setattr("core.lumos_runtime.getpass", lambda *_args, **_kwargs: _PASSPHRASE)
    runtime.router_ctx.on_lock_menu(["ac"])
    text = record.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["unlocked"] is True
    assert set(payload) == {"unlocked", "updated_at"}
    assert _PASSPHRASE not in text
    assert os.environ.get("LUMOS_PASSPHRASE") == _PASSPHRASE

    runtime.router_ctx.on_lock_menu(["kapat"])
    locked = json.loads(record.read_text(encoding="utf-8"))
    assert locked["unlocked"] is False
    assert set(locked) == {"unlocked", "updated_at"}
    assert _PASSPHRASE not in record.read_text(encoding="utf-8")
    assert "LUMOS_PASSPHRASE" not in os.environ
    assert runtime.router_ctx.ctx.state.is_locked() is True


def test_record_write_failure_does_not_keep_the_session_open(tmp_path: Path, monkeypatch):
    runtime = _start_cli(tmp_path, monkeypatch)
    monkeypatch.setattr("core.lumos_runtime.getpass", lambda *_args, **_kwargs: _PASSPHRASE)
    runtime.router_ctx.on_lock_menu(["ac"])
    record = _record(tmp_path)
    before = record.read_text(encoding="utf-8")
    assert json.loads(before)["unlocked"] is True
    assert os.environ.get("LUMOS_PASSPHRASE") == _PASSPHRASE

    def _fail(*_args, **_kwargs):
        raise OSError("session record write failed")

    monkeypatch.setattr("core.lumos_runtime.write_session_record", _fail)
    runtime.router_ctx.on_lock_menu(["kapat"])
    assert runtime.router_ctx.ctx.state.is_locked() is True
    assert "LUMOS_PASSPHRASE" not in os.environ
    assert record.read_text(encoding="utf-8") == before
    assert json.loads(before)["unlocked"] is True
