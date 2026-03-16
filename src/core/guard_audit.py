from __future__ import annotations

"""
Lightweight guard audit helpers.

Amaç:
- Core/sandbox write guard kararlarını düşük yan etkili şekilde kaydetmek.
- Filesystem davranışını değiştirmeden, sadece log/audit yüzeyi sağlamak.

Tasarım notları:
- Bilerek logging modülüne ve stdout'a sınırlı kalır; core state'e ek yazma yapmaz.
- Testler, caplog/dummy logger üzerinden bu katmanı doğrulayabilir.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


GuardAction = Literal["write", "patch", "overwrite", "rename", "move", "delete"]

GuardDecision = Literal["allow", "deny"]


@dataclass(frozen=True)
class GuardEvent:
    action: GuardAction
    decision: GuardDecision
    path: Path
    sandbox_mode: bool
    reason: str | None = None
    caller: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "decision": self.decision,
            "path": str(self.path),
            "sandbox_mode": self.sandbox_mode,
            "reason": self.reason or "",
            "caller": self.caller or "",
        }


_LOGGER = logging.getLogger("lumos.guard")


def record_guard_event(event: GuardEvent) -> None:
    """
    Guard kararı için merkezi ve hafif audit entry'si üret.

    Notlar:
    - Diskte yeni core dosyası oluşturmaz; sadece logging'i kullanır.
    - Varsayılan seviye INFO; deny durumlarında WARNING olarak loglanır.
    """
    level = logging.INFO if event.decision == "allow" else logging.WARNING
    _LOGGER.log(
        level,
        "guard_decision action=%s decision=%s path=%s sandbox_mode=%s reason=%s caller=%s",
        event.action,
        event.decision,
        str(event.path),
        event.sandbox_mode,
        (event.reason or ""),
        (event.caller or ""),
    )

