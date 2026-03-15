# Lumos Core Flow Stabilization (Pre–Memory Transfer)

**Goal:** Stabilize the active response path and routing consistency without expanding persona/behavior rules. Keep Lumos identity (Turkish, state injection) stable and ready for memory transfer.

**Date:** 2025-03 (pre–memory transfer).

---

## 1. Active Response Path (True Path)

End-to-end flow for user input:

| Stage | File(s) | Role |
|-------|--------|------|
| **CLI entry** | `lumos.py` → `src/main.py` | Env (LUMOS_MODE, etc.), then `create_runtime()` → `run_cli_loop(router_ctx)` |
| **Input** | `cli/cli_router.py` | `get_raw_input()` → raw line |
| **Parser / router** | `cli/cli_parse.py` | `normalize_command(raw, base_dir, aliases)` → `(route, args)` |
| **Deterministic commands** | `cli/cli_router.py` | Notes, readonly (`handle_readonly`), task mutation, kilit, kamera, alias, self_test, exit → **never** hit live_brain |
| **Unknown + offline** | `cli/cli_router.py` | `route == "unknown"`, `mode != "online"` → `get_fallback_message(raw, last_route)` → print; **no** LLM |
| **Unknown + online** | `cli/cli_router.py` | `route == "unknown"`, `mode == "online"`, `on_live_brain` set → `router_ctx.on_live_brain(raw)` |
| **Live brain** | `core/live_brain.py` | `handle_live_brain(raw, ..., state=state)` → builds mode/presence/consent/lock from `CoreState` and `general_approval`, calls `online_engine.process(raw, mode=..., presence=..., consent=..., lock=...)` |
| **Online engine** | `engine/online_engine.py` | `OnlineEngineV1.process()` → signer path or direct OpenAI path → `ModelClient.generate(prompt, mode=..., presence=..., consent=..., lock=...)` |
| **Model client** | `engine/model_client.py` | `ModelClient.generate()` → `_generate_openai()` with `_LUMOS_SYSTEM_PROMPT_TEMPLATE.format(mode=..., presence=..., consent=..., lock=...)` → OpenAI Responses API → reply text |
| **Output** | `cli/cli_router.py` | `print(msg)` from `handle_live_brain` return value |

**Identity and state:** Lumos identity (“You are Lumos”, Turkish default, anti–ChatGPT) and runtime state (mode, presence, consent, lock) are in `model_client._LUMOS_SYSTEM_PROMPT_TEMPLATE` and are injected in `_generate_openai()`. As of this stabilization, `handle_live_brain` receives `state` from the runtime and passes real mode/presence/consent/lock into `online_engine.process()`, so the model always gets current state.

---

## 2. Legacy / Conflicting Paths (Identified and Isolated)

- **Lumos.respond(ctx) path** (`core/lumos.py`): `Lumos.respond(ctx)` → `PolicyRules.evaluate(ctx, mode, ...)` → `engine.process(message)`.  
  - **Not used by the CLI** for free text. CLI uses `on_live_brain` → `handle_live_brain` → `online_engine.process()`.  
  - **Still used by:** `tests/test_offline.py`, `bootstrap.sh`, `patch_memory.sh`, and archived `main.py` backups.  
  - **Action:** Documented in code (comment on `respond()`). No removal; tests and scripts can keep using this path. Optionally rename or mark as “legacy” in docs later.

- **OfflineEngineV1** in the **PolicyRules** path: For offline, `PolicyRules.evaluate` calls `engine.process(getattr(ctx, "message", ""))`. So when tests call `lumos.respond(ctx)` with `engine=OfflineEngineV1()`, they hit this path. The **CLI** never calls `lumos.respond()`; for unknown input in offline it uses `get_fallback_message()`. So there are two offline behaviors:  
  1. **CLI:** unknown → `get_fallback_message()` (parser-based, no engine).  
  2. **Legacy:** `lumos.respond(ctx)` → OfflineEngineV1.process() (e.g. test_offline).  
  Both are valid; no conflict as long as tests assert the correct behavior (e.g. “Anlayamadım” for unrecognized “selam” in the legacy path).

- **Duplicate “help” / “durum” handling:** Only in the CLI path via `normalize_command` → `handle_readonly`; no duplicate in live_brain.

