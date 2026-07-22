"""Internal Alpha — premium dark panel visual polish (finding #1)."""

from __future__ import annotations

import re
from pathlib import Path

from tests.test_panel_component_split import read_panel_source

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_TOKENS_CSS = _REPO_ROOT / "ui" / "src" / "styles" / "lumos-tokens.css"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"
_PANEL_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "en.ts"

PREMIUM_DARK_MARKERS = (
    "--lumos-panel-navy:",
    "--lumos-land-teal: 45 212 191",
    "--panel-font-title:",
    "--panel-content-max:",
    'import "../styles/lumos-tokens.css"',
    "panel-header-tagline",
    "panel-module-head",
    "panel-module-eyebrow",
    "#panel-sosyal .medya-card-list",
    "#panel-posta .medya-card-list",
    "min-height: 9.5rem",
)


def test_panel_premium_dark_control_center_tokens() -> None:
    panel = read_panel_source()
    tokens = _TOKENS_CSS.read_text(encoding="utf-8")
    for token in PREMIUM_DARK_MARKERS:
        if token.startswith("--"):
            assert token in tokens, f"missing premium dark marker in tokens: {token}"
        else:
            assert token in panel, f"missing premium dark marker in panel: {token}"


def test_panel_nav_sig_hidden_to_reduce_branding_repetition() -> None:
    text = read_panel_source()
    assert ".panel-nav-sig {" in text
    assert "display: none;" in text.split(".panel-nav-sig {", 1)[1].split("}", 1)[0]


def test_panel_header_subtitle_and_module_groups_in_i18n() -> None:
    for path in (_PANEL_TR, _PANEL_EN):
        text = path.read_text(encoding="utf-8")
        assert "subtitle:" in text
        assert "moduleGroups:" in text
        assert "preview:" in text


def test_panel_i18n_keys_used_in_astro_exist_in_catalogs() -> None:
    astro = read_panel_source()
    keys = set(re.findall(r'data-i18n="(panel\.[^"]+)"', astro))
    keys |= set(re.findall(r'data-i18n-placeholder="(panel\.[^"]+)"', astro))
    keys |= set(re.findall(r'data-i18n-title="(panel\.[^"]+)"', astro))
    keys |= set(re.findall(r'data-i18n-aria-label="(panel\.[^"]+)"', astro))
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    missing_tr: list[str] = []
    missing_en: list[str] = []
    for key in sorted(keys):
        leaf = key.split(".")[-1] + ":"
        if leaf not in tr_text:
            missing_tr.append(key)
        if leaf not in en_text:
            missing_en.append(key)
    assert not missing_tr, f"panel tr catalog missing keys: {missing_tr[:8]}"
    assert not missing_en, f"panel en catalog missing keys: {missing_en[:8]}"


def test_panel_social_mail_draft_textareas_enlarged() -> None:
    text = read_panel_source()
    assert 'id="sosyal-share-content" rows="6"' in text
    assert 'id="posta-share-content" rows="8"' in text
