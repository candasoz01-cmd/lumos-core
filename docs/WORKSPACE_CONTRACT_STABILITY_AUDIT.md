# Workspace Contract Stability Audit

**Scope:** `src/core/workspace_contract.py` as the public core contract for Lumos workspace paths and persistent core-state writes.

**Constraint:** No runtime code changes; audit and recommendations only.

---

## 1. Stable Public API List

The following are the **exported path helpers and write sinks** that should be treated as the **stable public API** of the workspace contract. Callers should rely only on these for core paths and for any write that touches core state.

### 1.1 Constants (do not rename or change values; extend only via explicit contract change)

| Symbol | Purpose |
|--------|--------|
| `LUMOS_TRASH_DIRNAME` | Single trash directory name; no other trash/deleted dirs. |
| `LUMOS_SANDBOX_DIRNAME` | Single sandbox directory name; no other sandbox dirs. |
| `CORE_STATE_PATH_NAMES` | Tuple of core state path names under base; reference for overwrite/sandbox guard. |

### 1.2 Path helpers (read-only; return `Path`)

| Function | Returns | Use |
|----------|---------|-----|
| `trash_path(base_dir)` | `base_dir / "trash"` | Only valid trash location. |
| `sandbox_base_path(live_base_dir)` | `live_base_dir / "sandbox"` | Sandbox write target base. |
| `writing_base_dir(live_base_dir, is_sandbox_mode)` | Live base or sandbox base by mode. | Single source for write target base. |
| `alias_file_path(base_dir)` | `base_dir / "aliases.json"` | Aliases file. |
| `notes_file_path(base_dir)` | `base_dir / "notes.enc.json"` | Encrypted notes store. |
| `presence_cfg_path(base_dir)` | `base_dir / "presence.json"` | Presence config. |
| `identity_file_path(base_dir)` | `base_dir / "identity.json"` | Device identity. |
| `keystore_file_path(base_dir)` | `base_dir / "keystore.json"` | Keystore. |
| `config_file_path(base_dir)` | `base_dir / "config.json"` | Main config. |
| `logs_dir_path(base_dir)` | `base_dir / "logs"` | Logs directory. |
| `logs_file_path(base_dir)` | `base_dir / "logs" / "log.txt"` | Main log file. |

### 1.3 Write sinks (only way to persist core state; all respect sandbox guard)

| Function | Target | Guard |
|----------|--------|-------|
| `append_log_line(base_dir, line, *, is_sandbox_mode=False)` | `logs_file_path(base_dir)` | `allow_write_to_core` |
| `save_aliases_json(base_dir, aliases, *, is_sandbox_mode=False)` | `alias_file_path(base_dir)` | `allow_write_to_core` |
| `save_config_json(base_dir, data, *, is_sandbox_mode=False)` | `config_file_path(base_dir)` | `allow_write_to_core` |
| `save_notes_enc_json(base_dir, data, *, is_sandbox_mode=False)` | `notes_file_path(base_dir)` | `allow_write_to_core` |
| `save_presence_cfg_json(base_dir, data, *, is_sandbox_mode=False)` | `presence_cfg_path(base_dir)` | `allow_write_to_core` |
| `save_identity_json(base_dir, data, *, is_sandbox_mode=False)` | `identity_file_path(base_dir)` | `allow_write_to_core` |
| `save_keystore_json(base_dir, data, *, is_sandbox_mode=False)` | `keystore_file_path(base_dir)` | `allow_write_to_core` |
| `save_task_store_json(tasks_dir, data, *, sandbox_mode, live_base_dir=None)` | `tasks_dir / "tasks.json"` | `allow_write_to_core` when `sandbox_mode` |
| `ensure_trash_dir(base_dir, *, is_sandbox_mode=False)` | `trash_path(writing_base_dir(...))` | `allow_write_to_core` |
| `move_to_trash(base_dir, source_path, *, is_sandbox_mode=False)` | `trash_path(writing_base_dir(...))` | `is_allowed_trash_path` + `allow_write_to_core` |

### 1.4 Guards and checks

| Function | Purpose |
|----------|---------|
| `may_perform_permanent_delete(user_initiated: bool) -> bool` | Policy: permanent delete only when user-initiated. |
| `is_allowed_trash_path(base_dir, path) -> bool` | True iff path is the contract trash path. |
| `is_core_state_path(base_dir, candidate_path) -> bool` | True iff path is under base and is core state (for sandbox guard). |
| `allow_write_to_core(live_base_dir, target_path, is_sandbox_mode) -> bool` | False when sandbox and target is core under live base. |

### 1.5 Exception

| Symbol | Purpose |
|--------|--------|
| `CoreWriteForbidden` | Raised when a write sink would write to live core path in sandbox mode. |

