# Lumos Core — Architecture Review (Consolidated)

This document explains the current architecture, suggests a clean modular design for providers, improvements to `lumos_core`, and a revised folder structure. It is aligned with the actual codebase as of this review.

---

## 1. Current Architecture

### 1.1 Main Components

| Component | Location | Role |
|-----------|----------|------|
| **CLI entry points** | `lumos.py` (repo root), `src/main.py`, `src/lumos_core/__main__.py` | Set env (e.g. `LUMOS_MODE`, `LUMOS_DEBUG`), then dispatch to interactive CLI, web, env, ask, or chat. |
| **Interactive CLI** | `src/lumos_core/interactive_cli.py` | Main loop: "Sen:" prompt; handles **kilit**, **kamera**, **alias**, **durum**, **exit**. Uses `CoreEngine`, `CoreState`, lock/presence/keystore. Does **not** send free-form text to the AI router or `Lumos.respond()`. |
| **Simple CLI (ask/chat/env)** | `src/lumos_core/cli.py` | `env` → device scan + capabilities; `ask` / `chat` → pre_route → **AIRouter** → provider (e.g. OpenAI). `run_ask` / `run_chat` accept optional `router` for tests. |
| **Router** | `src/lumos_core/ai_router.py` | `AIRouter`: uses **registry** only (`ensure_builtins()`, `get_provider()`, `list_providers()`). `route(prompt, provider, **kwargs)` → `RouteResult(text, is_stub)`. Injects system prompt and chat context from memory. |
| **Providers** | `src/lumos_core/ai_providers/` | **Protocol**: `ai_providers/base.py` — `AIProvider` (Protocol) + `BaseAIProvider`. **Registry**: `registry.py` — `register()`, `get_provider()`, `list_providers()`, `list_available()`, `_register_builtins()`. **OpenAI**: `openai.py` — `OpenAIProvider(BaseAIProvider).complete(prompt, **kwargs)`. **Stub**: `stub.py` — `StubProvider` for unconfigured names. |
| **Identity layer** | `src/lumos_core/security/identity.py`, `keystore.py` | `DeviceIdentity`: Ed25519 keypair, `identity.json`; private key encrypted with root key. `FileKeyStore`: root key from passphrase. Used by online engine and unlock flow. |
| **Core / policy** | `core/lumos.py`, `policy/rules.py`, `policy/offline_engine.py`, `engine/online_engine.py` | `Lumos.respond(ctx)` → session/note memory enrichment → `PolicyRules.evaluate()` → `engine.process(message)` (offline intents or online signed `ModelClient`). |
| **Engine duality** | `core/engine.py` vs `engine/base.py` | **CoreEngine**: lock/presence actions (injected callbacks). **BaseEngine**: abstract `process(message)` → payload. **OfflineEngineV1** / **OnlineEngineV1**: concrete policy “response” engines. |

### 1.2 Request Flows

**Flow A — `lumos ask "Explain X" --provider openai` (or `python -m lumos_core ask ...`)**

1. `__main__.py` or `cli.main()` parses `ask` → `run_ask(prompt, provider)`.
2. **Pre-route**: `pre_route(Context(message=prompt))` → if destination is not `"provider"` (e.g. CLI command, relay, device phrase), print message and return.
3. **Memory**: `load_user_profile()`, `build_chat_context(user, approved_prefs, session_memory=None)`.
4. **Router**: `AIRouter().route(prompt, provider=provider, user_name=..., chat_context=...)` → `ensure_builtins()` → `get_provider(provider)` → `impl.complete(prompt, system_prompt=..., recent_messages=...)` → `RouteResult(text, is_stub)`.
5. **Output**: `build_response(result.text, user)` and print (with optional `[stub]` prefix).

**Flow B — Interactive CLI "Sen: kilit ac"**

1. `interactive_cli.main()` → loop reads input, normalizes command (e.g. `"kilit"`, args `["ac"]`).
2. `lock_menu()` → `engine.unlock_with_passphrase(pw)` (CoreEngine callback) → keystore + `lumos.lock_state.unlock(root_key)`.
3. No use of `AIRouter` or `Lumos.respond()` in this loop.

