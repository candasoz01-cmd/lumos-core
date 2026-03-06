# Lumos Core — Architecture Review

This document describes the current architecture, suggests a clean modular design for providers, improvements to `lumos_core`, and a revised folder structure.

---

## 1. Current Architecture

### 1.1 Main Components

| Component | Location | Role |
|-----------|----------|------|
| **CLI entry points** | `lumos.py`, `src/main.py`, `src/lumos_core/__main__.py` | Set env (e.g. `LUMOS_MODE`), then dispatch to interactive CLI, web, env, or ask. |
| **Interactive CLI** | `src/lumos_core/interactive_cli.py` | Main loop: "Sen:" prompt; handles **kilit**, **kamera**, **alias**, **durum**, **exit**. Uses `Lumos`, `CoreEngine`, `CoreState`, lock/presence/keystore. |
| **Simple CLI (ask/env)** | `src/lumos_core/cli.py` | `env` → device scan + capabilities; `ask` → routes prompt via **AIRouter** to a provider (e.g. OpenAI). |
| **Router** | `src/lumos_core/ai_router.py` | `AIRouter`: holds a `dict[str, AIProvider]`, starts with stubs for openai/gemini/anthropic, replaces openai with `OpenAIProvider` when `OPENAI_API_KEY` is set. `route(prompt, provider)` → `RouteResult(text, is_stub)`. |
| **Providers** | `src/lumos_core/ai_providers/openai.py` | `OpenAIProvider` implements `complete(prompt, **kwargs) -> str`. No shared base class; protocol in `ai_router`. |
| **Identity layer** | `src/lumos_core/security/identity.py`, `keystore.py` | `DeviceIdentity`: Ed25519 keypair, `identity.json`; `FileKeyStore`: root key from passphrase. Used by online engine and unlock flow. |
| **Core / policy** | `core/lumos.py`, `policy/rules.py`, `policy/offline_engine.py`, `engine/online_engine.py` | `Lumos.respond(ctx)` → session/note memory enrichment → `PolicyRules.evaluate()` → `engine.process(message)` (offline intents or online signed `ModelClient`). |
| **Engine duality** | `core/engine.py` vs `engine/base.py` | **CoreEngine**: lock/presence actions (injected callbacks). **BaseEngine** (and `OfflineEngineV1` / `OnlineEngineV1`): policy “engine” with `process(message)` → response payload. |

### 1.2 Request Flows

**Flow A — `lumos ask "Explain X" --provider openai`**

1. `__main__.py` or `cli` parses `ask` → `run_ask(prompt, provider)`.
2. `run_ask` builds `AIRouter()`, calls `router.route(prompt, provider=provider)`.
3. `AIRouter` looks up `_providers["openai"]` (real `OpenAIProvider` if `OPENAI_API_KEY` set, else `_StubProvider`).
4. `impl.complete(prompt)` → response text.
5. `RouteResult(text, is_stub)` printed to stdout.

**Flow B — Interactive CLI "Sen: kilit ac"**

1. `interactive_cli.main()` → loop reads input, `normalize_command()` → e.g. route `"kilit"`, args `["ac"]`.
2. `lock_menu()` → `engine.unlock_with_passphrase(pw)` (CoreEngine callback) → keystore + `lumos.lock_state.unlock(root_key)`.
3. No use of `AIRouter` or `Lumos.respond()` in this loop.

**Flow C — Policy path (currently not wired in the interactive loop)**

1. If something built a `Context(message=..., online=..., ...)` and called `lumos.respond(ctx)`:
2. Session memory and note memory enrich `ctx`.
3. `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)`:
   - Offline: `engine.process(message)` → OfflineEngineV1 intents (time, lock, perm status, etc.).
   - Online: unlock/identity checks, then `engine.process(message, short_context)` → OnlineEngineV1 → `ModelClient.generate(signed_payload)` (signed request to backend).
4. `Decision.payload` → response/follow_up/debug combined and returned.

So today:

- **Ask** uses the **AI router + providers** (OpenAI / stubs).
- **Interactive CLI** uses **lock/presence/alias/durum** and **CoreEngine**; it does **not** send free-form “Sen:” text to the router or to `Lumos.respond()`.
- **Lumos.respond()** exists and is fully implemented but is only referenced in backup `main.py` variants, not in the current interactive loop.

---

## 2. Clean Modular Architecture for Lumos Providers

### 2.1 Provider interface

Keep a single protocol and optional base for defaults (e.g. model, timeout):

```python
# src/lumos_core/ai_providers/base.py
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

Optional abstract base for shared behavior (e.g. model, key checks):

```python
# Optional: ai_providers/base.py (continued)
class BaseAIProvider:
    """Optional base: default is_available and get_display_name."""
    name: str = ""
    is_stub: bool = False

    def is_available(self) -> bool:
        return not self.is_stub

    def get_display_name(self) -> str:
        return self.name or self.__class__.__name__
