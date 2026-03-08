# Lumos Core — Architecture Review

This document explains the current architecture, the provider design, suggested improvements, and a proposed folder structure. Code references point to the actual codebase.

---

## 1. Current Architecture

### 1.1 Main Components

| Component | Location | Role |
|-----------|----------|------|
| **CLI entry points** | `lumos.py` (root), `src/main.py`, `src/lumos_core/__main__.py` | `__main__.py` is the main entry: subcommands `cli` (default), `web`, `env`, `ask`, `chat`. Delegates to `cli.py` for ask/chat/env and to `interactive_cli` for cli. |
| **Simple CLI (ask/chat/env)** | `src/lumos_core/cli.py` | `run_ask` / `run_chat`: memory-save intent → `pre_route(ctx)` → if destination is provider, `AIRouter.route()` with `build_chat_context()`. `_run_env`: device scan + capabilities JSON. |
| **Interactive CLI** | `src/lumos_core/interactive_cli.py` | Single large file: main loop with "Sen:" prompt; commands **kilit**, **kamera**, **alias**, **durum**, **exit**. Uses `CoreEngine`, `CoreState`, `FileKeyStore`, presence lock. Does **not** call `AIRouter` or `Lumos.respond()`. |
| **Router** | `src/lumos_core/ai_router.py` | `AIRouter`: uses registry only (`ensure_builtins()`, `get_provider()`, `list_providers()`). `route(prompt, provider, **kwargs)` → system prompt + chat_context → `impl.complete(...)` → `RouteResult(text, is_stub)`. |
| **Providers** | `src/lumos_core/ai_providers/` | **Protocol** (`base.py`): `AIProvider` with `complete()`, `is_available`, `get_display_name()`. **Registry** (`registry.py`): `register(name, factory)`, `get_provider()`, `list_providers()` / `list_available()`. **OpenAI** (`openai.py`), **Stub** (`stub.py`) for unconfigured names. |
| **Identity layer** | `security/identity.py`, `security/keystore.py` | **DeviceIdentity**: Ed25519 keypair in `identity.json`; private key encrypted with root key. **FileKeyStore**: root key from passphrase; used by unlock flow and online engine. |
| **Core / policy** | `core/lumos.py`, `policy/rules.py`, `engine/` | **Lumos.respond(ctx)**: session/note memory enrich → `PolicyRules.evaluate(ctx, mode, confidence, engine)` → `engine.process(message)` (offline or online) → `Decision.payload` → response string. **Not** used by ask/chat or interactive CLI. |
| **Engine duality** | `core/engine.py` vs `engine/base.py` | **CoreEngine**: lock/presence **actions** (injected callbacks). **BaseEngine** + OfflineEngineV1 / OnlineEngineV1: policy **response** engine — `process(message)` → payload. |

### 1.2 Request Flows

**Flow A — `ask` / `chat` (e.g. `python -m lumos_core ask "Explain X" --provider openai`)**

1. `__main__.py` → `_run_ask(prompt, provider)` → `cli.run_ask(prompt, provider)`.
2. **Memory-save intent**: if prompt matches "bunu hatırla: ...", store preference and return.
3. Build `Context(message=prompt)`, call **pre_route(ctx)** (`policy/pre_route.py`). If `destination != "provider"` (unsupported, CLI command, or tool), print message and return.
4. Build `AIRouter()`, load user profile, `build_chat_context(user, approved_prefs, session_memory)`.
5. **router.route(prompt, provider, user_name=..., chat_context=...)**:
   - `ensure_builtins()` → registry has stubs for openai/gemini/anthropic; real OpenAI if `OPENAI_API_KEY` set.
   - `get_provider(provider)` → instance; allow stub or require `is_available` for real.
   - System prompt + chat context injected; `impl.complete(prompt, system_prompt=..., recent_messages=...)`.
6. `build_response(result.text, user)` → print (with `[stub]` prefix if applicable). In chat, session_memory.add_turn().

**Flow B — Interactive CLI ("Sen: kilit ac")**

1. `__main__.py` → `_run_cli()` → `interactive_cli.main()`.
2. Loop: input → `normalize_command(raw, base_dir, aliases)` → e.g. `("kilit", ["ac"])`.
3. `lock_menu()` (or similar) → `engine.unlock_with_passphrase(pw)` (CoreEngine) → keystore + `lumos.lock_state.unlock(root_key)`.
4. No AIRouter or Lumos.respond().

**Flow C — Policy path (Lumos.respond)**

1. Caller builds `Context(message=..., online=..., ...)` and calls `lumos.respond(ctx)` (e.g. from tests or backup main variants).
2. Session memory and note memory enrich `ctx`.
3. `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)` → offline: `engine.process(message)`; online: unlock/identity checks then engine with short_context.
4. `Decision.payload` → response/follow_up/debug combined and returned.

