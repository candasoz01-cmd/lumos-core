# Stabilization Execution Plan

**Source documents:** STABILIZATION_MAIN_SPLIT_PLAN.md, WORKSPACE_CONTRACT_STABILITY_AUDIT.md, PERSISTENT_WRITE_PATH_AUDIT.md, WEB_STABILIZATION_AUDIT.md, PANEL_READONLY_AUDIT.md, STARTUP_HEALTH_AUDIT.md.

**Purpose:** Single ordered plan for stabilization: safest tasks first, clear split between analysis-only and code-change, and strict no-touch areas.

**Constraint:** This plan does not modify code; it only defines the execution order and rules.

---

## 1. Top 7 Stabilization Tasks (Safest Order)

| # | Task | Source doc(s) | Risk |
|---|------|----------------|------|
| **1** | **Documentation and boundary rules** — Document bak_lock as non-contract; directory-creation gap; web read-only and path rules; panel fallback/--write and read-only guarantee; startup_health boundary rules (no workspace_contract/security/presence_lock import); canonical base `.lumos` and legacy `src/.lumos`. Add or update README/architecture references and, if desired, a short STABILIZATION_RULES.md that references the six audits. | PERSISTENT_WRITE_PATH_AUDIT (P1); WEB_STABILIZATION_AUDIT (§3–4.3); PANEL_READONLY_AUDIT (P3); STARTUP_HEALTH_AUDIT (§5); WORKSPACE_CONTRACT_STABILITY_AUDIT (§4.4) | None (doc only) |
| **2** | **Web: fix log path** — In `web/app.py` `_read_status_snapshot()`, replace `logp = base / "log.txt"` with `logp = logs_file_path(base)` (import `logs_file_path` from `core.workspace_contract`). Ensures /status uses the same log file as CLI and contract. | WEB_STABILIZATION_AUDIT (§4.1) | Low |
| **3** | **Panel: fix tasks path** — In `panel/scripts/read_backend_state.py`, change tasks file from `base / "tasks.json"` to `base / "tasks" / "tasks.json"` in `_read_tasks_payload`, `_task_engine_health`, and `system_paths["tasks"]`. Aligns with main.py and TaskStore layout. | PANEL_READONLY_AUDIT (P1) | Low |
| **4** | **Panel: use contract path helpers** — In `read_backend_state.py`, use `trash_path(base)` for trash directory and `logs_file_path(base)` for the log file (replace ad-hoc `base / "trash"` and `base / "logs" / "log.txt"`). Keeps script aligned with workspace_contract. | PANEL_READONLY_AUDIT (P2); WORKSPACE_CONTRACT_STABILITY_AUDIT (§4.2) | Low |
| **5** | **Contract read-path alignment** — Use contract path helpers for **reads** only (no write flow change): `core/state.py` use `logs_file_path(...)` for default log path; `core/config.py` use `presence_cfg_path(base)` in `load_presence_from_config`; `security/identity.py` use `identity_file_path(self.paths.base_dir)` for identity file; `security/keystore.py` use `keystore_file_path(self.paths.base_dir)` for keystore file. Same resulting paths; single source of truth. | WORKSPACE_CONTRACT_STABILITY_AUDIT (§4.2) | Low |
| **6** | **Workspace_contract: add tasks_dir_path (optional)** — Add `tasks_dir_path(base_dir: Path | str) -> Path` returning `Path(base_dir) / "tasks"`. Use it in main.py bootstrap for `(base_path / "tasks").mkdir(...)` and in panel script for tasks file path (so panel uses `tasks_dir_path(base) / "tasks.json"`). Optionally document canonical base and legacy `src/.lumos` in the contract module or audit. | WORKSPACE_CONTRACT_STABILITY_AUDIT (§4.1); STABILIZATION_MAIN_SPLIT_PLAN (state in main); PANEL_READONLY_AUDIT (P2) | Low |
| **7** | **main.py extraction Phase 1–2** — Extract **help constants** to `cli/help_.py` (or keep in parse); then extract **parser + fallback** to `cli/parse.py` (normalize_command, get_fallback_message, _fold_for_search, fallback/help constants). Main imports from cli and re-exports `normalize_command` from main for backward compatibility if desired. Run tests and CLI smoke after each phase. | STABILIZATION_MAIN_SPLIT_PLAN (§2 phases 1–2) | Medium |

Tasks 1–6 are independent and can be done in order; task 7 should follow after 1–6 so that path and contract alignment are in place before refactoring main.

---

## 2. Analysis-Only vs Code-Change Tasks

