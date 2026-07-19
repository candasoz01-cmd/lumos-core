"""Atomic task claims for the Lumos Board orchestration surface."""

from __future__ import annotations

import fcntl
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
    ) -> None:
        self.store_dir = Path(store_dir)
        self.state_path = self.store_dir / "claims.json"
        self.audit_path = self.store_dir / "claim_events.jsonl"
        self.lock_path = self.store_dir / "claims.lock"
        self._clock = clock or (lambda: datetime.now(timezone.utc))

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
        override_approved_by: str | None = None,
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
        if bool(override_approved_by) != bool(override_reason):
            raise ClaimError("override için approved_by ve reason birlikte zorunlu")

        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            parent = None
            if parent_claim_id:
                parent = _find_claim(claims, parent_claim_id)
                if parent is None or parent.status is not ClaimStatus.ACTIVE:
                    raise ClaimError("aktif parent claim bulunamadı")
                if delegated_by != parent.owner:
                    raise ClaimError("alt görevi yalnız mevcut claim sahibi devredebilir")
                if repo != parent.repo or not _scopes_within(normalized_scopes, parent.scopes):
                    raise ClaimError("alt görev repo ve kapsamı parent claim içinde olmalı")

            conflicts = _find_conflicts(
                claims,
                task_id=task_id,
                repo=repo,
                scopes=normalized_scopes,
                ignored_claim_id=parent.claim_id if parent else None,
            )
            conflict_records = tuple(_to_conflict(claim, task_id, normalized_scopes) for claim in conflicts)
            if conflicts and override_approved_by:
                approved_by = _clean_text(override_approved_by, "override_approved_by")
                reason = _clean_text(override_reason or "", "override_reason")
                for conflict in conflicts:
                    replacement = replace(conflict, status=ClaimStatus.OVERRIDDEN, closed_at=now)
                    claims[claims.index(conflict)] = replacement
                    self._audit(
                        "CLAIM_OVERRIDDEN",
                        replacement,
                        actor=approved_by,
                        at=now,
                        details={"reason": reason, "new_owner": owner},
                    )
                conflicts = []
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
            self._audit(
                "CLAIM_QUEUED" if status is ClaimStatus.QUEUED else "CLAIM_ACQUIRED",
                claim,
                actor=owner,
                at=now,
                details={"conflicts": [item.claim_id for item in conflict_records]},
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
            try:
                yield claims
            except Exception:
                raise
            else:
                self._write_state(claims)
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
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

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
    ignored_claim_id: str | None,
) -> list[TaskClaim]:
    conflicts: list[TaskClaim] = []
    for claim in claims:
        if claim.status is not ClaimStatus.ACTIVE or claim.repo != repo or claim.claim_id == ignored_claim_id:
            continue
        duplicate_task = claim.task_id == task_id
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
