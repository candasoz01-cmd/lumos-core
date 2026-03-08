# Lumos Audit: Response Quality, Decision Consistency, Policy, Intent, Identity, Context

**Goal:** Identify existing logic for identity enforcement, response policy/safety, intent classification, command vs question separation, tool detection, short-session context, and answer quality/decision consistency. No architecture rewrite; findings and minimal v1 activation plan only.

---

## 1. Relevant Existing Files

| File | Purpose |
|------|--------|
| **policy/decision.py** | `Decision(allow, reason, payload)` for PolicyRules; `PreRouteResult(destination, message)` and `PreRouteDestination` ("provider" \| "tool" \| "tool_not_implemented" \| "unsupported") for pre_route. |
| **policy/rules.py** | `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)` → Decision. Enforces: offline vs online; when online: unlocked, lumos_id, confidence_threshold, user_is_child; then engine.process(). |
| **policy/pre_route.py** | Pre-route layer for ask/chat: runs **before** AIRouter. Uses OfflineEngineV1._classify(), command phrases, relay/device patterns, read-only tools. Returns PreRouteResult: send to provider vs show Lumos message. |
| **policy/offline_engine.py** | `OfflineEngineV1`: `process(message)` and `_classify(lower_msg)` → DEVICE_TIME, PERM_STATUS, NETWORK_REQUIRED_*, ACTION_SEND_SMS, ACTION_DRAFT_ORDER, GENERAL. Keyword/heuristic intent classification (no ML). |
| **context/context.py** | `Context`: message, online, confidence, user_is_child, short_context, lumos_id, unlocked, current_file. Single request-scoped context. |
| **security/identity.py** | `DeviceIdentity`: Ed25519 keypair, identity.json, lumos_id = sha256(public_key). Used by online engine and init scripts. |
| **security/consent.py** | `has_user_consent()` → bool (currently always False). Gate before persistence. |
| **security/persistence_guard.py** | `require_consent()`: raises if no consent. Not yet called from ask/chat persistence paths. |
| **memory/memory_manager.py** | `create_session_memory()`, `load_user_profile()`, `build_chat_context()`, `parse_memory_save_intent()`, `format_user_memory_for_context()`. Single entry for chat context. |
| **memory/session_memory.py** | `SessionMemory`: bounded recent messages + rolling summary; `enrich(ctx)` sets ctx.short_context; not persisted. |
| **memory/user_memory.py** | Approved preferences (user_memory.json); add_approved_preference, load_approved_preferences. |
| **user_identity.py** | `UserIdentity`: name, address_mode, preferred_address (user_preferences.json). Distinct from device identity. |
| **engine/online_engine.py** | OnlineEngineV1: loads DeviceIdentity with root key, sets lumos_id; process(message, short_context) → signed ModelClient. Used when Lumos.respond() runs in online mode. |
| **core/lumos.py** | `Lumos.respond(ctx)`: session_memory.enrich → note_memory.enrich → PolicyRules.evaluate → engine.process; returns combined response or None. **Not called from ask/chat or interactive_cli.** |
| **cli.py** | `run_ask` / `run_chat`: pre_route(ctx) → if destination != "provider" show route.message; else build_chat_context + router.route() + build_response. Memory-save intent handled before pre_route. |
| **ai_router.py** | `AIRouter.route(prompt, provider, **kwargs)`: chat_context (from build_chat_context), user_name; passes system_prompt + chat_context_suffix to provider. |
| **system_prompt.py** | `get_system_prompt(user_name)`: Lumos persona, transparency, no actions without approval, user control and safety. |
| **response_builder.py** | `build_response(response_text, user)`: applies UserIdentity address preference (fixed + preferred_address prefix). |
| **tools/file_tools.py** | Read-only file read: try_handle_read_file(msg, cwd, current_file). |
| **tools/project_tools.py** | Read-only project structure: try_handle_project_structure(msg, cwd). |
| **tools/system_tools.py** | Read-only system: cwd, list dir, python version, disk, system info; try_handle_readonly_tool(msg). |

---

## 2. What Exists vs Partially Implemented vs Unused vs Duplicated

### Implemented and in use (ask/chat)

- **pre_route (policy/pre_route.py):** Command vs question separation; tool-needed detection (read-only file/project/system); intent-based routing via OfflineEngineV1._classify(). Returns Lumos message for CLI commands, relay, device/system, time, perm, weather, FX, SMS, order; sends to provider only for GENERAL.
- **Context:** Used in ask/chat (Context(message=…)); short_context set by SessionMemory in chat.
- **Short-session context:** SessionMemory (bounded window + rolling summary); build_chat_context(user, prefs, session_memory); passed as chat_context to ai_router.route().
- **User identity (preferences):** UserIdentity (name, address_mode, preferred_address); load_user_profile(); build_response() applies address preference.
- **System prompt:** get_system_prompt(user_name); instructions on transparency, user control, safety.
- **Memory-save intent:** parse_memory_save_intent(); "bunu hatırla ..." handled in ask/chat before pre_route; stored via add_approved_preference.