---

## 2. Risky Usages Outside the Contract

### 2.1 Ad-hoc path construction (no contract helper used)

| Location | Current usage | Risk |
|----------|----------------|------|
| **main.py** ~938–942 | `(base_path / "tasks").mkdir(...)`, `(base_path / "logs").mkdir(...)`, `(base_path / "config").mkdir(...)` | Core directories created with literal `"tasks"`, `"logs"`, `"config"`. If contract ever adds `tasks_dir_path`/`logs_dir_path`/`config_dir_path`, these would be out of sync; sandbox/guard semantics not applied to directory creation. |
| **task_engine/engine.py** | `TaskStore`: `self._file = self.base_dir / "tasks.json"`. `_read_notes_or_tasks_verified`: `tasks_file = base_dir / "tasks.json"`. | Tasks path built manually; no `tasks_dir_path` or `task_store_file_path` in contract. Main passes `base_path / "tasks"` as TaskStore base_dir, so effective file is `.lumos/tasks/tasks.json` — consistent with `CORE_STATE_PATH_NAMES` and `is_core_state_path` (tasks/tasks.json) but not via a named helper. |
| **core/state.py** ~82 | `lp = log_path if log_path is not None else Path.cwd() / ".lumos" / "logs" / "log.txt"` | Log path built manually instead of `logs_file_path(Path.cwd() / ".lumos")`. Base (`.lumos`) is also hardcoded. |
| **security/presence_lock.py** ~25 | `base_dir = Path.cwd() / ".lumos"` when `base_dir is None` | Default base is hardcoded; not using a single “workspace base” helper. |
| **security/identity.py** | `IdentityPaths.identity_file` = `self.base_dir / "identity.json"` | Duplicates contract; should use `identity_file_path(self.paths.base_dir)` for consistency and single source of truth. |
| **security/keystore.py** | `KeyStorePaths.keystore_file` = `self.base_dir / "keystore.json"` | Same: duplicates contract; should use `keystore_file_path(self.paths.base_dir)`. |
| **core/config.py** ~99 | `legacy = base / "presence.json"` in `load_presence_from_config` | Should use `presence_cfg_path(base)` for consistency. |

### 2.2 Inconsistent default base_dir / base discovery

| Location | Default or discovery | Issue |
|----------|----------------------|--------|
| **main.py** | `_lumos_dir()` returns `".lumos"` (CWD-relative); doc says old `src/.lumos` not supported. | Canonical base is `.lumos`. |
| **security/identity.py** | `base_dir: str = "src/.lumos"` | Legacy default; diverges from main’s canonical `.lumos`. |
| **memory/secure_store.py** | `base_dir: str = "src/.lumos"` | Same. |
| **engine/online_engine.py** | `Path("src/.lumos").exists()` then `Path(".lumos").exists()`; returns `"src/.lumos"` or `".lumos"` | Ad-hoc discovery; not using a single contract or main-provided base. |
| **scripts/init_keystore.py**, **init_identity.py** | `base_dir="src/.lumos"` | Scripts; may be intentional for dev; document as legacy/dev-only. |

### 2.3 Writes that bypass the contract

| Location | Behavior | Risk |
|----------|----------|------|
| **security.bak_lock/identity.py** | `self.paths.identity_file.write_text(...)` | Direct write; no sandbox guard; legacy/backup code. |
| **security.bak_lock/keystore.py** | `self.paths.keystore_file.write_text(...)` | Same. |
| **main.py** ~938–942 | `base_path.mkdir(...)`, `(base_path / "tasks").mkdir(...)`, etc. | Directory creation not going through contract helpers that apply `allow_write_to_core` (no `ensure_logs_dir` / `ensure_tasks_dir` / `ensure_config_dir` in contract). So in sandbox mode, main could still create live core dirs if called before any guarded sink. |

### 2.4 Out-of-scope / different contract

| Location | Usage | Note |
|----------|--------|------|
| **device/contacts.py** | `path: str = "config/contacts.json"` (CWD-relative) | Not under `.lumos`; app-level config. If ever merged with Lumos base, should use contract path under base (e.g. config dir). |

### 2.5 Naming inconsistency in contract

| Item | Detail |
|------|--------|
| **Parameter name** | Sinks use `is_sandbox_mode`; `save_task_store_json` uses `sandbox_mode`. Same meaning, different name — can confuse and cause bugs when threading through. |

---

## 3. Recommended Freeze Rules

