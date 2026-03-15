"""
Analyze step executor: safe, non-destructive analysis.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from task_engine.action_registry import ExecutionContext

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord, TaskStep


def analyze_executor(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
) -> tuple[bool, str, str, bool]:
    """Run analyze step; no side effects, output is simulation."""
    return True, "Analiz tamamlandı.", "", False
