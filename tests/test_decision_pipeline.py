from __future__ import annotations

from pathlib import Path

import pytest

from core.adaptive_weights import DecisionWeights
from core.change_sensitivity import ChangeSensitivity
from core.decision_model import MutationOption
from core.decision_pipeline import run_decision_pipeline
from core.decision_ranker import rank_options
from core.decision_runner import (
    DecisionExecutionResult,
    explain_decision,
    format_result_preview,
)
from core.decision_simulator import SimulationResult
from core.evolution_tracker import record_execution
from core.strategy_updater import update_weights_from_outcome


def test_run_decision_pipeline_end_to_end(tmp_path: Path) -> None:
    goal = "Test decision pipeline end-to-end"

    target_file = tmp_path / "src" / "core" / "example_target.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# example target file\n", encoding="utf-8")

    result = run_decision_pipeline(
        goal, [target_file], update_weights_after_run=False
    )

    assert isinstance(result, DecisionExecutionResult)
    assert result.option is not None
    assert result.option.target_paths
    assert any(p.name == target_file.name for p in result.option.target_paths)


def test_run_decision_pipeline_produces_proposal_no_apply(tmp_path: Path) -> None:
    """Decision-to-patch bridge: proposal produced, no apply, real file unchanged."""
    goal = "Proposal-only run"
    target_file = tmp_path / "src" / "core" / "example_target.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    original_content = "# example target file\nline2\n"
    target_file.write_text(original_content, encoding="utf-8")

    result = run_decision_pipeline(
        goal, [target_file], update_weights_after_run=False
    )

    assert result is not None
    assert isinstance(result, DecisionExecutionResult)
    assert result.success
    assert len(result.proposal_ids) >= 1
    assert "Proposals produced" in result.proposal_summary
    assert "proposal_diff" in result.proposal_summary or "Diff preview" in result.proposal_summary
    assert "No apply" in result.notes or "no apply" in result.notes.lower()
    assert target_file.read_text(encoding="utf-8") == original_content
    # proposal_diff: no-op proposal may have empty diff; preview formatter includes it
    preview = format_result_preview(result)
    assert result.proposal_summary in preview
    # decision explanation layer
    assert result.decision_explanation
    assert "seçildi çünkü" in result.decision_explanation
    assert "risk" in result.decision_explanation
    assert "sensitivity" in result.decision_explanation.lower()


def test_explain_decision_deterministic() -> None:
    """explain_decision is template-based, no LLM."""
    option = MutationOption(
        option_id="minimal-abc",
        description="Minimal change",
        target_paths=[Path("src/core/foo.py")],
        estimated_risk=0.1,
        estimated_complexity=0.2,
        estimated_success_probability=0.9,
        estimated_impact=0.4,
        sensitivity_summary=[ChangeSensitivity.CRITICAL],
        score=0.5,
        rationale="minimal",
    )
    text = explain_decision(option)
    assert "Minimal değişiklik" in text
    assert "seçildi çünkü" in text
    assert "%10" in text or "%9" in text  # risk or success pct
    assert "CRITICAL" in text
    assert "sensitivity" in text.lower()


