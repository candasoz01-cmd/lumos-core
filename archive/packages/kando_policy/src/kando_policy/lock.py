from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LockState:
    unlocked: bool = False
    _root_key: Optional[bytes] = field(default=None, repr=False)

    def unlock(self, rk: bytes) -> None:
        self._root_key = rk
        self.unlocked = True

    def lock(self) -> None:
        self._root_key = None
        self.unlocked = False
