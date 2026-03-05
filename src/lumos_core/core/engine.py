"""
Core engine: lock/presence actions.
CLI/TUI call engine methods only; state is read from CoreState.
Engine does not hold state; snapshot/params passed as arguments.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


class CoreEngine:
    """Injected lock and presence actions. No state attributes; all inputs via method args."""

    def __init__(
        self,
        do_lock: Callable[[], None],
        device_lock_cli: Callable[[bool], None],
        unlock_with_passphrase: Callable[[str], tuple[bool, str]],
        presence_lock_module: Any,
    ) -> None:
        self.do_lock = do_lock
        self.device_lock_cli = device_lock_cli
        self.unlock_with_passphrase = unlock_with_passphrase
        self.pl = presence_lock_module

    def recover_presence(
        self,
        base_dir: Path,
        log_event: Callable[[str], None],
        lock_cb: Callable[[], None] | None = None,
        is_already_locked: Callable[[], bool] | None = None,
    ) -> None:
        """Boot recovery: if config enabled but thread not running, start and log presence_autostarted."""
        try:
            self.pl.recover_if_needed(
                base_dir, log_event, lock_cb=lock_cb, is_already_locked=is_already_locked
            )
        except Exception as e:
            try:
                from lumos_core.core.logfmt import logfmt
                log_event(logfmt("presence_autostart_failed", err=str(e)))
            except Exception:
                pass

