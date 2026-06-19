"""EC2-08: evidence continuity read helper + UI projection — U1–U6, U12."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_BRIDGE_TASK_POST,
    OPERATION_PANEL_TASK_CREATE,
    OPERATION_POLICY_BLOCKED,
    OUTCOME_OK,
    PHASE_AFTER,
    PHASE_BEFORE,
    PHASE_RESULT,
    SOURCE_ACTION_POLICY,
    SOURCE_KANDO_BRIDGE,
    SOURCE_PANEL_TASKS_SERVER,
    STORE_BRIDGE_OUTBOX,
    STORE_PANEL_TASKS,
    STORE_POLICY_LOG,
    UI_PROJECTION_SCHEMA,
    append_evidence_event,
    build_evidence_record,
    build_ui_projection_response,
    evidence_continuity_path,
    generate_correlation_id,
    project_evidence_for_ui,
    read_recent_evidence_events,
    validate_evidence_record,
)


def _append(tmp_path: Path, record: dict) -> None:
    append_evidence_event(tmp_path, record)


def test_u1_empty_journal_returns_empty_events(tmp_path):
    events, truncated = read_recent_evidence_events(tmp_path)
    assert events == []
    assert truncated is False
    resp = build_ui_projection_response(events, truncated=truncated)
    assert resp == {"schema": UI_PROJECTION_SCHEMA, "events": [], "truncated": False}


def test_u2_skips_malformed_jsonl_line(tmp_path):
    path = evidence_continuity_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    recs = []
    for i in range(3):
        rec = build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_PANEL_TASKS_SERVER,
            store=STORE_PANEL_TASKS,
            operation=OPERATION_PANEL_TASK_CREATE,
            phase=PHASE_AFTER,
            outcome=OUTCOME_OK,
            mutation="create",
            entity_id=f"tsk_{i}",
        )
        recs.append(rec)
        _append(tmp_path, rec)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("{not valid json\n")
    events, _ = read_recent_evidence_events(tmp_path, limit=10)
    assert len(events) == 3
    assert all(validate_evidence_record(e) == [] for e in events)


def test_u3_limit_and_truncated_flag(tmp_path):
    for i in range(8):
        _append(
            tmp_path,
            build_evidence_record(
                correlation_id=generate_correlation_id(),
                source=SOURCE_PANEL_TASKS_SERVER,
                store=STORE_PANEL_TASKS,
                operation=OPERATION_PANEL_TASK_CREATE,
                phase=PHASE_AFTER,
                outcome=OUTCOME_OK,
                mutation="create",
                entity_id=f"tsk_{i}",
            ),
        )
    events, truncated = read_recent_evidence_events(tmp_path, limit=5)
    assert len(events) == 5
    assert truncated is True
    resp = build_ui_projection_response(events, truncated=truncated)
    assert resp["truncated"] is True
    assert len(resp["events"]) == 5


def test_u4_payload_summary_only_allowed_keys(tmp_path):
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_KANDO_BRIDGE,
        store=STORE_BRIDGE_OUTBOX,
        operation=OPERATION_BRIDGE_TASK_POST,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        payload_summary={"title_preview": "README düzelt", "route": "agent/async", "job_id": "abc123"},
    )
    _append(tmp_path, rec)
    events, _ = read_recent_evidence_events(tmp_path)
    dto = project_evidence_for_ui(events[0])
    assert set((dto.get("payload_summary") or {}).keys()) <= {
        "title_preview",
        "route",
        "task_count",
        "events_appended",
        "trash_written",
        "step_count",
        "action",
        "reason_code",
        "job_id",
    }


def test_u5_projection_strips_secret_like_extra_fields():
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_secret",
        payload_summary={"title_preview": "normal"},
    )
    rec["api_key"] = "sk-live-should-not-leak"
    rec["payload_summary"]["secret_token"] = "bad"
    dto = project_evidence_for_ui(rec)
    assert "correlation_id" not in dto
    assert "api_key" not in dto
    assert "secret_token" not in (dto.get("payload_summary") or {})


def test_u6_panel_create_after_has_entity_ref_and_mutation(tmp_path):
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_panel01",
    )
    _append(tmp_path, rec)
    dto = project_evidence_for_ui(read_recent_evidence_events(tmp_path)[0][0])
    assert dto["entity_ref"] == {"kind": "task", "id": "tsk_panel01"}
    assert dto["mutation"] == "create"


def test_u12_regression_existing_validator_still_passes(tmp_path):
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_ACTION_POLICY,
        store=STORE_POLICY_LOG,
        operation=OPERATION_POLICY_BLOCKED,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        payload_summary={"reason_code": "blocked", "action": "delete", "route": "cli:task_mutation"},
    )
    assert validate_evidence_record(rec) == []
    _append(tmp_path, rec)
    lines = evidence_continuity_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        assert validate_evidence_record(json.loads(line)) == []


def test_read_newest_first_by_ts(tmp_path):
    older = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_BEFORE,
        outcome=OUTCOME_OK,
        mutation="create",
    )
    older["ts"] = "2026-06-19T10:00:00.000Z"
    newer = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_new",
    )
    newer["ts"] = "2026-06-19T12:00:00.000Z"
    _append(tmp_path, older)
    _append(tmp_path, newer)
    events, _ = read_recent_evidence_events(tmp_path, limit=2)
    assert events[0]["phase"] == PHASE_AFTER
    assert events[1]["phase"] == PHASE_BEFORE


def test_bridge_result_projection_includes_job_id(tmp_path):
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_KANDO_BRIDGE,
        store=STORE_BRIDGE_OUTBOX,
        operation=OPERATION_BRIDGE_TASK_POST,
        phase=PHASE_RESULT,
        outcome=OUTCOME_OK,
        payload_summary={"title_preview": "agent task", "route": "agent/async", "job_id": "job123"},
    )
    _append(tmp_path, rec)
    dto = project_evidence_for_ui(read_recent_evidence_events(tmp_path)[0][0])
    assert dto["payload_summary"]["job_id"] == "job123"
