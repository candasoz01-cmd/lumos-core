"""Mock connector: returns fake data, no external calls."""

from typing import Any

from lumos_social.connectors.base import BaseConnector, Update


class MockConnector(BaseConnector):
    """Sahte data dönen connector. fetch_updates ile test update'leri üretir."""

    def __init__(self) -> None:
        self._fetch_count = 0
        self._sent: list[tuple[str, str]] = []

    @property
    def name(self) -> str:
        return "mock"

    def fetch_updates(self) -> list[Update]:
        self._fetch_count += 1
        return [
            Update(
                id=f"mock-{self._fetch_count}-1",
                kind="message",
                payload={"text": "hello from mock", "seq": self._fetch_count},
                source=self.name,
            ),
        ]

    def send_message(self, target: str, content: str) -> bool:
        self._sent.append((target, content))
        return True

    def health(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": True,
            "fetch_count": self._fetch_count,
        }
