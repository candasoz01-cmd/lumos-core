"""Elektronik Uzmanı — pilot erişim kontrolü testleri."""
from __future__ import annotations

import pytest

from electronics.models import PilotAccessGrant
from electronics.pilot_access import (
    PilotAccessDenied,
    activate_grant,
    consume_case_slot,
    ensure_can_open_case,
    revoke_grant,
)


def _invited_grant(quota: int = 20) -> PilotAccessGrant:
    return PilotAccessGrant(lumos_id="lumos:test-user", case_quota=quota)


def test_activate_grant_requires_consent_version():
    grant = _invited_grant()
    with pytest.raises(PilotAccessDenied):
        activate_grant(grant, consent_version="")


def test_activate_grant_success():
    grant = _invited_grant()
    activate_grant(grant, consent_version="v1")
    assert grant.status == "active"
    assert grant.consent_version == "v1"
    assert grant.activated_at is not None


def test_revoked_grant_cannot_be_reactivated():
    grant = _invited_grant()
    activate_grant(grant, consent_version="v1")
    revoke_grant(grant)
    assert grant.status == "revoked"
    with pytest.raises(PilotAccessDenied):
        activate_grant(grant, consent_version="v2")


def test_ensure_can_open_case_rejects_inactive_grant():
    grant = _invited_grant()
    with pytest.raises(PilotAccessDenied):
        ensure_can_open_case(grant)


def test_ensure_can_open_case_allows_active_grant_with_quota():
    grant = _invited_grant()
    activate_grant(grant, consent_version="v1")
    ensure_can_open_case(grant)  # raise etmemeli


def test_consume_case_slot_increments_usage():
    grant = _invited_grant()
    activate_grant(grant, consent_version="v1")
    consume_case_slot(grant)
    assert grant.cases_used == 1


def test_consume_case_slot_blocks_after_quota_exhausted():
    grant = _invited_grant(quota=1)
    activate_grant(grant, consent_version="v1")
    consume_case_slot(grant)
    with pytest.raises(PilotAccessDenied):
        consume_case_slot(grant)


def test_revoked_grant_cannot_open_case():
    grant = _invited_grant()
    activate_grant(grant, consent_version="v1")
    revoke_grant(grant)
    with pytest.raises(PilotAccessDenied):
        ensure_can_open_case(grant)
