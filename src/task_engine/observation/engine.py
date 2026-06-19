"""
ObservationEngine: record events and maintain world state.
TaskEngine calls record_event; engine updates memory and world state.
Optional EC2-10 disk spill when lifecycle_spill is configured.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from task_engine.observation.events import ObservationEvent
from task_engine.observation.memory import ObservationMemory
from task_engine.observation.state import WorldState

if TYPE_CHECKING:
    from task_engine.observation.lifecycle_spill import ObservationLifecycleSpill


class ObservationEngine:
    """
    record_event(event) → store in memory and update world state.
    get_recent_events(limit) → from memory.
    """

    def __init__(
        self,
        memory: ObservationMemory | None = None,
        world_state: WorldState | None = None,
        lifecycle_spill: ObservationLifecycleSpill | None = None,
    ) -> None:
        self._memory = memory or ObservationMemory()
        self._world_state = world_state or WorldState()
        self._lifecycle_spill = lifecycle_spill

    def attach_lifecycle_spill(self, spill: ObservationLifecycleSpill) -> None:
        """EC2-10: wire disk spill after construction (TaskEngine auto-wire)."""
        self._lifecycle_spill = spill

    def record_event(self, event: ObservationEvent) -> None:
        self._memory.append(event)
        self.update_world_state(event)
        if self._lifecycle_spill is not None:
            self._lifecycle_spill.append(event)

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

    @property
    def lifecycle_spill(self) -> ObservationLifecycleSpill | None:
        return self._lifecycle_spill
