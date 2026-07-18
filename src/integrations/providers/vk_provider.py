from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from integrations.models import IntegrationRequest, IntegrationResult


VK_OAUTH_SCOPES = (
    "wall.read",
    "wall.publish",
)

VK_REQUIRED_ENV = (
    "LUMOS_VK_OAUTH_CLIENT_ID",
    "LUMOS_VK_OAUTH_CLIENT_SECRET",
    "LUMOS_VK_OAUTH_REDIRECT_URI",
)

VK_LIVE_CHECK_ENV = "LUMOS_VK_ACCESS_TOKEN"
VK_API_VERSION = "5.199"


def _configuration_status() -> dict[str, object]:
    configured = {name: bool(os.getenv(name, "").strip()) for name in VK_REQUIRED_ENV}
    return {
        "provider_id": "vk",
        "connected": False,
        "identity_status": "identity_required",
        "oauth_configuration": "configured" if all(configured.values()) else "missing",
        "required_env": list(VK_REQUIRED_ENV),
        "configured_env": configured,
        "secret_source": "environment_only",
        "execution_live": False,
    }


def _http_get_json(request: Request, timeout: float = 10.0) -> dict[str, object]:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _verify_vk_identity() -> dict[str, object]:
    token = os.environ[VK_LIVE_CHECK_ENV].strip()
    query = urlencode({"access_token": token, "v": VK_API_VERSION})
    request = Request(
        f"https://api.vk.com/method/users.get?{query}",
        headers={"Accept": "application/json"},
    )
    payload = _http_get_json(request)
    response = payload.get("response")
    user = response[0] if isinstance(response, list) and response else None
    if not isinstance(user, dict) or not user.get("id"):
        raise RuntimeError("vk_connection_check_failed")
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    return {"account_id": str(user.get("id", "")), "name": name}


def run_vk_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action == "connection_status":
        return IntegrationResult(True, request.provider, request.action, _configuration_status())

    if action == "verify_connection":
        if not request.requires_approval:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"requires_approval": True, "execution_started": False},
                "approval_required",
            )
        if not os.getenv(VK_LIVE_CHECK_ENV, "").strip():
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "awaiting_credentials", "required_env": [VK_LIVE_CHECK_ENV]},
                "vk_provider_not_configured",
            )
        try:
            identity = _verify_vk_identity()
        except Exception:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "verification_failed"},
                "vk_connection_check_failed",
            )
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {"status": "connected", "identity": identity},
        )

    if action == "authorization_contract":
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                **_configuration_status(),
                "scopes": list(VK_OAUTH_SCOPES),
                "workflow": ["connect", "draft", "explicit_approval", "publish"],
                "next_step": "configure_oauth_identity",
            },
        )

    if action == "publish":
        if not request.requires_approval:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"requires_approval": True, "execution_started": False},
                "approval_required",
            )
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {
                "approved": True,
                "execution_started": False,
                "identity_status": "identity_required",
            },
            "vk_publish_connector_not_live",
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_vk_action")


def register_vk_provider(register) -> None:
    register("vk", "connection_status", run_vk_action)
    register("vk", "authorization_contract", run_vk_action)
    register("vk", "publish", run_vk_action)
    register("vk", "verify_connection", run_vk_action)
