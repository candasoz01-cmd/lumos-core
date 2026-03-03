"""Connectors: base interface + implementations."""

from lumos_social.connectors.base import BaseConnector, Update
from lumos_social.connectors.mock import MockConnector

__all__ = ["BaseConnector", "Update", "MockConnector"]
