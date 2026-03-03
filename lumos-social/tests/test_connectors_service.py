"""Connector start(bus): mock ile event emit edilir."""

from lumos_social.connectors.mock import MockConnector
from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event


def test_mock_start_emits_one_event_with_once() -> None:
    bus = EventBus()
    seen: list[Event] = []
    bus.subscribe(seen.append)
    connector = MockConnector(once=True)
    connector.start(bus)
    assert len(seen) == 1
    assert seen[0].kind == "incoming_message"
    assert seen[0].payload.get("platform") == "mock"
    assert seen[0].payload.get("from_user") == "user_1"
    assert seen[0].payload.get("text") == "hello"


def test_mock_start_emits_n_events() -> None:
    bus = EventBus()
    seen: list[Event] = []
    bus.subscribe(seen.append)
    connector = MockConnector(n=3)
    connector.start(bus)
    assert len(seen) == 3
    for i, e in enumerate(seen):
        assert e.kind == "incoming_message"
        assert e.payload.get("seq") == i + 1


def test_mock_health() -> None:
    connector = MockConnector()
    assert connector.health()["ok"] is True
    assert connector.health()["name"] == "mock"
