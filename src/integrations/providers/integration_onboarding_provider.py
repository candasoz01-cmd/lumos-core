from __future__ import annotations

from typing import Any

from integrations.models import IntegrationRequest, IntegrationResult
from integrations.providers.global_catalog_provider import CATALOG_BY_ID, GLOBAL_INTEGRATION_CATALOG


TRUSTED_DISCOVERY_SOURCES = frozenset(
    {
        "oauth_session",
        "os_account",
        "installed_app",
        "browser_extension",
        "bluetooth_scan",
        "local_network_discovery",
        "user_selected",
    },
)

FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "card",
        "card_number",
        "cookie",
        "credit_card",
        "password",
        "secret",
        "token",
    },
)

LOCAL_CONNECTION_KINDS = frozenset(
    {
        "android_extension",
        "browser_extension",
        "chromium_extension",
        "local_api",
        "local_bridge",
        "local_protocol",
        "mobile_bridge",
        "os_bluetooth_bridge",
        "os_framework",
    },
)


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).strip().lower() in FORBIDDEN_INPUT_KEYS:
                return True
            if _contains_forbidden_key(nested):
                return True
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _cost_route(entry: dict[str, Any]) -> dict[str, object]:
    connection_kind = str(entry["connection_kind"])
    if connection_kind in LOCAL_CONNECTION_KINDS:
        return {
            "priority": 0,
            "path": "local_or_os_first",
            "price_status": "no_connector_purchase_expected",
        }
    if connection_kind in {"api_key", "api_key_oauth", "bot_api", "cloud_api"}:
        return {
            "priority": 1,
            "path": "existing_account_or_free_tier_first",
            "price_status": "live_plan_check_required",
        }
    if connection_kind in {"partner_api", "vendor_sdk", "vendor_cloud_api"}:
        return {
            "priority": 3,
            "path": "official_partner_route_only",
            "price_status": "live_quote_required",
        }
    return {
        "priority": 2,
        "path": "existing_account_oauth_first",
        "price_status": "live_plan_check_required",
    }


def _regional_suggestions(region: str, limit: int = 24) -> list[dict[str, object]]:
    if not region:
        return []
    matches = [
        entry
        for entry in GLOBAL_INTEGRATION_CATALOG
        if region in entry["regions"]
    ]
    suggestions = [
        {
            "provider_id": entry["provider_id"],
            "name": entry["name"],
            "category": entry["category"],
            "reason": "regional_relevance",
            "detected": False,
        }
        for entry in matches[:limit]
    ]
    return suggestions


def _offer_from_signal(signal: object) -> dict[str, object] | None:
    if not isinstance(signal, dict):
        return None
    provider_id = str(signal.get("provider_id", "")).strip().lower()
    source = str(signal.get("source", "")).strip().lower()
    if source not in TRUSTED_DISCOVERY_SOURCES:
        return None
    entry = CATALOG_BY_ID.get(provider_id)
    if entry is None:
        return None

    cost = _cost_route(entry)
    return {
        "offer_id": f"{provider_id}:{source}",
        "provider_id": provider_id,
        "name": entry["name"],
        "category": entry["category"],
        "detected": True,
        "detection_source": source,
        "prompt_tr": f"{entry['name']} hesabınız veya cihazınız tespit edildi. Lumos ile birlikte kullanmaya devam edelim mi?",
        "support_level": entry["support_level"],
        "connection_kind": entry["connection_kind"],
        "cost_recommendation": cost,
        "requires_user_consent": True,
        "payment_authorized": False,
    }


def _build_offer(request: IntegrationRequest) -> IntegrationResult:
    if _contains_forbidden_key(request.payload):
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {},
            "sensitive_input_not_allowed",
        )

    region = str(request.payload.get("region", request.region)).strip().upper()
    signals = request.payload.get("signals", [])
    if not isinstance(signals, list):
        return IntegrationResult(False, request.provider, request.action, {}, "discovery_signals_invalid")

    offers = [offer for signal in signals if (offer := _offer_from_signal(signal)) is not None]
    offers.sort(key=lambda item: (int(item["cost_recommendation"]["priority"]), str(item["name"])))
    return IntegrationResult(
        True,
        request.provider,
        request.action,
        {
            "region": region,
            "offers": offers,
            "regional_suggestions": _regional_suggestions(region),
            "detection_claim": "signal_backed_only",
            "pricing_rule": "live_check_then_lowest_total_cost",
            "automatic_purchase": False,
            "card_required_by_lumos": False,
        },
    )


def _accept_offer(request: IntegrationRequest) -> IntegrationResult:
    if not request.requires_approval:
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {"requires_approval": True},
            "approval_required",
        )
    provider_id = str(request.payload.get("provider_id", "")).strip().lower()
    entry = CATALOG_BY_ID.get(provider_id)
    if entry is None:
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {"provider_id": provider_id},
            "global_provider_unknown",
        )
    local = entry["connection_kind"] in LOCAL_CONNECTION_KINDS
    return IntegrationResult(
        True,
        request.provider,
        request.action,
        {
            "provider_id": provider_id,
            "consent_status": "recorded",
            "connection_status": "local_pairing_pending" if local else "provider_authorization_pending",
            "next_step": "local_pairing" if local else "official_provider_authorization",
            "payment_authorized": False,
            "automatic_purchase": False,
        },
    )


def run_integration_onboarding_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action == "build_offer":
        return _build_offer(request)
    if action == "accept_offer":
        return _accept_offer(request)
    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_onboarding_action")


def register_integration_onboarding_provider(register) -> None:
    register("integration_onboarding", "build_offer", run_integration_onboarding_action)
    register("integration_onboarding", "accept_offer", run_integration_onboarding_action)