**Flow C — Policy path (Lumos.respond)**

1. If something builds `Context(message=..., online=..., ...)` and calls `lumos.respond(ctx)`:
2. Session memory and note memory enrich `ctx`.
3. `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)`:
   - Offline: `engine.process(message)` → OfflineEngineV1 intents (time, lock, perm status, etc.).
   - Online: unlock/identity checks, then `engine.process(message, short_context)` → OnlineEngineV1 → `ModelClient.generate(signed_payload)`.
4. `Decision.payload` → response/follow_up/debug combined and returned.

**Summary**: **Ask/Chat** use **pre_route + AI router + providers**. **Interactive CLI** uses **lock/presence/alias/durum** and **CoreEngine** only. **Lumos.respond()** is implemented but not wired in the current interactive loop.

---

## 2. Clean Modular Architecture for Lumos Providers

The codebase **already** has a solid base: `AIProvider` protocol, `BaseAIProvider`, registry with factories, and router that depends only on the registry. Below are refinements and patterns for optional providers.

### 2.1 Provider Interface (current + small extensions)

Current protocol in `ai_providers/base.py` is good. Optional: add a clear `name` and `is_stub` in the protocol for type-friendly use:

```python
# src/lumos_core/ai_providers/base.py (optional extension)
@runtime_checkable
class AIProvider(Protocol):
    def complete(self, prompt: str, **kwargs: Any) -> str: ...
    @property
    def is_available(self) -> bool: ...
    def get_display_name(self) -> str: ...
    # Optional for router/CLI:
    # @property
    # def is_stub(self) -> bool: return getattr(self, "is_stub", True)
```

Keep `BaseAIProvider` with `name`, `is_stub`, and default `is_available` / `get_display_name` so concrete providers stay minimal.

### 2.2 Dynamic Registration (already in place)

- **Registry** (`ai_providers/registry.py`): `register(name, factory)`, `get_provider(name)`, `list_providers()`, `list_available()`, `ensure_builtins()`.
- **Router** (`ai_router.py`): uses only `ensure_builtins`, `get_provider`, `list_providers`; no direct imports of OpenAI/Gemini/Anthropic.
- **Builtins**: stubs for `openai`, `gemini`, `anthropic`; replace `openai` with `OpenAIProvider` when `OPENAI_API_KEY` is set and `openai` package is importable.

No structural change required; the design is already decoupled.

### 2.3 Optional Providers (Gemini, Anthropic) Without Tight Coupling

- Keep each optional provider in its own module (or optional package). Register only when the module is present and, if desired, when config (e.g. API key) is present.
- In `_register_builtins()` (or a separate `_register_optional()` called from `ensure_builtins()`), use try/import and env checks:

```python
# In registry.py, extend _register_builtins() or add:
def _register_optional() -> None:
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        try:
            from lumos_core.ai_providers.anthropic import AnthropicProvider
            register("anthropic", lambda: AnthropicProvider())
        except ImportError:
            pass
    if os.environ.get("GEMINI_API_KEY", "").strip():  # or GOOGLE_API_KEY
        try:
            from lumos_core.ai_providers.gemini import GeminiProvider
            register("gemini", lambda: GeminiProvider())
        except ImportError:
            pass

def ensure_builtins() -> None:
    global _BUILTINS_LOADED
    if not _BUILTINS_LOADED:
        _register_builtins()
        _register_optional()  # add this
        _BUILTINS_LOADED = True
```

- Alternatively, use optional extras and entry points so that `lumos_core_anthropic` / `lumos_core_gemini` register on import:

```python
# In lumos_core_anthropic/plugin.py
from lumos_core.ai_providers.registry import register
from .provider import AnthropicProvider
register("anthropic", lambda: AnthropicProvider())
```

Then document that installing `lumos-core[anthropic]` triggers registration. Core stays free of hard dependencies on Gemini/Anthropic.

### 2.4 Summary (Providers)

