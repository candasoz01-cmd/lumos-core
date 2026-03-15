# Live Brain Mode

When Lumos runs in **online mode**, free-text user input that does not match any registered CLI command is routed to the **Brain / Orchestrator** path instead of being rejected. This is called **live brain** mode.

## Command path vs free-text brain path

| Input type | Offline mode | Online mode |
|------------|--------------|-------------|
| **Known command** (e.g. `durum`, `görevler`, `yardım`) | CLI: normalized and dispatched to the corresponding handler | Same: CLI path |
| **Unknown / free text** | Rejected with a safe fallback message (no interpretation) | Sent to **live brain**: online engine (LLM) answers and may create a task via Brain |

- **Command path**: Deterministic. Input is normalized and matched to a fixed set of routes; handlers are in the CLI layer (notes, readonly, task mutation, lock, presence, alias, etc.).
- **Free-text brain path**: Only active when `LUMOS_MODE=online`. The input is passed to the online engine; the response is shown in natural Turkish. If the engine signals that a task should be created (`create_task` + `task_goal`), the Brain runs (Planner → TaskStore → TaskEngine) and the result is merged into the response.

## Input routing gate

The **input routing gate** is in **`src/cli/cli_router.py`**:

1. User input is read and normalized with `normalize_command(raw, ...)`.
2. If the route is **not** `"unknown"`, the existing CLI dispatch continues (notes, readonly, task mutation, etc.).
3. If the route is `"unknown"`:
   - **Offline**: `get_fallback_message(...)` is printed (safe rejection).
   - **Online** and `on_live_brain` is set: `on_live_brain(raw)` is called, which runs the live brain handler and prints the result.

So the gate is the `route == "unknown"` branch in `run_cli_loop()`: that branch checks `mode == "online"` and the presence of `on_live_brain`, and either invokes the live brain handler or the fallback.

## How online mode differs from offline

- **Offline**: Only registered commands are accepted. Unknown input always gets the fallback message; no LLM, no task creation from free text.
- **Online**: Registered commands behave the same. In addition, unknown input is sent to the online engine (and optionally to Brain for task creation). Consent, lock, and profile restrictions are not bypassed; task creation still goes through Planner/TaskEngine and permission checks.

## How to trigger live brain at startup

1. Set **`LUMOS_MODE=online`** (e.g. `export LUMOS_MODE=online` or `LUMOS_MODE=online python -m lumos_core`).
2. Start Lumos (e.g. `python src/main.py` or `lumos`).
3. Unlock if required (kilit menüsü).
4. At the `Sen:` prompt, type a **known command** → CLI path. Type **free text** (e.g. a question or request) → live brain path (online engine + optional task).

So **live brain is enabled automatically** whenever online mode is enabled; no separate flag is needed.

## Response style (live brain)

- Natural Turkish, concise.
- If **no task** was created: the online engine’s response is shown as-is (after minimal formatting).
- If a **task was created**: the direct response is shown, then a clear line that a task was created and run, plus the Brain summary.

## Security and policy

- No destructive actions.
- No bypass of consent, lock, or profile restrictions. Task creation from the brain path still uses the current permission profile and general approval; the TaskEngine enforces policy as usual.
