"""Connector + service: mock ile update çek → event oluşsun."""

from lumos_social.connectors.mock import MockConnector
from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event
from lumos_social.service import SocialService


def test_mock_fetch_and_publish_produces_event() -> None:
    """Mock ile 'update çek' → bus'ta event oluşur."""
    connector = MockConnector()
    bus = EventBus()
    service = SocialService(connector, bus)
    seen: list[Event] = []

    bus.subscribe(seen.append)
    n = service.fetch_and_publish()

    assert n == 1
    assert len(seen) == 1
    assert seen[0].kind == "incoming_message"
    assert seen[0].payload.get("text") == "hello from mock"
    assert seen[0].source == "mock"


def test_mock_fetch_twice_two_events() -> None:
    connector = MockConnector()
    bus = EventBus()
    service = SocialService(connector, bus)
    seen: list[Event] = []
    bus.subscribe(seen.append)

    service.fetch_and_publish()
    service.fetch_and_publish()

    assert len(seen) == 2
    assert seen[0].payload.get("seq") == 1
    assert seen[1].payload.get("seq") == 2


def test_mock_health() -> None:
    connector = MockConnector()
    assert connector.health()["ok"] is True
    connector.fetch_updates()
    assert connector.health()["fetch_count"] == 1
