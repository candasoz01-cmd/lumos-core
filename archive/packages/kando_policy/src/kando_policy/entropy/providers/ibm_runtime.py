"""IBM Quantum runtime ile entropy (hazırsa çalışır, yoksa graceful fail)."""
from __future__ import annotations


class IBMRuntimeProvider:
    """IBM Quantum runtime bağlantısı hazırsa gerçek backend kullanır; yoksa graceful fail."""

    def get_entropy(self, n: int) -> bytes:
        try:
            return self._get_entropy_ibm(n)
        except Exception:
            # Graceful fallback: IBM runtime yoksa veya hata varsa
            import os
            return os.urandom(n)

    def _get_entropy_ibm(self, n: int) -> bytes:
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
        except ImportError:
            import os
            return os.urandom(n)
        # Servis yapılandırılmamışsa veya bağlantı yoksa os.urandom
        try:
            service = QiskitRuntimeService()
            backend = service.least_busy(simulator=False, operational=True)
        except Exception:
            import os
            return os.urandom(n)
        from qiskit import QuantumCircuit, transpile

        out: list[int] = []
        for _ in range(n):
            qc = QuantumCircuit(8, 8)
            qc.h(range(8))
            qc.measure(range(8), range(8))
            compiled = transpile(qc, backend)
            job = backend.run(compiled, shots=1)
            counts = job.result().get_counts()
            bits = next(iter(counts.keys())) if counts else "0" * 8
            if len(bits) < 8:
                bits = bits.zfill(8)
            out.append(int(bits[:8], 2))
        return bytes(out)
