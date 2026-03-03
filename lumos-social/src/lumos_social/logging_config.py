"""Structured logging: JSON optional, human readable default, log level kontrolü."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _is_json_log() -> bool:
    return _env("LUMOS_SOCIAL_JSON_LOG", "0").lower() in ("1", "true", "yes")


class HumanHandler(logging.Handler):
    """Human readable: level message."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            sys.stderr.write(msg + "\n")
        except Exception:
            self.handleError(record)


class JsonHandler(logging.Handler):
    """One JSON object per line (structured)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload: dict[str, Any] = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
            }
            skip = {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "taskName",
            }
            for k, v in record.__dict__.items():
                if k not in skip and v is not None:
                    payload[k] = v
            sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            self.handleError(record)


def setup_logging(level: str | None = None) -> None:
    """Log level kontrolü; JSON veya human handler ekle."""
    log_level = (level or _env("LUMOS_SOCIAL_LOG_LEVEL", "INFO")).upper()
    numeric = getattr(logging, log_level, logging.INFO)
    root = logging.getLogger("lumos_social")
    root.setLevel(numeric)
    root.handlers.clear()
    if _is_json_log():
        h = JsonHandler()
    else:
        h = HumanHandler()
    h.setLevel(numeric)
    root.addHandler(h)


def get_logger(name: str) -> logging.Logger:
    """lumos_social.* altında logger döndür."""
    return logging.getLogger(f"lumos_social.{name}")
