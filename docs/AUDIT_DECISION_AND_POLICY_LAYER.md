# Lumos Audit: Response Quality, Policy, Intent, Identity, and Decision Consistency

**Goal:** Identify what already exists for identity enforcement, response policy, intent classification, command vs question separation, tool-needed detection, short-session context, and answer quality / decision consistency — without rewriting the architecture. Then propose a minimal v1 activation plan.

---

## 1. Relevant Existing Files

| File | Purpose |
|------|--------|
| **policy/rules.py** | `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)` — identity/lock gates (unlocked, lumos_id), confidence threshold, child mode; then calls `engine.process(message[, short_context])`. Returns `Decision(allow, reason, payload)`. Defines its own `Decision` dataclass inline. |
| **policy/decision.py** | Defines `Decision(allow, reason, payload)` with `Dict[str, Any]` — **not imported anywhere**; duplicate/orphan. |
| **policy/offline_engine.py** | `OfflineEngineV1`: intent classification via `_classify(lower_msg)` → DEVICE_TIME, PERM_STATUS, NETWORK_REQUIRED_WEATHER/FX, ACTION_SEND_SMS, ACTION_DRAFT_ORDER, GENERAL. Handles lock/unlock/time/perm/weather/fx/SMS/order and fallback “Anlayamadım.” No explicit “command vs question” or “tool-needed” layer. |
| **context/context.py** | `Context`: message, online, confidence, user_is_child, short_context, lumos_id, unlocked. Single struct used by the policy path. |
| **memory/session_memory.py** | `SessionMemory`: keeps last `max_items` (3) messages, builds `short_context = " \| ".join(history)`; `enrich(ctx)` sets `ctx.short_context`. Used only inside `Lumos.respond()`. |
| **memory/memory.py** | `Memory`: note memory (TTL, secure store); `enrich(ctx)` sets `ctx.memory_note_count`. Used only inside `Lumos.respond()`. |
| **core/lumos.py** | `Lumos.respond(ctx)`: lock state → session_memory.enrich → note_memory.enrich → PolicyRules.evaluate → engine.process; formats payload (response, reason, follow_up, debug). **Not called from ask/chat or interactive CLI.** |
| **engine/base.py** | `BaseEngine`: abstract `process(message) -> dict`. |
| **engine/base_engine.py** | Same idea (ABC, abstract `process`). **Note:** two base definitions (base.py vs base_engine.py). |
| **engine/online_engine.py** | `OnlineEngineV1`: loads identity (DeviceIdentity + passphrase), signs request; `process(message, short_context)` → ModelClient.generate. Identity enforced by presence of signer. |
| **security/identity.py** | `DeviceIdentity`: Ed25519, identity.json, lumos_id. Used by OnlineEngineV1 and init_identity. |
| **security/consent.py** | `has_user_consent()` — currently always `False`. Used in `__main__.py` to show onboarding when no consent. |
| **security/persistence_guard.py** | `require_consent()` — raises if no consent. **Not called from any live code path.** |
| **device/capabilities.py** | `classify(data)` — **environment** capability (can/limited/cannot for repo, python_env, disk, etc.). Not user intent. |
| **tools/file_classifier.py** | `classify_filename` / `scan_folder` — **file** category (sozlesme, dilekce, karar, etc.). Not chat intent. |
| **tools/run_classify.py** | CLI for file_classifier. Not used for conversation. |
| **ai_router.py** | Routes prompt to provider by name; no policy, no intent, no identity. |

---

## 2. What Exists vs Partially vs Unused

- **Identity enforcement**  
  **Exists and is implemented** in the **policy path only**: `PolicyRules.evaluate()` checks `unlocked` and `lumos_id` for online; `OnlineEngineV1` loads identity and signs requests. **Not in use** for ask/chat: they go straight to `AIRouter` and never build `Context` or call `Lumos.respond()`.

- **Response policy / safety rules**  
  **Exists** in `PolicyRules`: lock gate, identity gate, confidence threshold, child mode, then engine. **Partially implemented**: no content safety or “stay on Lumos” rule. **Unused** by ask/chat.

- **Intent classification**  
  **Exists** only in `OfflineEngineV1._classify()`: keyword/heuristic (time, perm, weather, fx, SMS, order) → intent string; then branch per intent. **Partial**: no explicit “command vs question” or “tool-needed” as separate concepts; no reuse for ask/chat.

