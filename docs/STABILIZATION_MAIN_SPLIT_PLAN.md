# Stabilization Plan: Reduce main.py Surface Area

**Goal:** Reduce `src/main.py` surface area without changing behavior, using a thin-router structure and extracting lock, presence, tasks, notes, and status flows into separate CLI modules.

**Constraint:** Current behavior must remain exactly the same. No refactor of logic; only relocation and wiring.

---

## 1. Proposed Target File / Module Structure

### 1.1 Current state

- **`src/main.py`** (~1370 lines): entry point, parser, all help constants, fallback logic, lock/presence menus (nested), alias menu, self-test, startup self-check, and the entire CLI loop with inline handling for every route.

### 1.2 Target structure

```
src/
  main.py                    # Thin router: setup, single loop, dispatch by route
  cli/
    __init__.py              # Re-exports for tests / external use if needed
    parse.py                 # normalize_command, handle_command, get_fallback_message,
                             # _fold_for_search, fallback/help constants, EXIT_SYNONYMS
    help_.py                 # HELP_* and REHBER constants only (optional; can stay in parse.py)
    lock.py                  # lock_menu, do_lock/device_lock_cli wiring (menu only; wiring stays in main)
    presence.py              # presence_menu
    status.py                # Status/durum handlers + helpers (_get_oneri, _get_tek_sonraki_adim,
                             # _get_guvenli_cevap, _get_en_onemli_eksik, _get_mod_cevabi,
                             # _format_neden_cevap, _shorten_previous_response, _note_for_hatirla)
    notes.py                 # All note/etiket route handlers + _record_note_op, note constants
    tasks.py                 # All görev + yetki + genel onay route handlers
    alias_.py                # alias_menu (optional; small, can stay in main)
```

**Thin-router contract:**

- **`main.py`** after extraction:
  - Imports: `core.*`, `engine.*`, `security.*`, `task_engine.*`, `memory.*`, and `cli.parse`, `cli.lock`, `cli.presence`, `cli.status`, `cli.notes`, `cli.tasks`, and optionally `cli.alias_` (or keep alias in main).
  - Owns: `main()`, bootstrap (base_dir, aliases, engines, lumos, keystore, state, CoreEngine, recovery), definition of `do_lock`, `device_lock_cli`, `unlock_with_passphrase`, and the single **while True** loop.
  - In the loop: read input, handle CLI_NOT_BEKLEME / CLI_NOT_DUZENLEME, call `normalize_command` (from cli.parse), then **dispatch by route** to:
    - `cli.status.handle_*` for durum/hazir/onerir/sonraki_adim/guvenli_miyim/en_onemli_eksik/hangi_moddayim/neden_boyle/kisaca_anlat/ne_yapiyorsun/son_yaptigin_ne/bugun_ne_yaptin
    - `cli.lock.run_lock_menu()` for kilit
    - `cli.presence.run_presence_menu()` for kamera
    - `cli.notes.handle_*` for all note/etiket routes
    - `cli.tasks.handle_*` for all görev/yetki/genel onay routes
    - Help/rehber: either in main (print constant) or `cli.parse.get_help_text(route)` returning string.
  - **State that stays in main** (single source of truth): `pending`, `current_task`, `last_action`, `today_date`, `today_actions`, `last_response_reason`, `last_response_text`, `last_route`, `saved_notes`, `cli_mode`, `last_note_undo`, `note_ops_history`, `last_task_create_fingerprint`, `current_permission_profile`, `general_approval`, `task_store`. Handlers receive these as arguments or a small “CLI context” object so behavior is unchanged.

### 1.3 Optional variants

