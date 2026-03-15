"""
Observation event types: what happened in the system.
Safe, in-memory only. No external IO.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# Event type constants
EVENT_ACTION_EXECUTED = "action_executed"
EVENT_STEP_VERIFIED = "step_verified"
EVENT_STEP_FAILED = "step_failed"
EVENT_POLICY_BLOCKED = "policy_blocked"
EVENT_TASK_CREATED = "task_created"


@dataclass(frozen=True)
class ObservationEvent:
    """Single observation event. Immutable."""
    timestamp: float
    task_id: int
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    step_id: int | None = None  # step index (0-based)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "payload": dict(self.payload),
            "step_id": self.step_id,
        }


def make_event(
    task_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
    step_id: int | None = None,
    timestamp: float | None = None,
) -> ObservationEvent:
    """Create an ObservationEvent with current timestamp if not provided."""
    return ObservationEvent(
        timestamp=timestamp if timestamp is not None else time.time(),
        task_id=task_id,
        event_type=event_type,
        payload=payload or {},
        step_id=step_id,
    )
