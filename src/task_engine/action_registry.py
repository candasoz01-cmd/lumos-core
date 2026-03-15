"""
Registry-based action dispatch for TaskEngine.
Maps step.kind to safe, non-destructive executors.
External/critical kinds are blocked by policy guard before dispatch; registry defends with same check.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from task_engine.profiles import (
    STEP_TYPE_ANALYZE,
    STEP_TYPE_CRITICAL,
    STEP_TYPE_EXTERNAL,
)

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord, TaskStep


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable context passed to executors (e.g. base_dir for read)."""
    base_dir: Path | None = None


# Executor: (step, task, context) -> (ok, output, error, verified)
Executor = Callable[["TaskStep", "TaskRecord", ExecutionContext], tuple[bool, str, str, bool]]


class ActionRegistry:
    """
    Maps step.kind to executor. Safe, non-destructive executors only.
    Default executor used when kind is not registered (e.g. analyze as safe default).
    """
    def __init__(self, default_executor: Executor | None = None) -> None:
        self._executors: dict[str, Executor] = {}
        self._default_executor = default_executor

    def register(self, kind: str, executor: Executor) -> None:
        """Register an executor for a step kind (normalized to lowercase)."""
        self._executors[(kind or "").strip().lower()] = executor

    def get_executor(self, kind: str) -> Executor | None:
        """Return executor for kind, or None if not registered and no default."""
        key = (kind or "").strip().lower()
        return self._executors.get(key) or self._default_executor

    def execute(
        self,
        step: "TaskStep",
        task: "TaskRecord",
        context: ExecutionContext,
    ) -> tuple[bool, str, str, bool]:
        """
        Dispatch step by kind. Returns (ok, output, error, verified).
        Blocks external/critical kinds (policy guard; defensive if something slips through).
        """
        kind = (step.kind or STEP_TYPE_ANALYZE).strip().lower()
        if kind in (STEP_TYPE_EXTERNAL, STEP_TYPE_CRITICAL):
            return False, "", "Bu adım türü yürütülmez (güvenlik).", False
        executor = self.get_executor(kind)
        if executor is None:
            return False, "", "Desteklenmeyen adım türü.", False
        return executor(step, task, context)
