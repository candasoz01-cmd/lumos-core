from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class LockState:
    unlocked: bool = False
    root_key: Optional[bytes] = None

    def lock(self) -> None:
        self.unlocked = False
        self.root_key = None

    def unlock(self, root_key: bytes) -> None:
        self.unlocked = True
        self.root_key = root_key
