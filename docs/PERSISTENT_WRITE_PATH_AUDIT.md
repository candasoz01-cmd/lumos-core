# Persistent Write Path Audit

**Scope:** All persistent write paths across the repository for the nine core-state areas: **tasks**, **logs**, **trash**, **config**, **aliases**, **notes**, **presence**, **identity**, **keystore**.

**Reference:** `src/core/workspace_contract.py` — path helpers and write sinks with sandbox guard.

**Constraint:** No code changes; audit only.

---

## 1. File-by-File List of Write Locations

### 1.1 Tasks (tasks.json under base/tasks/)

| File | Location | What is written | How |
|------|----------|------------------|-----|
| **src/task_engine/engine.py** | ~217–226 | TaskStore persistence (tasks + next_id) | `_save()` → `save_task_store_json(tasks_dir=self.base_dir, data=..., sandbox_mode=..., live_base_dir=...)` |
| **src/core/workspace_contract.py** | ~297–328 | tasks.json content | `save_task_store_json()`: uses `tasks_dir / "tasks.json"`, calls `allow_write_to_core` when `sandbox_mode`; implements the sink |

**Directory creation for tasks:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/main.py** | ~939 | tasks directory | `(base_path / "tasks").mkdir(parents=True, exist_ok=True)` — ad-hoc path, no contract helper |

---

### 1.2 Logs (logs/log.txt)

| File | Location | What is written | How |
|------|----------|----------------|-----|
| **src/security/presence_lock.py** | ~16–30, 239, 266, 276 | Log lines (device_locked, presence_started, presence_stopped) | `_append_log(...)` → `append_log_line(base_dir, line, is_sandbox_mode=...)` |
| **src/core/workspace_contract.py** | ~123–144 | logs/log.txt content | `append_log_line()`: uses `logs_file_path(base_dir)`, `allow_write_to_core`; implements the sink |

**Directory creation for logs:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/main.py** | ~940 | logs directory | `(base_path / "logs").mkdir(parents=True, exist_ok=True)` — ad-hoc path |
| **src/core/workspace_contract.py** | ~142 | logs dir (when appending) | `path.parent.mkdir(parents=True, exist_ok=True)` inside `append_log_line` |

---

### 1.3 Trash

| File | Location | What is written | How |
|------|----------|-----------------|-----|
| **src/core/workspace_contract.py** | ~342–360 | trash directory creation | `ensure_trash_dir(base_dir, is_sandbox_mode=...)`: uses `trash_path(writing_base_dir(...))`, `allow_write_to_core` |
| **src/core/workspace_contract.py** | ~363–396 | move file/dir into trash | `move_to_trash(base_dir, source_path, ...)`: uses `trash_path(writing_base_dir(...))`, `is_allowed_trash_path`, `allow_write_to_core`, `shutil.move` |

**Callers of trash writes:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/main.py** | ~941–942 | ensure trash exists at bootstrap | `ensure_trash_dir(base_path, is_sandbox_mode=sandbox_mode)` |

No other production code was found that creates the trash dir or moves files into trash. TaskStore does not use move_to_trash for archiving (archiving only sets `archived=True` in tasks.json).

---

### 1.4 Config (config.json)

| File | Location | What is written | How |
|------|----------|-----------------|-----|
| **src/core/config.py** | ~66–73 | config.json content | `save_config(base_dir, data, is_sandbox_mode=...)` → `save_config_json(Path(base_dir), data, is_sandbox_mode=...)` |
| **src/core/workspace_contract.py** | ~173–195 | config.json content | `save_config_json()`: uses `config_file_path(base_dir)`, `allow_write_to_core` |

**Directory creation for config:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/main.py** | ~942 | config directory | `(base_path / "config").mkdir(parents=True, exist_ok=True)` — ad-hoc path |

No other production code was found that writes config.json.

---

### 1.5 Aliases (aliases.json)

| File | Location | What is written | How |
|------|----------|-----------------|-----|
| **src/security/aliases.py** | ~23–32 | aliases.json content | `save_aliases(base_dir, aliases, is_sandbox_mode=...)` → `save_aliases_json(base_dir, aliases, is_sandbox_mode=...)` |
| **src/core/workspace_contract.py** | ~147–170 | aliases.json content | `save_aliases_json()`: uses `alias_file_path(base_dir)`, `allow_write_to_core` |

**Callers:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/main.py** | ~861, 1345, 1355 | Save aliases | `save_aliases(base_dir, ..., is_sandbox_mode=sandbox_mode)` |

