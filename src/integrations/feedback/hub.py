from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapters import FeedbackEventError, LarkWebhookAdapter, SlackWebhookAdapter
from .config import FeedbackHubConfig
from .models import FeedbackIngestResult
from .store import InMemoryFeedbackStore


class FeedbackHub:
    """Inbound-only feedback normalizer. It intentionally has no polling path."""

    def __init__(
        self,
        config: FeedbackHubConfig,
        store: InMemoryFeedbackStore | None = None,
    ) -> None:
        self.config = config
        self.store = store or InMemoryFeedbackStore()
        self._lark = LarkWebhookAdapter()

    def connection_status(self, provider: str) -> dict[str, object]:
        provider_id = provider.strip().lower()
        if provider_id == "slack":
            return self.config.slack_status()
        if provider_id == "lark":
            return {
                "provider": "lark",
                "status": "webhook_ready",
                "delivery_mode": "inbound_webhook",
                "polling_enabled": False,
            }
        return {
            "provider": provider_id,
            "status": "unsupported_provider",
            "delivery_mode": "inbound_webhook",
            "polling_enabled": False,
        }

    def ingest_webhook(
        self,
        provider: str,
        payload: Mapping[str, Any],
    ) -> FeedbackIngestResult:
        provider_id = provider.strip().lower()
        if provider_id == "slack":
            if not self.config.slack_configured:
                return FeedbackIngestResult(
                    accepted=False,
                    status="awaiting_configuration",
                    error="feedback_hub_awaiting_configuration",
                )
            adapter = SlackWebhookAdapter(self.config.slack_allowed_channel_ids)
        elif provider_id == "lark":
            adapter = self._lark
        else:
            return FeedbackIngestResult(
                accepted=False,
                status="unsupported_provider",
                error="feedback_provider_unsupported",
            )

        try:
            record = adapter.to_record(payload)
        except FeedbackEventError as exc:
            return FeedbackIngestResult(
                accepted=False,
                status="rejected",
                error=exc.code,
            )

        added = self.store.add(record)
        return FeedbackIngestResult(
            accepted=True,
            status="accepted" if added else "duplicate",
            duplicate=not added,
            record=record,
        )
