"""Landing index.astro — inline tokens; no dead external stylesheet link."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INDEX_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "index.astro"
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_LANDING_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "landing" / "tr.ts"
_LANDING_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "landing" / "en.ts"


def test_index_has_no_dead_lumos_tokens_stylesheet_link() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    assert "/styles/lumos-tokens.css" not in text
    assert "--lumos-land-teal:" in text


def test_landing_kurulum_bridge_env_proxy_steps() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    assert 'data-i18n="landing.install.step4"' in text
    assert "ui/.env.example ui/.env.local" in text
    assert "bridge_start.sh" in text
    assert "panel_tasks_server.py" in text
    assert "vercel dev" in text
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


def test_panel_hero_prefill_scroll_and_banner_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert "scrollIntoView({ behavior: \"smooth\", block: \"center\" })" in text
    assert "showPanelHeroPrefillBanner" in text
    assert 'id="panel-hero-prefill-banner"' in text
    assert 'panelT("panel.modules.chat.empty.heroPrefillBanner")' in text
    assert 'navigatePanelModule("sohbet")' in text
    assert "prefillPanelChatFromUrlQuery()" in text
