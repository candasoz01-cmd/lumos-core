from __future__ import annotations

from integrations.models import IntegrationRequest, IntegrationResult
from integrations.quantum_aer_connect import (
    is_qiskit_aer_provider,
    normalize_aer_provider_id,
    qiskit_aer_import_status,
    run_aer_smoke,
)
from integrations.quantum_cloud_connect import (
    QuantumCloudConfigurationError,
    configuration_error_data,
    connect_quantum_cloud,
    is_quantum_cloud_provider,
)
from integrations.quantum_registry import get_quantum_provider, list_quantum_providers
from integrations.quantum_usage_tracker import (
    record_quantum_usage,
    recommend_usage_mode,
)

# Quantum Layer — güvenlik ilkeleri:
# - Otonom bulut taraması veya bağlantı yok.
# - connect / discover (harici) her zaman yüksek risk; owner onayı olmadan yürütme yok.
# - list_catalog yalnızca yerel metadata döner; canlı API çağrısı yok.

SUPPORTED_QUANTUM_ACTIONS = (
    "list_catalog",
    "discover",
    "classify",
    "connect",
    "usage_recommendation",
)
HIGH_RISK_ACTIONS = ("discover", "connect")


def _connect_user_approved(request: IntegrationRequest) -> bool:
    if request.requires_approval:
        return True
    payload = request.payload
    if payload.get("approved") is True:
        return True
    if payload.get("user_approved") is True:
        return True
    return False


def _usage_fields() -> dict:
    rec = recommend_usage_mode()
    return {
        "recommended_mode": rec["recommended_mode"],
        "usage_recommendation": rec,
    }


def _handle_qiskit_aer_connect(request: IntegrationRequest) -> IntegrationResult:
    provider_id = normalize_aer_provider_id(
        str(request.payload.get("provider_id", "qiskit_aer")),
    )
    entry = get_quantum_provider(provider_id)
    if entry is None:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={"provider_id": provider_id},
            error="quantum_provider_unknown",
        )

    import_status = qiskit_aer_import_status()
    usage_extra = _usage_fields()

    if not import_status["ready"]:
        record_quantum_usage("connect", provider_id=provider_id)
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "provider_id": provider_id,
                "reason": "qiskit_aer_optional_deps_missing",
                "install_hint": import_status["install_hint"],
                "import_status": import_status,
                "autonomous_connect": False,
                **usage_extra,
            },
            error="not_configured",
        )

    try:
        smoke = run_aer_smoke()
    except ImportError:
        record_quantum_usage("connect", provider_id=provider_id)
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "provider_id": provider_id,
                "install_hint": import_status["install_hint"],
                "import_status": import_status,
                "autonomous_connect": False,
                **usage_extra,
            },
            error="not_configured",
        )

    record_quantum_usage("connect", provider_id=provider_id)
    usage_extra = _usage_fields()
    return IntegrationResult(
        ok=True,
        provider=request.provider,
        action=request.action,
        data={
            "provider_id": provider_id,
            "connection_status": "connected",
            "smoke": smoke,
            "import_status": import_status,
            "autonomous_connect": False,
            "approval_tier": entry.approval_tier,
            **usage_extra,
        },
    )


def _handle_quantum_cloud_connect(
    request: IntegrationRequest,
    provider_id: str,
) -> IntegrationResult:
    entry = get_quantum_provider(provider_id)
    if entry is None:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={"provider_id": provider_id},
            error="quantum_provider_unknown",
        )

    try:
        connection = connect_quantum_cloud(provider_id)
    except QuantumCloudConfigurationError as exc:
        record_quantum_usage(request.action, provider_id=provider_id)
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={**configuration_error_data(exc), **_usage_fields()},
            error="quantum_provider_not_configured",
        )
    except Exception as exc:  # Provider SDK/auth/network errors are intentionally sanitized.
        record_quantum_usage(request.action, provider_id=provider_id)
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "provider_id": provider_id,
                "reason": "provider_api_unavailable",
                "exception_type": type(exc).__name__,
                "read_only": True,
                "job_submission": False,
                "autonomous_connect": False,
                **_usage_fields(),
            },
            error="quantum_provider_unavailable",
        )

    record_quantum_usage(request.action, provider_id=provider_id)
    return IntegrationResult(
        ok=True,
        provider=request.provider,
        action=request.action,
        data={
            **connection,
            "approval_tier": entry.approval_tier,
            "autonomous_connect": False,
            **_usage_fields(),
        },
    )


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
        record_quantum_usage("list_catalog")
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "providers": list_quantum_providers(),
                "count": len(list_quantum_providers()),
                "autonomous_connect": False,
                **_usage_fields(),
            },
        )

    if action == "usage_recommendation":
        rec = recommend_usage_mode()
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data=rec,
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

    if action in HIGH_RISK_ACTIONS and not _connect_user_approved(request):
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "risk_level": "high",
                "requires_approval": True,
                "approval_hint": "Set payload approved=True or user_approved=True",
            },
            error="approval_required",
        )

    provider_id_raw = request.payload.get("provider_id", "")
    provider_id = provider_id_raw if isinstance(provider_id_raw, str) else ""

    if action == "connect" and is_qiskit_aer_provider(provider_id):
        return _handle_qiskit_aer_connect(request)

    if action in ("connect", "discover") and is_quantum_cloud_provider(provider_id):
        return _handle_quantum_cloud_connect(request, provider_id)

    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data={
            "provider_id": provider_id,
            "reason": "quantum_external_adapter_not_configured",
            "autonomous_connect": False,
            **_usage_fields(),
        },
        error="quantum_provider_not_configured",
    )


def register_quantum_provider(register) -> None:
    for action in SUPPORTED_QUANTUM_ACTIONS:
        register("quantum", action, run_quantum_action)
