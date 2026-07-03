"""
Panel runtime LockState snapshot — same-process injection with fail-closed default.

Panel ``panel_tasks_server`` typically runs in a separate process from the CLI
runtime. When no snapshot is available, gates must stay locked (ADR-010/ADR-012).

Same-process callers (tests, co-hosted integrations) may inject a LockState-like
object (``.unlocked`` attribute) or register a provider callback.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

_injected_lock: Any | None = None
_provider: Callable[[], Any | None] | None = None


def inject_panel_runtime_lock(lock_state: Any | None) -> None:
    """Direct same-process injection (tests or co-hosted panel)."""
    global _injected_lock
    _injected_lock = lock_state


def set_panel_runtime_lock_provider(provider: Callable[[], Any | None] | None) -> None:
    """Register a callback returning LockState-like object or None."""
    global _provider
    _provider = provider


def clear_panel_runtime_lock_hooks() -> None:
    """Reset injection hooks (tests)."""
    global _injected_lock, _provider
    _injected_lock = None
    _provider = None


def resolve_panel_runtime_lock() -> Any | None:
    """
    Resolve runtime lock snapshot for panel gates.

    Returns LockState-like object when available; ``None`` → fail-closed.
    """
    if _injected_lock is not None:
        return _injected_lock
    if _provider is not None:
        try:
            return _provider()
        except Exception:
            return None
    return None
