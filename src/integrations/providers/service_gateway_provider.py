from __future__ import annotations

from typing import Any

from integrations.models import IntegrationRequest, IntegrationResult


SERVICE_FAMILIES: tuple[dict[str, Any], ...] = (
    {"id": "ai", "path": "/v1/chat", "capabilities": ("chat", "tools", "multimodal")},
    {"id": "security", "path": "/v1/security/check", "capabilities": ("risk_check", "policy_check")},
    {"id": "identity", "path": "/v1/verify", "capabilities": ("identity_verification",)},
    {"id": "tools", "path": "/v1/tools", "capabilities": ("translate", "summarize", "search", "video")},
    {"id": "integrations", "path": "/v1/integrations/route", "capabilities": ("messaging", "social", "meeting", "work_tool", "device")},
    {"id": "regional", "path": "/v1/regional/route", "capabilities": ("provider_selection", "regional_policy")},
    {"id": "public_services", "path": "/v1/public-services/route", "capabilities": ("identity", "health", "education", "tax", "municipality", "documents")},
)

FAMILY_BY_ID = {family["id"]: family for family in SERVICE_FAMILIES}
TRUST_STAGES = (
    "request_validation",
    "trust_snapshot",
    "policy_decision",
    "confirmation_gate",
    "provider_route",
    "execute_or_deny",
    "redacted_audit",
)


def _public_family(family: dict[str, Any]) -> dict[str, Any]:
    return {**family, "capabilities": list(family["capabilities"])}


def run_service_gateway_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()

    if action == "describe_contract":
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                "name": "Lumos API",
                "contract_version": "lumos.service_gateway.v1",
                "status": "public_foundation",
                "production_transport": False,
                "families": [_public_family(family) for family in SERVICE_FAMILIES],
                "trust_stages": list(TRUST_STAGES),
                "external_effects_require_approval": True,
                "provider_credentials_embedded": False,
            },
        )

    if action == "plan_route":
        family_id = str(request.payload.get("family", "")).strip().lower()
        family = FAMILY_BY_ID.get(family_id)
        if family is None:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"family": family_id, "available_families": sorted(FAMILY_BY_ID)},
                "service_family_unknown",
            )

        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                "family": _public_family(family),
                "route_status": "plan_only",
                "execution_permitted": False,
                "requires_approval": True,
                "provider_selection": "not_executed",
                "trust_stages": list(TRUST_STAGES),
            },
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_service_gateway_action")


def register_service_gateway_provider(register) -> None:
    register("service_gateway", "describe_contract", run_service_gateway_action)
    register("service_gateway", "plan_route", run_service_gateway_action)
