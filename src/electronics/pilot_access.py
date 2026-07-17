"""
Elektronik Uzmanı — pilot erişim kontrolü (bkz. design doc §3).

Bu modül yalnızca `PilotAccessGrant` durum geçişlerini ve fair-use kotasını
kontrol eder. Hiçbir dış servis çağrısı, oturum/kimlik doğrulama veya
state-changing OS eylemi yapmaz — yalnızca in-memory karar mantığı.
"""
from __future__ import annotations

from electronics.models import PilotAccessGrant, now_utc


class PilotAccessDenied(Exception):
    """Pilot erişimi reddedildiğinde fırlatılır (davetsiz, iptal edilmiş,
    yanlış scope veya kota aşımı)."""


def activate_grant(grant: PilotAccessGrant, consent_version: str) -> PilotAccessGrant:
    """Bir daveti aktif pilot erişimine çevirir. Açık onay sözleşmesi
    sürümü (`consent_version`) olmadan aktivasyon yapılmaz."""
    if grant.status == "revoked":
        raise PilotAccessDenied(f"grant {grant.grant_id} is revoked and cannot be reactivated")
    if not consent_version:
        raise PilotAccessDenied("consent_version is required to activate a pilot grant")
    grant.status = "active"
    grant.consent_version = consent_version
    grant.activated_at = now_utc()
    return grant


def revoke_grant(grant: PilotAccessGrant) -> PilotAccessGrant:
    """Pilot erişimini iptal eder. Geri dönüşü yoktur (yeniden davet =
    yeni bir grant kaydı)."""
    grant.status = "revoked"
    grant.revoked_at = now_utc()
    return grant


def ensure_can_open_case(grant: PilotAccessGrant) -> None:
    """Yeni bir FaultCase açılmadan önce çağrılır. Yalnızca kontrol eder;
    hiçbir alanı değiştirmez. Reddedilirse PilotAccessDenied fırlatır."""
    if grant.status != "active":
        raise PilotAccessDenied(
            f"grant {grant.grant_id} is not active (status={grant.status})"
        )
    if grant.cases_used >= grant.case_quota:
        raise PilotAccessDenied(
            f"pilot case quota exceeded ({grant.cases_used}/{grant.case_quota})"
        )


def consume_case_slot(grant: PilotAccessGrant) -> PilotAccessGrant:
    """Bir FaultCase başarıyla açıldıktan SONRA çağrılır; kota sayacını
    bir artırır. Önce `ensure_can_open_case` ile doğrulanmalıdır."""
    ensure_can_open_case(grant)
    grant.cases_used += 1
    return grant
