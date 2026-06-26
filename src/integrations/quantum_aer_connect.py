"""Qiskit Aer connect spike — optional deps, minimal smoke only."""
from __future__ import annotations

from typing import Any

QUANTUM_INSTALL_HINT = "pip install 'lumos-core[quantum]'  # or: pip install qiskit qiskit-aer"


def normalize_aer_provider_id(provider_id: str) -> str:
    normalized = provider_id.strip().lower()
    if normalized in ("qiskit_aer_sim", "qiskit_aer"):
        return "qiskit_aer"
    return normalized


def is_qiskit_aer_provider(provider_id: str) -> bool:
    return normalize_aer_provider_id(provider_id) == "qiskit_aer"


def qiskit_aer_import_status() -> dict[str, Any]:
    qiskit_ok = False
    aer_ok = False
    try:
        import qiskit  # noqa: F401

        qiskit_ok = True
    except ImportError:
        pass
    try:
        from qiskit_aer import AerSimulator  # noqa: F401

        aer_ok = True
    except ImportError:
        pass
    return {
        "qiskit_available": qiskit_ok,
        "qiskit_aer_available": aer_ok,
        "ready": qiskit_ok and aer_ok,
        "install_hint": QUANTUM_INSTALL_HINT,
    }


def run_aer_smoke() -> dict[str, Any]:
    """Run a minimal 1-qubit Aer circuit; raises ImportError if deps missing."""
    status = qiskit_aer_import_status()
    if not status["ready"]:
        raise ImportError(QUANTUM_INSTALL_HINT)

    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator

    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    sim = AerSimulator()
    job = sim.run(qc, shots=1)
    result = job.result()
    counts = result.get_counts()
    return {
        "smoke_ok": True,
        "qubits": 1,
        "shots": 1,
        "counts": counts,
    }
