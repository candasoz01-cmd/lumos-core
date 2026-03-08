# Lumos Core — Full Architecture Review

This document explains the current architecture, the provider design, suggested improvements to `lumos_core`, and a proposed folder structure. It is intended as the single reference for architecture decisions.

---

## 1. Current Architecture

### 1.1 Main Components

| Component | Location | Role |
|-----------|----------|------|
| **CLI entry points** | `lumos.py`, `src/main.py`, `src/lumos_core/__main__.py` | Parse args; set env (e.g. `LUMOS_MODE`); dispatch to `cli`, `web`, `env`, `ask`, or `chat`. Default: interactive CLI. |
| **Simple CLI (ask/env/chat)** | `src/lumos_core/cli.py` | `env` → device scan + capabilities (JSON + summary). `ask` → pre_route → AIRouter → response_builder → stdout. `chat` → interactive loop with session memory over AIRouter. |
| **Router** | `src/lumos_core/ai_router.py` | `AIRouter`: uses **registry** only (`ensure_builtins`, `get_provider`, `list_providers`). `route(prompt, provider, **kwargs)` → `RouteResult(text, is_stub)`. Injects system prompt and chat context from memory. |
| **Providers** | `src/lumos_core/ai_providers/` | **Protocol** in `base.py` (`AIProvider`). **Registry** in `registry.py` (stubs + OpenAI when `OPENAI_API_KEY` set). **OpenAI** in `openai.py`; **Stub** in `stub.py`. |
| **Identity layer** | `user_identity.py` (user prefs), `security/identity.py` (device Ed25519), `security/keystore.py` (root key) | User: name, address_mode in `.lumos/user_preferences.json`. Device: Ed25519 keypair in `identity.json`; keystore for unlock. Used by online engine and unlock flow. |
| **Pre-route** | `src/lumos_core/policy/pre_route.py` | Before AIRouter: intent classification (OfflineEngineV1 + tool phrases). Decides: **provider**, **tool** (read-only), **unsupported**, or CLI message. |
| **Core / policy** | `core/lumos.py`, `policy/rules.py`, `policy/offline_engine.py`, `engine/` | `Lumos.respond(ctx)` → session/note memory → `PolicyRules.evaluate()` → engine (offline intents or online ModelClient). Implemented but **not** used by current ask/chat. |
| **Engine duality** | `core/engine.py` vs `engine/base.py` | **CoreEngine**: lock/presence callbacks (injected). **BaseEngine** (OfflineEngineV1 / OnlineEngineV1): policy “response” engine with `process(message)` → payload. |

### 1.2 Request Flow (Ask)

```
User: lumos ask "Explain X" --provider openai
         │
         ▼
┌─────────────────────┐     "bunu hatırla"     ┌──────────────────┐
│ __main__ → cli       │ ──────────────────────►│ memory_manager   │ → print, return
└─────────┬───────────┘                        └──────────────────┘
          │ else
          ▼
┌─────────────────────┐  destination ≠ provider  ┌──────────────────┐
│ pre_route(ctx)      │ ─────────────────────────►│ print route.msg   │ → return
│ (tools / unsupported)│                          └──────────────────┘
└─────────┬───────────┘
          │ destination == "provider"
          ▼
┌─────────────────────┐     ┌─────────────────┐
│ build_chat_context  │     │ AIRouter.route()  │
│ load_user_profile   │     │ get_provider()   │
└─────────┬───────────┘     │ impl.complete()  │
          │                 └────────┬────────┘
          ▼                          ▼
┌─────────────────────┐     ┌─────────────────┐
│ build_response()    │◄────│ RouteResult      │
│ print               │     │ (text, is_stub) │
└─────────────────────┘     └─────────────────┘
```

**Flow summary**

- **Ask/Chat**: CLI → pre_route → (if provider) AIRouter → registry → provider `complete()` → RouteResult → build_response → print.
- **Interactive CLI** (`lumos` or `lumos cli`): consent → interactive_cli loop (kilit, kamera, alias, durum). Uses CoreEngine only; does **not** call AIRouter or `Lumos.respond()`.
- **Policy path**: `Lumos.respond(ctx)` exists (session/note memory → PolicyRules → engine) but is not wired into ask/chat or the interactive loop.

---

## 2. Clean Modular Architecture for Lumos Providers

The codebase **already** implements a solid provider design: protocol, registry, optional OpenAI, stubs.

### 2.1 Provider Interface (Current)

**Location**: `src/lumos_core/ai_providers/base.py`

- **Protocol** `AIProvider`: `complete(prompt, **kwargs) -> str`, `is_available`, `get_display_name`.
- **Base class** `BaseAIProvider`: `name`, `is_stub`, default `is_available` / `get_display_name`.

**Recommendation**: Keep this as the single contract. No change required.

Optional extension if you need richer metadata (e.g. for CLI help):

```python
# Optional: in base.py
class AIProvider(Protocol):
    def complete(self, prompt: str, **kwargs: Any) -> str: ...
    @property
    def is_available(self) -> bool: return True
    def get_display_name(self) -> str: ...
    # Optional: for CLI --list-providers
    def get_model_hint(self) -> str: return ""  # e.g. "gpt-4o-mini"
```

