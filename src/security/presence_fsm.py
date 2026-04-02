"""Presence coarse state for status / tests."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class PresenceState(Enum):
    DISABLED = "disabled"
    ENABLED_IDLE = "enabled_idle"
    RUNNING = "running"


def get_state(base_dir: Path, pl) -> PresenceState:
    if not pl.is_enabled_from_config(base_dir):
        return PresenceState.DISABLED
    if pl.is_running():
        return PresenceState.RUNNING
    return PresenceState.ENABLED_IDLE
