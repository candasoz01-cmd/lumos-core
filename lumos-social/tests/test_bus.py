"""Tests for event bus."""

from lumos_social.bus import EventBus
from lumos_social.connector import ConnectorEvent


def test_bus_publish_subscribe() -> None:
    bus = EventBus()
    seen: list[ConnectorEvent] = []

    def handler(ev: ConnectorEvent) -> None:
        seen.append(ev)

    bus.subscribe(handler)
    e = ConnectorEvent(source="t", kind="k", payload={})
    bus.publish(e)
    assert len(seen) == 1
    assert seen[0] is e
    assert bus.stats()["events_seen"] == 1
    assert bus.stats()["handlers"] == 1


def test_bus_unsubscribe() -> None:
    bus = EventBus()
    seen: list[ConnectorEvent] = []

    def handler(ev: ConnectorEvent) -> None:
        seen.append(ev)

    bus.subscribe(handler)
    bus.publish(ConnectorEvent(source="a", kind="b", payload={}))
    bus.unsubscribe(handler)
    bus.publish(ConnectorEvent(source="c", kind="d", payload={}))
    assert len(seen) == 1