- **Help:** Keep all HELP_* and REHBER in `main.py` or move to `cli/help_.py` and have main (or parse) call a `get_help_text(route)` to avoid duplicating strings. Recommendation: move constants to `cli/help_.py` and have main/parse import and print.
- **Alias:** Keep `alias_menu` in main (small, ~30 lines) to minimize moving parts, or move to `cli/alias_.py` for symmetry.
- **Parser location:** Keep `normalize_command` in `main.py` and have tests import from main, or move to `cli/parse.py` and re-export from `main.py` for backward compatibility (`from main import normalize_command`). Recommendation: move to `cli/parse.py` and in main add `from cli.parse import normalize_command`; update tests to `from cli.parse import normalize_command` (or keep `from main import normalize_command` if main re-exports).

---

## 2. Extraction Order (Lowest Risk First)

Recommended order to minimize regressions and simplify review:

| Phase | Target module      | Risk | Rationale |
|-------|--------------------|------|-----------|
| 1     | Help constants     | Low  | Pure constants; no control flow. Move HELP_*, REHBER, UNKNOWN_CMD_TEXT, NEDEN_ANLAMADIN_TEXT, NEUTRAL_FALLBACK_TEXT, FALLBACK_BY_FAMILY, COMMAND_ANCHOR_WORDS, CASUAL_FIRST_WORDS to `cli/help_.py` (or keep in parse). |
| 2     | Parser + fallback  | Low  | normalize_command, get_fallback_message, _fold_for_search, _is_why_question, _first_token_folded, _has_anchor, _is_casual_or_indeterminate, _infer_family_from_raw, _route_to_family, and related constants. Well-covered by test_cli_parse. |
| 3     | Status helpers + dispatch | Medium | Status flow is read-only (get_durum_parts, format_durum, get_startup_summary) plus print. Move _get_oneri, _get_tek_sonraki_adim, _get_guvenli_cevap, _get_en_onemli_eksik, _get_mod_cevabi, _format_neden_cevap, _shorten_previous_response, _note_for_hatirla; then in main replace status route blocks with calls to status.handle_*(...) returning string or None; main still prints and updates last_* / today_*. |
| 4     | Lock menu         | Low  | Single nested function `lock_menu`. Extract to `cli/lock.py` as `run_lock_menu(state, engine, initial_cmd=None) -> str | None`. Main keeps do_lock/device_lock_cli/unlock; only the menu implementation moves. |
| 5     | Presence menu     | Medium | Large nested block with _run_cmd, atexit/inspect recovery block. Extract to `cli/presence.py` as `run_presence_menu(state, engine, base_dir, initial_cmd=None, sandbox_mode=False) -> str | None`. Dependencies: _input_or_eof, _parse_yes_no, logfmt, Path, pl. |
| 6     | Notes             | High  | Many routes and shared state (saved_notes, note_ops_history, last_note_undo, cli_mode). Extract handlers to `cli/notes.py`; each handler receives context (saved_notes, note_ops_history, last_note_undo, cli_mode, today_date, today_actions, last_*) and returns (output_string, side_effect_done) or a small result object; main applies side effects and prints. Alternatively: main keeps the loop and calls notes.handle_hatirla(...), notes.handle_notu_sil(...), etc., with context passed in. |
| 7     | Tasks             | Medium | All görev_*, yetki_profili, genel_onay_* handlers. Extract to `cli/tasks.py`; handlers take task_store, current_permission_profile, general_approval, base_dir, and mutable state (current_task, last_action, today_*). Main passes these and prints result. |
| 8     | Alias (optional)  | Low  | alias_menu to `cli/alias_.py` if desired. |

After each phase: run existing tests, run CLI smoke (durum, hazir, kilit, kamera, görevler, notlar, yardım), then proceed.

---

## 3. Exact Functions / Blocks That Should Move

### 3.1 Constants and helpers (by name)

