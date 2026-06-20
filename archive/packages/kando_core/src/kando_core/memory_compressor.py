"""
Compact memory compression: convert raw decision/evolution logs into
short reusable patterns that can guide future decision strategy.
Stdlib only, deterministic, no ML. Never crashes on missing or malformed logs.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

from core.log_window import read_recent_jsonl_records
from core.memory_patterns import MemoryPattern


# Default paths (relative to CWD)
DEFAULT_DECISION_HISTORY_PATH: Path = Path("logs") / "lumos_decision_history.jsonl"
DEFAULT_DECISION_FEEDBACK_PATH: Path = Path("logs") / "lumos_decision_feedback.jsonl"
DEFAULT_EVOLUTION_PATH: Path = Path("logs") / "lumos_evolution.jsonl"
DEFAULT_OUTPUT_PATH: Path = Path(".lumos") / "memory_patterns.json"

MIN_COMBINED_RECORDS = 20
# Bounded recent-history: max combined records from the three log sources
MEMORY_COMPRESSOR_RECENT_LIMIT = 300
MAX_PATTERNS = 10
MIN_EVIDENCE_FOR_PATTERN = 5
MIN_CONFIDENCE = 0.6
BIAS_DELTA = 0.01




def _decision_type_from_option_id(option_id: str) -> str:
    """Extract decision type: minimal, aggressive, medium, or unknown."""
    if not option_id or "-" not in option_id:
        return "unknown"
    prefix = option_id.split("-", 1)[0].lower()
    if prefix in ("minimal", "aggressive", "medium"):
        return prefix
    return "unknown"


def _path_group(path_str: str) -> str:
    """Normalize path to a small group (e.g. core, tools, tests, config)."""
    if not path_str:
        return "unknown"
    p = path_str.replace("\\", "/")
    parts = [x for x in p.split("/") if x]
    if not parts:
        return "unknown"
    # Prefer first meaningful segment (e.g. src/core -> core, src/tools -> tools)
    for part in parts:
        if part in ("src", "private", "var", "tmp", "T"):
            continue
        return part
    return parts[-1] if parts else "unknown"


def _extract_patterns(
    history: list[dict],
    feedback: list[dict],
    evolution: list[dict],
) -> list[MemoryPattern]:
    """Build up to MAX_PATTERNS patterns from aggregated counts. Deterministic."""
    patterns: list[MemoryPattern] = []
    pattern_id_counter = 0

    # --- Decision history + feedback: (type, success) counts
    type_success: dict[str, list[bool]] = defaultdict(list)
    for rec in history:
        if not isinstance(rec, dict):
            continue
        opt = rec.get("chosen_option_id") or rec.get("option_id") or ""
        success = rec.get("success")
        if not isinstance(success, bool):
            continue
        t = _decision_type_from_option_id(opt)
        if t != "unknown":
            type_success[t].append(success)
    for rec in feedback:
        if not isinstance(rec, dict):
            continue
        opt = rec.get("option_id") or ""
        success = rec.get("success")
        if not isinstance(success, bool):
            continue
        t = _decision_type_from_option_id(opt)
        if t != "unknown":
            type_success[t].append(success)

    for dtype, outcomes in type_success.items():
        if len(outcomes) < MIN_EVIDENCE_FOR_PATTERN:
            continue
        success_count = sum(1 for x in outcomes if x)
        rate = success_count / len(outcomes)
        if dtype == "minimal" and rate >= MIN_CONFIDENCE and pattern_id_counter < MAX_PATTERNS:
            patterns.append(
                MemoryPattern(
                    pattern_id=f"p{pattern_id_counter}",
                    source="decision_history+feedback",
                    summary="minimal decisions succeed often",
                    confidence=round(rate, 2),
                    evidence_count=len(outcomes),
                    recommended_bias={"success_weight": BIAS_DELTA},
                )
            )
            pattern_id_counter += 1
        elif dtype == "aggressive" and rate <= (1 - MIN_CONFIDENCE) and pattern_id_counter < MAX_PATTERNS:
            patterns.append(
                MemoryPattern(
                    pattern_id=f"p{pattern_id_counter}",
                    source="decision_history+feedback",
                    summary="aggressive decisions rollback often",
                    confidence=round(1 - rate, 2),
                    evidence_count=len(outcomes),
                    recommended_bias={"risk_weight": 0.02},
                )
            )
            pattern_id_counter += 1
        elif dtype == "medium" and (1 - MIN_CONFIDENCE) <= rate <= MIN_CONFIDENCE and pattern_id_counter < MAX_PATTERNS:
            patterns.append(
                MemoryPattern(
                    pattern_id=f"p{pattern_id_counter}",
                    source="decision_history+feedback",
                    summary="medium decisions perform best on balanced outcomes",
                    confidence=round(rate, 2),
                    evidence_count=len(outcomes),
                    recommended_bias={"success_weight": BIAS_DELTA, "risk_weight": BIAS_DELTA},
                )
            )
            pattern_id_counter += 1

    # --- Evolution: rollback rate
    rollback_outcomes: list[bool] = []
    for rec in evolution:
        if not isinstance(rec, dict):
            continue
        rb = rec.get("rollback_occurred")
        if isinstance(rb, bool):
            rollback_outcomes.append(rb)
    if len(rollback_outcomes) >= MIN_EVIDENCE_FOR_PATTERN and pattern_id_counter < MAX_PATTERNS:
        rollback_rate = sum(1 for x in rollback_outcomes if x) / len(rollback_outcomes)
        if rollback_rate >= MIN_CONFIDENCE:
            patterns.append(
                MemoryPattern(
                    pattern_id=f"p{pattern_id_counter}",
                    source="evolution",
                    summary="rollbacks occur often in evolution log",
                    confidence=round(rollback_rate, 2),
                    evidence_count=len(rollback_outcomes),
                    recommended_bias={"risk_weight": 0.02},
                )
            )
            pattern_id_counter += 1

    # --- Evolution: sensitivity_levels vs failure (result != ok/applied)
    sens_fail: dict[str, list[bool]] = defaultdict(list)
    for rec in evolution:
        if not isinstance(rec, dict):
            continue
        levels = rec.get("sensitivity_levels")
        result = rec.get("result")
        if not isinstance(levels, list):
            continue
        fail = result not in ("ok", "applied", "rolled_back")
        for lev in levels:
            if isinstance(lev, str):
                sens_fail[lev].append(fail)
    for sens, fails in sens_fail.items():
        if len(fails) < MIN_EVIDENCE_FOR_PATTERN or pattern_id_counter >= MAX_PATTERNS:
            continue
        fail_rate = sum(1 for x in fails if x) / len(fails)
        if fail_rate >= MIN_CONFIDENCE:
            patterns.append(
                MemoryPattern(
                    pattern_id=f"p{pattern_id_counter}",
                    source="evolution",
                    summary=f"sensitivity {sens} correlates with failures",
                    confidence=round(fail_rate, 2),
                    evidence_count=len(fails),
                    recommended_bias={"risk_weight": BIAS_DELTA},
                )
            )
            pattern_id_counter += 1

    # --- Evolution: path group vs success (result in ok/applied)
    path_success: dict[str, list[bool]] = defaultdict(list)
    for rec in evolution:
        if not isinstance(rec, dict):
            continue
        paths = rec.get("affected_paths") or []
        result = rec.get("result")
        success = result in ("ok", "applied")
        for p in paths:
            if isinstance(p, str):
                group = _path_group(p)
                path_success[group].append(success)
    for group, outcomes in path_success.items():
        if group == "unknown" or len(outcomes) < MIN_EVIDENCE_FOR_PATTERN or pattern_id_counter >= MAX_PATTERNS:
            continue
        success_rate = sum(1 for x in outcomes if x) / len(outcomes)
        if success_rate >= MIN_CONFIDENCE:
            patterns.append(
                MemoryPattern(
                    pattern_id=f"p{pattern_id_counter}",
                    source="evolution",
                    summary=f"path group '{group}' correlates with safer decisions",
                    confidence=round(success_rate, 2),
                    evidence_count=len(outcomes),
                    recommended_bias={"success_weight": BIAS_DELTA},
                )
            )
            pattern_id_counter += 1

    # Deduplicate by summary and cap at MAX_PATTERNS (we already cap when adding; ensure no duplicate summaries)
    seen_summaries: set[str] = set()
    unique: list[MemoryPattern] = []
    for p in patterns:
        if p.summary not in seen_summaries and len(unique) < MAX_PATTERNS:
            seen_summaries.add(p.summary)
            unique.append(p)
    # Reassign pattern_id by index
    for i, p in enumerate(unique):
        unique[i] = MemoryPattern(
            pattern_id=f"p{i}",
            source=p.source,
            summary=p.summary,
            confidence=p.confidence,
            evidence_count=p.evidence_count,
            recommended_bias=p.recommended_bias,
        )
    return unique


def compress_runtime_memory(
    decision_history_path: Path | None = None,
    decision_feedback_path: Path | None = None,
    evolution_path: Path | None = None,
    output_path: Path | None = None,
) -> dict:
    """
    Read decision/evolution logs, extract repeated patterns, write compressed
    patterns to .lumos/memory_patterns.json. Never raises on missing/malformed logs.

    Returns a report dict with keys: records_read, patterns_created, output_path, status.
    If combined records < 20 or no strong pattern exists, writes nothing and status is "skipped".
    """
    hist_path = decision_history_path or DEFAULT_DECISION_HISTORY_PATH
    feed_path = decision_feedback_path or DEFAULT_DECISION_FEEDBACK_PATH
    evol_path = evolution_path or DEFAULT_EVOLUTION_PATH
    out_path = output_path or DEFAULT_OUTPUT_PATH

    # Read at most MEMORY_COMPRESSOR_RECENT_LIMIT total (100 per source)
    per_source = max(1, MEMORY_COMPRESSOR_RECENT_LIMIT // 3)
    history = read_recent_jsonl_records(hist_path, per_source)
    feedback = read_recent_jsonl_records(feed_path, per_source)
    evolution = read_recent_jsonl_records(evol_path, per_source)

    records_read = len(history) + len(feedback) + len(evolution)

    if records_read < MIN_COMBINED_RECORDS:
        return {
            "records_read": records_read,
            "patterns_created": 0,
            "output_path": str(out_path),
            "status": "skipped",
            "reason": "fewer_than_20_records",
        }

    patterns = _extract_patterns(history, feedback, evolution)

    if not patterns:
        return {
            "records_read": records_read,
            "patterns_created": 0,
            "output_path": str(out_path),
            "status": "skipped",
            "reason": "no_strong_pattern",
        }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "patterns": [p.to_dict() for p in patterns],
        "records_read": records_read,
        "version": 1,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "records_read": records_read,
        "patterns_created": len(patterns),
        "output_path": str(out_path),
        "status": "ok",
    }
