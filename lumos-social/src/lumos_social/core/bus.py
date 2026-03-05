from collections import defaultdict
from typing import Callable

from .events import Event


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._handlers[event_type].append(handler)

    def emit(self, event: Event) -> None:
        for handler in self._handlers.get(event.type, []):
            handler(event)
