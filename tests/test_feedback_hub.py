import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.feedback import FeedbackHub, FeedbackHubConfig
from integrations.feedback.config import SLACK_ALLOWED_CHANNEL_IDS_ENV
from integrations.feedback.store import InMemoryFeedbackStore
from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


SLACK_CHANNEL_ID = "C0123456789"


def slack_payload(
    *,
    channel_id: str = SLACK_CHANNEL_ID,
    channel_name: str = "geri-bildirim-havuzu",
    message_id: str = "1784399846.315089",
) -> dict:
    return {
        "team_id": "T0123456789",
        "channel_name": channel_name,
        "event": {
            "type": "message",
            "channel": channel_id,
            "client_msg_id": message_id,
            "event_ts": "1784399846.315089",
            "text": "Arama sonucunu daha anlaşılır gösterin.",
            "user": "U0BCMM1LFKQ",
        },
    }


def lark_payload(message_id: str = "om_123") -> dict:
    return {
        "tenant_key": "tenant-1",
        "chat_name": "feedback",
        "header": {"event_id": "event-1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_123"}},
            "message": {
                "chat_id": "oc_123",
                "message_id": message_id,
                "create_time": "1784399846315",
                "content": '{"text":"Mobil görünüm daha sade olabilir."}',
            },
        },
    }


def configured_hub() -> FeedbackHub:
    return FeedbackHub(
        FeedbackHubConfig(slack_allowed_channel_ids=frozenset({SLACK_CHANNEL_ID})),
    )


def test_config_reads_comma_separated_slack_channel_ids(monkeypatch):
    monkeypatch.setenv(
        SLACK_ALLOWED_CHANNEL_IDS_ENV,
        "C0123456789, G0123456789, C0123456789",
    )
    config = FeedbackHubConfig.from_env()
    assert config.slack_allowed_channel_ids == {"C0123456789", "G0123456789"}


def test_missing_slack_config_returns_awaiting_configuration(monkeypatch):
    monkeypatch.delenv(SLACK_ALLOWED_CHANNEL_IDS_ENV, raising=False)
    status = FeedbackHubConfig.from_env().slack_status()
    assert status["status"] == "awaiting_configuration"
    assert status["missing_configuration"] == [SLACK_ALLOWED_CHANNEL_IDS_ENV]
    assert status["polling_enabled"] is False


def test_invalid_slack_channel_id_fails_configuration_closed():
    config = FeedbackHubConfig(slack_allowed_channel_ids=frozenset({"feedback-name"}))
    status = config.slack_status()
    assert status["status"] == "awaiting_configuration"
    assert status["invalid_configuration"] == ["feedback-name"]


def test_configured_slack_status_is_inbound_webhook_only():
    status = configured_hub().connection_status("slack")
    assert status["status"] == "configured"
    assert status["delivery_mode"] == "inbound_webhook"
    assert status["polling_enabled"] is False


def test_feedback_hub_exposes_no_polling_method():
    hub = configured_hub()
    assert not hasattr(hub, "poll")
    assert not hasattr(hub, "poll_events")


def test_slack_webhook_builds_provider_neutral_record():
    result = configured_hub().ingest_webhook("slack", slack_payload())
    assert result.accepted is True
    assert result.record is not None
    assert result.record.source_provider == "slack"
    assert result.record.source_channel_id == SLACK_CHANNEL_ID
    assert result.record.status == "new"


def test_slack_channel_id_is_required_even_when_name_exists():
    payload = slack_payload()
    payload["event"].pop("channel")
    result = configured_hub().ingest_webhook("slack", payload)
    assert result.accepted is False
    assert result.error == "slack_channel_id_required"


def test_slack_channel_name_does_not_authorize_wrong_id():
    payload = slack_payload(channel_id="C9999999999", channel_name="geri-bildirim-havuzu")
    result = configured_hub().ingest_webhook("slack", payload)
    assert result.accepted is False
    assert result.error == "slack_channel_not_allowed"


