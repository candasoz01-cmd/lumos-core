"""Qiskit Aer simülatör ile 1-bit/byte üretip bytes'a çeviren provider (deneysel)."""
from __future__ import annotations


def _check_qiskit() -> None:
    try:
        import qiskit  # noqa: F401
        from qiskit_aer import AerSimulator  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "Qiskit entropy provider için qiskit ve qiskit-aer kurulu olmalı: "
            "pip install qiskit qiskit-aer (veya pip install 'lumos-quantum[qiskit]')"
        ) from e


class QiskitAerProvider:
    """Aer simülatörde ölçüm ile bayt üreten deneysel provider."""

    def __init__(self) -> None:
        _check_qiskit()

    def get_entropy(self, n: int) -> bytes:
        if n <= 0:
            return b""
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator

        out: list[int] = []
        sim = AerSimulator()
        for _ in range(n):
            qc = QuantumCircuit(8, 8)
            qc.h(range(8))
            qc.measure(range(8), range(8))
            compiled = transpile(qc, sim)
            job = sim.run(compiled, shots=1)
            counts = job.result().get_counts()
            bits = next(iter(counts.keys())) if counts else "0" * 8
            if len(bits) < 8:
                bits = bits.zfill(8)
            out.append(int(bits[:8], 2))
        return bytes(out)
