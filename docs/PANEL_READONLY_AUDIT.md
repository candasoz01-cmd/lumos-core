# Panel Read-Only Data Flow Audit

**Scope:** Panel read-only data flow: `panel/js/backend-bridge.js`, `panel/js/contracts.js`, `panel/js/fixtures.js`, `panel/scripts/read_backend_state.py`, and the injected `__LUMOS_READ_STATE__` flow.

**Constraint:** No runtime code changes; audit only.

---

## 1. Read-Only Guarantee Assessment

### 1.1 Backend script (read_backend_state.py)

| Aspect | Assessment |
|--------|------------|
| **Writes to Lumos core state (.lumos)?** | **No.** The script only reads from the workspace (config mtime, identity/keystore path existence, tasks, trash, logs). It does not call any workspace_contract write sink (save_*, append_log_line, ensure_trash_dir, move_to_trash). |
| **Writes to repo (non–core-state)?** | **Yes, one path.** When run with `--write`, it writes to `panel/js/state_inject.js` with the line `window.__LUMOS_READ_STATE__ = <JSON>;`. This is a **dev/build artifact** (injected state for the static panel). It is not a write to `.lumos` or any core state path. |
| **Imports that could write?** | The script imports `core.workspace_contract` (path helpers, writing_base_dir, sandbox_base_path, trash_path, logs_dir_path, etc.) and `core.startup_health.consent_ok`. It does **not** import or call any save/append/move function. So the process is read-only with respect to Lumos state. |

**Conclusion:** For Lumos core state, the script is **read-only**. The only write is to `panel/js/state_inject.js`, which is intentional and documented; it does not touch core state.

### 1.2 Panel JS (browser)

| File | Reads | Writes |
|------|--------|--------|
| **backend-bridge.js** | `window.__LUMOS_READ_STATE__` only. No `fetch`, no XHR, no form POST. | None. Returns `null` or a copy of the object; does not mutate `__LUMOS_READ_STATE__` (callers may mutate the returned object). |
| **contracts.js** | CONTRACTS (local), optional LumosContracts. `applyContractFallbacks(screenKey, data)` **mutates** the passed-in `data` object (fills undefined keys with defaults). | No disk, no network. In-memory mutation of the data object only. |
| **fixtures.js** | PAYLOAD_FIXTURES (local), LumosContracts (optional). Mappers read `src.data` (backend or fixture payload). | None. |
| **state_inject.js** | N/A (it **sets** `window.__LUMOS_READ_STATE__` when the script runs). | Only the initial assignment when the script loads; no ongoing writes. |
| **app.js** | Bridge.readBackend*(), getEffectiveState(), mockState, DEMO_SCENARIOS, LumosFixtures, LumosContracts. No fetch/POST. | No backend or file writes. UI state (e.g. currentScenario, useFixtureData) is in-memory only. |

**Conclusion:** The panel is **read-only** with respect to the backend and to the Lumos workspace. There is no code path that sends a write request to a server or that writes to core state. The only “write” in the pipeline is the one performed **outside** the browser: `read_backend_state.py --write` overwriting `state_inject.js`.

### 1.3 Injected __LUMOS_READ_STATE__ flow

1. **Load order (index.html):** `contracts.js` → `fixtures.js` → `state_inject.js` → `backend-bridge.js` → `app.js`.
2. **state_inject.js** either: (a) contains a static default object (committed in repo), or (b) has been overwritten by `read_backend_state.py --write` with live read state. In both cases it assigns `window.__LUMOS_READ_STATE__ = <object>` once at load.
3. **backend-bridge.js** exposes `readBackendDashboardState()`, `readBackendSandboxState()`, … which call `getReadState()` and return the corresponding slice of `__LUMOS_READ_STATE__` or `null` if missing/invalid.
4. **app.js** `get*SourceData()` functions try, in order: Bridge backend → fixture payloads → demo/mockState. So when backend data is present and valid, the panel shows it; otherwise it falls back to fixture or demo without ever writing back.

**Conclusion:** The injection flow is one-way: script (or static file) → `__LUMOS_READ_STATE__` → bridge → app. No round-trip write from panel to backend or to .lumos.

