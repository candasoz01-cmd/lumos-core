"""Panel i18n v1 — LanguageSwitcher, I18nInit, nav + key section labels."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_TR_MESSAGES = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts"
_EN_MESSAGES = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "en.ts"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"

PANEL_I18N_MARKERS = (
    'import LanguageSwitcher from "../components/LanguageSwitcher.astro";',
    'import I18nInit from "../components/I18nInit.astro";',
    "<LanguageSwitcher />",
    "<I18nInit />",
    'data-i18n="panel.header.title"',
    'data-i18n="panel.nav.sohbet"',
    'data-i18n="panel.nav.gorevler"',
    'data-i18n="panel.nav.dosyalar"',
    'data-i18n="panel.sections.gorevler"',
    'data-i18n="panel.sections.dosyalar"',
    'data-i18n-aria-label="panel.sections.sohbet"',
)


def test_panel_astro_i18n_wiring_present() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_I18N_MARKERS:
        assert token in text, f"missing panel i18n token: {token}"


def test_panel_messages_imported_into_catalogs() -> None:
    tr_text = _TR_MESSAGES.read_text(encoding="utf-8")
    en_text = _EN_MESSAGES.read_text(encoding="utf-8")
    assert 'import panel from "./panel/tr";' in tr_text
    assert "panel," in tr_text
    assert 'import panel from "./panel/en";' in en_text
    assert "panel," in en_text


def test_panel_nav_keys_exist_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in ("sohbet:", "gorevler:", "dosyalar:", "sections:"):
        assert key in text
