#!/usr/bin/env python3
"""
Minimal quantum test for Lumos: connect to IBM Quantum and run a 1-qubit H + measure circuit.
Run from lumos-quantum: python run_quantum_test.py
"""

import sys


def main() -> int:
    try:
        from qiskit import QuantumCircuit
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError:
        print("Error: Missing dependencies. Install with:", file=sys.stderr)
        print("  pip install qiskit qiskit-ibm-runtime", file=sys.stderr)
        sys.exit(1)

    backend_name = "ibm_fez"
    shots = 256

    try:
        service = QiskitRuntimeService()
    except Exception as e:
        print(f"Error: Could not connect to IBM Quantum: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        backend = service.backend(backend_name)
    except Exception as e:
        print(f"Error: Backend '{backend_name}' not available: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Backend: {backend_name}")

    # 1-qubit circuit: H then measure
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)

    try:
        pm = generate_preset_pass_manager(
            target=backend.target,
            optimization_level=1,
        )
        isa_circuit = pm.run(qc)
    except Exception as e:
        print(f"Error: Transpilation failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        sampler = SamplerV2(mode=backend)
        job = sampler.run([isa_circuit], shots=shots)
    except Exception as e:
        print(f"Error: Job submission failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Job ID: {job.job_id()}")

    try:
        result = job.result()
    except Exception as e:
        print(f"Error: Failed to get result: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        status = job.status()
        status_str = getattr(status, "name", None) or str(status)
    except Exception:
        status_str = "unknown"
    print(f"Status: {status_str}")

    pub_result = result[0]
    counts = pub_result.join_data().get_counts()
    counts_out = {str(k): int(v) for k, v in counts.items()}
    # Sort by bit string for readable, consistent output (e.g. {'0': 120, '1': 136})
    counts_out = dict(sorted(counts_out.items()))
    print(f"Counts: {counts_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
