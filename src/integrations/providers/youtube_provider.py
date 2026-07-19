from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from integrations.models import IntegrationRequest, IntegrationResult


YOUTUBE_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
)

YOUTUBE_REQUIRED_ENV = (
    "LUMOS_GOOGLE_OAUTH_CLIENT_ID",
    "LUMOS_GOOGLE_OAUTH_CLIENT_SECRET",
    "LUMOS_GOOGLE_OAUTH_REDIRECT_URI",
)

YOUTUBE_LIVE_CHECK_ENV = "LUMOS_YOUTUBE_ACCESS_TOKEN"


def _configuration_status() -> dict[str, object]:
    configured = {name: bool(os.getenv(name, "").strip()) for name in YOUTUBE_REQUIRED_ENV}
    return {
        "provider_id": "youtube",
        "connected": False,
        "identity_status": "identity_required",
        "oauth_configuration": "configured" if all(configured.values()) else "missing",
        "required_env": list(YOUTUBE_REQUIRED_ENV),
        "configured_env": configured,
        "secret_source": "environment_only",
        "execution_live": False,
    }


def _http_get_json(request: Request, timeout: float = 10.0) -> dict[str, object]:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _verify_youtube_identity() -> dict[str, object]:
    token = os.environ[YOUTUBE_LIVE_CHECK_ENV].strip()
    request = Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    if not payload.get("sub"):
        raise RuntimeError("youtube_connection_check_failed")
    return {"account_id": str(payload.get("sub", "")), "name": str(payload.get("name", ""))}


def run_youtube_action(request: IntegrationRequest) -> IntegrationResult:
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
        if not os.getenv(YOUTUBE_LIVE_CHECK_ENV, "").strip():
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "awaiting_credentials", "required_env": [YOUTUBE_LIVE_CHECK_ENV]},
                "youtube_provider_not_configured",
            )
        try:
            identity = _verify_youtube_identity()
        except Exception:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "verification_failed"},
                "youtube_connection_check_failed",
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
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "scopes": list(YOUTUBE_OAUTH_SCOPES),
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
            "youtube_publish_connector_not_live",
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_youtube_action")


def register_youtube_provider(register) -> None:
    register("youtube", "connection_status", run_youtube_action)
    register("youtube", "authorization_contract", run_youtube_action)
    register("youtube", "publish", run_youtube_action)
    register("youtube", "verify_connection", run_youtube_action)
