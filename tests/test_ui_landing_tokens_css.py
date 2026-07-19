"""Landing index.astro — shared tokens via lumos-tokens.css."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INDEX_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "index.astro"
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_TOKENS_CSS = _REPO_ROOT / "ui" / "src" / "styles" / "lumos-tokens.css"
_LANDING_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "landing" / "tr.ts"
_LANDING_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "landing" / "en.ts"


def test_index_imports_shared_lumos_tokens_stylesheet() -> None:
    index = _INDEX_ASTRO.read_text(encoding="utf-8")
    panel = _PANEL_ASTRO.read_text(encoding="utf-8")
    tokens = _TOKENS_CSS.read_text(encoding="utf-8")
    assert 'import "../styles/lumos-tokens.css"' in index
    assert 'import "../styles/lumos-tokens.css"' in panel
    assert "--lumos-land-teal: 45 212 191" in tokens
    assert "--lumos-bg: #0a0e14" in tokens


def test_landing_kurulum_links_full_setup_without_internal_names() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    assert 'data-i18n="landing.install.step4"' in text
    assert "ui/.env.example ui/.env.local" in text
    assert "docs/getting-started.md" in text
    assert "KANDO_BRIDGE_SECRET" not in text
    assert "BRIDGE_UPSTREAM_URL" not in text
    assert 'data-i18n="landing.install.tryPanelWarning"' in text


def test_panel_conn_badge_setup_link_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert "wirePanelConnBadgeSetupLink" in text
    assert 'window.location.href = "/#kurulum"' in text
    assert 'data-setup-link' in text
    assert 'panelT("panel.shell.conn.setupHint")' in text


def test_landing_install_v8_keys_in_catalogs() -> None:
    tr_text = _LANDING_TR.read_text(encoding="utf-8")
    en_text = _LANDING_EN.read_text(encoding="utf-8")
    for key in (
        "step8:",
        "step5note:",
        "step6note:",
        "fullSetupGuide:",
        "tryPanelWarning:",
    ):
        assert key in tr_text, f"missing landing tr key: {key}"
        assert key in en_text, f"missing landing en key: {key}"


def test_landing_hero_ask_field_name_q() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    assert 'id="lumos-hero-ask-input"' in text
    assert 'name="q"' in text
    assert 'action="/panel"' in text
    assert 'method="get"' in text
    assert "if (!q) {" in text
    assert 'window.location.href = "/panel?q="' not in text


def test_landing_hero_ask_empty_submit_no_panel_redirect() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    tr_text = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts").read_text(encoding="utf-8")
    en_text = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "en.ts").read_text(encoding="utf-8")
    assert 'window.location.href = "/panel"' not in text
    assert 'id="lumos-hero-ask-error"' in text
    assert 'data-i18n="hero.askEmpty"' in text
    assert 'role="alert"' in text
    assert "showHeroAskError()" in text
    assert "input.focus()" in text
    assert 'aria-invalid="true"' in text or 'setAttribute("aria-invalid", "true")' in text
    assert "askEmpty:" in tr_text
    assert "askEmpty:" in en_text


def test_panel_hero_prefill_scroll_and_banner_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert "scrollIntoView({ behavior: \"smooth\", block: \"center\" })" in text
    assert "showPanelHeroPrefillBanner" in text
    assert 'id="panel-hero-prefill-banner"' in text
    assert 'panelT("panel.modules.chat.empty.heroPrefillBanner")' in text
    assert 'navigatePanelModule("sohbet")' in text
    assert "prefillPanelChatFromUrlQuery()" in text


def test_landing_world_roadmap_link_i18n_wiring() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    tr_text = _LANDING_TR.read_text(encoding="utf-8")
    en_text = _LANDING_EN.read_text(encoding="utf-8")
    assert 'data-i18n="landing.world.linkRoadmap"' in text
    assert "linkRoadmap:" in tr_text
    assert "linkRoadmap:" in en_text
    assert ">Yol haritası</a>" in text


def test_landing_kuantum_sections_i18n_wiring() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    tr_text = _LANDING_TR.read_text(encoding="utf-8")
    en_text = _LANDING_EN.read_text(encoding="utf-8")
    for key in (
        "quantumTitle:",
        "quantumScope:",
        "quantumCardStatus:",
        "quantumDetailStatus:",
        "quantumDetailBody:",
        "quantumDetailLinksLead:",
        "quantumAdrLink:",
        "quantumAdr013Link:",
        "quantumPanelLink:",
        "roadmapInlineLead:",
        "roadmapLinkFile:",
        "roadmapWorldVision:",
        "roadmapWorldVisionLink:",
    ):
        assert key in tr_text, f"missing landing tr key: {key}"
        assert key in en_text, f"missing landing en key: {key}"
    assert 'id="modul-kuantum"' in text
    assert 'data-i18n="landing.modules.quantumTitle"' in text
    assert 'data-i18n="landing.modules.quantumDetailStatus"' in text
    assert 'data-i18n="landing.modules.quantumAdrLink"' in text
    assert 'data-i18n="landing.modules.quantumAdr013Link"' in text
    assert "ADR-013-lumos-quantum-security-readiness.md" in text
    assert 'data-i18n="landing.modules.quantumPanelLink"' in text
    assert 'data-i18n="landing.modules.roadmapInlineLead"' in text
    assert 'data-i18n="landing.modules.roadmapLinkFile"' in text
    assert 'data-i18n="landing.modules.roadmapWorldVisionLink"' in text
    assert "<h3>Kuantum</h3>" not in text
    modules_inline_start = text.index('data-i18n="landing.modules.roadmapInlineLead"')
    modules_inline_end = text.index("</p>", modules_inline_start)
    modules_inline_block = text[modules_inline_start:modules_inline_end]
    assert ">ROADMAP.md</a>" not in modules_inline_block
    assert 'data-i18n="landing.modules.roadmapLinkFile"' in modules_inline_block


def test_landing_hero_ask_submit_distinct_from_cta_panel_tr() -> None:
    tr_text = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts").read_text(
        encoding="utf-8"
    )
    cta_panel = re.search(r'ctaPanel:\s*"([^"]+)"', tr_text)
    ask_submit = re.search(r'askSubmit:\s*"([^"]+)"', tr_text)
    assert cta_panel is not None
    assert ask_submit is not None
    assert ask_submit.group(1) != cta_panel.group(1)


def test_landing_mobile_nav_scroll_hint_in_mobile_block() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    assert 'class="lumos-site-nav__list lumos-site-nav__list--scroll-hint"' in text
    mobile_nav_anchor = "Küçük ekran cilası: yalnızca max-width ile"
    assert mobile_nav_anchor in text
    mobile_nav_start = text.index(mobile_nav_anchor)
    mobile_nav_block = text[mobile_nav_start : mobile_nav_start + 5000]
    assert "lumos-site-nav__list--scroll-hint" in mobile_nav_block
    assert "mask-image: linear-gradient" in mobile_nav_block


def test_landing_sticky_nav_scroll_margin_offset_token() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    assert "--lumos-sticky-nav-offset:" in text
    assert "scroll-margin-top: var(--lumos-sticky-nav-offset)" in text
    desktop_block = re.search(
        r"@media\s*\(\s*min-width:\s*768px\s*\)\s*\{[^}]*--lumos-sticky-nav-offset:\s*([\d.]+)rem",
        text,
        re.DOTALL,
    )
    assert desktop_block is not None, "desktop --lumos-sticky-nav-offset media block missing"
    desktop_rem = float(desktop_block.group(1))
    assert desktop_rem > 1.25
    mobile_default = re.search(
        r":root\s*\{[^}]*--lumos-sticky-nav-offset:\s*1\.25rem",
        text,
        re.DOTALL,
    )
    assert mobile_default is not None, "mobile default --lumos-sticky-nav-offset should be 1.25rem"
    mobile_nav_block_start = text.index("Küçük ekran cilası: yalnızca max-width ile")
    mobile_nav_block = text[mobile_nav_block_start : mobile_nav_block_start + 5000]
    assert ".lumos-site-nav {\n          position: relative;" in mobile_nav_block


def test_landing_hero_no_duplicate_inline_copy_dict() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    tr_text = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts").read_text(encoding="utf-8")
    en_text = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "en.ts").read_text(encoding="utf-8")
    assert "HERO_LANDING_COPY" not in text
    assert 'data-i18n="hero.askHint"' in text
    assert "askHint:" in tr_text
    assert "askHint:" in en_text


def _catalog_string(source: str, key: str) -> str:
    match = re.search(rf'{re.escape(key)}:\s*"([^"]+)"', source)
    assert match is not None, f"missing catalog key: {key}"
    return match.group(1)


def test_landing_ssr_fallbacks_match_tr_catalog() -> None:
    """SSR/no-JS fallbacks in index.astro must match Turkish i18n catalogs."""
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    tr_meta = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts").read_text(encoding="utf-8")
    landing_tr = _LANDING_TR.read_text(encoding="utf-8")

    meta_desc = _catalog_string(tr_meta, "description")
    assert meta_desc in text
    assert "hedefleyen yapay zekâ kontrol katmanı prototipidir" not in text

    try_panel = _catalog_string(landing_tr, "tryPanel")
    assert f'>{try_panel}</a>' in text
    assert ">Paneli dene</a>" not in text

    card_body = _catalog_string(landing_tr, "cardUserControlBody")
    assert card_body in text
    assert "Lumos yerine geçmez" not in text

    list_body = _catalog_string(landing_tr, "listUserDecisionBody")
    assert list_body in text

    og_image = _catalog_string(landing_tr, "ogImage")
    assert 'data-i18n-content="landing.assets.ogImage"' in text
    twitter_image = re.search(
        r'name="twitter:image"[^>]*\n\s*content="([^"]+)"',
        text,
    )
    assert twitter_image is not None
    assert twitter_image.group(1) == og_image


def test_umbrella_integration_routes_exist() -> None:
    """Integration hub and detail pages import shared tokens and umbrella chrome."""
    routes = (
        _REPO_ROOT / "ui" / "src" / "pages" / "integrations.astro",
        _REPO_ROOT / "ui" / "src" / "pages" / "integrations" / "github.astro",
        _REPO_ROOT / "ui" / "src" / "pages" / "integrations" / "google.astro",
        _REPO_ROOT / "ui" / "src" / "pages" / "integrations" / "mail.astro",
        _REPO_ROOT / "ui" / "src" / "pages" / "integrations" / "linear.astro",
        _REPO_ROOT / "ui" / "src" / "pages" / "slack.astro",
    )
    umbrella_tr = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "umbrella" / "tr.ts").read_text(
        encoding="utf-8"
    )
    umbrella_en = (_REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "umbrella" / "en.ts").read_text(
        encoding="utf-8"
    )
    for path in routes:
        assert path.is_file(), f"missing route: {path}"
        text = path.read_text(encoding="utf-8")
        assert "lumos-tokens.css" in text
        assert "umbrella-chrome.css" in text
        assert "WeLockSiteNav" in text
        assert "IntegrationPermMatrix" in text or path.name == "integrations.astro"
    assert "integrations:" in umbrella_tr
    assert "integrations:" in umbrella_en
    assert 'href="/integrations"' in (_REPO_ROOT / "ui" / "src" / "pages" / "index.astro").read_text(
        encoding="utf-8"
    )
    nav = (_REPO_ROOT / "ui" / "src" / "components" / "WeLockSiteNav.astro").read_text(encoding="utf-8")
    assert 'href="/integrations"' in nav
