"""RB-17 / G-03 — panel nav module infrastructure status badges."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"
_PANEL_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "en.ts"

PANEL_NAV_STATUS_MARKERS = (
    'class="panel-nav-status-pill lumos-status-pill',
    'data-i18n="panel.nav.status.',
    'data-i18n-title="panel.nav.statusTitle.',
    'id="panel-root-status"',
    'data-i18n="panel.rootStatus.title"',
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
    "elektronik",
    "yetenekler",
)

PANEL_NAV_STATUS_I18N_KEYS = (
    "status:",
    "statusSub:",
    "statusTitle:",
)

PANEL_ROOT_STATUS_I18N_KEYS = (
    "rootStatus:",
    "disclaimer:",
)


def test_panel_nav_status_badge_wiring_present() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    for token in PANEL_NAV_STATUS_MARKERS:
        assert token in text, f"missing panel nav status token: {token}"


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


def test_panel_nav_status_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_NAV_STATUS_I18N_KEYS:
        assert key in text, f"missing panel tr status nav key: {key}"
    for key in PANEL_ROOT_STATUS_I18N_KEYS:
        assert key in text, f"missing panel tr root status key: {key}"


def test_panel_nav_status_keys_in_panel_en() -> None:
    text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_NAV_STATUS_I18N_KEYS:
        assert key in text, f"missing panel en status nav key: {key}"
    for key in PANEL_ROOT_STATUS_I18N_KEYS:
        assert key in text, f"missing panel en root status key: {key}"


def test_panel_nav_status_copy_is_honest_not_preview() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    astro_nav = _PANEL_ASTRO.read_text(encoding="utf-8").split("panel-nav__primary")[1].split("</nav>")[0]
    assert 'sohbet: "🟢 Hazır"' in tr_text
    assert "köprü olmadan sınırlı" in tr_text
    assert "Kimlik bekliyor" in tr_text
    assert "Mimari hazır" in tr_text
    assert 'sohbet: "🟢 Ready"' in en_text
    assert "limited without bridge" in en_text
    assert "Identity required" in en_text
    assert "Architecture ready" in en_text
    assert "Topraksız mod" in tr_text
    assert "Toprak bekleniyor" in tr_text
    assert "Hydroponic mode" in en_text
    assert "Awaiting soil" in en_text
    assert 'data-i18n="panel.rootStatus.katmanALink"' in _PANEL_ASTRO.read_text(encoding="utf-8")
    assert "inactiveBadge" not in astro_nav
    assert "Önizleme" not in astro_nav


def test_panel_quantum_disclaimer_i18n_present() -> None:
    assert "disclaimer:" in _PANEL_TR.read_text(encoding="utf-8")
    assert "ORAA" in _PANEL_TR.read_text(encoding="utf-8")
    assert 'data-i18n="panel.modules.quantum.disclaimer"' in _PANEL_ASTRO.read_text(encoding="utf-8")


def test_panel_header_has_no_seasonal_badge_or_flags() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert "GlobalMay19Corner" not in text
    assert "lumos-m19g" not in text
    assert "/assets/flags/tr.svg" not in text


def test_panel_clipboard_attach_label_uses_paste_copy() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    astro = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert 'attachClipboard: "Panodan yapıştır"' in tr_text
    assert 'attachClipboard: "Paste from clipboard"' in en_text
    assert "Panodaki metni ilet" not in astro
    assert "Panodan yapıştır" in astro
