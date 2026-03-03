"""Connector interface: fetch_updates, send_message, health."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Update:
    """Single update from a connector (e.g. new message, notification)."""

    id: str
    kind: str
    payload: dict[str, Any]
    source: str = ""


class BaseConnector(ABC):
    """Interface for social connectors: fetch updates, send message, health check."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector identifier (e.g. 'mock', 'twitter')."""
        ...

    @abstractmethod
    def fetch_updates(self) -> list[Update]:
        """Fetch new updates since last call. Returns list of Update."""
        ...

    @abstractmethod
    def send_message(self, target: str, content: str) -> bool:
        """Send a message to target. Returns True on success."""
        ...

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Current health/status (e.g. connected, last_fetch)."""
        ...