| Task | Type | Description |
|------|------|--------------|
| **1. Documentation and boundary rules** | **Analysis + documentation only** | No runtime code change. Add or update docs (README, STABILIZATION_RULES.md, audit references) so that: bak_lock is marked non-contract; directory-creation gap is documented; web read-only and path rules are stated; panel fallback and --write are documented; startup_health boundary rules are stated; canonical base `.lumos` and legacy `src/.lumos` are documented. |
| **2. Web log path** | **Code change** | One file: `web/app.py`. Replace ad-hoc log path with `logs_file_path(base)`. |
| **3. Panel tasks path** | **Code change** | One file: `panel/scripts/read_backend_state.py`. Change tasks path to `base / "tasks" / "tasks.json"`. |
| **4. Panel contract path helpers** | **Code change** | One file: `panel/scripts/read_backend_state.py`. Use `trash_path(base)` and `logs_file_path(base)`. |
| **5. Contract read-path alignment** | **Code change** | Four files: `core/state.py`, `core/config.py`, `security/identity.py`, `security/keystore.py`. Use contract path helpers for read paths only. |
| **6. tasks_dir_path and usage** | **Code change** | Add helper in `core/workspace_contract.py`; use in `main.py` and `panel/scripts/read_backend_state.py`. Optional doc in contract or audit. |
| **7. main.py extraction Phase 1–2** | **Code change** | New `cli/` package; move help constants and parser+fallback; update main.py imports and loop to use cli; update tests if import paths change. |

**Summary:** One task is analysis/documentation only (task 1). Tasks 2–7 are code changes; 2–6 are low-risk, single- or few-file changes; task 7 is a multi-file refactor with medium risk.

---

## 3. Low-Risk Changes (Do First)

The following are **low-risk** and should be done before any larger refactor (e.g. main.py extraction):

- **Task 1 (doc only):** No runtime impact; reduces ambiguity and enforces boundaries by documentation.
- **Task 2 (web log path):** Single file; same logical path (logs dir + log.txt), only source of path changes to contract; no new write; existing presence_lock import already pulls workspace_contract.
- **Task 3 (panel tasks path):** Single file; fixes correctness when tasks exist under `.lumos/tasks/`; no write; no change to panel JS or contract shape.
- **Task 4 (panel contract helpers):** Single file; same paths, only source of path changes to contract; no write.
- **Task 5 (contract read-path alignment):** Four files; read-only call-site changes; same resulting paths; no change to write flows.
- **Task 6 (tasks_dir_path):** Add one helper and use it in two places; no change to write semantics; optional.

**Order:** Execute 1 → 2 → 3 → 4 → 5 → 6, then run the full regression checklist. Only then proceed to task 7 (main.py extraction).

---

## 4. Areas That Must Not Be Touched

The following must **not** be changed during stabilization without an explicit decision and design:

