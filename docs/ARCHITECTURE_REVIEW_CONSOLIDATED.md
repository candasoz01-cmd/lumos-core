# Lumos Core — Architecture Review (Consolidated)

This document explains the current architecture, proposes a clean modular design for providers, suggests improvements to `lumos_core`, and outlines a revised folder structure.

---

## 1. Current Architecture

### 1.1 Main Components

| Component | Location | Role |
|-----------|----------|------|
| **CLI entry points** | `lumos.py`, `src/main.py`, `src/lumos_core/__main__.py` | Set env (e.g. `LUMOS_MODE`), then dispatch to interactive CLI, web, env, or ask. |
| **Interactive CLI** | `src/lumos_core/interactive_cli.py` | Main loop: "Sen:" prompt; handles **kilit**, **kamera**, **alias**, **durum**, **exit**. Uses `CoreEngine`, `CoreState`, lock/presence/keystore. Does **not** send free-form text to the AI router or `Lumos.respond()`. |
| **Simple CLI (ask/env)** | `src/lumos_core/cli.py` | `env` → device scan + capabilities; `ask` → routes prompt via **AIRouter** to a provider (e.g. OpenAI). |
| **Router** | `src/lumos_core/ai_router.py` | `AIRouter`: holds `dict[str, AIProvider]`, registers stubs for openai/gemini/anthropic, replaces openai with `OpenAIProvider` when `OPENAI_API_KEY` is set. `route(prompt, provider)` → `RouteResult(text, is_stub)`. |
| **Providers** | `src/lumos_core/ai_providers/openai.py` | `OpenAIProvider` implements `complete(prompt, **kwargs) -> str`. No shared base class; protocol defined in `ai_router.py`. Stub lives in same file as `_StubProvider`. |
| **Identity layer** | `src/lumos_core/security/identity.py`, `keystore.py` | `DeviceIdentity`: Ed25519 keypair, `identity.json`; `FileKeyStore`: root key from passphrase. Used by online engine and unlock flow. |
| **Core / policy** | `core/lumos.py`, `policy/rules.py`, `policy/offline_engine.py`, `engine/online_engine.py` | `Lumos.respond(ctx)` → session/note memory enrichment → `PolicyRules.evaluate()` → `engine.process(message)` (offline intents or online signed `ModelClient`). |
| **Engine duality** | `core/engine.py` vs `engine/base.py` | **CoreEngine**: lock/presence actions (injected callbacks). **BaseEngine** (and OfflineEngineV1 / OnlineEngineV1): policy “engine” with `process(message)` → response payload. |

### 1.2 Request Flows

**Flow A — `lumos ask "Explain X" --provider openai`**

1. `__main__.py` parses `ask` → `_run_ask(prompt, provider)` → `cli.run_ask(prompt, provider)`.
2. `run_ask` builds `AIRouter()`, calls `router.route(prompt, provider=provider)`.
3. `AIRouter` looks up `_providers["openai"]` (real `OpenAIProvider` if `OPENAI_API_KEY` set, else `_StubProvider`).
4. `impl.complete(prompt)` → response text.
5. `RouteResult(text, is_stub)` printed to stdout.

**Flow B — Interactive CLI "Sen: kilit ac"**

1. `interactive_cli.main()` → loop reads input, `normalize_command()` → e.g. route `"kilit"`, args `["ac"]`.
2. `lock_menu()` → `engine.unlock_with_passphrase(pw)` (CoreEngine callback) → keystore + `lumos.lock_state.unlock(root_key)`.
3. No use of `AIRouter` or `Lumos.respond()` in this loop.

**Flow C — Policy path (implemented but not wired in interactive loop)**

1. If something built a `Context(message=..., online=..., ...)` and called `lumos.respond(ctx)`:
2. Session memory and note memory enrich `ctx`.
3. `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)`:
   - Offline: `engine.process(message)` → OfflineEngineV1 intents (time, lock, perm status, etc.).
   - Online: unlock/identity checks, then `engine.process(message, short_context)` → OnlineEngineV1 → `ModelClient.generate(signed_payload)`.
4. `Decision.payload` → response/follow_up/debug combined and returned.

**Summary:** Today, **ask** uses the AI router + providers; the **interactive CLI** uses lock/presence/alias/durum and CoreEngine only; **Lumos.respond()** exists but is not used in the current interactive loop.

---

## 2. Clean Modular Architecture for Lumos Providers

