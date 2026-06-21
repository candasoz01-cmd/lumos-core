"""RB-17 / G-03 — panel nav inactive module badges."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"
_PANEL_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "en.ts"

PANEL_NAV_INACTIVE_MARKERS = (
    'data-module-availability="inactive"',
    'class="panel-nav-inactive-badge lumos-soon-badge"',
    'data-i18n="panel.nav.inactiveBadge"',
    'data-i18n-title="panel.nav.inactiveBadgeTitle"',
)

PANEL_NAV_INACTIVE_MODULES = (
    "ses",
    "medya",
    "sosyal",
    "posta",
    "kuantum",
    "yayincilik",
    "yapayzeka",
    "entegrasyon",
    "kimlik",
    "guvenlik",
    "dunya",
    "ayarlar",
)

PANEL_NAV_ACTIVE_MODULES = (
    "sohbet",
    "gorevler",
    "dosyalar",
    "yetenekler",
)

PANEL_NAV_I18N_KEYS = (
    "inactiveBadge:",
    "inactiveBadgeTitle:",
)


def test_panel_nav_inactive_badge_wiring_present() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_NAV_INACTIVE_MARKERS:
        assert token in text, f"missing panel nav inactive token: {token}"


def test_panel_nav_inactive_modules_marked() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for module_id in PANEL_NAV_INACTIVE_MODULES:
        needle = f'data-module="{module_id}" data-module-availability="inactive"'
        assert needle in text, f"missing inactive nav marker for module: {module_id}"


def test_panel_nav_active_modules_not_marked_inactive() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for module_id in PANEL_NAV_ACTIVE_MODULES:
        assert f'data-module="{module_id}" data-module-availability="inactive"' not in text, (
            f"active module incorrectly marked inactive: {module_id}"
        )


def test_panel_nav_inactive_badge_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_NAV_I18N_KEYS:
        assert key in text, f"missing panel tr inactive nav key: {key}"


def test_panel_nav_inactive_badge_keys_in_panel_en() -> None:
    text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_NAV_I18N_KEYS:
        assert key in text, f"missing panel en inactive nav key: {key}"


def test_panel_nav_inactive_copy_describes_preview_without_claiming_availability() -> None:
    assert 'inactiveBadge: "Önizleme"' in _PANEL_TR.read_text(encoding="utf-8")
    assert 'inactiveBadge: "Preview"' in _PANEL_EN.read_text(encoding="utf-8")
    assert "tam modül işlevi aktif değil" in _PANEL_TR.read_text(encoding="utf-8")
    assert "the full module is not active" in _PANEL_EN.read_text(encoding="utf-8")


def test_panel_header_has_no_seasonal_badge_or_flags() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert "GlobalMay19Corner" not in text
    assert "lumos-m19g" not in text
