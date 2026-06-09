# Lumos Core — Architecture Map

Concise map of **core modules**, **panel components**, **backend contracts**, and **coupling points**. Focus: architecture clarity and future scaling.

---

## 1. Repository layout (high level)

```
lumos-core/
├── src/                    # Runtime Python (sys.path = src)
│   ├── main.py             # CLI entry (lock, presence, alias, durum, tasks, notes)
│   ├── core/               # Core engine, state, workspace contract, config
│   ├── task_engine/        # Tasks, profiles, permission matrix
│   ├── security/           # Lock, presence, identity, keystore, aliases, entropy
│   ├── memory/             # Notes, session, secure store, schema
│   ├── engine/             # Online/offline model engines, base
│   ├── policy/             # Rules, decision, offline_engine
│   ├── context/            # Context for Lumos respond()
│   ├── device/             # Contacts (device layer)
│   ├── tools/              # File classifier, run_classify
│   └── lumos_core/         # Installable package: __main__, version only
├── web/                    # Web v1 server (read-only /health, /status)
├── panel/                  # Operator panel (static HTML/JS/CSS; read-only bridge)
├── docs/                   # Contracts, karar sözleşmesi, guard/sandbox
├── tests/
└── .lumos/                 # Workspace spine: tasks/, logs/, trash/, config/
```

**Entry points:** `lumos` (or `python -m lumos_core`) → CLI (default) or `lumos web` → `web/app.py`. CLI loads `main.main()` from `src/main.py` with `src` on path.

---

## 2. Core modules

| Module | Role | Key exports / files |
|--------|-----|----------------------|
| **core** | Engine orchestration, state, workspace contract, config, logging | `engine.py` (CoreEngine: lock/presence actions), `state.py` (CoreState), `lumos.py` (Lumos: boot, respond), `workspace_contract.py` (paths, sinks, sandbox/trash), `config.py`, `logfmt.py`, `inviolable.py`, `startup_health.py` |
| **task_engine** | Task store, execution, permission profiles | `engine.py` (TaskEngine, TaskStore), `profiles.py` (PROFILE_*, STEP_TYPE_*, SECURITY_NEVER_AUTO, is_allowed_for_profile) |
| **security** | Lock, presence, identity, keystore, aliases, crypto | `lock.py`, `presence_lock.py`, `presence_fsm.py`, `identity.py`, `keystore.py`, `aliases.py`, `permissions.py`, `crypto.py`, `request_signer.py`, `entropy/` |
| **memory** | Notes, session, secure store | `memory.py`, `session_memory.py`, `secure_store.py`, `schema.py` |
| **engine** | Model / online-offline engines | `base.py`, `base_engine.py`, `online_engine.py`, `model_client.py` |
| **policy** | Decision rules, offline behavior | `rules.py`, `decision.py`, `offline_engine.py` |
| **context** | Request context for Lumos | `context.py` |
| **device** | Device-level (e.g. contacts) | `contacts.py` |

**Inviolable core (do not relax):** Security, permissions, workspace spine (tasks, logs, trash, config), decision layers (docs/lumos-karar-sozlesmesi.md). Referenced in `core/inviolable.py` and `task_engine/profiles.py`.

---

## 3. Panel components

| Layer | Location | Purpose |
|-------|----------|---------|
| **Shell** | `panel/index.html` | Single page; hash routing (`#dashboard`, `#tasks`, `#sandbox`, `#config`, `#identity`, `#keystore`, `#trash`, `#logs`, `#system`). |
| **Styles** | `panel/css/app.css` | Global panel styling. |
| **App** | `panel/js/app.js` | Routing, views, adapter API (`getDashboardData()`, `getTasksData()`, …), demo scenarios, data source selector (Demo / Fixture / Backend). |
| **Contracts** | `panel/js/contracts.js` | Single source of truth: `CONTRACTS` (per-screen schema), `applyContractFallbacks`, stub builders, normalizers. No fetch/API. |
| **Fixtures** | `panel/js/fixtures.js` | Backend-shaped payloads and mappers (`map*PayloadToPanelData`) from snake_case to panel shape. |
| **Backend bridge** | `panel/js/backend-bridge.js` | Read-only: `window.__LUMOS_READ_STATE__` → backend-shaped object per screen; missing → null (fixture/demo fallback). |
| **State inject** | `panel/js/state_inject.js` | Consumes injected state (e.g. from `read_backend_state.py --write`). |
| **Script** | `panel/scripts/read_backend_state.py` | Read-only backend snapshot: uses `workspace_contract`, `startup_health`; outputs JSON for Dashboard, Sandbox, System, Config, Identity, Keystore, Tasks, Trash, Logs. Injected into panel via `__LUMOS_READ_STATE__` (e.g. static build or dev pipeline). |