---

## 2. Weak Points or Ambiguity

### 2.1 Tasks file path mismatch (data correctness / “empty” backend)

- **Backend script:** Uses `tasks_file = base / "tasks.json"` (i.e. `.lumos/tasks.json`) in `_read_tasks_payload` and `_task_engine_health`, and `tasks_path = base / "tasks.json"` for `system_paths["tasks"]`.
- **Production layout (main.py):** Uses `task_store = TaskStore(base_path / "tasks", ...)`, so the tasks file lives at `.lumos/tasks/tasks.json`.
- **Effect:** When the workspace is in the standard layout, the script never finds a tasks file; `tasks_file_exists` is false, `task_list` is empty, and the panel shows “Görev listesi yok” or empty tasks even when tasks exist. So the panel can appear “read-only but wrong” (no data) rather than obviously broken.
- **Recommendation:** Use the same path as the rest of the stack: e.g. `base / "tasks" / "tasks.json"`, or a contract helper such as `tasks_dir_path(base) / "tasks.json"` if one is added.

### 2.2 Trash path built ad-hoc in script

- **Script:** `trash_dir = base_resolved / "trash"`. This matches the contract’s `trash_path(base)` but does not use the contract helper. If the contract ever changed the trash dir name, the script would be out of sync.
- **Recommendation:** Use `trash_path(base)` from workspace_contract for consistency and single source of truth.

### 2.3 Contract fallback logic can mask missing or wrong backend data

- **Mechanism:** `applyContractFallbacks(screenKey, data)` fills any key present in `CONTRACTS[screenKey]` but missing in `data` with the contract default (copy of default value). So if the backend returns a partial object (e.g. missing `task_list` or wrong shape), the normalizer still produces a full object; the UI then shows defaults for missing fields.
- **Risk:** A backend bug (e.g. wrong path, exception swallowed) can result in empty or wrong data; the panel will still render “valid” contract-shaped data (e.g. empty list, “—”). Operators might not notice that the data is fallback rather than real. So fallback **masks** backend/script issues; it does not fix them.
- **Mitigation:** Document that “empty list” or “Veri yok” can mean either “backend sent empty” or “backend unavailable / wrong path → fallback.” Consider a visible “source” indicator (e.g. “backend” vs “fixture” vs “demo”) so operators know when they are seeing live read state vs fallback.

### 2.4 Backend script tasks path and system_paths["tasks"] inconsistency with workspace_contract

- **system_paths["tasks"]** is set to `base / "tasks.json"` in the script. The rest of the codebase (and `is_core_state_path`) treats the tasks file as `base/tasks/tasks.json`. So the “Çalışma yolları” / system paths shown in the panel can point to a path that is not the one actually used by the CLI. This is both a correctness and a contract-safety issue.

### 2.5 Single write path: state_inject.js overwrite

- **What:** `read_backend_state.py --write` overwrites `panel/js/state_inject.js` with a single assignment and the current JSON snapshot.
- **Risk:** If the script is run with `--write` from a different env (e.g. different LUMOS_BASE_DIR or broken path), the injected state can be wrong or empty; the next panel load will show that state until the next `--write`. No automatic “stale” indicator exists. For stabilization, this is acceptable as an explicit dev step; it should remain clearly documented and optional (no production pipeline should depend on overwriting repo JS unless intended).

### 2.6 Keystore/identity “ready” derived from consent_ok only

- The script uses `consent_ok(base)` to set `keystore_ready` and `general_status`. It does not read keystore or identity content. So “Keystore hazır” / “Kilitli” is a proxy from consent only. This is intentional (no key ifşası) but worth noting: the panel does not reflect actual keystore init state, only consent.

---

## 3. Contract Safety Recommendations

1. **Use workspace_contract path helpers in read_backend_state.py for all core paths**  
   - Tasks: read from `base / "tasks" / "tasks.json"` (or use a future `tasks_dir_path(base) / "tasks.json"` if added).  
   - Trash: use `trash_path(base)` instead of `base / "trash"`.  
   - Logs: already correct (`base / "logs" / "log.txt`); consider `logs_file_path(base)` for consistency.  
   - Config/identity/keystore: already use contract helpers where used.  
   This keeps the script aligned with the rest of the stack and avoids path drift.