### 2.2 Dynamic Registration (Current)

**Location**: `src/lumos_core/ai_providers/registry.py`

- `register(name, factory)`, `get_provider(name)`, `list_providers()`, `list_available()`.
- `ensure_builtins()`: stubs for openai/gemini/anthropic; replace openai with `OpenAIProvider()` when `OPENAI_API_KEY` is set.

**Recommendation**: Use `list_available()` in CLI help and errors so users see only usable providers:

```python
# In cli.py or __main__.py
from lumos_core.ai_providers.registry import list_available, list_providers

# In run_ask, when catching ValueError for unknown provider:
supported = ", ".join(list_providers())
available = list_available()
if available:
    print(f"Available now: {', '.join(available)}", file=sys.stderr)
```

### 2.3 Optional Providers (Gemini, Anthropic) Without Tight Coupling

- Keep each provider in its own module (or optional package).
- Register only when the module is importable and, if desired, when config (e.g. API key) is present.
- Router and core depend only on the **registry**, not on concrete provider modules.

**Example**: register Gemini/Anthropic in `registry.py` behind try/import:

```python
# In _register_builtins() in registry.py, after OpenAI block:
def _register_builtins() -> None:
    # ... stubs and OpenAI as now ...
    try:
        from lumos_core.ai_providers.anthropic import AnthropicProvider
        if os.environ.get("ANTHROPIC_API_KEY", "").strip():
            register("anthropic", lambda: AnthropicProvider())
    except ImportError:
        pass
    try:
        from lumos_core.ai_providers.gemini import GeminiProvider
        if os.environ.get("GOOGLE_API_KEY", "").strip():
            register("gemini", lambda: GeminiProvider())
    except ImportError:
        pass
```

For **optional packages** (e.g. `lumos-provider-anthropic`), use entry points or a small plugin discovery so the core does not depend on them:

```python
# Optional: plugin discovery via importlib.metadata
def _register_plugins() -> None:
    try:
        from importlib.metadata import entry_points
        for ep in entry_points(group="lumos.providers", default=()):
            try:
                factory = ep.load()
                register(ep.name, factory)
            except Exception:
                pass
    except Exception:
        pass
```

**Summary**

- **Interface**: single `AIProvider` protocol (+ optional `BaseAIProvider`); no change needed.
- **Registration**: registry with `register(name, factory)`; router uses only `get_provider` / `list_providers` / `list_available`.
- **Optional providers**: try/import in registry, or entry_points; stubs for unconfigured/missing keep CLI stable.

---

## 3. Improvements to lumos_core Architecture

### 3.1 Maintainability

**Naming — two “engine” concepts**

- **CoreEngine** (`core/engine.py`): lock/presence callbacks (system actions).
- **BaseEngine** / OfflineEngineV1 / OnlineEngineV1 (`engine/`): policy “response” engine — `process(message)` → payload.

**Suggestion**: Rename for clarity. Keep **CoreEngine** as “core system actions”. Rename the policy engine hierarchy to **ResponseEngine** (or **PolicyEngine**) in docstrings and types, and document the distinction in a single place (e.g. `engine/README` or `docs/ENGINES.md`).

**Config in one place**

- Replace scattered `os.environ.get("LUMOS_*")` and hardcoded `Path("src/.lumos")` / `.lumos` with a small **LumosConfig** (or extend `core/config.py`) loaded once (env + optional config file).
- Pass config (or base_dir, mode) into CLI and engines so tests can inject a temp dir and env.

```python
# core/config.py (conceptual)
@dataclass
class LumosConfig:
    base_dir: Path
    mode: str
    debug: bool
    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "LumosConfig":
        env = env or os.environ
        base = env.get("LUMOS_BASE_DIR", "src/.lumos")
        if not Path(base).exists() and Path(".lumos").exists():
            base = ".lumos"
        return cls(
            base_dir=Path(base),
            mode=env.get("LUMOS_MODE", "offline").strip().lower(),
            debug=env.get("LUMOS_DEBUG", "0") == "1",
        )
```

**Interactive CLI size**

- `interactive_cli.py` mixes main loop, menus, and recovery. **Suggestion**: Split into:
  - `interactive_cli/main.py`: entry, config, main loop, dispatch only.
  - `interactive_cli/lock_menu.py`, `presence_menu.py`, `alias_menu.py`: one module per menu; receive state/engine as arguments.
- Keep `CoreState` and `CoreEngine` as the single source of truth.

### 3.2 Extensibility

- **Unify “ask” and “respond” (optional)**: To support free-form AI in the interactive “Sen:” loop, when the route is not a command, build `Context(message=raw, ...)` and either call `lumos.respond(ctx)` or `AIRouter.route(...)` (or both, depending on mode).
- **Provider registry**: Already in place; ensure new providers (including third-party) can `register("name", factory)` without editing the router.
- **Hooks / events**: For auditing or extensions, add a simple hook list (e.g. `on_before_route`, `on_after_respond`) that `AIRouter` or `Lumos` calls so plugins can listen without changing core code.