**Serving:** Panel is static; no routes in `web/app.py`. Run via `file://` or HTTP (e.g. `python3 -m http.server 8080` → `http://localhost:8080/panel/`).

---

## 4. Backend contracts

| Contract | Location | Role |
|----------|----------|------|
| **Workspace contract** | `src/core/workspace_contract.py` | Single trash dir, sandbox dir, core state path names; path helpers (`trash_path`, `sandbox_base_path`, `writing_base_dir`, `*_file_path`, `*_dir_path`); write sinks with sandbox guard (`append_log_line`, `save_aliases_json`, `save_config_json`, …); `allow_write_to_core`, `is_core_state_path`. |
| **Core state paths** | Same | `CORE_STATE_PATH_NAMES`: tasks.json, config, config.json, logs, trash, aliases.json, notes.enc.json, presence.json, identity.json, keystore.json. |
| **Profiles / security boundary** | `src/task_engine/profiles.py` | `STEP_TYPE_*`, `SECURITY_NEVER_AUTO`, `is_allowed_for_profile(profile, step_type, general_approval)`. Decision layers: analiz, öner, uygulama, asla. |
| **Inviolable constants** | `src/core/inviolable.py` | Expected literals for trash dirname, profiles, step types, SECURITY_NEVER_AUTO; `verify_core_constants()` for tests. |
| **Panel data contract** | `panel/BACKEND_DATA_CONTRACT.md` + `panel/js/contracts.js` | Per-screen required/optional/fallback fields; backend snake_case ↔ panel CONTRACTS; mappers in `fixtures.js`. |
| **Backend binding map** | `panel/BACKEND_BINDING_MAP.md` | Which backend sources map to which panel screens; integration risk levels. |

---

## 5. Coupling points (and scaling notes)

### 5.1 CLI → everything

- **main.py** imports: `core.*`, `engine.online_engine`, `memory.*`, `policy.offline_engine`, `security.*`, `task_engine.*`.
- **Single fat entry:** All subcommands (lock, presence, alias, durum, tasks, notes, self-test, etc.) live in one file; branching is deep.
- **Scaling:** Extract subcommand handlers into dedicated modules (e.g. `cli_lock`, `cli_tasks`, `cli_notes`) and keep `main.py` as a thin router to reduce merge conflicts and clarify boundaries.

### 5.2 Core state and write paths

- **CoreState** and **CoreEngine** are constructed in `main.py` and passed into lock/presence menus and recovery.
- All persistent writes go through **workspace_contract** sinks (with `is_sandbox_mode` and `allow_write_to_core`). Any new core state file should use the same pattern and be added to `CORE_STATE_PATH_NAMES`.
- **Coupling:** Adding a new core state artifact requires: (1) path helper + sink in `workspace_contract`, (2) optional inviolable test, (3) doc update. Keeps single source of truth and sandbox safety.

### 5.3 Task engine and profiles

- **task_engine** is used by CLI for task CRUD and for permission checks. **profiles.py** is the single place for step types and profile matrix; **core/inviolable.py** asserts expected literals.
- **Coupling:** Policy/decision logic that depends on “can this step run?” should call `is_allowed_for_profile` only; no ad-hoc profile checks elsewhere.

### 5.4 Lumos respond pipeline

- **Lumos** (core/lumos.py): `respond(ctx)` → session_memory.enrich → note_memory.enrich → PolicyRules.evaluate → decision.allow / payload.response. Depends on **context**, **policy**, **memory**, **engine** (BaseEngine).
- **Coupling:** New behavior that affects “what Lumos says” should extend policy/rules or engine, not bypass the pipeline.

### 5.5 Panel ↔ backend

- **Panel** never talks to `web/app.py` today. Data comes from: (1) `window.__LUMOS_READ_STATE__` (filled by `read_backend_state.py` or similar), or (2) fixture/demo.
- **read_backend_state.py** imports only from `src` (workspace_contract, startup_health, etc.); no `main.py`, no write flows. Output shape must match **BACKEND_DATA_CONTRACT.md** and **fixtures.js** mappers.
- **Coupling:** Adding a new panel screen or backend payload: (1) extend `read_backend_state.py` output, (2) add bridge getter in `backend-bridge.js`, (3) add CONTRACTS + normalizer in `contracts.js`, (4) add mapper in `fixtures.js`, (5) update BACKEND_DATA_CONTRACT.md. Keeps panel contract-driven and backend read-only.

### 5.6 Web server

