"""KA-001: Agent Status sözleşmesi v1 — doğrulama, normalize etme, çakışma."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.agent_status_contract import (  # noqa: E402
    LEGACY_AGENT_ID,
    SCHEMA_VERSION,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    STATUS_UNKNOWN,
    AgentStatusRecord,
    detect_ownership_conflicts,
    load_agent_status_records,
    record_from_payload,
    validate_agent_status_payload,
)


def _valid_payload(**overrides: object) -> dict:
    payload = {
        "version": SCHEMA_VERSION,
        "agent_id": "claude.code",
        "job_id": "abc123",
        "status": STATUS_RUNNING,
        "owner": "claude.code",
        "started_at": "2026-07-19T10:00:00+00:00",
        "updated_at": "2026-07-19T10:05:00+00:00",
        "evidence_ref": "outbox/agent_status_abc123.json",
        "progress": 40,
        "message": "tests",
    }
    payload.update(overrides)
    return payload


def _write_legacy(outbox: Path, job_id: str, *, status: str = "running", phase: str = "plan") -> Path:
    path = outbox / f"agent_status_{job_id}.json"
    path.write_text(
        json.dumps({"job_id": job_id, "phase": phase, "status": status, "final_report": None, "errors": []}),
        encoding="utf-8",
    )
    return path


# --- Doğrulama ---


def test_valid_payload_passes() -> None:
    assert validate_agent_status_payload(_valid_payload()) == []


def test_optional_fields_may_be_absent() -> None:
    payload = _valid_payload()
    for key in ("started_at", "updated_at", "progress", "message"):
        payload.pop(key)
    assert validate_agent_status_payload(payload) == []


def test_missing_required_fields_are_each_reported() -> None:
    errors = validate_agent_status_payload({"version": SCHEMA_VERSION})
    for expected in ("agent_id_missing", "job_id_missing", "owner_missing", "evidence_ref_missing", "status_invalid"):
        assert expected in errors


def test_invalid_values_are_rejected() -> None:
    assert "version_invalid" in validate_agent_status_payload(_valid_payload(version=2))
    assert "status_invalid" in validate_agent_status_payload(_valid_payload(status="paused"))
    assert "progress_invalid" in validate_agent_status_payload(_valid_payload(progress=101))
    assert "progress_invalid" in validate_agent_status_payload(_valid_payload(progress=True))
    assert "started_at_invalid" in validate_agent_status_payload(_valid_payload(started_at="dün"))
    assert validate_agent_status_payload([]) == ["payload_not_object"]


def test_record_from_payload_rejects_invalid() -> None:
    try:
        record_from_payload(_valid_payload(job_id=""))
    except ValueError as e:
        assert "job_id_missing" in str(e)
    else:
        raise AssertionError("ValueError bekleniyordu")


# --- Eski dosyaların salt okunur normalize edilmesi ---


def test_legacy_running_file_is_normalized(tmp_path: Path) -> None:
    path = _write_legacy(tmp_path, "deadbeef01", status="running", phase="apply_patch")
    result = load_agent_status_records(tmp_path)
    assert result.issues == []
    assert len(result.records) == 1
    record = result.records[0]
    assert record == AgentStatusRecord(
        version=SCHEMA_VERSION,
        agent_id=LEGACY_AGENT_ID,
        job_id="deadbeef01",
        status=STATUS_RUNNING,
        owner=LEGACY_AGENT_ID,
        started_at=None,
        updated_at=record.updated_at,
        evidence_ref=str(path),
        progress=None,
        message="apply_patch",
    )
    assert record.updated_at is not None


def test_legacy_completed_and_failed_statuses_survive(tmp_path: Path) -> None:
    _write_legacy(tmp_path, "aa11", status="completed", phase="done")
    _write_legacy(tmp_path, "bb22", status="failed", phase="error")
    _write_legacy(tmp_path, "cc33", status="exploded", phase="???")
    statuses = {r.job_id: r.status for r in load_agent_status_records(tmp_path).records}
    assert statuses == {"aa11": STATUS_COMPLETED, "bb22": STATUS_FAILED, "cc33": STATUS_UNKNOWN}


def test_legacy_missing_job_id_falls_back_to_filename(tmp_path: Path) -> None:
    path = tmp_path / "agent_status_f00d.json"
    path.write_text(json.dumps({"phase": "plan", "status": "running"}), encoding="utf-8")
    records = load_agent_status_records(tmp_path).records
    assert len(records) == 1
    assert records[0].job_id == "f00d"


def test_native_v1_file_passes_through(tmp_path: Path) -> None:
    path = tmp_path / "agent_status_abc123.json"
    path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
    result = load_agent_status_records(tmp_path)
    assert result.issues == []
    assert result.records[0].agent_id == "claude.code"
    assert result.records[0].progress == 40


def test_malformed_files_become_issues_not_crashes(tmp_path: Path) -> None:
    (tmp_path / "agent_status_bad1.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "agent_status_bad2.json").write_text("[1, 2]", encoding="utf-8")
    _write_legacy(tmp_path, "good1")
    result = load_agent_status_records(tmp_path)
    assert len(result.records) == 1
    assert result.records[0].job_id == "good1"
    assert sorted(result.issues) == [
        "agent_status_bad1.json: unreadable_or_invalid_json",
        "agent_status_bad2.json: payload_not_object",
    ]


def test_loader_never_writes(tmp_path: Path) -> None:
    path = _write_legacy(tmp_path, "abcd")
    before = path.read_bytes()
    load_agent_status_records(tmp_path)
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["agent_status_abcd.json"]


def test_missing_directory_is_empty_result(tmp_path: Path) -> None:
    result = load_agent_status_records(tmp_path / "yok")
    assert result.records == [] and result.issues == []


# --- Sahiplik çakışması ---


def _record(job_id: str, owner: str) -> AgentStatusRecord:
    return record_from_payload(_valid_payload(job_id=job_id, owner=owner, agent_id=owner))


def test_same_owner_is_not_a_conflict() -> None:
    records = [_record("j1", "claude.code"), _record("j1", "claude.code"), _record("j2", "codex")]
    assert detect_ownership_conflicts(records) == []


def test_conflicting_owners_are_reported_per_job() -> None:
    records = [
        _record("j1", "claude.code"),
        _record("j1", "codex"),
        _record("j2", "cursor"),
        _record("j2", "codex"),
        _record("j3", "codex"),
    ]
    conflicts = detect_ownership_conflicts(records)
    assert [(c.job_id, c.owners) for c in conflicts] == [
        ("j1", ("claude.code", "codex")),
        ("j2", ("codex", "cursor")),
    ]
