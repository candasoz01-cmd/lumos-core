"""Lumos core CLI: lock, presence, alias, durum."""
import json
import os
import re
from getpass import getpass
from pathlib import Path

from lumos_core.core.engine import CoreEngine
from lumos_core.core.logfmt import logfmt
from lumos_core.core.lumos import Lumos
from lumos_core.core.state import CoreState, format_status_line
from lumos_core.engine.online_engine import OnlineEngineV1
from lumos_core.memory.secure_store import SecureNotesStore
from lumos_core.policy.offline_engine import OfflineEngineV1
from lumos_core.security import presence_lock as pl
from lumos_core.security.aliases import load_aliases, save_aliases, apply_alias
from lumos_core.security.keystore import FileKeyStore
from lumos_core.security.permissions import PermissionManager


def norm_cmd(s: str) -> str:
    s = (s or "").strip().casefold()
    aliases = {
        "quit": "cik",
        "exit": "cik",
        "çık": "cik",
        "cık": "cik",
        "kilitle": "kapat",
        "lock": "kapat",
        "unlock": "ac",
        "aç": "ac",
    }
    return aliases.get(s, s)

# Canonical CLI: exit synonyms (q, çık, cik, quit -> exit)
EXIT_SYNONYMS = frozenset({"exit", "quit", "çık", "cik", "çik", "q"})

HELP_TEXT = """Komutlar: kilit | kamera | alias | durum | exit
  kilit    Cihaz kilidi / şifre
  kamera   Yüz tanıma (presence) kilit
  alias    Komut kısaltmaları (alias liste | alias ekle <ad> <hedef> | alias sil <ad>)
  durum    Özet durum (kilit, presence, mode, log)
  exit     Çıkış (q, çık, quit)
Örnek: kilit, kamera aç, durum, çık"""


def _lumos_dir() -> str:
    if Path("src/.lumos").exists():
        return "src/.lumos"
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


