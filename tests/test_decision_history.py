from __future__ import annotations

from pathlib import Path

import pytest

from core.change_sensitivity import ChangeSensitivity
from core.decision_history import record_decision_history
from core.decision_model import MutationOption
from core.decision_runner import DecisionExecutionResult


def test_record_decision_history_writes_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record_decision_history appends one JSON line to the history log."""
    history_log = tmp_path / "lumos_decision_history.jsonl"
    monkeypatch.setattr(
        "core.decision_history.DECISION_HISTORY_LOG_PATH", history_log
    )
    option = MutationOption(
        option_id="minimal-abc",
        description="Minimal change for goal",
        target_paths=[Path("src/core/foo.py")],
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
        notes="Proposals produced; no apply.",
        proposal_ids=("pid-1",),
        decision_explanation="Minimal seçildi.",
    )
    record_decision_history(result, "test goal")
    assert history_log.exists()
    lines = [
        ln
        for ln in history_log.read_text(encoding="utf-8").strip().splitlines()
        if ln
    ]
    assert len(lines) == 1
    import json
    record = json.loads(lines[0])
    assert record["goal"] == "test goal"
    assert record["chosen_option_id"] == "minimal-abc"
    assert record["option_description"] == "Minimal change for goal"
    assert record["risk"] == 0.1
    assert record["success_probability"] == 0.9
    assert record["complexity"] == 0.2
    assert record["impact"] == 0.4
    assert record["sensitivity_levels"] == ["LOW"]
    assert record["proposal_ids"] == ["pid-1"]
    assert record["success"] is True
    assert "timestamp" in record
    assert "notes" in record


def test_record_decision_history_never_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record_decision_history is best-effort; invalid path does not raise."""
    monkeypatch.setattr(
        "core.decision_history.DECISION_HISTORY_LOG_PATH",
        tmp_path / "nonexistent" / "nested" / "lumos_decision_history.jsonl",
    )
    option = MutationOption(
        option_id="x",
        description="",
        target_paths=[],
        estimated_risk=0.0,
        estimated_complexity=0.0,
        estimated_success_probability=1.0,
        estimated_impact=0.0,
        sensitivity_summary=[],
        score=0.0,
        rationale="",
    )
    result = DecisionExecutionResult(
        option=option, success=True, notes="", decision_explanation=""
    )
    record_decision_history(result, "goal")
    # If we get here without raising, the test passes.
    # On some OS/configs mkdir(parents=True) may still create the path; either way no crash.