```python
# Conceptual: ai_router.py or a small hooks module
_before_route: list[Callable[[str, str], None]] = []
def on_before_route(cb: Callable[[str, str], None]) -> None:
    _before_route.append(cb)
# In route(): for c in _before_route: c(prompt, provider)
```

### 3.3 Testability

- **Inject router**: In `run_ask` / `run_chat`, accept an optional `router: AIRouter | None = None` (default `AIRouter()`). Tests inject a router with stub or mock providers.
- **Inject config and paths**: Pass `base_dir` and config (or env dict) into identity, keystore, and device scan so tests use a temp directory and never touch real `src/.lumos` or `.lumos`.
- **Provider protocol**: Tests can use a small in-memory provider (e.g. `lambda prompt: "fixed"` wrapped in a minimal `AIProvider` implementation) so no real API keys or network are needed.

```python
# tests/conftest.py or test helper
def make_mock_router(responses: dict[str, str] | None = None):
    from lumos_core.ai_router import AIRouter
    router = AIRouter()
    class MockProvider:
        is_available = True
        is_stub = False
        def complete(self, prompt: str, **kwargs): return responses.get(prompt, "ok")
    router.register_provider("openai", MockProvider())
    return router
```

### 3.4 Separation of Concerns

- **CLI vs core**: Keep CLI as a thin layer: parse args → call a function in lumos_core (e.g. `run_ask`, `run_env`, `run_interactive`). No business logic in CLI; core should be callable from web or another UI without duplication.
- **Identity/keystore**: Keep in `security/`; have online engine and CLI receive an already-loaded identity/keystore (or a factory) so tests can substitute.
- **Policy vs engine**: `PolicyRules.evaluate()` should only decide allow/deny and pass through the engine’s payload; it should not know about HTTP or provider details. Keep “call external API” (ModelClient or AIRouter) inside the engine/router layer.

---

## 4. Revised Folder Structure (Proposal)

Goal: clearer boundaries, optional providers, and a single place for “response” logic.

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
│   │   │   ├── ask.py               # run_ask(), argparse for ask
│   │   │   ├── env.py               # _run_env, device scan + report
│   │   │   └── interactive/        # Interactive CLI
│   │   │       ├── __init__.py
│   │   │       ├── main.py         # Loop, dispatch, config
│   │   │       ├── lock_menu.py
│   │   │       ├── presence_menu.py
│   │   │       └── alias_menu.py
│   │   │
│   │   ├── core/                    # Core app + system actions
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # LumosConfig (env + file)
│   │   │   ├── lumos.py            # Lumos, boot(), respond()
│   │   │   ├── state.py            # CoreState
│   │   │   ├── engine.py           # CoreEngine (lock/presence)
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
│   │   │   ├── offline_engine.py   # OfflineEngineV1 (intents)
│   │   │   └── ...
│   │   │
│   │   ├── engine/                  # Online + shared “response” client
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # BaseEngine / ResponseEngine protocol
│   │   │   ├── online_engine.py    # OnlineEngineV1, ModelClient
│   │   │   └── model_client.py
│   │   │
│   │   ├── ai_router.py             # AIRouter (uses registry only)
│   │   │
│   │   ├── ai_providers/
│   │   │   ├── __init__.py         # Re-export protocol + registry
│   │   │   ├── base.py             # AIProvider protocol, BaseAIProvider
│   │   │   ├── registry.py        # register(), get_provider(), list_*
│   │   │   ├── stub.py
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

**Changes vs current layout**

- **cli/** groups all CLI: `ask`, `env`, and `interactive` (with submodules per menu). Entry stays `__main__.py`.
- **policy/** holds rules, pre_route, and offline “response” engine; **engine/** keeps online engine and model client. Naming (e.g. “response engine”) in docstrings and types makes the two “engine” concepts explicit.
- **ai_providers/** keeps base, registry, stub; router depends only on the registry.

Adopt incrementally: e.g. introduce config and injectable router first, then move CLI into `cli/` and split interactive menus.

---

## Summary

| Area | Current state | Recommendation |
|------|----------------|----------------|
| **Architecture** | Two entry styles (lumos.py vs `python -m lumos_core`); ask/chat use AIRouter + registry; interactive CLI uses CoreEngine only; `Lumos.respond()` not wired in loop. | Document clearly; optionally wire respond() or AIRouter into interactive “Sen:” for free-form AI. |
| **Providers** | Protocol + registry + stubs + optional OpenAI. | Keep; add `list_available()` to CLI messages; register Gemini/Anthropic via try/import or entry_points. |
| **Maintainability** | Two “engine” concepts; scattered config; large interactive_cli. | Rename policy engine in docs; centralize config; split interactive CLI into cli/interactive/*. |
| **Extensibility** | Registry in place. | Add optional hooks (on_before_route, on_after_respond); optional plugin entry_points. |
| **Testability** | Router has register_provider for tests. | Inject router in run_ask/run_chat; inject config/base_dir for identity and scan. |
| **Structure** | Flat CLI and mixed engine locations. | Optional move to cli/ (ask, env, interactive/*), keep policy/ vs engine/ clear. |
