# Lumos Core — Architecture Review

This document explains the current architecture, a clean modular design for providers, improvements to `lumos_core`, and a proposed folder structure. It includes concrete suggestions and short code examples.

---

## 1. Current Architecture

### 1.1 Main Components

| Component | Location | Role |
|-----------|----------|------|
| **CLI entry points** | `lumos.py` (root), `src/main.py`, `src/lumos_core/__main__.py` | Top-level entry: `__main__.py` parses `cli` \| `web` \| `env` \| `ask` \| `chat` \| `tg`; consent/onboarding; delegates to `lumos_core.cli` or `interactive_cli`. |
| **Simple CLI (ask/chat/env)** | `src/lumos_core/cli.py` | `env` → device scan + capabilities (JSON + summary). `ask` / `chat` → **pre_route** → **AIRouter** → provider (OpenAI or stub); memory via `memory_manager.build_chat_context`; output via `response_builder.build_response`. |
| **Interactive CLI** | `src/lumos_core/interactive_cli.py` | Main loop with "Sen:" prompt; commands **kilit**, **kamera**, **alias**, **durum**, **exit**. Uses `CoreEngine`, `CoreState`, `FileKeyStore`, presence lock. Does **not** call `AIRouter` or `Lumos.respond()`. |
| **Router** | `src/lumos_core/ai_router.py` | `AIRouter`: uses provider registry (`ensure_builtins`, `get_provider`, `list_providers`). `route(prompt, provider, **kwargs)` → `RouteResult(text, is_stub)`. Chat context only via `chat_context` from `memory_manager.build_chat_context()`. |
| **Providers** | `src/lumos_core/ai_providers/` | **base.py**: `AIProvider` protocol + `BaseAIProvider`. **registry.py**: `register(name, factory)`, `get_provider`, `list_providers`, `list_available`, `ensure_builtins` (stubs + OpenAI when `OPENAI_API_KEY` set). **openai.py**: `OpenAIProvider`; **stub.py**: `StubProvider`. |
| **Identity layer** | `src/lumos_core/security/identity.py`, `keystore.py` | `DeviceIdentity`: Ed25519 keypair, `identity.json`; `FileKeyStore`: root key from passphrase. Used by online engine and unlock flow; `base_dir` currently hardcoded (e.g. `src/.lumos` / `.lumos`). |
| **Core / policy** | `core/lumos.py`, `policy/rules.py`, `policy/offline_engine.py`, `engine/online_engine.py` | `Lumos.respond(ctx)` → session/note memory enrichment → `PolicyRules.evaluate()` → `engine.process(message)` (offline intents or online signed `ModelClient`). **Not** used by ask/chat or interactive CLI. |
| **Engine duality** | `core/engine.py` vs `engine/base.py` | **CoreEngine**: lock/presence actions (injected callbacks). **BaseEngine** (and `OfflineEngineV1` / `OnlineEngineV1`): policy “engine” with `process(message)` → response payload. |

### 1.2 Request Flows

**Flow A — `lumos ask "Explain X" --provider openai` (or `python -m lumos_core ask ...`)**

1. `__main__.py` or `cli.main()` parses `ask` → `run_ask(prompt, provider)`.
2. Optional memory-save: if prompt is "bunu hatırla: ...", store via `memory_manager` and return.
3. `Context(message=prompt)` → `pre_route(ctx)` → `PreRouteResult(destination, message)`.
4. If `destination != "provider"`: print `message` and return (e.g. tool result or "use interactive CLI").
5. Otherwise: `router = AIRouter()` (or injected), `router.route(prompt, provider=..., user_name=..., chat_context=build_chat_context(...))`.
6. `AIRouter` uses registry: `get_provider(provider)` → `impl.complete(prompt, system_prompt=..., **kwargs)`.
7. `build_response(result.text, user)` → print with optional `[stub]` prefix.

**Flow B — Interactive CLI "Sen: kilit ac"**

1. `interactive_cli.main()` → consent check, load aliases, `CoreEngine` + `CoreState` + keystore.
2. Loop: input → `normalize_command()` → e.g. route `"kilit"`, args `["ac"]`.
3. `lock_menu()` → `engine.unlock_with_passphrase(pw)` (CoreEngine callback) → keystore + `lumos.lock_state.unlock(root_key)`.
4. No `AIRouter` or `Lumos.respond()` in this loop.

**Flow C — Policy path (Lumos.respond; not wired in CLI)**

1. Caller builds `Context(message=..., online=..., ...)` and calls `lumos.respond(ctx)` (e.g. tests, backup `main.py` variants).
2. Session memory and note memory enrich `ctx`.
3. `PolicyRules.evaluate(ctx, mode, confidence_threshold, engine)` → offline: `engine.process(message)` (intents); online: identity + `engine.process(message, short_context)` → `ModelClient.generate(signed_payload)`.
4. `Decision.payload` → response/follow_up/debug combined and returned.

**Summary:** **Ask/Chat** use **pre_route → AIRouter → registry providers** (OpenAI/stubs) and **memory_manager** + **response_builder**. **Interactive CLI** uses **CoreEngine + CoreState + keystore/presence** only. **Lumos.respond()** is implemented but not used by the current interactive loop or by ask/chat.

