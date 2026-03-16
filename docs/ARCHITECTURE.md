# Lumos architecture (overview)

Short overview of the decision system, patch pipeline, sandbox validation, and log layers.

---

## Decision system

The decision system turns a **goal** and **target paths** into a single chosen strategy and optional patch proposals, without applying changes to files.

1. **Explorer** (`decision_explorer`): Generates several candidate **mutation options** (e.g. minimal, medium, aggressive) from the goal and target paths. Each option has estimated risk, complexity, success probability, impact, and sensitivity. Options are scored and written to the evolution log as high-level events.

2. **Simulator** (`decision_simulator`): For each option, produces a lightweight **simulation result** (e.g. reflecting the option’s own risk/success estimates). No real patch execution.

3. **Ranker** (`decision_ranker`): Combines options and simulations into a **final score** using configurable weights (from `.lumos/weights.json` via `adaptive_weights`). Options are sorted by score; the best one is chosen.

4. **Runner** (`decision_runner`): Turns the chosen option into **patch proposals** (one per target path), runs **validation** and **sandbox** steps, and returns a **DecisionExecutionResult** (proposal IDs, summary, diff preview, explanation). It does **not** apply patches.

5. **Pipeline** (`decision_pipeline`): Orchestrates the flow: explorer → simulator → ranker → runner, then records execution in the decision-feedback log, appends to decision history, and optionally updates weights from feedback so the next run uses the new ranking strategy.

Protected/core targets are identified when `base_dir` is provided; apply remains a separate, gated step and is not performed inside this pipeline.

---

## Patch pipeline

The patch pipeline enforces **“generate ≠ apply”**: proposals are created and validated first; applying to the real filesystem is a separate, controlled step.

1. **Propose** (`propose_text_patch`): Builds a **PatchProposal** (target path, original vs proposed text, metadata, fingerprint). For core/protected targets, `protected_target` and `requires_review` are set. The proposal is registered and a guard event is recorded; no file is written yet.

2. **Validate** (`validate_proposal_against_filesystem`): Reads the current file content and compares its fingerprint to the proposal’s original fingerprint. If they match, the proposal is marked validated; if not, status is `fingerprint_mismatch` and the proposal stays in a state that signals drift. The real file is still not modified.

3. **Sandbox** (optional): `run_sandbox_validation` writes the **proposed** content to a **temporary file** only. That path can be used for extra checks (e.g. parse, import, tests). The actual target path is never touched.

4. **Apply** (`apply_patch`): Writes the proposal to the real target only when explicitly invoked and only when policy allows it. For protected targets, apply is forbidden unless `allow_protected_apply` and review/state conditions are met; otherwise `ProtectedApplyForbidden` is raised.

So: the pipeline always goes **proposal → validation → (optional sandbox) → optional apply**. Core/protected targets never get applied without an explicit gate.

---

## Sandbox validation

Sandbox validation checks that the **proposed content** is usable, without changing the real workspace.

- **Behavior**: `run_sandbox_validation(proposal)` writes `proposal.proposed_text` to a **temporary file** (e.g. `tempfile.NamedTemporaryFile`), records the path in the patch registry and in guard/audit, and returns that path.
- **Purpose**: Callers can run extra checks on the temp file (e.g. syntax, imports, tests). The real target path is never read or written in this step.
- **Lifecycle**: The sandbox result is stored on the patch record so the system knows sandbox validation was run; apply remains a separate decision.

---

## Evolution and decision history logs

Lumos uses several append-only JSONL logs for observability and strategy updates. None of them are removed or replaced by the other.

- **Evolution log** (`logs/lumos_evolution.jsonl`): High-level **lifecycle events** for plans and patches (e.g. options generated, option selected, patch proposed, applied, failed, rolled back). Used to see the overall plan → patch → result flow and by the strategy layer to analyze success/rollback and sensitivity. Schema includes `action_type`, `result`, `affected_paths`, `sensitivity_levels`, `rollback_occurred`, `conflict_detected`.

- **Decision feedback log** (`logs/lumos_decision_feedback.jsonl`): **Execution outcome** of the decision pipeline (one record per run): `option_id`, `success`, `risk`, `timestamp`, `notes`. Used by the strategy updater to adjust weights (e.g. reward success, penalize failure) so future rankings improve. Separate from the evolution log to keep schemas and purposes clear.

- **Decision history log** (`logs/lumos_decision_history.jsonl`): **Readable history** of every decision: goal, chosen option id/description, risk, success probability, complexity, impact, sensitivity levels, proposal IDs, success flag, notes. Used for auditing and understanding what the system decided over time, without changing any behavior.

All logging is best-effort (failures do not crash the pipeline).
