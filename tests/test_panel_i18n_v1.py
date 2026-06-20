"""Panel i18n v1/v2 — LanguageSwitcher, nav, Ses/Medya/Sosyal/Posta module chrome."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_TR_MESSAGES = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts"
_EN_MESSAGES = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "en.ts"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"
_PANEL_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "en.ts"

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

PANEL_I18N_V2_MARKERS = (
    'data-i18n="panel.sections.ses"',
    'data-i18n="panel.sections.medya"',
    'data-i18n="panel.sections.sosyal"',
    'data-i18n="panel.sections.posta"',
    'data-i18n="panel.modules.voice.intro"',
    'data-i18n="panel.modules.voice.c1Title"',
    'data-i18n="panel.modules.media.outboxTitle"',
    'data-i18n="panel.modules.media.outboxRefresh"',
    'data-i18n="panel.modules.social.c1Title"',
    'data-i18n="panel.modules.mail.c1Title"',
    'data-i18n="panel.common.badges.demoNotConnected"',
    'data-i18n="panel.common.form.showSummary"',
    'data-i18n="panel.common.form.sendDemoDisabled"',
    'data-i18n-placeholder="panel.common.placeholders.shareSummary"',
    'data-i18n-title="panel.common.demo.sendTitle"',
    'function panelT(key)',
)

PANEL_I18N_V2_TR_KEYS = (
    "common:",
    "demoNotConnected:",
    "sharePreviewIntro:",
    "dataType:",
    "ses:",
    "medya:",
    "sosyal:",
    "posta:",
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
    for key in ("sohbet:", "gorevler:", "dosyalar:", "sections:", "ses:", "medya:", "sosyal:", "posta:"):
        assert key in text


def test_panel_astro_i18n_v2_module_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_I18N_V2_MARKERS:
        assert token in text, f"missing panel i18n v2 token: {token}"


def test_panel_i18n_v2_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V2_TR_KEYS:
        assert key in tr_text, f"missing panel tr key fragment: {key}"
        assert key in en_text, f"missing panel en key fragment: {key}"
