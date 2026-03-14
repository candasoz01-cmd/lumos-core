# Startup Health Dependency Hygiene Audit

**Scope:** `src/core/startup_health.py` — dependency hygiene, independence of startup checks, and stabilization-phase isolation.

**Constraint:** No runtime code changes; audit only.

---

## 1. Current Dependency Assessment

### 1.1 Direct imports (module top level)

| Import | Source | Purpose |
|--------|--------|---------|
| `platform` | stdlib | `platform.system() == "Darwin"` for macOS branch |
| `Path` | pathlib (stdlib) | `Path(base_dir) / "consent.json"` |
| `Any` | typing (stdlib) | Type hint for `presence_module` |

**No imports from:** `workspace_contract`, `security`, `presence_lock`, `config`, `state`, `engine`, `lumos`, `task_engine`, `memory`, or any other application module.

### 1.2 Injected / runtime dependencies

| Dependency | How it is supplied | Used in |
|-------------|--------------------|---------|
| **presence_module** | Caller passes as argument to `get_startup_summary`, `get_durum_parts`, and internally to `_presence_ok` | `presence_module.load_presence_cfg(Path(base_dir))`, `getattr(cfg, "enabled", False)` |
| **keystore_initialized** | Caller passes as `bool` | `_lock_ok(keystore_initialized)` |
| **base_dir** | Caller passes as `str \| Path` | Consent path, passed to presence load_presence_cfg |

So **startup_health does not import** presence_lock or keystore; it receives them from the caller (e.g. main.py). That keeps the module light and testable with mocks.

### 1.3 Optional lazy import (inside function)

| Location | Import | Purpose |
|----------|--------|---------|
| `_macos_permissions_ok()` | `import cv2` inside try | On Darwin, probe camera (VideoCapture(0)); release; return opened or None on failure |

If `cv2` is missing, the function catches and returns `None`. So cv2 is an optional, runtime-only dependency for the macOS camera check; it does not affect import-time or non-Darwin paths.

### 1.4 Path usage (no workspace_contract)

- **Consent:** `Path(base_dir) / "consent.json"` — ad-hoc. `consent.json` is **not** in `CORE_STATE_PATH_NAMES` in workspace_contract; there is no contract helper for it today.
- **Presence config path:** Not constructed in startup_health; `presence_module.load_presence_cfg(Path(base_dir))` delegates to the injected module (which uses its own path, e.g. base_dir / "presence.json").

**Conclusion:** The module has **no dependency** on workspace_contract, security, or other heavy domains. It depends only on stdlib and on **injected** presence/keystore state. Optional cv2 is confined to one function and one platform.

---

## 2. Independence of Startup Checks

### 2.1 Check breakdown

| Check | Implemented in | Inputs | Side effects |
|-------|----------------|--------|--------------|
| **Consent** | `_consent_ok(base_dir)` | base_dir | Reads `(base_dir)/consent.json` existence only; no write. |
| **Lock** | `_lock_ok(keystore_initialized)` | boolean from caller | None; pure function. |
| **Presence config** | `_presence_ok(presence_module, base_dir)` | injected module, base_dir | Calls `presence_module.load_presence_cfg(Path(base_dir))`; no write. |
| **macOS camera** | `_macos_permissions_ok()` | none | Optional cv2 probe; may open/release camera. |

### 2.2 Independence assessment

- **Consent:** Independent of other checks. Only needs base_dir. No dependency on lock, presence, or security code.
- **Lock:** Independent. Only needs a boolean; caller is responsible for how that value is obtained (e.g. from keystore).
- **Presence:** Depends on the **interface** of the injected module (must provide `load_presence_cfg(base_dir)` returning an object with at least an `enabled` attribute). The module does not depend on presence_lock at import time; swapping a mock for the real module keeps the rest of startup_health unchanged.
- **macOS:** Independent of consent/lock/presence. Only runs on Darwin and only when the function is called; optional cv2 does not affect other checks.

So the **checks are independent** in the sense that: (1) each uses a small, well-defined input set, (2) no check imports another domain, (3) presence is interface-based and injected, and (4) order of evaluation is fixed in the public API (consent → lock → presence → macOS) but there is no hidden cross-call between checks.

### 2.3 Callers and what they pass

| Caller | Uses | What it passes |
|--------|------|----------------|
| **main.py** | `get_durum_parts`, `get_startup_summary` | base_dir, ks.is_initialized(), pl (presence_lock) |
| **panel/scripts/read_backend_state.py** | `consent_ok` only | base_dir (from env) |

The panel script only needs `consent_ok(base_dir)`; it does not call `get_durum_parts` or `get_startup_summary`, so it never passes presence or keystore. That keeps the panel’s use of startup_health minimal and free of presence/keystore imports.

---

## 3. Isolation Risks

### 3.1 Adding imports from heavy domains

- **Risk:** If someone adds `from core.workspace_contract import ...` or `from security import ...` or `import security.presence_lock` at top level to “simplify” call sites or to read a path from the contract, startup_health would pull in those modules. That would:
  - Drag in workspace_contract (and possibly write sinks) for code that currently only needs a consent path.
  - Drag in security or presence_lock for code that currently only needs an injected interface.
