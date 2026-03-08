"""Minimal Qiskit demo: 1 qubit, H gate, measure, run on AerSimulator."""

import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# Print the version of Qiskit we're using
print("Qiskit", qiskit.__version__)


# Return True if the version of Qiskit is 1.0 or greater
def qiskit_1_or_greater() -> bool:
    parts = qiskit.__version__.split(".")[:2]
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor) >= (1, 0)
    except (ValueError, IndexError):
        return False


print("Qiskit >= 1.0:", qiskit_1_or_greater())

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
