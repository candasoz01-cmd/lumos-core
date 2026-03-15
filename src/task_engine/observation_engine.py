"""
Observation-driven TaskEngine: receive system_monitor signals, evaluate triggers,
create Task objects, push into TaskQueue.

Read-only: no destructive operations, no UI logic. Allows Lumos to autonomously
generate tasks based on system state.
"""
from __future__ import annotations

from typing import Any

from task_engine.models import Task, TaskPriority
from task_engine.queue import TaskQueue

# Default thresholds for signal-based triggers (system_monitor / device_perception shape).
TRIGGER_EFFICIENCY_BELOW = 70
TRIGGER_HIGH_CPU_PERCENT = 80.0
TRIGGER_HIGH_MEMORY_PERCENT = 85.0
TRIGGER_PROCESS_COUNT_ABOVE = 200
TRIGGER_HIGH_CPU_PROCESS_COUNT = 5
TRIGGER_HIGH_MEMORY_PROCESS_COUNT = 5
TRIGGER_SUSPICIOUS_COUNT = 1
TRIGGER_SENSITIVE_ACCESS_COUNT = 1


def _evaluate_triggers(signal: dict[str, Any]) -> list[tuple[str, TaskPriority]]:
    """
    Evaluate system_monitor-style signal; return list of (description, priority).
    Read-only; no side effects.
    """
    out: list[tuple[str, TaskPriority]] = []

    cpu = signal.get("cpu_percent")
    mem = signal.get("memory_percent")
    process_count = signal.get("process_count")
    if cpu is not None and float(cpu) >= TRIGGER_HIGH_CPU_PERCENT:
        out.append(("Review high CPU usage", TaskPriority.HIGH))
    if mem is not None and float(mem) >= TRIGGER_HIGH_MEMORY_PERCENT:
        out.append(("Review high memory usage", TaskPriority.HIGH))
    if process_count is not None and int(process_count) >= TRIGGER_PROCESS_COUNT_ABOVE:
        out.append(("Show device report", TaskPriority.MEDIUM))

    efficiency = signal.get("efficiency_score")
    if efficiency is not None and int(efficiency) < TRIGGER_EFFICIENCY_BELOW:
        out.append(("Show device report", TaskPriority.MEDIUM))

    high_cpu = signal.get("high_cpu_processes") or []
    high_mem = signal.get("high_memory_processes") or []
    suspicious = signal.get("suspicious_background") or []
    sensitive = signal.get("sensitive_access") or []

    if len(high_cpu) >= TRIGGER_HIGH_CPU_PROCESS_COUNT:
        out.append(("Review high CPU processes", TaskPriority.HIGH))
    if len(high_mem) >= TRIGGER_HIGH_MEMORY_PROCESS_COUNT:
        out.append(("Review high memory processes", TaskPriority.HIGH))
    if len(suspicious) >= TRIGGER_SUSPICIOUS_COUNT:
        out.append(("Review suspicious background activity", TaskPriority.CRITICAL))
    if len(sensitive) >= TRIGGER_SENSITIVE_ACCESS_COUNT:
        out.append(("Review sensitive access", TaskPriority.HIGH))

    return out


class ObservationTaskEngine:
    """
    TaskEngine: receives signals from system_monitor, evaluates triggers,
    creates Task objects, and pushes them into TaskQueue.

    Read-only system interaction; no destructive operations; no UI logic.
    """

    def __init__(self, queue: TaskQueue | None = None, max_queue_size: int = 500) -> None:
        self._queue = queue if queue is not None else TaskQueue(max_size=max_queue_size)

    @property
    def queue(self) -> TaskQueue:
        return self._queue

    def ingest_signal(self, signal: dict[str, Any], source: str = "system_monitor") -> int:
        """
        Evaluate triggers on a signal (system_monitor report or device_perception snapshot),
        create Tasks, and enqueue them. Returns the number of tasks enqueued.
        """
        triggered = _evaluate_triggers(signal)
        count = 0
        for description, priority in triggered:
            task = Task.create(
                source=source,
                description=description,
                priority=priority,
            )
            if self._queue.add_task(task):
                count += 1
        return count
