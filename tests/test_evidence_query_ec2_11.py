"""EC2-11: structured evidence query — Q1–Q6."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    EVIDENCE_QUERY_READ_SCOPE,
    EVIDENCE_QUERY_SCHEMA,
    OPERATION_PANEL_TASK_CREATE,
    OUTCOME_OK,
    PHASE_AFTER,
    SOURCE_PANEL_TASKS_SERVER,
    STORE_PANEL_TASKS,
    append_evidence_event,
    build_evidence_record,
    build_evidence_query_response,
    filter_evidence_events,
    generate_correlation_id,
    query_evidence_events,
)


def _append(tmp_path: Path, **kwargs) -> None:
    append_evidence_event(
        tmp_path,
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=kwargs.get("source", SOURCE_PANEL_TASKS_SERVER),
            store=kwargs.get("store", STORE_PANEL_TASKS),
            operation=kwargs.get("operation", OPERATION_PANEL_TASK_CREATE),
            phase=kwargs.get("phase", PHASE_AFTER),
            outcome=kwargs.get("outcome", OUTCOME_OK),
            mutation=kwargs.get("mutation", "create"),
            entity_id=kwargs.get("entity_id"),
        ),
    )


def test_q1_filter_by_entity_id() -> None:
    events = [
        {"entity_ref": {"id": "tsk_a"}, "operation": "panel.task.create", "source": "panel_tasks_server"},
        {"entity_ref": {"id": "tsk_b"}, "operation": "panel.task.create", "source": "panel_tasks_server"},
    ]
    out = filter_evidence_events(events, entity_id="tsk_a")
    assert len(out) == 1
    assert out[0]["entity_ref"]["id"] == "tsk_a"


def test_q2_query_response_schema(tmp_path: Path) -> None:
    _append(tmp_path, entity_id="tsk_q2")
    resp = query_evidence_events(tmp_path, entity_id="tsk_q2")
    assert resp["schema"] == EVIDENCE_QUERY_SCHEMA
    assert resp["read_scope"] == EVIDENCE_QUERY_READ_SCOPE
    assert resp["filters"]["entity_id"] == "tsk_q2"


def test_q3_query_no_match(tmp_path: Path) -> None:
    _append(tmp_path, entity_id="tsk_other")
    resp = query_evidence_events(tmp_path, entity_id="tsk_missing")
    assert resp["events"] == []


def test_q4_build_query_response_filters() -> None:
    resp = build_evidence_query_response([], filters={"entity_id": "tsk_x"})
    assert resp["filters"]["entity_id"] == "tsk_x"


def test_q5_panel_server_route() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert "/evidence/query" in src
    assert "build_evidence_query_response_from_base" in src


def test_q6_filter_by_operation_and_source() -> None:
    events = [
        {"operation": "panel.task.create", "source": "panel_tasks_server", "entity_ref": {"id": "tsk_1"}},
        {"operation": "guard.decision", "source": "guard_audit"},
    ]
    out = filter_evidence_events(events, operation="guard.decision", source="guard_audit")
    assert len(out) == 1
    assert out[0]["operation"] == "guard.decision"