```

### 2.2 Dynamic registration and optional providers

- **Registry**: one central place that knows “provider name → factory or instance”. The router only depends on the registry, not on concrete provider modules.
- **Optional providers**: each provider lives in its own module (or optional dependency). Register only when the module is present and (if desired) when config (e.g. API key) is present.

Example registry:

```python
# src/lumos_core/ai_providers/registry.py
from __future__ import annotations
from typing import Any, Callable, TypeAlias

ProviderFactory: TypeAlias = Callable[[], "AIProvider"]

_registry: dict[str, ProviderFactory] = {}

def register(name: str, factory: ProviderFactory) -> None:
    """Register a provider by name. Overwrites existing."""
    _registry[name] = factory

def unregister(name: str) -> None:
    _registry.pop(name, None)

def get_provider(name: str) -> "AIProvider" | None:
    factory = _registry.get(name)
    if factory is None:
        return None
    return factory()

def list_providers() -> list[str]:
    return sorted(_registry)

def list_available() -> list[str]:
    return [n for n in list_providers() if get_provider(n) and get_provider(n).is_available]
```

Example: register OpenAI only when key is set; keep stubs for the rest.

```python
# src/lumos_core/ai_providers/registry.py (continued)
def _register_builtins() -> None:
    from lumos_core.ai_providers.stub import StubProvider
    for name in ("openai", "gemini", "anthropic"):
        register(name, lambda n=name: StubProvider(n))

    import os
    if os.environ.get("OPENAI_API_KEY", "").strip():
        from lumos_core.ai_providers.openai import OpenAIProvider
        register("openai", OpenAIProvider)

# Call once at package init or first router use
def ensure_builtins() -> None:
    if not _registry:
        _register_builtins()
```

Router then uses the registry only:

```python
# ai_router.py
from lumos_core.ai_providers.registry import ensure_builtins, get_provider, list_providers

class AIRouter:
    def __init__(self) -> None:
        ensure_builtins()

    def route(self, prompt: str, provider: str, **kwargs: Any) -> RouteResult:
        impl = get_provider(provider.lower().strip())
        if impl is None:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {', '.join(list_providers())}")
        if not impl.is_available:
            raise ValueError(f"Provider '{provider}' is not available (e.g. API key not set).")
        text = impl.complete(prompt, **kwargs)
        return RouteResult(text=text, is_stub=getattr(impl, "is_stub", True))
```

Optional providers (e.g. Gemini) can be in a separate package or behind a try/import and register only when successful:

```python
# In registry or a small plugin module
def _register_optional() -> None:
    try:
        from lumos_core_anthropic import AnthropicProvider
        register("anthropic", AnthropicProvider)
    except ImportError:
        pass
    try:
        from lumos_core_gemini import GeminiProvider
        register("gemini", GeminiProvider)
    except ImportError:
        pass
