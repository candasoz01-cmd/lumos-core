from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
SUPPORTED_ACTIONS = ("list_catalog", "connection_status", "start_connect", "verify_connection")

LIVE_CONNECTION_CONFIG = {
    "whatsapp": {
        "required_env": (
            "LUMOS_WHATSAPP_ACCESS_TOKEN",
            "LUMOS_WHATSAPP_PHONE_NUMBER_ID",
            "LUMOS_META_GRAPH_VERSION",
        ),
        "connection_mode": "meta_cloud_api_readonly_check",
    },
    "telegram": {
        "required_env": ("LUMOS_TELEGRAM_BOT_TOKEN",),
        "connection_mode": "telegram_bot_api_readonly_check",
    },
    "facebook": {
        "required_env": (
            "LUMOS_FACEBOOK_PAGE_ACCESS_TOKEN",
            "LUMOS_META_GRAPH_VERSION",
        ),
        "connection_mode": "meta_graph_api_readonly_check",
    },
    "instagram": {
        "required_env": (
            "LUMOS_INSTAGRAM_ACCESS_TOKEN",
            "LUMOS_META_GRAPH_VERSION",
        ),
        "connection_mode": "meta_graph_api_readonly_check",
    },
    "threads": {
        "required_env": ("LUMOS_THREADS_ACCESS_TOKEN",),
        "connection_mode": "threads_graph_api_readonly_check",
    },
    "x": {
        "required_env": ("LUMOS_X_BEARER_TOKEN",),
        "connection_mode": "x_api_v2_readonly_check",
    },
    "linkedin": {
        "required_env": ("LUMOS_LINKEDIN_ACCESS_TOKEN",),
        "connection_mode": "linkedin_openid_userinfo_check",
    },
    "tiktok": {
        "required_env": ("LUMOS_TIKTOK_ACCESS_TOKEN",),
        "connection_mode": "tiktok_api_v2_readonly_check",
    },
}


def _provider_id(request: IntegrationRequest) -> str:
    return str(request.payload.get("provider_id", "")).strip().lower()


def _connection_status(provider: dict[str, object]) -> dict[str, object]:
    provider_id = str(provider["provider_id"])
    config = LIVE_CONNECTION_CONFIG.get(provider_id)
    if config is None:
        return {
            **provider,
            "status": "catalog_only",
            "autonomous_connect": False,
            "live_check_supported": False,
        }

    required_env = tuple(config["required_env"])
    missing = [name for name in required_env if not os.environ.get(name, "").strip()]
    return {
        **provider,
        "status": "awaiting_credentials" if missing else "configured",
        "autonomous_connect": False,
        "live_check_supported": True,
        "connection_mode": config["connection_mode"],
        "missing_configuration": missing,
    }


