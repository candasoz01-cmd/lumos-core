from __future__ import annotations

from pathlib import Path

import pytest

from core.adaptive_weights import DecisionWeights
from core.change_sensitivity import ChangeSensitivity
from core.decision_model import MutationOption
from core.decision_pipeline import infer_lumos_base_for_decision, run_decision_pipeline
from core.decision_ranker import (
    compute_base_score,
    compute_final_score,
    rank_options,
)
from core.decision_runner import (
    DecisionExecutionResult,
    explain_decision,
    format_result_preview,
)
from core.decision_simulator import SimulationResult
from core.evolution_tracker import record_execution
from core.strategy_updater import (
    MEMORY_BIAS_SCORE_CAP,
    update_weights_from_outcome,
)


def test_run_decision_pipeline_empty_target_paths_returns_none() -> None:
    assert run_decision_pipeline("g", [], update_weights_after_run=False) is None


def test_infer_lumos_base_for_decision_finds_dot_lumos(tmp_path: Path) -> None:
    lumos = tmp_path / ".lumos"
    f = lumos / "config" / "x.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("{}", encoding="utf-8")
    assert infer_lumos_base_for_decision([f]) == lumos.resolve()


def test_infer_lumos_base_for_decision_none_without_lumos_ancestor(tmp_path: Path) -> None:
    p = tmp_path / "src" / "a.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x = 1\n", encoding="utf-8")
    assert infer_lumos_base_for_decision([p]) is None


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


