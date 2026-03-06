"""Guard all persistence: require user consent before any disk/memory/log write."""

from __future__ import annotations

from lumos_core.security.consent import has_user_consent


def require_consent() -> None:
    """Raise if user has not granted consent. Call before any write."""
    if not has_user_consent():
        raise RuntimeError("Persistence blocked: user consent not granted")
