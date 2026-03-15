"""
Brain / Orchestrator: single high-level flow from user request to final response.

Connects Planner → TaskStore (create_from_steps) → TaskEngine (run_task) →
Verification (inside TaskEngine) → Observation (events) → response builder.

Responsibilities stay separated:
- Planner: generates steps from goal
- TaskEngine: orchestrates step execution
- Executors: attempt actions
- Verification: decides verified/unverified/simulation
- Observation: records what happened
- Brain: connects them into one flow; builds final human-readable response.

Safe, non-destructive: no external side effects, no destructive actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from task_engine.observation import (
    EVENT_POLICY_BLOCKED,
    EVENT_STEP_FAILED,
    EVENT_STEP_VERIFIED,
    ObservationEngine,
)
from task_engine.observation.events import ObservationEvent
from task_engine.planner import plan as planner_plan
from task_engine.engine import TaskEngine, TaskStore

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord


@dataclass
class BrainResult:
    """Result of Brain.run(): goal, task, verification counts, and human-readable summary."""

    goal: str
    task_id: int
    task_status: str
    verified_count: int
    unverified_count: int
    simulation_count: int
    block_reason_or_observation: str
    success: bool
    message: str
    human_readable_summary: str


def parse_request_to_goal(user_request: str) -> str:
    """
    Parse user request into a goal (normalize for Planner).
    Thin layer: trim and return; no interpretation or side effects.
    """
    return (user_request or "").strip()


def build_response(
    goal: str,
    task: "TaskRecord",
    events: list[ObservationEvent],
    *,
    include_goal: bool = True,
    include_task_id: bool = True,
    include_status: bool = True,
    include_counts: bool = True,
    include_reason_or_observation: bool = True,
) -> str:
    """
    Build final human-readable summary:
    - goal
    - created task id
    - final task status
    - verified / unverified / simulation counts
    - most relevant observation or block reason
    """
    parts: list[str] = []
    if include_goal and goal:
        parts.append(f"Hedef: {goal[:200]}" + ("..." if len(goal) > 200 else ""))
    if include_task_id:
        parts.append(f"Görev: {task.task_id} — {task.title or 'Görev'}")
    if include_status:
        parts.append(f"Durum: {task.status}")
    if include_counts:
        v = getattr(task, "verified_count", 0)
        u = getattr(task, "unverified_count", 0)
        s = getattr(task, "simulation_count", 0)
        parts.append(f"Doğrulanan: {v}, doğrulanamayan: {u}, simülasyon: {s}")
    reason = _most_relevant_reason_or_observation(task, events)
    if include_reason_or_observation and reason:
        parts.append(f"Not: {reason}")
    return "\n".join(parts)


def _most_relevant_reason_or_observation(
    task: "TaskRecord",
    events: list[ObservationEvent],
) -> str:
    """Pick the most relevant block reason or observation for the summary."""
    block = getattr(task, "block_reason", "") or task.error_summary or ""
    if block:
        return block[:300]
    for ev in reversed(events):
        if ev.task_id != task.task_id:
            continue
        if ev.event_type == EVENT_POLICY_BLOCKED:
            return ev.payload.get("message") or ev.payload.get("reason") or "Adım yetki nedeniyle durdu."
        if ev.event_type == EVENT_STEP_FAILED:
            return ev.payload.get("error") or ev.payload.get("message") or "Adım hata ile bitti."
        if ev.event_type == EVENT_STEP_VERIFIED:
            reason = ev.payload.get("reason", "")
            if reason:
                return f"Doğrulama: {reason}"
    return ""


def run(
    user_request: str,
    task_store: TaskStore,
    base_dir: Path | str,
    permission_profile: str,
    general_approval: bool,
    *,
    observation_engine: ObservationEngine | None = None,
    action_registry: Any = None,
    verification_engine: Any = None,
) -> BrainResult:
    """
    Single Brain flow: parse request → goal → plan → create task → run task →
    collect verification and observation → build final response.

    Safe, non-destructive. No external side effects.
    """
    goal = parse_request_to_goal(user_request)
    if not goal:
        return BrainResult(
            goal="",
            task_id=0,
            task_status="",
            verified_count=0,
            unverified_count=0,
            simulation_count=0,
            block_reason_or_observation="Hedef boş.",
            success=False,
            message="Hedef boş.",
            human_readable_summary="Hedef boş; işlem yapılmadı.",
        )

    steps = planner_plan(goal)
    title = goal[:80] if len(goal) > 80 else goal
    task = task_store.create_from_steps(
        title=title,
        description=goal,
        steps=steps,
        permission_profile=permission_profile,
    )

    engine = TaskEngine(
        task_store,
        permission_profile,
        general_approval,
        base_dir=base_dir,
        action_registry=action_registry,
        verification_engine=verification_engine,
        observation_engine=observation_engine,
    )
    ok, message = engine.run_task(task.task_id)

    task_after = task_store.get(task.task_id)
    if not task_after:
        return BrainResult(
            goal=goal,
            task_id=task.task_id,
            task_status="",
            verified_count=0,
            unverified_count=0,
            simulation_count=0,
            block_reason_or_observation="Görev kaydı bulunamadı.",
            success=False,
            message=message,
            human_readable_summary=f"Hedef: {goal[:200]}\nGörev {task.task_id} yürütüldü ancak kayıt sonradan bulunamadı.",
        )
    task = task_after

    events = []
    if observation_engine:
        events = observation_engine.get_recent_events(limit=50)

    block_or_obs = _most_relevant_reason_or_observation(task, events)
    summary = build_response(goal, task, events)

    return BrainResult(
        goal=goal,
        task_id=task.task_id,
        task_status=task.status,
        verified_count=getattr(task, "verified_count", 0),
        unverified_count=getattr(task, "unverified_count", 0),
        simulation_count=getattr(task, "simulation_count", 0),
        block_reason_or_observation=block_or_obs,
        success=ok,
        message=message,
        human_readable_summary=summary,
    )