def _http_get_json(request: Request, timeout: float = 10.0) -> dict[str, object]:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _verify_whatsapp() -> dict[str, object]:
    token = os.environ["LUMOS_WHATSAPP_ACCESS_TOKEN"].strip()
    phone_number_id = os.environ["LUMOS_WHATSAPP_PHONE_NUMBER_ID"].strip()
    graph_version = os.environ["LUMOS_META_GRAPH_VERSION"].strip()
    query = urlencode({"fields": "id,verified_name,display_phone_number"})
    request = Request(
        f"https://graph.facebook.com/{graph_version}/{phone_number_id}?{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("id"):
        raise RuntimeError("whatsapp_connection_check_failed")
    return {
        "account_id": str(payload.get("id", "")),
        "verified_name": str(payload.get("verified_name", "")),
        "display_phone_number": str(payload.get("display_phone_number", "")),
    }


def _verify_telegram() -> dict[str, object]:
    token = os.environ["LUMOS_TELEGRAM_BOT_TOKEN"].strip()
    request = Request(
        f"https://api.telegram.org/bot{token}/getMe",
        headers={"Accept": "application/json"},
    )
    payload = _http_get_json(request)
    result = payload.get("result") if payload.get("ok") is True else None
    if not isinstance(result, dict):
        raise RuntimeError("telegram_connection_check_failed")
    return {
        "bot_id": str(result.get("id", "")),
        "username": str(result.get("username", "")),
        "display_name": str(result.get("first_name", "")),
    }


def _verify_facebook() -> dict[str, object]:
    token = os.environ["LUMOS_FACEBOOK_PAGE_ACCESS_TOKEN"].strip()
    graph_version = os.environ["LUMOS_META_GRAPH_VERSION"].strip()
    query = urlencode({"fields": "id,name"})
    request = Request(
        f"https://graph.facebook.com/{graph_version}/me?{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("id"):
        raise RuntimeError("facebook_connection_check_failed")
    return {"account_id": str(payload.get("id", "")), "name": str(payload.get("name", ""))}


def _verify_instagram() -> dict[str, object]:
    token = os.environ["LUMOS_INSTAGRAM_ACCESS_TOKEN"].strip()
    graph_version = os.environ["LUMOS_META_GRAPH_VERSION"].strip()
    query = urlencode({"fields": "id,username"})
    request = Request(
        f"https://graph.facebook.com/{graph_version}/me?{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("id"):
        raise RuntimeError("instagram_connection_check_failed")
    return {"account_id": str(payload.get("id", "")), "username": str(payload.get("username", ""))}


def _verify_threads() -> dict[str, object]:
    token = os.environ["LUMOS_THREADS_ACCESS_TOKEN"].strip()
    query = urlencode({"fields": "id,username"})
    request = Request(
        f"https://graph.threads.net/v1.0/me?{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("id"):
        raise RuntimeError("threads_connection_check_failed")
    return {"account_id": str(payload.get("id", "")), "username": str(payload.get("username", ""))}


def _verify_x() -> dict[str, object]:
    token = os.environ["LUMOS_X_BEARER_TOKEN"].strip()
    request = Request(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    data = payload.get("data")
    if not isinstance(data, dict) or not data.get("id"):
        raise RuntimeError("x_connection_check_failed")
    return {"account_id": str(data.get("id", "")), "username": str(data.get("username", ""))}


def _verify_linkedin() -> dict[str, object]:
    token = os.environ["LUMOS_LINKEDIN_ACCESS_TOKEN"].strip()
    request = Request(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("sub"):
        raise RuntimeError("linkedin_connection_check_failed")
    return {"account_id": str(payload.get("sub", "")), "name": str(payload.get("name", ""))}


def _verify_tiktok() -> dict[str, object]:
    token = os.environ["LUMOS_TIKTOK_ACCESS_TOKEN"].strip()
    query = urlencode({"fields": "open_id,display_name"})
    request = Request(
        f"https://open.tiktokapis.com/v2/user/info/?{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    data = payload.get("data") if isinstance(payload, dict) else None
    user = data.get("user") if isinstance(data, dict) else None
    if not isinstance(user, dict) or not user.get("open_id"):
        raise RuntimeError("tiktok_connection_check_failed")
    return {"account_id": str(user.get("open_id", "")), "display_name": str(user.get("display_name", ""))}


def _verify_provider(provider_id: str) -> dict[str, object]:
    if provider_id == "whatsapp":
        return _verify_whatsapp()
    if provider_id == "telegram":
        return _verify_telegram()
    if provider_id == "facebook":
        return _verify_facebook()
    if provider_id == "instagram":
        return _verify_instagram()
    if provider_id == "threads":
        return _verify_threads()
    if provider_id == "x":
        return _verify_x()
    if provider_id == "linkedin":
        return _verify_linkedin()
    if provider_id == "tiktok":
        return _verify_tiktok()
    raise RuntimeError("communications_live_check_not_supported")


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

    status = _connection_status(provider)
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

    if not status["live_check_supported"]:
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            status,
            "communications_live_check_not_supported",
        )

    if status["status"] != "configured":
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            status,
            "communications_provider_not_configured",
        )

    if action == "start_connect":
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {**status, "next_action": "verify_connection"},
        )

    try:
        identity = _verify_provider(provider_id)
    except Exception:
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {**status, "status": "verification_failed"},
            "communications_connection_check_failed",
        )

    return IntegrationResult(
        True,
        request.provider,
        request.action,
        {**status, "status": "connected", "identity": identity},
    )


def register_communications_provider(register) -> None:
    for action in SUPPORTED_ACTIONS:
        register("communications", action, run_communications_action)
