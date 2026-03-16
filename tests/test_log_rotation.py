"""Tests for JSONL log rotation (log_rotation)."""
from __future__ import annotations

import json
from pathlib import Path

from core.log_rotation import (
    append_jsonl_with_rotation,
    rotate_jsonl_log,
    DEFAULT_KEEP,
)


def test_append_to_new_file(tmp_path: Path) -> None:
    """Append to non-existent file creates it and writes one line."""
    p = tmp_path / "new.jsonl"
    rec = {"a": 1, "b": "test"}
    out = append_jsonl_with_rotation(p, rec, max_bytes=1000, keep=2)
    assert out["appended"] is True
    assert out["rotated"] is False
    assert p.exists()
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == rec


def test_append_without_rotation(tmp_path: Path) -> None:
    """Append when under size limit does not rotate."""
    p = tmp_path / "small.jsonl"
    p.write_text('{"x": 1}\n', encoding="utf-8")
    out = append_jsonl_with_rotation(p, {"x": 2}, max_bytes=10_000, keep=3)
    assert out["appended"] is True
    assert out["rotated"] is False
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1]) == {"x": 2}


def test_rotate_when_size_limit_exceeded(tmp_path: Path) -> None:
    """When file size >= max_bytes, rotation happens before append."""
    p = tmp_path / "big.jsonl"
    # Write enough to exceed a small limit (e.g. 50 bytes)
    chunk = '{"id": 1, "data": "hello"}\n'
    p.write_text(chunk * 5, encoding="utf-8")
    assert p.stat().st_size >= 50
    out = append_jsonl_with_rotation(p, {"id": 6}, max_bytes=50, keep=3)
    assert out["appended"] is True
    assert out["rotated"] is True
    # Current file should only have the new line
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"id": 6}
    # Rotated file .1 should exist with old content
    p1 = Path(str(p) + ".1")
    assert p1.exists()
    old_lines = p1.read_text(encoding="utf-8").strip().splitlines()
    assert len(old_lines) == 5


def test_keep_only_three_rotated_files(tmp_path: Path) -> None:
    """Only the newest `keep` rotated files are retained (e.g. .1, .2, .3)."""
    p = tmp_path / "log.jsonl"
    max_b = 40
    keep = 3
    # Force multiple rotations by appending and growing
    for i in range(10):
        rec = {"i": i, "payload": "x" * 20}
        append_jsonl_with_rotation(p, rec, max_bytes=max_b, keep=keep)
    # We should have at most: log.jsonl, log.jsonl.1, log.jsonl.2, log.jsonl.3
    rotated = [Path(str(p) + f".{n}") for n in range(1, keep + 1)]
    for r in rotated:
        assert r.exists(), f"expected {r} to exist"
    # .4 should not exist
    assert not Path(str(p) + ".4").exists()


def test_rotate_jsonl_log_missing_file_never_raises(tmp_path: Path) -> None:
    """rotate_jsonl_log on missing file returns rotated=False, does not raise."""
    p = tmp_path / "missing.jsonl"
    out = rotate_jsonl_log(p, max_bytes=100, keep=3)
    assert out["rotated"] is False
    assert out["size_before"] == 0


def test_evolution_log_still_writes(tmp_path: Path, monkeypatch) -> None:
    """Integration: evolution log record_event still writes via rotation."""
    from core.evolution_log import record_event, get_recent_events

    monkeypatch.setattr("core.evolution_log.LOG_PATH", tmp_path / "lumos_evolution.jsonl")
    record_event(
        plan_id=None,
        patch_ids=[],
        action_type="PLAN_CREATED",
        result="ok",
        affected_paths=[],
        sensitivity_levels=[],
        rollback_occurred=False,
        conflict_detected=False,
    )
    events = get_recent_events(5)
    assert len(events) >= 1
    assert events[-1]["action_type"] == "PLAN_CREATED"


def test_decision_feedback_log_still_writes(tmp_path: Path, monkeypatch) -> None:
    """Integration: decision feedback log record_execution still writes."""
    from core.decision_runner import DecisionExecutionResult
    from core.decision_model import MutationOption
    from core.evolution_tracker import record_execution

    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    monkeypatch.setattr(
        "core.evolution_tracker.DECISION_FEEDBACK_LOG_PATH",
        feedback_log,
    )
    option = MutationOption(
        option_id="test-opt",
        description="Minimal",
        target_paths=[],
        estimated_risk=0.1,
        estimated_complexity=0.2,
        estimated_success_probability=0.9,
        estimated_impact=0.3,
        sensitivity_summary=[],
        score=0.5,
        rationale="test",
    )
    result = DecisionExecutionResult(
        option=option,
        success=True,
        notes="",
        proposal_ids=(),
        decision_explanation="",
    )
    record_execution(result)
    assert feedback_log.exists()
    lines = [
        ln
        for ln in feedback_log.read_text(encoding="utf-8").strip().splitlines()
        if ln
    ]
    assert len(lines) >= 1
    rec = json.loads(lines[-1])
    assert rec.get("option_id") == "test-opt"
    assert rec.get("success") is True


def test_decision_history_log_still_writes(tmp_path: Path, monkeypatch) -> None:
    """Integration: decision history record_decision_history still writes."""
    from core.change_sensitivity import ChangeSensitivity
    from core.decision_history import record_decision_history
    from core.decision_model import MutationOption
    from core.decision_runner import DecisionExecutionResult

    history_log = tmp_path / "logs" / "lumos_decision_history.jsonl"
    monkeypatch.setattr(
        "core.decision_history.DECISION_HISTORY_LOG_PATH",
        history_log,
    )
    option = MutationOption(
        option_id="minimal-abc",
        description="Minimal",
        target_paths=[Path("src/foo.py")],
        estimated_risk=0.1,
        estimated_complexity=0.2,
        estimated_success_probability=0.9,
        estimated_impact=0.4,
        sensitivity_summary=[ChangeSensitivity.LOW],
        score=0.5,
        rationale="minimal",
    )
    result = DecisionExecutionResult(
        option=option,
        success=True,
        notes="",
        proposal_ids=("p1",),
        decision_explanation="Ok",
    )
    record_decision_history(result, "test goal")
    assert history_log.exists()
    lines = [
        ln
        for ln in history_log.read_text(encoding="utf-8").strip().splitlines()
        if ln
    ]
    assert len(lines) >= 1
    rec = json.loads(lines[-1])
    assert rec.get("goal") == "test goal"
    assert rec.get("chosen_option_id") == "minimal-abc"
