"""ADR-032: privacy-preserving Account Activity Correlation kernel."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from account_activity.engine import (
    AUTO_FORBIDDEN_ACTIONS,
    DECISION_APPROVE_ACTION,
    DECISION_INVESTIGATE,
    RETENTION_ORDINARY,
    SOURCE_DEVICE_ACTIVITY,
    SOURCE_NETWORK,
    SOURCE_THIRD_PARTY_ALERT,
    VERDICT_LIKELY_OWNER,
    VERDICT_OWNER_MATCH,
    VERDICT_SUSPICIOUS,
    VERDICT_UNKNOWN,
    WINDOW_DEFAULT,
    WINDOW_TIGHT,
    AccountActivityCorrelator,
    CorrelationError,
    format_activity_line,
    make_device_id,
)

IPHONE_KEY = b"iphone-15-public-key-material-aaa"
MAC_KEY = b"macbook-public-key-material-bbbbbb"
T0 = datetime(2026, 9, 2, 6, 18, tzinfo=timezone.utc)


def _engine(tmp_path: Path | None = None) -> AccountActivityCorrelator:
    engine = AccountActivityCorrelator(persist_dir=tmp_path)
    engine.set_consent(True)
    engine.register_device(
        device_id=make_device_id(IPHONE_KEY),
        public_key_fingerprint=make_device_id(IPHONE_KEY + b"-fp"),
        display_label="iPhone 15",
        attestation_ref=make_device_id(b"iphone-attestation"),
    )
    return engine


def _grok_activity(engine: AccountActivityCorrelator, **overrides: object) -> None:
    agent_id = str(overrides.pop("agent_id", "lumos.local"))
    payload = {
        "observed_at": T0,
        "service_id": "xai.grok",
        "device_id": make_device_id(IPHONE_KEY),
        "session_kind": "user_session",
        "network_class": "mobile",
        "network_material": "net:mobile:cell-a",
    }
    payload.update(overrides)
    engine.record_activity(payload, agent_id=agent_id)


def _xai_alert(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "observed_at": T0 + timedelta(minutes=2),
        "service_id": "xai.grok",
        "source_label": "xAI security email",
        "ingest_agent_id": "agent:mail-triage",
        "claimed_network_class": "mobile",
        "network_material": "net:mobile:cell-a",
    }
    payload.update(overrides)
    return payload


def test_format_line_is_minimal_session_summary() -> None:
    engine = _engine()
    _grok_activity(engine)
    activity = engine.activities()[0]
    device = engine.known_devices()[0]
    assert (
        format_activity_line(activity, device)
        == "2026-09-02 06:18 — xAI/Grok — iPhone 15 — mobil ağ — kullanıcı oturumu"
    )


def test_label_only_device_is_rejected() -> None:
    engine = AccountActivityCorrelator()
    engine.set_consent(True)
    with pytest.raises(CorrelationError, match="device_id_not_bound"):
        engine.register_device(
            device_id="iPhone 15",
            public_key_fingerprint=make_device_id(b"x"),
            display_label="iPhone 15",
        )


def test_activity_requires_registered_device() -> None:
    engine = AccountActivityCorrelator()
    engine.set_consent(True)
    with pytest.raises(CorrelationError, match="device_not_registered"):
        engine.record_activity(
            {
                "observed_at": T0,
                "service_id": "xai.grok",
                "device_id": make_device_id(b"unknown-device"),
                "session_kind": "user_session",
                "network_class": "mobile",
            }
        )


def test_raw_history_password_and_plaintext_ip_are_rejected() -> None:
    engine = _engine()
    with pytest.raises(CorrelationError, match="forbidden_field:history"):
        engine.record_activity({"history": ["https://grok.x.ai/c/abc"], "device_id": "x"})
    with pytest.raises(CorrelationError, match="forbidden_field:password"):
        engine.ingest_alert({"password": "secret", "source_label": "xAI security email"})
    with pytest.raises(CorrelationError, match="plaintext_ip_forbidden"):
        engine.record_activity(
            {
                "observed_at": T0,
                "service_id": "xai.grok",
                "device_id": make_device_id(IPHONE_KEY),
                "session_kind": "user_session",
                "network_class": "mobile",
                "network_material": "203.0.113.44",
            }
        )


def test_consent_gate_and_revoke_purges_traces() -> None:
    engine = AccountActivityCorrelator()
    with pytest.raises(CorrelationError, match="recording_disabled"):
        engine.record_activity(
            {
                "observed_at": T0,
                "service_id": "xai.grok",
                "device_id": make_device_id(IPHONE_KEY),
                "session_kind": "user_session",
                "network_class": "mobile",
            }
        )
    engine = _engine()
    _grok_activity(engine)
    assert engine.activities()
    engine.set_consent(False)
    assert engine.activities() == ()
    result = engine.correlate(_xai_alert())
    assert result.verdict == VERDICT_UNKNOWN
    assert "kapalı" in result.explanation


def test_mail_alert_correlates_to_registered_iphone_session() -> None:
    engine = _engine()
    _grok_activity(engine)
    result = engine.correlate(_xai_alert(), agent_id="agent:mail-triage")

    assert result.verdict == VERDICT_OWNER_MATCH
    assert result.auto_action == "none"
    labels = [source.label for source in result.sources]
    kinds = [source.kind for source in result.sources]
    assert "xAI security email" in labels
    assert "Lumos device activity" in labels
    assert "network observation" in labels
    assert kinds == [
        SOURCE_THIRD_PARTY_ALERT,
        SOURCE_DEVICE_ACTIVITY,
        SOURCE_NETWORK,
    ]
    assert result.network_result == "same_network"
    explanation = engine.explain(result.correlation_id)
    assert "kesin hüküm" in explanation
    assert "xAI security email" in explanation
    assert "Lumos device activity" in explanation
    assert "sendin" not in explanation
    assert "definitely" not in explanation.lower()


def test_time_only_other_service_is_unknown_not_owner() -> None:
    engine = _engine()
    _grok_activity(engine, service_id="google")
    result = engine.correlate(_xai_alert())
    assert result.verdict == VERDICT_UNKNOWN
    assert result.confidence == "weak"


def test_unmatched_alert_is_suspicious() -> None:
    engine = _engine()
    result = engine.correlate(_xai_alert())
    assert result.verdict == VERDICT_SUSPICIOUS
    assert "Eşleşen kayıtlı cihaz aktivitesi yok" in result.explanation


def test_match_window_rejects_same_day_drift() -> None:
    engine = _engine()
    _grok_activity(engine)
    late = _xai_alert(observed_at=T0 + timedelta(minutes=11))
    result = engine.correlate(late)
    assert result.verdict == VERDICT_SUSPICIOUS
    tight = engine.correlate(
        _xai_alert(observed_at=T0 + timedelta(minutes=4)),
        window=WINDOW_TIGHT,
    )
    assert tight.verdict == VERDICT_OWNER_MATCH
    with pytest.raises(CorrelationError, match="window_exceeds_maximum"):
        engine.correlate(_xai_alert(), window=timedelta(hours=24))
    assert WINDOW_DEFAULT == timedelta(minutes=10)


def test_different_network_downgrades_to_likely_owner() -> None:
    engine = _engine()
    _grok_activity(engine, network_material="net:mobile:cell-a")
    result = engine.correlate(
        _xai_alert(
            claimed_network_class="wifi",
            network_material="net:wifi:other-prefix",
        )
    )
    assert result.verdict == VERDICT_LIKELY_OWNER
    assert result.network_result == "different_network"


def test_device_identity_conflict_is_suspicious() -> None:
    engine = _engine()
    engine.register_device(
        device_id=make_device_id(MAC_KEY),
        public_key_fingerprint=make_device_id(MAC_KEY + b"-fp"),
        display_label="MacBook",
    )
    _grok_activity(engine)
    result = engine.correlate(_xai_alert(claimed_device_id=make_device_id(MAC_KEY)))
    assert result.verdict == VERDICT_SUSPICIOUS


def test_mail_alert_never_auto_changes_password() -> None:
    engine = _engine()
    _grok_activity(engine)
    result = engine.correlate(_xai_alert())
    with pytest.raises(CorrelationError, match="human_approval_required"):
        engine.execute_action(result.correlation_id, "password_change")
    decision = engine.record_user_decision(
        result.correlation_id,
        DECISION_APPROVE_ACTION,
        action="password_change",
        agent_id="user:candas",
    )
    assert decision.action == "password_change"
    assert "password_change" in AUTO_FORBIDDEN_ACTIONS
    with pytest.raises(CorrelationError, match="human_approval_required"):
        engine.execute_action(result.correlation_id, "session_revoke")


def test_provenance_records_agent_match_and_user_decision() -> None:
    engine = _engine()
    _grok_activity(engine, agent_id="agent:ios")
    result = engine.correlate(_xai_alert(), agent_id="agent:mail-triage")
    engine.record_user_decision(
        result.correlation_id,
        DECISION_INVESTIGATE,
        agent_id="user:candas",
    )
    kinds = [event.kind for event in engine.provenance]
    assert "alert_ingested" in kinds
    assert "correlated" in kinds
    assert "user_decided" in kinds
    correlated = [event for event in engine.provenance if event.kind == "correlated"][-1]
    assert correlated.agent_id == "agent:mail-triage"
    assert correlated.details["verdict"] == VERDICT_OWNER_MATCH
    assert engine.verify_provenance_chain() is True


def test_retention_purges_ordinary_faster_than_high_risk() -> None:
    engine = _engine()
    _grok_activity(engine)
    ordinary_id = engine.activities()[0].event_id
    _grok_activity(
        engine,
        event_id="keep-high",
        observed_at=T0 - timedelta(days=20),
    )
    engine.mark_high_risk("keep-high")
    removed = engine.purge_expired(now=T0 + RETENTION_ORDINARY + timedelta(hours=1))
    ids = {item.event_id for item in engine.activities()}
    assert ordinary_id not in ids
    assert "keep-high" in ids
    assert removed >= 1


def test_persist_dir_never_writes_plaintext_ip(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _grok_activity(engine, network_material="net:mobile:cell-a")
    engine.correlate(_xai_alert())
    dumped = "".join(path.read_text(encoding="utf-8") for path in tmp_path.glob("*.jsonl"))
    assert "203.0.113" not in dumped
    assert "history" not in dumped
    assert "password" not in dumped
    assert "xai.grok" in dumped