- **Command vs question separation**  
  **Missing** as a dedicated layer. Offline engine effectively treats known phrases as commands and everything else as GENERAL/fallback; there is no shared “is_command” / “is_question” / “needs_tool” flag used elsewhere.

- **Tool-needed detection**  
  **Missing** for chat. Offline engine has “network required” and “action” intents but no generic “this request needs a tool” signal that could gate or shape provider calls.

- **Short-session conversational context**  
  **Exists**: `SessionMemory` builds `short_context` from last N messages and `Lumos.respond()` passes it to the engine. **Unused** by ask/chat (no session memory, no context object).

- **Answer quality / decision consistency**  
  **Partial**: `Decision(allow, reason, payload)` and structured response (response | reason | follow_up) exist in the policy path. **Unused** by ask/chat; provider output is printed raw (with optional [stub] prefix). No “Lumos identity” or “don’t go off-track” layer in front of the LLM.

- **Consent**  
  **Exists**: `has_user_consent()` (currently False), used for onboarding. `require_consent()` exists but is **not called** before any write.

---

## 3. Duplication and Orphans

- **Decision**: Defined in both `policy/rules.py` (used) and `policy/decision.py` (unused). Consolidate on one (e.g. `policy/decision.py`) and import in `rules.py`.
- **Base engine**: `engine/base.py` (simple class) and `engine/base_engine.py` (ABC). `core/lumos.py` imports `BaseEngine` from `engine.base`. One base is enough.

---

## 4. Reusable Parts (As-Is or With Minimal Wiring)

- **policy/rules.py** — Identity/lock/confidence/child gates; single entry `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)`. Reusable for any flow that builds `Context` and wants a decision.
- **context/context.py** — Already the carrier for message, online, short_context, lumos_id, unlocked, confidence, user_is_child. Reuse for ask/chat by building one Context per request.
- **memory/session_memory.py** — Builds short_context from history. Reuse by instantiating in the chat (or ask) flow and calling `enrich(ctx)` before evaluation.
- **policy/offline_engine.py** — Intent classification and command handling. Reusable as a **pre-step**: call `_classify` (or a small wrapper) to get intent; then either handle as command (existing branches) or pass “question” to provider. No need to duplicate intent logic.
- **security/identity.py** — Already used by OnlineEngineV1. For “Lumos stays in Lumos identity,” either use the existing online path (Lumos.respond with OnlineEngineV1) or pass identity/lumos_id into a thin gate before calling AIRouter.
- **core/lumos.py** — `Lumos.respond(ctx)` is the full pipeline. **Largest reuse**: route ask/chat through `respond()` instead of directly through AIRouter when you want policy + session + identity.

---

## 5. Missing Parts

- **Ask/chat use of policy path**: No code builds `Context` from the ask/chat prompt or calls `Lumos.respond()` or `PolicyRules.evaluate()` for those flows.
- **Explicit command vs question**: No shared “command” vs “question” (and optionally “tool_needed”) that both offline engine and chat can use.
- **Provider-side “decision consistency”**: No layer that (a) ensures responses are under Lumos identity, (b) avoids generic off-track answers, or (c) enforces request–response only (no autonomous suggestions). Could be: pre/post checks, system prompt, or a small “guard” that validates or rewrites.
- **Session in chat**: Chat loop does not maintain session memory or short_context; each line is independent.
- **Consent before writes**: `require_consent()` is never called; persistence can happen without consent.

---

## 6. Minimal v1 Activation Plan (Decision Consistency Layer)

**Objective:** Activate a minimal “decision consistency” path for v1: Lumos identity, distinguish question vs command/tool, avoid off-track generic answers, request–response only, no new autonomous suggestions, minimal and incremental.

**Step 1 — Wire ask/chat through the existing policy path (optional but maximal reuse)**  
- In the ask and chat flows, build `Context(message=user_input, online=..., unlocked=..., lumos_id=... from identity if available)`.  
- Option A: Call `Lumos.respond(ctx)` and use the existing engine (offline or online). Today offline engine does not call an LLM; online engine uses ModelClient (signed backend). So to keep using AIRouter (OpenAI, etc.), either:  
  - **Option B (minimal):** Keep sending to AIRouter but **before** that: (1) run identity/session in the same way as `Lumos.respond` (session_memory.enrich, set lumos_id/unlocked from current state), (2) run a single **pre-check** using existing policy + intent.

