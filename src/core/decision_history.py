"""
Decision history: readable log of every decision made by the decision pipeline.

Stored in logs/lumos_decision_history.jsonl. Best-effort append; never raises.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.decision_runner import DecisionExecutionResult
from core.log_rotation import append_jsonl_with_rotation, DEFAULT_KEEP, DEFAULT_MAX_BYTES

DECISION_HISTORY_LOG_PATH: Path = Path("logs") / "lumos_decision_history.jsonl"


def record_decision_history(
    result: DecisionExecutionResult,
    goal: str,
    log_path: Path | None = None,
) -> None:
    """
    Append one decision record to logs/lumos_decision_history.jsonl.

    Fields: timestamp, goal, chosen_option_id, option_description, risk,
    success_probability, complexity, impact, sensitivity_levels, proposal_ids,
    success, notes. Best-effort; never crashes the pipeline.
    """
    path = log_path if log_path is not None else DECISION_HISTORY_LOG_PATH
    path = path.resolve()
    option = result.option
    sensitivity_levels = [s.name for s in option.sensitivity_summary]
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "goal": goal,
        "chosen_option_id": option.option_id,
        "option_description": option.description,
        "risk": option.estimated_risk,
        "success_probability": option.estimated_success_probability,
        "complexity": option.estimated_complexity,
        "impact": option.estimated_impact,
        "sensitivity_levels": sensitivity_levels,
        "proposal_ids": list(result.proposal_ids),
        "success": result.success,
        "notes": result.notes or "",
    }
    try:
        append_jsonl_with_rotation(
            path,
            record,
            max_bytes=DEFAULT_MAX_BYTES,
            keep=DEFAULT_KEEP,
        )
    except Exception:
        return
