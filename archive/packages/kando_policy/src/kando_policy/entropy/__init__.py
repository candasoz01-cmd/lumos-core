"""
Tek giriş noktası: get_provider(name), entropy(n, provider="os").
Provider çalışmazsa fallback os.urandom.
"""
from __future__ import annotations

import os
from security.entropy.provider import EntropyProvider
from security.entropy.providers.os_urandom import OSUrandomProvider

_OS = OSUrandomProvider()


def get_provider(name: str) -> EntropyProvider:
    """İsimle provider döner. Bilinmeyen veya yüklenemeyen için os döner."""
    name = (name or "os").strip().lower()
    if name == "os":
        return _OS
    if name == "qiskit_aer":
        try:
            from security.entropy.providers.qiskit_aer import QiskitAerProvider
            return QiskitAerProvider()
        except Exception:
            return _OS
    if name == "ibm_runtime":
        try:
            from security.entropy.providers.ibm_runtime import IBMRuntimeProvider
            return IBMRuntimeProvider()
        except Exception:
            return _OS
    return _OS


def entropy(n: int, provider: str = "os") -> bytes:
    """n bayt entropy döner. provider çalışmazsa os.urandom kullanılır."""
    if n <= 0:
        return b""
    p = get_provider(provider)
    try:
        return p.get_entropy(n)
    except Exception:
        return _OS.get_entropy(n)


def get_random_bytes(n: int) -> bytes:
    """Geriye uyumluluk: LUMOS_ENTROPY_PROVIDER varsa onu kullanır, yoksa os."""
    prov = os.environ.get("LUMOS_ENTROPY_PROVIDER", "os")
    return entropy(n, provider=prov)


__all__ = ["EntropyProvider", "get_provider", "entropy", "get_random_bytes", "OSUrandomProvider"]
