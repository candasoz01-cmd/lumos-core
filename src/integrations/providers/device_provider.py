from __future__ import annotations

from integrations.models import IntegrationRequest, IntegrationResult

# Cihaz / kilit — güvenlik ilkeleri:
# - Reverse-engineering veya belgesiz protokolle doğrudan kilit kontrolü yok.
# - Yalnızca resmî API, belgeli yerel protokol veya kullanıcının açık izni
#   tanımlı akışlar (onay kaydı vb.) hedeflenir.
# - lock / unlock her zaman yüksek risk; requires_approval olmadan yürütme yok.
# - Cihaz kimliği eksikse ayrı hata; vendor adapter yoksa device_provider_not_configured.

SUPPORTED_DEVICE_ACTIONS = ("list_devices", "lock_status", "lock", "unlock")
HIGH_RISK_ACTIONS = ("lock", "unlock")


def _vendor_adapter_ready(vendor: object) -> bool:
    """Resmî vendor SDK / OpenAPI bağlandığında True olacak; şimdilik her zaman False."""
    if not isinstance(vendor, str) or not vendor.strip():
        return False
    return False


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
    # lock / unlock: yüksek risk; yürütme yalnızca açık onay bayrağı ile.
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
    vendor = request.payload.get("vendor")
    device_id_str = device_id.strip() if isinstance(device_id, str) else ""
    if not _vendor_adapter_ready(vendor):
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "device_id": device_id_str,
                "device_type": request.payload.get("device_type", ""),
                "vendor": vendor if isinstance(vendor, str) else "",
                "reason": "vendor_adapter_not_configured",
            },
            error="device_provider_not_configured",
        )
    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data={
            "device_id": device_id_str,
            "device_type": request.payload.get("device_type", ""),
            "vendor": vendor if isinstance(vendor, str) else "",
        },
        error="device_provider_not_configured",
    )


def register_device_provider(register) -> None:
    for action in SUPPORTED_DEVICE_ACTIONS:
        register("device", action, run_device_action)
