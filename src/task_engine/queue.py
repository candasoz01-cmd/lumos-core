"""
In-memory task queue for the task_engine module.

TaskQueue holds Task objects produced by TaskEngine. Read-only system interaction;
no destructive operations on the system. FIFO by default; get_next_task can
return by priority when configured.
"""
from __future__ import annotations

from collections import deque

from task_engine.models import Task, TaskPriority


class TaskQueue:
    """
    In-memory queue of Task items.
    - add_task(task): enqueue a task.
    - get_next_task(): remove and return the next task (by priority then FIFO).
    - list_tasks(): return a snapshot of all queued tasks (no removal).
    """

    def __init__(self, max_size: int = 500) -> None:
        self._deque: deque[Task] = deque(maxlen=max(1, max_size))

    def add_task(self, task: Task) -> bool:
        """Append a task. Returns False if queue is full."""
        if len(self._deque) >= self._deque.maxlen:
            return False
        self._deque.append(task)
        return True

    def get_next_task(self) -> Task | None:
        """Remove and return the next task (highest priority first, then FIFO). None if empty."""
        if not self._deque:
            return None
        # Return highest priority, then oldest
        ordered = sorted(self._deque, key=lambda t: (-t.priority.order(), t.created_at))
        next_task = ordered[0]
        self._deque.remove(next_task)
        return next_task

    def list_tasks(self) -> list[Task]:
        """Return a copy of all queued tasks (no removal). Order: by priority then created_at."""
        out = list(self._deque)
        out.sort(key=lambda t: (-t.priority.order(), t.created_at))
        return out

    def drain(self, n: int | None = None, by_priority: bool = True) -> list[Task]:
        """Remove and return up to n tasks (all if n is None). By priority then FIFO."""
        result: list[Task] = []
        while self._deque and (n is None or len(result) < n):
            t = self.get_next_task() if by_priority else self._deque.popleft()
            result.append(t)
        return result

    def __len__(self) -> int:
        return len(self._deque)
