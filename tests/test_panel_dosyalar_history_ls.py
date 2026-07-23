"""Dosyalar upload history — localStorage persistence (this device only)."""

from __future__ import annotations

from pathlib import Path

from tests.test_panel_component_split import read_panel_source

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"

LS_KEY = "lumos_panel_dosyalar_history_v1"
DEVICE_NOTE_TR = "Bu cihazda saklanır; en fazla 5 kayıt."


def test_dosyalar_history_local_storage_wiring() -> None:
    text = read_panel_source()
    assert LS_KEY in text
    assert "loadDosyalarUploadHistory" in text
    assert "persistDosyalarUploadHistory" in text
    assert 'JSON.stringify({ v: 1, items:' in text
    assert "renderDosyalarHistory();" in text.split("function wireDosyalarUpload", 1)[1]


def test_dosyalar_history_device_note_present() -> None:
    text = read_panel_source()
    assert 'id="dosyalar-history-device-note"' in text
    assert 'data-i18n="panel.modules.files.historyDeviceNote"' in text
    assert DEVICE_NOTE_TR in text


def test_dosyalar_history_i18n_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    assert "historyHeading:" in text
    assert "historyDeviceNote:" in text
