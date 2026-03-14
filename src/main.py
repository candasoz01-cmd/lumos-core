"""Lumos core CLI: lock, presence, alias, durum."""
import json
import os
from datetime import date
from getpass import getpass
from pathlib import Path
from typing import Any

from cli.cli_parse import (
    HATIRLA_NOTE_MAX_LEN,
    HELP_ARAMA_TEXT,
    HELP_ETIKETLER_TEXT,
    HELP_GORUNTULEME_TEXT,
    HELP_GUVENLIK_TEXT,
    HELP_KISA_TEXT,
    HELP_NOT_ISLEMLERI_TEXT,
    HELP_NOTLAR_TEXT,
    HELP_TEMEL_TEXT,
    HELP_TEXT,
    KISACA_ANLAT_SHORT_THRESHOLD,
    NOT_ADLANDIR_MAX_TAG_LEN,
    NOT_OZETLE_SHORT_THRESHOLD,
    REHBER_TEXT,
    UNKNOWN_CMD_TEXT,
    _format_neden_cevap,
    _format_today_bullet,
    _get_en_onemli_eksik,
    _get_guvenli_cevap,
    _get_mod_cevabi,
    _get_oneri,
    _get_tek_sonraki_adim,
    _record_note_op,
    _fold_for_search,
    _record_today_action,
    _shorten_previous_response,
    get_fallback_message,
    normalize_command,
)
from core.config import load_config
from core.engine import CoreEngine
from core.logfmt import logfmt
from core.lumos import Lumos
from core.state import CoreState, format_durum
from core.startup_health import get_durum_parts, get_startup_summary
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
    PROFILE_RAPOR,
    PROFILE_GUVENLI_YURUT,
    ALL_PROFILES,
    get_profile_display_name,
)


def _lumos_dir() -> str:
    # Çalışma kökü sabit: her zaman CWD altında `.lumos`.
    # Geliştirme sırasında eski `src/.lumos` düzeni desteklenmez; paketli çalışma ile hizalıdır.
    return ".lumos"

def _read_lumos_id(base_dir: str) -> str:
    try:
        p = Path(base_dir) / "identity.json"
        if not p.exists():
            return ""
        data = json.loads(p.read_text(encoding="utf-8"))
        return str(data.get("lumos_id", "")).strip()
    except Exception:
        return ""

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


def run_startup_self_check(
    base_dir: str | Path,
    state: CoreState,
    lumos: Lumos,
    aliases: dict,
    *,
    sandbox_mode: bool = False,
) -> None:
    """Açılışta kısa self-check: config, log, notes, parser, state. 2–5 sn aşmamalı."""
    print("self-check: başlıyor")
    results: list[tuple[str, bool, str]] = []

    base = Path(base_dir)
    tasks_dir = base / "tasks"
    logs_dir = base / "logs"
    trash_dir = trash_path(base)
    config_dir = base / "config"

    # Çalışma kökü ve sabit klasörlerin minimum yol kontrolleri.
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

    for name, path in (
        ("tasks_dir", tasks_dir),
        ("logs_dir", logs_dir),
        ("trash_dir", trash_dir),
    ):
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

    # config/ opsiyonel: varsa okunabilirliği bilgi amaçlı raporlanır.
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
    """Derin self-test: config, logs, not ekleme/düzenleme/özetleme, alias, yardım blokları, görev motoru. Sonuç: passed, toplam, geçen sayısı, kırık alanlar."""
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
        # base_dir verildiği için not kontrol adımı gerçek okuma yapar → tamamlandi veya kismi (güven katmanı)
        areas.append(("task_engine", bool(run_ok and t2 and t2.status in ("tamamlandi", "kismi") and t2.verified_count >= 1)))
    except Exception:
        areas.append(("task_engine", False))

    passed_count = sum(1 for _, p in areas if p)
    total = len(areas)
    failed_areas = [name for name, p in areas if not p]
    return (len(failed_areas) == 0, total, passed_count, failed_areas)


def _sandbox_mode_from_env() -> bool:
    """LUMOS_SANDBOX=1|true|yes (case-insensitive) → True; aksi halde False."""
    return os.getenv("LUMOS_SANDBOX", "").strip().lower() in ("1", "true", "yes")


