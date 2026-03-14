# Web Stabilization Audit

**Scope:** `web/app.py` and its dependencies for stabilization safety.

**Constraint:** No runtime code changes; audit only.

---

## 1. Current Dependency Map for web/app.py

### 1.1 Direct imports (load time)

| Import | Source | Purpose |
|--------|--------|---------|
| `json`, `os`, `sys`, `Path`, `HTTPServer`, `BaseHTTPRequestHandler` | stdlib | HTTP server, path, env |
| `VERSION` | `lumos_core.version` (optional; fallback `"0.1.0"`) | /health response |

**Entry:** `lumos_core/__main__.py` runs web by loading `web/app.py` via `importlib` from repo `web/app.py`; before that it prepends `_REPO_ROOT`, `_SRC` is set from `web/app.py`’s `__file__` (parent.parent = repo root). So `web/app.py` adds `src` to `sys.path` and then optionally imports `lumos_core.version`.  
**lumos_core.version:** Single constant `VERSION`; no further src dependencies.

### 1.2 Lazy / request-time import (/status only)

| Import | Location in app | Purpose |
|--------|------------------|---------|
| `security.presence_lock` as `pl` | Inside `_read_status_snapshot()`, in try block | `pl.load_presence_cfg(Path(base))`, `pl.is_running()` |

So **/health** does not import any src module beyond `lumos_core.version`.  
**/status** triggers import of `security.presence_lock`.

### 1.3 Transitive dependency tree (when /status is called)

```
web/app.py
  └── security.presence_lock
        ├── core.logfmt          (logfmt)
        └── core.workspace_contract  (append_log_line, save_presence_cfg_json)
              └── pathlib only (no other src imports)
```

- **core.logfmt:** No src imports; pure helper (logfmt string formatting).
- **core.workspace_contract:** Imports only `pathlib` from stdlib; defines path helpers and write sinks (append_log_line, save_presence_cfg_json, etc.). No import of main, state, task_engine, memory, engine, etc.

**Optional dependency:** `security.presence_lock` does `try: import cv2` at module load; if cv2 is missing, `cv2 = None`. Web does not use cv2 directly; only `is_running()` and `load_presence_cfg()` are used, which do not require cv2.

### 1.4 What web does **not** import

- `main` (CLI)
- `core.state`, `core.engine`, `core.lumos`, `core.startup_health`, `core.config`, `core.inviolable`
- `task_engine`
- `memory.memory`, `memory.secure_store`
- `security.lock`, `security.keystore`, `security.identity`, `security.aliases`
- `policy`, `engine` (online/offline), `context`

So the **dependency depth** is shallow: at most **web → presence_lock → logfmt + workspace_contract**. No CLI, no state machine, no task engine, no keystore/identity.

---

## 2. Stabilization Risks

### 2.1 Incorrect log path (behavioral bug)

- **Location:** `web/app.py` ~50–51: `logp = base / "log.txt"`.
- **Contract/canonical:** `workspace_contract.logs_file_path(base)` = `base / "logs" / "log.txt"` (i.e. `logs` subdir).
- **Risk:** Web reads `.lumos/log.txt` (or `src/.lumos/log.txt`) instead of `.lumos/logs/log.txt`. If logs are only written under `logs/log.txt`, web’s `last_log_ts` will always be empty. This makes /status inconsistent with CLI “durum” and with any reader that uses `logs_file_path`.
- **Severity:** Medium (read-only; no data loss, but /status is misleading).

### 2.2 Pulling write capability into the web process

- **Fact:** `security.presence_lock` is imported for /status and it imports `append_log_line` and `save_presence_cfg_json` from `core.workspace_contract`. So the **web process** loads the module that contains all core write sinks (logs, config, presence, aliases, notes, identity, keystore, tasks, trash).
- **Current use:** Web only calls `load_presence_cfg()` (read) and `is_running()` (read). It never calls `append_log_line`, `save_presence_cfg`, or any other write.
- **Risk:** If someone later adds a route or helper that calls a presence_lock or workspace_contract write function from the web handler, writes would happen in the web process without the same lifecycle as the CLI (e.g. no lock state, no sandbox_mode from main). Mitigation: keep web explicitly read-only and do not add write calls; see rules below.

