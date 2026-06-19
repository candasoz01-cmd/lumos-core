"""Hardcoded action policy (CLI/panel ile aynı kurallar)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.evidence_continuity import (
    OPERATION_POLICY_BLOCKED,
    OUTCOME_ERROR,
    PHASE_AFTER,
    SOURCE_ACTION_POLICY,
    STORE_POLICY_LOG,
    evidence_continuity_path,
    validate_evidence_record,
)
from policy.action_policy import (
    ACCESS_IDENTITY,
    CANCEL_TASK,
    CREATE_TASK,
    DELETE_TASK,
    PolicyContext,
    check_policy,
    log_policy_blocked,
    policy_user_message,
)


def test_offline_blocks_create():
    r = check_policy(CREATE_TASK, PolicyContext(online=False, koruma_active=False, consent=True))
    assert not r.allowed
    assert r.reason == "offline_mode"


def test_online_allows_create_when_unlocked():
    r = check_policy(CREATE_TASK, PolicyContext(online=True, koruma_active=False, consent=False))
    assert r.allowed


def test_koruma_blocks_delete():
    r = check_policy(DELETE_TASK, PolicyContext(online=True, koruma_active=True, consent=True))
    assert not r.allowed
    assert r.reason == "koruma_aktif_delete"


def test_online_unlocked_allows_delete():
    r = check_policy(DELETE_TASK, PolicyContext(online=True, koruma_active=False, consent=True))
    assert r.allowed


def test_consent_blocks_identity():
    r = check_policy(ACCESS_IDENTITY, PolicyContext(online=True, koruma_active=False, consent=False))
    assert not r.allowed
    assert r.reason == "consent_required"


def test_cancel_blocked_offline():
    r = check_policy(CANCEL_TASK, PolicyContext(online=False, koruma_active=False, consent=True))
    assert not r.allowed


def test_policy_log_appends_line():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        log_policy_blocked(str(base), "create_task", "offline_mode")
        p = base / "logs" / "log.txt"
        assert p.is_file()
        txt = p.read_text(encoding="utf-8")
        assert "policy_blocked" in txt
        assert "action=create_task" in txt
        assert "reason=offline_mode" in txt
        assert "ts=" in txt


def test_policy_block_mirrors_to_evidence_journal():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        log_policy_blocked(str(base), "create_task", "offline_mode")
        journal = evidence_continuity_path(base)
        assert journal.is_file()
        records = [
            json.loads(line)
            for line in journal.read_text(encoding="utf-8").strip().splitlines()
            if line.strip()
        ]
        assert len(records) == 1
        rec = records[0]
        assert rec["source"] == SOURCE_ACTION_POLICY
        assert rec["store"] == STORE_POLICY_LOG
        assert rec["operation"] == OPERATION_POLICY_BLOCKED
        assert rec["phase"] == PHASE_AFTER
        assert rec["outcome"] == OUTCOME_ERROR
        assert rec["payload_summary"]["action"] == "create_task"
        assert rec["payload_summary"]["reason_code"] == "offline_mode"
        assert validate_evidence_record(rec) == []
        assert (base / "logs" / "log.txt").is_file()


def test_user_messages_non_empty():
    assert "[POLICY_BLOCKED]" in policy_user_message(CREATE_TASK, "offline_mode")
    assert "çevrimdışı" in policy_user_message(CREATE_TASK, "offline_mode")
    assert "koruma aktif" in policy_user_message(DELETE_TASK, "koruma_aktif_delete")
    assert "izin yok" in policy_user_message(ACCESS_IDENTITY, "consent_required")
