#!/usr/bin/env python3
"""
Quick manual test of the full decision pipeline.

- Calls run_decision_pipeline() with goal "test decision" and target src/core/state.py.
- Prints format_result_preview(result).
- No file changes (apply is never used; update_weights_after_run=False to avoid writing weights).
"""
from __future__ import annotations

from pathlib import Path

from core.decision_pipeline import run_decision_pipeline
from core.decision_runner import format_result_preview


def main() -> None:
    goal = "test decision"
    target_paths = [Path("src/core/state.py")]

    result = run_decision_pipeline(
        goal,
        target_paths,
        base_dir=None,
        update_weights_after_run=False,
    )

    if result is None:
        print("No result (empty options or invalid paths).")
        return

    print(format_result_preview(result))


if __name__ == "__main__":
    main()
