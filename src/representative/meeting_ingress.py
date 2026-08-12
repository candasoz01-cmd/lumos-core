from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from urllib.parse import urlsplit


class MeetingIngressError(RuntimeError):
    """Safe, provider-neutral ingress failure."""


class MeetingEnvironment(str, Enum):
    CLOSED_REHEARSAL = "closed_rehearsal"
    EXTERNAL = "external"


class RetentionKind(str, Enum):
    MEDIA_ZERO = "media_zero"
    TIMED = "timed"


@dataclass(frozen=True)
class RetentionPolicy:
    kind: RetentionKind
    hours: int | None = None

    @classmethod
    def media_zero(cls) -> RetentionPolicy:
        return cls(RetentionKind.MEDIA_ZERO)

    @classmethod
    def timed(cls, hours: int) -> RetentionPolicy:
        return cls(RetentionKind.TIMED, hours=hours)

    def validate_for(self, environment: MeetingEnvironment) -> None:
        if self.kind is RetentionKind.MEDIA_ZERO:
            if self.hours is not None:
                raise MeetingIngressError("retention_policy_invalid")
            if environment is MeetingEnvironment.CLOSED_REHEARSAL:
                raise MeetingIngressError("rehearsal_retention_must_be_timed")
            return

        if self.hours is None or not 1 <= self.hours <= 24:
            raise MeetingIngressError("timed_retention_out_of_range")
        if environment is MeetingEnvironment.EXTERNAL:
            raise MeetingIngressError("external_meeting_requires_media_zero_retention")


_OPAQUE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_AI_DISCLOSURE = re.compile(r"(?:^|\W)AI(?:\W|$)", re.IGNORECASE)


def _validate_https_url(value: str, *, expected_host: str | None = None) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise MeetingIngressError("secure_url_required")
    if expected_host is not None and parsed.hostname.lower() != expected_host:
        raise MeetingIngressError("unsupported_meeting_platform")


@dataclass(frozen=True)
class MeetingJoinRequest:
    meeting_url: str
    output_media_url: str
    opaque_session_id: str
    environment: MeetingEnvironment
    retention: RetentionPolicy | None
    bot_name: str = "Lumos Representative — AI Translator"

    def validate(self) -> None:
        _validate_https_url(self.meeting_url, expected_host="meet.google.com")
        _validate_https_url(self.output_media_url)
        if not _OPAQUE_SESSION_ID.fullmatch(self.opaque_session_id):
            raise MeetingIngressError("opaque_session_id_invalid")
        if self.retention is None:
            raise MeetingIngressError("retention_policy_required")
        self.retention.validate_for(self.environment)
        if self.bot_name != self.bot_name.strip() or not 1 <= len(self.bot_name) <= 100:
            raise MeetingIngressError("bot_name_invalid")
        if not _AI_DISCLOSURE.search(self.bot_name):
            raise MeetingIngressError("bot_name_must_disclose_ai")


@dataclass(frozen=True)
class MeetingSession:
    provider: str
    bot_id: str
    state: str


class MeetingIngress(Protocol):
    """Provider-neutral meeting control plane.

    The media plane is bound to ``output_media_url`` for this first slice;
    audio input/output contracts will be added with the translator runtime.
    """

    def join(self, request: MeetingJoinRequest) -> MeetingSession: ...

    def leave(self, session: MeetingSession) -> MeetingSession: ...

    def kill(self, session: MeetingSession) -> MeetingSession: ...
