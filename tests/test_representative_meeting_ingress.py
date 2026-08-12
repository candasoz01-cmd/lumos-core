import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from representative import (
    CLOSED_REHEARSAL_STEPS,
    ClosedRehearsal,
    MeetingEnvironment,
    MeetingIngressError,
    MeetingJoinRequest,
    MeetingSession,
    RecallMeetingIngress,
    RehearsalStep,
    RetentionPolicy,
)


class FakeTransport:
    def __init__(self, response=None):
        self.response = response or {"id": "bot-123"}
        self.calls = []

    def request(self, *, method, url, headers, payload):
        self.calls.append(
            {"method": method, "url": url, "headers": dict(headers), "payload": payload},
        )
        return self.response


_DEFAULT_RETENTION = object()


def join_request(
    *,
    environment=MeetingEnvironment.CLOSED_REHEARSAL,
    retention=_DEFAULT_RETENTION,
):
    if retention is _DEFAULT_RETENTION:
        retention = RetentionPolicy.timed(24)
    return MeetingJoinRequest(
        meeting_url="https://meet.google.com/abc-defg-hij",
        output_media_url="https://representative.example.test/session/token",
        opaque_session_id="rep_20260812_001",
        environment=environment,
        retention=retention,
    )


def test_closed_rehearsal_builds_explicit_24_hour_retention_and_output_media():
    transport = FakeTransport(response={"id": "86fb5e99-2a27-4d4e-897f-bc9dbe353100"})
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)

    session = ingress.join(join_request())

    assert session == MeetingSession(
        provider="recall",
        bot_id="86fb5e99-2a27-4d4e-897f-bc9dbe353100",
        state="joining",
    )
    payload = transport.calls[0]["payload"]
    assert payload["recording_config"]["retention"] == {"type": "timed", "hours": 24}
    assert payload["output_media"]["camera"]["kind"] == "webpage"
    assert payload["metadata"] == {"session_id": "rep_20260812_001"}
    assert "automatic_audio_output" not in payload
    assert "transcription" not in str(payload).lower()
    assert "chat" not in str(payload).lower()


def test_external_meeting_builds_explicit_media_zero_retention():
    transport = FakeTransport()
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)

    payload = ingress.build_create_payload(
        join_request(
            environment=MeetingEnvironment.EXTERNAL,
            retention=RetentionPolicy.media_zero(),
        ),
    )

    assert payload["recording_config"] == {"retention": None}
    assert transport.calls == []


def test_external_meeting_stays_blocked_until_compliance_is_resolved():
    transport = FakeTransport()
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)

    with pytest.raises(MeetingIngressError, match="external_meeting_compliance_blocked"):
        ingress.join(
            join_request(
                environment=MeetingEnvironment.EXTERNAL,
                retention=RetentionPolicy.media_zero(),
            ),
        )

    assert transport.calls == []


@pytest.mark.parametrize(
    ("environment", "retention", "error"),
    [
        (MeetingEnvironment.CLOSED_REHEARSAL, None, "retention_policy_required"),
        (
            MeetingEnvironment.CLOSED_REHEARSAL,
            RetentionPolicy.timed(25),
            "timed_retention_out_of_range",
        ),
        (
            MeetingEnvironment.EXTERNAL,
            RetentionPolicy.timed(1),
            "external_meeting_requires_media_zero_retention",
        ),
    ],
)
def test_unsafe_retention_fails_before_network(environment, retention, error):
    transport = FakeTransport()
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)

    with pytest.raises(MeetingIngressError, match=error):
        ingress.join(join_request(environment=environment, retention=retention))

    assert transport.calls == []


def test_missing_secret_fails_before_network(monkeypatch):
    monkeypatch.delenv("LUMOS_RECALL_API_KEY", raising=False)
    transport = FakeTransport()
    ingress = RecallMeetingIngress(transport=transport)

    with pytest.raises(MeetingIngressError, match="recall_api_key_required"):
        ingress.join(join_request())

    assert transport.calls == []


@pytest.mark.parametrize(
    "meeting_url",
    [
        "http://meet.google.com/abc-defg-hij",
        "https://zoom.us/j/123",
        "https://meet.google.com.evil.test/abc-defg-hij",
    ],
)
def test_only_secure_google_meet_urls_are_accepted(meeting_url):
    transport = FakeTransport()
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)
    request = join_request()
    request = MeetingJoinRequest(
        meeting_url=meeting_url,
        output_media_url=request.output_media_url,
        opaque_session_id=request.opaque_session_id,
        environment=request.environment,
        retention=request.retention,
    )

    with pytest.raises(MeetingIngressError):
        ingress.join(request)

    assert transport.calls == []


def test_secret_is_only_sent_as_authorization_header():
    transport = FakeTransport(response={"id": "86fb5e99-2a27-4d4e-897f-bc9dbe353100"})
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)

    session = ingress.join(join_request())

    call = transport.calls[0]
    assert call["headers"]["Authorization"] == "test-secret"
    assert "test-secret" not in str(call["payload"])
    assert "test-secret" not in repr(session)


def test_invalid_provider_bot_id_is_not_exposed_as_a_session():
    transport = FakeTransport(response={"id": "not-a-uuid"})
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)

    with pytest.raises(MeetingIngressError, match="meeting_ingress_response_invalid"):
        ingress.join(join_request())


def test_kill_switch_uses_irreversible_leave_call_endpoint():
    transport = FakeTransport()
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)
    bot_id = "86fb5e99-2a27-4d4e-897f-bc9dbe353100"

    result = ingress.kill(MeetingSession(provider="recall", bot_id=bot_id, state="in_call"))

    assert result.state == "killed"
    assert transport.calls[0]["method"] == "POST"
    assert transport.calls[0]["url"].endswith(f"/bot/{bot_id}/leave_call/")
    assert transport.calls[0]["payload"] is None


def test_bot_name_requires_explicit_ai_disclosure():
    transport = FakeTransport()
    ingress = RecallMeetingIngress(api_key="test-secret", transport=transport)
    request = join_request()
    request = MeetingJoinRequest(
        meeting_url=request.meeting_url,
        output_media_url=request.output_media_url,
        opaque_session_id=request.opaque_session_id,
        environment=request.environment,
        retention=request.retention,
        bot_name="Lumos Translator",
    )

    with pytest.raises(MeetingIngressError, match="bot_name_must_disclose_ai"):
        ingress.join(request)

    assert transport.calls == []


def test_closed_rehearsal_enforces_all_eight_steps_in_order():
    rehearsal = ClosedRehearsal()

    with pytest.raises(MeetingIngressError, match="closed_rehearsal_step_out_of_order"):
        rehearsal.advance(RehearsalStep.TR_TO_EN_COMPLETED)

    for step in CLOSED_REHEARSAL_STEPS:
        rehearsal = rehearsal.advance(step)

    assert len(rehearsal.completed) == 8
    assert rehearsal.is_complete is True
    assert rehearsal.completed[-2:] == (
        RehearsalStep.KILL_SWITCH_TRIGGERED,
        RehearsalStep.BOT_LEFT,
    )