---

## 2. Clean Modular Architecture for Lumos Providers

The codebase already uses a protocol, base class, and registry. Below is a concise description plus optional extensions and code examples.

### 2.1 Provider Interface (Current)

- **Protocol** (`ai_providers/base.py`): `AIProvider` with `complete(prompt, **kwargs) -> str`, `is_available` (property), `get_display_name()`.
- **Optional base** (`BaseAIProvider`): `name`, `is_stub`, default `is_available` / `get_display_name`.
- **Router** depends only on the registry and the protocol; it does not import concrete provider modules.

Example protocol usage:

```python
# ai_providers/base.py (existing)
@runtime_checkable
class AIProvider(Protocol):
    def complete(self, prompt: str, **kwargs: Any) -> str: ...
    @property
    def is_available(self) -> bool: return True
    def get_display_name(self) -> str: return getattr(self, "name", self.__class__.__name__)
```

### 2.2 Dynamic Registration (Current)

- **Registry** (`ai_providers/registry.py`): `register(name, factory)`, `get_provider(name)`, `list_providers()`, `list_available()`, `ensure_builtins()`.
- **Builtins**: stubs for `openai`, `gemini`, `anthropic`; replace `openai` with `OpenAIProvider()` when `OPENAI_API_KEY` is set (and `openai` package is importable).

Example: registering an optional provider at runtime (e.g. in `_register_builtins()` or a plugin loader):

```python
# In registry._register_builtins() or a small plugin loader
def _register_optional() -> None:
    try:
        from lumos_core.ai_providers.anthropic import AnthropicProvider
        if os.environ.get("ANTHROPIC_API_KEY", "").strip():
            register("anthropic", lambda: AnthropicProvider())
    except ImportError:
        pass
    try:
        from lumos_core.ai_providers.gemini import GeminiProvider
        if os.environ.get("GEMINI_API_KEY", "").strip():
            register("gemini", lambda: GeminiProvider())
    except ImportError:
        pass
```

### 2.3 Optional Providers Without Tight Coupling

- Keep each provider in its own module; router and core only depend on `ai_providers.base` and `ai_providers.registry`.
- Optional dependencies: e.g. `openai` in `[openai]` extra in `pyproject.toml`; Gemini/Anthropic in separate extras or optional packages that call `register()` on import.
- Stubs remain for unconfigured or missing providers so CLI always shows a consistent list and friendly messages.

Example optional provider implementation (same interface as OpenAI):

```python
# ai_providers/anthropic.py (optional; register only when ANTHROPIC_API_KEY set)
from lumos_core.ai_providers.base import BaseAIProvider

class AnthropicProvider(BaseAIProvider):
    name = "Anthropic"
    is_stub = False

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = (api_key or os.environ.get("ANTHROPIC_API_KEY") or "").strip()

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(self, prompt: str, **kwargs: Any) -> str:
        # ... call Anthropic API, return response text
        pass
```

### 2.4 Summary (Providers)

- **Interface**: `AIProvider` protocol + `BaseAIProvider`; already in place.
- **Registration**: registry with `register(name, factory)`; router uses `get_provider` / `list_providers`; already in place.
- **Optional providers**: register inside try/import or from an optional package; keep stubs for missing/unconfigured providers.

---

## 3. Improvements to lumos_core Architecture

### 3.1 Maintainability

- **Naming / single engine concept**: Two “engine” concepts exist: **CoreEngine** (lock/presence) and **BaseEngine** / OfflineEngineV1 / OnlineEngineV1 (policy/response). Rename for clarity:
  - Keep **CoreEngine** for “core system actions” (lock, presence).
  - Use a clear name for the policy side, e.g. **ResponseEngine** or **PolicyEngine**, and document it in `engine/base.py` and `policy/` so “engine” consistently means either “core actions” or “response/policy”.

- **Config in one place**: Replace scattered `os.environ.get("LUMOS_*")` and hardcoded `Path("src/.lumos")` / `.lumos` with a single `LumosConfig` (or extend `core/config.py`) loaded once (env + optional config file). Pass config (or `base_dir`, `mode`, etc.) into CLI and engines instead of reading env inside many modules.

  Example central config:

  ```python
  # core/config.py — extend or add
  @dataclass
  class LumosConfig:
      base_dir: Path
      mode: str = "offline"
      debug: bool = False

      @classmethod
      def from_env(cls) -> "LumosConfig":
          base = os.environ.get("LUMOS_BASE_DIR", ".lumos")
          if Path("src/.lumos").exists() and base == ".lumos":
              base = "src/.lumos"
          return cls(
              base_dir=Path(base),
              debug=os.environ.get("LUMOS_DEBUG", "0") == "1",
          )
  ```

- **Interactive CLI size**: `interactive_cli.py` is large and mixes main loop, menus, and helpers. Split into:
  - `interactive_cli/main.py`: entry, config, and main loop only.
  - `interactive_cli/lock_menu.py`, `presence_menu.py`, `alias_menu.py`: one module per menu; receive state/engine as arguments.
  - Keep `CoreState` and `CoreEngine` as the single source of truth.

