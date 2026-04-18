"""
Kriptografik entropy: Qiskit ölçümü ile rastgele bayt.
Qiskit yoksa veya hata durumunda os.urandom kullanılır.
"""
from __future__ import annotations

import os


def get_random_bytes(n: int) -> bytes:
    """n bayt rastgele veri. Önce Qiskit ile dene, yoksa os.urandom."""
    if n <= 0:
        return b""
    try:
        return _qiskit_random_bytes(n)
    except Exception:
        return os.urandom(n)


def _qiskit_random_bytes(n: int) -> bytes:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    out = []
    sim = AerSimulator()
    # Her bayt için 8 qubit: H uygula, ölç; bit dizisini bayta çevir
    for _ in range(n):
        qc = QuantumCircuit(8, 8)
        qc.h(range(8))
        qc.measure(range(8), range(8))
        compiled = transpile(qc, sim)
        job = sim.run(compiled, shots=1)
        counts = job.result().get_counts()
        # counts örn. {"01010101": 1}; tek anahtar
        bits = next(iter(counts.keys())) if counts else "0" * 8
        if len(bits) < 8:
            bits = bits.zfill(8)
        out.append(int(bits[:8], 2))
    return bytes(out)
