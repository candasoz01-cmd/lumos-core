"""
VerificationEngine: dispatch by step.kind to verifier, produce VerificationResult.
Blocked kinds (external/critical) never run executor; if verification were invoked defensively, result is not verified.
"""
from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from task_engine.action_registry import ExecutionContext
from task_engine.profiles import (
    STEP_TYPE_ANALYZE,
    STEP_TYPE_CRITICAL,
    STEP_TYPE_EXTERNAL,
    STEP_TYPE_PLAN,
    STEP_TYPE_READ,
    STEP_TYPE_SAFE_LOCAL,
)
from task_engine.verification.results import VerificationResult

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord, TaskStep


# Verifier: (step, task, context, ok, output, error, verified_from_executor) -> VerificationResult
Verifier = Callable[
    ["TaskStep", "TaskRecord", ExecutionContext, bool, str, str, bool],
    VerificationResult,
]


class VerificationEngine:
    """
    Maps step.kind to verifier. Returns VerificationResult after executor runs.
    Blocked kinds (external/critical) are not executed; verification layer does not bypass policy.
    """
    def __init__(self, default_verifier: Verifier | None = None) -> None:
        self._verifiers: dict[str, Verifier] = {}
        self._default_verifier = default_verifier

    def register(self, kind: str, verifier: Verifier) -> None:
        """Register a verifier for a step kind (normalized to lowercase)."""
        self._verifiers[(kind or "").strip().lower()] = verifier

    def get_verifier(self, kind: str) -> Verifier | None:
        """Return verifier for kind, or None if not registered and no default."""
        key = (kind or "").strip().lower()
        return self._verifiers.get(key) or self._default_verifier

    def verify(
        self,
        step: "TaskStep",
        task: "TaskRecord",
        context: ExecutionContext,
        ok: bool,
        output: str,
        error: str,
        verified_from_executor: bool,
    ) -> VerificationResult:
        """
        Get verifier for step.kind and run it. Blocked kinds get non-verified result.
        """
        kind = (step.kind or STEP_TYPE_ANALYZE).strip().lower()
        if kind in (STEP_TYPE_EXTERNAL, STEP_TYPE_CRITICAL):
            return VerificationResult(
                verified=False,
                reason="blocked",
                details="Bu adım türü yürütülmez (güvenlik).",
            )
        verifier = self.get_verifier(kind)
        if verifier is None:
            return VerificationResult(
                verified=False,
                reason="no_verifier",
                details="Doğrulayıcı tanımlı değil.",
            )
        return verifier(
            step, task, context,
            ok, output, error, verified_from_executor,
        )