def test_slack_allowed_id_remains_authorized_when_name_changes():
    result = configured_hub().ingest_webhook(
        "slack",
        slack_payload(channel_name="renamed-channel"),
    )
    assert result.accepted is True
    assert result.record is not None
    assert result.record.source_channel == "renamed-channel"


def test_slack_ingest_does_not_start_without_configuration():
    hub = FeedbackHub(FeedbackHubConfig())
    result = hub.ingest_webhook("slack", slack_payload())
    assert result.accepted is False
    assert result.status == "awaiting_configuration"
    assert result.error == "feedback_hub_awaiting_configuration"


def test_slack_non_message_event_is_rejected():
    payload = slack_payload()
    payload["event"]["type"] = "reaction_added"
    result = configured_hub().ingest_webhook("slack", payload)
    assert result.error == "slack_message_event_required"


def test_lark_webhook_builds_same_record_contract():
    result = configured_hub().ingest_webhook("lark", lark_payload())
    assert result.accepted is True
    assert result.record is not None
    assert result.record.source_provider == "lark"
    assert result.record.source_channel_id == "oc_123"
    assert result.record.author_display == "ou_123"


def test_lark_requires_chat_id():
    payload = lark_payload()
    payload["event"]["message"].pop("chat_id")
    result = configured_hub().ingest_webhook("lark", payload)
    assert result.accepted is False
    assert result.error == "lark_chat_id_required"


def test_lark_plain_text_content_is_supported():
    payload = lark_payload()
    payload["event"]["message"]["content"] = "Plain feedback"
    result = configured_hub().ingest_webhook("lark", payload)
    assert result.record is not None
    assert result.record.original_text == "Plain feedback"


def test_feedback_id_is_stable_for_same_source_event():
    first = configured_hub().ingest_webhook("slack", slack_payload())
    second = configured_hub().ingest_webhook("slack", slack_payload())
    assert first.record is not None and second.record is not None
    assert first.record.feedback_id == second.record.feedback_id


def test_store_marks_repeated_source_event_as_duplicate():
    hub = FeedbackHub(
        FeedbackHubConfig(slack_allowed_channel_ids=frozenset({SLACK_CHANNEL_ID})),
        store=InMemoryFeedbackStore(),
    )
    first = hub.ingest_webhook("slack", slack_payload())
    second = hub.ingest_webhook("slack", slack_payload())
    assert first.status == "accepted"
    assert second.status == "duplicate"
    assert second.duplicate is True
    assert len(hub.store.records()) == 1


def test_same_message_id_from_different_providers_is_not_duplicate():
    hub = configured_hub()
    slack = hub.ingest_webhook("slack", slack_payload(message_id="same-id"))
    lark = hub.ingest_webhook("lark", lark_payload(message_id="same-id"))
    assert slack.duplicate is False
    assert lark.duplicate is False


def test_unsupported_provider_is_rejected():
    result = configured_hub().ingest_webhook("unknown", {})
    assert result.accepted is False
    assert result.status == "unsupported_provider"


def test_registry_reports_slack_awaiting_configuration(monkeypatch):
    monkeypatch.delenv(SLACK_ALLOWED_CHANNEL_IDS_ENV, raising=False)
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="feedback",
            action="connection_status",
            payload={"provider_id": "slack"},
        ),
    )
    assert result.ok is True
    assert result.data["status"] == "awaiting_configuration"


def test_registry_ingests_configured_slack_webhook(monkeypatch):
    monkeypatch.setenv(SLACK_ALLOWED_CHANNEL_IDS_ENV, SLACK_CHANNEL_ID)
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="feedback",
            action="ingest_webhook",
            payload={"provider_id": "slack", "event": slack_payload()},
        ),
    )
    assert result.ok is True
    assert result.data["record"]["source_channel_id"] == SLACK_CHANNEL_ID
    assert result.data["polling_enabled"] is False