**Summary:** Ask/Chat use **pre_route + AIRouter + providers + memory**. Interactive CLI uses **CoreEngine + CoreState + keystore/presence** only. **Lumos.respond()** is implemented but not used by the current interactive loop or by ask/chat.

---

## 2. Clean Modular Architecture for Providers

The codebase **already** uses a protocol + registry pattern. Below: interface summary, dynamic registration, and how to add optional providers without coupling.

### 2.1 Provider Interface (Current + Small Refinements)

**Existing** (`ai_providers/base.py`):

- **AIProvider** (Protocol): `complete(prompt, **kwargs) -> str`, `is_available` (property), `get_display_name()`.
- **BaseAIProvider**: `name`, `is_stub`, default `is_available` / `get_display_name`.

**Suggestion:** Document in the protocol (or in a small `ChatRequest` dataclass) that kwargs may include `system_prompt`, `recent_messages`, `model` so all providers share the same contract. The router already passes these in `ai_router.py`.

Optional: explicit typed kwargs for clarity and forward compatibility:

```python
# Optional: ai_providers/base.py — document or add a TypedDict/dataclass
from typing import TypedDict

class ChatOptions(TypedDict, total=False):
    system_prompt: str
    recent_messages: list[dict[str, str]]
    model: str

# Protocol stays; complete(prompt, **kwargs) can accept ChatOptions
```

### 2.2 Dynamic Registration (Current)

Registry (`ai_providers/registry.py`) already provides:

- `register(name, factory)` — overwrites by name.
- `get_provider(name)` — returns instance or None.
- `list_providers()` / `list_available()`.
- `ensure_builtins()` — stubs for openai/gemini/anthropic; real OpenAI when `OPENAI_API_KEY` is set.

Router (`ai_router.py`) depends only on the registry; it does not import concrete provider modules. This is the right separation.

### 2.3 Optional Providers (Gemini, Anthropic) Without Tight Coupling

Keep core package free of hard dependencies on Gemini/Anthropic. Register them only when present and configured.

**Option A — Same repo, optional imports in registry**

In `registry.py`, extend `_register_builtins()` (or add `_register_optional()` called from `ensure_builtins()`):

```python
def _register_optional() -> None:
    """Register optional providers when package and config are present."""
    try:
        if os.environ.get("ANTHROPIC_API_KEY", "").strip():
            from lumos_core.ai_providers.anthropic import AnthropicProvider
            register("anthropic", lambda: AnthropicProvider())
    except ImportError:
        pass
    try:
        if os.environ.get("GEMINI_API_KEY", "").strip():
            from lumos_core.ai_providers.gemini import GeminiProvider
            register("gemini", lambda: GeminiProvider())
    except ImportError:
        pass
```

**Option B — External packages (e.g. lumos-provider-anthropic)**

Third-party or internal packages can register on import:

```python
# In lumos_provider_anthropic/__init__.py
from lumos_core.ai_providers.registry import register
from .provider import AnthropicProvider

def _register():
    import os
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        register("anthropic", lambda: AnthropicProvider())

_register()
```

User installs `lumos-core` and `lumos-provider-anthropic`; no change to core. Entry point or explicit import of the plugin triggers registration.

**Summary:** Keep a single **AIProvider** protocol and **registry**; router uses only the registry. Optional providers: same-repo try/import or separate package that calls `register()`.

---

## 3. Improvements to lumos_core

### 3.1 Maintainability

- **Engine naming:** Two concepts: (1) **CoreEngine** = lock/presence actions, (2) **BaseEngine** / OfflineEngineV1 / OnlineEngineV1 = policy/response. Rename for clarity, e.g. keep **CoreEngine**; rename the second to **ResponseEngine** or **PolicyEngine** in docs and type names (and optionally in code). A short module doc in `engine/base.py` and `core/engine.py` explaining "core actions vs response engine" helps.
- **Config in one place:** Replace scattered `os.environ.get("LUMOS_*")` and `Path("src/.lumos")` / `.lumos` with a single **LumosConfig** (or extend `core/config.py`): load once from env + optional config file. Pass config (or base_dir, mode) into CLI and engines instead of reading env in many modules.
- **Interactive CLI size:** Split `interactive_cli.py` into:
  - `interactive_cli/main.py`: entry, config, main loop only.
  - `interactive_cli/lock_menu.py`, `presence_menu.py`, `alias_menu.py`: one module per menu; receive state/engine as arguments.
  - Keep CoreState and CoreEngine as single source of truth.

### 3.2 Extensibility

