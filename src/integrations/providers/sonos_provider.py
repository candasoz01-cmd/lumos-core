from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from integrations.models import IntegrationRequest, IntegrationResult


SONOS_REQUIRED_ENV = ("LUMOS_SONOS_ACCESS_TOKEN",)


def _configuration_status() -> dict[str, object]:
    configured = {name: bool(os.getenv(name, "").strip()) for name in SONOS_REQUIRED_ENV}
    return {
        "provider_id": "sonos",
        "connected": False,
        "identity_status": "identity_required",
        "oauth_configuration": "configured" if all(configured.values()) else "missing",
        "required_env": list(SONOS_REQUIRED_ENV),
        "configured_env": configured,
        "secret_source": "environment_only",
        "execution_live": False,
    }


def _http_get_json(request: Request, timeout: float = 10.0) -> dict[str, object]:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _verify_sonos_identity() -> dict[str, object]:
    token = os.environ["LUMOS_SONOS_ACCESS_TOKEN"].strip()
    request = Request(
        "https://api.ws.sonos.com/control/api/v1/households",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _http_get_json(request)
    households = payload.get("households")
    if not isinstance(households, list) or not households:
        raise RuntimeError("sonos_connection_check_failed")
    return {"household_count": len(households), "household_ids": [str(h.get("id", "")) for h in households]}


def run_sonos_action(request: IntegrationRequest) -> IntegrationResult:
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
        if not os.getenv("LUMOS_SONOS_ACCESS_TOKEN", "").strip():
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "awaiting_credentials", "required_env": list(SONOS_REQUIRED_ENV)},
                "sonos_provider_not_configured",
            )
        try:
            identity = _verify_sonos_identity()
        except Exception:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"status": "verification_failed"},
                "sonos_connection_check_failed",
            )
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {"status": "connected", "identity": identity},
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_sonos_action")


def register_sonos_provider(register) -> None:
    register("sonos", "connection_status", run_sonos_action)
    register("sonos", "verify_connection", run_sonos_action)