### 3.2 Extensibility

- **Unify “Sen:” with AI (optional)**: To support free-form AI in the interactive loop, when the normalized command is not kilit/kamera/alias/durum/exit, build `Context(message=raw, ...)`, call `pre_route(ctx)`; if `destination == "provider"`, call `AIRouter.route(...)` (and optionally run policy/identity via `Lumos.respond(ctx)` if you want one path). Reuses the same pre_route + router + memory as ask/chat.

- **Provider registry**: Already in place; third-party code can `register("name", factory)` without editing the router.

- **Hooks / events**: For auditing or extensions, add a simple hook list (e.g. `on_before_route`, `on_after_respond`) that `AIRouter` or `Lumos` calls so plugins can listen without changing core code.

  Example:

  ```python
  # ai_router.py — optional hooks
  _before_route: list[Callable[[str, str], None]] = []
  _after_route: list[Callable[[str, str, RouteResult], None]] = []

  def on_before_route(cb: Callable[[str, str], None]) -> None:
      _before_route.append(cb)
  def on_after_route(cb: Callable[[str, str, RouteResult], None]) -> None:
      _after_route.append(cb)

  # In route(): for cb in _before_route: cb(prompt, provider); ...; for cb in _after_route: cb(prompt, provider, result)
  ```

### 3.3 Testability

- **Inject router**: `run_ask` and `run_chat` already accept optional `router: AIRouter | None`; tests can inject a router with stub or mock providers.

- **Inject config and paths**: Inject `base_dir` and config (or env dict) into identity, keystore, and scan so tests can use a temp directory and avoid touching real `src/.lumos` or `.lumos`.

  Example test injection:

  ```python
  # tests: use temp dir for identity/keystore
  def test_ask_uses_injected_router(tmp_path):
      router = AIRouter()
      router.register_provider("openai", MockProvider("fixed response"))
      run_ask("hello", provider="openai", router=router)
      # assert output contains "fixed response"
  ```

- **Provider protocol**: Use small adapters in tests (e.g. a class with `complete(prompt, **kwargs) -> "fixed"`) so tests don’t need real API keys or network.

### 3.4 Separation of Concerns

- **CLI vs core**: Keep CLI thin: parse args → call a function in `lumos_core` (e.g. `run_ask`, `run_env`, `run_interactive`). No business logic in CLI; core should be callable from another UI (e.g. web) without duplicating logic.

- **Identity/keystore**: Keep in `security/`; have online engine and CLI receive an already-loaded identity/keystore (or a factory) so tests can substitute.

- **Policy vs engine**: `PolicyRules.evaluate()` should only decide allow/deny and pass through the engine’s payload; it shouldn’t know about HTTP or provider details. Keep “call external API” (ModelClient, or future use of AIRouter) inside the engine layer.

---

## 4. Revised Folder Structure (Proposal)

Goal: clearer boundaries, optional providers, and a single place for “response” logic.

```
lumos-core/
├── src/
│   ├── lumos_core/
│   │   ├── __init__.py
│   │   ├── __main__.py              # Entry: cli | web | env | ask | chat | tg
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
│   │   ├── ai_providers/
│   │   │   ├── __init__.py          # Re-export protocol + registry
│   │   │   ├── base.py              # AIProvider protocol, BaseAIProvider
│   │   │   ├── registry.py          # register(), get_provider(), list_*
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
├── lumos-quantum/   # or qc_demo at repo root
├── tests/
└── docs/
```

**Changes compared to current layout:**

- **cli/** groups all CLI: `ask` (and `run_chat`), `env`, and `interactive` with submodules per menu. Entry stays `__main__.py`.
- **policy/** holds policy rules, `pre_route`, and offline “response” engine; **engine/** keeps online engine and model client. Naming (e.g. “response engine”) in docstrings and types makes the two “engine” concepts explicit.
- **ai_providers/** already has base, registry, stub; router depends only on the registry.

Adopt this structure incrementally (e.g. introduce config and base_dir injection first, then move CLI into `cli/` and split interactive menus).

---

## Summary

- **Current**: Two entry styles (root `lumos.py` vs `python -m lumos_core`); interactive CLI does lock/presence/alias/durum only; ask/chat use pre_route + AIRouter + registry (OpenAI/stubs) + memory_manager + response_builder; `Lumos.respond()` is implemented but not used in the loop or ask/chat; two “engine” concepts (CoreEngine vs Offline/Online engine).
- **Providers**: Single `AIProvider` protocol and registry are already in place; optional providers (Gemini, Anthropic) can register via try/import or optional packages; stubs keep the CLI stable when unconfigured.
- **Improvements**: Clarify engine naming, centralize config and paths, split interactive CLI into smaller modules, inject router/config/paths for tests, keep CLI thin and core reusable.
- **Structure**: Optional reorganization into `cli/` (with interactive submodules), clear `policy/` vs `engine/`, and the existing `ai_providers` base/registry/stub layout.
