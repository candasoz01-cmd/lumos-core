from __future__ import annotations

import logging
from pathlib import Path

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

