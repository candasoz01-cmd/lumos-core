"""Görevler API skip rozeti — prod + loopback API sessiz atlama görünürlüğü."""

from __future__ import annotations

from pathlib import Path

from tests.test_panel_component_split import read_panel_source

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"

GOREVLER_SYNC_SKIP_BADGE_LABEL = "yalnızca bu cihaz / sunucu senkronu kapalı"


def test_gorevler_sync_badge_markup_present() -> None:
    text = read_panel_source()
    assert 'id="gorevler-sync-badge"' in text
    assert GOREVLER_SYNC_SKIP_BADGE_LABEL in text


def test_sync_gorevler_tasks_api_skip_badge_wiring() -> None:
    text = read_panel_source()
    assert "function syncGorevlerTasksApiSkipBadge()" in text
    assert "shouldSkipGorevlerTasksApi()" in text.split("function syncGorevlerTasksApiSkipBadge()", 1)[1].split(
        "function shouldFallbackGorevlerTasksLocal", 1
    )[0]


def test_gorevler_init_calls_sync_badge() -> None:
    text = read_panel_source()
    wire_block = text.split("function wireGorevlerPrototype()", 1)[1].split("wirePanel();", 1)[0]
    assert "syncGorevlerTasksApiSkipBadge();" in wire_block