- **Interface**: Keep single `AIProvider` protocol and `BaseAIProvider`; optional protocol fields for `is_stub`/`name` if you want stricter typing.
- **Registration**: Already registry-based; router already uses only the registry.
- **Optional providers**: Register in `_register_optional()` with try/import + env, or via optional packages that call `register()` on import.

---

## 3. Improvements to lumos_core Architecture

### 3.1 Maintainability

- **Engine naming**: Two concepts exist — **CoreEngine** (lock/presence) and **BaseEngine** / OfflineEngineV1 / OnlineEngineV1 (policy/response). Rename for clarity:
  - Keep **CoreEngine** for “core system actions” (lock, presence).
  - Use **ResponseEngine** or **PolicyEngine** in docs and types for BaseEngine and its implementations; consider moving offline/online engines under `policy/` or keeping under `engine/` with a clear module doc that states “response/policy engine, not core actions”.
- **Config**: Centralize env and paths. Use `core/config.py` (already has `load_config`, `load_presence_from_config`) and introduce a small `LumosConfig` (or extend existing) for `LUMOS_MODE`, `LUMOS_DEBUG`, base_dir (e.g. `src/.lumos` vs `.lumos`), and optionally API keys. Load once and pass into CLI and engines instead of reading `os.environ` and `Path("src/.lumos")` in many modules. `lumos.py` and identity already use `src/.lumos` / `.lumos`; this should be one configurable base_dir.
- **Interactive CLI size**: Split `interactive_cli.py` into a small package:
  - `interactive_cli/main.py`: entry, config, main loop, dispatch.
  - `interactive_cli/lock_menu.py`, `presence_menu.py`, `alias_menu.py`: one module per menu; receive state/engine as arguments.
  - Keep `CoreState` and `CoreEngine` as the single source of truth.

### 3.2 Extensibility

- **Unify “Sen:” with AI (optional)**: To support free-form AI in the interactive loop, when the route is “unknown” or a new “chat” route, build `Context(message=raw, ...)`, call `lumos.respond(ctx)`, or alternatively call `AIRouter.route(...)` and print the result. That way the same entry point can drive both commands and AI replies.
- **Provider registry**: Already in place; document that third-party or optional packages can call `register("name", factory)` without editing the router.
- **Hooks / events**: Add optional hooks (e.g. `on_before_route`, `on_after_respond`) that `AIRouter` or `Lumos` call so extensions can observe or audit without changing core code.

### 3.3 Testability

- **Inject router**: `run_ask` and `run_chat` already accept optional `router: AIRouter | None`; tests can inject a router with stub or mock providers.
- **Inject config and paths**: Pass `base_dir` and config (or env dict) into identity, keystore, and device scan so tests can use a temp directory and avoid touching real `src/.lumos` or `.lumos`. Same for `Lumos` and engines.
- **Provider protocol**: Tests can pass a small object implementing `complete`, `is_available`, and optionally `is_stub` without real API keys or network.

### 3.4 Separation of Concerns

- **CLI vs core**: Keep CLI thin: parse args → call `run_ask`, `run_chat`, `run_env`, or interactive `main()`. No business logic in CLI; core should be callable from web or another UI without duplicating logic.
- **Identity/keystore**: Keep in `security/`; online engine and CLI receive an already-loaded identity/keystore (or factory) so tests can substitute.
- **Policy vs engine**: `PolicyRules.evaluate()` should only decide allow/deny and pass through the engine’s payload; “call external API” (ModelClient or future use of AIRouter) stays inside the engine layer.
- **Pre-route vs router**: Pre-route handles “is this a command or tool?”; router handles “which provider and how to call it.” Keep pre-route independent of provider list.

---

## 4. Revised Folder Structure (Proposal)

Goal: clearer boundaries, optional providers, single place for “response” logic, and a thin CLI layer.

