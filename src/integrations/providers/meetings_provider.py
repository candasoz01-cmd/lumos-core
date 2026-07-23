from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from integrations.models import IntegrationRequest, IntegrationResult


MEETING_CATALOG = (
    {"provider_id": "zoom", "regions": ["global"]},
    {"provider_id": "microsoft_teams", "regions": ["global"]},
    {"provider_id": "google_meet", "regions": ["global"]},
    {"provider_id": "webex", "regions": ["global"]},
    {"provider_id": "jitsi", "regions": ["global"]},
    {"provider_id": "tencent_meeting", "regions": ["CN", "APAC"]},
    {"provider_id": "lark_meetings", "regions": ["CN", "APAC", "global"]},
    {"provider_id": "jiomeet", "regions": ["IN"]},
)

CATALOG_BY_ID = {item["provider_id"]: item for item in MEETING_CATALOG}
SUPPORTED_ACTIONS = ("list_catalog", "connection_status", "start_connect", "verify_connection")

LIVE_CONNECTION_CONFIG = {
    "zoom": {
        "required_env": ("LUMOS_ZOOM_ACCESS_TOKEN",),
        "connection_mode": "zoom_api_readonly_check",
    },
    "microsoft_teams": {
        "required_env": ("LUMOS_MICROSOFT_TEAMS_ACCESS_TOKEN",),
        "connection_mode": "microsoft_graph_readonly_check",
    },
    "google_meet": {
        "required_env": ("LUMOS_GOOGLE_MEET_ACCESS_TOKEN",),
        "connection_mode": "google_oauth_userinfo_check",
    },
    "webex": {
        "required_env": ("LUMOS_WEBEX_ACCESS_TOKEN",),
        "connection_mode": "webex_api_readonly_check",
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


def _verify_zoom() -> dict[str, object]:
    token = os.environ["LUMOS_ZOOM_ACCESS_TOKEN"].strip()
    request = Request(
        "https://api.zoom.us/v2/users/me",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("id"):
        raise RuntimeError("zoom_connection_check_failed")
    return {"account_id": str(payload.get("id", "")), "email": str(payload.get("email", ""))}


def _verify_microsoft_teams() -> dict[str, object]:
    token = os.environ["LUMOS_MICROSOFT_TEAMS_ACCESS_TOKEN"].strip()
    request = Request(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("id"):
        raise RuntimeError("microsoft_teams_connection_check_failed")
    return {
        "account_id": str(payload.get("id", "")),
        "display_name": str(payload.get("displayName", "")),
    }


def _verify_google_meet() -> dict[str, object]:
    token = os.environ["LUMOS_GOOGLE_MEET_ACCESS_TOKEN"].strip()
    request = Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("sub"):
        raise RuntimeError("google_meet_connection_check_failed")
    return {
        "account_id": str(payload.get("sub", "")),
        "name": str(payload.get("name", "")),
        "verified_scope": "google_account_identity_only",
    }


def _verify_webex() -> dict[str, object]:
    token = os.environ["LUMOS_WEBEX_ACCESS_TOKEN"].strip()
    request = Request(
        "https://webexapis.com/v1/people/me",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("id"):
        raise RuntimeError("webex_connection_check_failed")
    return {
        "account_id": str(payload.get("id", "")),
        "display_name": str(payload.get("displayName", "")),
    }


def _verify_provider(provider_id: str) -> dict[str, object]:
    if provider_id == "zoom":
        return _verify_zoom()
    if provider_id == "microsoft_teams":
        return _verify_microsoft_teams()
    if provider_id == "google_meet":
        return _verify_google_meet()
    if provider_id == "webex":
        return _verify_webex()
    raise RuntimeError("meetings_live_check_not_supported")


def run_meetings_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action not in SUPPORTED_ACTIONS:
        return IntegrationResult(False, request.provider, request.action, {}, "unsupported_meetings_action")

    if action == "list_catalog":
        providers = [dict(item) for item in MEETING_CATALOG]
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
            "meetings_provider_unknown",
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
            "meetings_live_check_not_supported",
        )

    if status["status"] != "configured":
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            status,
            "meetings_provider_not_configured",
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
            "meetings_connection_check_failed",
        )

    return IntegrationResult(
        True,
        request.provider,
        request.action,
        {**status, "status": "connected", "identity": identity},
    )


def register_meetings_provider(register) -> None:
    for action in SUPPORTED_ACTIONS:
        register("meetings", action, run_meetings_action)
