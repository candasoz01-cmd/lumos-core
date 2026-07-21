from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lumos_board.coordination_gateway import (
    AUDIT_SCHEMA,
    CoordinationError,
    EventKind,
    ReaderConflict,
    ReaderUnauthorized,
    Route,
    SingleReaderGateway,
)


NOW = datetime(2026, 7, 19, 13, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        return self.value


def _audit(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_only_one_reader_can_hold_the_live_lease(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path, clock=Clock())

    first = gateway.claim_reader(reader_id="lumos-primary")

    assert first.token
    assert first.token not in gateway.reader_path.read_text(encoding="utf-8")
    with pytest.raises(ReaderConflict, match="lumos-primary"):
        gateway.claim_reader(reader_id="lumos-secondary")


def test_atomic_reader_claim_has_one_winner(tmp_path: Path) -> None:
    barrier = threading.Barrier(2)
    results: list[str] = []

    def attempt(reader_id: str) -> None:
        barrier.wait()
        try:
            SingleReaderGateway(tmp_path).claim_reader(reader_id=reader_id)
            results.append("accepted")
        except ReaderConflict:
            results.append("conflict")

    threads = [threading.Thread(target=attempt, args=(reader,)) for reader in ("one", "two")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == ["accepted", "conflict"]


def test_stale_reader_can_be_taken_over_and_is_audited(tmp_path: Path) -> None:
    clock = Clock()
    gateway = SingleReaderGateway(tmp_path, clock=clock)
    old = gateway.claim_reader(reader_id="old-reader", ttl_seconds=10)
    clock.value += timedelta(seconds=11)

    new = gateway.claim_reader(reader_id="lumos-primary")

    assert new.reader_id == "lumos-primary"
    with pytest.raises(ReaderUnauthorized):
        gateway.read_user_digest(old.token)
    events = _audit(gateway.audit_path)
    assert "READER_STALE_TAKEOVER" in [event["event"] for event in events]


def test_heartbeat_extends_reader_lease_and_release_revokes_it(tmp_path: Path) -> None:
    clock = Clock()
    gateway = SingleReaderGateway(tmp_path, clock=clock)
    session = gateway.claim_reader(reader_id="lumos-primary", ttl_seconds=10)
    clock.value += timedelta(seconds=5)

    expires_at = gateway.heartbeat_reader(session.token, ttl_seconds=30)

    assert expires_at == clock.value + timedelta(seconds=30)
    gateway.release_reader(session.token)
    with pytest.raises(ReaderUnauthorized):
        gateway.read_user_digest(session.token)


def test_events_are_deduplicated_and_correlated_by_task(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path)

    first = gateway.submit_event(
        dedupe_key="ci:#631:success",
        source="github-ci",
        task_id="KA-002",
        kind=EventKind.INFORMATION,
        message="CI passed",
        user_relevant=True,
    )
    duplicate = gateway.submit_event(
        dedupe_key="ci:#631:success",
        source="github-ci",
        task_id="KA-002",
        kind=EventKind.INFORMATION,
        message="CI passed again",
        user_relevant=True,
    )

    assert first.accepted is True
    assert duplicate.accepted is False
    assert duplicate.duplicate_of == first.event.event_id
    assert duplicate.event.task_id == "KA-002"
    assert len(gateway.events_path.read_text(encoding="utf-8").splitlines()) == 1


def test_user_digest_contains_only_policy_selected_events(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path)
    session = gateway.claim_reader(reader_id="lumos-primary")
    samples = [
        ("decision", EventKind.DECISION_REQUIRED, "normal", False),
        ("risk-high", EventKind.RISK, "high", False),
        ("risk-low", EventKind.RISK, "low", False),
        ("recommend", EventKind.RECOMMENDATION, "normal", False),
        ("info-user", EventKind.INFORMATION, "normal", True),
        ("info-task", EventKind.INFORMATION, "normal", False),
        ("result", EventKind.RESULT, "normal", False),
    ]
    receipts = {
        key: gateway.submit_event(
            dedupe_key=key,
            source="agent-a",
            task_id="KA-003",
            kind=kind,
            message=key,
            severity=severity,
            user_relevant=user_relevant,
        )
        for key, kind, severity, user_relevant in samples
    }

    digest = gateway.read_user_digest(session.token)

    assert [event.message for event in digest.decisions] == ["decision"]
    assert [event.message for event in digest.risks] == ["risk-high"]
    assert [event.message for event in digest.recommendations] == ["recommend"]
    assert [event.message for event in digest.information] == ["info-user"]
    assert receipts["risk-low"].event.route is Route.TASK
    assert receipts["result"].event.route is Route.TASK


def test_internal_routes_are_read_only_by_the_single_reader(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path)
    session = gateway.claim_reader(reader_id="lumos-primary")
    gateway.submit_event(
        dedupe_key="dependency:KA-003:reviewer",
        source="agent-a",
        task_id="KA-003",
        kind=EventKind.DEPENDENCY,
        message="Review required",
        target_agent="reviewer-agent",
    )

    routes = gateway.read_internal_routes(session.token, target="reviewer-agent")

    assert len(routes) == 1
    assert routes[0].route is Route.AGENT
    with pytest.raises(ReaderUnauthorized):
        gateway.read_internal_routes("invalid", target="reviewer-agent")


def test_acknowledge_hides_delivered_events_but_read_does_not(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path)
    session = gateway.claim_reader(reader_id="lumos-primary")
    event = gateway.submit_event(
        dedupe_key="decision:631",
        source="github-ci",
        task_id="KA-002",
        kind=EventKind.DECISION_REQUIRED,
        message="PR #631 merge kararı gerekiyor",
    ).event

    assert gateway.read_user_digest(session.token).event_ids == (event.event_id,)
    assert gateway.read_user_digest(session.token).event_ids == (event.event_id,)
    gateway.acknowledge(session.token, [event.event_id])

    assert gateway.read_user_digest(session.token).event_ids == ()


def test_non_user_event_cannot_be_acknowledged_as_user_delivery(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path)
    session = gateway.claim_reader(reader_id="lumos-primary")
    event = gateway.submit_event(
        dedupe_key="result:KA-003",
        source="agent-a",
        task_id="KA-003",
        kind=EventKind.RESULT,
        message="Internal result",
    ).event

    with pytest.raises(CoordinationError, match="kullanıcı rotasındaki"):
        gateway.acknowledge(session.token, [event.event_id])


def test_sensitive_text_is_redacted_before_it_reaches_inbox(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path)

    event = gateway.submit_event(
        dedupe_key="risk:secret",
        source="agent-a",
        task_id="KA-003",
        kind=EventKind.RISK,
        message="token=super-secret-value erişimde göründü",
        severity="high",
    ).event

    assert event.message == "[redacted] erişimde göründü"
    assert "super-secret-value" not in gateway.events_path.read_text(encoding="utf-8")


def test_every_route_and_delivery_action_has_audit_evidence(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path)
    session = gateway.claim_reader(reader_id="lumos-primary")
    event = gateway.submit_event(
        dedupe_key="info:628",
        source="github-ci",
        task_id="KA-000",
        kind=EventKind.INFORMATION,
        message="#628 testleri tamamlandı",
        user_relevant=True,
    ).event
    gateway.read_user_digest(session.token)
    gateway.acknowledge(session.token, [event.event_id])

    audit = _audit(gateway.audit_path)

    assert all(item["schema"] == AUDIT_SCHEMA for item in audit)
    assert {item["event"] for item in audit} >= {
        "READER_CLAIMED",
        "EVENT_ROUTED",
        "USER_DIGEST_READ",
        "USER_DIGEST_ACKNOWLEDGED",
    }


def test_internal_route_read_cannot_leak_user_inbox(tmp_path: Path) -> None:
    gateway = SingleReaderGateway(tmp_path, clock=Clock())
    session = gateway.claim_reader(reader_id="lumos-primary")
    gateway.submit_event(
        dedupe_key="d1",
        source="cyber",
        task_id="KA-9",
        kind=EventKind.DECISION_REQUIRED,
        message="karar gerekli",
        user_relevant=True,
    )

    assert gateway.read_internal_routes(session.token, target="user") == ()
    digest = gateway.read_user_digest(session.token)
    assert len(digest.decisions) == 1


def test_audit_failure_rolls_back_reader_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = SingleReaderGateway(tmp_path, clock=Clock())
    original_audit = gateway._audit

    def failing_audit(event_type: str, **kwargs: object) -> None:
        if event_type == "READER_CLAIMED":
            raise OSError("disk dolu")
        original_audit(event_type, **kwargs)

    monkeypatch.setattr(gateway, "_audit", failing_audit)
    with pytest.raises(CoordinationError, match="geri alındı"):
        gateway.claim_reader(reader_id="lumos-primary")
    assert not gateway.reader_path.exists()

    monkeypatch.setattr(gateway, "_audit", original_audit)
    recovered = gateway.claim_reader(reader_id="lumos-primary")
    assert recovered.token


def test_event_append_rolls_back_when_audit_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = SingleReaderGateway(tmp_path, clock=Clock())
    original_audit = gateway._audit

    def failing_audit(event_type: str, **kwargs: object) -> None:
        if event_type == "EVENT_ROUTED":
            raise OSError("disk dolu")
        original_audit(event_type, **kwargs)

    monkeypatch.setattr(gateway, "_audit", failing_audit)
    with pytest.raises(CoordinationError, match="geri alındı"):
        gateway.submit_event(
            dedupe_key="d1", source="cyber", task_id="T1",
            kind=EventKind.INFORMATION, message="bilgi", user_relevant=True,
        )

    monkeypatch.setattr(gateway, "_audit", original_audit)
    retry = gateway.submit_event(
        dedupe_key="d1", source="cyber", task_id="T1",
        kind=EventKind.INFORMATION, message="bilgi", user_relevant=True,
    )
    assert retry.accepted is True
    assert retry.duplicate_of is None
