"""Elektronik Uzmanı — veri modeli testleri (Faz 1 pilot kapsamı)."""
from __future__ import annotations

import pytest

from electronics.models import (
    DeviceBoardInfo,
    EvidenceReference,
    FaultCase,
    Finding,
    InvalidFaultCaseTransition,
    InvalidFeatureAccessTransition,
    MeasurementEntry,
    FeatureAccessState,
    PilotAccessGrant,
    RiskFlag,
)


def _device() -> DeviceBoardInfo:
    return DeviceBoardInfo(device_type="PSU", brand="Örnek", model="X100")


def _case() -> FaultCase:
    return FaultCase(
        lumos_id="lumos:test-user",
        title="Açılmıyor",
        symptom_description="Cihaz güç verince açılmıyor, hafif yanık kokusu var.",
        device=_device(),
    )


# ---------------------------------------------------------------------------
# PilotAccessGrant
# ---------------------------------------------------------------------------


def test_pilot_access_grant_defaults_to_rapor_scope():
    grant = PilotAccessGrant(lumos_id="lumos:test-user")
    assert grant.scope == "rapor"
    assert grant.status == "invited"
    assert grant.cases_used == 0


def test_pilot_access_grant_rejects_non_rapor_scope():
    with pytest.raises(ValueError):
        PilotAccessGrant(lumos_id="lumos:test-user", scope="guvenli_yurut")


def test_pilot_access_grant_rejects_negative_quota():
    with pytest.raises(ValueError):
        PilotAccessGrant(lumos_id="lumos:test-user", case_quota=-1)


# ---------------------------------------------------------------------------
# FaultCase
# ---------------------------------------------------------------------------


def test_fault_case_defaults():
    case = _case()
    assert case.status == "open"
    assert case.source == "lumos_native"
    assert case.feature_access_state_snapshot == "pilot"
    assert case.measurement_ids == []


def test_fault_case_legal_transition_sequence():
    case = _case()
    case.start_progress()
    assert case.status == "in_progress"
    case.resolve()
    assert case.status == "resolved"
    case.archive()
    assert case.status == "archived"


def test_fault_case_illegal_transition_raises():
    case = _case()
    with pytest.raises(InvalidFaultCaseTransition):
        case.resolve()  # open -> resolved atlanamaz


def test_fault_case_archived_is_terminal():
    case = _case()
    case.start_progress()
    case.archive()
    with pytest.raises(InvalidFaultCaseTransition):
        case.start_progress()


def test_fault_case_link_helpers_bump_updated_at():
    case = _case()
    before = case.updated_at
    case.link_measurement("m-1")
    assert "m-1" in case.measurement_ids
    assert case.updated_at >= before


# ---------------------------------------------------------------------------
# MeasurementEntry
# ---------------------------------------------------------------------------


def test_measurement_entry_is_always_manual():
    m = MeasurementEntry(
        case_id="case-1",
        test_point_label="C12 anot",
        measurement_type="voltage",
        measured_value=4.8,
        unit="V",
        reference_point="GND",
        expected_nominal=5.0,
    )
    assert m.entered_by == "user"


def test_measurement_entry_deviation_flag_within_tolerance():
    m = MeasurementEntry(
        case_id="case-1",
        test_point_label="C12 anot",
        measurement_type="voltage",
        measured_value=4.8,
        unit="V",
        reference_point="GND",
        expected_nominal=5.0,
    )
    assert m.deviation_flag() is False  # %4 sapma, %10 tolerans içinde


def test_measurement_entry_deviation_flag_outside_tolerance():
    m = MeasurementEntry(
        case_id="case-1",
        test_point_label="C12 anot",
        measurement_type="voltage",
        measured_value=3.0,
        unit="V",
        reference_point="GND",
        expected_nominal=5.0,
    )
    assert m.deviation_flag() is True  # %40 sapma


def test_measurement_entry_deviation_flag_none_without_expected_value():
    m = MeasurementEntry(
        case_id="case-1",
        test_point_label="C12 anot",
        measurement_type="voltage",
        measured_value=4.8,
        unit="V",
        reference_point="GND",
    )
    assert m.deviation_flag() is None


def test_voltage_measurement_requires_reference_point():
    with pytest.raises(ValueError):
        MeasurementEntry(
            case_id="case-1",
            test_point_label="C12 anot",
            measurement_type="voltage",
            measured_value=4.8,
            unit="V",
        )


def test_energized_measurement_requires_risk_check():
    with pytest.raises(ValueError):
        MeasurementEntry(
            case_id="case-1",
            test_point_label="C12 anot",
            measurement_type="voltage",
            measured_value=4.8,
            unit="V",
            reference_point="GND",
            circuit_state="energized",
        )


def test_measurement_comparison_supports_expected_range():
    m = MeasurementEntry(
        case_id="case-1",
        test_point_label="C12 anot",
        measurement_type="voltage",
        measured_value=4.8,
        unit="V",
        reference_point="GND",
        expected_min=4.75,
        expected_max=5.25,
    )
    assert m.comparison_result == "within"


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------


