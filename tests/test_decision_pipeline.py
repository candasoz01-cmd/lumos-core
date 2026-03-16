from __future__ import annotations

from pathlib import Path

from core.change_sensitivity import ChangeSensitivity
from core.decision_model import MutationOption
from core.decision_pipeline import run_decision_pipeline
from core.decision_runner import (
    DecisionExecutionResult,
    explain_decision,
    format_result_preview,
)


def test_run_decision_pipeline_end_to_end(tmp_path: Path) -> None:
    goal = "Test decision pipeline end-to-end"

    target_file = tmp_path / "src" / "core" / "example_target.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# example target file\n", encoding="utf-8")

    result = run_decision_pipeline(goal, [target_file])

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

    result = run_decision_pipeline(goal, [target_file])

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

