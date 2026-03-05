"""
Presence state machine: single source for presence state.
States: DISABLED, ENABLED_IDLE, RUNNING (STOPPING is internal to thread).
Log rules: presence_enabled/presence_disabled on config change only;
  presence_started/presence_stopped from presence_lock (stopped only when not silent + was_running).
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PresenceState(str, Enum):
    DISABLED = "DISABLED"           # config enabled=False, thread not running
    ENABLED_IDLE = "ENABLED_IDLE"   # config enabled=True, thread not running
    RUNNING = "RUNNING"             # config enabled=True, thread running


def get_state(base_dir: Path, presence_lock_module: Any) -> PresenceState:
    """Current presence state from config + thread. No side effects."""
    enabled = False
    try:
        enabled = bool(presence_lock_module.is_enabled_from_config(Path(base_dir)))
    except Exception:
        pass
    running = False
    try:
        running = bool(presence_lock_module.is_running())
    except Exception:
        pass
    if not enabled:
        return PresenceState.DISABLED
    return PresenceState.RUNNING if running else PresenceState.ENABLED_IDLE
