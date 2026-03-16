#!/usr/bin/env python3
"""
Summarize Lumos evolution log (logs/lumos_evolution.jsonl).

Prints: total events, success rate, rollback rate, most affected files,
average risk level. No changes to existing modules; reads JSONL only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter

DEFAULT_LOG_PATH = Path("logs") / "lumos_evolution.jsonl"

# Match strategy_updater semantics for success and risk
SUCCESS_RESULTS = frozenset({"ok", "applied", "rolled_back"})
SENSITIVITY_RISK = {"CRITICAL": 3, "HIGH": 2, "LOW": 1}
TOP_FILES = 10


def _risk_from_sensitivity_levels(levels: list) -> float:
    if not levels:
        return 0.0
    return float(max(SENSITIVITY_RISK.get(str(x).upper(), 0) for x in levels))


def _load_events(log_path: Path) -> list[dict]:
    events: list[dict] = []
    if not log_path.exists():
        return events
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _compute_summary(events: list[dict]) -> dict:
    total = len(events)
    if total == 0:
        return {
            "total_events": 0,
            "success_rate": 0.0,
            "rollback_rate": 0.0,
            "avg_risk": 0.0,
            "most_affected": [],
        }

    success_count = sum(
        1 for e in events if e.get("result", "") in SUCCESS_RESULTS
    )
    rollback_count = sum(
        1 for e in events
        if e.get("rollback_occurred") or e.get("result") == "rolled_back"
    )
    risk_sum = 0.0
    for e in events:
        levels = e.get("sensitivity_levels") or []
        if isinstance(levels, list):
            risk_sum += _risk_from_sensitivity_levels(levels)
    avg_risk = risk_sum / total

    path_counts: Counter[str] = Counter()
    for e in events:
        paths = e.get("affected_paths") or []
        if isinstance(paths, list):
            for p in paths:
                if p:
                    path_counts[str(p)] += 1
    most_affected = path_counts.most_common(TOP_FILES)

    return {
        "total_events": total,
        "success_rate": success_count / total,
        "rollback_rate": rollback_count / total,
        "avg_risk": avg_risk,
        "most_affected": most_affected,
    }


def _print_report(summary: dict, log_path: Path) -> None:
    print(f"Lumos evolution log: {log_path}")
    print("-" * 50)
    print(f"  Total events:     {summary['total_events']}")
    print(f"  Success rate:     {summary['success_rate']:.1%}")
    print(f"  Rollback rate:    {summary['rollback_rate']:.1%}")
    print(f"  Average risk:     {summary['avg_risk']:.2f}")
    print()
    print("  Most affected paths:")
    if summary["most_affected"]:
        for path, count in summary["most_affected"]:
            print(f"    {count:4d}  {path}")
    else:
        print("    (none)")
    print("-" * 50)


def main() -> int:
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LOG_PATH
    log_path = log_path.resolve()

    events = _load_events(log_path)
    summary = _compute_summary(events)
    _print_report(summary, log_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
