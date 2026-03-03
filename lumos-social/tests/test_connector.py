"""Tests for connector interface and mock connector."""

from lumos_social.connector import ConnectorEvent
from lumos_social.mock_connector import MockConnector


def test_mock_connector_name() -> None:
    c = MockConnector()
    assert c.name == "mock"


def test_mock_connector_connect_disconnect() -> None:
    c = MockConnector()
    assert c.connect() is True
    assert c.status()["connected"] is True
    c.disconnect()
    assert c.status()["connected"] is False


def test_mock_connector_poll_when_disconnected() -> None:
    c = MockConnector()
    assert c.poll() == []


def test_mock_connector_poll_when_connected() -> None:
    c = MockConnector()
    c.connect()
    events = c.poll()
    assert len(events) == 1
    assert events[0].source == "mock"
    assert events[0].kind == "mock_ping"
    assert "seq" in events[0].payload
    c.poll()
    assert c.status()["poll_count"] == 2


def test_connector_event_dataclass() -> None:
    e = ConnectorEvent(source="x", kind="y", payload={"a": 1}, ts=123.0)
    assert e.source == "x"
    assert e.kind == "y"
    assert e.payload["a"] == 1
    assert e.ts == 123.0
