"""
Device-driven task layer: receive system signals, evaluate triggers, create
structured tasks, queue them, and feed device_action_policy.

Read-only by default: no process termination or destructive system operations.
This module extends the core task_engine (Task, TaskPriority, TaskQueue, ObservationTaskEngine)
with device_guard and device_action_policy integration.

Flow:
  system_monitor / device_perception (signals)
       → ObservationTaskEngine.ingest_signal() or DeviceTaskEngine.ingest_report()
       → triggers evaluated → Task(s) created → TaskQueue
       → list_tasks() / drain() → device_action_policy (suggestions / execution gating)
"""

from __future__ import annotations

from typing import Any

from task_engine.models import Task, TaskPriority
from task_engine.observation_engine import ObservationTaskEngine

# Optional device-layer dependency; engine still works without it (no tasks from policy).
try:
    from device.device_action_policy import suggest_actions
    from device.device_guard import DeviceGuard
except ImportError:
    suggest_actions = None  # type: ignore[assignment]
    DeviceGuard = None  # type: ignore[assignment]


def _priority_from_category(category: str) -> TaskPriority:
    """Map device_action_policy category to TaskPriority."""
    if category == "security_sensitive":
        return TaskPriority.CRITICAL
    if category == "process_control":
        return TaskPriority.HIGH
    return TaskPriority.MEDIUM


class DeviceTaskEngine(ObservationTaskEngine):
    """
    Extends ObservationTaskEngine with device_guard and device_action_policy:
    ingest_report() and run_guard_and_ingest() create Tasks from suggested actions.
    Read-only: no process termination or destructive system operations.
    """

    def ingest_report(self, report: dict[str, Any], source: str = "device_guard") -> int:
        """
        Use device_guard report shape and device_action_policy.suggest_actions
        to create one Task per suggested action and enqueue. Returns number enqueued.
        If device_action_policy is unavailable, returns 0. Read-only.
        """
        if suggest_actions is None:
            return 0
        suggestions = suggest_actions(report)
        count = 0
        for s in suggestions:
            description = str(s.get("description") or s.get("action_id", "show_device_report")).replace("_", " ").title()
            priority = _priority_from_category(str(s.get("category", "")))
            task = Task.create(source=source, description=description, priority=priority)
            if self._queue.add_task(task):
                count += 1
        return count

    def run_guard_and_ingest(self) -> int:
        """
        One-shot: run device_guard (system_monitor + classification), then
        ingest the report into the queue via suggest_actions. Returns number of tasks enqueued.
        If device_guard is unavailable, returns 0. Read-only.
        """
        if DeviceGuard is None:
            return 0
        guard = DeviceGuard()
        report = guard.run().to_dict()
        return self.ingest_report(report, source="device_guard")

    def get_pending_tasks(self, sort_by_priority: bool = True) -> list[Task]:
        """Return current queued tasks without removing them. Read-only."""
        return self._queue.list_tasks()

    def drain_queue(self, n: int | None = None, by_priority: bool = True) -> list[Task]:
        """Remove and return up to n tasks (all if n is None). By priority or FIFO."""
        return self._queue.drain(n=n, by_priority=by_priority)
