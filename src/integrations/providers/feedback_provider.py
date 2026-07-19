from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from integrations.feedback import FeedbackHub, FeedbackHubConfig
from integrations.models import IntegrationRequest, IntegrationResult


SUPPORTED_ACTIONS = ("connection_status", "ingest_webhook")
_hub: FeedbackHub | None = None
_hub_config: FeedbackHubConfig | None = None


def _default_hub() -> FeedbackHub:
    global _hub, _hub_config
    config = FeedbackHubConfig.from_env()
    if _hub is None or config != _hub_config:
        _hub = FeedbackHub(config)
        _hub_config = config
    return _hub


def run_feedback_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action not in SUPPORTED_ACTIONS:
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {},
            "unsupported_feedback_action",
        )

    provider_id = str(request.payload.get("provider_id", "")).strip().lower()
    hub = _default_hub()
    if action == "connection_status":
        status = hub.connection_status(provider_id)
        return IntegrationResult(
            status["status"] != "unsupported_provider",
            request.provider,
            request.action,
            status,
            "" if status["status"] != "unsupported_provider" else "feedback_provider_unsupported",
        )

    event = request.payload.get("event")
    if not isinstance(event, Mapping):
        return IntegrationResult(
            False,
            request.provider,
            request.action,
            {"provider_id": provider_id},
            "feedback_webhook_event_required",
        )
    result = hub.ingest_webhook(provider_id, event)
    data: dict[str, Any] = {
        "provider_id": provider_id,
        "status": result.status,
        "duplicate": result.duplicate,
        "delivery_mode": "inbound_webhook",
        "polling_enabled": False,
    }
    if result.record is not None:
        data["record"] = result.record.as_dict()
    return IntegrationResult(
        result.accepted,
        request.provider,
        request.action,
        data,
        result.error,
    )


def register_feedback_provider(register) -> None:
    for action in SUPPORTED_ACTIONS:
        register("feedback", action, run_feedback_action)
