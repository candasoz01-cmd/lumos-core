from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Protocol
from urllib.request import Request, urlopen
from uuid import UUID

from .meeting_ingress import (
    MeetingEnvironment,
    MeetingIngressError,
    MeetingJoinRequest,
    MeetingSession,
    RetentionKind,
)

RECALL_API_BASE_URL = "https://us-east-1.recall.ai/api/v1"


class JsonTransport(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object] | None,
    ) -> Mapping[str, object]: ...


class UrllibJsonTransport:
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object] | None,
    ) -> Mapping[str, object]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(url, data=body, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=15.0) as response:
                raw = response.read()
        except Exception:
            raise MeetingIngressError("meeting_ingress_request_failed") from None

        if not raw:
            return {}
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MeetingIngressError("meeting_ingress_response_invalid") from exc
        if not isinstance(decoded, dict):
            raise MeetingIngressError("meeting_ingress_response_invalid")
        return decoded


class RecallMeetingIngress:
    """Fail-closed Recall implementation of the meeting control plane."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        transport: JsonTransport | None = None,
    ) -> None:
        configured_key = api_key if api_key is not None else os.environ.get("LUMOS_RECALL_API_KEY", "")
        self._api_key = configured_key.strip()
        self._transport = transport or UrllibJsonTransport()

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise MeetingIngressError("recall_api_key_required")
        return {
            "Authorization": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def build_create_payload(request: MeetingJoinRequest) -> dict[str, object]:
        """Build a secret-free payload for validation and dry-run inspection."""

        request.validate()
        assert request.retention is not None
        retention: dict[str, object] | None
        if request.retention.kind is RetentionKind.MEDIA_ZERO:
            retention = None
        else:
            retention = {"type": "timed", "hours": request.retention.hours}
        return {
            "meeting_url": request.meeting_url,
            "bot_name": request.bot_name,
            "recording_config": {
                "retention": retention,
            },
            "output_media": {
                "camera": {
                    "kind": "webpage",
                    "config": {"url": request.output_media_url},
                },
            },
            "metadata": {"session_id": request.opaque_session_id},
        }

    def join(self, request: MeetingJoinRequest) -> MeetingSession:
        payload = self.build_create_payload(request)
        if request.environment is MeetingEnvironment.EXTERNAL:
            raise MeetingIngressError("external_meeting_compliance_blocked")
        headers = self._headers()
        response = self._transport.request(
            method="POST",
            url=f"{RECALL_API_BASE_URL}/bot/",
            headers=headers,
            payload=payload,
        )
        bot_id = str(response.get("id", "")).strip()
        if not bot_id:
            raise MeetingIngressError("meeting_ingress_response_invalid")
        try:
            bot_id = str(UUID(bot_id))
        except ValueError:
            raise MeetingIngressError("meeting_ingress_response_invalid") from None
        return MeetingSession(provider="recall", bot_id=bot_id, state="joining")

    def leave(self, session: MeetingSession) -> MeetingSession:
        return self._leave_call(session, state="left")

    def kill(self, session: MeetingSession) -> MeetingSession:
        return self._leave_call(session, state="killed")

    def _leave_call(self, session: MeetingSession, *, state: str) -> MeetingSession:
        if session.provider != "recall" or not session.bot_id.strip():
            raise MeetingIngressError("meeting_session_invalid")
        try:
            bot_id = str(UUID(session.bot_id))
        except ValueError:
            raise MeetingIngressError("meeting_session_invalid") from None
        headers = self._headers()
        self._transport.request(
            method="POST",
            url=f"{RECALL_API_BASE_URL}/bot/{bot_id}/leave_call/",
            headers=headers,
            payload=None,
        )
        return MeetingSession(provider="recall", bot_id=session.bot_id, state=state)
