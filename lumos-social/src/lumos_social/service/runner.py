"""Always-on service runner: start(), stop(), health(), event loop, connector + bus."""

from typing import Any

from lumos_social.app.handlers import register_handlers
from lumos_social.app.runner import build_connector
from lumos_social.config import Config, load_config
from lumos_social.connectors.base import BaseConnector
from lumos_social.core.bus import EventBus
from lumos_social.logging import get_logger, setup_logging

logger = get_logger("service.runner")


class ServiceRunner:
    """start/stop/health; connector başlatır, bus'a handler register eder."""

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or load_config()
        self._bus: EventBus | None = None
        self._connector: BaseConnector | None = None
        self._running = False

    def start(self) -> None:
        """Event loop (sync); connector başlatır, bus register eder."""
        setup_logging(self._config.log_level)
        self._bus = EventBus()
        register_handlers(self._bus)
        self._connector = build_connector(self._config, once=False, n=None)
        if self._connector is None:
            raise RuntimeError("No connector built")
        self._connector.start(self._bus)
        self._running = True
        logger.info("service started connector=%s", self._config.connector)

    def stop(self) -> None:
        """Connector ve kaynakları durdur."""
        if self._connector is not None:
            try:
                self._connector.stop()
            except Exception:
                logger.exception("connector stop error")
            self._connector = None
        self._bus = None
        self._running = False
        logger.info("service stopped")

    def health(self) -> dict[str, Any]:
        """Durum: running, connector, bus stats."""
        if self._bus is None:
            return {"running": False, "connector": self._config.connector}
        return {
            "running": self._running,
            "connector": self._config.connector,
            "bus_events_seen": self._bus.stats().get("events_seen", 0),
        }