| Area | Rule | Source |
|------|------|--------|
| **security.bak_lock** | Do not use in production; do not add workspace_contract or sandbox guard there in stabilization. Document as legacy/non-contract only. | PERSISTENT_WRITE_PATH_AUDIT (P1); WORKSPACE_CONTRACT_STABILITY_AUDIT (§4.5) |
| **Core security and authorization** | No relaxation of SECURITY_NEVER_AUTO, profiles (rapor, guvenli_yurut, kisitli_otonom), consent, lock, keystore, or identity rules. No automatic permanent delete; no automatic write to core state without guard. | lumos-karar-sozlesmesi; task_engine/profiles; workspace_contract |
| **startup_health imports** | Do not add imports from `core.workspace_contract`, `security`, or `security.presence_lock`. Keep presence and lock as injected parameters only. | STARTUP_HEALTH_AUDIT (§5) |
| **Web** | No `import main` or CLI; no write flows (no append_log_line, save_*, ensure_trash_dir, move_to_trash, etc.). /health and /status stay minimal and read-only. | WEB_STABILIZATION_AUDIT (§3) |
| **Panel** | No write endpoints or actions from the UI; no fetch/POST to a backend that writes to .lumos or runs CLI. Script remains read-only for core state; only --write to state_inject.js is allowed. | PANEL_READONLY_AUDIT (§3, P5) |
| **workspace_contract stable API** | Do not remove or break signatures of path helpers or write sinks. Do not add new core state path names without a path helper and, if writable, a write sink and guard. Do not introduce new trash/sandbox dir names. | WORKSPACE_CONTRACT_STABILITY_AUDIT (§3) |
| **main.py state and callbacks** | When extracting to cli/*: do not move `do_lock`, `device_lock_cli`, `unlock_with_passphrase` into cli; they stay in main. Shared mutable state (saved_notes, last_route, today_actions, etc.) remains owned by main and is only passed into handlers. | STABILIZATION_MAIN_SPLIT_PLAN (§1.2, §4) |

---

## 5. Regression Test Checklist

After **each** code-change task (2–7), run the following. All must pass before considering the task done and before moving to the next task.

### 5.1 Automated tests

- [ ] **pytest**  
  `pytest tests/` (or equivalent) from repo root. No new failures.
- [ ] **test_cli_parse**  
  If parser or help moved to cli: `from main import normalize_command` or `from cli.parse import normalize_command` still works as expected; tests that use normalize_command, get_fallback_message pass.
- [ ] **test_workspace_contract**  
  All existing contract tests pass (paths, guards, sinks, sandbox).
- [ ] **test_sandbox_mode_source**  
  If touched: `from main import _sandbox_mode_from_env` (or unchanged import) and sandbox behavior unchanged.
- [ ] **Other project tests**  
  Any task_engine, presence, identity, keystore, or core tests: no regressions.

### 5.2 CLI smoke (manual or scripted)

Run the interactive CLI (e.g. `python -m lumos_core` or `python src/main.py`) and verify:

- [ ] **durum** — Prints status block; consent/lock/presence and not_line look correct.
- [ ] **hazır** — Prints startup summary.
- [ ] **yardım** / **help** — Full help text; **yardım temel**, **yardım notlar**, **yardım etiketler** show expected blocks.
- [ ] **kilit** — Enters lock menu; **durum**, **cik** work.
- [ ] **kamera** — Enters presence menu; **durum**, **cik** work (skip ac/kapat if no camera).
- [ ] **görevler** — Lists tasks or “Kayıtlı görev yok.”
- [ ] **görev durumu \<id>** / **görev özeti \<id>** — If a task exists, show detail.
- [ ] **notları göster** / **bunu hatırla \<metin>** — Notes flow works or shows empty.
- [ ] **alias liste** — Shows aliases or “(alias yok).”
- [ ] **self test** — Completes and reports passed/failed areas.
- [ ] **exit** / **cik** — Exits cleanly.

### 5.3 Web

- [ ] **GET /health** — Returns `{"ok": true, "version": "..."}`.
- [ ] **GET /status** — Returns JSON with lock_status, presence_enabled, presence_running, mode, last_log_ts. After task 2, last_log_ts should reflect logs from `.lumos/logs/log.txt` when present.

### 5.4 Panel

- [ ] **Without --write** — Open panel (e.g. index.html); fixture or default state_inject.js loads; all screens render without JS errors.
- [ ] **Kartlı sonuç (`#yanit`)** — Follow **`docs/panel-manuel-test.md`**: from `panel/` run `python3 -m http.server 8080`, open **http://127.0.0.1:8080/#yanit**; verify lead summary card, stacked peek cards, click-to-expand, three action buttons.
- [ ] **With --write** — Run `panel/scripts/read_backend_state.py --write` from repo root (with LUMOS_BASE_DIR pointing to a test .lumos if needed); reload panel; Dashboard, System, Tasks, Trash, Logs show backend-derived data where applicable. After tasks 3–4, tasks list and trash/logs paths should match real layout.

### 5.5 Sandbox mode (if applicable)

- [ ] **LUMOS_SANDBOX=1** — Run CLI or script; writes go to sandbox base; no write to live .lumos core paths (verify with test or manual check). Contract guard tests already cover this; ensure no regression.

### 5.6 Sign-off

- [ ] **CI** — If the project has CI, ensure the branch passes (lint, tests, any build steps). Per workspace rules: “CI yeşil değilse tamamlandı deme.”

---

## Summary

| Item | Content |
|------|--------|
| **Top 7 tasks (order)** | 1) Doc & boundary rules (analysis only) → 2) Web log path → 3) Panel tasks path → 4) Panel contract helpers → 5) Contract read-path alignment → 6) tasks_dir_path (optional) → 7) main.py extraction Phase 1–2. |
| **Analysis-only** | Task 1 only. |
| **Code-change** | Tasks 2–7; 2–6 low-risk, 7 medium-risk. |
| **Low-risk first** | 1–6 before 7; run full regression after 6. |
| **Do not touch** | bak_lock production use; core security/authorization; startup_health new domain imports; web main/write; panel write flows; contract stable API break; main-owned callbacks and state. |
| **Regression** | pytest, test_cli_parse, test_workspace_contract, CLI smoke (durum, hazır, yardım, kilit, kamera, görevler, notlar, alias, self test, exit), web /health and /status, panel with and without --write, sandbox guard, CI. |

This plan does not modify any code; it only defines the execution order, task types, boundaries, and regression checklist for the stabilization phase.