1. **Path names:** Do not add new top-level core state path names (e.g. new files or dirs under base) without adding a corresponding path helper and, if it is writable, a write sink in `workspace_contract.py`, and updating `CORE_STATE_PATH_NAMES` if it is core state.
2. **Trash / sandbox:** Do not introduce new trash or sandbox directory names; only `LUMOS_TRASH_DIRNAME` and `LUMOS_SANDBOX_DIRNAME`.
3. **Core state writes:** All persistent writes to paths that are considered core state (under base and listed in `CORE_STATE_PATH_NAMES` or covered by `is_core_state_path`) must go through a contract write sink that calls `allow_write_to_core` when `is_sandbox_mode` (or `sandbox_mode`) is True.
4. **New callers:** New code that needs a path under the Lumos workspace must use the contract path helpers (or a helper that itself uses them), not ad-hoc `base / "tasks"`, `base / "logs"`, etc.
5. **Permanent delete:** Any permanent delete must respect `may_perform_permanent_delete(user_initiated)` and must not be performed automatically without explicit user action.
6. **API stability:** The list in §1 is the stable public API. Do not remove or change signatures of path helpers or write sinks in a breaking way; add new helpers/sinks or optional parameters instead.

---

## 4. Minimal Safe Improvements for Stabilization Phase

These are minimal, non-breaking improvements that reduce risk and align the repo with the contract. They are suitable for a stabilization phase without changing runtime behavior beyond making it more consistent and guard-compliant.

### 4.1 Contract additions (optional but recommended)

- **`tasks_dir_path(base_dir: Path | str) -> Path`**  
  Return `Path(base_dir) / "tasks"`. Single source for the tasks directory; main and TaskStore can use it so that the path name `"tasks"` exists in one place.
- **Align parameter name in `save_task_store_json`:**  
  Add a deprecation period or alias: accept both `sandbox_mode` and `is_sandbox_mode` (one delegates to the other) so that callers can migrate to `is_sandbox_mode` and the contract can eventually standardize on `is_sandbox_mode` for all sinks.

### 4.2 Call-site improvements (use existing contract only)

- **core/state.py:** Use `logs_file_path(Path.cwd() / ".lumos")` (or the same base_dir passed from main) instead of `Path.cwd() / ".lumos" / "logs" / "log.txt"`.
- **core/config.py:** In `load_presence_from_config`, use `presence_cfg_path(base)` instead of `base / "presence.json"`.
- **security/identity.py:** Use `identity_file_path(self.paths.base_dir)` for the identity file path (read and any internal reference) instead of `self.base_dir / "identity.json"`.
- **security/keystore.py:** Use `keystore_file_path(self.paths.base_dir)` for the keystore file path instead of `self.base_dir / "keystore.json"`.

These keep behavior the same (same resulting path) but tie reads to the contract.

### 4.3 Bootstrap in main (optional; needs contract extension)

- If contract adds `ensure_logs_dir(base_dir, *, is_sandbox_mode=False)` and `ensure_tasks_dir(...)` / `ensure_config_dir(...)` (each using the corresponding path helper and `allow_write_to_core`), then main’s bootstrap could call these instead of raw `(base_path / "logs").mkdir(...)` etc. That would ensure directory creation also respects sandbox. This is a small behavioral refinement in sandbox mode (currently main creates live core dirs at startup even in sandbox if it runs that block).

### 4.4 Documentation and tests

- **Document** in the contract module (or in this audit) that the canonical workspace base is `.lumos` (CWD-relative) and that `src/.lumos` is legacy/dev-only; scripts and any remaining `src/.lumos` defaults should be explicitly marked as such.
- **Add a simple test** (or extend existing tests) that all core-state writes that the test suite triggers go through the contract sinks (e.g. no direct `write_text` on paths that `is_core_state_path` returns True for, except inside `workspace_contract.py` itself).

### 4.5 Do not change in stabilization (leave for later)

- **security.bak_lock:** Legacy code; leave as-is unless removing.
- **engine/online_engine.py base discovery:** Behavioral change if switched to a single base; do in a dedicated change.
- **Default base_dir in identity/secure_store:** Changing defaults from `src/.lumos` to `.lumos` can change where scripts write; do with explicit migration/announcement.

---

## Summary Table

| Category | Count | Action |
|----------|-------|--------|
| Stable public API (path helpers + sinks + guards + exception) | §1 | Freeze; document as contract. |
| Risky ad-hoc path construction | 7+ call sites | Prefer contract helpers; add `tasks_dir_path` if desired. |
| Writes outside contract | main bootstrap dirs; bak_lock | Optional: add ensure_*_dir; leave bak_lock. |
| Naming inconsistency | `sandbox_mode` vs `is_sandbox_mode` | Align in contract over time. |
| Freeze rules | 6 | Adopt so all core paths and writes flow through workspace_contract. |

This audit does not modify any runtime code; it only records the stable API, risky usages, freeze rules, and minimal safe improvements for a later stabilization phase.
