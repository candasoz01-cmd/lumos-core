# Dependency and Import Coupling Audit

**Scope:** Actual Python import and dependency coupling across the repository.  
**Focus:** core ↔ security/task_engine/policy/memory; panel ↔ backend bridge and contract; web ↔ core/workspace; risky coupling, circular dependency risk, fat entrypoints.  
**No runtime code was modified.**

---

## 1. Concise Dependency Map

### 1.1 Core → other domains

| From (core) | To | Notes |
|-------------|----|--------|
| `core.lumos` | `context`, `policy.rules`, `policy.offline_engine`, `memory.memory`, `memory.session_memory`, `engine.base`, `security.lock`, `core.version` | Lumos composes policy, memory, engine, lock |
| `core.engine` | (none at import) | Uses `core.logfmt` only in exception path (local import) |
| `core.config` | `core.workspace_contract` (config_file_path, save_config_json) | Config read/write goes through contract |
| `core.inviolable` | `core.workspace_contract`, `task_engine.profiles` | Verification of core constants + task_engine profile constants |
| `core.state` | (none) | Receives lumos and presence_lock_module as constructor args |
| `core.startup_health` | (none) | Receives presence_module as arg; no workspace_contract |
| `core.logfmt` | (none) | Standalone |
| `core.version` | (none) | Standalone |
| `core.workspace_contract` | (none) | No outbound domain imports; pathlib + local `json` only |

### 1.2 Security / task_engine / policy / memory → core (and each other)

| From | To |
|------|-----|
| `security.identity` | `security.crypto`, `core.workspace_contract` (save_identity_json) |
| `security.keystore` | `security.crypto`, `security.entropy`, `core.workspace_contract` (save_keystore_json) |
| `security.aliases` | `core.workspace_contract` (CoreWriteForbidden, save_aliases_json) |
| `security.presence_lock` | `core.logfmt`, `core.workspace_contract` (append_log_line, save_presence_cfg_json) |
| `security.crypto` | `security.entropy` |
| `security.request_signer` | `security.crypto`, `security.entropy` |
| `memory.secure_store` | `core.workspace_contract` (save_notes_enc_json), `security.crypto` |
| `memory.memory` | `memory.schema`, `memory.secure_store` |
| `memory.session_memory` | `context.context` |
| `policy.rules` | `context.context` only |
| `policy.offline_engine` | `device.contacts` only (no core) |
| `task_engine.engine` | `core.workspace_contract` (may_perform_permanent_delete, save_task_store_json), `task_engine.profiles` |
| `task_engine.profiles` | (none) |
| `task_engine.__init__` | `task_engine.engine`, `task_engine.profiles` |

**Summary:** `core.workspace_contract` is the central sink for all persistent writes from security, memory, and task_engine. No package imports `core.lumos` or `main`; cycles back into core are only via `workspace_contract` and `core.logfmt`.

### 1.3 Panel → backend bridge and contract

| Consumer | Imports (Python) | Contract dependency |
|----------|------------------|----------------------|
| `panel/scripts/read_backend_state.py` | `core.workspace_contract` (identity_file_path, keystore_file_path, config_file_path, trash_path, sandbox_base_path, writing_base_dir, logs_dir_path), `core.startup_health` (consent_ok) | Reads paths and consent only; no main, no write flows. Output shape is fixture contract for Dashboard, Sandbox, System, Config, Identity, Keystore, Tasks, Trash, Logs. |
| Panel JS (fixtures, contracts, app) | — | Data contract only: expects keys such as `workspace_contract`, `system_health`, `system_paths`; no Python imports. |

Panel bridge is intentionally narrow: one script, two core modules (workspace_contract + startup_health). If `startup_health` or `workspace_contract` started pulling in security/lumos, panel would gain that coupling transitively.

### 1.4 Web → core/workspace

| Consumer | Imports | Coupling |
|----------|---------|----------|
| `web/app.py` | Adds `src` to `sys.path`; optional `lumos_core.version`; inside `_read_status_snapshot()`: **dynamic** `import security.presence_lock as pl` | Web does not run Lumos. It discovers `.lumos` via path (`_lumos_dir()`: `repo/src/.lumos` or `repo/.lumos`). Status uses `pl.load_presence_cfg()`, `pl.is_running()`. So web depends on **security.presence_lock**, which in turn pulls **core.logfmt** and **core.workspace_contract**. |

So: **web → security.presence_lock → core (logfmt, workspace_contract)**. Tight coupling of a read-only HTTP process to the security layer and workspace contract.

### 1.5 Entrypoints and aggregation

