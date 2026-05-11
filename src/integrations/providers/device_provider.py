from __future__ import annotations
from integrations.models import IntegrationRequest, IntegrationResult
SUPPORTED_DEVICE_ACTIONS = ("list_devices", "lock_status", "lock", "unlock")
HIGH_RISK_ACTIONS = ("lock", "unlock")
def run_device_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action not in SUPPORTED_DEVICE_ACTIONS:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="unsupported_device_action",
        )
    if action in HIGH_RISK_ACTIONS and not request.requires_approval:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "risk_level": "high",
                "requires_approval": True,
            },
            error="approval_required",
        )
    device_id = request.payload.get("device_id")
    if action != "list_devices" and (not isinstance(device_id, str) or not device_id.strip()):
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="device_id_required",
        )
    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data={
            "device_id": device_id.strip() if isinstance(device_id, str) else "",
            "device_type": request.payload.get("device_type", ""),
            "vendor": request.payload.get("vendor", ""),
        },
        error="device_provider_not_configured",
    )
def register_device_provider(register) -> None:
    for action in SUPPORTED_DEVICE_ACTIONS:
        register("device", action, run_device_action)
