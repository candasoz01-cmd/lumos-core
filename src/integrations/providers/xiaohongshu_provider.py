from __future__ import annotations

import os

from integrations.models import IntegrationRequest, IntegrationResult


XIAOHONGSHU_OAUTH_SCOPES = (
    "posts.read",
    "posts.publish",
)

XIAOHONGSHU_REQUIRED_ENV = (
    "LUMOS_XIAOHONGSHU_PARTNER_CLIENT_ID",
    "LUMOS_XIAOHONGSHU_PARTNER_CLIENT_SECRET",
    "LUMOS_XIAOHONGSHU_PARTNER_REDIRECT_URI",
)


def _configuration_status() -> dict[str, object]:
    configured = {name: bool(os.getenv(name, "").strip()) for name in XIAOHONGSHU_REQUIRED_ENV}
    return {
        "provider_id": "xiaohongshu",
        "connected": False,
        "identity_status": "identity_required",
        "oauth_configuration": "configured" if all(configured.values()) else "missing",
        "required_env": list(XIAOHONGSHU_REQUIRED_ENV),
        "configured_env": configured,
        "secret_source": "environment_only",
        "execution_live": False,
    }


def run_xiaohongshu_action(request: IntegrationRequest) -> IntegrationResult:
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
                "scopes": list(XIAOHONGSHU_OAUTH_SCOPES),
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
            "xiaohongshu_publish_connector_not_live",
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_xiaohongshu_action")


def register_xiaohongshu_provider(register) -> None:
    register("xiaohongshu", "connection_status", run_xiaohongshu_action)
    register("xiaohongshu", "authorization_contract", run_xiaohongshu_action)
    register("xiaohongshu", "publish", run_xiaohongshu_action)
