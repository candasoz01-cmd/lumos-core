"""
TaskQueue watcher: prints new tasks to CLI when they appear.

Read-only: observes the queue, does not modify it. Tracks seen task IDs
and on each tick() prints tasks that have not been seen before.
"""
from __future__ import annotations

from task_engine.models import Task
from task_engine.queue import TaskQueue


class TaskQueueWatcher:
    """
    Watches a TaskQueue and prints new tasks to stdout when they appear.
    Call tick() from the CLI loop (e.g. each iteration).
    """

    def __init__(self, queue: TaskQueue) -> None:
        self._queue = queue
        self._seen_ids: set[str] = set()

    def tick(self) -> None:
        """
        List current tasks; for any task not yet seen, print it and mark seen.
        Prune seen_ids to current queue so drained tasks are forgotten.
        """
        current = self._queue.list_tasks()
        current_ids = {t.id for t in current}
        for task in current:
            if task.id not in self._seen_ids:
                self._seen_ids.add(task.id)
                self._print_task(task)
        self._seen_ids &= current_ids

    def _print_task(self, task: Task) -> None:
        """Print a single task line (CLI format)."""
        print(f"  [yeni] [{task.priority.value}] {task.description} (kaynak: {task.source})")