- **web/app.py** is minimal: GET /health, GET /status. Reads from `.lumos` (or `src/.lumos`) and security presence for status; no panel serving, no write.
- **Coupling:** If later you add panel serving or write APIs, keep them behind explicit routes and preserve read-only and sandbox rules for core paths.

---

## 6. Summary diagram (logical)

```
┌─────────────────────────────────────────────────────────────────┐
│  Entry: lumos / lumos web                                         │
│  CLI: main.py  ──► CoreEngine, CoreState, Lumos, TaskEngine       │
│  Web: web/app.py  ──► /health, /status (read-only)               │
└─────────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────────────────────────────────┐
│  core/           │  │  task_engine/  security/  memory/  policy/   │
│  workspace_      │  │  engine/  context/  device/                   │
│  contract,       │  │  (profiles, permissions, notes, rules)       │
│  state, config  │  └─────────────────────────────────────────────┘
└────────┬────────┘                          │
         │                                   │
         ▼                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  .lumos/  (tasks, logs, trash, config, aliases, notes, presence,  │
│           identity, keystore)  — all writes via workspace_contract│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Panel (static)                                                  │
│  index.html ← app.js ← contracts.js ← fixtures.js                │
│                  ↑           ↑              ↑                     │
│  backend-bridge.js (__LUMOS_READ_STATE__)  read_backend_state.py │
│  (read-only; no web/app.py routes)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Future scaling (short list)

1. **CLI:** Split `main.py` into subcommand modules; keep a single router and shared CoreState/CoreEngine construction.
2. **Core state:** Any new persistent artifact → workspace_contract path + sink + CORE_STATE_PATH_NAMES; avoid ad-hoc paths.
3. **Panel live data:** When adding real API: keep contract (contracts.js + BACKEND_DATA_CONTRACT.md) as single schema; add an API layer that returns snake_case matching current payloads so existing mappers and normalizers stay valid.
4. **Web:** If panel is served by the same process, serve static panel from a dedicated prefix and keep /health and /status separate; avoid mixing write endpoints with read-only contract without explicit design.
5. **Tests:** Keep inviolable and workspace_contract tests; add integration tests for panel adapter (given __LUMOS_READ_STATE__, getXxxData() matches CONTRACTS).

---

## 8. Related docs

| Doc | Purpose |
|-----|---------|
| **docs/DEPENDENCY_AUDIT.md** | Dependency and import coupling audit: core ↔ security/task_engine/policy/memory, panel/web coupling, fat entrypoints, circular risk, safe refactor priorities. |
| **Stabilization audits and execution plan** | |
| **docs/STABILIZATION_MAIN_SPLIT_PLAN.md** | Plan to reduce main.py surface area: thin router, extraction of lock/presence/tasks/notes/status into cli modules; target structure, extraction order, exact moves, risks. |
| **docs/WORKSPACE_CONTRACT_STABILITY_AUDIT.md** | Stable public API for workspace_contract; risky usages outside contract; freeze rules; minimal safe improvements (path helpers, call-site alignment). |
| **docs/PERSISTENT_WRITE_PATH_AUDIT.md** | File-by-file list of write locations for tasks, logs, trash, config, aliases, notes, presence, identity, keystore; compliance with workspace_contract; remediation priorities. |
| **docs/WEB_STABILIZATION_AUDIT.md** | Web app dependency map; read-only guarantee; log path fix; rules to keep web minimal; safe next steps and panel-serving guidance. |
| **docs/PANEL_READONLY_AUDIT.md** | Panel read-only data flow (backend-bridge, contracts, fixtures, read_backend_state.py, __LUMOS_READ_STATE__); weak points; contract safety; refactor priorities. |
| **docs/STARTUP_HEALTH_AUDIT.md** | startup_health.py dependency hygiene; no workspace_contract/security/presence_lock import; boundary rules; injected deps only. |
| **docs/STABILIZATION_EXECUTION_PLAN.md** | Single execution plan: top 7 tasks in safest order, analysis vs code-change, low-risk first, no-touch areas, regression test checklist. |

This map is the single reference for core modules, panel structure, backend contracts, and coupling; update it when adding new core state, panel screens, or entry points.

---

## Current verified entry chain

Verified on 2026-06-09:

```text
lumos / python -m lumos_core
-> src/lumos_core/__main__.py
-> src/main.py
-> core.lumos_runtime.create_runtime
-> cli.cli_router.run_cli_loop
```

Current active runtime is `src/`.

`packages/kando_*` modules exist as separated/package-oriented Kando modules, but the root `lumos` entrypoint does not currently start from those packages.

Root `package.json` contains `build: cd ui && npm install && npm run build`, but no `ui/` directory is visible in the current confirmed project map. Treat it as a suspicious or legacy build target until verified.
