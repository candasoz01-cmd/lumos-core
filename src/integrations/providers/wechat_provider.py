from __future__ import annotations

import os

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


def run_wechat_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action == "connection_status":
        return IntegrationResult(True, request.provider, request.action, _configuration_status())

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
