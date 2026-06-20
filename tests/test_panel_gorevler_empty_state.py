"""Görevler listesi boş durum — panel.astro empty state wiring."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"

GOREVLER_LIST_EMPTY_DEFAULT = (
    "Henüz görev yok. Yukarıdan kısa bir başlık yazıp «Görev ekle» kullanın."
)
GOREVLER_LIST_EMPTY_FILTER = (
    "Bu filtrede görev yok. «Tümü» ile tüm görevleri görebilirsin."
)


def test_gorevler_list_empty_markup_present() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert 'id="gorevler-list-empty"' in text
    assert "gorevler-list-empty" in text


def test_gorevler_list_empty_messages_present() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert GOREVLER_LIST_EMPTY_DEFAULT in text
    assert GOREVLER_LIST_EMPTY_FILTER in text


def test_gorevler_render_syncs_empty_state() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    render_block = text.split("function render()", 1)[1].split("function showHint", 1)[0]
    assert "let visibleCount = 0" in render_block
    assert "syncGorevlerListEmptyState(visibleCount)" in render_block
