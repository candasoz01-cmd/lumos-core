"""Build connector from config and CLI args."""

from lumos_social.config import Config
from lumos_social.connectors.base import BaseConnector
from lumos_social.connectors.mock import MockConnector


def build_connector(
    cfg: Config,
    once: bool = False,
    n: int | None = None,
) -> BaseConnector:
    """Build connector from config (mock for now)."""
    if cfg.connector == "mock":
        return MockConnector(once=once, n=n)
    return MockConnector(once=once, n=n)
