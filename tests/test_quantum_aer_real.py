"""Real (unmocked) Qiskit Aer smoke tests.

Skipped automatically when the optional quantum stack is not installed
(``pip install -r requirements-quantum.txt``). Local simulator only: no network,
no credentials, no cloud provider.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("qiskit")
pytest.importorskip("qiskit_aer")

from integrations.models import IntegrationRequest  # noqa: E402
from integrations.quantum_aer_connect import qiskit_aer_import_status, run_aer_smoke  # noqa: E402
from integrations.registry import register_default_integrations  # noqa: E402


@pytest.fixture
def tmp_lumos_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / ".lumos"
    base.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    return base


def test_real_aer_import_status_ready():
    status = qiskit_aer_import_status()
    assert status["qiskit_available"] is True
    assert status["qiskit_aer_available"] is True
    assert status["ready"] is True


def test_real_aer_smoke_runs_one_qubit_circuit():
    smoke = run_aer_smoke()
    assert smoke["smoke_ok"] is True
    assert smoke["qubits"] == 1
    assert sum(smoke["counts"].values()) == smoke["shots"]


def test_real_aer_hadamard_distribution_is_balanced():
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator

    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)
    shots = 2000
    counts = AerSimulator().run(circuit, shots=shots).result().get_counts()
    assert sum(counts.values()) == shots
    # 5 sigma for a fair coin at 2000 shots is ~112; keep it loose to avoid flakes.
    assert abs(counts.get("0", 0) - shots / 2) < 250


def test_real_aer_connect_requires_approval(tmp_lumos_base: Path):
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="quantum",
            action="connect",
            payload={"provider_id": "qiskit_aer_sim"},
        ),
    )
    assert result.ok is False
    assert result.error == "approval_required"


def test_real_aer_connect_with_approval_is_local_and_non_autonomous(tmp_lumos_base: Path):
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="quantum",
            action="connect",
            payload={"provider_id": "qiskit_aer_sim", "approved": True},
        ),
    )
    assert result.ok is True
    assert result.data["connection_status"] == "connected"
    assert result.data["smoke"]["smoke_ok"] is True
    assert result.data["autonomous_connect"] is False
