"""Event dataclasses for the message pipeline."""

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    """Base event: kind + payload. Used for bus and pipeline."""

    kind: str
    payload: dict[str, Any]
    source: str = ""
    ts: float | None = None


def incoming_message_event(
    payload: dict[str, Any] | None = None,
    source: str = "",
    ts: float | None = None,
) -> Event:
    """Build an 'incoming_message' event (e.g. from a connector)."""
    return Event(
        kind="incoming_message",
        payload=payload or {},
        source=source,
        ts=ts or time.time(),
    )
