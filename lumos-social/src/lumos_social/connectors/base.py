"""Connector protocol: start(bus), stop(). Connectors emit events to bus."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumos_social.core.bus import EventBus


class BaseConnector(ABC):
    """Interface: start(bus) to emit events, stop() to tear down."""

    @abstractmethod
    def start(self, bus: "EventBus") -> None:
        """Start and emit events to bus (e.g. once, N times, or loop)."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop and release resources."""
        ...
