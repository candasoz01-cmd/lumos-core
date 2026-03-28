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
    """Run safe local step; patch: hedefleri patch_pipeline ile gerçek uygular."""
    desc = (task.description or "").strip()
    if desc.lower().startswith("patch:"):
        from task_engine.executors.patch_apply_executor import patch_apply_executor

        return patch_apply_executor(step, task, context)
    return True, "Güvenli yerel iş tamamlandı.", "", False
