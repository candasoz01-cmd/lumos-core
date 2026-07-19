from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from .config import is_slack_channel_id
from .models import FeedbackRecord


class FeedbackEventError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _required_text(value: object, error: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise FeedbackEventError(error)
    return text


def _feedback_id(provider: str, workspace: str, channel_id: str, message_id: str) -> str:
    raw = "\x1f".join((provider, workspace, channel_id, message_id)).encode()
    return f"fb_{sha256(raw).hexdigest()[:20]}"


def _summary(text: str) -> str:
    return " ".join(text.split())[:240]


class SlackWebhookAdapter:
    def __init__(self, allowed_channel_ids: frozenset[str]) -> None:
        self._allowed_channel_ids = allowed_channel_ids

    def to_record(self, payload: Mapping[str, Any]) -> FeedbackRecord:
        event_value = payload.get("event", payload)
        if not isinstance(event_value, Mapping):
            raise FeedbackEventError("slack_event_required")
        event = event_value
        if event.get("type") != "message" or event.get("subtype"):
            raise FeedbackEventError("slack_message_event_required")

        channel_id = _required_text(event.get("channel"), "slack_channel_id_required")
        if not is_slack_channel_id(channel_id):
            raise FeedbackEventError("slack_channel_id_invalid")
        if channel_id not in self._allowed_channel_ids:
            raise FeedbackEventError("slack_channel_not_allowed")

        workspace = _required_text(payload.get("team_id"), "slack_workspace_id_required")
        message_id = _required_text(
            event.get("client_msg_id") or event.get("ts"),
            "slack_message_id_required",
        )
        original_text = _required_text(event.get("text"), "feedback_text_required")
        channel_name = str(event.get("channel_name") or payload.get("channel_name") or "").strip()
        author = str(event.get("user_name") or event.get("user") or "unknown").strip()
        received_at = str(event.get("event_ts") or event.get("ts") or "").strip()
        source_url = str(event.get("permalink") or payload.get("permalink") or "").strip()

        return FeedbackRecord(
            feedback_id=_feedback_id("slack", workspace, channel_id, message_id),
            source_provider="slack",
            source_workspace=workspace,
            source_channel_id=channel_id,
            source_channel=channel_name,
            source_message_id=message_id,
            source_url=source_url,
            author_display=author,
            received_at=received_at,
            feedback_type="unspecified",
            priority="untriaged",
            status="new",
            summary=_summary(original_text),
            original_text=original_text,
        )


class LarkWebhookAdapter:
    def to_record(self, payload: Mapping[str, Any]) -> FeedbackRecord:
        event_value = payload.get("event")
        if not isinstance(event_value, Mapping):
            raise FeedbackEventError("lark_event_required")
        message_value = event_value.get("message")
        if not isinstance(message_value, Mapping):
            raise FeedbackEventError("lark_message_event_required")

        chat_id = _required_text(message_value.get("chat_id"), "lark_chat_id_required")
        message_id = _required_text(message_value.get("message_id"), "lark_message_id_required")
        workspace = _required_text(
            payload.get("tenant_key") or payload.get("tenant_id"),
            "lark_workspace_id_required",
        )
        original_text = self._message_text(message_value.get("content"))
        sender = event_value.get("sender")
        sender_id = sender.get("sender_id") if isinstance(sender, Mapping) else None
        author = sender_id.get("open_id") if isinstance(sender_id, Mapping) else ""
        source_url = str(payload.get("message_url") or "").strip()
        received_at = str(message_value.get("create_time") or "").strip()
        channel_name = str(payload.get("chat_name") or "").strip()

        return FeedbackRecord(
            feedback_id=_feedback_id("lark", workspace, chat_id, message_id),
            source_provider="lark",
            source_workspace=workspace,
            source_channel_id=chat_id,
            source_channel=channel_name,
            source_message_id=message_id,
            source_url=source_url,
            author_display=str(author or "unknown"),
            received_at=received_at,
            feedback_type="unspecified",
            priority="untriaged",
            status="new",
            summary=_summary(original_text),
            original_text=original_text,
        )

    @staticmethod
    def _message_text(content: object) -> str:
        if isinstance(content, Mapping):
            return _required_text(content.get("text"), "feedback_text_required")
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return _required_text(content, "feedback_text_required")
            if isinstance(parsed, Mapping):
                return _required_text(parsed.get("text"), "feedback_text_required")
        raise FeedbackEventError("feedback_text_required")