### 2.3 Base dir discovery duplicated

- **Location:** `web/app.py` `_lumos_dir()`: prefers `repo/src/.lumos`, else `repo/.lumos`.
- **Risk:** Duplicated and slightly different from main’s `_lumos_dir()` (main returns `.lumos` string, no repo path). If repo layout or canonical base changes, web and main can diverge. Prefer a single source of truth (e.g. env `LUMOS_BASE_DIR` or a shared helper) for stabilization.

### 2.4 Panel serving added later

- **Current:** Web has no panel routes. Panel is separate (e.g. `panel/scripts/read_backend_state.py` produces JSON; panel UI is likely static or served elsewhere).
- **Risk if panel is served by the same process:** To serve a “dashboard” or “system” view, there could be pressure to:
  - Import `task_engine`, `core.startup_health`, `core.state`, or `panel/scripts/read_backend_state`-style logic into the web app.
  - Add write routes (e.g. “save config”, “run task”) that would pull main/cli or core state and break the “read-only, minimal” guarantee.
- **Mitigation:** Keep panel as static assets + a single read-only API (e.g. one endpoint that returns a snapshot). Do not import main, CLI, or write paths; do not add POST/write handlers. See rules and recommendations below.

### 2.5 Optional cv2 in presence_lock

- **Fact:** `presence_lock` does `try: import cv2 except: cv2 = None`. When web imports presence_lock, that import runs; if cv2 is installed, it is loaded in the web process.
- **Risk:** Low for correctness; possible minor memory/startup cost. Web does not start the presence thread or use the camera; only config read and `is_running()` are used.

---

## 3. Explicit Rules to Keep Web Minimal

Adopt these as explicit stabilization rules; enforce in review and, if desired, via a small lint or checklist.

1. **No main or CLI import**  
   Web must not `import main` or any CLI entry (e.g. `lumos_core.__main__`’s CLI path). Web must not run the interactive loop or load full Lumos state (lock, keystore, task store, etc.) for normal requests.

2. **No write flows**  
   Web must not call any function that performs a persistent write to core state. Forbidden call targets include (but are not limited to): `append_log_line`, `save_*_json` / `save_*` in workspace_contract, `save_aliases`, `save_config`, `save_presence_cfg`, `save_identity_json`, `save_keystore_json`, `save_notes_enc_json`, `save_task_store_json`, `ensure_trash_dir`, `move_to_trash`, and any method that ultimately calls these (e.g. `nm._save_to_store()`). Allowed: read-only file access and read-only use of presence_lock (`load_presence_cfg`, `is_running`).

3. **Use contract path helpers for any path under .lumos**  
   Any path under the Lumos base (e.g. logs, config, presence, tasks) must be obtained via `core.workspace_contract` path helpers (e.g. `logs_file_path`, `presence_cfg_path`) or a wrapper that uses them—not ad-hoc `base / "log.txt"` or `base / "presence.json"`. This keeps web aligned with the rest of the stack and avoids path drift (e.g. log file location).

4. **Keep /health and /status minimal and read-only**  
   - **/health:** Must remain a simple liveness check: return `{"ok": true, "version": "..."}`. No filesystem or core reads required.  
   - **/status:** Must remain read-only: only read presence config, presence thread status, and (if needed) last log timestamp from the canonical log file. No state mutation, no lock/unlock, no task execution, no config/alias/notes/identity/keystore writes.

5. **If panel is served from the same process**  
   - Serve panel as **static files** (HTML/JS/CSS) and/or a **single read-only API** that returns a snapshot (e.g. one JSON payload for dashboard/system).  
   - Do **not** add routes that trigger task execution, config save, presence start/stop, lock/unlock, or any other write or state-changing operation.  
   - Prefer reusing a **minimal read-only** helper (e.g. a dedicated module that only reads from disk and uses contract paths) rather than importing `main`, `core.state`, `core.lumos`, or `panel/scripts/read_backend_state` in full if that script pulls extra core. If a shared “read-only snapshot” module is introduced, it must not import main or any write path.