```
lumos-core/
├── src/
│   ├── lumos_core/
│   │   ├── __init__.py
│   │   ├── __main__.py              # Entry: cli | web | env | ask | chat
│   │   ├── version.py
│   │   │
│   │   ├── cli/                     # CLI layer (thin)
│   │   │   ├── __init__.py
│   │   │   ├── ask.py               # run_ask(), run_chat()
│   │   │   ├── env.py               # _run_env, device scan + report
│   │   │   └── interactive/
│   │   │       ├── __init__.py
│   │   │       ├── main.py          # Loop, dispatch, config
│   │   │       ├── lock_menu.py
│   │   │       ├── presence_menu.py
│   │   │       └── alias_menu.py
│   │   │
│   │   ├── core/                    # Core app + system actions
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # LumosConfig (env + file), load_config
│   │   │   ├── lumos.py             # Lumos, boot(), respond()
│   │   │   ├── state.py             # CoreState
│   │   │   ├── engine.py            # CoreEngine (lock/presence)
│   │   │   ├── version.py
│   │   │   └── logfmt.py
│   │   │
│   │   ├── context/
│   │   │   ├── __init__.py
│   │   │   └── context.py
│   │   │
│   │   ├── policy/                  # Policy + response engines
│   │   │   ├── __init__.py
│   │   │   ├── decision.py
│   │   │   ├── rules.py
│   │   │   ├── pre_route.py
│   │   │   ├── offline_engine.py
│   │   │   └── ...
│   │   │
│   │   ├── engine/                  # Online + shared “response” client
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseEngine / ResponseEngine protocol
│   │   │   ├── online_engine.py
│   │   │   └── model_client.py
│   │   │
│   │   ├── ai_router.py             # AIRouter (uses registry only)
│   │   │
│   │   ├── ai_providers/
│   │   │   ├── __init__.py          # Re-export protocol + registry
│   │   │   ├── base.py              # AIProvider protocol, BaseAIProvider
│   │   │   ├── registry.py
│   │   │   ├── stub.py
│   │   │   ├── openai.py
│   │   │   └── (optional) anthropic.py, gemini.py or external pkg
│   │   │
│   │   ├── memory/
│   │   ├── security/
│   │   ├── device/
│   │   ├── system/
│   │   ├── tools/
│   │   ├── ui/
│   │   └── scripts/
│   │
│   └── main.py                      # Redirect to lumos_core
│
├── lumos.py                         # Optional top-level entry (env + dispatch)
├── web/
├── lumos-quantum/
├── tests/
└── docs/
```

**Changes compared to current layout:**

- **cli/** groups all CLI: `ask`/`chat`, `env`, and `interactive` with submodules per menu. Entry remains `__main__.py`; current `cli.py` is split into `cli/ask.py` and `cli/env.py`, and `interactive_cli` becomes `cli/interactive/`.
- **policy/** holds rules, decision, pre_route, and offline engine; **engine/** keeps online engine and model client. Naming in docstrings (e.g. “response engine”) makes the two “engine” concepts explicit.
- **ai_providers/** already has base, registry, stub, openai; add optional anthropic/gemini modules or document entry-point registration from optional packages.

You can adopt this incrementally: e.g. introduce `_register_optional()` and config first, then move CLI into `cli/` and split interactive menus.

---

## Summary

- **Current**: Two entry styles (`lumos.py` vs `python -m lumos_core`); interactive CLI does lock/presence/alias/durum only; ask/chat use pre_route + AIRouter + OpenAI/stubs; `Lumos.respond()` exists but is not used in the interactive loop; two “engine” concepts (CoreEngine vs Offline/Online engine). Provider design is already registry-based and protocol-driven.
- **Providers**: Keep single `AIProvider` protocol and registry; add optional providers via `_register_optional()` (try/import + env) or optional packages that register on import.
- **Improvements**: Clarify engine naming, centralize config and base_dir, split interactive CLI into smaller modules, inject router/config/paths for tests, keep CLI thin and core reusable, optional hooks for extensibility.
- **Structure**: Optional reorganization into `cli/` (with ask, env, interactive submodules), clear `policy/` vs `engine/`, and keep the existing `ai_providers` base/registry/stub layout.
