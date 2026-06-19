"""Evidence Continuity v1 helper and journal tests."""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    SCHEMA_V1,
    OPERATION_ENGINE_TASK_MUTATION,
    OPERATION_PANEL_TASK_CREATE,
    OUTCOME_OK,
    PHASE_AFTER,
    PHASE_BEFORE,
    SOURCE_PANEL_TASKS_SERVER,
    SOURCE_TASK_ENGINE,
    STORE_PANEL_TASKS,
    STORE_TASK_ENGINE,
    append_evidence_event,
    build_evidence_record,
    evidence_continuity_path,
    generate_correlation_id,
    sanitize_payload_summary,
    title_preview_from,
    validate_evidence_record,
)


def _assert_journal_lines_valid(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            assert validate_evidence_record(json.loads(line)) == []


def test_generate_correlation_id_is_uuid4():
    cid = generate_correlation_id()
    assert len(cid) == 36
    assert cid.count("-") == 4


def test_evidence_continuity_path_under_logs(tmp_path):
    p = evidence_continuity_path(tmp_path)
    assert p == tmp_path / "logs" / "evidence_continuity.jsonl"


def test_validate_evidence_record_requires_schema_fields():
    record = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_BEFORE,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_abc",
    )
    assert record["schema"] == SCHEMA_V1
    assert validate_evidence_record(record) == []


def test_validate_evidence_record_rejects_bad_source():
    record = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source="bad_source",
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_BEFORE,
        outcome=OUTCOME_OK,
    )
    errors = validate_evidence_record(record)
    assert any("invalid:source" in e for e in errors)


def test_validate_evidence_record_rejects_missing_correlation_id():
    record = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_BEFORE,
        outcome=OUTCOME_OK,
    )
    del record["correlation_id"]
    errors = validate_evidence_record(record)
    assert any("missing:correlation_id" in e for e in errors)


def test_sanitize_payload_summary_filters_keys():
    out = sanitize_payload_summary(
        {
            "title_preview": "hello\nworld",
            "route": "POST /tasks",
            "forbidden": "x",
            "task_count": "3",
        }
    )
    assert "forbidden" not in out
    assert out["title_preview"] == "hello world"
    assert out["task_count"] == 3


def test_title_preview_from_truncates():
    assert title_preview_from("a" * 50) == "a" * 40


def test_append_evidence_event_writes_jsonl(tmp_path):
    corr = generate_correlation_id()
    record = build_evidence_record(
        correlation_id=corr,
        source=SOURCE_TASK_ENGINE,
        store=STORE_TASK_ENGINE,
        operation=OPERATION_ENGINE_TASK_MUTATION,
        phase=PHASE_BEFORE,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="1",
        payload_summary={"step_count": 2},
    )
    result = append_evidence_event(tmp_path, record)
    assert result.get("appended") is True
    journal = evidence_continuity_path(tmp_path)
    assert journal.is_file()
    lines = journal.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["correlation_id"] == corr
    assert parsed["schema"] == SCHEMA_V1
    _assert_journal_lines_valid(journal)


def test_append_evidence_event_best_effort_invalid_record(tmp_path):
    result = append_evidence_event(tmp_path, {"schema": "bad"})
    assert result.get("appended") is False
    assert not evidence_continuity_path(tmp_path).exists()


def test_panel_write_doc_emits_before_after(tmp_path, monkeypatch):
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    import panel_tasks_server as pts  # noqa: E402

    doc = pts._empty_doc()
    doc["tasks"] = [{"id": "tsk_test", "title": "Demo", "status": "active"}]
    pts._write_doc(
        doc,
        evidence={
            "operation": OPERATION_PANEL_TASK_CREATE,
            "mutation": "create",
            "entity_id": "tsk_test",
            "route": "POST /tasks",
            "title_preview": "Demo",
            "events_appended": 0,
        },
    )
    journal = evidence_continuity_path(tmp_path)
    lines = journal.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    phases = [json.loads(line)["phase"] for line in lines]
    assert phases == [PHASE_BEFORE, PHASE_AFTER]
    corr_ids = {json.loads(line)["correlation_id"] for line in lines}
    assert len(corr_ids) == 1
    stores = {json.loads(line)["store"] for line in lines}
    assert stores == {STORE_PANEL_TASKS}
    _assert_journal_lines_valid(journal)
