"""
ObservationEngine: record events and maintain world state.
TaskEngine calls record_event; engine updates memory and world state.
No external IO. Safe, in-memory only.
"""
from __future__ import annotations

from task_engine.observation.events import ObservationEvent
from task_engine.observation.memory import ObservationMemory
from task_engine.observation.state import WorldState


class ObservationEngine:
    """
    record_event(event) → store in memory and update world state.
    get_recent_events(limit) → from memory.
    """
    def __init__(
        self,
        memory: ObservationMemory | None = None,
        world_state: WorldState | None = None,
    ) -> None:
        self._memory = memory or ObservationMemory()
        self._world_state = world_state or WorldState()

    def record_event(self, event: ObservationEvent) -> None:
        self._memory.append(event)
        self.update_world_state(event)

    def get_recent_events(self, limit: int = 50) -> list[ObservationEvent]:
        return self._memory.get_recent(limit=limit)

    def update_world_state(self, event: ObservationEvent) -> None:
        """Called by record_event; exposed for direct update if needed."""
        self._world_state.push_event(event)

    @property
    def world_state(self) -> WorldState:
        return self._world_state

    @property
    def memory(self) -> ObservationMemory:
        return self._memory