### 2.1 Provider interface

- **Single protocol** in one place; optional base class for shared behavior (e.g. `is_available`, `get_display_name`).
- Use a `Protocol` so any class with `complete()` (and optionally `is_available`) can be used without inheritance.

**Suggested:** `src/lumos_core/ai_providers/base.py`

```python
from __future__ import annotations
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class AIProvider(Protocol):
    """Protocol for an AI provider. Implement complete() and optional metadata."""

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Send prompt to the provider and return the response text."""
        ...

    @property
    def is_available(self) -> bool:
        """True if the provider can be used (e.g. API key set)."""
        return True

    def get_display_name(self) -> str:
        """Human-readable name for CLI/UI."""
        return getattr(self, "name", self.__class__.__name__)
```

Optional abstract base for defaults:

```python
class BaseAIProvider:
    """Optional base: default is_available and get_display_name."""
    name: str = ""
    is_stub: bool = False

    @property
    def is_available(self) -> bool:
        return not self.is_stub

    def get_display_name(self) -> str:
        return self.name or self.__class__.__name__
```

### 2.2 Dynamic registration and optional providers

- **Registry**: One central place mapping provider name → factory (or instance). The router depends only on the registry, not on concrete provider modules.
- **Optional providers**: Each provider in its own module (or optional dependency). Register only when the module is present and, if desired, when config (e.g. API key) is present.

**Suggested:** `src/lumos_core/ai_providers/registry.py`

- `register(name, factory)` — register a callable that returns an `AIProvider`.
- `get_provider(name)` — return an instance or `None`.
- `list_providers()` / `list_available()` — for CLI and validation.
- `ensure_builtins()` — register stubs for openai/gemini/anthropic, then replace openai with `OpenAIProvider` when `OPENAI_API_KEY` is set. Optional providers (Gemini, Anthropic) can be registered inside `try/import` or from an optional package.

Router then:

- Calls `ensure_builtins()` once (e.g. in `__init__`).
- Uses only `get_provider(name)` and `list_providers()` / `list_available()`; no direct imports of provider classes.

This keeps the core package free of hard dependencies on Gemini/Anthropic while allowing them to be plugged in when installed.

### 2.3 Summary

- **Interface**: Single `AIProvider` protocol (+ optional `BaseAIProvider`) with `complete`, `is_available`, `get_display_name`.
- **Registration**: Registry with `register(name, factory)`; router uses `get_provider(name)` and `list_providers()` / `list_available()`.
- **Optional providers**: Register inside try/import or from an optional package; stubs for unconfigured or missing providers keep the CLI stable.

---

## 3. Improvements to lumos_core Architecture

### 3.1 Maintainability

- **Naming / single engine concept**: Two “engine” concepts exist: **CoreEngine** (lock/presence) and **BaseEngine** / OfflineEngineV1 / OnlineEngineV1 (policy/response). Rename for clarity:
  - Keep **CoreEngine** for “core system actions” (lock, presence).
  - Use **ResponseEngine** or **PolicyEngine** in docs and types for BaseEngine and its implementations; consider moving under `policy/` or keeping under `engine/` with a clear module doc.
- **Config in one place**: Replace scattered `os.environ.get("LUMOS_*")` and hardcoded `Path("src/.lumos")` / `.lumos` with a small **LumosConfig** (or extend `core/config.py`) loaded once (env + optional config file). Pass config (or base_dir, mode, etc.) into CLI and engines instead of reading env inside many modules.
- **Interactive CLI size**: Split `interactive_cli.py` into:
  - `interactive_cli/main.py`: entry, config, and main loop only.
  - `interactive_cli/lock_menu.py`, `presence_menu.py`, `alias_menu.py`: one module per menu; receive state/engine as arguments.
  - Keep `CoreState` and `CoreEngine` as the single source of truth.

### 3.2 Extensibility

- **Unify “ask” and “respond” (optional)**: To support free-form AI in the interactive “Sen:” loop, when the route is unknown (or a new route “chat”), build `Context(message=raw, ...)`, call `lumos.respond(ctx)`, or optionally call `AIRouter` for online provider routing.
- **Provider registry**: As in section 2, make the router depend on a registry so new providers (including third-party) can `register("name", factory)` without editing the router.
- **Hooks / events**: For auditing or extensions, add a simple hook list (e.g. `on_before_route`, `on_after_respond`) that `Lumos` or `AIRouter` calls so extensions can listen without changing core code.

