"""OS CSPRNG (os.urandom) tabanlı entropy provider."""
from __future__ import annotations

import os


class OSUrandomProvider:
    """os.urandom kullanan varsayılan entropy sağlayıcı."""

    def get_entropy(self, n: int) -> bytes:
        if n <= 0:
            return b""
        return os.urandom(n)
