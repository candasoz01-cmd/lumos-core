from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

QuantumProviderType = Literal["cloud", "framework", "simulator", "research"]
QuantumApprovalTier = Literal["auto-doc", "needs-owner", "blocked"]
QuantumProviderStatus = Literal["planned", "stub", "none"]


@dataclass(frozen=True)
class QuantumProviderEntry:
    provider_id: str
    display_name: str
    provider_type: QuantumProviderType
    auth_model: str
    cost_risk: str
    egress_risk: str
    approval_tier: QuantumApprovalTier
    status: QuantumProviderStatus
    demo_safe_note: str
    connect_priority: int | None = None  # 1 = ilk yol arkadaşı; 2 = Aer sonrası bulut


# connect_priority: 1 = ilk yol arkadaşı (Qiskit/Aer pilot); 2 = sonraki dal (IBM cloud).
# Öncelik otomatik bağlantı demek değildir — tüm connect yolları onay kapısından geçer.
# Kaynak: docs/analysis/lumos-quantum-provider-catalog.md
QUANTUM_PROVIDERS: tuple[QuantumProviderEntry, ...] = (
    QuantumProviderEntry(
        provider_id="ibm_quantum",
        display_name="IBM Quantum",
        provider_type="cloud",
        auth_model="IBM Cloud API key / QiskitRuntimeService token",
        cost_risk="high",
        egress_risk="medium",
        approval_tier="needs-owner",
        status="stub",
        demo_safe_note="OSS metadata only; first cloud branch after local Aer — not production connect",
        connect_priority=2,
    ),
    QuantumProviderEntry(
        provider_id="azure_quantum",
        display_name="Azure Quantum",
        provider_type="cloud",
        auth_model="Azure AD + workspace resource",
        cost_risk="high",
        egress_risk="medium",
        approval_tier="needs-owner",
        status="planned",
        demo_safe_note="Catalog only in public OSS",
    ),
    QuantumProviderEntry(
        provider_id="amazon_braket",
        display_name="Amazon Braket",
        provider_type="cloud",
        auth_model="AWS IAM + Braket role",
        cost_risk="high",
        egress_risk="medium",
        approval_tier="needs-owner",
        status="planned",
        demo_safe_note="Catalog only in public OSS",
    ),
    QuantumProviderEntry(
        provider_id="google_quantum_ai",
        display_name="Google Quantum AI",
        provider_type="cloud",
        auth_model="Google Cloud IAM + Quantum Engine API",
        cost_risk="high",
        egress_risk="medium",
        approval_tier="needs-owner",
        status="planned",
        demo_safe_note="Catalog only in public OSS",
    ),
    QuantumProviderEntry(
        provider_id="qiskit",
        display_name="Qiskit",
        provider_type="framework",
        auth_model="Local pip; cloud via IBM token when using Runtime",
        cost_risk="low_local_high_runtime",
        egress_risk="low_local_medium_cloud",
        approval_tier="needs-owner",
        status="stub",
        demo_safe_note="First companion framework; local connect spike needs owner approval",
        connect_priority=1,
    ),
    QuantumProviderEntry(
        provider_id="cirq",
        display_name="Cirq",
        provider_type="framework",
        auth_model="Local pip; GCP auth for Google Quantum",
        cost_risk="low_local_high_cloud",
        egress_risk="low_medium",
        approval_tier="needs-owner",
        status="planned",
        demo_safe_note="Catalog only in public OSS",
    ),
    QuantumProviderEntry(
        provider_id="pennylane",
        display_name="PennyLane",
        provider_type="framework",
        auth_model="Local pip; per-plugin cloud auth",
        cost_risk="low_to_medium",
        egress_risk="plugin_dependent",
        approval_tier="needs-owner",
        status="planned",
        demo_safe_note="Catalog only in public OSS",
    ),
    QuantumProviderEntry(
        provider_id="qiskit_aer",
        display_name="Qiskit Aer",
        provider_type="simulator",
        auth_model="none_local",
        cost_risk="low",
        egress_risk="low",
        approval_tier="needs-owner",
        status="stub",
        demo_safe_note="First companion simulator; local Aer spike — connect needs owner approval",
        connect_priority=1,
    ),
    QuantumProviderEntry(
        provider_id="local_sim",
        display_name="Local CPU/GPU simulators",
        provider_type="simulator",
        auth_model="none",
        cost_risk="low",
        egress_risk="low",
        approval_tier="auto-doc",
        status="planned",
        demo_safe_note="Generic local simulation note",
    ),
    QuantumProviderEntry(
        provider_id="cloud_managed_sim",
        display_name="Cloud managed simulators",
        provider_type="simulator",
        auth_model="cloud_provider_auth",
        cost_risk="medium_to_high",
        egress_risk="medium",
        approval_tier="needs-owner",
        status="planned",
        demo_safe_note="Must be labeled sim-not-QPU in production",
    ),
    QuantumProviderEntry(
        provider_id="nist_pqc_watch",
        display_name="NIST PQC / standards watch",
        provider_type="research",
        auth_model="none_public_docs",
        cost_risk="none",
        egress_risk="none",
        approval_tier="auto-doc",
        status="stub",
        demo_safe_note="ADR-013 readiness: watch only, no PQC implementation claim",
    ),
    QuantumProviderEntry(
        provider_id="quantum_benchmark_index",
        display_name="Quantum benchmark / paper index",
        provider_type="research",
        auth_model="none_curated_links",
        cost_risk="none",
        egress_risk="low_user_click",
        approval_tier="auto-doc",
        status="planned",
        demo_safe_note="Static reference list target in OSS",
    ),
    QuantumProviderEntry(
        provider_id="quantum_readiness_inventory",
        display_name="Quantum Readiness inventory",
        provider_type="research",
        auth_model="local_scan",
        cost_risk="none",
        egress_risk="none",
        approval_tier="auto-doc",
        status="stub",
        demo_safe_note="scan_quantum_readiness — not a compute connect path",
    ),
)


def list_quantum_providers() -> list[dict[str, str]]:
    return [_entry_to_dict(entry) for entry in QUANTUM_PROVIDERS]


def get_quantum_provider(provider_id: str) -> QuantumProviderEntry | None:
    normalized = provider_id.strip().lower()
    for entry in QUANTUM_PROVIDERS:
        if entry.provider_id == normalized:
            return entry
    return None


def _entry_to_dict(entry: QuantumProviderEntry) -> dict[str, str]:
    data = {
        "provider_id": entry.provider_id,
        "display_name": entry.display_name,
        "provider_type": entry.provider_type,
        "auth_model": entry.auth_model,
        "cost_risk": entry.cost_risk,
        "egress_risk": entry.egress_risk,
        "approval_tier": entry.approval_tier,
        "status": entry.status,
        "demo_safe_note": entry.demo_safe_note,
    }
    if entry.connect_priority is not None:
        data["connect_priority"] = str(entry.connect_priority)
    return data