### 3.3 Testability

- **Inject router and engines**: In `run_ask` and wherever the router is used, accept an optional `router: AIRouter` (default `AIRouter()`). Same for `Lumos(engine=...)` and the interactive CLI’s engine/state.
- **Config and paths**: Inject base_dir and config (or env dict) into identity, keystore, and scan so tests can use a temp directory and avoid touching real `src/.lumos` or `.lumos`.
- **Provider protocol**: Rely on the `AIProvider` protocol and small adapters in tests (e.g. a provider that returns a fixed string) so tests don’t need real API keys or network.

### 3.4 Separation of concerns

- **CLI vs core**: Keep CLI as a thin layer: parse args → call a function in lumos_core (e.g. `run_ask`, `run_env`, `run_interactive`). No business logic in CLI; core should be callable from another UI (e.g. web) without duplicating logic.
- **Identity/keystore**: Keep in `security/`; have the online engine and CLI receive an already-loaded identity/keystore (or a factory) so tests can substitute.
- **Policy vs engine**: `PolicyRules.evaluate()` should only decide allow/deny and pass through the engine’s payload; it shouldn’t know about HTTP or provider details. Keep “call external API” (ModelClient, or future use of AIRouter) inside the engine layer.

---

## 4. Revised Folder Structure (Proposal)

Goal: clearer boundaries, optional providers, and a single place for “response” logic.

```
lumos-core/
├── src/
│   ├── lumos_core/
│   │   ├── __init__.py
│   │   ├── __main__.py              # Entry: cli | web | env | ask
│   │   ├── version.py
│   │   │
│   │   ├── cli/                     # CLI layer (thin)
│   │   │   ├── __init__.py
│   │   │   ├── ask.py               # run_ask(), argparse for ask
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
│   │   │   ├── config.py            # LumosConfig (env + file)
│   │   │   ├── lumos.py
│   │   │   ├── state.py
│   │   │   ├── engine.py            # CoreEngine (lock/presence)
│   │   │   └── ...
│   │   │
│   │   ├── context/
│   │   ├── policy/                  # Policy + response engines
│   │   │   ├── rules.py
│   │   │   ├── offline_engine.py
│   │   │   └── ...
│   │   ├── engine/                  # Online + shared response client
│   │   │   ├── base.py              # BaseEngine / ResponseEngine protocol
│   │   │   ├── online_engine.py
│   │   │   └── model_client.py
│   │   │
│   │   ├── ai_router.py             # AIRouter (uses registry only)
│   │   ├── ai_providers/
│   │   │   ├── __init__.py          # Re-export protocol + registry
│   │   │   ├── base.py              # AIProvider protocol, BaseAIProvider
│   │   │   ├── registry.py          # register(), get_provider(), list_*
│   │   │   ├── stub.py              # StubProvider
│   │   │   ├── openai.py
│   │   │   └── (optional) gemini.py, anthropic.py or external pkg
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
├── web/
├── lumos-quantum/
├── tests/
└── docs/
```

**Changes vs current layout:**

- **cli/** groups all CLI: `ask`, `env`, and `interactive` (with submodules per menu). Entry stays `__main__.py`.
- **policy/** holds policy rules and offline “response” engine; **engine/** keeps online engine and model client. Naming (e.g. “response engine”) in docstrings and types makes the two “engine” concepts explicit.
- **ai_providers/** gets a clear **base** (protocol + optional base class), **registry**, and **stub**; router depends only on the registry.

You can adopt this incrementally (e.g. introduce registry and base first, then move CLI into `cli/` and split interactive menus).

---

## Summary

- **Current**: Two entry styles (lumos.py vs `python -m lumos_core`); interactive CLI does lock/presence/alias/durum only; `ask` uses AIRouter + OpenAI/stubs; `Lumos.respond()` is implemented but not used in the current loop; two “engine” concepts (CoreEngine vs Offline/Online engine).
- **Providers**: Define a single `AIProvider` protocol and a registry; register built-in and optional providers via factories; router uses only the registry for loose coupling and optional dependencies.
- **Improvements**: Clarify engine naming, centralize config, split interactive CLI, inject router/config/paths for tests, keep CLI thin and core reusable.
- **Structure**: Optional reorganization into `cli/` (with interactive submodules), clear `policy/` vs `engine/`, and a dedicated `ai_providers` base/registry/stub layout.
