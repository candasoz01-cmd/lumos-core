"""19 Mayıs anması — UI-only date gating (Europe/Istanbul)."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MAY19_COMPONENT = _REPO_ROOT / "ui" / "src" / "components" / "GlobalMay19Corner.astro"
_LANDING_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "index.astro"

MAY19_DATE_GATE_MARKERS = (
    "isMay19CommemorationDay",
    "Europe/Istanbul",
    "getMonth() === 4",
    "getDate() === 19",
    "showMay19Commemoration",
)


def test_global_may19_corner_is_date_gated() -> None:
    text = _MAY19_COMPONENT.read_text(encoding="utf-8")
    for token in MAY19_DATE_GATE_MARKERS[:4]:
        assert token in text, f"missing May19 date gate marker in component: {token}"
    assert "showMay19Commemoration &&" in text


def test_landing_may19_surfaces_are_date_gated() -> None:
    text = _LANDING_ASTRO.read_text(encoding="utf-8")
    assert "showMay19Commemoration" in text
    assert "{showMay19Commemoration && <GlobalMay19Corner />}" in text
    assert 'class="lumos-may19-card lumos-may19-card--sideline"' in text
    assert text.count("showMay19Commemoration &&") >= 2
