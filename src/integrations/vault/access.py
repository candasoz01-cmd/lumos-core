from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class CredentialAccessAction(StrEnum):
    """Kasa erişim kararı; secret veya token taşımaz."""

    REUSE = "reuse"
    REAUTHENTICATE = "reauthenticate"
    APPROVAL_REQUIRED = "approval_required"
    DENY = "deny"


class CredentialBindingStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True)
class CredentialBindingKey:
    """Bir Lumos kullanıcısındaki tek uygulama/hesap/amaç bağını tanımlar."""

    owner_id: str
    provider: str
    account_id: str
    purpose_code: str

    def __post_init__(self) -> None:
        for field_name in ("owner_id", "provider", "account_id", "purpose_code"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name}_required")
            object.__setattr__(self, field_name, value.strip())


@dataclass(frozen=True)
class CredentialBinding:
    """Doğrulanmış hesap bağı; gerçek secret yalnızca vault'ta kalır."""

    key: CredentialBindingKey
    vault_ref: str
    granted_scopes: frozenset[str]
    verified_at: datetime
    expires_at: datetime
    verification_source: str
    status: CredentialBindingStatus = CredentialBindingStatus.ACTIVE
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.vault_ref, str) or not self.vault_ref.strip():
            raise ValueError("vault_ref_required")
        if not isinstance(self.verification_source, str) or not self.verification_source.strip():
            raise ValueError("verification_source_required")
        _require_aware(self.verified_at, "verified_at")
        _require_aware(self.expires_at, "expires_at")
        if self.expires_at <= self.verified_at:
            raise ValueError("expires_at_must_follow_verified_at")
        if self.revoked_at is not None:
            _require_aware(self.revoked_at, "revoked_at")
        if self.status is CredentialBindingStatus.REVOKED and self.revoked_at is None:
            raise ValueError("revoked_at_required")
        if self.status is CredentialBindingStatus.ACTIVE and self.revoked_at is not None:
            raise ValueError("active_binding_cannot_have_revoked_at")

        normalized_scopes = frozenset(
            scope.strip() for scope in self.granted_scopes if isinstance(scope, str) and scope.strip()
        )
        object.__setattr__(self, "vault_ref", self.vault_ref.strip())
        object.__setattr__(self, "verification_source", self.verification_source.strip())
        object.__setattr__(self, "granted_scopes", normalized_scopes)

    def public_metadata(self) -> dict[str, object]:
        """UI/audit için güvenli özet; vault ref ve secret döndürülmez."""
        return {
            "owner_id": self.key.owner_id,
            "provider": self.key.provider,
            "account_id": self.key.account_id,
            "purpose_code": self.key.purpose_code,
            "granted_scopes": sorted(self.granted_scopes),
            "verified_at": _to_iso(self.verified_at),
            "expires_at": _to_iso(self.expires_at),
            "verification_source": self.verification_source,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class CredentialAccessRequest:
    key: CredentialBindingKey
    required_scopes: frozenset[str]
    consequential: bool = False

    def __post_init__(self) -> None:
        normalized_scopes = frozenset(
            scope.strip() for scope in self.required_scopes if isinstance(scope, str) and scope.strip()
        )
        object.__setattr__(self, "required_scopes", normalized_scopes)


@dataclass(frozen=True)
class CredentialAccessDecision:
    action: CredentialAccessAction
    reason: str

    @property
    def reusable(self) -> bool:
        return self.action is CredentialAccessAction.REUSE


def evaluate_credential_access(
    binding: CredentialBinding | None,
    request: CredentialAccessRequest,
    *,
    now: datetime | None = None,
) -> CredentialAccessDecision:
    """Geçerli düşük riskli bağı tekrar kullanır; şüphede kapalı kalır."""
    checked_at = now or datetime.now(timezone.utc)
    _require_aware(checked_at, "now")

    if binding is None:
        return CredentialAccessDecision(
            CredentialAccessAction.REAUTHENTICATE,
            "credential_binding_missing",
        )
    if binding.key != request.key:
        return CredentialAccessDecision(
            CredentialAccessAction.DENY,
            "credential_binding_mismatch",
        )
    if binding.status is CredentialBindingStatus.REVOKED:
        return CredentialAccessDecision(
            CredentialAccessAction.APPROVAL_REQUIRED,
            "credential_revoked_approval_required",
        )
    if checked_at >= binding.expires_at:
        return CredentialAccessDecision(
            CredentialAccessAction.REAUTHENTICATE,
            "credential_expired",
        )
    if not request.required_scopes.issubset(binding.granted_scopes):
        return CredentialAccessDecision(
            CredentialAccessAction.APPROVAL_REQUIRED,
            "scope_expansion_required",
        )
    if request.consequential:
        return CredentialAccessDecision(
            CredentialAccessAction.APPROVAL_REQUIRED,
            "consequential_action_required",
        )
    return CredentialAccessDecision(
        CredentialAccessAction.REUSE,
        "verified_context_reused",
    )


def _require_aware(value: datetime, field_name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name}_must_be_timezone_aware")


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
