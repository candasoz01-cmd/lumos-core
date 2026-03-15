# Cleanup plan: backup files and .lumos workspace

**Status:** Plan only. No deletions or moves have been performed.

---

## 1. Backup file cleanup plan

### 1.1 Scope

All backup and duplicate files under `src/` that appear to be historical snapshots from refactors (main.py split, lock/presence, runtime extraction). No production code or tests import any of these files (verified by grep).

### 1.2 Inventory

#### A. main.py–related backups (src/)

| File | Likely origin |
|------|----------------|
| `src/main.py.bak` | Early backup |
| `src/main.py.bak2` | Second snapshot |
| `src/main.py.bak_gate` | Gate-related refactor |
| `src/main.py.bak_lock` | Lock flow refactor |
| `src/main.py.bak_lock_cli` | Lock CLI refactor |
| `src/main.py.bak_lock_console` | Lock console variant |
| `src/main.py.bak_lockfix` | Lock fix snapshot |
| `src/main.py.bak_memhook` | Memory hook experiment |
| `src/main.py.bak_online_fix` | Online mode fix |
| `src/main.py.refactor_bak` | Refactor snapshot |
| `src/main.py.broken_backup` | Broken state backup |
| `src/main.py.broken.20260220_222834` | Dated broken backup |

#### B. Other module backups (src/)

| File / dir | Parent module |
|------------|----------------|
| `src/core/lumos.py.bak_unlock` | core.lumos |
| `src/policy/offline_engine.py.bak` | policy |
| `src/policy/offline_engine.py.bak_lock_cli` | policy |
| `src/policy/offline_engine.py.bak_fallback_cli` | policy |
| `src/policy/offline_engine.py.bak_unlock` | policy |
| `src/policy/rules.py.bak` | policy |
| `src/policy/rules.py.bak_gate` | policy |
| `src/context/context.py.bak` | context (live module) |
| `src/context/context.py.bak_gate` | context |
| `src/context/context.py.bak_unlock` | context |
| `src/memory/memory.py.bak` | memory |
| `src/memory/memory.py.bak2` | memory |
| `src/memory/secure_store.py.bak2` | memory |
| `src/memory/schema.py.bak` | memory |
| `src/security/keystore.py.bak2` | security |
| `src/security.bak_lock/` | entire directory (identity, keystore, crypto, permissions) |
| `src/engine/model_client.py.bak_full` | engine |
| `src/scripts/init_keystore.py.bak_fix` | scripts |

### 1.3 Grouping

#### Safe to archive (recommended first step)

Move to a single archive location so they leave `src/` but remain recoverable. Prefer **archive over delete** until the team confirms they are no longer needed.

- **Location suggestion:** `archive/backups_pre_stabilization/` at repo root (or `docs/archive/backups_pre_stabilization/` if you want archives under docs). Keep the same relative paths under that dir (e.g. `archive/.../src/main.py.bak`, `archive/.../src/security.bak_lock/...`) so paths are obvious.
- **Contents:** All files listed in §1.2 (all main.py.* backups, all .bak / .bak_* / .refactor_bak / .broken* under src/, and the whole `src/security.bak_lock/` directory).
- **Verification before archive:** Run full test suite and CI; confirm no test or script references any of these files (already verified: no imports found).

#### Safe to delete (only after approval)

Same set as “safe to archive.” Safe to delete in the sense that:

- No code or test imports them.
- They are almost certainly in git history if needed for rollback.

Delete only after the team agrees that archiving is unnecessary or after archives have been kept for a while and are no longer needed.

#### Keep temporarily (do not archive/delete yet)

- **None** of the backup files need to be “kept temporarily” in `src/` for correctness; they are not referenced.
- **Optional:** If `security.bak_lock` is considered a candidate for a future merge or comparison, keep that directory (or a copy) in a separate branch or archive and remove it from `src/` to reduce noise. Document the decision.

### 1.4 Recommended sequence

1. **Create archive directory** (e.g. `archive/backups_pre_stabilization/`).
2. **Move** all files from §1.2 into the archive, preserving relative paths under `src/` (and `security.bak_lock` as a subtree).
3. **Commit** as a single “chore: archive backup and duplicate files under src/” (or similar).
4. **Run CI** and full tests to confirm nothing breaks (no references expected).
5. **Later:** If the team decides backups are no longer needed, delete the archive in a separate commit; or leave the archive in place for a defined period.

### 1.5 What not to touch

- **Live modules:** `main.py`, `core/lumos_runtime.py`, `core/lumos.py`, `context/context.py`, `security/*.py` (non-backup), `memory/*.py` (non-backup), `policy/*.py` (non-backup), etc.
- **Tests and scripts** that import from `main` or other live modules.
- **`lumos_core/__main__.py`** and any entrypoints that delegate to `main`.

---

## 2. .lumos purpose summary

