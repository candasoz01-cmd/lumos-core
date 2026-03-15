"""
ObservationMemory: in-memory store for observation events.
No persistence. Simple list append and recent retrieval.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from task_engine.observation.events import ObservationEvent


class ObservationMemory:
    """Stores events in a bounded in-memory list. No external IO."""
    def __init__(self, maxlen: int = 1000) -> None:
        self._events: deque["ObservationEvent"] = deque(maxlen=maxlen)

    def append(self, event: "ObservationEvent") -> None:
        self._events.append(event)

    def get_recent(self, limit: int = 50) -> list["ObservationEvent"]:
        """Return most recent events (newest last)."""
        n = min(limit, len(self._events))
        if n <= 0:
            return []
        return list(self._events)[-n:]

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)
