"""Runtime permission leases for offline flows (no-op when enabled)."""


class PermissionManager:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def acquire(self, name: str, purpose: str = "", ttl_seconds: int = 0) -> None:
        if not self.enabled:
            return
        return None