### Partially implemented

- **Identity enforcement (device):** PolicyRules.evaluate() checks ctx.lumos_id and ctx.unlocked for **online** mode. That path is only used by `Lumos.respond()`. Ask/chat **do not** call Lumos.respond(); they never set ctx.lumos_id or run PolicyRules. So device identity is enforced only on the respond() path, which is currently unused from CLI.
- **Consent:** has_user_consent() always False; persistence_guard.require_consent() exists but is not called before user_memory or log writes in ask/chat.

### Unused but valuable

- **PolicyRules + Decision (policy/rules.py):** Full gate: offline → engine.process; online → check unlocked, lumos_id, confidence, user_is_child → engine.process. Only used in core/lumos.py respond(). No caller from ask/chat or interactive_cli.
- **Lumos.respond():** Complete flow (session + note memory enrich → PolicyRules → engine). Could be the single “decision consistency” entry point if ask/chat fed into it instead of bypassing it.
- **confidence_threshold / user_is_child:** In PolicyRules only; never set in ask/chat Context (default confidence 1.0, user_is_child False in Context).

### Duplication / two paths

- **Two entry paths to “answer”:**
  1. **ask/chat:** Context(message) → pre_route → (if provider) AIRouter.route() → build_response. No PolicyRules, no device identity check, no confidence.
  2. **Lumos.respond():** Context → session/note enrich → PolicyRules.evaluate() → engine.process (offline or online). Not used by ask/chat.
- **Intent classification:** OfflineEngineV1._classify() is used both in offline_engine.process() (for respond path) and in pre_route (for ask/chat). Same intents, no duplication of logic.

---

## 3. Reusable Parts

- **pre_route(ctx):** Already does command vs question and tool-needed detection; returns PreRouteResult. Keep using it before any provider call in ask/chat.
- **OfflineEngineV1._classify(lower_msg):** Single place for intent (DEVICE_TIME, PERM_STATUS, NETWORK_*, ACTION_*, GENERAL). Reuse for any new “decision layer” that needs intent.
- **PolicyRules.evaluate(ctx, mode, confidence_threshold, engine):** Reusable for a v1 “decision consistency” layer if ask/chat build a full Context (including lumos_id, unlocked when applicable) and call it before AIRouter.
- **Context:** Already has all fields needed for policy (message, online, confidence, user_is_child, short_context, lumos_id, unlocked). Ask/chat can fill lumos_id/unlocked from device identity when desired.
- **Decision / PreRouteResult:** Clear types; no need to replace.
- **system_prompt (get_system_prompt):** Already pushes “Lumos identity”, no unapproved actions, safety. Can be extended with “request-response only” / “no autonomous suggestions” if needed.
- **SessionMemory + build_chat_context:** Already provide short-session context; keep as single wiring point.

---

## 4. Missing Parts

- **Identity enforcement on ask/chat:** Device identity (lumos_id) and lock state are not checked in the ask/chat path. If “Lumos stays in Lumos identity” means “only respond when device identity is present and optionally unlocked”, that gate exists in PolicyRules but is not invoked from ask/chat.
- **Single “decision consistency” entry point:** No single place that (1) enforces identity, (2) applies policy, (3) then routes to provider. respond() does (1)+(2)+engine; ask/chat do pre_route + router only.
- **Explicit “answer quality” or “off-track” layer:** No code that checks response content for quality, consistency, or off-track generic answers. System prompt is the only lever.
- **Consent before persistence:** require_consent() not called before writing user_memory or logs in ask/chat.
- **Policy __init__.py:** policy package has empty __init__; no impact on behavior.

---

## 5. Minimal v1 Activation Plan (Decision Consistency Layer)

Objective: Reuse existing code so that Lumos (1) stays in Lumos identity, (2) distinguishes normal question vs command/tool, (3) avoids generic off-track answers only via system prompt (no new quality checker), (4) stays request-response only, (5) no autonomous suggestions, (6) minimal, incremental changes.

### Step 1: Wire identity into ask/chat Context (optional but recommended)

- In `cli.run_ask` and `cli.run_chat`, after building `Context(message=...)`, optionally set:
  - `ctx.lumos_id`: from DeviceIdentity if available (read identity.json lumos_id when present; no unlock required for read).
  - `ctx.unlocked`: False in ask/chat unless you later add an explicit “unlock for this session” step.