def test_finding_requires_evidence():
    with pytest.raises(ValueError):
        Finding(
            case_id="case-1",
            statement="C12 kısa devre olabilir",
            confidence_level="medium",
            evidence=[],
        )


def test_finding_lumos_assist_requires_disclaimer():
    with pytest.raises(ValueError):
        Finding(
            case_id="case-1",
            statement="C12 kısa devre olabilir",
            confidence_level="medium",
            evidence=[EvidenceReference(kind="measurement", ref_id="m-1")],
            created_by="lumos_assist",
            disclaimer_shown=False,
        )


def test_finding_lumos_assist_with_disclaimer_succeeds():
    finding = Finding(
        case_id="case-1",
        statement="C12 kısa devre olabilir",
        confidence_level="medium",
        evidence=[EvidenceReference(kind="measurement", ref_id="m-1")],
        created_by="lumos_assist",
        disclaimer_shown=True,
    )
    assert finding.disclaimer_shown is True


def test_finding_confidence_score_bounds():
    with pytest.raises(ValueError):
        Finding(
            case_id="case-1",
            statement="C12 kısa devre olabilir",
            confidence_level="medium",
            evidence=[EvidenceReference(kind="measurement", ref_id="m-1")],
            confidence_score=101,
        )


# ---------------------------------------------------------------------------
# RiskFlag
# ---------------------------------------------------------------------------


def test_risk_flag_is_never_suppressed():
    risk = RiskFlag(
        case_id="case-1",
        risk_category="mains_voltage",
        severity="critical",
        triggered_by="keyword_match",
    )
    assert risk.suppressed is False
    assert risk.required_ack is True
    assert risk.acknowledged is False


def test_risk_flag_acknowledge_sets_timestamp():
    risk = RiskFlag(
        case_id="case-1",
        risk_category="fire_smoke_smell",
        severity="critical",
        triggered_by="user_reported_symptom",
    )
    risk.acknowledge()
    assert risk.acknowledged is True
    assert risk.acknowledged_at is not None
    assert risk.flow_action == "block"
    assert risk.allows_flow is False


def test_warn_risk_allows_flow_only_after_acknowledgement():
    risk = RiskFlag(
        case_id="case-1",
        risk_category="other",
        severity="warn",
        triggered_by="keyword_match",
    )
    assert risk.flow_action == "continue_after_ack"
    assert risk.allows_flow is False
    risk.acknowledge()
    assert risk.allows_flow is True


# ---------------------------------------------------------------------------
# FeatureAccessState
# ---------------------------------------------------------------------------


def test_feature_access_state_starts_closed():
    state = FeatureAccessState(feature_key="electronics_expert_pilot")
    assert state.status == "closed"


def test_feature_access_state_linear_transition():
    state = FeatureAccessState(feature_key="electronics_expert_pilot")
    state.transition_to("pilot", decision_ref="ADR-017")
    assert state.status == "pilot"
    assert state.decision_ref == "ADR-017"
    state.transition_to("validated", decision_ref="OD-101")
    assert state.status == "validated"
    state.transition_to("paid", decision_ref="OD-102")
    assert state.status == "paid"


def test_feature_access_state_cannot_skip_stages():
    state = FeatureAccessState(feature_key="electronics_expert_pilot")
    with pytest.raises(InvalidFeatureAccessTransition):
        state.transition_to("validated", decision_ref="ADR-017")


def test_feature_access_state_requires_decision_ref():
    state = FeatureAccessState(feature_key="electronics_expert_pilot")
    with pytest.raises(InvalidFeatureAccessTransition):
        state.transition_to("pilot", decision_ref="")


def test_feature_access_state_paid_is_terminal():
    state = FeatureAccessState(feature_key="electronics_expert_pilot")
    state.transition_to("pilot", decision_ref="ADR-017")
    state.transition_to("validated", decision_ref="OD-101")
    state.transition_to("paid", decision_ref="OD-102")
    with pytest.raises(InvalidFeatureAccessTransition):
        state.transition_to("pilot", decision_ref="OD-103")


def test_feature_access_state_can_roll_back_for_safety():
    state = FeatureAccessState(feature_key="electronics_expert_pilot")
    state.transition_to("pilot", decision_ref="ADR-017")
    state.transition_to("validated", decision_ref="OD-101")
    state.transition_to("paid", decision_ref="OD-102")
    state.rollback_to(
        "closed", decision_ref="OD-103", reason="open critical safety incident"
    )
    assert state.status == "closed"
    assert state.rollback_reason == "open critical safety incident"


def test_feature_access_rollback_requires_audit_reason():
    state = FeatureAccessState(feature_key="electronics_expert_pilot", status="pilot")
    with pytest.raises(InvalidFeatureAccessTransition):
        state.rollback_to("closed", decision_ref="OD-103", reason="")
