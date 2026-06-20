from __future__ import annotations

# ruff: noqa: E402

"""
Plan registry: ChangePlan lifecycle state yönetimi.

PlanState:
- PLAN_CREATED
- PLAN_VALIDATED
- PLAN_READY
- PLAN_EXECUTING
- PLAN_APPLIED
- PLAN_FAILED
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from core.change_plan import ChangePlan
from core.guard_audit import GuardEvent, record_guard_event


PlanState = Literal[
    "PLAN_CREATED",
    "PLAN_VALIDATED",
    "PLAN_READY",
    "PLAN_EXECUTING",
    "PLAN_APPLIED",
    "PLAN_FAILED",
]


@dataclass(frozen=True)
class PlanRecord:
    plan_id: str
    plan: ChangePlan
    patch_ids: List[str]
    state: PlanState
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime] = None
    failed_patches: List[str] = None


_PLANS: Dict[str, PlanRecord] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def register_plan(plan: ChangePlan) -> PlanRecord:
    existing = _PLANS.get(plan.plan_id)
    if existing is not None:
        return existing
    ts = _now()
    rec = PlanRecord(
        plan_id=plan.plan_id,
        plan=plan,
        patch_ids=[p.id for p in plan.patches],
        state="PLAN_CREATED",
        created_at=ts,
        updated_at=ts,
        executed_at=None,
        failed_patches=[],
    )
    _PLANS[plan.plan_id] = rec
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=plan.target_paths[0],
            sandbox_mode=False,
            reason="PLAN_CREATED",
            caller="core.plan_registry.register_plan",
        ),
    )
    return rec


def get_plan(plan_id: str) -> Optional[PlanRecord]:
    return _PLANS.get(plan_id)


def _set_state(plan_id: str, state: PlanState) -> Optional[PlanRecord]:
    rec = _PLANS.get(plan_id)
    if rec is None:
        return None
    updated = replace(rec, state=state, updated_at=_now())
    _PLANS[plan_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=updated.plan.target_paths[0],
            sandbox_mode=False,
            reason=state,
            caller="core.plan_registry._set_state",
        ),
    )
    return updated


def mark_validated(plan_id: str) -> Optional[PlanRecord]:
    return _set_state(plan_id, "PLAN_VALIDATED")


def mark_ready(plan_id: str) -> Optional[PlanRecord]:
    return _set_state(plan_id, "PLAN_READY")


def mark_executing(plan_id: str) -> Optional[PlanRecord]:
    rec = _PLANS.get(plan_id)
    if rec is None:
        return None
    now = _now()
    updated = replace(rec, state="PLAN_EXECUTING", updated_at=now, executed_at=now)
    _PLANS[plan_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=updated.plan.target_paths[0],
            sandbox_mode=False,
            reason="PLAN_EXECUTED",
            caller="core.plan_registry.mark_executing",
        ),
    )
    return updated


def mark_applied(plan_id: str) -> Optional[PlanRecord]:
    return _set_state(plan_id, "PLAN_APPLIED")


def mark_failed(plan_id: str, failed_patch_ids: List[str]) -> Optional[PlanRecord]:
    rec = _PLANS.get(plan_id)
    if rec is None:
        return None
    updated = replace(
        rec,
        state="PLAN_FAILED",
        updated_at=_now(),
        failed_patches=list(failed_patch_ids),
    )
    _PLANS[plan_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="deny",
            path=updated.plan.target_paths[0],
            sandbox_mode=False,
            reason="PLAN_FAILED",
            caller="core.plan_registry.mark_failed",
        ),
    )
    return updated


def clear_plans() -> None:
    _PLANS.clear()

