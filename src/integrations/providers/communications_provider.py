from __future__ import annotations

from integrations.models import IntegrationRequest, IntegrationResult


COMMUNICATION_CATALOG = (
    {"provider_id": "telegram", "category": "messaging", "regions": ["global"]},
    {"provider_id": "whatsapp", "category": "messaging", "regions": ["global"]},
    {"provider_id": "signal", "category": "messaging", "regions": ["global"]},
    {"provider_id": "line", "category": "messaging", "regions": ["JP", "TW", "TH"]},
    {"provider_id": "kakao_talk", "category": "messaging", "regions": ["KR"]},
    {"provider_id": "viber", "category": "messaging", "regions": ["EE", "ME", "SEA"]},
    {"provider_id": "tiktok", "category": "social", "regions": ["global"]},
    {"provider_id": "facebook", "category": "social", "regions": ["global"]},
    {"provider_id": "instagram", "category": "social", "regions": ["global"]},
    {"provider_id": "x", "category": "social", "regions": ["global"]},
    {"provider_id": "linkedin", "category": "social", "regions": ["global"]},
    {"provider_id": "threads", "category": "social", "regions": ["global"]},
    {"provider_id": "gmail", "category": "mail", "regions": ["global"]},
    {"provider_id": "outlook", "category": "mail", "regions": ["global"]},
    {"provider_id": "hotmail", "category": "mail", "regions": ["global"]},
    {"provider_id": "yahoo_mail", "category": "mail", "regions": ["global", "JP"]},
    {"provider_id": "icloud_mail", "category": "mail", "regions": ["global"]},
    {"provider_id": "proton_mail", "category": "mail", "regions": ["global"]},
    {"provider_id": "gmx", "category": "mail", "regions": ["DE", "AT", "CH"]},
    {"provider_id": "zoho_mail", "category": "mail", "regions": ["global", "IN"]},
)

CATALOG_BY_ID = {item["provider_id"]: item for item in COMMUNICATION_CATALOG}
SUPPORTED_ACTIONS = ("list_catalog", "connection_status", "start_connect")


def _provider_id(request: IntegrationRequest) -> str:
    return str(request.payload.get("provider_id", "")).strip().lower()


def run_communications_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action not in SUPPORTED_ACTIONS:
        return IntegrationResult(False, request.provider, request.action, {}, "unsupported_communications_action")

    if action == "list_catalog":
        category = str(request.payload.get("category", "")).strip().lower()
        providers = [
            dict(item)
            for item in COMMUNICATION_CATALOG
            if not category or item["category"] == category
        ]
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                "count": len(providers),
                "providers": providers,
                "autonomous_connect": False,
                "credentials_in_payload": False,
            },
        )

    provider_id = _provider_id(request)
    provider = CATALOG_BY_ID.get(provider_id)
    if provider is None:
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {"provider_id": provider_id},
            "communications_provider_unknown",
        )

    status = {
        **provider,
        "status": "awaiting_credentials",
        "autonomous_connect": False,
    }
    if action == "connection_status":
        return IntegrationResult(True, request.provider, request.action, status)

    if not request.requires_approval:
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {**status, "requires_approval": True},
            "approval_required",
        )

    return IntegrationResult(
        False,
        request.provider,
        request.action,
        status,
        "communications_provider_not_configured",
    )


def register_communications_provider(register) -> None:
    for action in SUPPORTED_ACTIONS:
        register("communications", action, run_communications_action)
