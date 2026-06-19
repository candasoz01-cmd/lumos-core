"""Phase 1: panel görev sil — parse + server ref eşlemesi (panel.astro ile hizalı)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _canonicalize_task_input(raw: str) -> str:
    s = str(raw or "").strip()
    s = re.sub(r"\bgorev\b", "görev", s, flags=re.I)
    s = re.sub(r"\bolustur\b", "oluştur", s, flags=re.I)
    return s.lower().strip()


def parse_panel_gorev_sil(raw: str) -> dict[str, str] | None:
    """panel.astro parsePanelGorevKomutu sil dalının Python aynası."""
    s0 = str(raw or "").strip()
    if not s0:
        return None
    s = _canonicalize_task_input(s0)
    m = re.match(r"^(?:görev|gorev)\s+sil(?=\s|:|$)", s, re.I)
    if not m:
        return None
    ref = re.sub(r"^\s*:+\s*", "", s[m.end() :]).strip()
    return {"verb": "sil", "ref": ref}


def test_parse_panel_gorev_sil_basic() -> None:
    assert parse_panel_gorev_sil("görev sil alışveriş") == {"verb": "sil", "ref": "alışveriş"}
    assert parse_panel_gorev_sil("gorev sil: tsk_abc") == {"verb": "sil", "ref": "tsk_abc"}
    assert parse_panel_gorev_sil("görev sil") == {"verb": "sil", "ref": ""}


def test_parse_panel_gorev_sil_not_create() -> None:
    assert parse_panel_gorev_sil("görev oluştur alışveriş") is None
    assert parse_panel_gorev_sil("mini görev ekle test") is None


def test_panel_tasks_server_find_by_ref_title() -> None:
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    doc = {
        "tasks": [
            {"id": "tsk_1", "title": "Alışveriş listesi", "status": "active"},
            {"id": "tsk_2", "title": "Rapor yaz", "status": "done"},
        ]
    }
    assert pts._find_task_by_ref(doc, "tsk_1") is not None
    assert pts._find_task_by_ref(doc, "alışveriş listesi") is not None
    assert pts._find_task_by_ref(doc, "alışveriş-listesi") is not None
    assert pts._find_task_by_ref(doc, "yok") is None