- **To `cli/help_.py` (or `cli/parse.py`):**
  - `EXIT_SYNONYMS`
  - `HELP_TEXT`, `HELP_ETIKETLER_TEXT`, `HELP_NOTLAR_TEXT`, `HELP_NOT_ISLEMLERI_TEXT`, `HELP_TEMEL_TEXT`, `HELP_GUVENLIK_TEXT`, `HELP_KISA_TEXT`, `HELP_ARAMA_TEXT`, `HELP_GORUNTULEME_TEXT`
  - `REHBER_TEXT`
  - `UNKNOWN_CMD_TEXT`, `NEDEN_ANLAMADIN_TEXT`, `NEUTRAL_FALLBACK_TEXT`
  - `COMMAND_ANCHOR_WORDS`, `CASUAL_FIRST_WORDS`, `FALLBACK_BY_FAMILY`

- **To `cli/parse.py`):**
  - `norm_cmd` (if still used; else remove)
  - `_fold_for_search`
  - `_is_why_question`, `_first_token_folded`, `_has_anchor`, `_is_casual_or_indeterminate`, `_infer_family_from_raw`, `_route_to_family`
  - `get_fallback_message`
  - `GOREV_SECOND_TOKEN_TOLERANCE`, `YETKI_PROFIL_TOLERANCE`
  - `normalize_command`, `handle_command`

### 3.2 Status flow (to `cli/status.py`)

- **Functions to move:**
  - `_get_oneri` (lines ~206–234)
  - `_get_tek_sonraki_adim` (~236–249)
  - `_get_guvenli_cevap` (~251–269)
  - `_get_en_onemli_eksik` (~271–278)
  - `_get_mod_cevabi` (~281–292)
  - `_format_neden_cevap` (~274–279)
  - `_shorten_previous_response` (~291–314)
  - `_note_for_hatirla` (~352–364)
- **Constants:** `KISACA_ANLAT_SHORT_THRESHOLD`, `HATIRLA_NOTE_MAX_LEN`, `NOT_OZETLE_SHORT_THRESHOLD`, `NOT_ADLANDIR_MAX_TAG_LEN`
- **Route blocks in main loop to replace with calls:**  
  `onerir`, `sonraki_adim`, `guvenli_miyim`, `en_onemli_eksik`, `hangi_moddayim`, `neden_boyle`, `kisaca_anlat`, `ne_yapiyorsun`, `son_yaptigin_ne`, `bugun_ne_yaptin`, and the `durum` / `hazir` print logic (status module can return the string to print; main still sets `current_task[0]` and last_* / today_*).

### 3.3 Lock (to `cli/lock.py`)

- **Block to move:** The entire `lock_menu` function (lines ~796–837 in current main.py), including its inner `_run_cmd`.
- **Signature:** `run_lock_menu(*, state: CoreState, engine: CoreEngine, initial_cmd: str | None = None) -> str | None`.
- **Dependencies to inject or import:** `_input_or_eof` (can live in cli/io.py or parse.py), `getpass`, `state.lock_status`, `engine.do_lock`, `engine.unlock_with_passphrase`, `engine.device_lock_cli`. `_GLOBAL_CMDS` can be passed as argument or defined in lock.py.

### 3.4 Presence (to `cli/presence.py`)

- **Block to move:** The entire `presence_menu` function (lines ~679–793), including:
  - Inner `_run_cmd` (durum, ac, kapat, sure, cik and global cmd passthrough)
  - The trailing try/except block that registers atexit and calls `pl.start_presence_lock` for recovery
- **Signature:** `run_presence_menu(*, state: CoreState, engine: CoreEngine, base_dir: str, initial_cmd: str | None = None, sandbox_mode: bool = False) -> str | None`.
- **Dependencies:** `_input_or_eof`, `_parse_yes_no`, `logfmt`, `Path`, `pl` (presence_lock module), `state.log_event`, `state.is_locked`, `sandbox_mode`.

### 3.5 Notes (to `cli/notes.py`)

