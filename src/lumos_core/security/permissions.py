from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import time

@dataclass
class PermissionGrant:
    name: str
    purpose: str
    acquired_at: float
    ttl_seconds: Optional[int] = None

    def is_active(self, now: Optional[float] = None) -> bool:
        now = now or time.time()
        if self.ttl_seconds is None:
            return True
        return (now - self.acquired_at) <= self.ttl_seconds

@dataclass
class PermissionManager:
    enabled: bool = True
    grants: Dict[str, PermissionGrant] = field(default_factory=dict)
    audit: List[str] = field(default_factory=list)

    def _log(self, msg: str) -> None:
        self.audit.append(msg)

    def cleanup(self) -> None:
        now = time.time()
        expired = [k for k, g in self.grants.items() if not g.is_active(now)]
        for k in expired:
            self._log(f"RELEASE(auto-expire): {k}")
            self.grants.pop(k, None)

    def request(self, name: str, purpose: str, ttl_seconds: Optional[int] = None) -> None:
        if not self.enabled:
            return
        self.cleanup()
        # Bu katman "OS izni" değil: çekirdek içi kiralama (lease)
        self._log(f"REQUEST: {name} purpose='{purpose}' ttl={ttl_seconds}")

    def acquire(self, name: str, purpose: str, ttl_seconds: Optional[int] = None) -> None:
        if not self.enabled:
            return
        self.cleanup()
        self.grants[name] = PermissionGrant(
            name=name,
            purpose=purpose,
            acquired_at=time.time(),
            ttl_seconds=ttl_seconds
        )
        self._log(f"ACQUIRE: {name} ttl={ttl_seconds}")

    def release(self, name: str) -> None:
        if not self.enabled:
            return
        self.cleanup()
        if name in self.grants:
            self.grants.pop(name, None)
            self._log(f"RELEASE: {name}")

    def is_granted(self, name: str) -> bool:
        self.cleanup()
        g = self.grants.get(name)
        return bool(g and g.is_active())

    def snapshot(self) -> dict:
        self.cleanup()
        active = {}
        now = time.time()
        for k, g in self.grants.items():
            remaining = None
            if g.ttl_seconds is not None:
                remaining = max(0, int(g.ttl_seconds - (now - g.acquired_at)))
            active[k] = {
                "purpose": g.purpose,
                "ttl_seconds": g.ttl_seconds,
                "remaining_seconds": remaining
            }
        return {
            "active": active,
            "audit_tail": self.audit[-10:]
        }
