"""
WorldState: aggregated view of recent events and system state.
In-memory only. No persistence.
"""
from __future__ import annotations

from collections import deque
from typing import Any

from task_engine.observation.events import (
    EVENT_STEP_FAILED,
    EVENT_TASK_CREATED,
    ObservationEvent,
)

# Default bounds for in-memory state
DEFAULT_RECENT_EVENTS_MAX = 500
DEFAULT_LAST_TASKS_MAX = 50
DEFAULT_LAST_ERRORS_MAX = 100


class WorldState:
    """
    Maintains recent_events, known_files (placeholder), last_tasks, last_errors.
    Simple in-memory storage with bounded lists.
    """
    def __init__(
        self,
        recent_events_max: int = DEFAULT_RECENT_EVENTS_MAX,
        last_tasks_max: int = DEFAULT_LAST_TASKS_MAX,
        last_errors_max: int = DEFAULT_LAST_ERRORS_MAX,
    ) -> None:
        self._recent_events: deque[ObservationEvent] = deque(maxlen=recent_events_max)
        self.known_files: list[str] = []  # intentional stub — file inventory deferred (NA-06)
        self._last_tasks: deque[dict[str, Any]] = deque(maxlen=last_tasks_max)
        self._last_errors: deque[str] = deque(maxlen=last_errors_max)

    @property
    def recent_events(self) -> list[ObservationEvent]:
        return list(self._recent_events)

    @property
    def last_tasks(self) -> list[dict[str, Any]]:
        return list(self._last_tasks)

    @property
    def last_errors(self) -> list[str]:
        return list(self._last_errors)

    def push_event(self, event: ObservationEvent) -> None:
        self._recent_events.append(event)
        if event.event_type == EVENT_STEP_FAILED:
            err = event.payload.get("error") or event.payload.get("message") or "step_failed"
            self._last_errors.append(str(err)[:200])
        elif event.event_type == EVENT_TASK_CREATED:
            self._last_tasks.append({
                "task_id": event.task_id,
                **event.payload,
            })

    def clear(self) -> None:
        self._recent_events.clear()
        self._last_tasks.clear()
        self._last_errors.clear()
