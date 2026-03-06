#!/usr/bin/env python3
"""
Minimal quantum test for Lumos: connect to IBM Quantum, run a 1-qubit H + measure circuit.
Verifies Lumos can connect to IBM Quantum and execute a simple circuit.

Usage: python run_quantum_test.py
"""
from __future__ import annotations

import sys

BACKEND_NAME = "ibm_fez"
SHOTS = 256


def main() -> int:
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError as e:
        print("Error: Missing dependencies. Install with:", file=sys.stderr)
        print("  pip install qiskit qiskit-ibm-runtime", file=sys.stderr)
        sys.exit(1)

    try:
        service = QiskitRuntimeService()
        backend = service.backend(BACKEND_NAME)
    except Exception as e:
        print(f"Error: Could not connect or get backend '{BACKEND_NAME}': {e}", file=sys.stderr)
        sys.exit(1)

    # 1-qubit circuit: H then measure
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)

    try:
        transpiled = transpile(qc, backend)
    except Exception as e:
        print(f"Error: Transpile failed: {e}", file=sys.stderr)
        sys.exit(1)

    sampler = SamplerV2(backend=backend)
    try:
        job = sampler.run([transpiled], shots=SHOTS)
    except Exception as e:
        print(f"Error: Run failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Backend: {BACKEND_NAME}")
    print(f"Job ID: {job.job_id()}")

    try:
        result = job.result()
    except Exception as e:
        print(f"Error: Getting result failed: {e}", file=sys.stderr)
        sys.exit(1)

    status = job.status()
    print(f"Status: {status.name if hasattr(status, 'name') else status}")

    # SamplerV2: result[0].data.meas.get_counts()
    counts = None
    if len(result) > 0:
        r0 = result[0]
        if hasattr(r0, "data") and hasattr(r0.data, "meas"):
            meas = r0.data.meas
            if hasattr(meas, "get_counts"):
                counts = meas.get_counts()
    if counts is None:
        print("Error: Could not extract measurement counts from result.", file=sys.stderr)
        sys.exit(1)

    # Normalize to string keys for display, e.g. {'0': 120, '1': 136}
    out = {str(k): int(v) for k, v in counts.items()}
    print(f"Counts: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