**Step 2 — Reuse intent for “command vs question” (minimal)**  
- In the path that serves ask/chat, call the same intent logic as OfflineEngineV1 (e.g. a thin wrapper around `_classify` or a single function that returns intent + “is_command”).  
- If `is_command` and intent is one of the handled ones (time, lock, perm, etc.): run existing offline engine branch (or return “use interactive CLI for lock/time”) and **do not** call the provider.  
- If not a handled command: treat as “question” and send to provider (AIRouter or, if wired, engine).  
- No new “tool-needed” model in v1; optional later.

**Step 3 — Identity and “Lumos identity”**  
- For **identity**: In the ask/chat path, if online mode and identity is required, load or receive `lumos_id` (and optionally sign) as today in OnlineEngineV1; otherwise pass through. Reuse `DeviceIdentity` and existing keystore/unlock state.  
- For **“Lumos stays in Lumos identity”** (no generic off-track answers): Minimal v1 = ensure the **request** is clearly scoped (e.g. system prompt or a one-line “answer as Lumos, request–response only”). No new guard code unless you add a simple post-check (e.g. reject if response is empty or too generic). Prefer reusing existing pipeline and a small prompt constraint.

**Step 4 — Request–response only, no autonomous suggestions**  
- No code changes needed if the product contract is “only respond when user writes.” Chat/ask already do that.  
- If the backend or provider can suggest follow-ups, constrain that in the **call site** (e.g. don’t display or don’t request suggestions) rather than a new subsystem.

**Step 5 — Consolidate Decision and document**  
- Use a single `Decision` (e.g. from `policy/decision.py`) and import it in `policy/rules.py`; remove the inline duplicate.  
- Add a short doc or comment: “Policy path: Context → session enrich → policy evaluate → engine.process; ask/chat can reuse by building Context and calling evaluate (and optionally Lumos.respond).”

---

## 7. Optional Follow-Up Code Changes (Minimal)

- **cli.py (ask) / chat loop**: Build `Context(message=prompt, online=False for now, ...)`. Optionally call `session_memory.enrich(ctx)` if you add a session for ask. Then either:  
  - Call `Lumos.respond(ctx)` and use engine only (no AIRouter), or  
  - Call a small **pre_route(ctx)** that: runs intent (reuse offline engine’s classify); if command → return structured response and do not call AIRouter; if question → call AIRouter and optionally attach `ctx.short_context` to the prompt.
- **Session in chat**: Instantiate `SessionMemory` in the chat flow; each turn: append user message, `enrich(ctx)`, then route. Gives short-session context with no new types.
- **policy/decision.py**: Make it the single source for `Decision`; in `policy/rules.py` use `from lumos_core.policy.decision import Decision` and remove the local dataclass.
- **Optional “guard”**: A single function `allow_provider_response(ctx, raw_response) -> bool` that returns False for empty or placeholder; call it before printing. No autonomous suggestion logic.

---

## 8. Summary Table

| Concern | Exists? | Where | Used by ask/chat? | Reuse for v1? |
|--------|---------|--------|--------------------|----------------|
| Identity enforcement | Yes | policy/rules.py, OnlineEngineV1, identity.py | No | Yes: wire Context + optional identity into ask/chat |
| Policy / safety rules | Yes (gates) | policy/rules.py | No | Yes: same evaluate() |
| Intent classification | Yes | offline_engine._classify | No | Yes: command vs question |
| Command vs question | No (implicit in offline) | — | — | Add via existing _classify |
| Tool-needed detection | No | — | — | Skip for v1 |
| Short-session context | Yes | session_memory.py | No | Yes: enrich(ctx) in chat |
| Decision consistency | Partial (Decision + payload) | lumos.respond, rules | No | Yes: route through respond or pre_route |
| Consent | Yes (stub) | consent.py, persistence_guard | Partially (onboarding) | Optional: call require_consent before writes |

**Minimum next step to activate a solid “decision consistency layer” for v1:**  
Use the existing policy path for ask/chat: build `Context`, optionally enrich with session memory, run `PolicyRules.evaluate` (and intent from offline engine); if allowed and “question,” send to AIRouter; otherwise return structured response. Unify `Decision` in one module. Add no new autonomous suggestions; keep request–response only.
