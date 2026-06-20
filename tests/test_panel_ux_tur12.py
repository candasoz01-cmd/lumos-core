"""Tur 12 UX (non-i18n): bubble copy, mobile compose scroll, module focus."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"
_PANEL_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "en.ts"

PANEL_UX_TUR12_1_MARKERS = (
    "function createChatBubbleCopyButton(",
    'copyBtn.setAttribute("data-panel-copy", "")',
    "function panelBubblePlainText(wrap, kind)",
    "function panelWriteTextToClipboard(text)",
    'panelT("panel.modules.chat.bubbles.copy")',
    'panelT("panel.modules.chat.bubbles.copied")',
    'panelT("panel.modules.chat.bubbles.copyFailed")',
    'panelT("panel.modules.chat.bubbles.copyEmpty")',
    "actions.appendChild(createChatBubbleCopyButton())",
    't.closest("button[data-panel-copy]")',
)

PANEL_UX_TUR12_1_I18N_KEYS = (
    "copy:",
    "copied:",
    "copyFailed:",
    "copyEmpty:",
    "copyUnsupported:",
)


def test_panel_ux_tur12_1_bubble_copy_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_UX_TUR12_1_MARKERS:
        assert token in text, f"missing tur12-1 token: {token}"


def test_panel_ux_tur12_1_bubble_copy_i18n_keys() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_UX_TUR12_1_I18N_KEYS:
        assert key in tr_text, f"missing panel tr tur12-1 key: {key}"
        assert key in en_text, f"missing panel en tur12-1 key: {key}"


PANEL_UX_TUR12_2_MARKERS = (
    "function scrollPanelComposeIntoView(",
    "#panel-sohbet .chat-compose-stack",
    'scrollIntoView({ behavior: "smooth", block: "end" })',
    "vv.height < window.innerHeight * 0.82",
    'document.activeElement === input',
    '(pointer: coarse) and (hover: none)',
)


def test_panel_ux_tur12_2_mobile_compose_scroll_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_UX_TUR12_2_MARKERS:
        assert token in text, f"missing tur12-2 token: {token}"
