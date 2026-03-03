"""In-process event bus: subscribe / publish."""

from collections.abc import Callable
from typing import Any

from lumos_social.core.events import Event

Handler = Callable[[Event], None]


class EventBus:
    """Subscribe handlers, publish events. Single process."""

    def __init__(self) -> None:
        self._handlers: list[Handler] = []
        self._events_seen: int = 0

    def subscribe(self, handler: Handler) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: Handler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def publish(self, event: Event) -> None:
        self._events_seen += 1
        for h in self._handlers:
            try:
                h(event)
            except Exception:
                pass

    def stats(self) -> dict[str, Any]:
        return {"handlers": len(self._handlers), "events_seen": self._events_seen}
