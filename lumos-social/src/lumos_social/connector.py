"""Connector interface for social platforms. No real integrations in v1; mock only."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ConnectorEvent:
    """Single event from a connector (e.g. message, notification)."""

    source: str
    kind: str
    payload: dict[str, Any]
    ts: float | None = None


class BaseConnector(ABC):
    """Interface that all social connectors must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector identifier (e.g. 'mock', 'twitter')."""
        ...

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection. Returns True if ready. No tokens in repo."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down connection."""
        ...

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Current status (connected, last_poll, etc.)."""
        ...

    def poll(self) -> list[ConnectorEvent]:
        """Fetch new events since last poll. Default: empty list."""
        return []