### 2.1 What .lumos is

**.lumos** is the **single working root (çalışma kökü)** for a Lumos instance. It is the canonical directory for runtime state, persistent memory, logs, config, and trash. It lives under the process CWD (e.g. `./.lumos`). The repo does not ship `.lumos`; it is ignored by git (`.gitignore` contains `.lumos/`).

### 2.2 What it contains (by contract)

| Path under .lumos | Type | Purpose |
|-------------------|------|--------|
| `tasks/` | dir | Task engine working directory |
| `tasks/tasks.json` | file | Task store (core state) |
| `logs/` | dir | Log directory |
| `logs/log.txt` | file | Append-only event log (core state) |
| `trash/` | dir | Single trash directory (core) |
| `config/` | dir | Config directory (core) |
| `config.json` | file | Main config (core state) |
| `aliases.json` | file | Command aliases (core state) |
| `notes.enc.json` | file | Encrypted notes – memory store (core state) |
| `presence.json` | file | Presence-lock config (core state) |
| `identity.json` | file | Device identity (core state, security) |
| `keystore.json` | file | Keystore (core state, security) |
| `consent.json` | file | Optional consent flag (not in CORE_STATE_PATH_NAMES) |
| `sandbox/` | dir | Only when sandbox_mode; sandbox write target |

Definitions of “core” paths and sinks live in `core/workspace_contract.py` (e.g. `CORE_STATE_PATH_NAMES`, `is_core_state_path`, path helpers, `allow_write_to_core`).

### 2.3 Runtime state, logs, config, memory, or mixed?

**.lumos is mixed.** It holds:

- **Runtime state:** tasks, presence config, permission/session-related data.
- **Logs:** append-only event log under `logs/log.txt`.
- **Config:** `config.json`, `config/`, presence.json.
- **Memory store:** encrypted notes in `notes.enc.json`; keys/identity in `keystore.json` and `identity.json`.
- **Trash:** single trash location for moved/deleted items.

So it is not “only” runtime state, logs, config, or memory—it is the single workspace that contains all of these by design.

### 2.4 Part of the core runtime contract?

**Yes.** The workspace contract defines:

- The **only** supported workspace root (CWD-based `.lumos`).
- **Single trash** (`trash_path`); no other trash/deleted dirs.
- **Core state paths** via `CORE_STATE_PATH_NAMES` and `is_core_state_path`.
- **Central sinks** for all writes (logs, aliases, config, notes, presence, identity, keystore, tasks, trash) and the rule that in sandbox mode nothing writes to live core paths under `.lumos` (`allow_write_to_core`).

So `.lumos` layout and core paths are part of the core runtime contract; changing them without updating the contract and all readers/writers would break the product.

---

## 3. Risks if cleanup is done incorrectly

### 3.1 Backup / archive cleanup

- **Deleting a file that is still referenced:** Already checked; no code or test imports any of the backup files. Risk of breakage from deleting the listed backups is low.
- **Moving without updating imports:** No imports point at these backups; move/archive does not require code changes. Risk is low.
- **Losing history:** If backups are deleted and not archived, recovery depends on git history. Archiving first avoids that risk.

### 3.2 .lumos cleanup (if someone “cleans” the workspace by hand)

- **Renaming or moving .lumos:** All code assumes one root (e.g. `_lumos_dir()` → `.lumos`). Changing it without a single shared source (e.g. env or shared helper) breaks CLI/runtime and any other entrypoint that uses the same root.
- **Adding another trash (e.g. deleted/, trash2/):** Violates the “single trash” rule and can confuse guards and any logic that assumes one trash path.
- **Changing core file names or layout:** Paths are hard-coded in `workspace_contract` and callers. Renaming or moving files without updating the contract and all readers/writers breaks load/save and can corrupt or lose state.
- **Writing to core paths outside the defined sinks:** Bypasses `allow_write_to_core`; in sandbox mode can overwrite live core state; can desync or corrupt state.
- **Deleting or editing core files by hand:**  
  - `keystore.json` / `identity.json`: can make unlock impossible or break device identity.  
  - `notes.enc.json`: loss of encrypted notes.  
  - `tasks/tasks.json`: loss of task state.  
  - `aliases.json`, `config.json`, `presence.json`: loss of preferences and presence config.  
  - `logs/log.txt`: loss of audit trail and any logic that depends on it.
- **Using a different workspace root (e.g. src/.lumos) as the main workspace:** Docs say the old `src/.lumos` layout is not supported; runtime uses CWD `.lumos`. Mixing roots can split or duplicate state (e.g. CLI vs web/online_engine) and cause inconsistent behavior.

**Summary:** Backup cleanup is low risk if limited to the listed files and the recommended archive-then-optional-delete flow. .lumos must not be “cleaned” in an ad-hoc way; any change to layout or core paths must go through the workspace contract and be reflected in code and docs.