```

This keeps the core package free of hard dependencies on Gemini/Anthropic while allowing them to be plugged in when installed.

### 2.3 Summary

- **Interface**: single `AIProvider` protocol (+ optional `BaseAIProvider`) with `complete`, `is_available`, `get_display_name`.
- **Registration**: registry with `register(name, factory)`; router uses `get_provider(name)` and `list_providers()` / `list_available()`.
- **Optional providers**: register inside try/import or from an optional package; stubs for unconfigured or missing providers keep the CLI stable.

---

## 3. Improvements to lumos_core Architecture

### 3.1 Maintainability

- **Naming / single engine concept**: Two different “engine” concepts exist: **CoreEngine** (lock/presence) and **BaseEngine** / OfflineEngineV1 / OnlineEngineV1 (policy/response). Rename for clarity, e.g.:
  - Keep **CoreEngine** for “core system actions” (lock, presence).
  - Rename **BaseEngine** / OfflineEngineV1 / OnlineEngineV1 to **ResponseEngine** or **PolicyEngine** (and put under `policy/` or `engine/` with a clear module doc). That way “engine” in docs and code consistently means one of “core actions” vs “response/policy”.
- **Config in one place**: Replace scattered `os.environ.get("LUMOS_*")` and `Path("src/.lumos")` / `.lumos` with a small `LumosConfig` (or use existing `core/config.py` if it fits) loaded once (env + optional config file). Pass config (or base_dir, mode, etc.) into CLI and engines instead of reading env inside many modules.
- **Interactive CLI size**: `interactive_cli.py` is large and mixes menu logic, recovery, and TUI. Split into:
  - `interactive_cli/main.py`: entry, config, and main loop only.
  - `interactive_cli/lock_menu.py`, `presence_menu.py`, `alias_menu.py`: one module per menu; receive state/engine as arguments.
  - Keep `CoreState` and `CoreEngine` as the single source of truth for lock/presence and callbacks.

### 3.2 Extensibility

- **Unify “ask” and “respond” (optional)**: If you want the interactive “Sen:” to support free-form AI answers:
  - In the main loop, when `route == "unknown"` (or a new route `"chat"`), build `Context(message=raw, ...)`, call `lumos.respond(ctx)` and print the result.
  - Optionally, for “online” or when a flag is set, call `AIRouter` instead of (or in addition to) the policy engine, so the same prompt can go to OpenAI/Gemini/Anthropic from the interactive session.
- **Provider registry**: As in section 2, make the router depend on a registry so new providers (including third-party) can `register("name", factory)` without editing the router.
- **Hooks / events**: For auditing or future features, add a simple event or hook list (e.g. `on_before_route`, `on_after_respond`) that `Lumos` or `AIRouter` calls so extensions can listen without changing core code.

### 3.3 Testability

- **Inject router and engines**: In `run_ask` and wherever the router is used, accept an optional `router: AIRouter` (defaulting to `AIRouter()`). Tests can inject a router with stub or mock providers. Same for `Lumos(engine=...)` and for the interactive CLI’s engine/state.
- **Config and paths**: Inject base_dir and config (or env dict) into identity, keystore, and scan so tests can use a temp directory and avoid touching real `src/.lumos` or `.lumos`.
- **Provider protocol**: Rely on the `AIProvider` protocol and small adapter classes in tests (e.g. `lambda prompt: "fixed"`) so you don’t need real API keys or network.

### 3.4 Separation of concerns

- **CLI vs core**: Keep CLI as a thin layer: parse args → call a function in `lumos_core` (e.g. `run_ask`, `run_env`, `run_interactive`). No business logic in CLI; core should be callable from another UI (e.g. web) without duplicating logic.
- **Identity/keystore**: Used by online engine and unlock; keep them in `security/` and have the online engine and CLI receive an already-loaded identity/keystore (or a factory) so tests can substitute.
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
│   │   │   ├── __init__.py
│   │   │   └── context.py
│   │   │
│   │   ├── policy/                  # Policy + response engines
│   │   │   ├── __init__.py
│   │   │   ├── decision.py
│   │   │   ├── rules.py
│   │   │   ├── offline_engine.py    # OfflineEngineV1 (intents)
│   │   │   └── ...
│   │   │
│   │   ├── engine/                  # Online + shared “response” client
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseEngine / ResponseEngine protocol
│   │   │   ├── online_engine.py     # OnlineEngineV1, ModelClient
│   │   │   └── model_client.py
│   │   │
│   │   ├── ai_router.py             # AIRouter (uses registry only)
│   │   │
│   │   ├── ai_providers/
│   │   │   ├── __init__.py          # Re-export protocol + registry
│   │   │   ├── base.py              # AIProvider protocol, BaseAIProvider
│   │   │   ├── registry.py         # register(), get_provider(), list_*
│   │   │   ├── stub.py              # StubProvider
│   │   │   ├── openai.py
│   │   │   └── (optional) gemini.py, anthropic.py or external pkg
│   │   │
│   │   ├── memory/
│   │   ├── security/                # identity, keystore, crypto, lock, presence
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

Changes compared to current layout:

- **cli/** groups all CLI: `ask`, `env`, and `interactive` (with submodules for each menu). Entry stays `__main__.py`.
- **policy/** holds both policy rules and offline “response” engine; **engine/** keeps online engine and model client. Naming (e.g. “response engine”) in docstrings and types makes the two “engine” concepts explicit.
- **ai_providers/** gets a clear **base** (protocol + optional base class), **registry**, and **stub**; router depends only on the registry.

You can adopt this structure incrementally (e.g. introduce registry and base first, then move CLI into `cli/` and split interactive menus).

---

## Summary

- **Current**: Two entry styles (lumos.py vs `python -m lumos_core`); interactive CLI does lock/presence/alias/durum only; `ask` uses AIRouter + OpenAI/stubs; `Lumos.respond()` is implemented but not used in the current loop; two “engine” concepts (CoreEngine vs Offline/Online engine).
- **Providers**: Define a single `AIProvider` protocol and a registry; register built-in and optional providers via factories; router uses only the registry for loose coupling and optional dependencies.
- **Improvements**: Clarify engine naming, centralize config, split interactive CLI into smaller modules, inject router/config/paths for tests, and keep CLI thin and core reusable.
- **Structure**: Optional reorganization into `cli/` (with interactive submodules), clear `policy/` vs `engine/`, and a dedicated `ai_providers` base/registry/stub layout.

This should give you a clear map of the current design and a concrete path to a more modular, testable, and extensible Lumos core.
