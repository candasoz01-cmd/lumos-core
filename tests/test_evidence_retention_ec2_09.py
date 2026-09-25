"""EC2-09 — evidence retention policy and storage summary (T1–T8)."""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    EVIDENCE_RETENTION_POLICY_ID,
    OPERATION_PANEL_TASK_CREATE,
    OUTCOME_OK,
    PHASE_AFTER,
    SOURCE_PANEL_TASKS_SERVER,
    STORE_PANEL_TASKS,
    append_evidence_event,
    build_evidence_record,
    evidence_continuity_path,
    evidence_journal_storage_summary,
    evidence_retention_policy,
    generate_correlation_id,
    read_recent_evidence_events,
    validate_evidence_record,
)
from core.log_rotation import append_jsonl_with_rotation  # noqa: E402


def test_t1_evidence_retention_policy_constants():
    policy = evidence_retention_policy()
    assert policy["policy_id"] == EVIDENCE_RETENTION_POLICY_ID
    assert policy["max_bytes_per_file"] is None
    assert policy["rotated_files_kept"] == "all_existing"
    assert policy["max_file_slots"] is None
    assert policy["automatic_deletion"] is False
    assert policy["read_scope"] == "current_rotated_and_fallback"


def test_t2_append_uses_named_retention_constants(tmp_path, monkeypatch):
    import core.evidence_continuity as ec

    monkeypatch.setattr(ec, "EVIDENCE_CONTINUITY_MAX_BYTES", 50)
    path = evidence_continuity_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk = json.dumps({"schema": "x", "payload": "y" * 20}) + "\n"
    path.write_text(chunk * 3, encoding="utf-8")
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_r",
    )
    result = append_evidence_event(tmp_path, rec)
    assert result.get("appended") is True
    assert result.get("rotated") is False
    assert path.read_text(encoding="utf-8").startswith(chunk * 3)


def test_t3_storage_summary_empty_journal(tmp_path):
    summary = evidence_journal_storage_summary(tmp_path)
    assert summary["file_count"] == 0
    assert summary["total_bytes"] == 0
    assert summary["journal_path"] == str(evidence_continuity_path(tmp_path))


def test_t4_storage_summary_with_rotated_files(tmp_path):
    path = evidence_continuity_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"a":1}\n', encoding="utf-8")
    rotated = Path(str(path) + ".1")
    rotated.write_text('{"b":2}\n' * 2, encoding="utf-8")
    summary = evidence_journal_storage_summary(tmp_path)
    assert summary["file_count"] == 2
    assert summary["total_bytes"] > 0


def test_t5_build_evidence_recent_response_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    resp = pts.build_evidence_recent_response()
    assert "retention" in resp
    assert "storage" in resp
    assert resp["retention"]["policy_id"] == EVIDENCE_RETENTION_POLICY_ID
    assert resp["schema"] == "lumos.evidence_continuity.ui_projection.v1"


def test_t6_ec2_08_response_shape_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    resp = pts.build_evidence_recent_response(limit=5)
    assert "events" in resp
    assert "truncated" in resp
    assert isinstance(resp["events"], list)


def test_t7_journal_record_schema_unchanged():
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_t7",
    )
    assert validate_evidence_record(rec) == []


def test_t8_read_recent_includes_retained_rotation(tmp_path):
    path = evidence_continuity_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    old_rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_old",
        payload_summary={"title_preview": "old-marker"},
    )
    append_jsonl_with_rotation(path, old_rec, max_bytes=200, keep=2)
    new_rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_new",
        payload_summary={"title_preview": "new-marker"},
    )
    append_jsonl_with_rotation(path, new_rec, max_bytes=200, keep=2)
    events, _ = read_recent_evidence_events(tmp_path, limit=10)
    previews = [
        (e.get("payload_summary") or {}).get("title_preview")
        for e in events
        if isinstance(e, dict)
    ]
    assert "new-marker" in previews
    assert "old-marker" in previews


def test_retained_sources_newest_window_and_fallback_without_current(tmp_path):
    from core.evidence_settings import preserve_audit_fallback

    def record(day):
        rec = build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_PANEL_TASKS_SERVER, store=STORE_PANEL_TASKS,
            operation=OPERATION_PANEL_TASK_CREATE, phase=PHASE_AFTER,
            outcome=OUTCOME_OK, entity_id=f"task-{day}",
        )
        rec['ts'] = f'2026-09-{day:02d}T12:00:00.000Z'
        return rec

    path = evidence_continuity_path(tmp_path)
    path.parent.mkdir(parents=True)
    # Historical slots beyond the old rotation limit remain discoverable.
    rotated = Path(str(path) + '.99')
    rotated.write_text('\n'.join(json.dumps(record(day)) for day in (23, 21)))
    preserve_audit_fallback(tmp_path, record(24))
    fallback = tmp_path / 'evidence_archive' / 'audit_fallback'
    (fallback / 'broken.json').write_text('{')
    (fallback / 'unfinished.pending').write_text(json.dumps({'record': record(25)}))
    events, truncated = read_recent_evidence_events(tmp_path, limit=2)
    assert [rec['ts'] for rec in events] == [record(24)['ts'], record(23)['ts']]
    assert truncated is True
    all_events, truncated = read_recent_evidence_events(tmp_path, limit=10)
    assert len(all_events) == 3
    assert truncated is False
    assert rotated.exists()
    assert evidence_journal_storage_summary(tmp_path)['file_count'] == 1
