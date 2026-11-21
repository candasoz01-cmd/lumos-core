"""T4-1: keystore_ready, consent_ok, and LockState.unlocked stay independent.

Characterization only. No trust engine and no gate change.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.panel_bridge_state import build_panel_read_state
from core.startup_health import consent_ok, get_durum_parts, keystore_ready
from security.lock import LockState

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_each_signal_can_be_true_while_the_others_are_false(tmp_path: Path):
    lock = LockState()
    assert keystore_ready(True) is True
    assert lock.unlocked is False
    assert consent_ok(tmp_path) is False

    (tmp_path / "consent.json").write_text("{}", encoding="utf-8")
    assert consent_ok(tmp_path) is True
    assert keystore_ready(False) is False
    assert lock.unlocked is False

    lock.unlock(b"\x01" * 32)
    assert lock.unlocked is True
    assert keystore_ready(False) is False
    assert consent_ok(tmp_path) is True

    lock.lock()
    assert lock.unlocked is False
    assert consent_ok(tmp_path) is True
    assert keystore_ready(True) is True


def test_lock_toggle_does_not_create_consent_or_keystore(tmp_path: Path):
    lock = LockState()
    lock.unlock(b"\x02" * 32)
    lock.lock()
    assert not (tmp_path / "consent.json").exists()
    assert not (tmp_path / "keystore.json").exists()
    assert consent_ok(tmp_path) is False
    assert keystore_ready(False) is False


def test_consent_file_does_not_unlock_or_mark_keystore_ready(tmp_path: Path):
    lock = LockState()
    (tmp_path / "consent.json").write_text("{}", encoding="utf-8")
    assert consent_ok(tmp_path) is True
    assert lock.unlocked is False
    assert keystore_ready(False) is False


def test_durum_parts_report_keystore_and_consent_without_a_lock_field(tmp_path: Path):
    class _Presence:
        def load_presence_cfg(self, base_dir: Path):
            return type("Cfg", (), {"enabled": False})()

    parts = get_durum_parts(tmp_path, keystore_initialized=False, presence_module=_Presence())
    assert parts["consent_ok"] is False
    assert parts["keystore_ready"] is False
    assert "session_unlocked" not in parts
    assert "unlocked" not in parts

    (tmp_path / "consent.json").write_text("{}", encoding="utf-8")
    parts_consent = get_durum_parts(
        tmp_path, keystore_initialized=True, presence_module=_Presence()
    )
    assert parts_consent["consent_ok"] is True
    assert parts_consent["keystore_ready"] is True
    assert "session_unlocked" not in parts_consent


def test_panel_payload_keeps_the_three_signals_distinct(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    (tmp_path / "keystore.json").write_text(
        json.dumps({"v": 1, "root_key": {"v": 1}}), encoding="utf-8"
    )

    locked = build_panel_read_state(
        repo_root=_REPO_ROOT,
        runtime_lock_state=type("Lock", (), {"unlocked": False})(),
    )
    assert locked["keystore"]["keystore_ready"] is True
    assert locked["keystore"]["consent_ok"] is False
    assert locked["guidance"]["session_unlocked"] is False

    (tmp_path / "keystore.json").unlink()
    (tmp_path / "consent.json").write_text("{}", encoding="utf-8")
    unlocked = build_panel_read_state(
        repo_root=_REPO_ROOT,
        runtime_lock_state=type("Lock", (), {"unlocked": True})(),
    )
    assert unlocked["keystore"]["keystore_ready"] is False
    assert unlocked["keystore"]["consent_ok"] is True
    assert unlocked["guidance"]["session_unlocked"] is True

    missing = build_panel_read_state(repo_root=_REPO_ROOT)
    assert missing["keystore"]["keystore_ready"] is False
    assert missing["keystore"]["consent_ok"] is True
    assert missing["guidance"]["session_unlocked"] is None
    assert missing["guidance"]["session_unlocked_source"] == "unavailable"