| Entrypoint | Top-level imports (domain count) | Role |
|------------|-----------------------------------|------|
| `src/main.py` | **core** (config, engine, logfmt, lumos, state, startup_health, workspace_contract), **engine** (online_engine), **memory** (schema, secure_store), **policy** (offline_engine), **security** (presence_lock, aliases, keystore, permissions), **task_engine** (re-export bundle) | Single fat CLI entry: all domains loaded at startup. |
| `src/core/lumos.py` | context, policy.rules, memory (memory, session_memory), engine.base, policy.offline_engine, core.version, security.lock | Orchestrator that composes policy, memory, engine, lock. |

`lumos_core/__main__.py` and `lumos.py` (repo root) delegate to `main` or package entry; they do not add new domain imports.

---

## 2. Top 5 Risky Coupling Points

1. **`main.py` as fat entrypoint**  
   One file imports almost every domain (core ×7, engine, memory ×2, policy, security ×4, task_engine). Any change in any of these can force `main.py` to change; startup cost and test surface are high. Refactors (e.g. optional online, optional task_engine) are harder because everything is pulled at once.

2. **`core.workspace_contract` as single write hub**  
   Security (identity, keystore, aliases, presence_lock), memory (secure_store), and task_engine (engine) all persist through it. Contract changes (signatures, guards, new paths) ripple to many callers. No other shared sink exists, so this module is a high-impact single point of failure.

3. **Web server → `security.presence_lock`**  
   The read-only web app dynamically imports `security.presence_lock` for status. That pulls in `core.logfmt` and `core.workspace_contract`. So a lightweight HTTP process depends on the full presence lock and workspace contract stack. Failure or behavior change in presence_lock or contract affects web status.

4. **`core.lumos` as domain aggregator**  
   Lumos directly imports policy, memory, engine, and security.lock. The “core” object is a composition of all domains; extracting or replacing one (e.g. policy or memory) requires touching `lumos.py` and its tests. There is no thin interface layer between lumos and these domains.

5. **Panel bridge → `core.startup_health` + `core.workspace_contract`**  
   Panel’s only Python bridge imports both. Today `startup_health` does not import workspace_contract or security, so the bridge stays minimal. If `startup_health` (or any shared helper it uses) gains dependencies on security or full workspace_contract usage, panel gains that coupling and any associated startup/behavior cost.

---

## 3. Circular Dependency Risk

- **No strict import cycle found.**  
  - `core.lumos` → security.lock, policy, memory, engine.  
  - security.* → core.workspace_contract (and core.logfmt in presence_lock).  
  - `core.workspace_contract` does not import security, policy, memory, or task_engine.  
  So the graph is DAG from workspace_contract outward; core.lumos and main sit at the top, pulling domains that in turn only pull core.workspace_contract and core.logfmt.

- **Possible future cycle:** If `core.workspace_contract` or any core module that lumos/main depend on started importing security or task_engine (e.g. for “guard” or “profile” checks inside the contract), a cycle could appear. Keeping workspace_contract and startup_health free of domain imports avoids that.

---

## 4. Safe Refactor Priorities (Stabilization Phase)

1. **Thin CLI router / reduce `main.py` surface**  
   Extract a small router or command registry that delegates to domain-specific handlers. Lazy-import or load only the domains needed for the chosen command. Reduces startup cost and keeps `main.py` from being the single file that must change for every domain change.

2. **Read-only path / status API for panel and web**  
   Introduce a minimal read-only interface (e.g. path discovery and status flags) that panel and web can use without importing full `workspace_contract` or `security.presence_lock`. Options: small “paths only” module, or env-based base dir + documented paths. Keeps web and panel bridge stable when contract or presence internals change.

3. **Freeze and document `workspace_contract` public API**  
   Explicitly list and document the public symbols used by security, memory, task_engine, and main. Avoid adding new callers; prefer extending via new functions with clear guard/sandbox semantics. Reduces ripple from contract changes.

4. **Keep `startup_health` dependency-light**  
   Preserve the current design: no imports of workspace_contract or security inside `startup_health`, so the panel bridge remains minimal and no accidental cycle is introduced via startup_health.

5. **Lumos composition via interfaces / injection**  
   Consider introducing narrow interfaces (e.g. “policy evaluator”, “memory enricher”, “engine”) and constructing Lumos with injected implementations rather than hard imports. Allows swapping or testing policy/memory/engine without changing lumos internals; reduces risk when extracting or replacing a domain.

---

**Document generated from static analysis of Python imports and documented contracts. No runtime code was modified.**
