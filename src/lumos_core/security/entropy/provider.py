"""Entropy provider arayüzü."""
from __future__ import annotations

from typing import Protocol


class EntropyProvider(Protocol):
    """Kriptografik entropy sağlayan provider arayüzü."""

    def get_entropy(self, n: int) -> bytes:
        """n bayt rastgele (kriptografik) veri döner."""
        ...
