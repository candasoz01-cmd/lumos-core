"""Simple middleware pipeline: process events through a chain of handlers."""

import logging
from collections.abc import Callable

from lumos_social.core.events import Event

Handler = Callable[[Event], None]
logger = logging.getLogger(__name__)


class Pipeline:
    """Register handlers; process(event) runs each in order (middleware-style)."""

    def __init__(self) -> None:
        self._handlers: list[Handler] = []

    def add_handler(self, handler: Handler) -> None:
        self._handlers.append(handler)

    def remove_handler(self, handler: Handler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def process(self, event: Event) -> None:
        for h in self._handlers:
            try:
                h(event)
            except Exception:
                logger.exception("pipeline handler error")
                raise


def log_handler(event: Event) -> None:
    """Minimal handler: log/print the event."""
    msg = f"event kind={event.kind} source={event.source} payload={event.payload}"
    logger.info(msg)
    print(msg)