- **Mitigation:** Keep the rule: no import of workspace_contract, security, or presence_lock in startup_health. Paths stay ad-hoc or callers pass them; presence/keystore stay injected.

### 3.2 Consent path drift

- **Current:** `Path(base_dir) / "consent.json"` is local to this module. If the project later adds a consent path (or file) to workspace_contract, startup_health could drift (e.g. different filename or location).
- **Risk:** Low for behavior today; medium for long-term consistency. If consent is ever added to CORE_STATE_PATH_NAMES or a helper is introduced, startup_health could be updated to use it; until then, ad-hoc is acceptable but should be documented.

### 3.3 Optional cv2 and macOS

- **Risk:** On Darwin, `_macos_permissions_ok()` imports cv2 and opens the camera. That can trigger system permission prompts and can fail in headless or restricted environments. The function already returns `None` on failure and does not raise; callers treat `None` as “unknown/skipped.”
- **Isolation:** cv2 is not imported at module load; only when the function runs. So startup_health remains importable and usable without cv2; only the macOS camera check is affected.

### 3.4 Tight coupling of “durum” wording

- **Observation:** The strings returned by `get_startup_summary` and `get_durum_parts` (e.g. "Hazır değil. Consent alınmadı.", "kritik eksik yok") are fixed in this module. If another module (e.g. main, or a future i18n layer) needed to depend on these exact strings, that would create a coupling. Currently this is documentation/UX only and does not affect dependency hygiene.

---

## 4. Safe Refactor Suggestions

### 4.1 Do not add new top-level imports from app domains

- Do **not** add `from core import workspace_contract`, `from security import ...`, or `import security.presence_lock` (or any other app module that pulls in write paths or heavy stack) at the top of startup_health. Keep the module depending only on stdlib and on **injected** dependencies.

### 4.2 Optional: consent path via contract (only if contract gains consent)

- If the project later adds a consent path to workspace_contract (e.g. `consent_file_path(base_dir)`), then startup_health could be refactored to use it for consistency. Until then, keeping `Path(base_dir) / "consent.json"` is safe and avoids coupling.

### 4.3 Keep presence and lock as injected parameters

- Do not replace the `presence_module` and `keystore_initialized` parameters with internal imports. Callers (main, tests) should remain the only place that wires presence_lock and keystore; startup_health should only require the minimal interface (load_presence_cfg, boolean for lock).

### 4.4 Optional: document the presence interface

- In the docstring of `get_startup_summary` / `get_durum_parts` or at module level, state explicitly: “presence_module must provide `load_presence_cfg(base_dir: Path)` returning an object with at least an `enabled` attribute.” That makes the contract clear for future refactors and for tests that inject mocks.

### 4.5 macOS camera check remains optional

- Keeping `_macos_permissions_ok()` as-is (optional cv2, return None on failure) is acceptable. If the project ever wants to avoid cv2 in core entirely, this check could be moved to a separate optional module (e.g. under security or a “platform” helper) and invoked by main only when needed; that would be a larger refactor and is not required for stabilization.

---

## 5. Recommended Boundary Rules

1. **No workspace_contract import**  
   startup_health must not import from `core.workspace_contract` in the stabilization phase. If consent (or any other path used here) is later added to the contract, a single, minimal use of a path helper may be considered with explicit review; no use of write sinks or guard logic.

2. **No security or presence_lock import**  
   startup_health must not import from `security` or from `security.presence_lock`. Lock state is provided as a boolean by the caller; presence is provided as an injected module with the documented interface.

3. **No other core/application imports**  
   Do not add imports from `core.config`, `core.state`, `core.engine`, `core.lumos`, `task_engine`, `memory`, `policy`, or `engine`. Startup checks stay self-contained with stdlib + injected parameters.

4. **Optional cv2 only inside one function**  
   The only optional dependency is cv2 in `_macos_permissions_ok()`. It must remain lazy (import inside the function) and must not be used elsewhere in the module. No other optional “heavy” imports (e.g. opencv, ML, or network libs) should be added.

5. **Public API stays minimal**  
   Public entry points are: `consent_ok(base_dir)`, `get_startup_summary(base_dir, keystore_initialized, presence_module)`, `get_durum_parts(base_dir, keystore_initialized, presence_module)`. New public functions should not introduce new domain dependencies; they should use the same injected pattern if they need presence or lock.

6. **Panel use remains minimal**  
   The panel script only needs `consent_ok(base_dir)`. No change in startup_health should require the panel to pass presence_module or keystore; `consent_ok` must remain callable with only base_dir.

---

## Summary Table

| Aspect | Status |
|--------|--------|
| **Direct imports** | Only stdlib (platform, pathlib, typing). No workspace_contract, security, or presence_lock. |
| **Injected deps** | presence_module, keystore_initialized, base_dir — all passed by caller. |
| **Optional lazy** | cv2 in `_macos_permissions_ok()` only; safe for import and non-Darwin. |
| **Check independence** | Consent, lock, presence, macOS are separate; presence is interface-based and injected. |
| **Isolation risks** | Adding imports from heavy domains; consent path drift if contract gains consent later. |
| **Boundary rules** | No workspace_contract/security/presence_lock import; no new app-domain imports; optional cv2 confined; public API minimal; panel keeps using only consent_ok. |

No runtime code was modified; this document is audit and recommendation only.
