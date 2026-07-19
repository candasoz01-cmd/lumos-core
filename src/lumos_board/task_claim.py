"""Atomic task claims for the Lumos Board orchestration surface."""

from __future__ import annotations

import fcntl
import base64
import hashlib
import hmac
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator, Sequence


CLAIM_STORE_SCHEMA = "lumos.task_claim_store.v1"
CLAIM_EVENT_SCHEMA = "lumos.task_claim_event.v1"
APPROVER_REGISTRY_SCHEMA = "lumos.override_approver_registry.v1"
OVERRIDE_APPROVAL_SCHEMA = "lumos.override_approval.v1"
OVERRIDE_VERIFICATION_METHOD = "HMAC_SHA256_ALLOWLIST"


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

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "task_id": self.task_id,
            "repo": self.repo,
            "branch": self.branch,
            "worktree": self.worktree,
            "owner": self.owner,
            "scopes": list(self.scopes),
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
    ) -> None:
        self.store_dir = Path(store_dir)
        self.state_path = self.store_dir / "claims.json"
        self.audit_path = self.store_dir / "claim_events.jsonl"
        self.lock_path = self.store_dir / "claims.lock"
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._override_verifier = override_verifier
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
        delegated_by: str | None = None,
        override_token: str | None = None,
        override_reason: str | None = None,
    ) -> ClaimResult:
        task_id = _clean_text(task_id, "task_id")
        repo = _clean_text(repo, "repo")
        branch = _clean_text(branch, "branch")
        worktree = _clean_text(worktree, "worktree")
        owner = _clean_text(owner, "owner")
        normalized_scopes = _normalize_scopes(scopes)
        if ttl_seconds <= 0:
            raise ClaimError("ttl_seconds sıfırdan büyük olmalı")
        if bool(override_token) != bool(override_reason):
            raise ClaimError("override için signed token ve reason birlikte zorunlu")

        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            parent = None
            if parent_claim_id:
                parent = _find_claim(claims, parent_claim_id)
                if parent is None or parent.status is not ClaimStatus.ACTIVE:
                    raise ClaimError("aktif parent claim bulunamadı")
                # GÜVEN SINIRI (v1): depo, owner dahil bütün kimlikleri
                # self-asserted kabul eder; delegated_by da bu sınırın
                # içindedir ve kriptografik olarak doğrulanmaz. Çağıran
                # kimliğinin gerçek doğrulaması bilinçli olarak coordination
                # gateway katmanına (KA-003) bırakılmıştır — ortak dosyada
                # saklanacak her per-claim secret tüm ajanlarca okunabilir
                # olacağı için burada sahte bir güvence üretilmez.
                if delegated_by != parent.owner:
                    raise ClaimError("alt görevi yalnız mevcut claim sahibi devredebilir")
                if repo != parent.repo or not _scopes_within(normalized_scopes, parent.scopes):
                    raise ClaimError("alt görev repo ve kapsamı parent claim içinde olmalı")

            conflicts = _find_conflicts(
                claims,
                task_id=task_id,
                repo=repo,
                scopes=normalized_scopes,
                parent_claim_id=parent.claim_id if parent else None,
            )
            conflict_records = tuple(_to_conflict(claim, task_id, normalized_scopes) for claim in conflicts)
            overridden_claim_ids: list[str] = []
            if override_token and not conflicts:
                raise ClaimError("override yalnız aktif conflict için kullanılabilir")
            if conflicts and override_token:
                if len(conflicts) != 1:
                    raise ClaimError("tek approval birden fazla claim'i override edemez")
                if self._override_verifier is None:
                    raise ClaimError("override verifier yapılandırılmamış")
                reason = _clean_text(override_reason or "", "override_reason")
                conflict = conflicts[0]
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
            )
            claims.append(claim)
            acquire_details: dict[str, object] = {
                "conflicts": [item.claim_id for item in conflict_records]
            }
            if overridden_claim_ids:
                acquire_details["overridden"] = overridden_claim_ids
            self._audit(
                "CLAIM_QUEUED" if status is ClaimStatus.QUEUED else "CLAIM_ACQUIRED",
                claim,
                actor=owner,
                at=now,
                details=acquire_details,
            )
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

    def list_claims(self, *, include_closed: bool = False) -> tuple[TaskClaim, ...]:
        with self._locked_state() as claims:
            self._expire_stale(claims, self._now())
            selected = claims if include_closed else [
                claim for claim in claims if claim.status in {ClaimStatus.ACTIVE, ClaimStatus.QUEUED}
            ]
            return tuple(sorted(selected, key=lambda item: (item.started_at, item.claim_id)))

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
        queued = sorted(
            (claim for claim in claims if claim.status is ClaimStatus.QUEUED),
            key=lambda item: (item.started_at, item.claim_id),
        )
        for candidate in queued:
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
            claims[claims.index(candidate)] = promoted
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
    exclude_claim_id: str | None = None,
) -> list[TaskClaim]:
    conflicts: list[TaskClaim] = []
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
        if duplicate_task or scope_collision:
            conflicts.append(claim)
    return conflicts


def _to_conflict(claim: TaskClaim, task_id: str, scopes: Sequence[str]) -> ClaimConflict:
    reason = "DUPLICATE_TASK" if claim.task_id == task_id else "SCOPE_CONFLICT"
    overlap = tuple(scope for scope in claim.scopes if any(_scope_overlap(scope, item) for item in scopes))
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