No directory creation specific to aliases (file lives under base_dir; parent is base_dir).

---

### 1.6 Notes (notes.enc.json)

| File | Location | What is written | How |
|------|----------|-----------------|-----|
| **src/memory/secure_store.py** | ~56–68 | notes.enc.json content (encrypted) | `save(root_key, notes)` → `save_notes_enc_json(self.base, data, is_sandbox_mode=self._is_sandbox_mode)` |
| **src/core/workspace_contract.py** | ~198–219 | notes.enc.json content | `save_notes_enc_json()`: uses `notes_file_path(base_dir)`, `allow_write_to_core` |

**Call chain:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/memory/memory.py** | ~41–46, 71, 86 | Persist notes | `_save_to_store()` → `self.store.save(self.root_key, self.notes)` |
| **src/main.py** | ~831 | After self-test note pop | `nm._save_to_store()` |

**Directory creation:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/memory/secure_store.py** | ~28 | base dir for notes | `self.base.mkdir(parents=True, exist_ok=True)` in `__init__` — ad-hoc (base is Path(base_dir)) |

---

### 1.7 Presence (presence.json)

| File | Location | What is written | How |
|------|----------|-----------------|-----|
| **src/security/presence_lock.py** | ~166–172 | presence.json content | `save_presence_cfg(base_dir, cfg, is_sandbox_mode=...)` → `save_presence_cfg_json(base_dir, asdict(cfg), is_sandbox_mode=...)` |
| **src/core/workspace_contract.py** | ~222–244 | presence.json content | `save_presence_cfg_json()`: uses `presence_cfg_path(base_dir)`, `allow_write_to_core` |

**Callers:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/main.py** | ~1131, 1143, 1157, 1171 | Save presence config (ac, kapat, sure) | `pl.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)` |

No separate directory for presence (file under base_dir).

---

### 1.8 Identity (identity.json)

| File | Location | What is written | How |
|------|----------|-----------------|-----|
| **src/security/identity.py** | ~43–77 | identity.json content (init) | `init(root_key)` → `save_identity_json(self.paths.base_dir, data, is_sandbox_mode=self._is_sandbox_mode)` |
| **src/core/workspace_contract.py** | ~247–269 | identity.json content | `save_identity_json()`: uses `identity_file_path(base_dir)`, `allow_write_to_core` |

**Directory creation:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/security/identity.py** | ~39 | base dir | `self.paths.base_dir.mkdir(parents=True, exist_ok=True)` in `__init__` — ad-hoc |

**Direct write (non-compliant):**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/security.bak_lock/identity.py** | ~37, 75 | base dir + identity.json | `self.paths.base_dir.mkdir(...)` and `self.paths.identity_file.write_text(json.dumps(data, ...))` — bypasses contract |

---

### 1.9 Keystore (keystore.json)

| File | Location | What is written | How |
|------|----------|-----------------|-----|
| **src/security/keystore.py** | ~37–42 | keystore.json content (init) | `init(passphrase)` → `save_keystore_json(self.paths.base_dir, data, is_sandbox_mode=self._is_sandbox_mode)` |
| **src/core/workspace_contract.py** | ~272–294 | keystore.json content | `save_keystore_json()`: uses `keystore_file_path(base_dir)`, `allow_write_to_core` |

**Directory creation:**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/security/keystore.py** | ~30 | base dir | `self.paths.base_dir.mkdir(parents=True, exist_ok=True)` in `__init__` — ad-hoc |

**Direct write (non-compliant):**  
| File | Location | What | How |
|------|----------|------|-----|
| **src/security.bak_lock/keystore.py** | ~28, 40 | base dir + keystore.json | `self.paths.base_dir.mkdir(...)` and `self.paths.keystore_file.write_text(json.dumps(data, ...))` — bypasses contract |

---

### 1.10 Other Writes (non–core-state or test/script)

