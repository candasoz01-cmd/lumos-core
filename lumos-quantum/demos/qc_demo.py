"""Minimal Qiskit demo: 1 qubit, H gate, measure, run on AerSimulator."""

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

import qiskit

print("Qiskit", qiskit.__version__)


def is_qiskit_1_0_or_greater() -> bool:
    try:
        from packaging.version import Version
        return Version(qiskit.__version__) >= Version("1.0")
    except ImportError:
        parts = qiskit.__version__.split(".")[:2]
        major = int(parts[0]) if parts else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor) >= (1, 0)


qc = QuantumCircuit(1, 1)
qc.h(0)
qc.measure(0, 0)

print(qc.draw())

sim = AerSimulator()
compiled = transpile(qc, sim)
job = sim.run(compiled, shots=1000)

result = job.result()
counts = result.get_counts()
print(counts)
