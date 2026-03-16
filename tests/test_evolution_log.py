from __future__ import annotations

from pathlib import Path

from core.evolution_log import (
    get_conflict_stats,
    get_failed_patches,
    get_recent_events,
    get_rollbacks,
    record_event,
)


def test_record_and_read_event(tmp_path: Path, monkeypatch):
    log_file = tmp_path / "evolution.jsonl"
    monkeypatch.setattr("core.evolution_log.LOG_PATH", log_file)

    record_event(
        plan_id="plan-1",
        patch_ids=["p1", "p2"],
        action_type="PLAN_CREATED",
        result="ok",
        affected_paths=["/tmp/a.py", "/tmp/b.py"],
        sensitivity_levels=["CRITICAL"],
        rollback_occurred=False,
        conflict_detected=False,
    )

    events = get_recent_events(1)
    assert len(events) == 1
    e = events[0]
    assert e["plan_id"] == "plan-1"
    assert e["patch_ids"] == ["p1", "p2"]
    assert e["action_type"] == "PLAN_CREATED"
    assert e["affected_paths"] == ["/tmp/a.py", "/tmp/b.py"]
    assert e["sensitivity_levels"] == ["CRITICAL"]


def test_failed_patches_and_conflicts_and_rollbacks(tmp_path: Path, monkeypatch):
    log_file = tmp_path / "evolution.jsonl"
    monkeypatch.setattr("core.evolution_log.LOG_PATH", log_file)

    record_event(
        plan_id="plan-1",
        patch_ids=["p1"],
        action_type="PATCH_FAILED",
        result="error",
        affected_paths=["/tmp/a.py"],
        sensitivity_levels=[],
        rollback_occurred=False,
        conflict_detected=False,
    )
    record_event(
        plan_id="plan-1",
        patch_ids=["p1"],
        action_type="TRANSACTION_CONFLICT",
        result="error",
        affected_paths=["/tmp/a.py"],
        sensitivity_levels=[],
        rollback_occurred=False,
        conflict_detected=True,
    )
    record_event(
        plan_id="plan-1",
        patch_ids=["p1"],
        action_type="PATCH_ROLLED_BACK",
        result="rolled_back",
        affected_paths=["/tmp/a.py"],
        sensitivity_levels=[],
        rollback_occurred=True,
        conflict_detected=False,
    )

    failed = get_failed_patches()
    assert any(e["action_type"] == "PATCH_FAILED" for e in failed)

    rollbacks = get_rollbacks()
    assert any(e["rollback_occurred"] for e in rollbacks)

    stats = get_conflict_stats()
    assert stats["total_events"] == len(get_recent_events(10))
    assert stats["conflict_events"] >= 1
    assert stats["conflict_ratio"] > 0.0

