"""
Decision quality estimator: predict success and risk of a decision before execution
using past decision history and memory patterns. Never raises; safe on missing data.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

# Default paths (relative to CWD)
DEFAULT_DECISION_HISTORY_PATH: Path = Path("logs") / "lumos_decision_history.jsonl"
DEFAULT_DECISION_FEEDBACK_PATH: Path = Path("logs") / "lumos_decision_feedback.jsonl"
DEFAULT_MEMORY_PATTERNS_PATH: Path = Path(".lumos") / "memory_patterns.json"

MIN_HISTORY_RECORDS = 20
NEUTRAL_SUCCESS = 0.5
NEUTRAL_RISK = 0.5
NEUTRAL_CONFIDENCE = 0.2
PATTERN_BOOST = 0.08
ROLLBACK_RISK_BOOST = 0.15
MAX_EVIDENCE_CONFIDENCE_BOOST = 0.2


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.resolve().exists():
        return []
    records: list[dict] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _strategy_from_option_id(option_id: str) -> str:
    if not option_id or "-" not in option_id:
        return "unknown"
    prefix = option_id.split("-", 1)[0].lower()
    if prefix in ("minimal", "aggressive", "medium"):
        return prefix
    return "unknown"


def _is_rollback(notes: str) -> bool:
    if not notes:
        return False
    n = notes.lower()
    return "rollback" in n or "rolled_back" in n


def _load_memory_patterns(path: Path) -> list[dict]:
    if not path.resolve().exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    patterns = data.get("patterns")
    if not isinstance(patterns, list):
        return []
    return [p for p in patterns if isinstance(p, dict)]


def _pattern_matches_strategy(summary: str, strategy: str) -> str | None:
    """If pattern summary is about this strategy, return which effect: success_boost, risk_boost, or None."""
    if not summary or not strategy:
        return None
    s = summary.lower()
    if strategy == "minimal" and "minimal" in s and ("succeed" in s or "success" in s):
        return "success_boost"
    if strategy == "aggressive" and "aggressive" in s and ("rollback" in s or "fail" in s):
        return "risk_boost"
    if strategy == "medium" and "medium" in s and ("balanced" in s or "perform" in s):
        return "success_boost"
    return None


def estimate_decision_quality(
    option: dict,
    context: dict,
    *,
    history_path: Path | str | None = None,
    feedback_path: Path | str | None = None,
    memory_patterns_path: Path | str | None = None,
) -> dict:
    """
    Estimate quality and risk of a decision before execution.
    Uses decision history, feedback, and memory patterns. Never raises.

    option: { strategy, target_path?, estimated_impact? }
    context: { sensitivity?, file_type? }

    Returns: { predicted_success, predicted_risk, confidence, explanation }
    All numeric values in [0.0, 1.0].
    """
    out: dict = {
        "predicted_success": NEUTRAL_SUCCESS,
        "predicted_risk": NEUTRAL_RISK,
        "confidence": NEUTRAL_CONFIDENCE,
        "explanation": "insufficient history",
    }
    try:
        option = option or {}
        context = context or {}
        hist_p = Path(history_path) if history_path is not None else DEFAULT_DECISION_HISTORY_PATH
        feed_p = Path(feedback_path) if feedback_path is not None else DEFAULT_DECISION_FEEDBACK_PATH
        mem_p = Path(memory_patterns_path) if memory_patterns_path is not None else DEFAULT_MEMORY_PATTERNS_PATH

        history = _read_jsonl(hist_p.resolve())
        feedback = _read_jsonl(feed_p.resolve())
        total_records = len(history) + len(feedback)

        if total_records < MIN_HISTORY_RECORDS:
            return out

        strategy = (option.get("strategy") or "").strip().lower()
        if strategy not in ("minimal", "medium", "aggressive"):
            strategy = "minimal"

        # By-strategy: success count, total count, rollback count
        by_strategy: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
        for rec in history:
            if not isinstance(rec, dict):
                continue
            opt_id = rec.get("chosen_option_id") or rec.get("option_id") or ""
            st = _strategy_from_option_id(opt_id)
            if st == "unknown":
                continue
            success = rec.get("success")
            if not isinstance(success, bool):
                continue
            rollback = _is_rollback(str(rec.get("notes") or ""))
            by_strategy[st].append((success, rollback))
        for rec in feedback:
            if not isinstance(rec, dict):
                continue
            opt_id = rec.get("option_id") or ""
            st = _strategy_from_option_id(opt_id)
            if st == "unknown":
                continue
            success = rec.get("success")
            if not isinstance(success, bool):
                continue
            by_strategy[st].append((success, False))

        if not by_strategy:
            return out

        # Success rate and rollback rate for the chosen strategy
        lst = by_strategy.get(strategy) or []
        n = len(lst)
        if n == 0:
            success_rate = 0.5
            rollback_rate = 0.0
            success_count = 0
            rollback_count = 0
        else:
            success_count = sum(1 for s, _ in lst if s)
            rollback_count = sum(1 for _, r in lst if r)
            success_rate = success_count / n
            rollback_rate = rollback_count / n

        predicted_success = success_rate
        predicted_risk = 1.0 - success_rate
        if rollback_rate > 0.1 and strategy == "aggressive":
            predicted_risk = _clamp01(predicted_risk + ROLLBACK_RISK_BOOST)
        if rollback_rate > 0:
            predicted_risk = _clamp01(predicted_risk + rollback_rate * 0.2)

        # Memory pattern adjustments
        patterns = _load_memory_patterns(mem_p.resolve())
        total_evidence = 0
        for p in patterns:
            summary = p.get("summary") or ""
            effect = _pattern_matches_strategy(summary, strategy)
            evidence = int(p.get("evidence_count") or 0)
            conf = float(p.get("confidence") or 0)
            if evidence > 0:
                total_evidence += evidence
            if effect == "success_boost" and conf >= 0.6:
                predicted_success = _clamp01(predicted_success + PATTERN_BOOST)
            if effect == "risk_boost" and conf >= 0.6:
                predicted_risk = _clamp01(predicted_risk + PATTERN_BOOST)

        # Confidence: higher when we have more evidence for this strategy
        confidence = 0.3 + 0.4 * min(1.0, n / 50)
        if total_evidence >= 20:
            confidence = _clamp01(confidence + MAX_EVIDENCE_CONFIDENCE_BOOST)
        confidence = _clamp01(confidence)

        explanation = (
            f"strategy={strategy}, history success rate={success_rate:.2f}, "
            f"rollback rate={rollback_rate:.2f}, n={n}"
        )
        if patterns:
            explanation += ", memory patterns applied"

        out["predicted_success"] = round(_clamp01(predicted_success), 4)
        out["predicted_risk"] = round(_clamp01(predicted_risk), 4)
        out["confidence"] = round(_clamp01(confidence), 4)
        out["explanation"] = explanation
        return out
    except Exception:
        return out
