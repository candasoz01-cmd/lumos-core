from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from integrations.models import IntegrationRequest, IntegrationResult


WEIBO_OAUTH_SCOPES = (
    "statuses.read",
    "statuses.publish",
)

WEIBO_REQUIRED_ENV = (
    "LUMOS_WEIBO_OAUTH_CLIENT_ID",
    "LUMOS_WEIBO_OAUTH_CLIENT_SECRET",
    "LUMOS_WEIBO_OAUTH_REDIRECT_URI",
)

WEIBO_LIVE_CHECK_ENV = "LUMOS_WEIBO_ACCESS_TOKEN"


def _configuration_status() -> dict[str, object]:
    configured = {name: bool(os.getenv(name, "").strip()) for name in WEIBO_REQUIRED_ENV}
    return {
        "provider_id": "weibo",
        "connected": False,
        "identity_status": "identity_required",
        "oauth_configuration": "configured" if all(configured.values()) else "missing",
        "required_env": list(WEIBO_REQUIRED_ENV),
        "configured_env": configured,
        "secret_source": "environment_only",
        "execution_live": False,
    }


def _http_get_json(request: Request, timeout: float = 10.0) -> dict[str, object]:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _verify_weibo_identity() -> dict[str, object]:
    token = os.environ[WEIBO_LIVE_CHECK_ENV].strip()
    query = urlencode({"access_token": token})
    request = Request(
        f"https://api.weibo.com/2/account/get_uid.json?{query}",
        headers={"Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("uid"):
        raise RuntimeError("weibo_connection_check_failed")
    return {"account_id": str(payload.get("uid", ""))}


def run_weibo_action(request: IntegrationRequest) -> IntegrationResult:
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
        if not os.getenv(WEIBO_LIVE_CHECK_ENV, "").strip():
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "awaiting_credentials", "required_env": [WEIBO_LIVE_CHECK_ENV]},
                "weibo_provider_not_configured",
            )
        try:
            identity = _verify_weibo_identity()
        except Exception:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "verification_failed"},
                "weibo_connection_check_failed",
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
                "scopes": list(WEIBO_OAUTH_SCOPES),
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
            "weibo_publish_connector_not_live",
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_weibo_action")


def register_weibo_provider(register) -> None:
    register("weibo", "connection_status", run_weibo_action)
    register("weibo", "authorization_contract", run_weibo_action)
    register("weibo", "publish", run_weibo_action)
    register("weibo", "verify_connection", run_weibo_action)
