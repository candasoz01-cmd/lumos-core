from __future__ import annotations

import json
import logging
from pathlib import Path

from core.evidence_continuity import (
    OPERATION_GUARD_DECISION,
    OUTCOME_ERROR,
    PHASE_AFTER,
    SOURCE_GUARD_AUDIT,
    STORE_GUARD,
    evidence_continuity_path,
    validate_evidence_record,
)
from core.guard_audit import GuardEvent, record_guard_event


def test_record_guard_event_logs_allow_decision(caplog):
    path = Path("/tmp/example.txt")
    event = GuardEvent(
        action="write",
        decision="allow",
        path=path,
        sandbox_mode=False,
        reason="sandbox_disabled",
        caller="test",
    )

    logger_name = "lumos.guard"
    with caplog.at_level(logging.INFO, logger=logger_name):
        record_guard_event(event)

    assert any(
        "guard_decision" in rec.message
        and "decision=allow" in rec.message
        and "path=/tmp/example.txt" in rec.message
        for rec in caplog.records
        if rec.name == logger_name
    )


def test_record_guard_event_logs_deny_decision_as_warning(caplog):
    path = Path("/tmp/protected.txt")
    event = GuardEvent(
        action="write",
        decision="deny",
        path=path,
        sandbox_mode=True,
        reason="core_state_under_live_base",
        caller="test",
    )

    logger_name = "lumos.guard"
    with caplog.at_level(logging.WARNING, logger=logger_name):
        record_guard_event(event)

    assert any(
        rec.levelno == logging.WARNING
        and "guard_decision" in rec.message
        and "decision=deny" in rec.message
        and "path=/tmp/protected.txt" in rec.message
        for rec in caplog.records
        if rec.name == logger_name
    )


def test_record_guard_event_deny_mirrors_to_journal(tmp_path, caplog, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    path = tmp_path / "tasks" / "tasks.json"
    event = GuardEvent(
        action="write",
        decision="deny",
        path=path,
        sandbox_mode=True,
        reason="core_state_under_live_base",
        caller="test",
    )

    logger_name = "lumos.guard"
    with caplog.at_level(logging.WARNING, logger=logger_name):
        record_guard_event(event)

    journal = evidence_continuity_path(tmp_path)
    assert journal.is_file()
    records = [
        json.loads(line)
        for line in journal.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    rec = records[0]
    assert rec["source"] == SOURCE_GUARD_AUDIT
    assert rec["store"] == STORE_GUARD
    assert rec["operation"] == OPERATION_GUARD_DECISION
    assert rec["phase"] == PHASE_AFTER
    assert rec["outcome"] == OUTCOME_ERROR
    assert validate_evidence_record(rec) == []


def test_record_guard_event_allow_no_journal_line(tmp_path, caplog):
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

    assert not evidence_continuity_path(tmp_path).exists()