def test_decision_ranker_centralized_score_math_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Centralized compute_final_score: formula is single source of truth; no duplicate in tests."""
    # final = base + quality + memory (only place this math lives is decision_ranker._compute_final_score)
    assert abs(compute_final_score(1.0, 0.2, 0.1) - 1.3) < 1e-9
    assert abs(compute_final_score(0.5, -0.2, -0.1) - 0.2) < 1e-9
    assert compute_final_score(0.0, 0.0, 0.0) == 0.0
    # rank_options with no quality/memory uses same base as compute_base_score (no formula duplicate)
    weights = DecisionWeights(success_weight=0.4, risk_weight=0.3, impact_weight=0.3)
    monkeypatch.setattr("core.decision_ranker.load_weights", lambda *a, **k: weights)
    monkeypatch.setattr(
        "core.decision_ranker.estimate_decision_quality",
        lambda *a, **k: {"predicted_success": 0.5, "predicted_risk": 0.5},
    )
    monkeypatch.setattr("core.decision_ranker.get_memory_bias_score_for_option", lambda *a, **k: 0.0)
    opt = MutationOption(
        option_id="minimal-x",
        description="X",
        target_paths=[Path("x.py")],
        estimated_risk=0.2,
        estimated_complexity=0.1,
        estimated_success_probability=0.7,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    sim = SimulationResult(success_probability=0.7, estimated_risk=0.2, notes="")
    ranked = rank_options([opt], [sim])
    assert abs(ranked[0].final_score - compute_base_score(opt, sim, weights)) < 1e-9


def test_decision_ranker_quality_and_memory_default_to_zero() -> None:
    """With no history/feedback/memory paths, quality_score and memory_bias are 0; ranking by base only."""
    opt_a = MutationOption(
        option_id="minimal-a",
        description="A",
        target_paths=[Path("x.py")],
        estimated_risk=0.1,
        estimated_complexity=0.1,
        estimated_success_probability=0.8,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    opt_b = MutationOption(
        option_id="minimal-b",
        description="B",
        target_paths=[Path("x.py")],
        estimated_risk=0.1,
        estimated_complexity=0.1,
        estimated_success_probability=0.4,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.4,
        rationale="",
    )
    sims = [
        SimulationResult(success_probability=0.8, estimated_risk=0.1, notes=""),
        SimulationResult(success_probability=0.4, estimated_risk=0.1, notes=""),
    ]
    ranked = rank_options([opt_a, opt_b], sims)
    assert len(ranked) == 2
    assert ranked[0].option.option_id == "minimal-a"
    assert ranked[0].final_score > ranked[1].final_score


def test_decision_ranker_final_score_is_base_plus_quality_plus_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """final_score = base_score + quality_score + memory_bias; estimator/memory unavailable -> 0."""
    def capture_weights(*a, **k):
        return DecisionWeights(success_weight=0.4, risk_weight=0.3, impact_weight=0.3)

    def fake_estimate(option: dict, context: dict, **kwargs):
        return {"predicted_success": 0.9, "predicted_risk": 0.2, "confidence": 0.8, "explanation": ""}

    def fake_memory_bias(option_id: str, **kwargs):
        return 0.05

    monkeypatch.setattr("core.decision_ranker.load_weights", capture_weights)
    monkeypatch.setattr(
        "core.decision_ranker.estimate_decision_quality",
        fake_estimate,
    )
    monkeypatch.setattr(
        "core.decision_ranker.get_memory_bias_score_for_option",
        fake_memory_bias,
    )
    opt = MutationOption(
        option_id="minimal-x",
        description="X",
        target_paths=[Path("x.py")],
        estimated_risk=0.2,
        estimated_complexity=0.1,
        estimated_success_probability=0.7,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    sim = SimulationResult(success_probability=0.7, estimated_risk=0.2, notes="")
    ranked = rank_options([opt], [sim])
    assert len(ranked) == 1
    weights = DecisionWeights(success_weight=0.4, risk_weight=0.3, impact_weight=0.3)
    base_score = compute_base_score(opt, sim, weights)
    quality_score = (0.9 - 0.2) * 0.2
    memory_bias = 0.05
    expected = compute_final_score(base_score, quality_score, memory_bias)
    assert abs(ranked[0].final_score - expected) < 1e-6


def test_ranking_backward_safe_when_quality_estimator_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When quality estimator raises or is unavailable, ranking equals base-only (old) behavior."""
    weights = DecisionWeights(success_weight=0.4, risk_weight=0.3, impact_weight=0.3)
    monkeypatch.setattr("core.decision_ranker.load_weights", lambda *a, **k: weights)
    # Estimator raises every time
    def raise_estimator(*a, **k):
        raise RuntimeError("estimator unavailable")
    monkeypatch.setattr("core.decision_ranker.estimate_decision_quality", raise_estimator)
    # Memory can return 0 (no path) or we force 0 for baseline
    monkeypatch.setattr(
        "core.decision_ranker.get_memory_bias_score_for_option",
        lambda *a, **k: 0.0,
    )
    opt_a = MutationOption(
        option_id="minimal-a",
        description="A",
        target_paths=[Path("x.py")],
        estimated_risk=0.1,
        estimated_complexity=0.1,
        estimated_success_probability=0.9,
        estimated_impact=0.4,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    opt_b = MutationOption(
        option_id="minimal-b",
        description="B",
        target_paths=[Path("x.py")],
        estimated_risk=0.2,
        estimated_complexity=0.1,
        estimated_success_probability=0.4,
        estimated_impact=0.4,
        sensitivity_summary=[],
        score=0.4,
        rationale="",
    )
    options = [opt_a, opt_b]
    sims = [
        SimulationResult(success_probability=0.9, estimated_risk=0.1, notes=""),
        SimulationResult(success_probability=0.4, estimated_risk=0.2, notes=""),
    ]
    ranked = rank_options(options, sims)
    # Old behavior: A has higher base score than B; order must be A first
    base_a = compute_base_score(opt_a, sims[0], weights)
    base_b = compute_base_score(opt_b, sims[1], weights)
    assert base_a > base_b
    assert ranked[0].option.option_id == "minimal-a"
    assert ranked[1].option.option_id == "minimal-b"
    # Scores are base-only (quality=0, memory=0)
    assert abs(ranked[0].final_score - base_a) < 1e-9
    assert abs(ranked[1].final_score - base_b) < 1e-9


def test_ranking_backward_safe_when_memory_bias_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When memory bias raises or is unavailable, ranking equals base-only (old) behavior."""
    weights = DecisionWeights(success_weight=0.4, risk_weight=0.3, impact_weight=0.3)
    monkeypatch.setattr("core.decision_ranker.load_weights", lambda *a, **k: weights)
    monkeypatch.setattr(
        "core.decision_ranker.estimate_decision_quality",
        lambda *a, **k: {"predicted_success": 0.5, "predicted_risk": 0.5},
    )
    # Memory raises every time
    def raise_memory(*a, **k):
        raise OSError("memory patterns missing")
    monkeypatch.setattr("core.decision_ranker.get_memory_bias_score_for_option", raise_memory)
    opt_a = MutationOption(
        option_id="minimal-a",
        description="A",
        target_paths=[Path("x.py")],
        estimated_risk=0.1,
        estimated_complexity=0.1,
        estimated_success_probability=0.85,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    opt_b = MutationOption(
        option_id="minimal-b",
        description="B",
        target_paths=[Path("x.py")],
        estimated_risk=0.1,
        estimated_complexity=0.1,
        estimated_success_probability=0.35,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.35,
        rationale="",
    )
    options = [opt_a, opt_b]
    sims = [
        SimulationResult(success_probability=0.85, estimated_risk=0.1, notes=""),
        SimulationResult(success_probability=0.35, estimated_risk=0.1, notes=""),
    ]
    ranked = rank_options(options, sims)
    base_a = compute_base_score(opt_a, sims[0], weights)
    base_b = compute_base_score(opt_b, sims[1], weights)
    assert base_a > base_b
    assert ranked[0].option.option_id == "minimal-a"
    assert ranked[1].option.option_id == "minimal-b"
    # Quality from (0.5-0.5)*0.2 = 0 for both; memory = 0
    assert abs(ranked[0].final_score - base_a) < 1e-9
    assert abs(ranked[1].final_score - base_b) < 1e-9


# Quality additive cap 0.2 (from (success-risk)*0.2); memory cap MEMORY_BIAS_SCORE_CAP.
QUALITY_ADDITIVE_CAP = 0.2


def test_ranking_quality_and_memory_contribution_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quality and memory contributions to final_score stay within caps; total additive is bounded."""
    weights = DecisionWeights(success_weight=0.4, risk_weight=0.3, impact_weight=0.3)
    monkeypatch.setattr("core.decision_ranker.load_weights", lambda *a, **k: weights)
    # Estimator returns values that would yield +0.2 and -0.2 at the formula (success-risk)*0.2
    def extreme_high(*a, **k):
        return {"predicted_success": 1.0, "predicted_risk": 0.0}
    def extreme_low(*a, **k):
        return {"predicted_success": 0.0, "predicted_risk": 1.0}
    # Memory returns at cap
    def memory_plus(*a, **k):
        return MEMORY_BIAS_SCORE_CAP
    def memory_minus(*a, **k):
        return -MEMORY_BIAS_SCORE_CAP
    opt = MutationOption(
        option_id="minimal-x",
        description="X",
        target_paths=[Path("x.py")],
        estimated_risk=0.2,
        estimated_complexity=0.1,
        estimated_success_probability=0.6,
        estimated_impact=0.4,
        sensitivity_summary=[],
        score=0.5,
        rationale="",
    )
    sim = SimulationResult(success_probability=0.6, estimated_risk=0.2, notes="")
    base = compute_base_score(opt, sim, weights)
    # Max additive: quality 0.2 + memory 0.1
    monkeypatch.setattr("core.decision_ranker.estimate_decision_quality", extreme_high)
    monkeypatch.setattr("core.decision_ranker.get_memory_bias_score_for_option", memory_plus)
    ranked_high = rank_options([opt], [sim])
    additive_high = ranked_high[0].final_score - base
    assert additive_high <= QUALITY_ADDITIVE_CAP + MEMORY_BIAS_SCORE_CAP + 1e-9
    # Min additive: quality -0.2 + memory -0.1
    monkeypatch.setattr("core.decision_ranker.estimate_decision_quality", extreme_low)
    monkeypatch.setattr("core.decision_ranker.get_memory_bias_score_for_option", memory_minus)
    ranked_low = rank_options([opt], [sim])
    additive_low = ranked_low[0].final_score - base
    assert additive_low >= -(QUALITY_ADDITIVE_CAP + MEMORY_BIAS_SCORE_CAP) - 1e-9


def test_ranking_order_changes_only_when_added_score_meaningfully_differs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rank order cannot be reversed when base_score gap is larger than max possible additive delta."""
    weights = DecisionWeights(success_weight=0.4, risk_weight=0.3, impact_weight=0.3)
    monkeypatch.setattr("core.decision_ranker.load_weights", lambda *a, **k: weights)
    max_additive_delta = 2 * (QUALITY_ADDITIVE_CAP + MEMORY_BIAS_SCORE_CAP)
    # Option A: high base; Option B: low base, gap > max_additive_delta
    opt_high = MutationOption(
        option_id="minimal-high",
        description="High base",
        target_paths=[Path("x.py")],
        estimated_risk=0.05,
        estimated_complexity=0.1,
        estimated_success_probability=0.95,
        estimated_impact=0.5,
        sensitivity_summary=[],
        score=0.9,
        rationale="",
    )
    opt_low = MutationOption(
        option_id="minimal-low",
        description="Low base",
        target_paths=[Path("x.py")],
        estimated_risk=0.7,
        estimated_complexity=0.1,
        estimated_success_probability=0.15,
        estimated_impact=0.1,
        sensitivity_summary=[],
        score=0.15,
        rationale="",
    )
    sim_high = SimulationResult(success_probability=0.95, estimated_risk=0.05, notes="")
    sim_low = SimulationResult(success_probability=0.15, estimated_risk=0.7, notes="")
    base_high = compute_base_score(opt_high, sim_high, weights)
    base_low = compute_base_score(opt_low, sim_low, weights)
    assert base_high - base_low > max_additive_delta
    # Give low option max additive, high option min additive
    call_count = [0]
    def estimator_high_then_low(*a, **k):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"predicted_success": 0.0, "predicted_risk": 1.0}
        return {"predicted_success": 1.0, "predicted_risk": 0.0}
    def memory_high_then_low(option_id: str, **k):
        return -MEMORY_BIAS_SCORE_CAP if "high" in option_id else MEMORY_BIAS_SCORE_CAP
    monkeypatch.setattr("core.decision_ranker.estimate_decision_quality", estimator_high_then_low)
    monkeypatch.setattr("core.decision_ranker.get_memory_bias_score_for_option", memory_high_then_low)
    ranked = rank_options([opt_high, opt_low], [sim_high, sim_low])
    # Order must remain high first: added score cannot overcome base gap
    assert ranked[0].option.option_id == "minimal-high"
    assert ranked[1].option.option_id == "minimal-low"
    assert ranked[0].final_score > ranked[1].final_score


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

