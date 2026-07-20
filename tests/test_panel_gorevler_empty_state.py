"""Görevler listesi boş durum — panel.astro empty state wiring."""

from __future__ import annotations

from pathlib import Path

from tests.test_panel_component_split import read_panel_source

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"

GOREVLER_LIST_EMPTY_I18N_KEYS = (
    'panelT("panel.modules.tasks.empty.listDefault")',
    'panelT("panel.modules.tasks.empty.listFilter")',
)


def test_gorevler_list_empty_markup_present() -> None:
    text = read_panel_source()
    assert 'id="gorevler-list-empty"' in text
    assert "gorevler-list-empty" in text


def test_gorevler_list_empty_messages_present() -> None:
    text = read_panel_source()
    for key in GOREVLER_LIST_EMPTY_I18N_KEYS:
        assert key in text, f"missing görevler empty i18n key: {key}"


def test_gorevler_render_syncs_empty_state() -> None:
    text = read_panel_source()
    render_block = text.split("function render()", 1)[1].split("function showHint", 1)[0]
    assert "let visibleCount = 0" in render_block
    assert "syncGorevlerListEmptyState(visibleCount)" in render_block
