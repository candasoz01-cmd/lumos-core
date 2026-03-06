"""User consent gate. No persistence until consent is granted."""

from __future__ import annotations


def has_user_consent() -> bool:
    """Return True only if user has granted persistence consent.
    Initial behavior: always False.
    Future: check ~/.lumos/consent.json.
    """
    return False
