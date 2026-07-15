from __future__ import annotations

import os

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


def run_vk_action(request: IntegrationRequest) -> IntegrationResult:
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
