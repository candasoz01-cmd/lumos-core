"""EC2-07: tasks.json events[] projection metadata — E1–E6."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    AUDIT_TRUTH_EVIDENCE_JOURNAL,
    EVENTS_DEPRECATION_SOFT_V1,
    EVENTS_PROJECTION_ROLE,
    TASKS_JSON_EVENTS_PROJECTION_POLICY_ID,
    enrich_tasks_doc_api_response,
    tasks_json_events_projection_meta,
)


def _load_panel_tasks_server():
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    return pts


def test_e1_projection_meta_policy() -> None:
    meta = tasks_json_events_projection_meta()
    assert meta["policy_id"] == TASKS_JSON_EVENTS_PROJECTION_POLICY_ID
    assert meta["role"] == EVENTS_PROJECTION_ROLE
    assert meta["audit_truth"] == AUDIT_TRUTH_EVIDENCE_JOURNAL
    assert meta["reconcile_with_journal"] is False
    assert meta["deprecation_status"] == EVENTS_DEPRECATION_SOFT_V1


def test_e2_enrich_empty_doc() -> None:
    out = enrich_tasks_doc_api_response({"v": 1, "tasks": [], "events": []})
    assert out["events_meta"]["events_count"] == 0


def test_e3_enrich_with_events() -> None:
    doc = {
        "v": 1,
        "tasks": [{"id": "tsk_1"}],
        "events": [{"id": "ev_1"}, {"id": "ev_2"}],
    }
    out = enrich_tasks_doc_api_response(doc)
    assert out["events_meta"]["events_count"] == 2
    assert len(out["events"]) == 2


def test_e4_read_doc_unchanged_on_disk(tmp_path, monkeypatch) -> None:
    pts = _load_panel_tasks_server()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(
        '{"v":1,"tasks":[],"events":[{"id":"ev_x"}]}',
        encoding="utf-8",
    )
    doc = pts._read_doc()
    assert "events_meta" not in doc
    assert len(doc["events"]) == 1


def test_e5_get_handler_uses_enrich() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert "enrich_tasks_doc_api_response" in src


def test_e6_original_doc_not_mutated() -> None:
    doc = {"v": 1, "tasks": [], "events": [{"id": "ev_1"}]}
    out = enrich_tasks_doc_api_response(doc)
    assert "events_meta" not in doc
    assert "events_meta" in out
