"""Atomic task claims for the Lumos Board orchestration surface."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import os
import re
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator, Mapping, Sequence


CLAIM_STORE_SCHEMA = "lumos.task_claim_store.v1"
CLAIM_EVENT_SCHEMA = "lumos.task_claim_event.v1"
APPROVER_REGISTRY_SCHEMA = "lumos.override_approver_registry.v1"
OVERRIDE_APPROVAL_SCHEMA = "lumos.override_approval.v1"
OVERRIDE_VERIFICATION_METHOD = "HMAC_SHA256_ALLOWLIST"
DELEGATION_OWNER_REGISTRY_SCHEMA = "lumos.delegation_owner_registry.v1"
DELEGATION_TOKEN_SCHEMA = "lumos.delegation_token.v1"
DELEGATION_VERIFICATION_METHOD = "HMAC_SHA256_OWNER_ALLOWLIST"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_BRANCH_NAME = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/-]{0,127}$")
_TOPIC_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ClaimStatus(str, Enum):
    ACTIVE = "ACTIVE"
    QUEUED = "QUEUED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    OVERRIDDEN = "OVERRIDDEN"


class ClaimError(ValueError):
    """Base error for invalid or unauthorized claim operations."""


class ClaimStoreCorrupt(ClaimError):
    """Raised when persisted state cannot be trusted; writes fail closed."""


@dataclass(frozen=True)
class VerifiedOverrideApproval:
    approval_id: str
    approver_id: str
    verification_method: str
    expires_at: datetime


class OverrideApprovalVerifier:
    """Verify signed approvals against a fail-closed approver allowlist."""

    def __init__(
        self,
        *,
        secret: bytes,
        approvers: dict[str, datetime],
    ) -> None:
        if len(secret) < 32:
            raise ClaimError("override approval secret en az 32 byte olmalı")
        if not approvers:
            raise ClaimError("override approver allowlist boş olamaz")
        self._secret = secret
        self._approvers = dict(approvers)

    @classmethod
    def from_registry_file(cls, path: Path, *, secret: str) -> OverrideApprovalVerifier:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimError("override approver registry okunamıyor") from exc
        if not isinstance(payload, dict) or payload.get("schema") != APPROVER_REGISTRY_SCHEMA:
            raise ClaimError("override approver registry şeması geçersiz")
        entries = payload.get("approvers")
        if not isinstance(entries, list):
            raise ClaimError("override approver listesi geçersiz")
        approvers: dict[str, datetime] = {}
        try:
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("enabled") is not True:
                    continue
                approver_id = _required_text(entry, "approver_id")
                if approver_id in approvers:
                    raise ClaimError("override approver registry tekrarlı kimlik içeriyor")
                approvers[approver_id] = _parse_time(_required_text(entry, "valid_until"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ClaimError("override approver registry kaydı geçersiz") from exc
        return cls(secret=_clean_text(secret, "override approval secret").encode(), approvers=approvers)

    def verify(
        self,
        token: str,
        *,
        task_id: str,
        current_owner: str,
        new_owner: str,
        reason: str,
        now: datetime,
    ) -> VerifiedOverrideApproval:
        try:
            encoded_payload, encoded_signature = _clean_text(token, "override_token").split(".", 1)
            payload_bytes = _b64url_decode(encoded_payload)
            signature = _b64url_decode(encoded_signature)
            expected = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ClaimError("override approval imzası geçersiz")
            payload = json.loads(payload_bytes)
            if not isinstance(payload, dict) or payload.get("schema") != OVERRIDE_APPROVAL_SCHEMA:
                raise ClaimError("override approval şeması geçersiz")
            approval_id = _required_text(payload, "approval_id")
            approver_id = _required_text(payload, "approver_id")
            issued_at = _parse_time(_required_text(payload, "issued_at"))
            expires_at = _parse_time(_required_text(payload, "expires_at"))
        except ClaimError:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimError("override approval token geçersiz") from exc

        if payload.get("verification_method") != OVERRIDE_VERIFICATION_METHOD:
            raise ClaimError("override doğrulama yöntemi geçersiz")
        if issued_at > now or expires_at <= now or expires_at <= issued_at:
            raise ClaimError("override approval süresi geçersiz veya dolmuş")
        allowlist_until = self._approvers.get(approver_id)
        if allowlist_until is None or allowlist_until <= now or expires_at > allowlist_until:
            raise ClaimError("override approver allowlist yetkisi geçersiz")
        if approver_id in {current_owner, new_owner}:
            raise ClaimError("override approver owner'lardan farklı olmalı")
        expected_context = {
            "task_id": task_id,
            "current_owner": current_owner,
            "new_owner": new_owner,
            "reason": reason,
        }
        if any(payload.get(key) != value for key, value in expected_context.items()):
            raise ClaimError("override approval bağlamı eşleşmiyor")
        return VerifiedOverrideApproval(
            approval_id=approval_id,
            approver_id=approver_id,
            verification_method=OVERRIDE_VERIFICATION_METHOD,
            expires_at=expires_at,
        )


def sign_override_approval(
    *,
    secret: bytes,
    approval_id: str,
    approver_id: str,
    task_id: str,
    current_owner: str,
    new_owner: str,
    reason: str,
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    """Create a token in a trusted approval service; the claim CLI never calls this."""
    payload = {
        "schema": OVERRIDE_APPROVAL_SCHEMA,
        "approval_id": _clean_text(approval_id, "approval_id"),
        "approver_id": _clean_text(approver_id, "approver_id"),
        "verification_method": OVERRIDE_VERIFICATION_METHOD,
        "task_id": _clean_text(task_id, "task_id"),
        "current_owner": _clean_text(current_owner, "current_owner"),
        "new_owner": _clean_text(new_owner, "new_owner"),
        "reason": _clean_text(reason, "reason"),
        "issued_at": _format_time(issued_at),
        "expires_at": _format_time(expires_at),
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(secret, payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


@dataclass(frozen=True)
class VerifiedDelegation:
    delegation_id: str
    parent_owner: str
    verification_method: str
    expires_at: datetime


class DelegationVerifier:
    """Verify parent-owner delegation tokens against an owner allowlist."""

    def __init__(self, *, secret: bytes, owners: dict[str, datetime]) -> None:
        if len(secret) < 32:
            raise ClaimError("delegation secret en az 32 byte olmalı")
        if not owners:
            raise ClaimError("delegation owner allowlist boş olamaz")
        self._secret = secret
        self._owners = dict(owners)

    @classmethod
    def from_registry_file(cls, path: Path, *, secret: str) -> DelegationVerifier:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimError("delegation owner registry okunamıyor") from exc
        if not isinstance(payload, dict) or payload.get("schema") != DELEGATION_OWNER_REGISTRY_SCHEMA:
            raise ClaimError("delegation owner registry şeması geçersiz")
        entries = payload.get("owners")
        if not isinstance(entries, list):
            raise ClaimError("delegation owner listesi geçersiz")
        owners: dict[str, datetime] = {}
        try:
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("enabled") is not True:
                    continue
                owner_id = _required_text(entry, "owner_id")
                if owner_id in owners:
                    raise ClaimError("delegation owner registry tekrarlı kimlik içeriyor")
                owners[owner_id] = _parse_time(_required_text(entry, "valid_until"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ClaimError("delegation owner registry kaydı geçersiz") from exc
        return cls(secret=_clean_text(secret, "delegation secret").encode(), owners=owners)

    def verify(
        self,
        token: str,
        *,
        parent_claim_id: str,
        parent_owner: str,
        child_owner: str,
        child_task_id: str,
        repo: str,
        scopes: Sequence[str],
        now: datetime,
    ) -> VerifiedDelegation:
        try:
            encoded_payload, encoded_signature = _clean_text(token, "delegation_token").split(".", 1)
            payload_bytes = _b64url_decode(encoded_payload)
            signature = _b64url_decode(encoded_signature)
            expected = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ClaimError("delegation token imzası geçersiz")
            payload = json.loads(payload_bytes)
            if not isinstance(payload, dict) or payload.get("schema") != DELEGATION_TOKEN_SCHEMA:
                raise ClaimError("delegation token şeması geçersiz")
            delegation_id = _required_text(payload, "delegation_id")
            token_owner = _required_text(payload, "parent_owner")
            issued_at = _parse_time(_required_text(payload, "issued_at"))
            expires_at = _parse_time(_required_text(payload, "expires_at"))
            token_scopes = payload.get("scopes")
            if not isinstance(token_scopes, list) or not all(isinstance(item, str) for item in token_scopes):
                raise ClaimError("delegation token scope listesi geçersiz")
        except ClaimError:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimError("delegation token geçersiz") from exc

        if payload.get("verification_method") != DELEGATION_VERIFICATION_METHOD:
            raise ClaimError("delegation doğrulama yöntemi geçersiz")
        if issued_at > now or expires_at <= now or expires_at <= issued_at:
            raise ClaimError("delegation token süresi geçersiz veya dolmuş")
        allowlist_until = self._owners.get(token_owner)
        if allowlist_until is None or allowlist_until <= now or expires_at > allowlist_until:
            raise ClaimError("delegation owner allowlist yetkisi geçersiz")
        expected_context: dict[str, object] = {
            "parent_claim_id": parent_claim_id,
            "parent_owner": parent_owner,
            "child_owner": child_owner,
            "child_task_id": child_task_id,
            "repo": repo,
            "scopes": list(scopes),
        }
        if any(payload.get(key) != value for key, value in expected_context.items()):
            raise ClaimError("delegation token parent/owner bağlamı eşleşmiyor")
        return VerifiedDelegation(
            delegation_id=delegation_id,
            parent_owner=token_owner,
            verification_method=DELEGATION_VERIFICATION_METHOD,
            expires_at=expires_at,
        )


def sign_delegation_token(
    *,
    secret: bytes,
    delegation_id: str,
    parent_claim_id: str,
    parent_owner: str,
    child_owner: str,
    child_task_id: str,
    repo: str,
    scopes: Sequence[str],
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    """Create a token in a trusted coordination service; the claim CLI never calls this."""
    payload = {
        "schema": DELEGATION_TOKEN_SCHEMA,
        "delegation_id": _clean_text(delegation_id, "delegation_id"),
        "verification_method": DELEGATION_VERIFICATION_METHOD,
        "parent_claim_id": _clean_text(parent_claim_id, "parent_claim_id"),
        "parent_owner": _clean_text(parent_owner, "parent_owner"),
        "child_owner": _clean_text(child_owner, "child_owner"),
        "child_task_id": _clean_text(child_task_id, "child_task_id"),
        "repo": _clean_text(repo, "repo"),
        "scopes": list(_normalize_scopes(scopes)),
        "issued_at": _format_time(issued_at),
        "expires_at": _format_time(expires_at),
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(secret, payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


@dataclass(frozen=True)
class TaskClaim:
    claim_id: str
    task_id: str
    repo: str
    branch: str
    worktree: str
    owner: str
    scopes: tuple[str, ...]
    status: ClaimStatus
    started_at: datetime
    heartbeat_at: datetime
    expires_at: datetime
    parent_claim_id: str | None = None
    pr_ref: str | None = None
    closed_at: datetime | None = None
    topics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "task_id": self.task_id,
            "repo": self.repo,
            "branch": self.branch,
            "worktree": self.worktree,
            "owner": self.owner,
            "scopes": list(self.scopes),
            "topics": list(self.topics),
            "status": self.status.value,
            "started_at": _format_time(self.started_at),
            "heartbeat_at": _format_time(self.heartbeat_at),
            "expires_at": _format_time(self.expires_at),
            "parent_claim_id": self.parent_claim_id,
            "pr_ref": self.pr_ref,
            "closed_at": _format_time(self.closed_at) if self.closed_at else None,
        }

    @classmethod
    def from_dict(cls, value: object) -> TaskClaim:
        if not isinstance(value, dict):
            raise ClaimStoreCorrupt("claim kaydı nesne değil")
        try:
            scopes = value["scopes"]
            if not isinstance(scopes, list) or not all(isinstance(v, str) for v in scopes):
                raise TypeError("invalid scopes")
            topics = value.get("topics", [])
            if not isinstance(topics, list) or not all(isinstance(v, str) for v in topics):
                raise TypeError("invalid topics")
            return cls(
                claim_id=_required_text(value, "claim_id"),
                task_id=_required_text(value, "task_id"),
                repo=_required_text(value, "repo"),
                branch=_required_text(value, "branch"),
                worktree=_required_text(value, "worktree"),
                owner=_required_text(value, "owner"),
                scopes=tuple(scopes),
                status=ClaimStatus(_required_text(value, "status")),
                started_at=_parse_time(_required_text(value, "started_at")),
                heartbeat_at=_parse_time(_required_text(value, "heartbeat_at")),
                expires_at=_parse_time(_required_text(value, "expires_at")),
                parent_claim_id=_optional_text(value, "parent_claim_id"),
                pr_ref=_optional_text(value, "pr_ref"),
                topics=tuple(topics),
                closed_at=(
                    _parse_time(_required_text(value, "closed_at"))
                    if value.get("closed_at") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ClaimStoreCorrupt("claim kaydı geçersiz") from exc


@dataclass(frozen=True)
class ClaimConflict:
    claim_id: str
    task_id: str
    owner: str
    reason: str
    scopes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "task_id": self.task_id,
            "owner": self.owner,
            "reason": self.reason,
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    claim: TaskClaim | None
    conflicts: tuple[ClaimConflict, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "claim": self.claim.to_dict() if self.claim else None,
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


class TaskClaimStore:
    """File-backed claim store serialized by an operating-system file lock."""

    def __init__(
        self,
        store_dir: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        override_verifier: OverrideApprovalVerifier | None = None,
        delegation_verifier: DelegationVerifier | None = None,
        published_ref: Callable[..., None] | None = None,
    ) -> None:
        self.store_dir = Path(store_dir)
        self.state_path = self.store_dir / "claims.json"
        self.audit_path = self.store_dir / "claim_events.jsonl"
        self.lock_path = self.store_dir / "claims.lock"
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._override_verifier = override_verifier
        self._delegation_verifier = delegation_verifier
        self._published_ref = published_ref or verify_published_work
        self._pending_events: list[dict[str, object]] = []

    def claim(
        self,
        *,
        task_id: str,
        repo: str,
        branch: str,
        worktree: str,
        owner: str,
        scopes: Sequence[str],
        ttl_seconds: int = 1800,
        queue_on_conflict: bool = False,
        parent_claim_id: str | None = None,
        delegation_token: str | None = None,
        override_token: str | None = None,
        override_reason: str | None = None,
        topics: Sequence[str] = (),
    ) -> ClaimResult:
        task_id = _clean_text(task_id, "task_id")
        repo = _clean_text(repo, "repo")
        branch = _clean_text(branch, "branch")
        worktree = _clean_text(worktree, "worktree")
        owner = _clean_text(owner, "owner")
        normalized_scopes = _normalize_scopes(scopes)
        normalized_topics = _normalize_topics(topics)
        if ttl_seconds <= 0:
            raise ClaimError("ttl_seconds sıfırdan büyük olmalı")
        if bool(override_token) != bool(override_reason):
            raise ClaimError("override için signed token ve reason birlikte zorunlu")
        # Devir kooperatif alt-claim, override insan-onaylı devralmadır;
        # birleşirse çocuk kendi parent'ını override edip aktif öksüz
        # kalabilir. İki mekanizma aynı istekte kullanılamaz.
        if parent_claim_id and override_token:
            raise ClaimError("devir (parent_claim_id) ve override aynı istekte birleştirilemez")
        if bool(parent_claim_id) != bool(delegation_token):
            raise ClaimError("alt görev için parent claim ve signed delegation token birlikte zorunlu")

        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            parent = None
            delegation = None
            if parent_claim_id:
                parent = _find_claim(claims, parent_claim_id)
                if parent is None or parent.status is not ClaimStatus.ACTIVE:
                    raise ClaimError("aktif parent claim bulunamadı")
                if repo != parent.repo or not _scopes_within(normalized_scopes, parent.scopes):
                    raise ClaimError("alt görev repo ve kapsamı parent claim içinde olmalı")
                if self._delegation_verifier is None:
                    raise ClaimError("delegation verifier yapılandırılmamış")
                delegation = self._delegation_verifier.verify(
                    delegation_token or "",
                    parent_claim_id=parent.claim_id,
                    parent_owner=parent.owner,
                    child_owner=owner,
                    child_task_id=task_id,
                    repo=repo,
                    scopes=normalized_scopes,
                    now=now,
                )

            conflicts = _find_conflicts(
                claims,
                task_id=task_id,
                repo=repo,
                scopes=normalized_scopes,
                topics=normalized_topics,
                parent_claim_id=parent.claim_id if parent else None,
            )
            conflict_records = tuple(
                _to_conflict(claim, task_id, normalized_scopes, normalized_topics) for claim in conflicts
            )
            overridden_claim_ids: list[str] = []
            if override_token and not conflicts:
                raise ClaimError("override yalnız aktif conflict için kullanılabilir")
            if conflicts and override_token:
                # Override yalnız ACTIVE lease'i devralır; QUEUED yer
                # tutucular ayrı approval gerektirmez, sıralarını koruyup
                # yeni sahibin arkasında beklemeye devam ederler.
                active_conflicts = [
                    item for item in conflicts if item.status is ClaimStatus.ACTIVE
                ]
                if len(active_conflicts) != 1:
                    raise ClaimError("tek approval birden fazla claim'i override edemez")
                if self._override_verifier is None:
                    raise ClaimError("override verifier yapılandırılmamış")
                reason = _clean_text(override_reason or "", "override_reason")
                conflict = active_conflicts[0]
                approval = self._override_verifier.verify(
                    override_token,
                    task_id=task_id,
                    current_owner=conflict.owner,
                    new_owner=owner,
                    reason=reason,
                    now=now,
                )
                replacement = replace(conflict, status=ClaimStatus.OVERRIDDEN, closed_at=now)
                claims[claims.index(conflict)] = replacement
                self._audit(
                    "CLAIM_OVERRIDDEN",
                    replacement,
                    actor=approval.approver_id,
                    at=now,
                    details={
                        "approval_id": approval.approval_id,
                        "approver_id": approval.approver_id,
                        "verification_method": approval.verification_method,
                        "verified_at": _format_time(now),
                        "reason": reason,
                        "previous_owner": conflict.owner,
                        "new_owner": owner,
                    },
                )
                # Başarılı override sonrası çağıran engellenmiş sayılmaz;
                # override edilen kayıt audit'te ve details'te izlenir.
                overridden_claim_ids = [conflict.claim_id]
                self._close_orphaned_children(claims, now)
                conflicts = []
                conflict_records = ()
            elif conflicts and not queue_on_conflict:
                return ClaimResult(accepted=False, claim=None, conflicts=conflict_records)

            status = ClaimStatus.QUEUED if conflicts else ClaimStatus.ACTIVE
            claim = TaskClaim(
                claim_id=str(uuid.uuid4()),
                task_id=task_id,
                repo=repo,
                branch=branch,
                worktree=worktree,
                owner=owner,
                scopes=normalized_scopes,
                status=status,
                started_at=now,
                heartbeat_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
                parent_claim_id=parent_claim_id,
                topics=normalized_topics,
            )
            claims.append(claim)
            acquire_details: dict[str, object] = {
                "conflicts": [item.claim_id for item in conflict_records]
            }
            if overridden_claim_ids:
                acquire_details["overridden"] = overridden_claim_ids
            if delegation:
                acquire_details["delegation"] = {
                    "delegation_id": delegation.delegation_id,
                    "parent_claim_id": parent_claim_id,
                    "parent_owner": delegation.parent_owner,
                    "verification_method": delegation.verification_method,
                    "verified_at": _format_time(now),
                }
            self._audit(
                "CLAIM_QUEUED" if status is ClaimStatus.QUEUED else "CLAIM_ACQUIRED",
                claim,
                actor=owner,
                at=now,
                details=acquire_details,
            )
            if overridden_claim_ids:
                # Override bir blocker kapattı: yalnız eski lease'e takılan
                # bekleyenler yeni claim eklendikten sonra terfi edebilmeli.
                self._promote_queued(claims, now)
            return ClaimResult(accepted=status is ClaimStatus.ACTIVE, claim=claim, conflicts=conflict_records)

    def heartbeat(self, claim_id: str, *, owner: str, ttl_seconds: int = 1800) -> TaskClaim:
        if ttl_seconds <= 0:
            raise ClaimError("ttl_seconds sıfırdan büyük olmalı")
        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            claim = _require_owned_active(claims, claim_id, owner)
            updated = replace(
                claim,
                heartbeat_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            claims[claims.index(claim)] = updated
            self._audit("CLAIM_HEARTBEAT", updated, actor=owner, at=now)
            return updated

    def release(self, claim_id: str, *, owner: str) -> TaskClaim:
        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            claim = _require_owned_open(claims, claim_id, owner)
            updated = replace(claim, status=ClaimStatus.RELEASED, closed_at=now)
            claims[claims.index(claim)] = updated
            self._audit("CLAIM_RELEASED", updated, actor=owner, at=now)
            self._close_orphaned_children(claims, now)
            self._promote_queued(claims, now)
            return updated

    def attach_pr(self, claim_id: str, *, owner: str, pr_ref: str) -> TaskClaim:
        pr_ref = _clean_text(pr_ref, "pr_ref")
        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            claim = _require_owned_open(claims, claim_id, owner)
            updated = replace(claim, pr_ref=pr_ref)
            claims[claims.index(claim)] = updated
            self._audit("CLAIM_PR_ATTACHED", updated, actor=owner, at=now, details={"pr_ref": pr_ref})
            return updated

    def record_result(
        self,
        claim_id: str,
        *,
        owner: str,
        commit: str,
        tree: str,
        branch: str,
        tests: Mapping[str, object],
    ) -> TaskClaim:
        """Record a verifiable result. Does not transfer the claim."""
        return self._record_delivery(
            claim_id,
            owner=owner,
            commit=commit,
            tree=tree,
            branch=branch,
            tests=tests,
            to_owner=None,
            ttl_seconds=0,
        )

    def handoff(
        self,
        claim_id: str,
        *,
        owner: str,
        to_owner: str,
        commit: str,
        tree: str,
        branch: str,
        tests: Mapping[str, object],
        ttl_seconds: int = 1800,
    ) -> TaskClaim:
        """Record a handoff and move the live lease to ``to_owner``."""
        if ttl_seconds <= 0:
            raise ClaimError("ttl_seconds sıfırdan büyük olmalı")
        return self._record_delivery(
            claim_id,
            owner=owner,
            commit=commit,
            tree=tree,
            branch=branch,
            tests=tests,
            to_owner=_clean_text(to_owner, "to_owner"),
            ttl_seconds=ttl_seconds,
        )

    def list_claims(self, *, include_closed: bool = False) -> tuple[TaskClaim, ...]:
        # Read-only projection: a lease past expires_at is EXPIRED here even
        # when the stored status is still ACTIVE. This path does not write.
        claims = self._read_state() if self.state_path.exists() else []
        return project_claims(claims, self._now(), include_closed=include_closed)

    def _record_delivery(
        self,
        claim_id: str,
        *,
        owner: str,
        commit: str,
        tree: str,
        branch: str,
        tests: Mapping[str, object],
        to_owner: str | None,
        ttl_seconds: int,
    ) -> TaskClaim:
        owner = _clean_text(owner, "owner")
        commit = _clean_text(commit, "commit").lower()
        tree = _clean_text(tree, "tree").lower()
        branch = _clean_text(branch, "branch")
        test_record = _normalize_tests(tests)
        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            claim = _require_owned_active(claims, claim_id, owner)
            if branch != claim.branch:
                raise ClaimError("sonuç dalı claim dalı ile aynı olmalı")
            self._published_ref(repo=claim.repo, branch=branch, commit=commit, tree=tree)
            details: dict[str, object] = {
                "commit": commit,
                "tree": tree,
                "branch": branch,
                "tests": test_record,
            }
            if to_owner is None:
                self._audit("CLAIM_RESULT", claim, actor=owner, at=now, details=details)
                return claim
            if to_owner == owner:
                raise ClaimError("devir alan ajan farklı olmalı")
            updated = replace(
                claim,
                owner=to_owner,
                heartbeat_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            claims[claims.index(claim)] = updated
            details["from_owner"] = owner
            details["to_owner"] = to_owner
            self._audit("CLAIM_HANDOFF", updated, actor=owner, at=now, details=details)
            return updated

    @contextmanager
    def _locked_state(self) -> Iterator[list[TaskClaim]]:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            claims = self._read_state()
            self._pending_events = []
            try:
                yield claims
            except Exception:
                # Geri alınan işlem audit izi bırakmaz; bekleyen olaylar düşer.
                self._pending_events = []
                raise
            else:
                self._write_state(claims)
                self._flush_audit()
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_state(self) -> list[TaskClaim]:
        if not self.state_path.exists():
            return []
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimStoreCorrupt("claim deposu okunamıyor") from exc
        if not isinstance(payload, dict) or payload.get("schema") != CLAIM_STORE_SCHEMA:
            raise ClaimStoreCorrupt("claim deposu şeması geçersiz")
        values = payload.get("claims")
        if not isinstance(values, list):
            raise ClaimStoreCorrupt("claim listesi geçersiz")
        return [TaskClaim.from_dict(value) for value in values]

    def _write_state(self, claims: Sequence[TaskClaim]) -> None:
        payload = {
            "schema": CLAIM_STORE_SCHEMA,
            "claims": [claim.to_dict() for claim in claims],
        }
        fd, temporary_name = tempfile.mkstemp(prefix="claims.", suffix=".tmp", dir=self.store_dir)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.state_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _expire_stale(self, claims: list[TaskClaim], now: datetime) -> None:
        for index, claim in enumerate(claims):
            if claim.status is ClaimStatus.ACTIVE and claim.expires_at <= now:
                expired = replace(claim, status=ClaimStatus.EXPIRED, closed_at=now)
                claims[index] = expired
                self._audit("CLAIM_EXPIRED", expired, actor="lumos-board", at=now)
        self._close_orphaned_children(claims, now)
        self._promote_queued(claims, now)

    def _close_orphaned_children(self, claims: list[TaskClaim], now: datetime) -> None:
        """Parent'ı artık ACTIVE olmayan ACTIVE/QUEUED alt-claim'leri kapatır.

        Devir modeli "alt görev parent lease'i içinde yaşar" der; parent
        kapanınca çocuklar kapsam tutmaya devam edemez. Kaskad, torunları da
        kapsasın diye sabit noktaya kadar tekrarlanır.
        """
        changed = True
        while changed:
            changed = False
            by_id = {claim.claim_id: claim for claim in claims}
            for index, claim in enumerate(claims):
                if claim.status not in {ClaimStatus.ACTIVE, ClaimStatus.QUEUED}:
                    continue
                if not claim.parent_claim_id:
                    continue
                parent = by_id.get(claim.parent_claim_id)
                if parent is not None and parent.status is ClaimStatus.ACTIVE:
                    continue
                orphaned = replace(claim, status=ClaimStatus.EXPIRED, closed_at=now)
                claims[index] = orphaned
                self._audit(
                    "CLAIM_EXPIRED",
                    orphaned,
                    actor="lumos-board",
                    at=now,
                    details={"reason": "parent_closed", "parent_claim_id": claim.parent_claim_id},
                )
                changed = True

    def _promote_queued(self, claims: list[TaskClaim], now: datetime) -> None:
        """Engeli kalkan QUEUED claim'leri sıra (started_at) düzeninde aktifleştirir.

        Kuyruk yer tutar: yeni bir claim, önündeki QUEUED kayıtları da engel
        olarak görür; boşalan slotu her zaman en eski kuyruk kaydı alır.
        """
        # Pozisyon bazlı değiştirme: terfiler liste girdilerini yerinde
        # güncellediği için adaylar eşitlikle değil indeksle bulunur.
        queued = sorted(
            (
                (index, claim)
                for index, claim in enumerate(claims)
                if claim.status is ClaimStatus.QUEUED
            ),
            key=lambda item: (item[1].started_at, item[1].claim_id),
        )
        for candidate_index, candidate in queued:
            candidate_rank = (candidate.started_at, candidate.claim_id)
            # Engel yalnız aktif kayıtlar ve sırada daha önde bekleyenlerdir;
            # arkadaki kuyruk kayıtları öndekinin terfisini kilitleyemez.
            visible = [
                claim
                for claim in claims
                if claim.status is ClaimStatus.ACTIVE
                or (
                    claim.status is ClaimStatus.QUEUED
                    and (claim.started_at, claim.claim_id) < candidate_rank
                )
            ]
            blockers = _find_conflicts(
                visible,
                task_id=candidate.task_id,
                repo=candidate.repo,
                scopes=candidate.scopes,
                topics=candidate.topics,
                parent_claim_id=candidate.parent_claim_id,
                exclude_claim_id=candidate.claim_id,
            )
            if blockers:
                continue
            promoted = replace(
                candidate,
                status=ClaimStatus.ACTIVE,
                heartbeat_at=now,
                expires_at=now + (candidate.expires_at - candidate.started_at),
            )
            claims[candidate_index] = promoted
            self._audit("CLAIM_PROMOTED", promoted, actor=promoted.owner, at=now)

    def _audit(
        self,
        event_type: str,
        claim: TaskClaim,
        *,
        actor: str,
        at: datetime,
        details: dict[str, object] | None = None,
    ) -> None:
        event = {
            "schema": CLAIM_EVENT_SCHEMA,
            "event": event_type,
            "at": _format_time(at),
            "claim_id": claim.claim_id,
            "task_id": claim.task_id,
            "repo": claim.repo,
            "owner": claim.owner,
            "actor": actor,
            "details": details or {},
        }
        # Durum kalıcılaşmadan audit yazılmaz (bkz. sözleşme kural 11);
        # olaylar _locked_state başarıyla kapanınca _flush_audit ile yazılır.
        self._pending_events.append(event)

    def _flush_audit(self) -> None:
        if not self._pending_events:
            return
        with self.audit_path.open("a", encoding="utf-8") as handle:
            for event in self._pending_events:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._pending_events = []

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ClaimError("clock timezone içermeli")
        return value.astimezone(timezone.utc)


def _clean_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimError(f"{field} boş olamaz")
    return value.strip()


def _required_text(value: dict[str, object], field: str) -> str:
    item = value[field]
    if not isinstance(item, str) or not item:
        raise TypeError(field)
    return item


def _optional_text(value: dict[str, object], field: str) -> str | None:
    item = value.get(field)
    if item is None:
        return None
    if not isinstance(item, str) or not item:
        raise TypeError(field)
    return item


def project_claims(
    claims: Sequence[TaskClaim], now: datetime, *, include_closed: bool
) -> tuple[TaskClaim, ...]:
    """Show a past lease as EXPIRED without writing the store."""
    projected: list[TaskClaim] = []
    by_id = {claim.claim_id: claim for claim in claims}
    for claim in claims:
        status = claim.status
        if status is ClaimStatus.ACTIVE and claim.expires_at <= now:
            status = ClaimStatus.EXPIRED
        if status in {ClaimStatus.ACTIVE, ClaimStatus.QUEUED} and claim.parent_claim_id:
            parent = by_id.get(claim.parent_claim_id)
            parent_status = parent.status if parent is not None else None
            if parent is not None and parent.status is ClaimStatus.ACTIVE and parent.expires_at <= now:
                parent_status = ClaimStatus.EXPIRED
            if parent_status is not ClaimStatus.ACTIVE:
                status = ClaimStatus.EXPIRED
        if status is not claim.status:
            claim = replace(claim, status=status)
        projected.append(claim)
    if not include_closed:
        projected = [
            claim
            for claim in projected
            if claim.status in {ClaimStatus.ACTIVE, ClaimStatus.QUEUED}
        ]
    return tuple(sorted(projected, key=lambda item: (item.started_at, item.claim_id)))


def verify_published_work(*, repo: str, branch: str, commit: str, tree: str) -> None:
    """Reject completed work whose branch is absent or does not match the commit."""
    if repo != "lumos-core":
        raise ClaimError("bu depo için dal doğrulaması yok")
    if not _SHA40.fullmatch(commit) or not _SHA40.fullmatch(tree):
        raise ClaimError("commit ve tree tam SHA olmalı")
    if not _BRANCH_NAME.fullmatch(branch) or ".." in branch.split("/"):
        raise ClaimError("dal adı geçersiz")
    ref = f"refs/heads/{branch}"
    listed = subprocess.run(
        ["git", "ls-remote", "origin", ref],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if listed.returncode != 0:
        raise ClaimError("dal doğrulanamadı")
    shas = [line.split()[0] for line in listed.stdout.splitlines() if line.strip()]
    if shas != [commit]:
        raise ClaimError("dal GitHub'da yok veya bildirilen commit değil")
    kind = subprocess.run(
        ["git", "cat-file", "-t", f"{commit}^{{tree}}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if kind.returncode != 0:
        fetched = subprocess.run(
            ["git", "fetch", "--no-tags", "--depth", "1", "origin", ref],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if fetched.returncode != 0:
            raise ClaimError("commit alınamadı")
        kind = subprocess.run(
            ["git", "cat-file", "-t", f"{commit}^{{tree}}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    if kind.returncode != 0 or kind.stdout.strip() != "tree":
        raise ClaimError("commit ağacı okunamadı")
    shown = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{tree}}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if shown.returncode != 0 or shown.stdout.strip() != tree:
        raise ClaimError("tree bildirilen commit ile uyuşmuyor")


def _normalize_topics(topics: Sequence[str] | None) -> tuple[str, ...]:
    if not topics:
        return ()
    normalized: set[str] = set()
    for raw in topics:
        topic = _clean_text(raw, "topic")
        if not _TOPIC_NAME.fullmatch(topic):
            raise ClaimError("konu açık bir belirteç olmalı")
        normalized.add(topic)
    return tuple(sorted(normalized))


def _normalize_tests(tests: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(tests, dict) or set(tests) != {"command", "passed", "failed", "skipped"}:
        raise ClaimError("test sonucu command, passed, failed, skipped alanlarını taşımalı")
    command = tests["command"]
    if not isinstance(command, str) or not command.strip():
        raise ClaimError("tests.command boş olamaz")
    counts: dict[str, int] = {}
    for key in ("passed", "failed", "skipped"):
        value = tests[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ClaimError(f"tests.{key} sıfır veya daha büyük tam sayı olmalı")
        counts[key] = value
    return {
        "command": command.strip(),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
    }


def _normalize_scopes(scopes: Sequence[str]) -> tuple[str, ...]:
    if not scopes:
        raise ClaimError("en az bir kapsam zorunlu")
    normalized: set[str] = set()
    for raw_scope in scopes:
        scope = _clean_text(raw_scope, "scope").replace("\\", "/")
        path = PurePosixPath(scope)
        if path.is_absolute() or ".." in path.parts:
            raise ClaimError("kapsam repo-relative olmalı")
        cleaned = str(path)
        if cleaned in {"", "."}:
            raise ClaimError("repo kökü kapsam olarak alınamaz")
        normalized.add(cleaned.rstrip("/"))
    return tuple(sorted(normalized))


def _scope_overlap(left: str, right: str) -> bool:
    left_path = PurePosixPath(left)
    right_path = PurePosixPath(right)
    return left_path == right_path or left_path in right_path.parents or right_path in left_path.parents


def _scopes_within(child: Sequence[str], parent: Sequence[str]) -> bool:
    return all(any(scope == root or PurePosixPath(root) in PurePosixPath(scope).parents for root in parent) for scope in child)


def _find_conflicts(
    claims: Sequence[TaskClaim],
    *,
    task_id: str,
    repo: str,
    scopes: Sequence[str],
    parent_claim_id: str | None,
    topics: Sequence[str] = (),
    exclude_claim_id: str | None = None,
) -> list[TaskClaim]:
    conflicts: list[TaskClaim] = []
    declared_topics = set(topics)
    for claim in claims:
        # QUEUED kayıtlar da yer tutar: kuyruktaki ajan sırasını kaybetmez.
        if claim.status not in {ClaimStatus.ACTIVE, ClaimStatus.QUEUED} or claim.repo != repo:
            continue
        if claim.claim_id == exclude_claim_id:
            continue
        duplicate_task = claim.task_id == task_id
        if claim.claim_id == parent_claim_id:
            # Devir, parent kapsamı İÇİNDE çalışmaya izin verir; aynı görev
            # kimliğinin ikinci kez aktifleşmesine izin vermez.
            if duplicate_task:
                conflicts.append(claim)
            continue
        scope_collision = any(_scope_overlap(left, right) for left in scopes for right in claim.scopes)
        # Yalnız iki tarafta da açıkça yazılmış konular çakışır. Boş konu
        # listesi yeni işi engellemez.
        topic_collision = bool(declared_topics & set(claim.topics))
        if duplicate_task or scope_collision or topic_collision:
            conflicts.append(claim)
    return conflicts


def _to_conflict(
    claim: TaskClaim, task_id: str, scopes: Sequence[str], topics: Sequence[str] = ()
) -> ClaimConflict:
    scope_hit = tuple(scope for scope in claim.scopes if any(_scope_overlap(scope, item) for item in scopes))
    topic_hit = tuple(sorted(set(claim.topics) & set(topics)))
    if claim.task_id == task_id:
        reason = "DUPLICATE_TASK"
        overlap = scope_hit
    elif scope_hit:
        reason = "SCOPE_CONFLICT"
        overlap = scope_hit
    else:
        reason = "TOPIC_CONFLICT"
        overlap = topic_hit
    return ClaimConflict(claim.claim_id, claim.task_id, claim.owner, reason, overlap)


def _find_claim(claims: Sequence[TaskClaim], claim_id: str) -> TaskClaim | None:
    return next((claim for claim in claims if claim.claim_id == claim_id), None)


def _require_owned_active(claims: Sequence[TaskClaim], claim_id: str, owner: str) -> TaskClaim:
    claim = _require_owned_open(claims, claim_id, owner)
    if claim.status is not ClaimStatus.ACTIVE:
        raise ClaimError("claim aktif değil")
    return claim


def _require_owned_open(claims: Sequence[TaskClaim], claim_id: str, owner: str) -> TaskClaim:
    claim = _find_claim(claims, _clean_text(claim_id, "claim_id"))
    if claim is None or claim.status not in {ClaimStatus.ACTIVE, ClaimStatus.QUEUED}:
        raise ClaimError("açık claim bulunamadı")
    if claim.owner != _clean_text(owner, "owner"):
        raise ClaimError("claim sahibi eşleşmiyor")
    return claim


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