- **Helpers to move:** `_record_note_op`, `_record_today_action` (if only used by notes; else keep in main or status).
- **Route blocks to move (as functions that take context and return string + optional state updates):**  
  `hatirla`, `son_not_ne`, `notu_kopyala`, `notu_disa_aktar`, `notu_paylas`, `not_ozetle`, `notlari_goster`, `etiketli_notlari_goster`, `etikete_gore_notlari_goster`, `etiketleri_goster`, `etiket_ara`, `not_gecmisi`, `notlari_temizle`, `notu_sil`, `notu_duzenle`, `notu_adlandir`, `etiket_kaldir`, `etiket_degistir`, `not_birlestir`, `notu_geri_al`, `kac_not_var`, `not_ara`, `etiketli_not_ara`.
- **Design:** Either (a) one function per route, e.g. `handle_hatirla(args, context) -> NotesResult`, and main applies context updates and prints, or (b) handlers receive mutable context and return only the string to print. Option (b) keeps main simpler and avoids defining a large NotesResult type.

### 3.6 Tasks (to `cli/tasks.py`)

- **Route blocks to move:**  
  `yetki_profili`, `genel_onay_ac`, `genel_onay_kapat`, `gorev_olustur`, `gorevler`, `gorev_durumu`, `gorev_adimlari`, `gorev_ozeti`, `gorev_iptal`, `gorev_temizle_tamamlananlar`, `gorev_temizle_simulasyonlar`, `gorev_arsivle`, `gorev_sil`, `gorev_sayac`.
- **Dependencies:** `TaskStore`, `TaskEngine`, `compute_task_stats`, `format_task_stats_line`, `find_recent_similar_task`, `get_profile_display_name`, `ALL_PROFILES`, `PROFILE_*`. Handlers take `task_store`, `current_permission_profile`, `general_approval`, `base_dir`, and mutable lists for `current_task`, `last_action`, `today_date`, `today_actions`, `last_task_create_fingerprint`.

### 3.7 Remain in main.py (no move)

- `_lumos_dir`, `_read_lumos_id`, `_input_or_eof`, `_parse_yes_no` (or move _input_or_eof/_parse_yes_no to cli/io.py used by lock and presence).
- `_sandbox_mode_from_env`
- `main()`: bootstrap, `do_lock`, `device_lock_cli`, `unlock_with_passphrase`, `state`, `engine`, `_recovery_lock_cb`, `engine.recover_presence`, `run_startup_self_check`, `run_self_test`, `_record_note_op`, `_record_today_action`, `_format_today_bullet`, definition of `_GLOBAL_CMDS`, `run_panel`, and the **while True** loop skeleton with:
  - watchdog_tick
  - input read and pending
  - CLI_NOT_BEKLEME / CLI_NOT_DUZENLEME handling
  - `normalize_command` call
  - dispatch to help (print), status handlers, lock_menu, presence_menu, notes handlers, tasks handlers, alias_menu, self_test, exit
- The `maybe_device_lock` hook: keep as `globals().get('maybe_device_lock')` in main so external/tests can inject; document in plan.

---

## 4. Risks and How to Avoid Regressions

### 4.1 Shared mutable state

- **Risk:** Notes and tasks logic rely on `saved_notes`, `last_route`, `today_actions`, `current_task`, etc. Moving handlers can introduce bugs if state is duplicated or updated in the wrong order.
- **Mitigation:** Keep a single “CLI context” object or explicit arguments in main; pass mutable lists/dicts into handlers; do not create new state in modules. In the first iteration, handlers can return (text_to_print, optional_updates) and main applies updates in a single place. Alternatively, pass a context object with methods like `context.record_today_action(...)` implemented in main and passed in.

### 4.2 Normalize_command and tests

- **Risk:** `tests/test_cli_parse.py` and any other code imports `normalize_command` and `get_fallback_message` from `main`. Changing import path can break tests.
- **Mitigation:** Either (1) move to `cli/parse.py` and add in main `from cli.parse import normalize_command, get_fallback_message` and keep `from main import normalize_command` working, or (2) update tests to `from cli.parse import normalize_command, get_fallback_message` in the same commit as the move. Prefer (1) for minimal test churn.