- This does not change behavior yet; it only makes Context ready for PolicyRules.

### Step 2: Call PolicyRules (or a thin wrapper) before AIRouter in ask/chat

- **Option A (minimal):** Keep current flow; add a single “policy gate” function used only in ask/chat, e.g. `policy_gate_for_ask_chat(ctx) -> tuple[bool, str | None]`: returns (True, None) to proceed to provider, or (False, message) to show a Lumos message and skip the provider.
  - Inside: if ctx.lumos_id is required for “identity enforcement”, check it and return (False, "Kimlik yok...") when missing.
  - Reuse PolicyRules.evaluate logic only for the identity/unlock/confidence part, or call PolicyRules.evaluate with a no-op engine that returns allow=True and payload=None when you only want the gate (allow/deny).
- **Option B (reuse respond path):** In ask/chat, build full Context (with lumos_id, unlocked, mode, confidence, user_is_child), then call `Lumos.respond(ctx)`. If respond() returns a string, show it; if None, optionally fall back to “blocked” message. If you want provider answers in ask/chat, respond() would need to call AIRouter when engine returns “use provider” (e.g. when offline engine returns GENERAL with a special payload). That is a larger change; not minimal.

**Recommendation:** Option A. Add `policy_gate_for_ask_chat(ctx)` in policy (or cli) that:
- Checks lumos_id if you want “Lumos identity required” (or skip check for v1 to keep behavior unchanged).
- Returns (True, None) to continue to pre_route + AIRouter, or (False, message) to print message and return.
- Call it in run_ask and run_chat after building ctx, before pre_route. If gate returns (False, msg), print msg and return/continue.

### Step 3: Harden system prompt (no new modules)

- In `system_prompt.get_system_prompt()`, add one or two short lines: e.g. “Answer only the user’s request. Do not suggest unrelated topics or actions unless the user asks.” to reinforce request-response only and no autonomous suggestions. No new code paths.

### Step 4: Keep pre_route as the only command/tool/router

- No change. pre_route already ensures: command/tool → Lumos message; only GENERAL → provider. No duplication.

### Step 5 (optional): Consent before persistence

- Before any write to user_memory or user_preferences in cli or memory_manager, call `require_consent()` (or check has_user_consent() and skip write). Prevents persistence until consent is implemented. Minimal and incremental.

---

## 6. Optional Follow-Up Code Changes (Minimal)

- **policy/pre_route.py or policy/rules.py:** Add `policy_gate_for_ask_chat(ctx: Context) -> tuple[bool, str | None]`. Implementation: if identity required, read lumos_id from identity.json (or from a small helper that returns current device lumos_id or ""); if empty, return (False, "Lumos: Kimlik yok. python -m lumos_core.scripts.init_identity"); else return (True, None).
- **cli.py (run_ask, run_chat):** After `ctx = Context(message=...)`, call `policy_gate_for_ask_chat(ctx)`. If (False, msg), print msg and return/continue; else proceed to pre_route.
- **system_prompt.py:** Append one line to base: e.g. “Answer only what the user asked; do not suggest other actions or topics unless asked.”
- **memory_manager or user_memory (write paths):** Add `require_consent()` (or has_user_consent() check) before writing. Optional for v1.

No refactor of unrelated files; no new subsystems. Reuse PolicyRules concepts (identity check) and keep pre_route as the single command/tool/question split.

---

## 7. Summary Table

| Concern | Exists | Where | Used in ask/chat? |
|--------|--------|-------|-------------------|
| Identity enforcement (device) | Yes | PolicyRules (lumos_id, unlocked) | No |
| Response policy / safety rules | Partially | PolicyRules (online gate); system_prompt | System prompt yes; PolicyRules no |
| Intent classification | Yes | OfflineEngineV1._classify | Via pre_route yes |
| Command vs question separation | Yes | pre_route (phrases, prefixes, relay, device) | Yes |
| Tool-needed detection | Yes | pre_route + file/project/system tools | Yes |
| Short-session context | Yes | SessionMemory, build_chat_context | Yes (chat) |
| Answer quality / decision consistency | Only system prompt | system_prompt.py | Yes |
| Consent gate | Yes | consent.py, persistence_guard | Not wired to writes |

**Minimum next step to activate a solid “decision consistency layer” for v1:** Add a small policy gate (e.g. `policy_gate_for_ask_chat`) that optionally enforces lumos_id before provider call; call it from run_ask and run_chat. Optionally tighten system prompt for request-response only and no autonomous suggestions. Reuse pre_route and existing Context; no new architecture.