def normalize_command(raw: str, base_dir: Path, aliases: dict) -> tuple[str, list[str]]:
    """Strip, casefold, apply user aliases, normalize head to canonical command. Return (canonical, args)."""
    s = (raw or "").strip().casefold()
    if not s:
        return ("", [])
    s = apply_alias(s, aliases)
    s = re.sub(r"[.,]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().casefold()
    if not s:
        return ("", [])
    parts = s.split()
    head = parts[0]
    rest = parts[1:] if len(parts) > 1 else []
    if head in EXIT_SYNONYMS:
        return ("exit", [])
    if head in ("help", "?"):
        return ("help", [])
    if head in ("kilit", "lock"):
        return ("kilit", rest)
    if head in ("kamera", "presence"):
        return ("kamera", rest)
    if head == "alias":
        return ("alias", rest)
    if head == "durum":
        return ("durum", rest)
    return ("unknown", [])


def handle_command(raw: str, base_dir: Path, aliases: dict) -> tuple[str, list[str]]:
    """Alias for normalize_command for compatibility."""
    return normalize_command(raw, base_dir, aliases)


def main() -> None:
    mode = os.getenv("LUMOS_MODE", "offline").strip().lower()

    base_dir = _lumos_dir()
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
    ks = FileKeyStore(base_dir=base_dir)

    def _attach_notes(rk: bytes) -> bool:
        try:
            store = SecureNotesStore(base_dir=base_dir)
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
        from pathlib import Path as _P
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
            if cmd in ("cik", "çık"):
                print("OK")
                return True
            if cmd and cmd.split()[0] in _GLOBAL_CMDS:
                return cmd
            if cmd in ("durum", "status"):
                cfg = pl.load_presence_cfg(_P(base_dir))
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

                cfg = pl.load_presence_cfg(_P(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                cfg.enabled = True
                cfg.timeout_sec = timeout
                cfg.poll_sec = 1.0
                cfg.camera_index = 0
                cfg.require_face = True
                cfg.lock_mode = "mac"
                if not was_enabled:
                    state.log_event(logfmt("presence_enabled", timeout=cfg.timeout_sec, poll=cfg.poll_sec, cam=cfg.camera_index, require_face=cfg.require_face))
                pl.save_presence_cfg(_P(base_dir), cfg)
                pl.start_presence_lock(base_dir=_P(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face)
                print("OK")
                return False

            if cmd in ("kapat", "off", "stop"):
                cfg = pl.load_presence_cfg(_P(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                pl.stop_presence_lock(base_dir=_P(base_dir), reason=None, silent=True)
                if was_enabled:
                    state.log_event(logfmt("presence_disabled"))
                cfg.enabled = False
                pl.save_presence_cfg(_P(base_dir), cfg)
                print("OK")
                return False

            if cmd in ("sure", "süre", "timeout"):
                cfg = pl.load_presence_cfg(_P(base_dir))
                default = int(getattr(cfg, "timeout_sec", 30))
                while True:
                    raw = _input_or_eof(f"Süre (sn) [{default}]: ")
                    if raw in ("cik", "çık", "exit", "quit"):
                        break
                    if raw == "" or raw in ("ok", "tamam"):
                        val = default
                        cfg.timeout_sec = val
                        pl.save_presence_cfg(_P(base_dir), cfg)
                        if cfg.enabled:
                            pl.stop_presence_lock(base_dir=_P(base_dir), silent=True)
                            pl.start_presence_lock(base_dir=_P(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face, silent_stop=True, reason="internal")
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
                    pl.save_presence_cfg(_P(base_dir), cfg)
                    if cfg.enabled:
                        pl.stop_presence_lock(base_dir=_P(base_dir), silent=True)
                        pl.start_presence_lock(base_dir=_P(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face, silent_stop=True, reason="internal")
                    print("OK")
                    break
                return False

            print("HELP: durum | ac | kapat | sure | cik")
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
            from pathlib import Path as _P
    
            _base = _P(base_dir)
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

    state = CoreState(lumos, pl, mode)
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

    engine.recover_presence(Path(base_dir), state.log_event, _recovery_lock_cb, state.is_locked)

    _GLOBAL_CMDS = {"kilit", "lock", "kamera", "presence", "alias", "exit", "quit"}

    def lock_menu(*, state: CoreState, engine: CoreEngine, initial_cmd: str | None = None) -> str | None:
        def _run_cmd(c: str) -> bool | str:
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
            print("HELP: durum | ac | kapat | cik")
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
            save_aliases(base_dir, aliases)
            print("OK")
            return
        if args[0] == "sil":
            name = (args[1] if len(args) > 1 else "").strip().lower()
            if not name:
                print("Lütfen alias sil <ad> yaz.")
                return
            if name in aliases:
                del aliases[name]
                save_aliases(base_dir, aliases)
            print("OK")
            return
        print("Alias: alias liste | alias ekle <ad> <hedef> | alias sil <ad>")

    def run_panel() -> None:
        from pathlib import Path as _P
        try:
            from lumos_core.ui.tui import run_tui, tui_available
        except ImportError:
            print("Bu terminal panel desteklemiyor (curses yok).")
            return
        if not tui_available():
            print("Bu terminal panel desteklemiyor.")
            return
        mode_label = state.mode_str()
        title_line2 = f"{mode_label} • güvenli"
        log_path = _P.cwd() / ".lumos" / "log.txt"

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

    # ---- CLI döngüsü ----
    pending: str | None = None
    while True:
        try:
            pl.watchdog_tick(Path(base_dir), state.log_event, _recovery_lock_cb, state.is_locked)
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
        route, args = normalize_command(raw, Path(base_dir), aliases)

        if route == "":
            continue
        if route == "help":
            print(HELP_TEXT)
            continue
        if route == "unknown":
            print("Bilinmeyen komut. (help yaz)")
            continue
        if route == "exit":
            print("OK")
            break
        if route == "durum":
            snap = state.snapshot(base_dir=base_dir, log_path=Path.cwd() / ".lumos" / "log.txt")
            print(format_status_line(snap))
            continue
        if route == "kilit":
            result = lock_menu(state=state, engine=engine, initial_cmd=args[0] if args else None)
            if result is not None:
                pending = result
            continue
        if route == "kamera":
            result = presence_menu(state=state, engine=engine, base_dir=base_dir, initial_cmd=args[0] if args else None)
            if result is not None:
                pending = result
            continue
        if route == "alias":
            alias_menu(args=args)
            continue
        print("Bilinmeyen komut. (help yaz)")

if __name__ == "__main__":
    main()
