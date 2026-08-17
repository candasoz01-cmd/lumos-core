"""EC2-13: köprü async agent tamamlanması → evidence journal `result` faz (R1–R10)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_BRIDGE_TASK_POST,
    OUTCOME_ERROR,
    OUTCOME_OK,
    PHASE_AFTER,
    PHASE_RESULT,
    SOURCE_GUARD_AUDIT,
    SOURCE_KANDO_BRIDGE,
    STORE_BRIDGE_OUTBOX,
    append_evidence_event,
    evidence_continuity_path,
    mirror_bridge_agent_result_record,
    mirror_bridge_agent_result_to_evidence_journal,
    mirror_guard_event_record,
    mirror_post_task_outbox_record,
    validate_evidence_record,
)
from core.guard_audit import GuardEvent  # noqa: E402


def _read_journal_records(tmp_path: Path) -> list[dict]:
    journal = evidence_continuity_path(tmp_path)
    if not journal.is_file():
        return []
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").strip().splitlines() if line.strip()]


def test_r1_ok_final_report_result_phase(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1: status ok → phase result, outcome ok."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    fr = {"status": "ok", "task": "README düzelt", "changed_files": ["src/core/x.py"]}
    mirror_bridge_agent_result_to_evidence_journal("a1b2c3d4e5f67890", fr, base_dir=tmp_path)
    records = _read_journal_records(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["phase"] == PHASE_RESULT
    assert rec["outcome"] == OUTCOME_OK
    assert rec["source"] == SOURCE_KANDO_BRIDGE
    assert rec["operation"] == OPERATION_BRIDGE_TASK_POST


def test_r2_failed_final_report_outcome_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R2: status failed → outcome error."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    fr = {"status": "failed", "task": "risky change", "errors": ["verify_failed"]}
    mirror_bridge_agent_result_to_evidence_journal("b2c3d4e5f6789012", fr, base_dir=tmp_path)
    rec = _read_journal_records(tmp_path)[0]
    assert rec["phase"] == PHASE_RESULT
    assert rec["outcome"] == OUTCOME_ERROR
    assert rec["error"]["code"] == "verify_failed"


def test_r3_partial_status_outcome_error() -> None:
    """R3: status partial → outcome error with agent_partial code when no errors list."""
    fr = {"status": "partial", "task": "partial work"}
    rec = mirror_bridge_agent_result_record("c3d4e5f678901234", fr)
    assert rec["outcome"] == OUTCOME_ERROR
    assert rec["error"]["code"] == "agent_partial"


def test_r4_payload_summary_job_id() -> None:
    """R4: payload_summary.job_id present and truncated."""
    long_id = "x" * 64
    rec = mirror_bridge_agent_result_record(long_id, {"status": "ok", "task": "t"})
    assert rec["payload_summary"]["job_id"] == "x" * 32
    assert rec["payload_summary"]["route"] == "agent/async"


def test_r5_no_final_report_secrets_in_journal() -> None:
    """R5: commit hash / changed_files not in journal record."""
    fr = {
        "status": "ok",
        "task": "safe task",
        "changed_files": ["src/core/secret.py"],
        "commit": {"ok": True, "hash": "deadbeef" * 5},
    }
    rec = mirror_bridge_agent_result_record("job1", fr)
    dumped = json.dumps(rec)
    assert "deadbeef" not in dumped
    assert "secret.py" not in dumped
    assert "changed_files" not in dumped


def test_r6_after_and_result_two_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R6: EC2-03 after + EC2-13 result → two journal lines."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    raw = json.dumps({"goal": "README düzelt"}, ensure_ascii=False).encode()
    after_rec = mirror_post_task_outbox_record(
        {"raw": raw, "route": "agent"},
        {"http_status": 200, "response": {"accepted": True, "ok": True}},
    )
    append_evidence_event(tmp_path, after_rec)
    mirror_bridge_agent_result_to_evidence_journal(
        "d4e5f67890123456",
        {"status": "ok", "task": "README düzelt"},
        base_dir=tmp_path,
    )
    records = _read_journal_records(tmp_path)
    assert len(records) == 2
    assert records[0]["phase"] == PHASE_AFTER
    assert records[1]["phase"] == PHASE_RESULT


def test_r7_sync_mirror_record_only_no_agent_hook() -> None:
    """R7: mirror_post_task_outbox_record never emits result phase."""
    rec = mirror_post_task_outbox_record(
        {"raw": b"{}", "route": "direct"},
        {"http_status": 200, "response": {"accepted": True}},
    )
    assert rec["phase"] == PHASE_AFTER


def test_r8_validate_evidence_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R8: every journal line passes validate_evidence_record."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    mirror_bridge_agent_result_to_evidence_journal("e5f6789012345678", {"status": "ok", "task": "t"}, base_dir=tmp_path)
    for rec in _read_journal_records(tmp_path):
        assert validate_evidence_record(rec) == []


def test_r9_bridge_enum_unchanged() -> None:
    """R9: same bridge enum triplet as EC2-03."""
    rec = mirror_bridge_agent_result_record("f678901234567890", {"status": "ok", "task": "t"})
    assert rec["source"] == SOURCE_KANDO_BRIDGE
    assert rec["store"] == STORE_BRIDGE_OUTBOX
    assert rec["operation"] == OPERATION_BRIDGE_TASK_POST


def test_r10_guard_deny_no_result_phase() -> None:
    """R10: guard deny uses after only — no result phase."""
    rec = mirror_guard_event_record(
        GuardEvent(
            action="write",
            decision="deny",
            path=Path("/tmp/tasks.json"),
            sandbox_mode=True,
            reason="core_state_under_live_base",
            caller="test",
        )
    )
    assert rec["phase"] == PHASE_AFTER
    assert rec["source"] == SOURCE_GUARD_AUDIT


def test_agent_runner_worker_mirrors_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration: start_agent_job success path appends result journal line."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    outbox = tmp_path / ".lumos" / "outbox"
    outbox.mkdir(parents=True)
    ok_report = {"status": "ok", "task": "agent goal", "changed_files": [], "errors": []}

    with patch("kando.agent_runner.run_agent_pipeline", return_value=ok_report):
        with patch("kando.agent_runner._copy_cursor_bridge_snapshots_to_outbox"):
            from kando.agent_runner import start_agent_job

            job_id = start_agent_job("agent goal", False, repo_root=tmp_path, outbox_dir=outbox)
            # Status dosyasındaki "completed" yayın noktasıdır: worker, evidence journal
            # mirror'ını bu yayından ÖNCE yazar (agent_runner sıralama sözleşmesi).
            status_path = outbox / f"agent_status_{job_id}.json"
            completed = False
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                if status_path.is_file():
                    data = json.loads(status_path.read_text(encoding="utf-8"))
                    if data.get("status") == "completed":
                        completed = True
                        break
                time.sleep(0.05)

    assert completed, "agent job status dosyası süresinde 'completed' olmadı"
    records = _read_journal_records(tmp_path)
    assert any(r.get("phase") == PHASE_RESULT for r in records)
