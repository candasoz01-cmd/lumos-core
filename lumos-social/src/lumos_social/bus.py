"""Event bus / message pipeline skeleton. In-memory, single process."""

from collections.abc import Callable
from typing import Any

from lumos_social.connector import ConnectorEvent

Handler = Callable[[ConnectorEvent], None]


class EventBus:
    """Simple in-process event bus: subscribe handlers, publish events."""

    def __init__(self) -> None:
        self._handlers: list[Handler] = []
        self._events_seen: int = 0

    def subscribe(self, handler: Handler) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: Handler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def publish(self, event: ConnectorEvent) -> None:
        self._events_seen += 1
        for h in self._handlers:
            try:
                h(event)
            except Exception:
                pass  # don't break bus on handler error

    def stats(self) -> dict[str, Any]:
        return {"handlers": len(self._handlers), "events_seen": self._events_seen}
