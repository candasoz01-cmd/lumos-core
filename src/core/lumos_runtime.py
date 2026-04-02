"""Lumos runtime initialization: engine, memory, policy, context, bootstrap.

Extracted from main.py. Owns workspace bootstrap, engine/memory/policy setup,
CoreState/CoreEngine, lock/presence menus, CLI contexts, and router context build.
Integrates task_engine (TaskStore, TaskEngine for records; ObservationTaskEngine for
internal tasks from system_monitor signals). Does not own CLI entrypoint or run_cli_loop.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Any

from cli.cli_parse import (
    HELP_TEXT,
    _record_note_op,
    _record_today_action,
    _shorten_previous_response,
    normalize_command,
)
from cli.cli_readonly import ReadOnlyContext
from cli.cli_router import RouterContext
from cli.cli_tasks_mutation import TaskMutationContext
from core.config import load_config
from core.engine import CoreEngine
from core.health_check import run_health_check
from core.live_brain import handle_live_brain
from core.logfmt import logfmt
from core.lumos import Lumos
from core.state import CoreState
from core.workspace_contract import ensure_trash_dir, logs_file_path, trash_path
from engine.online_engine import OnlineEngineV1
from memory.schema import MemoryNote
from memory.secure_store import SecureNotesStore
from policy.offline_engine import OfflineEngineV1
from security import presence_lock as pl
from security.aliases import load_aliases, save_aliases
from security.keystore import FileKeyStore
from security.permissions import PermissionManager
from task_engine import (
    TaskStore,
    TaskEngine,
    ObservationTaskEngine,
    TaskQueueWatcher,
    PROFILE_RAPOR,
    PROFILE_GUVENLI_YURUT,
)
from task_engine.observation import ObservationEngine as EventRecordingEngine


def _lumos_dir() -> str:
    return ".lumos"


def _input_or_eof(prompt: str, eof_value: str = "cik") -> str:
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return eof_value


def _parse_yes_no(x: str) -> bool | None:
    x = (x or "").strip().lower()
    x = x.replace("ı", "i").replace("İ", "i")
    yes = {"evet", "e", "y", "yes", "ok", "tamam", "ewet"}
    no = {"hayir", "hayır", "h", "n", "no"}
    if x in yes:
        return True
    if x in no:
        return False
    return None


def _sandbox_mode_from_env() -> bool:
    return os.getenv("LUMOS_SANDBOX", "").strip().lower() in ("1", "true", "yes")


def run_startup_self_check(
    base_dir: str | Path,
    state: CoreState,
    lumos: Lumos,
    aliases: dict,
    *,
    sandbox_mode: bool = False,
) -> None:
    """Açılışta kısa self-check: config, log, notes, parser, state."""
    print("self-check: başlıyor")
    results: list[tuple[str, bool, str]] = []
    base = Path(base_dir)
    tasks_dir = base / "tasks"
    logs_dir = base / "logs"
    trash_dir = trash_path(base)
    config_dir = base / "config"
    try:
        if not base.exists():
            results.append(("workdir", False, "çalışma kökü yok"))
        elif not base.is_dir():
            results.append(("workdir", False, "çalışma kökü dizin değil"))
        elif os.access(base, os.W_OK):
            results.append(("workdir", True, "ok"))
        else:
            results.append(("workdir", False, "çalışma kökü yazılamıyor"))
    except Exception as e:
        results.append(("workdir", False, str(e)[:60]))
    for name, path in (("tasks_dir", tasks_dir), ("logs_dir", logs_dir), ("trash_dir", trash_dir)):
        try:
            if not path.exists():
                results.append((name, False, "yok"))
            elif not path.is_dir():
                results.append((name, False, "dizin değil"))
            elif os.access(path, os.W_OK):
                results.append((name, True, "ok"))
            else:
                results.append((name, False, "yazılamıyor"))
        except Exception as e:
            results.append((name, False, str(e)[:60]))
    try:
        if not config_dir.exists():
            results.append(("config_dir", True, "yok (opsiyonel)"))
        elif not config_dir.is_dir():
            results.append(("config_dir", False, "dizin değil"))
        elif os.access(config_dir, os.W_OK):
            results.append(("config_dir", True, "ok"))
        else:
            results.append(("config_dir", False, "yazılamıyor"))
    except Exception as e:
        results.append(("config_dir", False, str(e)[:60]))
    try:
        load_config(Path(base_dir))
        results.append(("config", True, "ok"))
    except Exception as e:
        results.append(("config", False, str(e)[:60]))
    try:
        state.log_event(logfmt("self_check", step="logs"))
        results.append(("logs", True, "ok"))
    except Exception as e:
        results.append(("logs", False, str(e)[:60]))
    notes_msg = "ok"
    try:
        nm = getattr(lumos, "note_memory", None)
        if nm is None:
            results.append(("notes", False, "note_memory yok"))
        else:
            if getattr(lumos.lock_state, "unlocked", False) and nm.store and nm.root_key:
                nm._load_from_store()
            notes_msg = "ok (kilitli)" if state.is_locked() else "ok"
            results.append(("notes", True, notes_msg))
    except Exception as e:
        results.append(("notes", False, str(e)[:60]))
    try:
        r, a = normalize_command("help", Path(base_dir), aliases)
        if r == "help" and a == []:
            results.append(("parser", True, "ok"))
        else:
            results.append(("parser", False, "help route beklenmedi"))
    except Exception as e:
        results.append(("parser", False, str(e)[:60]))
    try:
        state.lock_status()
        state.snapshot(base_dir=base_dir)
        results.append(("state", True, "ok"))
    except Exception as e:
        results.append(("state", False, str(e)[:60]))
    try:
        ts = TaskStore(Path(base_dir) / "tasks", sandbox_mode=sandbox_mode)
        ts.list_all()
        results.append(("task_engine", True, "ok"))
    except Exception as e:
        results.append(("task_engine", False, str(e)[:60]))
    for name, ok, msg in results:
        status = "ok" if ok else "fail"
        if not ok:
            print(f"  {name}: {status} ({msg})")
        else:
            print(f"  {name}: {msg}")
    all_ok = all(r[1] for r in results)
    if all_ok:
        print("overall: ready")
    else:
        failed = [r[0] for r in results if not r[1]]
        print("overall: Kısmen hazır — " + ", ".join(failed))


def run_self_test(
    base_dir: str | Path,
    state: CoreState,
    lumos: Lumos,
    aliases: dict,
    saved_notes: list,
    *,
    sandbox_mode: bool = False,
) -> tuple[bool, int, int, list[str]]:
    """Derin self-test: config, logs, notes, alias, help, task_engine."""
    areas: list[tuple[str, bool]] = []
    try:
        load_config(Path(base_dir))
        areas.append(("config", True))
    except Exception:
        areas.append(("config", False))
    try:
        state.log_event(logfmt("self_test", step="logs"))
        areas.append(("logs", True))
    except Exception:
        areas.append(("logs", False))
    try:
        if state.is_locked():
            saved_notes.append("__self_test_note__")
            saved_notes.pop()
        else:
            nm = getattr(lumos, "note_memory", None)
            if nm and getattr(lumos.lock_state, "unlocked", False):
                n = MemoryNote(kind="constraint", content="__self_test__", source="local")
                nm.add(n)
                if nm.notes and nm.notes[-1].content == "__self_test__":
                    nm.notes.pop()
                    if nm.store and nm.root_key:
                        nm._save_to_store()
                else:
                    raise RuntimeError("note add verify failed")
        areas.append(("notes_add", True))
    except Exception:
        areas.append(("notes_add", False))
    try:
        if state.is_locked() and saved_notes:
            old = saved_notes[-1]
            saved_notes[-1] = "__edit_test__"
            saved_notes[-1] = old
        elif not state.is_locked():
            nm = getattr(lumos, "note_memory", None)
            if nm and nm.notes:
                old = nm.notes[-1].content
                nm.notes[-1].content = "__edit_test__"
                nm.notes[-1].content = old
        areas.append(("notes_edit", True))
    except Exception:
        areas.append(("notes_edit", False))
    try:
        _shorten_previous_response("Self test uzun bir metin özetlenebilir mi kontrol ediyor.")
        areas.append(("notes_summarize", True))
    except Exception:
        areas.append(("notes_summarize", False))
    try:
        a1 = load_aliases(base_dir)
        save_aliases(base_dir, a1 if isinstance(a1, dict) else {}, is_sandbox_mode=sandbox_mode)
        areas.append(("alias", True))
    except Exception:
        areas.append(("alias", False))
    try:
        ok = bool(HELP_TEXT and HELP_TEXT.strip())
        r, a = normalize_command("help", Path(base_dir), aliases)
        ok = ok and (r == "help" and a == [])
        areas.append(("help_blocks", ok))
    except Exception:
        areas.append(("help_blocks", False))
    try:
        ts = TaskStore(Path(base_dir) / "tasks", sandbox_mode=sandbox_mode)
        t = ts.create("Self-test görev", "not kontrol ve özet ver", PROFILE_GUVENLI_YURUT)
        engine = TaskEngine(ts, PROFILE_GUVENLI_YURUT, True, base_dir=Path(base_dir) / "tasks")
        run_ok, _ = engine.run_task(t.task_id)
        t2 = ts.get(t.task_id)
        areas.append(
            (
                "task_engine",
                bool(
                    run_ok
                    and t2
                    and t2.status in ("tamamlandi", "kismi")
                    and t2.verified_count >= 1
                ),
            )
        )
    except Exception:
        areas.append(("task_engine", False))
    passed_count = sum(1 for _, p in areas if p)
    total = len(areas)
    failed_areas = [name for name, p in areas if not p]
    return (len(failed_areas) == 0, total, passed_count, failed_areas)


@dataclass
class RuntimeResult:
    """Result of create_runtime(). main uses this to run CLI or exit after TUI."""

    ui_consumed: bool
    router_ctx: RouterContext | None


def create_runtime(sandbox_mode: bool | None = None) -> RuntimeResult:
    """Bootstrap workspace, engine, memory, policy; build state and CLI contexts. Returns RuntimeResult."""
    if sandbox_mode is None:
        sandbox_mode = _sandbox_mode_from_env()
    mode = os.getenv("LUMOS_MODE", "offline").strip().lower()
    base_dir = _lumos_dir()
    base_path = Path(base_dir)
    try:
        base_path.mkdir(parents=True, exist_ok=True)
        (base_path / "tasks").mkdir(parents=True, exist_ok=True)
        (base_path / "logs").mkdir(parents=True, exist_ok=True)
        ensure_trash_dir(base_path, is_sandbox_mode=sandbox_mode)
        (base_path / "config").mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        aliases = load_aliases(base_dir)
    except Exception:
        aliases = {}
    if not isinstance(aliases, dict):
        aliases = {}

    perm = PermissionManager(enabled=True)
    offline_engine = OfflineEngineV1(perm=perm)
    online_engine = OnlineEngineV1()
    engine = offline_engine if mode == "offline" else online_engine
    lumos = Lumos(mode=mode, engine=engine)
    lumos.boot()
    if mode == "online" and (os.getenv("OPENAI_API_KEY") or "").strip():
        print("OpenAI client connected")
    root_key: bytes | None = None
    ks = FileKeyStore(base_dir=base_dir, is_sandbox_mode=sandbox_mode)

    def _attach_notes(rk: bytes) -> bool:
        try:
            store = SecureNotesStore(base_dir=base_dir, is_sandbox_mode=sandbox_mode)
            lumos.note_memory.attach_store(store, rk)
            return True
        except Exception:
            return False

    def unlock_with_passphrase(passphrase: str) -> tuple[bool, str]:
        nonlocal root_key, online_engine, engine
        p = (passphrase or "").strip()
        if not p:
            return False, "FAIL"
        try:
            rk = ks.load_root_key(p)
            if not _attach_notes(rk):
                return False, "FAIL"
            root_key = rk
            lumos.lock_state.unlock(rk)
            try:
                lumos.note_memory.root_key = rk
            except Exception:
                pass
            os.environ["LUMOS_PASSPHRASE"] = p
            if mode == "online":
                online_engine = OnlineEngineV1()
                engine = online_engine
                lumos.engine = engine
            try:
                if mode == "online":
                    if hasattr(online_engine, "set_passphrase"):
                        online_engine.set_passphrase(p)
                    elif hasattr(online_engine, "passphrase"):
                        online_engine.passphrase = p
                    if hasattr(online_engine, "client") and hasattr(
                        online_engine.client, "set_passphrase"
                    ):
                        online_engine.client.set_passphrase(p)
                    elif hasattr(online_engine, "client") and hasattr(
                        online_engine.client, "passphrase"
                    ):
                        online_engine.client.passphrase = p
            except Exception:
                pass
            return True, "OK"
        except Exception:
            return False, "FAIL"

    def device_lock_cli(silent: bool = False) -> None:
        try:
            nm = getattr(lumos, "note_memory", None)
            if nm and hasattr(nm, "device_lock"):
                nm.device_lock()
            if not silent:
                print("Cihaz kilitlendi. (Lumos aktif)")
        except Exception:
            if not silent:
                print("Device lock hata verdi.")

    def do_lock() -> None:
        nonlocal root_key
        lumos.lock_state.lock()
        try:
            os.environ.pop("LUMOS_PASSPHRASE", None)
        except Exception:
            pass
        root_key = None
        try:
            lumos.note_memory.root_key = None
        except Exception:
            pass

    state = CoreState(lumos, pl, mode, base_dir=Path(base_dir), sandbox_mode=sandbox_mode)
    core_engine = CoreEngine(do_lock, device_lock_cli, unlock_with_passphrase, pl)

    def _recovery_lock_cb() -> None:
        try:
            core_engine.do_lock()
        except Exception:
            pass
        try:
            core_engine.device_lock_cli(silent=True)
        except Exception:
            pass

    core_engine.recover_presence(
        Path(base_dir),
        state.log_event,
        _recovery_lock_cb,
        state.is_locked,
        is_sandbox_mode=sandbox_mode,
    )

    print("Lumos başlatılıyor.")
    health = run_health_check()
    print(f"health_check: {health.get('overall', 'unknown')}")
    run_startup_self_check(base_dir, state, lumos, aliases, sandbox_mode=sandbox_mode)

    _GLOBAL_CMDS = {"kilit", "lock", "kamera", "presence", "alias", "self", "exit", "quit"}

    def presence_menu(
        *,
        state: CoreState,
        engine: CoreEngine,
        base_dir: str,
        initial_cmd: str | None = None,
    ) -> str | None:
        pl_mod = engine.pl

        def _lock_cb() -> None:
            engine.do_lock()
            try:
                engine.device_lock_cli(silent=False)
            except Exception:
                pass

        def _run_cmd(cmd: str) -> bool | str:
            cmd = (cmd or "").strip().lower()
            if cmd.startswith("kamera "):
                cmd = cmd.split(None, 1)[1].strip()
            _qc = cmd.replace("\u0131", "i")
            if _qc in ("ne yapiyorsun", "napiyon", "neyapiyorsun", "ne yapiyon"):
                print("Şu an kamera menüsündeyim.")
                return False
            if cmd in ("cik", "çık"):
                print("OK")
                return True
            if cmd and cmd.split()[0] in _GLOBAL_CMDS:
                return cmd
            if cmd in ("durum", "status"):
                cfg = pl_mod.load_presence_cfg(Path(base_dir))
                print(
                    f"enabled={cfg.enabled} timeout={cfg.timeout_sec}s face={cfg.require_face} mode={cfg.lock_mode} status={pl_mod.presence_status()}"
                )
                return False
            if cmd in ("ac", "aç", "on"):
                ans = _input_or_eof("Kamera tabanlı otomatik kilit açılsın mı? (evet/hayır): ")
                if ans in ("cik", "çık", "exit", "quit"):
                    print("OK")
                    return True
                __yn = _parse_yes_no(ans)
                if __yn is None:
                    print("Lütfen evet/hayır yaz.")
                    return False
                ans = "evet" if __yn else "hayır"
                if ans not in ("evet", "e", "yes", "y"):
                    print("OK")
                    return False
                raw = _input_or_eof("Kaç saniye yüz görünmezse kilitlesin? (varsayılan 30): ")
                try:
                    timeout = int(raw) if raw else 30
                except Exception:
                    timeout = 30
                if timeout < 5:
                    timeout = 5
                cfg = pl_mod.load_presence_cfg(Path(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                cfg.enabled = True
                cfg.timeout_sec = timeout
                cfg.poll_sec = 1.0
                cfg.camera_index = 0
                cfg.require_face = True
                cfg.lock_mode = "mac"
                if not was_enabled:
                    state.log_event(
                        logfmt(
                            "presence_enabled",
                            timeout=cfg.timeout_sec,
                            poll=cfg.poll_sec,
                            cam=cfg.camera_index,
                            require_face=cfg.require_face,
                        )
                    )
                pl_mod.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                pl_mod.start_presence_lock(
                    base_dir=Path(base_dir),
                    lock_cb=_lock_cb,
                    is_already_locked=state.is_locked,
                    timeout_sec=cfg.timeout_sec,
                    poll_sec=cfg.poll_sec,
                    camera_index=cfg.camera_index,
                    require_face=cfg.require_face,
                    is_sandbox_mode=sandbox_mode,
                )
                print("OK")
                return False
            if cmd in ("kapat", "off", "stop"):
                cfg = pl_mod.load_presence_cfg(Path(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                pl_mod.stop_presence_lock(
                    base_dir=Path(base_dir), reason=None, silent=True, is_sandbox_mode=sandbox_mode
                )
                if was_enabled:
                    state.log_event(logfmt("presence_disabled"))
                cfg.enabled = False
                pl_mod.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                print("OK")
                return False
            if cmd in ("sure", "süre", "timeout"):
                cfg = pl_mod.load_presence_cfg(Path(base_dir))
                default = int(getattr(cfg, "timeout_sec", 30))
                while True:
                    raw = _input_or_eof(f"Süre (sn) [{default}]: ")
                    if raw in ("cik", "çık", "exit", "quit"):
                        break
                    if raw == "" or raw in ("ok", "tamam"):
                        val = default
                        cfg.timeout_sec = val
                        pl_mod.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                        if cfg.enabled:
                            pl_mod.stop_presence_lock(
                                base_dir=Path(base_dir), silent=True, is_sandbox_mode=sandbox_mode
                            )
                            pl_mod.start_presence_lock(
                                base_dir=Path(base_dir),
                                lock_cb=_lock_cb,
                                is_already_locked=state.is_locked,
                                timeout_sec=cfg.timeout_sec,
                                poll_sec=cfg.poll_sec,
                                camera_index=cfg.camera_index,
                                require_face=cfg.require_face,
                                silent_stop=True,
                                reason="internal",
                                is_sandbox_mode=sandbox_mode,
                            )
                        print("OK")
                        break
                    if not raw.isdigit():
                        print("Lütfen sayı, ok veya çık yaz.")
                        continue
                    val = int(raw)
                    if val < 5 or val > 600:
                        print("Süre 5 ile 600 saniye arasında olmalı.")
                        continue
                    cfg.timeout_sec = val
                    pl_mod.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                    if cfg.enabled:
                        pl_mod.stop_presence_lock(
                            base_dir=Path(base_dir), silent=True, is_sandbox_mode=sandbox_mode
                        )
                        pl_mod.start_presence_lock(
                            base_dir=Path(base_dir),
                            lock_cb=_lock_cb,
                            is_already_locked=state.is_locked,
                            timeout_sec=cfg.timeout_sec,
                            poll_sec=cfg.poll_sec,
                            camera_index=cfg.camera_index,
                            require_face=cfg.require_face,
                            silent_stop=True,
                            reason="internal",
                            is_sandbox_mode=sandbox_mode,
                        )
                    print("OK")
                    break
                return False
            print(
                "Bunu anlamadım. Burada durum, ac, kapat, sure veya cik yazabilirsin."
            )
            return False

        print("Kamera: durum | ac | kapat | sure | cik")
        if initial_cmd:
            r = _run_cmd(initial_cmd)
            if r is True:
                return None
            if isinstance(r, str):
                return r
        while True:
            cmd = _input_or_eof("Kamera> ")
            r = _run_cmd(cmd)
            if r is True:
                return None
            if isinstance(r, str):
                return r
        return None

    def lock_menu(
        *,
        state: CoreState,
        engine: CoreEngine,
        initial_cmd: str | None = None,
    ) -> str | None:
        def _run_cmd(c: str) -> bool | str:
            _qc = (c or "").strip().replace("\u0131", "i")
            if _qc in ("ne yapiyorsun", "napiyon", "neyapiyorsun", "ne yapiyon"):
                print("Şu an kilit menüsündeyim.")
                return False
            if c in ("cik", "çık"):
                print("OK")
                return True
            if c and c.split()[0] in _GLOBAL_CMDS:
                return c
            if c in ("durum", "status"):
                print(state.lock_status())
                return False
            if c in ("kapat", "kilitle", "lock"):
                engine.do_lock()
                try:
                    engine.device_lock_cli(silent=True)
                except Exception:
                    pass
                return False
            if c in ("ac", "aç", "unlock", "open"):
                pw = getpass("Passphrase: ")
                ok, msg = engine.unlock_with_passphrase(pw)
                print(msg)
                return False
            print("Bunu anlamadım. Burada durum, ac, kapat veya cik yazabilirsin.")
            return False

        print("LOCK")
        print("Kilit: durum | ac | kapat | cik")
        if initial_cmd:
            c = initial_cmd.strip().lower()
            if c.startswith("kilit "):
                c = c.split(None, 1)[1].strip()
            r = _run_cmd(c)
            if r is True:
                return None
            if isinstance(r, str):
                return r
        while True:
            cmd = _input_or_eof("Kilit> ")
            if cmd.startswith("kilit "):
                cmd = cmd.split(None, 1)[1].strip()
            r = _run_cmd(cmd)
            if r is True:
                return None
            if isinstance(r, str):
                return r
        return None

    def alias_menu(*, args: list[str]) -> None:
        if not args:
            print("Alias: alias liste | alias ekle <ad> <hedef> | alias sil <ad>")
            return
        if args[0] == "liste":
            if not aliases:
                print("(alias yok)")
            else:
                for k, v in sorted(aliases.items()):
                    print(f"  {k} -> {v}")
            return
        if args[0] == "ekle":
            rest = " ".join(args[1:]).strip()
            tokens = rest.split(None, 1)
            name = tokens[0].lower() if tokens else ""
            target = tokens[1].strip() if len(tokens) > 1 else name
            if not name:
                print("Lütfen alias ekle <ad> <hedef> yaz. Örnek: alias ekle k kilit")
                return
            aliases[name] = target
            save_aliases(base_dir, aliases, is_sandbox_mode=sandbox_mode)
            print("OK")
            return
        if args[0] == "sil":
            name = (args[1] if len(args) > 1 else "").strip().lower()
            if not name:
                print("Lütfen alias sil <ad> yaz.")
                return
            if name in aliases:
                del aliases[name]
                save_aliases(base_dir, aliases, is_sandbox_mode=sandbox_mode)
            print("OK")
            return
        print("Alias: alias liste | alias ekle <ad> <hedef> | alias sil <ad>")

    def run_panel() -> None:
        try:
            from ui.tui import run_tui, tui_available
        except ImportError:
            print("Bu terminal panel desteklemiyor (curses yok).")
            return
        if not tui_available():
            print("Bu terminal panel desteklemiyor.")
            return
        mode_label = state.mode_str()
        title_line2 = f"{mode_label} • güvenli"
        log_path = logs_file_path(base_dir)

        def snapshot_getter() -> Any:
            return state.snapshot(base_dir=base_dir, log_path=log_path)

        run_tui(
            title="Lumos Core",
            title_line2=title_line2,
            snapshot_getter=snapshot_getter,
            items=[
                (
                    "Kilit",
                    lambda: lock_menu(state=state, engine=core_engine, initial_cmd=None),
                ),
                (
                    "Kamera (Presence)",
                    lambda: presence_menu(
                        state=state, engine=core_engine, base_dir=base_dir, initial_cmd=None
                    ),
                ),
                ("Alias", lambda: alias_menu(args=[])),
                ("Kayıtlar", lambda: None),
                ("Kapat", None),
            ],
            descriptions=[
                "Cihaz kilidi / şifre",
                "Yüz tanıma kilit",
                "Komut kısaltmaları",
                "Son 200 log satırı",
                "Panelden çık",
            ],
            hint="↑↓ seç, Enter onay, q çıkış",
            log_path=log_path,
            log_item_index=3,
        )

    ui_mode = (os.getenv("LUMOS_UI") or "").strip().lower()
    if ui_mode == "tui":
        try:
            run_panel()
        except Exception:
            print("Panel açılamadı, normal CLI'ye geçiliyor.")
        return RuntimeResult(ui_consumed=True, router_ctx=None)

    tasks_dir = base_path / "tasks"
    task_store = TaskStore(tasks_dir, sandbox_mode=sandbox_mode)
    observation_engine = ObservationTaskEngine(max_queue_size=500)
    queue_watcher = TaskQueueWatcher(observation_engine.queue)
    event_recording_engine = EventRecordingEngine()
    current_permission_profile: list[str] = [PROFILE_RAPOR]
    general_approval: list[bool] = [False]

    pending_ref: list[str | None] = [None]
    current_task: list[str | None] = [None]
    last_action: list[str | None] = [None]
    today_date: list[str] = [""]
    today_actions: list[list[str]] = [[]]
    last_response_reason: list[str | None] = [None]
    last_response_text: list[str | None] = [None]
    last_route: list[str | None] = [None]
    saved_notes: list[list[str]] = [[]]
    cli_mode: list[str] = ["normal_komut_modu"]
    last_note_undo: list[tuple[str, Any] | None] = [None]
    note_ops_history: list[list[str]] = [[]]
    last_task_create_fingerprint: list[tuple[str, str] | None] = [None]
    # Pending intent: clarification flow — when we asked e.g. "Hangi klasör?", store intent + missing param.
    pending_intent: list[dict | None] = [None]
    # Pending action: consent flow — when a task was blocked due to genel onay, store so we can resume after "onaylıyorum".
    pending_action: list[dict | None] = [None]

    ctx = ReadOnlyContext()
    ctx.base_dir = base_dir
    ctx.state = state
    ctx.ks = ks
    ctx.pl = pl
    ctx.mode = mode
    ctx.engine = core_engine
    ctx.saved_notes = saved_notes
    ctx.note_ops_history = note_ops_history
    ctx.last_response_reason = last_response_reason
    ctx.last_action = last_action
    ctx.last_response_text = last_response_text
    ctx.today_date = today_date
    ctx.today_actions = today_actions
    ctx.current_task = current_task
    ctx.current_permission_profile = current_permission_profile
    ctx.task_store = task_store
    ctx.aliases = aliases
    ctx.general_approval = general_approval
    ctx.record_note_op = lambda label: _record_note_op(note_ops_history, label)
    ctx.record_today_action = lambda action: _record_today_action(
        today_date, today_actions, action
    )

    mut_ctx = TaskMutationContext()
    mut_ctx.base_dir = base_dir
    mut_ctx.task_store = task_store
    mut_ctx.current_permission_profile = current_permission_profile
    mut_ctx.general_approval = general_approval
    mut_ctx.current_task = current_task
    mut_ctx.last_action = last_action
    mut_ctx.today_date = today_date
    mut_ctx.today_actions = today_actions
    mut_ctx.last_task_create_fingerprint = last_task_create_fingerprint
    mut_ctx.record_today_action = ctx.record_today_action
    mut_ctx.event_recording_engine = event_recording_engine
    mut_ctx.pending_intent = pending_intent
    mut_ctx.pending_action = pending_action
    mut_ctx.policy_runtime_mode = mode
    mut_ctx.policy_is_locked = state.is_locked

    def get_raw_input() -> str:
        try:
            return input("Sen: ").strip()
        except EOFError:
            return "çık"

    router_ctx = RouterContext()
    router_ctx.base_dir = base_dir
    router_ctx.aliases = aliases
    router_ctx.ctx = ctx
    router_ctx.mut_ctx = mut_ctx
    router_ctx.pending_ref = pending_ref
    router_ctx.cli_mode = cli_mode
    router_ctx.last_route = last_route
    router_ctx.last_note_undo = last_note_undo
    router_ctx.get_raw_input = get_raw_input
    router_ctx.observation_engine = observation_engine
    router_ctx.queue_watcher_tick = queue_watcher.tick
    router_ctx.watchdog_tick = lambda: pl.watchdog_tick(
        Path(base_dir),
        state.log_event,
        _recovery_lock_cb,
        state.is_locked,
        is_sandbox_mode=sandbox_mode,
    )
    router_ctx.on_lock_menu = lambda args: lock_menu(
        state=state, engine=core_engine, initial_cmd=args[0] if args else None
    )
    router_ctx.on_presence_menu = lambda args: presence_menu(
        state=state, engine=core_engine, base_dir=base_dir, initial_cmd=args[0] if args else None
    )

    def do_self_test() -> None:
        passed, total, passed_count, failed_areas = run_self_test(
            base_dir, state, lumos, aliases, saved_notes[0], sandbox_mode=sandbox_mode
        )
        if passed:
            print(f"self test: passed ({passed_count}/{total})")
        else:
            print(f"self test: failed ({passed_count}/{total})")
            if failed_areas:
                print("Kırık alanlar: " + ", ".join(failed_areas))

    router_ctx.on_self_test = do_self_test
    router_ctx.on_alias_menu = lambda args: alias_menu(args=args)

    router_ctx.mode = mode
    if mode == "online":
        def _live_brain_handler(raw: str) -> None:
            msg = handle_live_brain(
                raw,
                lumos.engine,
                task_store,
                base_dir,
                current_permission_profile[0],
                general_approval[0],
                observation_engine=event_recording_engine,
                state=state,
                general_approval_ref=general_approval,
                pending_intent_ref=pending_intent,
                pending_action_ref=pending_action,
            )
            print(msg)

        router_ctx.on_live_brain = _live_brain_handler
    else:
        router_ctx.on_live_brain = None

    return RuntimeResult(ui_consumed=False, router_ctx=router_ctx)

# lumos:instruction-pipeline safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)


print("agent test")


print("agent auto")

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)


# agent auto comment


# lumos:agent-auto safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)
