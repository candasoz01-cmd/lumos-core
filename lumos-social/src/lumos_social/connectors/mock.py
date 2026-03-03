"""Mock connector: emit N or 1 incoming_message events in start(bus)."""

import uuid

from lumos_social.connectors.base import BaseConnector
from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event


class MockConnector(BaseConnector):
    """--once: 1 event. --n N: N events. Payload: platform, from_user, text, message_id."""

    def __init__(self, once: bool = False, n: int | None = None) -> None:
        self._once = once
        self._n = n
        self._stopped = False

    @property
    def name(self) -> str:
        return "mock"

    def start(self, bus: EventBus) -> None:
        count = 1 if self._once else (self._n if self._n is not None else 1)
        for i in range(count):
            event = self._make_event(seq=i + 1)
            bus.publish(event)
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def _make_event(self, seq: int = 1) -> Event:
        return Event(
            kind="incoming_message",
            payload={
                "platform": "mock",
                "from_user": "user_1",
                "text": "hello",
                "message_id": f"mock-{uuid.uuid4().hex[:8]}",
                "seq": seq,
            },
            source="mock",
        )

    def health(self) -> dict[str, object]:
        return {"name": self.name, "ok": True}
