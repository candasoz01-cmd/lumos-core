from __future__ import annotations

from typing import Any

from integrations.models import IntegrationRequest, IntegrationResult


CHINA_INTEGRATIONS: tuple[dict[str, Any], ...] = (
    {
        "provider_id": "wecom",
        "name": "WeCom / WeChat Work",
        "sync_scopes": ("contacts", "messages", "calendar"),
    },
    {
        "provider_id": "dingtalk",
        "name": "DingTalk",
        "sync_scopes": ("contacts", "messages", "calendar", "docs"),
    },
    {
        "provider_id": "feishu",
        "name": "Feishu",
        "sync_scopes": ("contacts", "messages", "calendar", "docs"),
    },
    {
        "provider_id": "alipay_mini_program",
        "name": "Alipay Mini Program",
        "sync_scopes": ("identity", "mini_program"),
    },
)


def _catalog() -> list[dict[str, Any]]:
    return [
        {
            **entry,
            "sync_scopes": list(entry["sync_scopes"]),
            "status": "awaiting_credentials",
            "autonomous_sync": False,
        }
        for entry in CHINA_INTEGRATIONS
    ]


def _find_provider(provider_id: str) -> dict[str, Any] | None:
    normalized = provider_id.strip().lower()
    return next(
        (entry for entry in CHINA_INTEGRATIONS if entry["provider_id"] == normalized),
        None,
    )


def run_china_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action == "list_catalog":
        providers = _catalog()
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "region": "CN",
                "providers": providers,
                "count": len(providers),
                "autonomous_sync": False,
                "payments_in_scope": False,
            },
        )

    provider_id = request.payload.get("provider_id", "")
    if not isinstance(provider_id, str) or not provider_id.strip():
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="provider_id_required",
        )
    entry = _find_provider(provider_id)
    if entry is None:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={"provider_id": provider_id.strip().lower()},
            error="china_provider_unknown",
        )

    if action == "sync_status":
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "provider_id": entry["provider_id"],
                "status": "awaiting_credentials",
                "sync_scopes": list(entry["sync_scopes"]),
                "autonomous_sync": False,
            },
        )

    if action == "start_sync":
        if not request.requires_approval:
            return IntegrationResult(
                ok=False,
                provider=request.provider,
                action=request.action,
                data={
                    "provider_id": entry["provider_id"],
                    "requires_approval": True,
                    "autonomous_sync": False,
                },
                error="approval_required",
            )
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "provider_id": entry["provider_id"],
                "status": "awaiting_credentials",
                "sync_scopes": list(entry["sync_scopes"]),
                "autonomous_sync": False,
            },
            error="china_provider_not_configured",
        )

    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data={"provider_id": entry["provider_id"]},
        error="unsupported_china_action",
    )


def register_china_provider(register) -> None:
    for action in ("list_catalog", "sync_status", "start_sync"):
        register("china", action, run_china_action)