def main(sandbox_mode: bool | None = None) -> None:
    if sandbox_mode is None:
        sandbox_mode = _sandbox_mode_from_env()

    mode = os.getenv("LUMOS_MODE", "offline").strip().lower()

    base_dir = _lumos_dir()
    base_path = Path(base_dir)
    # Sabit omurga: tasks/, logs/, trash/, config/ — yoksa kontrollü oluştur.
    try:
        base_path.mkdir(parents=True, exist_ok=True)
        (base_path / "tasks").mkdir(parents=True, exist_ok=True)
        (base_path / "logs").mkdir(parents=True, exist_ok=True)
        ensure_trash_dir(base_path, is_sandbox_mode=sandbox_mode)
        (base_path / "config").mkdir(parents=True, exist_ok=True)
    except Exception:
        # Dizın oluşturma hataları self-check içinde raporlanır.
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
    root_key = None
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

                    if hasattr(online_engine, "client") and hasattr(online_engine.client, "set_passphrase"):

                        online_engine.client.set_passphrase(p)

                    elif hasattr(online_engine, "client") and hasattr(online_engine.client, "passphrase"):

                        online_engine.client.passphrase = p

            except Exception:

                pass

            return True, "OK"

        except Exception:

            return False, "FAIL"

    


    def device_lock_cli(silent: bool = False):
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

        fn = globals().get('maybe_device_lock')

        if callable(fn):

            fn(lumos)

        try:

            os.environ.pop("LUMOS_PASSPHRASE", None)

        except Exception:

            pass
        root_key = None

        try:
            lumos.note_memory.root_key = None
        except Exception:
            pass

    def presence_menu(*, state: CoreState, engine: CoreEngine, base_dir: str, initial_cmd: str | None = None) -> str | None:
        pl = engine.pl

        def _lock_cb():
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
                cfg = pl.load_presence_cfg(Path(base_dir))
                print(f"enabled={cfg.enabled} timeout={cfg.timeout_sec}s face={cfg.require_face} mode={cfg.lock_mode} status={pl.presence_status()}")
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

                cfg = pl.load_presence_cfg(Path(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                cfg.enabled = True
                cfg.timeout_sec = timeout
                cfg.poll_sec = 1.0
                cfg.camera_index = 0
                cfg.require_face = True
                cfg.lock_mode = "mac"
                if not was_enabled:
                    state.log_event(logfmt("presence_enabled", timeout=cfg.timeout_sec, poll=cfg.poll_sec, cam=cfg.camera_index, require_face=cfg.require_face))
                pl.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                pl.start_presence_lock(base_dir=Path(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face, is_sandbox_mode=sandbox_mode)
                print("OK")
                return False

            if cmd in ("kapat", "off", "stop"):
                cfg = pl.load_presence_cfg(Path(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                pl.stop_presence_lock(base_dir=Path(base_dir), reason=None, silent=True, is_sandbox_mode=sandbox_mode)
                if was_enabled:
                    state.log_event(logfmt("presence_disabled"))
                cfg.enabled = False
                pl.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                print("OK")
                return False

            if cmd in ("sure", "süre", "timeout"):
                cfg = pl.load_presence_cfg(Path(base_dir))
                default = int(getattr(cfg, "timeout_sec", 30))
                while True:
                    raw = _input_or_eof(f"Süre (sn) [{default}]: ")
                    if raw in ("cik", "çık", "exit", "quit"):
                        break
                    if raw == "" or raw in ("ok", "tamam"):
                        val = default
                        cfg.timeout_sec = val
                        pl.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                        if cfg.enabled:
                            pl.stop_presence_lock(base_dir=Path(base_dir), silent=True, is_sandbox_mode=sandbox_mode)
                            pl.start_presence_lock(base_dir=Path(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face, silent_stop=True, reason="internal", is_sandbox_mode=sandbox_mode)
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
                    pl.save_presence_cfg(Path(base_dir), cfg, is_sandbox_mode=sandbox_mode)
                    if cfg.enabled:
                        pl.stop_presence_lock(base_dir=Path(base_dir), silent=True, is_sandbox_mode=sandbox_mode)
                        pl.start_presence_lock(base_dir=Path(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face, silent_stop=True, reason="internal", is_sandbox_mode=sandbox_mode)
                    print("OK")
                    break
                return False

            print('Bunu anlamadım. Burada durum, ac, kapat, sure veya cik yazabilirsin.')
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

        try:
            import inspect
            import atexit
        
            _base = Path(base_dir)
            _pcfg = pl.load_presence_cfg(_base)
    
            def _presence_lock_action():
                try:
                    engine.do_lock()
                except Exception:
                    pass
                try:
                    engine.device_lock_cli(silent=True)
                except Exception:
                    pass
    
            if getattr(_pcfg, "enabled", False) and not pl.is_running():
                try:
                    _sig = inspect.signature(pl.start_presence_lock)
                    _candidates = {
                        "base_dir": _base,
                        "on_lock": _presence_lock_action,
                        "lock_cb": _presence_lock_action,
                        "lock_fn": _presence_lock_action,
                        "callback": _presence_lock_action,
                        "on_trigger": _presence_lock_action,
                        "on_timeout": _presence_lock_action,
                        "is_already_locked": state.is_locked,
                    }
                    _kwargs = {k: v for k, v in _candidates.items() if k in _sig.parameters}
                    pl.start_presence_lock(**_kwargs)
                except Exception:
                    try:
                        pl.start_presence_lock(base_dir=_base)
                    except Exception:
                        pass

            if getattr(_pcfg, "enabled", False):
                def _presence_stop():
                    try:
                        _sig2 = inspect.signature(pl.stop_presence_lock)
                        _kwargs2 = {"base_dir": _base} if "base_dir" in _sig2.parameters else {}
                        pl.stop_presence_lock(**_kwargs2)
                    except Exception:
                        pass
    
                atexit.register(_presence_stop)
        except Exception:
            pass

    state = CoreState(lumos, pl, mode, base_dir=Path(base_dir), sandbox_mode=sandbox_mode)
    engine = CoreEngine(do_lock, device_lock_cli, unlock_with_passphrase, pl)

    def _recovery_lock_cb():
        try:
            engine.do_lock()
        except Exception:
            pass
        try:
            engine.device_lock_cli(silent=True)
        except Exception:
            pass

    engine.recover_presence(
        Path(base_dir),
        state.log_event,
        _recovery_lock_cb,
        state.is_locked,
        is_sandbox_mode=sandbox_mode,
    )

    print("Lumos başlatılıyor.")
    run_startup_self_check(base_dir, state, lumos, aliases, sandbox_mode=sandbox_mode)

    # Ürün iyileştirmesi: "hazir" / "hazır mıyım" ana promptta çalışıyor; Kilit> / Kamera> alt menülerinde global komut olarak eklenebilir.
    _GLOBAL_CMDS = {"kilit", "lock", "kamera", "presence", "alias", "self", "exit", "quit"}

    def lock_menu(*, state: CoreState, engine: CoreEngine, initial_cmd: str | None = None) -> str | None:
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
            print('Bunu anlamadım. Burada durum, ac, kapat veya cik yazabilirsin.')
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

        def snapshot_getter():
            return state.snapshot(base_dir=base_dir, log_path=log_path)

        run_tui(
            title="Lumos Core",
            title_line2=title_line2,
            snapshot_getter=snapshot_getter,
            items=[
                ("Kilit", lambda: lock_menu(state=state, engine=engine, initial_cmd=None)),
                ("Kamera (Presence)", lambda: presence_menu(state=state, engine=engine, base_dir=base_dir, initial_cmd=None)),
                ("Alias", lambda: alias_menu(args=[])),
                ("Kayıtlar", lambda: None),  # handled by TUI log viewer
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
        return

    # ---- Görev motoru + yetki profili + genel onay ----
    tasks_dir = base_path / "tasks"
    task_store = TaskStore(tasks_dir, sandbox_mode=sandbox_mode)
    current_permission_profile: list[str] = [PROFILE_RAPOR]
    general_approval: list[bool] = [False]

    # ---- CLI döngüsü ----
    pending: str | None = None
    current_task: list[str | None] = [None]  # aktif görev; "ne yapıyorsun" buna bakar
    last_action: list[str | None] = [None]   # en son tamamlanan iş; "son yaptığın ne" buna bakar
    today_date: list[str] = [""]             # YYYY-MM-DD; gün değişince today_actions sıfırlanır
    today_actions: list[list[str]] = [[]]     # bugünkü (tekilleştirilmiş) işler; "bugün ne yaptın" buna bakar
    last_response_reason: list[str | None] = [None]  # son cevabın gerekçesi; "neden böyle diyorsun" buna bakar
    last_response_text: list[str | None] = [None]     # son cevabın tam metni; "bunu kısaca anlat" buna bakar
    last_route: list[str | None] = [None]             # son başarılı komut route; fallback'te aileye göre yardım için
    saved_notes: list[list[str]] = [[]]               # kullanıcı notları (bunu hatırla / not et vb.)
    # Tek state: komut yorumlama ile metin-bekleyen akışlar kesin ayrım
    CLI_NORMAL = "normal_komut_modu"
    CLI_NOT_BEKLEME = "not_bekleme_modu"
    CLI_NOT_DUZENLEME = "not_duzenleme_modu"
    cli_mode: list[str] = [CLI_NORMAL]
    last_note_undo: list[tuple[str, Any] | None] = [None]  # (op, data) tek adımlık geri al
    note_ops_history: list[list[str]] = [[]]          # son not işlemleri (en fazla 5); "not geçmişi"
    last_task_create_fingerprint: list[tuple[str, str] | None] = [None]  # (profil, açıklama) yakın tekrar uyarısı için
    while True:
        try:
            pl.watchdog_tick(
                Path(base_dir),
                state.log_event,
                _recovery_lock_cb,
                state.is_locked,
                is_sandbox_mode=sandbox_mode,
            )
        except Exception:
            pass
        if pending is not None:
            raw = pending
        else:
            try:
                raw = input("Sen: ").strip()
            except EOFError:
                raw = "çık"

        pending = None

        # ---- Metin-bekleyen modlar: parser çalışmaz, girdi koşulsuz not metnidir ----
        if cli_mode[0] == CLI_NOT_BEKLEME:
            cli_mode[0] = CLI_NORMAL
            if not raw.strip():
                print("Boş metin kabul edilmiyor.")
                continue
            note_text = raw.strip()
            if len(note_text) > HATIRLA_NOTE_MAX_LEN:
                note_text = (note_text[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,") or note_text[:HATIRLA_NOTE_MAX_LEN])
            saved_notes[0].append(note_text)
            _record_note_op(note_ops_history, "bunu hatırla")
            last_response_reason[0] = "bunu hatırla dedin"
            last_action[0] = "En son hatırla işlemini yaptım."
            last_response_text[0] = "Bunu not ettim."
            _record_today_action(today_date, today_actions, last_action[0])
            print("Bunu not ettim.")
            continue
        if cli_mode[0] == CLI_NOT_DUZENLEME:
            cli_mode[0] = CLI_NORMAL
            if not raw.strip():
                print("Boş metin kabul edilmiyor.")
                continue
            old_content = saved_notes[0][-1]
            saved_notes[0][-1] = raw.strip()
            last_note_undo[0] = ("notu_duzenle", old_content)
            _record_note_op(note_ops_history, "notu düzenle")
            last_action[0] = "En son notu düzenledim."
            last_response_text[0] = "Son notu güncelledim."
            print("Son notu güncelledim.")
            continue

        # ---- normal_komut_modu: sadece burada parser çalışır ----
        route, args = normalize_command(raw, Path(base_dir), aliases)

        if route == "":
            continue
        if route != "unknown":
            last_route[0] = route
        if route == "unknown":
            print(get_fallback_message(raw, last_route[0]))
            continue
        if route == "help":
            last_response_reason[0] = "komut listesini istedin"
            last_action[0] = "En son yardım listesini gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_TEXT
            print(HELP_TEXT)
            continue
        if route == "help_etiketler":
            last_response_reason[0] = "etiket komutlarını istedin"
            last_action[0] = "En son etiket yardımını gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_ETIKETLER_TEXT
            print(HELP_ETIKETLER_TEXT)
            continue
        if route == "help_notlar":
            last_response_reason[0] = "not komutlarını istedin"
            last_action[0] = "En son not yardımını gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_NOTLAR_TEXT
            print(HELP_NOTLAR_TEXT)
            continue
        if route == "help_not_islemleri":
            last_response_reason[0] = "not işlem komutlarını istedin"
            last_action[0] = "En son not işlemleri yardımını gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_NOT_ISLEMLERI_TEXT
            print(HELP_NOT_ISLEMLERI_TEXT)
            continue
        if route == "help_temel":
            last_response_reason[0] = "temel komutları istedin"
            last_action[0] = "En son temel yardımını gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_TEMEL_TEXT
            print(HELP_TEMEL_TEXT)
            continue
        if route == "help_guvenlik":
            last_response_reason[0] = "güvenlik komutlarını istedin"
            last_action[0] = "En son güvenlik yardımını gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_GUVENLIK_TEXT
            print(HELP_GUVENLIK_TEXT)
            continue
        if route == "help_kisa":
            last_response_reason[0] = "kısa yardımı istedin"
            last_action[0] = "En son kısa yardımı gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_KISA_TEXT
            print(HELP_KISA_TEXT)
            continue
        if route == "help_arama":
            last_response_reason[0] = "arama komutlarını istedin"
            last_action[0] = "En son arama yardımını gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_ARAMA_TEXT
            print(HELP_ARAMA_TEXT)
            continue
        if route == "help_goruntuleme":
            last_response_reason[0] = "görüntüleme komutlarını istedin"
            last_action[0] = "En son görüntüleme yardımını gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_GORUNTULEME_TEXT
            print(HELP_GORUNTULEME_TEXT)
            continue
        if route == "rehber":
            last_response_reason[0] = "rehberi istedin"
            last_action[0] = "En son yardım rehberini gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = REHBER_TEXT
            print(REHBER_TEXT)
            continue
        if route == "onerir":
            oneriler = _get_oneri(base_dir, ks.is_initialized(), pl)
            for o in oneriler:
                print(o)
            last_response_reason[0] = (oneriler[0].rstrip(".") if oneriler and oneriler[0] else None)
            last_action[0] = "En son sonraki adım önerisini verdim."
            last_response_text[0] = "\n".join(oneriler) if oneriler else None
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "sonraki_adim":
            step = _get_tek_sonraki_adim(base_dir, ks.is_initialized(), pl)
            print(step)
            last_response_reason[0] = step.replace("Bir sonraki adım: ", "").strip() if step.startswith("Bir sonraki adım:") else step
            last_action[0] = "En son tek sonraki adımı söyledim."
            last_response_text[0] = step
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "guvenli_miyim":
            resp = _get_guvenli_cevap(base_dir, ks.is_initialized(), pl)
            print(resp)
            last_response_reason[0] = resp.split(". ", 1)[1].strip().rstrip(".") if ". " in resp else resp
            last_action[0] = "En son güvenlik cevabını verdim."
            last_response_text[0] = resp
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "en_onemli_eksik":
            resp = _get_en_onemli_eksik(base_dir, ks.is_initialized(), pl)
            print(resp)
            last_response_reason[0] = resp
            last_action[0] = "En son tek kritik eksiği söyledim."
            last_response_text[0] = resp
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "hangi_moddayim":
            resp = _get_mod_cevabi(mode, base_dir, ks.is_initialized(), pl)
            print(resp)
            last_response_reason[0] = resp
            last_action[0] = "En son mod cevabını verdim."
            last_response_text[0] = resp
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "neden_boyle":
            ned_cevap = _format_neden_cevap(last_response_reason[0])
            print(ned_cevap)
            last_action[0] = "En son önceki cevabın gerekçesini söyledim."
            last_response_text[0] = ned_cevap
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "kisaca_anlat":
            prev = (last_response_text[0] or "").strip()
            if not prev or len(prev) < KISACA_ANLAT_SHORT_THRESHOLD:
                out_short = "Zaten kısa söyledim."
                print(out_short)
            else:
                out_short = _shorten_previous_response(prev)
                print(out_short)
            last_response_reason[0] = "kısaca anlat dedin"
            last_action[0] = "En son önceki cevabı kısaca özetledim."
            last_response_text[0] = out_short
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "hatirla":
            note_rest = (args[0].strip() if args else "")
            if note_rest:
                if len(note_rest) > HATIRLA_NOTE_MAX_LEN:
                    note_rest = (note_rest[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,") or note_rest[:HATIRLA_NOTE_MAX_LEN])
                saved_notes[0].append(note_rest)
                _record_note_op(note_ops_history, "bunu hatırla")
                last_response_reason[0] = "bunu hatırla dedin"
                last_action[0] = "En son hatırla işlemini yaptım."
                last_response_text[0] = "Bunu not ettim."
                _record_today_action(today_date, today_actions, last_action[0])
                print("Bunu not ettim.")
            else:
                cli_mode[0] = CLI_NOT_BEKLEME
                last_response_reason[0] = "bunu hatırla dedin"
                last_action[0] = "En son hatırla istedin; not metnini bekliyorum."
                print("Ne hatırlayayım?")
            continue
        if route == "son_not_ne":
            if saved_notes[0]:
                print("Son not: " + saved_notes[0][-1])
            else:
                print("Henüz kayıtlı bir not yok.")
            continue
        if route == "notu_kopyala":
            if saved_notes[0]:
                _record_note_op(note_ops_history, "notu kopyala")
                print(saved_notes[0][-1])
            else:
                print("Kopyalanacak kayıtlı not yok.")
            continue
        if route == "notu_disa_aktar":
            if saved_notes[0]:
                _record_note_op(note_ops_history, "notu dışa aktar")
                print(saved_notes[0][-1])
            else:
                print("Dışa aktarılacak kayıtlı not yok.")
            continue
        if route == "notu_paylas":
            if saved_notes[0]:
                _record_note_op(note_ops_history, "notu paylaş")
                print(saved_notes[0][-1])
            else:
                print("Paylaşılacak kayıtlı not yok.")
            continue
        if route == "not_ozetle":
            if not saved_notes[0]:
                print("Özetlenecek kayıtlı not yok.")
            else:
                _record_note_op(note_ops_history, "not özetle")
                last_note = saved_notes[0][-1].strip()
                if len(last_note) <= NOT_OZETLE_SHORT_THRESHOLD:
                    print("Son not zaten yeterince kısa.")
                else:
                    short = _shorten_previous_response(last_note).strip()
                    if not short:
                        short = (last_note[:120].rsplit(maxsplit=1)[0].rstrip(".,") + ".") if len(last_note) > 120 else last_note
                    print("Kısa özet: " + short)
            continue
        if route == "notlari_goster":
            if not saved_notes[0]:
                print("Henüz kayıtlı not yok.")
            else:
                recent = saved_notes[0][-5:]
                print("Kayıtlı notlar:")
                for n in recent:
                    print("- " + n)
            continue
        if route == "etiketli_notlari_goster":
            tagged = [n for n in saved_notes[0] if n.startswith("[") and "] " in n]
            if not tagged:
                print("Henüz etiketli not yok.")
            else:
                recent_tagged = tagged[-5:]
                print("Etiketli notlar:")
                for n in recent_tagged:
                    print("- " + n)
            continue
        if route == "etikete_gore_notlari_goster":
            tag_raw = (args[0] if args else "").strip()
            if not tag_raw:
                print("Göstermek için bir etiket yazman gerekiyor.")
                continue
            tagged = [n for n in saved_notes[0] if n.startswith("[") and "] " in n]
            folded = _fold_for_search(tag_raw)
            matches = [n for n in tagged if _fold_for_search(n[1 : n.index("] ")].strip()) == folded]
            if not matches:
                print("Bu etikete sahip not bulamadım.")
            else:
                recent = matches[-5:]
                print("Eşleşen notlar:")
                for n in recent:
                    print("- " + n)
            continue
        if route == "etiketleri_goster":
            seen: set[str] = set()
            tags_ordered: list[str] = []
            for n in reversed(saved_notes[0]):
                if n.startswith("[") and "] " in n:
                    tag = n[1 : n.index("] ")].strip()
                    if tag and tag not in seen:
                        seen.add(tag)
                        tags_ordered.append(tag)
            if not tags_ordered:
                print("Henüz kayıtlı etiket yok.")
            else:
                print("Kayıtlı etiketler:")
                for t in tags_ordered:
                    print("- " + t)
            continue
        if route == "etiket_ara":
            word = (args[0] if args else "").strip()
            if not word:
                print("Aramak için bir etiket yazman gerekiyor.")
                continue
            seen_tag: set[str] = set()
            tags_ordered_etiket_ara: list[str] = []
            for n in reversed(saved_notes[0]):
                if n.startswith("[") and "] " in n:
                    tag = n[1 : n.index("] ")].strip()
                    if tag and tag not in seen_tag:
                        seen_tag.add(tag)
                        tags_ordered_etiket_ara.append(tag)
            folded = _fold_for_search(word)
            matched = [t for t in tags_ordered_etiket_ara if folded in _fold_for_search(t)]
            if not matched:
                print("Bu aramayla eşleşen etiket bulamadım.")
            else:
                print("Eşleşen etiketler:")
                for t in matched:
                    print("- " + t)
            continue
        if route == "not_gecmisi":
            if not note_ops_history[0]:
                print("Henüz kayıtlı not işlemi yok.")
            else:
                print("Son not işlemleri:")
                for op in reversed(note_ops_history[0]):
                    print("- " + op)
            continue
        if route == "notlari_temizle":
            if not saved_notes[0]:
                print("Temizlenecek kayıtlı not yok.")
            else:
                last_note_undo[0] = ("notlari_temizle", saved_notes[0][:])
                saved_notes[0].clear()
                _record_note_op(note_ops_history, "notları temizle")
                print("Kayıtlı notları temizledim.")
            continue
        if route == "notu_sil":
            if not saved_notes[0]:
                print("Silinecek kayıtlı not yok.")
            else:
                last_note_undo[0] = ("notu_sil", saved_notes[0][-1])
                saved_notes[0].pop()
                _record_note_op(note_ops_history, "notu sil")
                print("Son notu sildim.")
            continue
        if route == "notu_duzenle":
            if not saved_notes[0]:
                print("Düzenlenecek kayıtlı not yok.")
            else:
                inline_text = (args[0] if args else "").strip()
                if inline_text:
                    if len(inline_text) > HATIRLA_NOTE_MAX_LEN:
                        inline_text = (inline_text[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,") or inline_text[:HATIRLA_NOTE_MAX_LEN])
                    old_content = saved_notes[0][-1]
                    saved_notes[0][-1] = inline_text
                    last_note_undo[0] = ("notu_duzenle", old_content)
                    _record_note_op(note_ops_history, "notu düzenle")
                    last_action[0] = "En son notu düzenledim."
                    print("Son notu güncelledim.")
                else:
                    cli_mode[0] = CLI_NOT_DUZENLEME
                    print("Son notu düzenlemek için yeni kısa metni yaz.")
            continue
        if route == "notu_adlandir":
            tag_raw = (args[0] if args else "").strip()
            if not tag_raw:
                print("Etiket için kısa bir ad yazman gerekiyor.")
                continue
            if not saved_notes[0]:
                print("Etiketlenecek kayıtlı not yok.")
                continue
            tag = tag_raw
            if len(tag) > NOT_ADLANDIR_MAX_TAG_LEN:
                tag = tag[:NOT_ADLANDIR_MAX_TAG_LEN].strip()
            old_content = saved_notes[0][-1]
            saved_notes[0][-1] = "[" + tag + "] " + old_content
            last_note_undo[0] = ("notu_duzenle", old_content)
            _record_note_op(note_ops_history, "notu adlandır")
            print("Son notu etiketledim.")
            continue
        if route == "etiket_kaldir":
            tag_raw = (args[0] if args else "").strip()
            if not tag_raw:
                print("Kaldırmak için bir etiket yazman gerekiyor.")
                continue
            if not saved_notes[0]:
                print("Etiketi kaldıracak kayıtlı not yok.")
                continue
            last = saved_notes[0][-1]
            if not last.startswith("[") or "] " not in last:
                print("Son notta bu etiket yok.")
                continue
            idx = last.index("] ")
            tag_in_note = last[1:idx].strip()
            if _fold_for_search(tag_in_note) != _fold_for_search(tag_raw):
                print("Son notta bu etiket yok.")
                continue
            rest = last[idx + 2 :].strip()
            saved_notes[0][-1] = rest
            last_note_undo[0] = ("notu_duzenle", last)
            _record_note_op(note_ops_history, "etiket kaldır")
            print("Etiketi kaldırdım.")
            continue
        if route == "etiket_degistir":
            eski_raw = (args[0] if len(args) > 0 else "").strip()
            yeni_raw = (args[1] if len(args) > 1 else "").strip()
            if not eski_raw or not yeni_raw:
                print("Eski ve yeni etiket yazman gerekiyor.")
                continue
            if not saved_notes[0]:
                print("Etiket değiştirilecek kayıtlı not yok.")
                continue
            last = saved_notes[0][-1]
            if not last.startswith("[") or "] " not in last:
                print("Son notta bu etiket yok.")
                continue
            idx = last.index("] ")
            tag_in_note = last[1:idx].strip()
            if _fold_for_search(tag_in_note) != _fold_for_search(eski_raw):
                print("Son notta bu etiket yok.")
                continue
            yeni = yeni_raw
            if len(yeni) > NOT_ADLANDIR_MAX_TAG_LEN:
                yeni = yeni[:NOT_ADLANDIR_MAX_TAG_LEN].strip()
            rest = last[idx + 2 :].strip()
            saved_notes[0][-1] = "[" + yeni + "] " + rest
            last_note_undo[0] = ("notu_duzenle", last)
            _record_note_op(note_ops_history, "etiket değiştir")
            print("Etiketi güncelledim.")
            continue
        if route == "not_birlestir":
            if len(saved_notes[0]) < 2:
                print("Birleştirmek için en az 2 kayıtlı not gerekiyor.")
            else:
                last_two = [saved_notes[0][-2].strip(), saved_notes[0][-1].strip()]
                merged = (last_two[0] + " " + last_two[1]).strip()
                if len(merged) > 240:
                    merged = (merged[:240].rsplit(maxsplit=1)[0].rstrip(".,") + ".").strip() or merged[:240]
                saved_notes[0].append(merged)
                last_note_undo[0] = ("not_birlestir", None)
                _record_note_op(note_ops_history, "not birleştir")
                print("Son iki notu birleştirdim.")
            continue
        if route == "notu_geri_al":
            u = last_note_undo[0]
            if not u:
                print("Geri alınacak uygun bir not işlemi yok.")
            else:
                op, data = u
                if op == "notu_sil":
                    saved_notes[0].append(data)
                elif op == "notlari_temizle":
                    saved_notes[0][:] = data
                elif op == "notu_duzenle":
                    saved_notes[0][-1] = data
                elif op == "not_birlestir":
                    saved_notes[0].pop()
                last_note_undo[0] = None
                _record_note_op(note_ops_history, "notu geri al")
                print("Son not işlemini geri aldım.")
            continue
        if route == "kac_not_var":
            n = len(saved_notes[0])
            if n == 0:
                print("Kayıtlı not yok.")
            else:
                print(f"{n} kayıtlı not var.")
            continue
        if route == "not_ara":
            word = (args[0] if args else "").strip()
            if not word:
                print("Aramak için bir kelime yazman gerekiyor.")
                continue
            _record_note_op(note_ops_history, "not ara")
            folded = _fold_for_search(word)
            matches = [n for n in saved_notes[0] if folded in _fold_for_search(n)]
            if not matches:
                print("Bu aramayla eşleşen not bulamadım.")
            else:
                recent = matches[-5:]
                print("Eşleşen notlar:")
                for n in recent:
                    print("- " + n)
            continue
        if route == "etiketli_not_ara":
            word = (args[0] if args else "").strip()
            if not word:
                print("Aramak için bir kelime yazman gerekiyor.")
                continue
            tagged = [n for n in saved_notes[0] if n.startswith("[") and "] " in n]
            folded = _fold_for_search(word)
            matches = [n for n in tagged if folded in _fold_for_search(n)]
            if not matches:
                print("Bu aramayla eşleşen etiketli not bulamadım.")
            else:
                print("Eşleşen etiketli notlar:")
                for n in matches:
                    print("- " + n)
            continue
        # ---- Görev motoru + yetki + genel onay komutları ----
        if route == "yetki_profili":
            if not args or not args[0].strip():
                profile = current_permission_profile[0]
                print("Yetki profili: " + get_profile_display_name(profile))
                continue
            name = (args[0] or "").strip().lower().replace("-", "_")
            if name in ALL_PROFILES:
                current_permission_profile[0] = name
                print("Yetki profili: " + get_profile_display_name(name))
            else:
                print("Geçerli profiller: rapor, guvenli_yurut, kisitli_otonom")
            continue
        if route == "genel_onay_ac":
            general_approval[0] = True
            print("Genel onay açık. Bu oturumda izin profili kapsamında işler yürütülebilir.")
            continue
        if route == "genel_onay_kapat":
            general_approval[0] = False
            print("Genel onay kapalı.")
            continue
        if route == "gorev_olustur":
            desc = (args[0] if args else "").strip()
            if not desc:
                print("Kullanım: görev oluştur <açıklama>")
                continue
            profile = current_permission_profile[0]
            # Aynı açıklama + aynı profil + çok yakın zamanda oluşturulmuş görev varsa önce uyar, yeni görev açma.
            from task_engine import find_recent_similar_task  # lokal import: CLI bağımsız test edilebilir

            fingerprint = (profile, desc)
            similar = find_recent_similar_task(task_store.list_all(), desc, profile)
            if similar and last_task_create_fingerprint[0] != fingerprint:
                last_task_create_fingerprint[0] = fingerprint
                print(
                    f"Benzer bir görev zaten var: {similar.task_id}. "
                    "İstersen önce onu inceleyebilirsin (görev durumu/özeti/adımları). "
                    "Aynı komutu tekrar yazarsan yeni görev oluştururum."
                )
                continue
            last_task_create_fingerprint[0] = None
            t = task_store.create(title=desc[:80], description=desc, permission_profile=profile)
            print(f"Görev {t.task_id} oluşturuldu: {t.title}")
            task_engine = TaskEngine(task_store, profile, general_approval[0], base_dir=base_dir)
            current_task[0] = "görev yürütülüyor."
            try:
                ok, msg = task_engine.run_task(t.task_id)
                print(msg)
                last_action[0] = f"Görev {t.task_id} oluşturulup yürütüldü: {t.title}"
                _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "gorevler":
            tasks = task_store.list_all()
            if not tasks:
                print("Kayıtlı görev yok.")
            else:
                from task_engine import compute_task_stats, format_task_stats_line

                stats = compute_task_stats(tasks)
                print(format_task_stats_line(stats))
                for t in tasks:
                    status_label = t.status
                    if getattr(t, "archived", False):
                        status_label = f"{status_label} (arşiv)"
                    print(f"  {t.task_id}: {t.title} — {status_label}")
            continue
        if route == "gorev_durumu":
            id_str = (args[0] if args else "").strip()
            if not id_str:
                print("Kullanım: görev durumu <id>")
                continue
            try:
                tid = int(id_str)
            except ValueError:
                print("Geçerli bir görev id yaz.")
                continue
            t = task_store.get(tid)
            if not t:
                print("Görev bulunamadı.")
                continue
            print(f"Görev {t.task_id}: {t.title}")
            print(f"  Durum: {t.status} | Profil: {t.permission_profile} | Oluşturulma: {t.created_at}")
            if t.error_summary:
                print(f"  Hata: {t.error_summary}")
            continue
        if route == "gorev_adimlari":
            id_str = (args[0] if args else "").strip()
            if not id_str:
                print("Kullanım: görev adımları <id>")
                continue
            try:
                tid = int(id_str)
            except ValueError:
                print("Geçerli bir görev id yaz.")
                continue
            t = task_store.get(tid)
            if not t:
                print("Görev bulunamadı.")
                continue
            print(f"Görev {t.task_id}: {t.title} — adımlar:")
            for i, s in enumerate(t.steps, 1):
                rk = getattr(s, "result_kind", "") or "-"
                print(f"  {i}. [{s.status}] sonuç: {rk} — {s.title}")
            continue
        if route == "gorev_ozeti":
            id_str = (args[0] if args else "").strip()
            if not id_str:
                print("Kullanım: görev özeti <id>")
                continue
            try:
                tid = int(id_str)
            except ValueError:
                print("Geçerli bir görev id yaz.")
                continue
            t = task_store.get(tid)
            if not t:
                print("Görev bulunamadı.")
                continue
            # Doğrulama sayacı: toplam adım, tamamlanan, doğrulanan, doğrulanamayan, simülasyon, son durum, kısa sonuç
            total_steps = len(t.steps)
            completed_steps = sum(1 for s in t.steps if s.status == "tamamlandi")
            verified = getattr(t, "verified_count", 0)
            unverified = getattr(t, "unverified_count", 0)
            simulation = getattr(t, "simulation_count", 0)
            parts = [
                f"Toplam adım: {total_steps}",
                f"Tamamlanan adım: {completed_steps}",
                f"Doğrulanan adım: {verified}",
                f"Doğrulanamayan adım: {unverified}",
                f"Simülasyon adım: {simulation}",
                f"Son durum: {t.status}",
            ]
            if getattr(t, "elapsed_seconds", 0) > 0:
                parts.append(f"Geçen süre: {t.elapsed_seconds:.1f}s")
            short_result = (t.description or "")[:80]
            if len(t.description or "") > 80:
                short_result += "..."
            parts.append(f"Kısa sonuç: {short_result or '(yok)'}")
            print("\n".join(parts))
            continue
        if route == "gorev_iptal":
            id_str = (args[0] if args else "").strip()
            if not id_str:
                print("Kullanım: görev iptal <id>")
                continue
            try:
                tid = int(id_str)
            except ValueError:
                print("Geçerli bir görev id yaz.")
                continue
            task_engine = TaskEngine(task_store, current_permission_profile[0], general_approval[0], base_dir=base_dir)
            ok, msg = task_engine.cancel_task(tid)
            print(msg)
            continue
        if route == "gorev_temizle_tamamlananlar":
            # Yalnızca arşivleme yap; silme yok.
            count = task_store.archive_completed()
            if count == 0:
                print("Arşivlenecek tamamlanmış görev yok.")
            else:
                print(f"{count} tamamlanmış görevi arşive taşıdım.")
            continue
        if route == "gorev_temizle_simulasyonlar":
            # Yalnızca arşivleme yap; silme yok.
            count = task_store.archive_simulations()
            if count == 0:
                print("Arşivlenecek simülasyon görevi yok.")
            else:
                print(f"{count} simülasyon görevi arşive taşıdım.")
            continue
        if route == "gorev_arsivle":
            id_str = (args[0] if args else "").strip()
            if not id_str:
                print("Kullanım: görev arşivle <id>")
                continue
            try:
                tid = int(id_str)
            except ValueError:
                print("Geçerli bir görev id yaz.")
                continue
            if task_store.archive(tid):
                print(f"Görev {tid} arşive taşındı (silinmedi).")
            else:
                print("Görev bulunamadı veya zaten arşivde.")
            continue
        if route == "gorev_sil":
            id_str = (args[0] if args else "").strip()
            if not id_str:
                print("Kullanım: görev sil <id>")
                continue
            try:
                tid = int(id_str)
            except ValueError:
                print("Geçerli bir görev id yaz.")
                continue
            # Kalıcı silme: yalnızca açık kullanıcı komutu (guard: user_initiated=True).
            if task_store.delete(tid, user_initiated=True):
                print("Dikkat: Bu görev kalıcı olarak silindi ve geri alınamaz.")
            else:
                print("Silinecek görev bulunamadı.")
            continue
        if route == "gorev_sayac":
            from task_engine import compute_task_stats, format_task_stats_line

            stats = compute_task_stats(task_store.list_all())
            print(format_task_stats_line(stats))
            continue
        if route == "ne_yapiyorsun":
            if current_task[0]:
                txt = "Şu an " + current_task[0]
                print(txt)
                last_response_reason[0] = current_task[0]
            else:
                txt = "Şu an aktif bir görevim yok."
                print(txt)
                last_response_reason[0] = "aktif görev yoktu"
            last_response_text[0] = txt
            continue
        if route == "son_yaptigin_ne":
            if last_action[0]:
                print(last_action[0])
                last_response_reason[0] = last_action[0]
                last_response_text[0] = last_action[0]
            else:
                txt = "Henüz kayda değer bir işlem yapmadım."
                print(txt)
                last_response_reason[0] = "henüz işlem yoktu"
                last_response_text[0] = txt
            continue
        if route == "bugun_ne_yaptin":
            if today_date[0] != date.today().isoformat():
                today_date[0] = date.today().isoformat()
                today_actions[0] = []
            if not today_actions[0]:
                txt = "Bugün kayda değer bir işlem yapmadım."
                print(txt)
                last_response_reason[0] = "bugün işlem yoktu"
                last_response_text[0] = txt
            else:
                items = today_actions[0][-5:]  # en fazla 5 madde, en son yapılanlar
                lines = ["Bugün şunları yaptım:"] + ["- " + _format_today_bullet(a) for a in items]
                txt = "\n".join(lines)
                print(txt)
                last_response_reason[0] = "bugünkü işlere baktım"
                last_response_text[0] = txt
            continue
        if route == "unknown":
            last_response_reason[0] = None
            last_response_text[0] = None
            print(UNKNOWN_CMD_TEXT)
            continue
        if route == "exit":
            print("OK")
            break
        if route == "durum":
            current_task[0] = "durum çıktısını hazırlıyorum."
            try:
                # "durum özet" yazıldıysa sahada net görünsün
                is_ozet = bool(
                    args
                    and ("ozet" in (args[0].lower().replace("ö", "o").replace("ı", "i") or "")
                         or "özet" in (args[0] or ""))
                )
                if is_ozet:
                    print("Durum özeti:")
                log_path = logs_file_path(base_dir)
                snap = state.snapshot(base_dir=base_dir, log_path=log_path)
                parts = get_durum_parts(Path(base_dir), ks.is_initialized(), engine.pl)
                durum_txt = format_durum(snap, parts["consent_ok"], parts["lock_ok"], parts["durum_label"], parts["not_line"])
                print(durum_txt)
                last_response_reason[0] = parts.get("not_line") or parts.get("durum_label", "")
                last_action[0] = "En son durum özetini gösterdim."
                last_response_text[0] = durum_txt
                _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "hazir":
            current_task[0] = "açılış sağlık özetini doğruluyorum."
            try:
                summary = get_startup_summary(Path(base_dir), not state.is_locked(), pl)
                print(summary)
                last_response_reason[0] = summary
                last_action[0] = "En son hazır olma özetini verdim."
                last_response_text[0] = summary
                _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "kilit":
            current_task[0] = "kilit menüsündeyim."
            try:
                result = lock_menu(state=state, engine=engine, initial_cmd=args[0] if args else None)
                if result is not None:
                    pending = result
                else:
                    last_action[0] = "En son kilit menüsünü açtım."
                    _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "kamera":
            current_task[0] = "kamera menüsündeyim."
            try:
                result = presence_menu(state=state, engine=engine, base_dir=base_dir, initial_cmd=args[0] if args else None)
                if result is not None:
                    pending = result
                else:
                    last_action[0] = "En son kamera menüsünü açtım."
                    _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "self_test":
            passed, total, passed_count, failed_areas = run_self_test(
                base_dir, state, lumos, aliases, saved_notes[0], sandbox_mode=sandbox_mode
            )
            if passed:
                print(f"self test: passed ({passed_count}/{total})")
            else:
                print(f"self test: failed ({passed_count}/{total})")
                if failed_areas:
                    print("Kırık alanlar: " + ", ".join(failed_areas))
            continue
        if route == "alias":
            alias_menu(args=args)
            last_action[0] = "En son alias işlemi yaptım."
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        print(get_fallback_message(raw, last_route[0]))

if __name__ == "__main__":
    main()
