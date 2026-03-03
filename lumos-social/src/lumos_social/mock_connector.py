"""Mock connector for testing and development. No real platform calls."""

import time
from typing import Any

from lumos_social.connector import BaseConnector, ConnectorEvent


class MockConnector(BaseConnector):
    """In-memory mock that never touches external services."""

    def __init__(self) -> None:
        self._connected = False
        self._poll_count = 0

    @property
    def name(self) -> str:
        return "mock"

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def status(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "name": self.name,
            "poll_count": self._poll_count,
        }

    def poll(self) -> list[ConnectorEvent]:
        if not self._connected:
            return []
        self._poll_count += 1
        return [
            ConnectorEvent(
                source=self.name,
                kind="mock_ping",
                payload={"seq": self._poll_count},
                ts=time.time(),
            )
        ]
