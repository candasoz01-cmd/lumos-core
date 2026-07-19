from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from integrations.models import IntegrationRequest, IntegrationResult


WECHAT_OAUTH_SCOPES = (
    "moments.read",
    "moments.publish",
)

WECHAT_REQUIRED_ENV = (
    "LUMOS_WECHAT_OFFICIAL_ACCOUNT_APP_ID",
    "LUMOS_WECHAT_OFFICIAL_ACCOUNT_APP_SECRET",
    "LUMOS_WECHAT_OFFICIAL_ACCOUNT_REDIRECT_URI",
)

WECHAT_LIVE_CHECK_ENV = (
    "LUMOS_WECHAT_OFFICIAL_ACCOUNT_APP_ID",
    "LUMOS_WECHAT_OFFICIAL_ACCOUNT_APP_SECRET",
)


def _configuration_status() -> dict[str, object]:
    configured = {name: bool(os.getenv(name, "").strip()) for name in WECHAT_REQUIRED_ENV}
    return {
        "provider_id": "wechat",
        "connected": False,
        "identity_status": "identity_required",
        "oauth_configuration": "configured" if all(configured.values()) else "missing",
        "required_env": list(WECHAT_REQUIRED_ENV),
        "configured_env": configured,
        "secret_source": "environment_only",
        "execution_live": False,
    }


def _http_get_json(request: Request, timeout: float = 10.0) -> dict[str, object]:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _verify_wechat_credentials() -> dict[str, object]:
    app_id = os.environ["LUMOS_WECHAT_OFFICIAL_ACCOUNT_APP_ID"].strip()
    app_secret = os.environ["LUMOS_WECHAT_OFFICIAL_ACCOUNT_APP_SECRET"].strip()
    query = urlencode({"grant_type": "client_credential", "appid": app_id, "secret": app_secret})
    request = Request(
        f"https://api.weixin.qq.com/cgi-bin/token?{query}",
        headers={"Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("access_token"):
        raise RuntimeError("wechat_connection_check_failed")
    return {"app_id": app_id, "token_type": "official_account_app_credential"}


def run_wechat_action(request: IntegrationRequest) -> IntegrationResult:
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
        missing = [name for name in WECHAT_LIVE_CHECK_ENV if not os.getenv(name, "").strip()]
        if missing:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "awaiting_credentials", "required_env": missing},
                "wechat_provider_not_configured",
            )
        try:
            identity = _verify_wechat_credentials()
        except Exception:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "verification_failed"},
                "wechat_connection_check_failed",
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
                "scopes": list(WECHAT_OAUTH_SCOPES),
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
            "wechat_publish_connector_not_live",
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_wechat_action")


def register_wechat_provider(register) -> None:
    register("wechat", "connection_status", run_wechat_action)
    register("wechat", "authorization_contract", run_wechat_action)
    register("wechat", "publish", run_wechat_action)
    register("wechat", "verify_connection", run_wechat_action)
