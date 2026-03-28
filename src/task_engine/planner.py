"""
Planner: convert high-level goals into TaskEngine step sequences.
Safe default behavior only: read, analyze, plan. No destructive actions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from task_engine.profiles import (
    STEP_TYPE_ANALYZE,
    STEP_TYPE_PLAN,
    STEP_TYPE_READ,
    STEP_TYPE_SAFE_LOCAL,
)

if TYPE_CHECKING:
    from task_engine.engine import TaskStep


class DefaultPlanner:
    """
    Converts a goal (description) into a sequence of TaskSteps.
    Only produces read / analyze / plan steps. No write_local, external, or critical.
    """
    def plan(self, goal: str) -> list["TaskStep"]:
        """
        goal: high-level description (e.g. task description).
        Returns list of TaskStep with safe kinds only.
        """
        from task_engine.engine import TaskStep
        d = (goal or "").strip().lower()
        steps: list[TaskStep] = []
        # patch: → minimum kapsam patch_pipeline (tek veya çok dosya) tek adım
        if d.startswith("patch:"):
            steps.append(
                TaskStep(
                    "Dosya patch uygula (patch_pipeline)",
                    kind=STEP_TYPE_SAFE_LOCAL,
                ),
            )
            return steps
        # Not sistemi / özet talebi
        if "not" in d or "özet" in d or "ozet" in d or "kontrol" in d:
            steps.append(TaskStep("Not sistemini kontrol et", kind=STEP_TYPE_READ))
            steps.append(TaskStep("Sonuçları analiz et", kind=STEP_TYPE_ANALYZE))
            steps.append(TaskStep("Kısa özet hazırla", kind=STEP_TYPE_ANALYZE))
        # Genel / boş: analyze → plan → analyze
        if not steps:
            steps.append(TaskStep("Görevi analiz et", kind=STEP_TYPE_ANALYZE))
            steps.append(TaskStep("Adımları planla", kind=STEP_TYPE_PLAN))
            steps.append(TaskStep("Sonucu raporla", kind=STEP_TYPE_ANALYZE))
        return steps


_default_planner: DefaultPlanner | None = None


def get_default_planner() -> DefaultPlanner:
    """Return the default planner instance."""
    global _default_planner
    if _default_planner is None:
        _default_planner = DefaultPlanner()
    return _default_planner


def plan(goal: str) -> list["TaskStep"]:
    """
    Convert goal into a sequence of TaskSteps (safe defaults only).
    Uses the default planner. No destructive actions.
    """
    return get_default_planner().plan(goal)
