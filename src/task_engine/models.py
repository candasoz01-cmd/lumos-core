"""
Core task model for the task_engine module.

Task and TaskPriority are used by TaskQueue and TaskEngine for
observation-driven internal tasks. Read-only system interaction; no destructive operations.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskPriority(str, Enum):
    """Priority for internal tasks. Higher priority is preferred when draining."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def order(self) -> int:
        """Numeric order for sorting (higher = more urgent)."""
        return {"low": 0, "medium": 1, "high": 2, "critical": 3}[self.value]


@dataclass
class Task:
    """
    A single internal task generated from system observations.
    Minimal fields: id, source, description, priority, created_at.
    """

    id: str
    source: str
    description: str
    priority: TaskPriority
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        source: str,
        description: str,
        priority: TaskPriority,
        id_: str | None = None,
    ) -> Task:
        """Create a Task with an optional id (generated if not provided)."""
        return cls(
            id=id_ or str(uuid.uuid4()),
            source=source,
            description=description,
            priority=priority,
            created_at=time.time(),
        )
