"""Ortak Uzman Modülü kartı ve Elektronik Uzmanı PWA pilot sözleşmesi."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PANEL = _ROOT / "ui" / "src" / "pages" / "panel.astro"
_COMPONENT = _ROOT / "ui" / "src" / "components" / "ExpertModulePilotCard.astro"
_TR = _ROOT / "ui" / "src" / "i18n" / "messages" / "electronics" / "tr.ts"
_EN = _ROOT / "ui" / "src" / "i18n" / "messages" / "electronics" / "en.ts"


def test_expert_module_uses_reusable_component() -> None:
    component = _COMPONENT.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "data-expert-module-card" in component
    assert "data-expert-module-id={moduleId}" in component
    assert "<slot />" in component
    assert 'import ExpertModulePilotCard from "../components/ExpertModulePilotCard.astro"' in panel
    assert '<ExpertModulePilotCard\n              moduleId="electronics"' in panel


def test_electronics_is_active_local_pilot_module() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    assert 'data-module="elektronik"' in panel
    assert 'data-module-panel="elektronik"' in panel
    assert 'data-module="elektronik" data-module-availability="inactive"' not in panel
    assert 'data-i18n="panel.nav.status.elektronik"' in panel


def test_pilot_activation_and_cases_are_device_local() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    assert 'const EXPERT_PILOT_STORAGE_PREFIX = "lumos.expert.pilot.v1."' in panel
    assert 'const ELECTRONICS_CASES_STORAGE_KEY = "lumos.expert.electronics.cases.v1"' in panel
    assert "localStorage.setItem(expertPilotStorageKey(moduleId), \"enabled\")" in panel
    assert "writeElectronicsCases([faultCase, ...readElectronicsCases()])" in panel
    assert "fetch(" not in panel.split('const ELECTRONICS_CASES_STORAGE_KEY =')[1].split(
        "function scrollPanelComposeIntoView"
    )[0]


def test_critical_risk_blocks_measurement_record() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    assert 'const hardStop = riskSeverity === "critical"' in panel
    assert "measurement: hardStop\n                ? null" in panel
    assert '"panel.modules.electronics.pilotUi.criticalBlocked"' in panel


def test_voltage_and_energized_measurement_guards_present() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    assert 'circuitState !== "deenergized" && riskSeverity === "none"' in panel
    assert '!hardStop && measurementType === "voltage" && !referencePoint' in panel
    assert 'riskCheckRef: riskId' in panel
    assert 'enteredBy: "user"' in panel


def test_expert_pilot_copy_has_tr_en_parity_and_honest_scope() -> None:
    tr = _TR.read_text(encoding="utf-8")
    en = _EN.read_text(encoding="utf-8")
    for key in (
        "pilotUi:",
        "activate:",
        "criticalBlocked:",
        "voltageReferenceRequired:",
        "definitiveNotice:",
    ):
        assert key in tr
        assert key in en
    assert "Canlı teşhis veya dış sağlayıcı bağlantısı yoktur" in tr
    assert "There is no live diagnosis or external provider connection" in en


def test_expert_module_mobile_controls_keep_touch_safe_size() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    assert ".expert-module-card__activate," in panel
    assert ".expert-module-form__submit" in panel
    assert "min-height: 2.75rem" in panel
    assert "@media (max-width: 640px)" in panel