| File | Location | What | Compliant / Notes |
|------|----------|------|-------------------|
| **src/core/workspace_contract.py** | 142, 166, 192, 217, 241, 266, 291, 323, 360, 396 | Implementation of sinks (path.write_text, mkdir, shutil.move) | N/A — this is the contract implementation |
| **panel/scripts/read_backend_state.py** | ~396 | `panel/js/state_inject.js` | Not core-state; dev bridge file under repo, not under .lumos |
| **src/tools/run_classify.py** | ~24 | `output.json` (CWD) | Not core-state; tool output |
| **scripts/legacy/** | Various | Patches to main.py / presence_lock.py; write_text to source files | Legacy tooling; not runtime persistent state |
| **tests/** | test_workspace_contract.py, test_presence_lifecycle.py | tmp_path / ROOT/.lumos/... write_text for test setup | Test fixtures only; not production |
| **web/app.py** | ~75 | `self.wfile.write(...)` | HTTP response body, not disk |
| **lumos.py** | ~14 | `p = base / "identity.json"` | Read-only (read_text); no write |

---

## 2. Whether Each Write Is Compliant With workspace_contract

| Area | Write (file content) | Compliant? | Notes |
|------|----------------------|------------|--------|
| **Tasks** | tasks.json | Yes | TaskStore._save() → save_task_store_json only; guard when sandbox_mode |
| **Logs** | logs/log.txt | Yes | All log appends via append_log_line only |
| **Trash** | dir creation + move | Yes | ensure_trash_dir, move_to_trash only; guards applied |
| **Config** | config.json | Yes | save_config → save_config_json only |
| **Aliases** | aliases.json | Yes | save_aliases → save_aliases_json only |
| **Notes** | notes.enc.json | Yes | SecureNotesStore.save() → save_notes_enc_json only |
| **Presence** | presence.json | Yes | save_presence_cfg → save_presence_cfg_json only |
| **Identity** | identity.json (production) | Yes | DeviceIdentity.init() → save_identity_json only |
| **Identity** | identity.json (bak_lock) | No | Direct write_text; no guard |
| **Keystore** | keystore.json (production) | Yes | FileKeyStore.init() → save_keystore_json only |
| **Keystore** | keystore.json (bak_lock) | No | Direct write_text; no guard |

**Directory creation (core-state dirs):**

| Location | Compliant? | Notes |
|----------|------------|--------|
| main.py: base_path.mkdir, (base_path / "tasks").mkdir, (base_path / "logs").mkdir, (base_path / "config").mkdir | No | Ad-hoc paths; no contract helper or allow_write_to_core |
| main.py: ensure_trash_dir | Yes | Uses contract |
| workspace_contract: append_log_line path.parent.mkdir | Yes | Inside sink |
| workspace_contract: save_* path.parent.mkdir, ensure_trash_dir path.mkdir, save_task_store_json tasks_dir_path.mkdir | Yes | Inside sinks |
| security/identity.py: base_dir.mkdir | No | Ad-hoc; no ensure_* from contract |
| security/keystore.py: base_dir.mkdir | No | Same |
| memory/secure_store.py: self.base.mkdir | No | Same |
| security.bak_lock/identity.py, keystore.py: base_dir.mkdir | No | Same; plus direct file write |

---

## 3. Direct File Writes That Should Be Considered Stabilization Risks

### High (bypass contract and guard)

1. **src/security.bak_lock/identity.py** (~75)  
   - `self.paths.identity_file.write_text(json.dumps(data, indent=2), encoding="utf-8")`  
   - Writes identity.json with no sandbox guard and no use of `identity_file_path` / `save_identity_json`.  
   - **Risk:** If ever used in production or mixed with sandbox mode, could write to live core path.

2. **src/security.bak_lock/keystore.py** (~40)  
   - `self.paths.keystore_file.write_text(json.dumps(data, indent=2), encoding="utf-8")`  
   - Same for keystore.json.  
   - **Risk:** Same as above.

### Medium (directory creation only; file content via contract)

3. **src/main.py** (~938–942)  
   - `base_path.mkdir(...)`, `(base_path / "tasks").mkdir(...)`, `(base_path / "logs").mkdir(...)`, `(base_path / "config").mkdir(...)`  
   - Creates core-state directories without contract helpers or `allow_write_to_core`.  
   - **Risk:** In sandbox mode, main could still create live `.lumos/tasks`, `.lumos/logs`, `.lumos/config` at startup. File writes to those dirs later go through contract; only dir creation is unguarded.

4. **src/security/identity.py** (~39), **src/security/keystore.py** (~30), **src/memory/secure_store.py** (~28)  
   - `base_dir.mkdir(parents=True, exist_ok=True)` or `self.base.mkdir(...)`  
   - **Risk:** Same idea: directory creation is ad-hoc; if base_dir were ever wrong or sandbox semantics extended to “no live core dir creation,” these would need to go through contract (e.g. an ensure_* that uses allow_write_to_core).

### Low (test / script; not production core state)

5. **tests/test_presence_lifecycle.py**, **tests/test_workspace_contract.py**  
   - Direct `write_text` on tmp_path or ROOT/.lumos/... for test setup.  
   - **Risk:** Low; test fixtures. Only risk is tests assuming paths that diverge from contract (e.g. log path).

6. **panel/scripts/read_backend_state.py** (--write)  
   - Writes `panel/js/state_inject.js`.  
   - **Risk:** None for core-state; not under .lumos.

7. **src/tools/run_classify.py**  
   - Writes `output.json` in CWD.  
   - **Risk:** None for core-state.

---

## 4. Safest Remediation Priorities

**Do not modify code** per request; below is the recommended order for a future stabilization phase.

### P1 — Document and isolate (no behavior change)

1. **Mark bak_lock as non-contract.**  
   In docs or module docstrings, state that `security.bak_lock` is legacy/backup and must not be used in production; it does not use workspace_contract and must not be mixed with sandbox or canonical base.

2. **Document directory-creation gap.**  
   In WORKSPACE_CONTRACT_STABILITY_AUDIT or this doc, state that core-state **directory** creation in main.py and in identity/keystore/secure_store is currently ad-hoc and does not go through contract helpers or sandbox guard.

### P2 — Low-risk, contract-aligned improvements

3. **Use contract path helpers for reads where missing.**  
   Already covered in WORKSPACE_CONTRACT_STABILITY_AUDIT (e.g. identity_file_path, keystore_file_path for read paths). No new write paths.

4. **Add optional contract helpers for dirs (if desired).**  
   If contract is extended with `ensure_tasks_dir`, `ensure_logs_dir`, `ensure_config_dir` (each using the same path as the contract and `allow_write_to_core` when creating), main.py bootstrap could call these instead of raw `(base_path / "tasks").mkdir(...)` etc. Same for identity/keystore/secure_store base dir if an `ensure_base_dir`-style helper exists. Reduces risk of creating live core dirs in sandbox.

### P3 — Replace direct writes (behavior-preserving)

5. **Replace bak_lock writes with contract sinks.**  
   If bak_lock remains in tree and must behave like production: in `security.bak_lock/identity.py` and `keystore.py`, replace `identity_file.write_text(...)` / `keystore_file.write_text(...)` with `save_identity_json(self.paths.base_dir, data)` / `save_keystore_json(self.paths.base_dir, data)` (and optionally add `is_sandbox_mode` if bak_lock is ever used with sandbox). Then remove direct write_text. Requires tests to ensure bak_lock still works as intended.

### P4 — Tests and guardrails

6. **Test that core-state file writes go through contract.**  
   Add or extend a test (e.g. in test_workspace_contract or a new test file) that: for any path under a given base that `is_core_state_path(base, path)` returns True, no production code path (excluding workspace_contract.py and bak_lock) performs a direct `write_text` or `open(..., "w")` on that path. This guards against future regressions.

7. **Optional: lint or script check.**  
   A simple grep/script that fails if any file under `src/` (excluding `src/core/workspace_contract.py` and `src/security.bak_lock`) contains `.write_text(` or `open(..., "w")` on a path that looks like `*identity.json`, `*keystore.json`, `*tasks.json`, etc. Reduces chance of new direct writes.

---

## Summary Table

| Area    | File content write | Compliant | Dir creation | Compliant |
|---------|--------------------|-----------|--------------|-----------|
| Tasks   | task_engine → save_task_store_json | Yes | main: ad-hoc | No |
| Logs    | presence_lock → append_log_line     | Yes | main: ad-hoc; contract inside append_log_line | Partial |
| Trash   | ensure_trash_dir, move_to_trash     | Yes | contract     | Yes |
| Config  | config.save_config → save_config_json | Yes | main: ad-hoc | No |
| Aliases | aliases.save_aliases → save_aliases_json | Yes | —           | — |
| Notes   | secure_store.save → save_notes_enc_json | Yes | secure_store: ad-hoc | No |
| Presence| presence_lock.save_presence_cfg → save_presence_cfg_json | Yes | — | — |
| Identity| identity.init → save_identity_json  | Yes | identity: ad-hoc | No |
| Identity| bak_lock identity_file.write_text | **No** | bak_lock: ad-hoc | No |
| Keystore| keystore.init → save_keystore_json  | Yes | keystore: ad-hoc | No |
| Keystore| bak_lock keystore_file.write_text  | **No** | bak_lock: ad-hoc | No |

**Stabilization risks:** 2 direct file writes (bak_lock identity + keystore); 4+ ad-hoc directory creations (main + identity + keystore + secure_store).  
**Remediation:** P1 document/isolate → P2 optional contract dir helpers and read-path alignment → P3 replace bak_lock writes if kept → P4 tests/lint.

No code was modified; this document is audit-only.
