# Brain flow — authoritative high-level execution path

This document describes the single end-to-end flow from user request to final response in Lumos: the **Brain** (orchestrator) connects Planner, TaskEngine, Verification, and Observation into one path.

## Overview

1. **User request** → parsed into a **goal** (thin parse: normalize/trim).
2. **Goal** → **Planner** produces a sequence of **steps** (safe kinds only: read, analyze, plan).
3. **Steps** → **TaskStore** creates a **task** (via `create_from_steps`; no duplicate planning).
4. **Task** → **TaskEngine** runs the task: for each step, **Executors** run, **Verification** decides verified/unverified/simulation, **Observation** records events.
5. **After run** → Brain collects task status, verification counts, and recent observation events.
6. **Response builder** → produces a human-readable summary: goal, task id, status, verified/unverified/simulation counts, and most relevant observation or block reason.

## Components (responsibilities)

| Layer | Responsibility |
|-------|----------------|
| **Brain / Orchestrator** | Connects flow: parse request → goal → plan → create task → run task → collect results → build response. Entry: `core.brain.run()`. |
| **Planner** | Generates steps from a goal. `task_engine.planner.plan(goal)` → list of `TaskStep`. |
| **TaskEngine** | Orchestrates execution: runs steps in order, enforces profile/approval, calls executors and verification, records observation events. |
| **Executors** | Attempt actions per step (read, analyze, plan, safe_local). Registered in `ActionRegistry`. |
| **Verification** | Decides verified / unverified / simulation per step. `VerificationEngine.verify(...)` → `VerificationResult`. |
| **Observation** | Records what happened (task_created, action_executed, step_verified, step_failed, policy_blocked). `ObservationEngine.record_event()`. |
| **Response builder** | Builds final summary string: goal, task id, status, counts, block reason or observation. `core.brain.build_response()`. |

## Entry point

- **Canonical entry**: `core.brain.run(user_request, task_store, base_dir, permission_profile, general_approval, observation_engine=...)`
- **CLI**: "görev oluştur &lt;açıklama&gt;" is handled by `handle_task_mutation("gorev_olustur", ...)` which calls `brain_run(...)` and prints `result.human_readable_summary`.

## Data flow (no parallel duplicate systems)

- **Goal** comes from `parse_request_to_goal(user_request)`.
- **Steps** come from `task_engine.planner.plan(goal)` only (no second planning in TaskStore for this path).
- **Task** is created with `task_store.create_from_steps(title, description, steps, permission_profile)`.
- **Execution** is only inside `TaskEngine.run_task(task_id)` (executors, verification, observation called from there).
- **Verification counts** and **observation events** are read from the updated task and from `observation_engine.get_recent_events()` after `run_task` returns.

## Safety

- Brain and the flow are **non-destructive**: no external side effects, no destructive actions. Executors and policy restrict step kinds (no permanent_delete, external_write, or critical_system_config in this path).

## File reference

- **Orchestrator**: `src/core/brain.py` — `run()`, `parse_request_to_goal()`, `build_response()`, `BrainResult`.
- **Planner**: `src/task_engine/planner.py`.
- **Task creation with steps**: `src/task_engine/engine.py` — `TaskStore.create_from_steps()`, `TaskEngine.run_task()`.
- **Verification**: `src/task_engine/verification/`.
- **Observation**: `src/task_engine/observation/`.
- **CLI wiring**: `src/cli/cli_tasks_mutation.py` — `gorev_olustur` → `brain_run()`.