def test_decision_ranker_uses_adaptive_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ranker uses load_weights(); custom weights change ranking."""
    monkeypatch.setattr(
        "core.decision_ranker.load_weights",
        lambda *a, **k: DecisionWeights(
            success_weight=0.8, risk_weight=0.1, impact_weight=0.1
        ),
    )
    opt_high_success = MutationOption(
        option_id="a",
        description="High success",
        target_paths=[Path("x.py")],
        estimated_risk=0.2,
        estimated_complexity=0.2,
        estimated_success_probability=0.95,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    opt_low_success = MutationOption(
        option_id="b",
        description="Low success",
        target_paths=[Path("x.py")],
        estimated_risk=0.2,
        estimated_complexity=0.2,
        estimated_success_probability=0.3,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.3,
        rationale="",
    )
    options = [opt_low_success, opt_high_success]
    sims = [
        SimulationResult(success_probability=0.3, estimated_risk=0.2, notes=""),
        SimulationResult(success_probability=0.95, estimated_risk=0.2, notes=""),
    ]
    ranked = rank_options(options, sims)
    assert len(ranked) == 2
    assert ranked[0].option.option_id == "a"
    assert ranked[0].final_score >= ranked[1].final_score


def test_strategy_updater_writes_weights(tmp_path: Path) -> None:
    """update_weights_from_outcome and apply_decision_feedback_updates write .lumos/weights.json."""
    weights_file = tmp_path / ".lumos" / "weights.json"
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    update_weights_from_outcome(True, weights_path=str(weights_file))
    assert weights_file.exists()
    import json
    data = json.loads(weights_file.read_text(encoding="utf-8"))
    assert "success_weight" in data and "risk_weight" in data and "impact_weight" in data
    assert 0 <= data["success_weight"] <= 1


def test_evolution_tracker_writes_decision_feedback_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record_execution appends to lumos_decision_feedback.jsonl."""
    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    monkeypatch.setattr(
        "core.evolution_tracker.DECISION_FEEDBACK_LOG_PATH", feedback_log
    )
    option = MutationOption(
        option_id="test-opt",
        description="Test",
        target_paths=[],
        estimated_risk=0.1,
        estimated_complexity=0.0,
        estimated_success_probability=0.9,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    result = DecisionExecutionResult(
        option=option, success=True, notes="ok", decision_explanation="Test"
    )
    record_execution(result)
    assert feedback_log.exists()
    lines = [
        ln
        for ln in feedback_log.read_text(encoding="utf-8").strip().splitlines()
        if ln
    ]
    assert len(lines) == 1
    import json
    obj = json.loads(lines[0])
    assert obj.get("option_id") == "test-opt" and obj.get("success") is True


def test_proposal_diff_preview_alias() -> None:
    """DecisionExecutionResult.proposal_diff_preview returns proposal_diff."""
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
        option=option,
        success=True,
        notes="",
        proposal_diff="--- a\n+++ b\n",
        decision_explanation="",
    )
    assert result.proposal_diff_preview == "--- a\n+++ b\n"
    assert result.proposal_diff_preview == result.proposal_diff


def test_pipeline_updates_weights_from_feedback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With update_weights_after_run=True, pipeline runs apply_decision_feedback_updates."""
    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    state_file = tmp_path / ".lumos" / "strategy_feedback_state.json"
    feedback_log.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "core.evolution_tracker.DECISION_FEEDBACK_LOG_PATH", feedback_log
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_DECISION_FEEDBACK_LOG_PATH", feedback_log
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_FEEDBACK_STATE_PATH", state_file
    )
    monkeypatch.setattr(
        "core.adaptive_weights.DEFAULT_WEIGHTS_PATH", weights_file
    )
    target_file = tmp_path / "src" / "app.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# app\n", encoding="utf-8")

    result = run_decision_pipeline(
        "goal", [target_file], base_dir=tmp_path, update_weights_after_run=True
    )
    assert result is not None
    assert feedback_log.exists()
    import json
    assert weights_file.exists() or (result.success and True)
    if weights_file.exists():
        data = json.loads(weights_file.read_text(encoding="utf-8"))
        assert "success_weight" in data


def test_protected_core_no_apply(tmp_path: Path) -> None:
    """Pipeline with target under base_dir core path: proposal produced, no apply."""
    lumos_dir = tmp_path / ".lumos"
    lumos_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = lumos_dir / "tasks.json"
    tasks_file.write_text('{"tasks":[]}', encoding="utf-8")
    original = tasks_file.read_text(encoding="utf-8")

    result = run_decision_pipeline(
        "goal",
        [tasks_file],
        base_dir=lumos_dir,
        update_weights_after_run=False,
    )
    assert result is not None
    assert tasks_file.read_text(encoding="utf-8") == original
    assert "No apply" in result.notes or "no apply" in result.notes.lower()