6. **No new dependencies on heavy core**  
   Do not add imports of `core.lumos`, `core.state`, `core.engine`, `task_engine`, `memory.memory`, `security.keystore`, `security.identity`, `policy`, or `engine` (online/offline) in the web request path unless explicitly justified and documented as an exception. Prefer the minimal set already used: version, presence_lock (read-only surface), and contract path helpers.

---

## 4. Safe Next-Step Recommendations

### 4.1 Fix log path (stabilization, no new features)

- In `_read_status_snapshot()`, replace `logp = base / "log.txt"` with the contract path:
  - Import once at top of `web/app.py`: `from core.workspace_contract import logs_file_path` (and optionally `presence_cfg_path` if you want to align presence config path too).
  - Set `logp = logs_file_path(base)`.
- This makes /status’s `last_log_ts` consistent with CLI and other readers, without adding write or new dependencies (workspace_contract is already pulled in via presence_lock).

### 4.2 Align base dir with contract / env

- Prefer a single source for “Lumos base dir”: e.g. `os.getenv("LUMOS_BASE_DIR", ".lumos")` with resolve relative to CWD or repo root, and use that in both web and (where applicable) main. Optionally, a thin shared helper in `core` or `lumos_core` that only returns the base path (no other imports) so web and CLI stay in sync without web importing main.

### 4.3 Document and enforce “web is read-only”

- In `web/app.py` docstring or a short `web/README.md`, state: “Web v1 is read-only: no writes to core state; /health and /status only. New routes must not call any write sink or main/CLI.”
- Add the rules from §3 to the repo’s stabilization or architecture docs (e.g. `docs/WEB_STABILIZATION_AUDIT.md` or `docs/ARCHITECTURE_MAP.md`) and reference them in PR templates or contribution guidelines.

### 4.4 If panel serving is added later

- **Option A (recommended):** Keep web as-is; serve panel as static files (e.g. from `panel/` or a build output) via the same HTTP server or a simple static handler. Expose one read-only API endpoint (e.g. `GET /api/state`) that returns a snapshot. Implement that endpoint by either:
  - Copying the minimal read logic from `panel/scripts/read_backend_state.py` into a small module used only by web (no main, no write paths), or
  - Invoking the script as a subprocess and streaming JSON, so the web process does not load task_engine, startup_health, etc.
- **Option B:** If the snapshot logic is implemented inside the web process, add a dedicated “read-only snapshot” module that imports only: path helpers from workspace_contract, presence_lock (read-only), and minimal file reads (tasks.json, trash dir listing, logs, etc.). No main, no state, no task_engine.workspace_contract write sinks, no keystore/identity. Document that module as the single place for “web read-only” so future changes don’t accidentally add writes or heavy core.

### 4.5 Optional: thin presence facade for web

- To avoid loading the full `presence_lock` (and thus workspace_contract write sinks) into the web process, introduce a minimal “presence status” facade used only by web (e.g. `web/presence_status.py` or under `src/`): it only reads `presence.json` (via `presence_cfg_path`) and exposes “is thread running” via a simple mechanism (e.g. a shared file or env that the CLI sets when it runs presence). Then web would not need to import `security.presence_lock` at all. This is a larger change; treat as optional and only if you want to minimize web’s dependency surface further.

---

## Summary

| Item | Status |
|------|--------|
| **Dependency depth** | Shallow: web → (on /status) presence_lock → logfmt + workspace_contract. No main, CLI, state, task_engine, memory, keystore, identity. |
| **/health** | Minimal; only VERSION (and stdlib). |
| **/status** | Read-only use of presence_lock (load_presence_cfg, is_running); log path is wrong (base/log.txt vs base/logs/log.txt). |
| **Risks** | Log path bug; write capability loaded via presence_lock; base dir duplication; future panel could pull too much core. |
| **Rules** | No main/CLI; no write flows; use contract path helpers; keep /health and /status minimal and read-only; if panel is served, keep it static + single read-only API; no heavy core in request path. |
| **Next steps** | Fix log path with logs_file_path; align base dir; document and enforce read-only; if adding panel, use static + one read-only API or a dedicated minimal snapshot module. |

No runtime code was modified; this document is audit and recommendation only.