---

## 3. What Was Cleaned or Isolated

- **State injection:** `handle_live_brain()` now takes optional `state: CoreState | None`. When provided, it computes `mode`, `presence`, `consent`, `lock` from `state` and `general_approval` and passes them to `online_engine.process(..., mode=..., presence=..., consent=..., lock=...)`, so the model prompt always receives current runtime state.
- **Runtime wiring:** In `lumos_runtime.create_runtime()`, the online `_live_brain_handler` now calls `handle_live_brain(..., state=state)`.
- **Diagnostics:** In `engine/model_client.py`, on LLM exception we no longer print to stdout; we use `logger.exception("LLM error: %s", e)` and return the user-facing “Model hatası oluştu.” so the terminal stays clean and the real reason is in logs.
- **OPENAI_MODEL:** Default in `model_client._generate_openai()` when `OPENAI_MODEL` is unset is `"gpt-4o"` so the API is not called with `model=None`.
- **Legacy path:** Documented in `core/lumos.py` that `respond()` is used by scripts/tests and that CLI free-text uses the live_brain path.
- **Tests:**  
  - `tests/test_offline.py`: Expects “Anlayamadım” from OfflineEngineV1 for “selam” (legacy path).  
  - `tests/test_online.py`: Boot message “Lumos başlatılıyor”, mode “online”, and one of “Online hazır değil.” / “Yanındayım.” / “Yanıt” / “selam” so it passes with or without API key.  
  - `tests/test_live_brain.py`: New test `test_live_brain_injects_state_when_provided()` ensures that when `state` is passed, `engine.process` is called with `mode`, `lock`, `consent` (and presence).  
  - `tests/test_model_client.py`: Existing tests for Lumos identity and state placeholders remain.

---

## 4. Online / Offline Consistency

- **Known commands:** Always go through the deterministic CLI flow (`normalize_command` → notes/readonly/task_mutation/kilit/kamera/alias/self_test/exit). They never go through the free-text/live_brain path.
- **Free text in online mode:** Only when `route == "unknown"` and `mode == "online"` and `on_live_brain` is set → `handle_live_brain` → online engine → model client. State is injected; user sees a single message string.
- **Free text in offline mode:** `route == "unknown"`, `mode != "online"` → `get_fallback_message(raw, last_route)`; no LLM, safe fallback.

---

## 5. Files in the Active Response Path

- `lumos.py` – CLI entry, env
- `src/main.py` – create_runtime, run_cli_loop
- `src/core/lumos_runtime.py` – build router_ctx, set mode and on_live_brain, pass state into handle_live_brain
- `src/cli/cli_router.py` – loop, normalize_command, dispatch, on_live_brain for unknown+online
- `src/cli/cli_parse.py` – normalize_command, get_fallback_message
- `src/cli/cli_readonly.py` – handle_readonly (durum, hazir, help, etc.)
- `src/core/live_brain.py` – handle_live_brain, state injection into process()
- `src/engine/online_engine.py` – OnlineEngineV1.process()
- `src/engine/model_client.py` – ModelClient.generate(), _generate_openai(), Lumos system prompt and state placeholders

Supporting (not in the “unknown → answer” path but used by it):

- `src/core/state.py` – CoreState (lock_status, presence_display, mode_str)
- `src/core/brain.py` – used by live_brain when create_task + task_goal

---

## 6. What Was Not Done (Out of Scope)

- Memory transfer behavior
- Deep personality / tone / voice tuning
- Long-form behavior consolidation
- Changing Lumos identity text beyond what was already in the template

---

## 7. Confirmation

- **Lumos identity:** Still “Lumos”, Turkish default, state in prompt; no persona expansion.
- **State injection:** Active: runtime state is passed from `CoreState` and `general_approval` into `handle_live_brain` and then into `online_engine.process()` and the model client.
- **Active path:** Single, clear path from CLI input → parser → unknown+online → live_brain → online_engine → model_client → output.
- **Legacy path:** Documented and isolated; no removal of useful code; tests aligned with current behavior.
- **Diagnostics:** LLM errors logged, user message simple.

**Lumos core flow is stable and ready for memory transfer.**