- **Unify "Sen:" with AI (optional):** To support free-form AI in the interactive loop, when the normalized command is not kilit/kamera/alias/durum/exit, build `Context(message=raw, ...)`, call `pre_route(ctx)`; if `destination == "provider"`, call `AIRouter.route(...)` (and optionally run policy/identity via `Lumos.respond(ctx)` if you want one path). Reuses the same pre_route + router + memory as ask/chat.
- **Provider registry:** Already in place; document that third-party providers can `register(name, factory)`.
- **Hooks/events:** For auditing or extensions, add a simple hook list (e.g. `on_before_route`, `on_after_respond`) that AIRouter or Lumos calls so plugins can listen without changing core code.

### 3.3 Testability

- **Inject router:** In `run_ask` / `run_chat`, accept an optional `router: AIRouter | None = None`; use `router or AIRouter()`. Tests inject a router with stub or mock providers.
- **Inject config/paths:** Pass `base_dir` and config (or env dict) into identity, keystore, and device scan so tests use a temp directory and avoid real `src/.lumos` or `.lumos`.
- **Provider protocol:** Tests can pass a small adapter (e.g. a class with `complete(prompt, **kwargs) -> "fixed"`) that satisfies the protocol without API keys or network.

Example for `run_ask`:

```python
def run_ask(prompt: str, provider: str = "openai", router: AIRouter | None = None) -> None:
    ...
    r = router or AIRouter()
    result = r.route(prompt, provider=provider, ...)
```

### 3.4 Separation of Concerns

- **CLI vs core:** Keep CLI thin: parse args → call a function in lumos_core (`run_ask`, `run_env`, `run_interactive`). No business logic in CLI; core callable from web or another UI without duplication.
- **Identity/keystore:** Keep in `security/`; online engine and CLI receive an already-loaded identity/keystore (or factory) so tests can substitute.
- **Policy vs engine:** `PolicyRules.evaluate()` should only decide allow/deny and pass through the engine payload; HTTP/provider details stay in the engine layer (ModelClient, or future use of AIRouter inside the engine).

---

## 4. Revised Folder Structure (Proposal)

Goal: clearer boundaries, optional providers, single place for "response" logic.

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
│   │   │   └── interactive/        # Interactive CLI
│   │   │       ├── __init__.py
│   │   │       ├── main.py          # Loop, dispatch, config
│   │   │       ├── lock_menu.py
│   │   │       ├── presence_menu.py
│   │   │       └── alias_menu.py
│   │   │
│   │   ├── core/                    # Core app + system actions
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # LumosConfig (env + file)
│   │   │   ├── lumos.py             # Lumos, boot(), respond()
│   │   │   ├── state.py             # CoreState
│   │   │   ├── engine.py            # CoreEngine (lock/presence)
│   │   │   ├── version.py
│   │   │   └── logfmt.py
│   │   │
│   │   ├── context/
│   │   ├── policy/                  # Policy + offline response engine
│   │   │   ├── decision.py
│   │   │   ├── rules.py
│   │   │   ├── offline_engine.py
│   │   │   └── ...
│   │   │
│   │   ├── engine/                  # Online + shared response client
│   │   │   ├── base.py              # BaseEngine / ResponseEngine protocol
│   │   │   ├── online_engine.py
│   │   │   └── model_client.py
│   │   │
│   │   ├── ai_router.py             # AIRouter (uses registry only)
│   │   ├── ai_providers/
│   │   │   ├── base.py
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
├── web/
├── lumos-quantum/
├── tests/
└── docs/
```

**Changes vs current:**

- **cli/** groups all CLI: `ask`/`env` in one place, **interactive** as a subpackage with one module per menu. Entry stays `__main__.py`.
- **policy/** holds rules and offline response engine; **engine/** keeps online engine and model client. Naming (e.g. "response engine") in docstrings clarifies the two "engine" concepts.
- **ai_providers/** already has base, registry, stub; router depends only on registry.

Adopt incrementally: e.g. introduce optional router injection and config first, then move CLI into `cli/` and split interactive menus.

---

## Summary

- **Current:** Two entry styles (root `lumos.py` vs `python -m lumos_core`); interactive CLI does lock/presence/alias/durum only; ask/chat use pre_route + AIRouter + OpenAI/stubs + memory; `Lumos.respond()` is implemented but not used by the loop or ask/chat; two engine concepts (CoreEngine vs Offline/Online).
- **Providers:** Single **AIProvider** protocol and registry; register built-in and optional providers via factories; router uses only the registry; optional providers via try/import or external package.
- **Improvements:** Clarify engine naming, centralize config, split interactive CLI into smaller modules, inject router/config/paths for tests, keep CLI thin and core reusable.
- **Structure:** Optional reorganization into `cli/` (with interactive submodules), clear policy vs engine, and existing ai_providers base/registry/stub layout.
