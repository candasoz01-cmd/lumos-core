from __future__ import annotations

from integrations.models import IntegrationRequest, IntegrationResult
from integrations.quantum_registry import get_quantum_provider, list_quantum_providers

# Quantum Layer — güvenlik ilkeleri:
# - Otonom bulut taraması veya bağlantı yok.
# - connect / discover (harici) her zaman yüksek risk; requires_approval olmadan yürütme yok.
# - list_catalog yalnızca yerel metadata döner; canlı API çağrısı yok.

SUPPORTED_QUANTUM_ACTIONS = ("list_catalog", "discover", "classify", "connect")
HIGH_RISK_ACTIONS = ("discover", "connect")


def run_quantum_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action not in SUPPORTED_QUANTUM_ACTIONS:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="unsupported_quantum_action",
        )

    if action == "list_catalog":
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "providers": list_quantum_providers(),
                "count": len(list_quantum_providers()),
                "autonomous_connect": False,
            },
        )

    if action == "classify":
        provider_id = request.payload.get("provider_id", "")
        entry = get_quantum_provider(provider_id) if isinstance(provider_id, str) else None
        if entry is None:
            return IntegrationResult(
                ok=False,
                provider=request.provider,
                action=request.action,
                data={"provider_id": provider_id if isinstance(provider_id, str) else ""},
                error="quantum_provider_unknown",
            )
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "provider_id": entry.provider_id,
                "provider_type": entry.provider_type,
                "approval_tier": entry.approval_tier,
                "status": entry.status,
                "cost_risk": entry.cost_risk,
                "egress_risk": entry.egress_risk,
            },
        )

    if action in HIGH_RISK_ACTIONS and not request.requires_approval:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "risk_level": "high",
                "requires_approval": True,
            },
            error="approval_required",
        )

    provider_id = request.payload.get("provider_id", "")
    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data={
            "provider_id": provider_id if isinstance(provider_id, str) else "",
            "reason": "quantum_external_adapter_not_configured",
            "autonomous_connect": False,
        },
        error="quantum_provider_not_configured",
    )


def register_quantum_provider(register) -> None:
    for action in SUPPORTED_QUANTUM_ACTIONS:
        register("quantum", action, run_quantum_action)
