"""Lumos Agent Wall — salt-okunur operatör görünürlüğü (ADR-025).

Board kayıtlarını (claim + agent status) dört soruya indirger:
hangi ajan ne işte, ne bekliyor, nerede kilitlendi, hangi karar duruyor.

Komut yüzeyi yoktur. Durdur / devam / yön / onay / başka ajana ver bu
modülde tanımlanmaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Mapping

from lumos_board.agent_status import (
    AgentState,
    ProjectedAgentStatus,
    mask_secretlike,
    read_agent_status_projection,
)
from lumos_board.task_claim import ClaimStatus, TaskClaim, TaskClaimStore

WALL_SCHEMA = "lumos.board.agent_wall.v1"
DEFAULT_STALE_AFTER_SECONDS = 120.0


class WallState(str, Enum):
    """Operatör görünürlük sözlüğü; kontrol yetkisi vermez."""

    WORKING = "WORKING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    NEEDS_DECISION = "NEEDS_DECISION"


_STATE_ORDER = {
    WallState.NEEDS_DECISION: 0,
    WallState.BLOCKED: 1,
    WallState.WAITING: 2,
    WallState.WORKING: 3,
}

_STATE_LABEL_TR = {
    WallState.NEEDS_DECISION: "karar gerekli",
    WallState.BLOCKED: "kilitli",
    WallState.WAITING: "bekliyor",
    WallState.WORKING: "çalışıyor",
}


@dataclass(frozen=True)
class WallRow:
    agent: str
    task: str
    state: WallState
    waiting_on: str
    decision_needed: str
    source: str
    ref: str

    def to_dict(self) -> dict[str, object]:
        return {
            "agent": self.agent,
            "task": self.task,
            "state": self.state.value,
            "waiting_on": self.waiting_on,
            "decision_needed": self.decision_needed,
            "source": self.source,
            "ref": self.ref,
        }


@dataclass(frozen=True)
class WallProjection:
    rows: tuple[WallRow, ...]
    counts: dict[str, int]
    schema: str = WALL_SCHEMA
    read_only: bool = True
    command_surface: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "read_only": self.read_only,
            "command_surface": self.command_surface,
            "counts": dict(self.counts),
            "rows": [row.to_dict() for row in self.rows],
        }


def _scope_overlap(left: str, right: str) -> bool:
    left_path = PurePosixPath(left)
    right_path = PurePosixPath(right)
    return left_path == right_path or left_path in right_path.parents or right_path in left_path.parents


def _claim_blocks(queued: TaskClaim, other: TaskClaim) -> bool:
    if other.status is not ClaimStatus.ACTIVE:
        return False
    if other.repo != queued.repo or other.claim_id == queued.claim_id:
        return False
    if other.task_id == queued.task_id:
        return True
    return any(
        _scope_overlap(left, right) for left in queued.scopes for right in other.scopes
    )


def _waiting_on(queued: TaskClaim, claims: tuple[TaskClaim, ...]) -> str:
    blockers = [claim for claim in claims if _claim_blocks(queued, claim)]
    if not blockers:
        return ""
    return ", ".join(
        f"{mask_secretlike(claim.owner, limit=80)} ({mask_secretlike(claim.task_id, limit=80)})"
        for claim in blockers
    )


def _heartbeat_age_seconds(claim: TaskClaim, now: datetime) -> float:
    heartbeat = claim.heartbeat_at
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=timezone.utc)
    return (now - heartbeat.astimezone(timezone.utc)).total_seconds()


def _row_from_claim(
    claim: TaskClaim,
    claims: tuple[TaskClaim, ...],
    *,
    now: datetime,
    stale_after_seconds: float,
) -> WallRow:
    agent = mask_secretlike(claim.owner, limit=80)
    task = mask_secretlike(claim.task_id, limit=80)
    ref = mask_secretlike(claim.claim_id, limit=80)
    if claim.status is ClaimStatus.QUEUED:
        waiting = _waiting_on(claim, claims)
        if waiting:
            return WallRow(
                agent=agent,
                task=task,
                state=WallState.WAITING,
                waiting_on=waiting,
                decision_needed="",
                source="claim",
                ref=ref,
            )
        return WallRow(
            agent=agent,
            task=task,
            state=WallState.NEEDS_DECISION,
            waiting_on="",
            decision_needed="Kuyrukta; bloke eden aktif claim görünmüyor",
            source="claim",
            ref=ref,
        )
    if _heartbeat_age_seconds(claim, now) > stale_after_seconds:
        return WallRow(
            agent=agent,
            task=task,
            state=WallState.BLOCKED,
            waiting_on="heartbeat",
            decision_needed="Ajan sessiz; heartbeat gecikti",
            source="claim",
            ref=ref,
        )
    return WallRow(
        agent=agent,
        task=task,
        state=WallState.WORKING,
        waiting_on="",
        decision_needed="",
        source="claim",
        ref=ref,
    )


def _row_from_status(record: ProjectedAgentStatus) -> WallRow | None:
    agent = mask_secretlike(record.record.agent_id, limit=80)
    task = mask_secretlike(record.task_title or record.record.job_id, limit=80)
    ref = mask_secretlike(record.display_ref, limit=160)
    if record.state is AgentState.COMPLETED:
        return None
    if record.state is AgentState.BLOCKED or record.stale:
        decision = "Ajan işi kilitlendi veya stale"
        if record.stale:
            decision = "Ajan durumu stale"
        return WallRow(
            agent=agent,
            task=task,
            state=WallState.BLOCKED,
            waiting_on="",
            decision_needed=decision,
            source="agent_status",
            ref=ref,
        )
    if record.state is AgentState.UNKNOWN:
        return WallRow(
            agent=agent,
            task=task,
            state=WallState.NEEDS_DECISION,
            waiting_on="",
            decision_needed="Ajan durumu unknown",
            source="agent_status",
            ref=ref,
        )
    return WallRow(
        agent=agent,
        task=task,
        state=WallState.WORKING,
        waiting_on="",
        decision_needed="",
        source="agent_status",
        ref=ref,
    )


def read_wall_projection(
    store: TaskClaimStore,
    *,
    status_sources: Mapping[str, Path | str] | None = None,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    now: datetime | None = None,
) -> WallProjection:
    """Claim ve agent-status kayıtlarını salt-okunur duvar satırlarına çevirir."""
    read_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    claims = store.list_claims(include_closed=False)
    rows: list[WallRow] = [
        _row_from_claim(
            claim,
            claims,
            now=read_now,
            stale_after_seconds=stale_after_seconds,
        )
        for claim in claims
    ]

    if status_sources:
        projection = read_agent_status_projection(
            status_sources,
            stale_after_seconds=stale_after_seconds,
            now=read_now,
        )
        for conflict in projection.conflicts:
            owners = ", ".join(mask_secretlike(owner, limit=80) for owner in conflict.owners)
            rows.append(
                WallRow(
                    agent=mask_secretlike(owners, limit=80),
                    task=mask_secretlike(conflict.job_id, limit=80),
                    state=WallState.NEEDS_DECISION,
                    waiting_on="",
                    decision_needed=f"Sahiplik çakışması: {owners}",
                    source="conflict",
                    ref=mask_secretlike(conflict.job_id, limit=80),
                )
            )
        claim_tasks = {claim.task_id for claim in claims}
        for record in projection.records:
            if record.record.job_id in claim_tasks:
                continue
            row = _row_from_status(record)
            if row is not None:
                rows.append(row)

    rows.sort(
        key=lambda row: (
            _STATE_ORDER[row.state],
            row.agent,
            row.task,
            row.ref,
        )
    )
    counts = {state.value: 0 for state in WallState}
    for row in rows:
        counts[row.state.value] += 1
    return WallProjection(rows=tuple(rows), counts=counts)


def format_wall_table(projection: WallProjection) -> str:
    """İnsan okunur özet; komut fiili içermez."""
    lines = [
        "Lumos Agent Wall — yalnız görünürlük (komut yok)",
        f"  {_STATE_LABEL_TR[WallState.NEEDS_DECISION]:<14} {projection.counts[WallState.NEEDS_DECISION.value]}",
        f"  {_STATE_LABEL_TR[WallState.BLOCKED]:<14} {projection.counts[WallState.BLOCKED.value]}",
        f"  {_STATE_LABEL_TR[WallState.WAITING]:<14} {projection.counts[WallState.WAITING.value]}",
        f"  {_STATE_LABEL_TR[WallState.WORKING]:<14} {projection.counts[WallState.WORKING.value]}",
        "",
    ]
    if not projection.rows:
        lines.append("(açık satır yok)")
        return "\n".join(lines) + "\n"
    header = f"{'Ajan':<22} {'Görev':<18} {'Durum':<16} {'Beklenen':<28} Karar"
    lines.append(header)
    lines.append("-" * len(header))
    for row in projection.rows:
        lines.append(
            f"{row.agent:<22} {row.task:<18} {_STATE_LABEL_TR[row.state]:<16} "
            f"{(row.waiting_on or '—'):<28} {row.decision_needed or '—'}"
        )
    return "\n".join(lines) + "\n"