### 4.3 Lock/presence and engine callbacks

- **Risk:** `do_lock`, `device_lock_cli`, `unlock_with_passphrase` close over `root_key`, `lumos`, `ks`, `mode`, `online_engine`, `engine`. They must stay in main; only the menu UI moves. If presence or lock module tries to create its own lock callback, behavior could diverge.
- **Mitigation:** Lock and presence modules receive `engine: CoreEngine` (and state) and call `engine.do_lock()`, `engine.device_lock_cli(silent=...)`, `engine.unlock_with_passphrase(pw)`. No new closure in modules; all callbacks remain in main.

### 4.4 Presence atexit and recovery block

- **Risk:** The block that calls `pl.start_presence_lock` and `atexit.register(pl.stop_presence_lock)` is inside `presence_menu` in current code. Moving it to `cli/presence.py` must preserve exact call order and arguments (e.g. `is_already_locked=state.is_locked`).
- **Mitigation:** Move the entire block into `run_presence_menu` so that when the user first enters the presence menu, the same recovery/atexit logic runs. Or keep recovery in main (run once at boot) and only move the interactive menu loop; document which option is chosen.

### 4.5 Help and fallback string consistency

- **Risk:** Help and fallback strings are string literals; moving them to another file must not change content or encoding.
- **Mitigation:** Copy-paste only; no search-replace that could alter characters. Consider a single test that checks byte length or key phrases of HELP_TEXT and REHBER_TEXT.

### 4.6 Import cycles

- **Risk:** main → cli.status → core.startup_health, main → cli.notes → … If cli.* imports main, cycle.
- **Mitigation:** cli modules must not import main. main imports cli.* and core/engine/security/task_engine. Help/parse may import from core only if needed (e.g. get_durum_parts in status).

### 4.7 Self-test and startup self-check

- **Risk:** `run_startup_self_check` and `run_self_test` call `normalize_command("help", ...)` and reference HELP_TEXT. After moving, they must still resolve the same.
- **Mitigation:** After moving constants to cli/help_.py, have main (or run_self_test) import HELP_TEXT from cli.help_ and use it in the same way. run_self_test and run_startup_self_check can stay in main and call into cli only for parse/help.

### 4.8 Regression testing

- **Before/after each phase:** Run `pytest tests/` (including test_cli_parse.py, test_sandbox_mode_source.py, test_presence_lifecycle.py, test_online.py as applicable). Manually run CLI: `durum`, `hazir`, `yardım`, `kilit` (then cik), `kamera` (then cik), `görevler`, `görev oluştur test`, `notları göster`, `bunu hatırla test not`, `alias liste`, `self test`, then exit. Ensure no behavior or output change.

---

## 5. Summary

| Item | Content |
|------|--------|
| **Target structure** | Thin `main.py` + `cli/parse.py`, `cli/help_.py`, `cli/status.py`, `cli/lock.py`, `cli/presence.py`, `cli/notes.py`, `cli/tasks.py`, optional `cli/alias_.py`. |
| **Extraction order** | 1) Help constants, 2) Parser+fallback, 3) Status, 4) Lock menu, 5) Presence menu, 6) Notes, 7) Tasks, 8) Alias (optional). |
| **Exact moves** | See §3: constants and helpers by name; status helpers and route blocks; lock_menu; presence_menu; note handlers and _record_note_op; task route blocks. |
| **Risks** | Shared state, import paths for tests, engine callbacks in main only, presence recovery/atexit, string consistency, import cycles, self-test references. Mitigations: single context in main, re-exports, no new closures in cli, copy-paste help strings, cli never imports main, run full test suite and smoke after each phase. |

**Do not modify code yet.** This document is the plan only; implementation follows in separate steps after approval.
