"""Duvar onay şeması v1 kayıt deposu (lumos-wall-v1 § Onay şeması v1).

Altı zorunlu alan: ``approval_id``, ``task``, ``gate``, ``action``,
``head_sha``, ``approved_by``. Boş ``approved_by`` bekleyen kayıttır;
onay yalnız fail-closed kurucu/onaycı registry'sindeki bir insan kimliğiyle
verilebilir. Claim override HMAC'i (lease devralma) bu şemanın uygulaması
değildir ve burada genişletilmez. İmza servisi, GitHub CheckRun veya yayın
güvenlik kökü bu modülün kapsamı dışıdır.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Sequence

from lumos_board.task_claim import (
    ClaimError,
    ClaimStoreCorrupt,
    _clean_text,
    _format_time,
    _optional_text,
    _parse_time,
    _required_text,
)

FOUNDER_APPROVAL_SCHEMA = "lumos.founder_approval.v1"
FOUNDER_APPROVAL_STORE_SCHEMA = "lumos.founder_approval_store.v1"
FOUNDER_APPROVAL_EVENT_SCHEMA = "lumos.founder_approval_event.v1"
FOUNDER_APPROVER_REGISTRY_SCHEMA = "lumos.founder_approver_registry.v1"

# GitHub'ın bot/App kimlik biçimleri insan onayı sayılmaz (sözleşme: "Ajan,
# bot veya App bu alanı insan onayı olarak dolduramaz").
_NON_HUMAN_MARKERS = ("[bot]",)
_NON_HUMAN_PREFIXES = ("app/",)


class FounderApproverRegistry:
    """Fail-closed insan onaycı allowlist'i; boş veya bozuk registry onay veremez."""

    def __init__(self, approvers: dict[str, datetime]) -> None:
        if not approvers:
            raise ClaimError("founder approver allowlist boş olamaz")
        self._approvers = dict(approvers)

    @classmethod
    def from_registry_file(cls, path: Path) -> FounderApproverRegistry:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimError("founder approver registry okunamıyor") from exc
        if not isinstance(payload, dict) or payload.get("schema") != FOUNDER_APPROVER_REGISTRY_SCHEMA:
            raise ClaimError("founder approver registry şeması geçersiz")
        entries = payload.get("approvers")
        if not isinstance(entries, list):
            raise ClaimError("founder approver listesi geçersiz")
        approvers: dict[str, datetime] = {}
        try:
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("enabled") is not True:
                    continue
                approver_id = _required_text(entry, "approver_id")
                if approver_id in approvers:
                    raise ClaimError("founder approver registry tekrarlı kimlik içeriyor")
                approvers[approver_id] = _parse_time(_required_text(entry, "valid_until"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ClaimError("founder approver registry kaydı geçersiz") from exc
        return cls(approvers)

    def require_human(self, approver_id: str, *, now: datetime) -> str:
        approver_id = _clean_text(approver_id, "approved_by")
        lowered = approver_id.lower()
        if any(marker in lowered for marker in _NON_HUMAN_MARKERS) or any(
            lowered.startswith(prefix) for prefix in _NON_HUMAN_PREFIXES
        ):
            raise ClaimError("approved_by insan onayı olmalı; bot/App kimliği kabul edilmez")
        valid_until = self._approvers.get(approver_id)
        if valid_until is None or valid_until <= now:
            raise ClaimError("approved_by founder approver allowlist'inde geçerli değil")
        return approver_id


@dataclass(frozen=True)
class FounderApproval:
    approval_id: str
    task: str
    gate: str
    action: str
    head_sha: str
    approved_by: str | None
    recorded_at: datetime
    approved_at: datetime | None = None

    @property
    def is_approved(self) -> bool:
        return bool(self.approved_by)

    def matches(self, *, task: str, gate: str, action: str, head_sha: str) -> bool:
        # Head değişince sayaç sıfırlanır: eşleşme dört alan üzerinden ve tamdır.
        return (
            self.task == task
            and self.gate == gate
            and self.action == action
            and self.head_sha == head_sha
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": FOUNDER_APPROVAL_SCHEMA,
            "approval_id": self.approval_id,
            "task": self.task,
            "gate": self.gate,
            "action": self.action,
            "head_sha": self.head_sha,
            "approved_by": self.approved_by,
            "recorded_at": _format_time(self.recorded_at),
            "approved_at": _format_time(self.approved_at) if self.approved_at else None,
        }

    @classmethod
    def from_dict(cls, value: object) -> FounderApproval:
        if not isinstance(value, dict):
            raise ClaimStoreCorrupt("onay kaydı nesne değil")
        try:
            if value.get("schema") != FOUNDER_APPROVAL_SCHEMA:
                raise ValueError("schema")
            approved_by = _optional_text(value, "approved_by")
            approved_at = (
                _parse_time(_required_text(value, "approved_at"))
                if value.get("approved_at") is not None
                else None
            )
            if bool(approved_by) != bool(approved_at):
                raise ValueError("approved_by/approved_at tutarsız")
            return cls(
                approval_id=_required_text(value, "approval_id"),
                task=_required_text(value, "task"),
                gate=_required_text(value, "gate"),
                action=_required_text(value, "action"),
                head_sha=_required_text(value, "head_sha"),
                approved_by=approved_by,
                recorded_at=_parse_time(_required_text(value, "recorded_at")),
                approved_at=approved_at,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ClaimStoreCorrupt("onay kaydı geçersiz") from exc


class FounderApprovalStore:
    """File-backed, append-only denetim izli Duvar onay kaydı deposu.

    Claim deposunun çatalı değildir: lease, TTL veya kapsam tutmaz; yalnız
    kurucu kararlarının kaydını üretir ve okur.
    """

    def __init__(
        self,
        store_dir: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        registry: FounderApproverRegistry | None = None,
    ) -> None:
        self.store_dir = Path(store_dir)
        self.state_path = self.store_dir / "founder_approvals.json"
        self.audit_path = self.store_dir / "founder_approval_events.jsonl"
        self.lock_path = self.store_dir / "founder_approvals.lock"
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._registry = registry
        self._pending_events: list[dict[str, object]] = []

    def request(self, *, task: str, gate: str, action: str, head_sha: str) -> FounderApproval:
        """Kayıt açar veya mevcut kaydı döndürür; aynı geçerli onay tekrar sorulmaz."""
        task = _clean_text(task, "task")
        gate = _clean_text(gate, "gate")
        action = _clean_text(action, "action")
        head_sha = _clean_text(head_sha, "head_sha")
        with self._locked_state() as approvals:
            now = self._now()
            existing = _find_match(approvals, task=task, gate=gate, action=action, head_sha=head_sha)
            if existing is not None:
                return existing
            approval = FounderApproval(
                approval_id=str(uuid.uuid4()),
                task=task,
                gate=gate,
                action=action,
                head_sha=head_sha,
                approved_by=None,
                recorded_at=now,
            )
            approvals.append(approval)
            self._audit("APPROVAL_REQUESTED", approval, actor="lumos-board", at=now)
            return approval

    def grant(self, approval_id: str, *, approved_by: str) -> FounderApproval:
        """Bekleyen kaydı insan onayıyla kapatır; registry yoksa fail-closed."""
        if self._registry is None:
            raise ClaimError("founder approver registry yapılandırılmamış; onay verilemez")
        with self._locked_state() as approvals:
            now = self._now()
            approver = self._registry.require_human(approved_by, now=now)
            approval = _find_by_id(approvals, _clean_text(approval_id, "approval_id"))
            if approval is None:
                raise ClaimError("onay kaydı bulunamadı")
            if approval.is_approved:
                raise ClaimError("onay kaydı zaten kapatılmış; yeni karar yeni kayıttır")
            updated = replace(approval, approved_by=approver, approved_at=now)
            approvals[approvals.index(approval)] = updated
            self._audit("APPROVAL_GRANTED", updated, actor=approver, at=now)
            return updated

    def check(self, *, task: str, gate: str, action: str, head_sha: str) -> FounderApproval | None:
        """Geçerli (approved_by dolu) onayı döndürür; yoksa None (fail-closed)."""
        task = _clean_text(task, "task")
        gate = _clean_text(gate, "gate")
        action = _clean_text(action, "action")
        head_sha = _clean_text(head_sha, "head_sha")
        with self._locked_state() as approvals:
            match = _find_match(approvals, task=task, gate=gate, action=action, head_sha=head_sha)
            if match is not None and match.is_approved:
                return match
            return None

    def list_approvals(self) -> tuple[FounderApproval, ...]:
        with self._locked_state() as approvals:
            return tuple(sorted(approvals, key=lambda item: (item.recorded_at, item.approval_id)))

    @contextmanager
    def _locked_state(self) -> Iterator[list[FounderApproval]]:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            approvals = self._read_state()
            self._pending_events = []
            try:
                yield approvals
            except Exception:
                # Geri alınan işlem audit izi bırakmaz; bekleyen olaylar düşer.
                self._pending_events = []
                raise
            else:
                self._write_state(approvals)
                self._flush_audit()
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_state(self) -> list[FounderApproval]:
        if not self.state_path.exists():
            return []
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimStoreCorrupt("onay deposu okunamıyor") from exc
        if not isinstance(payload, dict) or payload.get("schema") != FOUNDER_APPROVAL_STORE_SCHEMA:
            raise ClaimStoreCorrupt("onay deposu şeması geçersiz")
        values = payload.get("approvals")
        if not isinstance(values, list):
            raise ClaimStoreCorrupt("onay listesi geçersiz")
        return [FounderApproval.from_dict(value) for value in values]

    def _write_state(self, approvals: Sequence[FounderApproval]) -> None:
        payload = {
            "schema": FOUNDER_APPROVAL_STORE_SCHEMA,
            "approvals": [approval.to_dict() for approval in approvals],
        }
        fd, temporary_name = tempfile.mkstemp(prefix="founder_approvals.", suffix=".tmp", dir=self.store_dir)
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

    def _audit(self, event_type: str, approval: FounderApproval, *, actor: str, at: datetime) -> None:
        self._pending_events.append(
            {
                "schema": FOUNDER_APPROVAL_EVENT_SCHEMA,
                "event": event_type,
                "at": _format_time(at),
                "approval_id": approval.approval_id,
                "task": approval.task,
                "gate": approval.gate,
                "action": approval.action,
                "head_sha": approval.head_sha,
                "approved_by": approval.approved_by,
                "actor": actor,
            }
        )

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


def _find_match(
    approvals: Sequence[FounderApproval], *, task: str, gate: str, action: str, head_sha: str
) -> FounderApproval | None:
    # Onaylı kayıt bekleyenden önce gelir: aynı soru yeniden açılmaz.
    matches = [
        approval
        for approval in approvals
        if approval.matches(task=task, gate=gate, action=action, head_sha=head_sha)
    ]
    for approval in matches:
        if approval.is_approved:
            return approval
    return matches[0] if matches else None


def _find_by_id(approvals: Sequence[FounderApproval], approval_id: str) -> FounderApproval | None:
    return next((approval for approval in approvals if approval.approval_id == approval_id), None)
