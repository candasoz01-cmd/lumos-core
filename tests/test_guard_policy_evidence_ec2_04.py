"""EC2-04: guard deny / policy block evidence journal mirror (T1–T10)."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_BRIDGE_TASK_POST,
    OPERATION_GUARD_DECISION,
    OPERATION_POLICY_BLOCKED,
    OUTCOME_ERROR,
    PHASE_AFTER,
    SOURCE_ACTION_POLICY,
    SOURCE_GUARD_AUDIT,
    SOURCE_KANDO_BRIDGE,
    STORE_BRIDGE_OUTBOX,
    STORE_GUARD,
    STORE_POLICY_LOG,
    append_evidence_event,
    build_evidence_record,
    evidence_continuity_path,
    generate_correlation_id,
    mirror_guard_event_record,
    mirror_policy_blocked_record,
    mirror_post_task_outbox_record,
    validate_evidence_record,
)
from core.guard_audit import GuardEvent, record_guard_event  # noqa: E402
from core.workspace_contract import allow_write_to_core  # noqa: E402
from policy.action_policy import log_policy_blocked  # noqa: E402


def _read_journal_records(tmp_path: Path) -> list[dict]:
    journal = evidence_continuity_path(tmp_path)
    if not journal.is_file():
        return []
    return [
        json.loads(line)
        for line in journal.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]


def test_t1_sandbox_deny_writes_guard_journal_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T1: sandbox deny → one journal line; source guard_audit, outcome error."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    core_path = tmp_path / "tasks" / "tasks.json"
    allowed = allow_write_to_core(tmp_path, core_path, is_sandbox_mode=True)
    assert allowed is False
    records = _read_journal_records(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["source"] == SOURCE_GUARD_AUDIT
    assert rec["store"] == STORE_GUARD
    assert rec["operation"] == OPERATION_GUARD_DECISION
    assert rec["phase"] == PHASE_AFTER
    assert rec["outcome"] == OUTCOME_ERROR
    assert validate_evidence_record(rec) == []


def test_t2_guard_allow_no_journal_line(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """T2: guard allow → no journal line."""
    event = GuardEvent(
        action="write",
        decision="allow",
        path=Path("/tmp/example.txt"),
        sandbox_mode=False,
        reason="sandbox_disabled",
        caller="test",
    )
    logger_name = "lumos.guard"
    with caplog.at_level(logging.INFO, logger=logger_name):
        record_guard_event(event)
    assert _read_journal_records(tmp_path) == []


def test_t3_policy_block_writes_journal_and_log_txt(tmp_path: Path) -> None:
    """T3: policy block → journal + log.txt; source action_policy."""
    log_policy_blocked(str(tmp_path), "create_task", "offline_mode")
    log_txt = tmp_path / "logs" / "log.txt"
    assert log_txt.is_file()
    assert "policy_blocked" in log_txt.read_text(encoding="utf-8")
    records = _read_journal_records(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["source"] == SOURCE_ACTION_POLICY
    assert rec["store"] == STORE_POLICY_LOG
    assert rec["operation"] == OPERATION_POLICY_BLOCKED
    assert rec["payload_summary"]["route"] == "cli:task_mutation"
    assert validate_evidence_record(rec) == []


def test_t4_append_evidence_no_guard_allow_journal_or_explosion(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """T4: append_evidence_event → guard allow log only; no guard allow journal; no loop."""
    record = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_KANDO_BRIDGE,
        store=STORE_BRIDGE_OUTBOX,
        operation=OPERATION_BRIDGE_TASK_POST,
        phase=PHASE_AFTER,
        outcome="ok",
        payload_summary={"route": "POST /task"},
    )
    logger_name = "lumos.guard"
    with caplog.at_level(logging.INFO, logger=logger_name):
        result = append_evidence_event(tmp_path, record)
    assert result.get("appended") is True
    assert any("decision=allow" in rec.message for rec in caplog.records if rec.name == logger_name)
    records = _read_journal_records(tmp_path)
    assert len(records) == 1
    assert all(r.get("source") != SOURCE_GUARD_AUDIT for r in records)


def test_t5_guard_deny_payload_basename_only_no_full_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T5: guard deny payload — no full path; basename in title_preview."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    full_path = tmp_path / "tasks" / "tasks.json"
    allow_write_to_core(tmp_path, full_path, is_sandbox_mode=True)
    records = _read_journal_records(tmp_path)
    assert len(records) == 1
    payload = records[0]["payload_summary"]
    assert payload["title_preview"] == "tasks.json"
    journal_text = evidence_continuity_path(tmp_path).read_text(encoding="utf-8")
    assert str(full_path) not in journal_text


def test_t6_every_journal_line_passes_validator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T6: each journal line validates cleanly."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    allow_write_to_core(tmp_path, tmp_path / "aliases.json", is_sandbox_mode=True)
    log_policy_blocked(str(tmp_path), "delete_task", "koruma_aktif_delete")
    for rec in _read_journal_records(tmp_path):
        assert validate_evidence_record(rec) == []


def test_t7_two_policy_blocks_two_journal_appends(tmp_path: Path) -> None:
    """T7: two consecutive policy blocks → log.txt 2 lines; journal 2 appends."""
    log_policy_blocked(str(tmp_path), "create_task", "offline_mode")
    log_policy_blocked(str(tmp_path), "delete_task", "koruma_aktif_delete")
    log_txt = (tmp_path / "logs" / "log.txt").read_text(encoding="utf-8").strip().splitlines()
    assert len(log_txt) == 2
    records = _read_journal_records(tmp_path)
    assert len(records) == 2
    assert all(r["source"] == SOURCE_ACTION_POLICY for r in records)


def test_t8_enum_and_payload_keys_regression() -> None:
    """T8: new enum values and payload keys pass frozenset validator."""
    guard_rec = mirror_guard_event_record(
        GuardEvent(
            action="write",
            decision="deny",
            path=Path("/secret/path/tasks.json"),
            sandbox_mode=True,
            reason="core_state_under_live_base",
            caller="workspace_contract.allow_write_to_core",
        )
    )
    assert guard_rec["source"] == SOURCE_GUARD_AUDIT
    assert validate_evidence_record(guard_rec) == []
    policy_rec = mirror_policy_blocked_record("create_task", "offline_mode")
    assert policy_rec["source"] == SOURCE_ACTION_POLICY
    assert validate_evidence_record(policy_rec) == []
    bridge_rec = mirror_post_task_outbox_record(
        {"raw": b'{"goal": "x"}', "route": "agent"},
        {"http_status": 200, "response": {"accepted": True}},
    )
    assert validate_evidence_record(bridge_rec) == []


def test_t9_existing_guard_and_policy_channels_preserved(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T9: logging + log.txt behavior preserved alongside journal mirror."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    deny_event = GuardEvent(
        action="write",
        decision="deny",
        path=Path("/tmp/protected.txt"),
        sandbox_mode=True,
        reason="core_state_under_live_base",
        caller="test",
    )
    logger_name = "lumos.guard"
    with caplog.at_level(logging.WARNING, logger=logger_name):
        record_guard_event(deny_event)
    assert any(
        rec.levelno == logging.WARNING and "decision=deny" in rec.message
        for rec in caplog.records
        if rec.name == logger_name
    )
    log_policy_blocked(str(tmp_path), "create_task", "offline_mode")
    log_txt = (tmp_path / "logs" / "log.txt").read_text(encoding="utf-8")
    assert "policy_blocked" in log_txt
    assert "action=create_task" in log_txt


def test_t10_bridge_ec2_03_mirror_regression() -> None:
    """T10: EC2-03 bridge mirror enum still validates."""
    rec = mirror_post_task_outbox_record(
        {"raw": b'{"goal": "regression"}', "route": "agent"},
        {"http_status": 200, "response": {"accepted": True}},
    )
    assert rec["source"] == SOURCE_KANDO_BRIDGE
    assert rec["store"] == STORE_BRIDGE_OUTBOX
    assert rec["operation"] == OPERATION_BRIDGE_TASK_POST
    assert validate_evidence_record(rec) == []
