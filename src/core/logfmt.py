"""Structured log line helper (event=key …)."""

from __future__ import annotations

from typing import Any


def logfmt(event: str, **kwargs: Any) -> str:
    parts = [f"event={event}"]
    for k in sorted(kwargs.keys()):
        parts.append(f"{k}={kwargs[k]}")
    return " | ".join(parts)
