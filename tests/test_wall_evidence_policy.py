from datetime import datetime, timezone

import pytest

from lumos_board.evidence_policy import EvidencePolicy, deletion_blockers

T = datetime(2026, 9, 24, tzinfo=timezone.utc)


def test_internal_cannot_disable_or_show_switch():
    p = EvidencePolicy()
    assert p.view()['toggle_visible'] is False
    with pytest.raises(ValueError):
        p.set_capture(False)
    with pytest.raises(ValueError):
        EvidencePolicy(capture_deleted_content=False)


def test_customer_opt_out_preserves_audit_and_old_terms():
    p = EvidencePolicy(profile='customer')
    terms = p.record_terms(T, kind='deleted_content', severity='ordinary')
    disabled = p.set_capture(False)
    assert disabled.record_terms(T, kind='deleted_content', severity='ordinary') is None
    assert disabled.record_terms(T, kind='audit', severity='ordinary') is not None
    assert terms['default_retention'] == 'indefinite'
    assert 'MINIMUM_RETENTION_NOT_ELAPSED' in deletion_blockers(
        terms, at=T, exact_scope_approval_verified=True, investigation_open=False)


def test_one_year_does_not_authorize_deletion():
    terms = EvidencePolicy().record_terms(T, kind='audit', severity='ordinary')
    assert deletion_blockers(terms, at=T.replace(year=2028), investigation_open=False) == [
        'EXPLICIT_SCOPE_APPROVAL_REQUIRED']


@pytest.mark.parametrize('severity', ['unknown', 'critical'])
def test_unresolved_severity_held_indefinitely(severity):
    terms = EvidencePolicy().record_terms(T, kind='audit', severity=severity)
    assert 'SEVERITY_RETENTION_UNRESOLVED' in deletion_blockers(
        terms, at=T.replace(year=2040), exact_scope_approval_verified=True,
        investigation_open=False)


def test_leap_year_and_tamper():
    terms = EvidencePolicy().record_terms(datetime(2024, 2, 29, tzinfo=timezone.utc),
                                         kind='audit', severity='ordinary')
    assert terms['retain_until'].startswith('2025-03-01')
    terms['retain_until'] = '2024-03-01T00:00:00+00:00'
    assert deletion_blockers(terms, at=T) == ['RETENTION_FLOOR_TAMPERED']


def test_unknown_inputs_fail_closed():
    with pytest.raises(ValueError):
        EvidencePolicy(profile='anything')
    with pytest.raises(ValueError):
        EvidencePolicy(profile='customer', capture_deleted_content='false')
    assert deletion_blockers({}, at=T) == ['INVALID_RETENTION_RECORD']
    assert deletion_blockers({'schema': 'lumos.wall.retention.v1'}, at=T) == ['INVALID_RETENTION_RECORD']