2. **Document the single non–core-state write**  
   In the script docstring or panel README, state explicitly: “The only write performed by this script is to `panel/js/state_inject.js` when run with `--write`. This is a dev/build artifact and does not modify Lumos core state (.lumos).”

3. **Keep backend output shape and panel contract in sync via one checklist or test**  
   - Backend output keys (e.g. dashboard.sandbox_mode, tasks.task_list, system.system_health keys) should match what fixtures.js mappers and contracts.js expect.  
   - Document the backend payload shape (e.g. in BACKEND_DATA_CONTRACT.md or similar) and, if feasible, add a small test or lint that checks that the script’s output includes the keys the panel expects, so renames or restructuring don’t silently break the panel.

4. **Do not add write endpoints or actions from the panel**  
   The panel must remain read-only: no “save config,” “run task,” “move to trash,” or “unlock” from the UI that would require the script or a future API to perform writes. Any such feature would need a separate design and explicit approval.

5. **Optional: source indicator in UI**  
   When data comes from `type: "backend"`, show a small “Canlı veri” or “Backend” badge; when from fixture/demo, show “Demo” or “Fixture.” This reduces the chance that contract fallback is mistaken for real backend data.

---

## 4. Stabilization-Safe Refactor Priorities

### P1 — Fix tasks path (correctness, no new features)

- In `read_backend_state.py`, change tasks file path from `base / "tasks.json"` to `base / "tasks" / "tasks.json"` (or the same path used by TaskStore). Update `_read_tasks_payload`, `_task_engine_health`, and `system_paths["tasks"]` accordingly. This aligns the script with main.py and workspace_contract and fixes “empty tasks” when tasks exist under `.lumos/tasks/`.

### P2 — Use contract path helpers in script (consistency)

- Use `trash_path(base)` for the trash directory.  
- Use `logs_file_path(base)` for the log file (already correct path; switch to helper for single source of truth).  
- Optionally add and use `tasks_dir_path(base)` in workspace_contract if the project adopts it; then use it here.

### P3 — Document fallback behavior and single write

- In docs (e.g. PANEL_READONLY_AUDIT.md or panel README): (a) Contract fallback fills missing keys; it can mask backend errors or wrong paths. (b) The only write is `--write` to `state_inject.js`; it is not a core-state write.

### P4 — Optional: backend shape contract test

- Add a minimal test that runs `read_backend_state.py` (no `--write`) against a temp dir with minimal structure (e.g. empty .lumos or with tasks/trash/logs), captures stdout JSON, and asserts presence of expected top-level keys (dashboard, sandbox, system, config, identity, keystore, tasks, trash, logs) and, if possible, key nested keys (e.g. system.system_health) so backend/panel contract drift is caught.

### P5 — No refactor (do not do)

- Do not add fetch/POST from panel to any “backend” that could write to .lumos or run CLI commands.  
- Do not change the read-only guarantee of the script (no new imports of save_*, append_log_line, move_to_trash, etc.).

---

## Summary Table

| Question | Answer |
|----------|--------|
| Is the panel fully read-only with respect to Lumos core state? | **Yes.** No code path in the panel or in the script writes to .lumos or calls workspace_contract write sinks. |
| Is there any accidental write path to core state? | **No.** The only write is script `--write` to `panel/js/state_inject.js` (dev artifact). |
| Does contract fallback mask risky data issues? | **Yes, partially.** Fallback fills missing keys with defaults, so wrong or empty backend data can look like “valid empty” data. Fix tasks path and document fallback to reduce confusion. |
| Are backend output and panel contracts cleanly separated? | **Yes.** Backend outputs snake_case payloads; fixtures.js mappers convert to panel shape; contracts.js defines CONTRACTS and normalizers. Separation is clear. Weak point is path/schema drift (tasks path, key names) if not kept in sync. |

**Stabilization-safe priorities:** P1 fix tasks path → P2 use contract path helpers in script → P3 document fallback and --write → P4 optional contract test → P5 do not add write flows.

No runtime code was modified; this document is audit and recommendation only.
