"""Panel i18n v1/v2/v3/v4 — LanguageSwitcher, nav, modules, Sohbet chat, Görevler."""

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

PANEL_I18N_V3_MARKERS = (
    'data-i18n="panel.modules.chat.empty.default"',
    'data-i18n="panel.modules.chat.capability.title"',
    'data-i18n="panel.modules.chat.security.approval"',
    'data-i18n-placeholder="panel.modules.chat.compose.placeholder"',
    'data-i18n="panel.modules.chat.compose.send"',
    'data-i18n="panel.modules.chat.compose.attachFile"',
    'panelT("panel.modules.chat.empty.default")',
    'panelT("panel.modules.chat.modeHints.sendOffline")',
    'chatBubbleRoleLabel(kind)',
    'function refreshPanelChatI18n()',
    'refreshPanelChatI18n()',
)

PANEL_I18N_V3_TR_KEYS = (
    "chat:",
    "empty:",
    "modeHints:",
    "bubbles:",
    "capability:",
    "compose:",
)

PANEL_I18N_V4_MARKERS = (
    'data-i18n="panel.modules.tasks.intro"',
    'data-i18n="panel.modules.tasks.form.titleLabel"',
    'data-i18n-placeholder="panel.modules.tasks.form.titlePlaceholder"',
    'data-i18n="panel.modules.tasks.status.bekliyor"',
    'data-i18n="panel.modules.tasks.list.filterAll"',
    'data-i18n="panel.modules.tasks.detail.close"',
    'function gorevlerStatusLabel(',
    'panelT("panel.modules.tasks.empty.listDefault")',
    'gorevlerPriorityLabel(t.priority)',
)

PANEL_I18N_V4_TR_KEYS = (
    "form:",
    "priority:",
    "status:",
    "list:",
    "empty:",
    "detail:",
)

PANEL_I18N_V5_MARKERS = (
    'data-i18n="panel.sections.kuantum"',
    'data-i18n="panel.modules.quantum.intro"',
    'data-i18n="panel.modules.quantum.c1Title"',
    'data-i18n="panel.nav.lumosCore"',
    'data-i18n="panel.nav.yayincilik"',
    'data-i18n="panel.modules.publishing.c1Title"',
    'data-i18n="panel.modules.capabilities.intro"',
    'data-i18n="panel.modules.capabilities.testBtn"',
)

PANEL_I18N_V5_TR_KEYS = (
    "lumosCore:",
    "yayincilik:",
    "yapayzeka:",
    "entegrasyon:",
    "capabilities:",
)

PANEL_I18N_V6_MARKERS = (
    'data-i18n-aria-label="panel.shell.conn.ariaLabel"',
    'data-i18n-title="panel.shell.conn.title"',
    'data-i18n="panel.shell.userMode.menuOffline"',
    'data-i18n="panel.shell.userMode.segLegend"',
    'data-i18n-aria-label="panel.shell.userMode.badgeAria"',
    'function panelConnBadgeLabel(',
    'function refreshPanelShellI18n()',
    'refreshPanelShellI18n()',
    'panelT("panel.shell.userMode.badgeLimited")',
)

PANEL_I18N_V6_TR_KEYS = (
    "shell:",
    "conn:",
    "userMode:",
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


def test_panel_astro_i18n_v3_chat_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_I18N_V3_MARKERS:
        assert token in text, f"missing panel i18n v3 token: {token}"


def test_panel_i18n_v3_chat_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V3_TR_KEYS:
        assert key in tr_text, f"missing panel tr v3 key fragment: {key}"
        assert key in en_text, f"missing panel en v3 key fragment: {key}"


def test_panel_astro_i18n_v4_gorevler_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_I18N_V4_MARKERS:
        assert token in text, f"missing panel i18n v4 token: {token}"


def test_panel_i18n_v4_gorevler_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V4_TR_KEYS:
        assert key in tr_text, f"missing panel tr v4 key fragment: {key}"
        assert key in en_text, f"missing panel en v4 key fragment: {key}"


def test_panel_astro_i18n_v5_lumos_core_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_I18N_V5_MARKERS:
        assert token in text, f"missing panel i18n v5 token: {token}"


def test_panel_i18n_v5_lumos_core_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V5_TR_KEYS:
        assert key in tr_text, f"missing panel tr v5 key fragment: {key}"
        assert key in en_text, f"missing panel en v5 key fragment: {key}"


def test_panel_astro_i18n_v6_shell_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_I18N_V6_MARKERS:
        assert token in text, f"missing panel i18n v6 token: {token}"


def test_panel_i18n_v6_shell_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V6_TR_KEYS:
        assert key in tr_text, f"missing panel tr v6 key fragment: {key}"
        assert key in en_text, f"missing panel en v6 key fragment: {key}"
