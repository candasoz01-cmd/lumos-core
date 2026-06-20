from __future__ import annotations

# ruff: noqa: E402

"""
Change plan modeli: deterministik, çok patch'li değişiklik planları.

Amaç:
- Dosya değişikliklerini doğrudan üretmek yerine önce bir "plan" altında toplamak.
- Aynı hedef/görev tekrarlandığında aynı plan (veya aynı yapıda plan) üretilebilsin.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List
import uuid

from core.change_sensitivity import ChangeSensitivity, classify_sensitivity
from core.patch_model import PatchProposal
from core.evolution_log import record_event


PlanState = str  # PLAN_CREATED, PLAN_VALIDATED, PLAN_READY, PLAN_EXECUTING, PLAN_APPLIED, PLAN_FAILED


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ChangePlan:
    plan_id: str
    goal_description: str
    target_paths: List[Path]
    estimated_sensitivity: ChangeSensitivity
    patch_count: int
    created_at: datetime
    patches: List[PatchProposal] = field(default_factory=list)

    @staticmethod
    def new(goal_description: str, patches: List[PatchProposal]) -> "ChangePlan":
        if not patches:
            raise ValueError("ChangePlan requires at least one PatchProposal")
        paths = [p.target_path for p in patches]
        # Heuristik: en yüksek hassasiyeti plan hassasiyeti olarak al.
        sensitivities = [classify_sensitivity(p.target_path) for p in patches]
        estimated = max(sensitivities, key=lambda s: s.value)
        plan = ChangePlan(
            plan_id=str(uuid.uuid4()),
            goal_description=goal_description,
            target_paths=paths,
            estimated_sensitivity=estimated,
            patch_count=len(patches),
            created_at=_now(),
            patches=list(patches),
        )
        # Evolution: PLAN_CREATED
        record_event(
            plan_id=plan.plan_id,
            patch_ids=[p.id for p in plan.patches],
            action_type="PLAN_CREATED",
            affected_paths=[str(p.target_path) for p in plan.patches],
            sensitivity_levels=[estimated.name],
        )
        return plan


@dataclass(frozen=True)
class PlanValidationResult:
    ok: bool
    errors: List[str]


def validate_plan(plan: ChangePlan) -> PlanValidationResult:
    """
    Plan uygulanmadan önce basit tutarlılık kontrolleri:

    - Aynı path'e birden fazla patch (target conflict)
    - Patch listesi boş olmamalı
    """
    errors: List[str] = []
    if not plan.patches or plan.patch_count <= 0:
        errors.append("empty_plan")

    seen = {}
    for p in plan.patches:
        key = str(p.target_path.resolve())
        if key in seen:
            errors.append(f"duplicate_patch_for_path:{key}")
        else:
            seen[key] = True

    return PlanValidationResult(ok=not errors, errors=errors)

