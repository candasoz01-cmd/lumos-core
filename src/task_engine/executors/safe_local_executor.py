"""
Safe local step executor: safe, non-destructive local actions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from task_engine.action_registry import ExecutionContext

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord, TaskStep


def safe_local_executor(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
) -> tuple[bool, str, str, bool]:
    """Run safe local step; no destructive action."""
    return True, "Güvenli yerel iş tamamlandı.", "", False
