from __future__ import annotations
from pathlib import Path
import re

def die(msg: str):
    raise SystemExit(msg)

root = Path(".")
main_p = root / "src" / "main.py"
pl_p = root / "src" / "security" / "presence_lock.py"

for p in (main_p, pl_p):
    if not p.exists():
        die(f"ERR: missing {p}")

main = main_p.read_text(encoding="utf-8")
pl = pl_p.read_text(encoding="utf-8")

changed_main = False
changed_pl = False

if "presence_started" not in pl:
    if "_append_log" not in pl:
        die("ERR: presence_lock.py içinde _append_log bulunamadı (format farklı).")

    insert_marker = re.search(r"def\s+_append_log\(", pl)
    if not insert_marker:
        die("ERR: presence_lock.py içinde _append_log bloğu bulunamadı.")

    helper = r'''
def _log_started(reason: str | None = None):
    extra = f"reason={reason}" if reason else ""
    _append_log("presence_started", extra)

def _log_stopped(reason: str | None = None, silent: bool = False):
    if silent:
        return
    extra = f"reason={reason}" if reason else ""
    _append_log("presence_stopped", extra)
'''
    pl = pl[:insert_marker.start()] + helper + pl[insert_marker.start():]
    changed_pl = True

if re.search(r"def\s+start_presence_lock\s*\([^)]*\):", pl):
    if "reason:" not in pl:
        pl = re.sub(
            r"(def\s+start_presence_lock\s*\()",
            r"\1reason: str | None = None, ",
            pl,
            count=1
        )
        changed_pl = True

    if "silent_stop" not in pl:
        pl = re.sub(
            r"(def\s+stop_presence_lock\s*\()",
            r"\1silent: bool = False, reason: str | None = None, ",
            pl,
            count=1
        )
        changed_pl = True

    pl2, n = re.subn(
        r"_append_log\(\s*['\"]presence_enabled['\"][^\)]*\)\s*",
        "",
        pl
    )
    if n > 0:
        pl = pl2
        changed_pl = True

    pl2, n = re.subn(
        r"_append_log\(\s*['\"]presence_disabled['\"][^\)]*\)\s*",
        "",
        pl
    )
    if n > 0:
        pl = pl2
        changed_pl = True

    if "_log_started(" not in pl or "_log_stopped(" not in pl:
        die("ERR: helper log fonksiyonları eklenemedi.")

    if "_log_started(reason)" not in pl:
        pl2, n = re.subn(
            r"(start_presence_lock[^\n]*\n)",
            r"\1    _log_started(reason)\n",
            pl,
            count=1
        )
        if n:
            pl = pl2
            changed_pl = True

    if "_log_stopped(" not in pl:
        m = re.search(r"def\s+stop_presence_lock\s*\(", pl)
        if not m:
            die("ERR: stop_presence_lock bulunamadı.")
        body_start = pl.find("):", m.start())
        if body_start == -1:
            die("ERR: stop_presence_lock signature parse edilemedi.")
else:
    die("ERR: presence_lock.py içinde start_presence_lock bulunamadı (format farklı).")

if "presence_autostarted" not in main:
    main2, n = re.subn(
        r"(pl\.recover_if_needed\([^\)]*\)\s*)",
        r"\1\n        try:\n            snap = state.snapshot(Path(base_dir))\n            if snap.get('presence_enabled') and not pl.is_running():\n                pl.start_presence_lock(Path(base_dir), lock_cb=_recovery_lock_cb, is_already_locked=state.is_locked, reason='boot_desync')\n                state.log_event('presence_autostarted | reason=boot_desync')\n        except Exception as e:\n            state.log_event(f'presence_autostart_failed | err={e}')\n",
        main,
        count=1,
        flags=re.S
    )
    if n:
        main = main2
        changed_main = True

if "presence_enabled" in main:
    main2, n = re.subn(
        r"state\.log_event\(\s*['\"]presence_enabled[^'\"]*['\"]\s*\)\s*",
        "",
        main
    )
    if n:
        main = main2
        changed_main = True

if "presence_disabled" in main:
    main2, n = re.subn(
        r"state\.log_event\(\s*['\"]presence_disabled[^'\"]*['\"]\s*\)\s*",
        "",
        main
    )
    if n:
        main = main2
        changed_main = True

if not (changed_main or changed_pl):
    die("SKIP: Patch uygulanacak hedef bulunamadı (dosya formatı farklı olabilir).")

if changed_pl:
    pl_p.write_text(pl, encoding="utf-8")
if changed_main:
    main_p.write_text(main, encoding="utf-8")

print("OK: patch_presence_lifecycle uygulandı.")
