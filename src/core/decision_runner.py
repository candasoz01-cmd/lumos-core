from __future__ import annotations

from dataclasses import dataclass

from core.decision_model import MutationOption


@dataclass(frozen=True)
class DecisionExecutionResult:
    option: MutationOption
    success: bool
    notes: str


def execute_decision(option: MutationOption) -> DecisionExecutionResult:
    """
    İlk sürüm execution katmanı.

    - Sadece temel bir doğrulama yapar.
    - Gerçek patch apply işlemi içermez.
    """
    if not option.target_paths:
        return DecisionExecutionResult(
            option=option,
            success=False,
            notes="No target_paths defined for option.",
        )

    # İleride gerçek execution pipeline entegrasyonu için yer tutucu.
    return DecisionExecutionResult(
        option=option,
        success=True,
        notes="Execution stub: validation passed, no changes applied.",
    )

