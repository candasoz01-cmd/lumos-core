"""Structured logging: JSON optional, human default, log level. Delegates to logging_config."""

from lumos_social.logging_config import get_logger, setup_logging

__all__ = ["get_logger", "setup_logging"]
