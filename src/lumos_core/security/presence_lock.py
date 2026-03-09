"""
Presence lock: worker thread + config-driven lifecycle.
Thread-safe: module-level Lock around start/stop. presence_stopped only when (not silent) and was_running.

Teşhis (presence lock tetiklenmiyordu): lock_cb çağrılıyordu ama lock_mode "mac" hiç
kullanılmıyordu; macOS ekran kilidi tetiklenmiyordu. trigger_macos_screen_lock() eklendi.
Teşhis (absence_timeout hiç düşmüyordu): cap.read() False iken continue ile timeout
kontrolü atlanıyordu; ayrıca cascade false positive verebiliyordu. Timeout her iterasyonda
kontrol ediliyor, ok=False "yok" sayılıyor; cascade sıkılaştırıldı (minNeighbors=8, minSize 70).
"""
import json
import platform
import time
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Optional

from lumos_core.core.logfmt import logfmt


def trigger_macos_screen_lock() -> bool:
    """Trigger macOS lock screen. No-op on non-Darwin. Returns True if lock was triggered.
    Logs success/fail/error to .lumos/log.txt (macos_lock_triggered | macos_lock_failed | macos_lock_error)."""
    if platform.system() != "Darwin":
        return False

    def _log(msg: str) -> None:
        try:
            _append_log(msg)
        except Exception:
            pass

    try:
        import ctypes
        login_pf = ctypes.CDLL(
            "/System/Library/PrivateFrameworks/login.framework/Versions/Current/login"
        )
        result = login_pf.SACLockScreenImmediate()
        if result == 0:
            _log(logfmt("macos_lock_triggered", method="sac"))
            return True
        _log(logfmt("macos_lock_failed", method="sac", result=result))
    except Exception as e:
        _log(logfmt("macos_lock_error", method="sac", err=str(e)))

    try:
        import subprocess
        r = subprocess.run(
            ["pmset", "displaysleepnow"],
            timeout=2,
            capture_output=True,
            check=False,
        )
        if r.returncode == 0:
            _log(logfmt("macos_lock_triggered", method="pmset"))
            return True
        _log(logfmt("macos_lock_failed", method="pmset", returncode=r.returncode))
    except Exception as e:
        _log(logfmt("macos_lock_error", method="pmset", err=str(e)))

    return False


def _append_log(message: str) -> None:
    try:
        from datetime import datetime
        log_dir = Path.cwd() / ".lumos"
        log_dir.mkdir(parents=True, exist_ok=True)
        logp = log_dir / "log.txt"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {message}"
        logp.write_text((logp.read_text(encoding="utf-8") if logp.exists() else "") + line + "\n", encoding="utf-8")
    except Exception:
        pass


def log_event(message: str) -> None:
    _append_log(message)


_LOCK = threading.RLock()


try:
    import cv2
except Exception:
    cv2 = None

_CFG_NAME = "presence.json"
_STOP = threading.Event()
_THREAD: Optional[threading.Thread] = None
_STATUS = "OFF"

def _cfg_path(base_dir: Path) -> Path:
    return Path(base_dir) / _CFG_NAME

def _set_status(s: str) -> None:
    global _STATUS
    _STATUS = s

def presence_status() -> str:
    return _STATUS


def is_running() -> bool:
    global _THREAD
    t = _THREAD
    return t is not None and t.is_alive()


@dataclass
class PresenceLockConfig:
    enabled: bool = False
    timeout_sec: int = 30
    poll_sec: float = 1.0
    camera_index: int = 0
    require_face: bool = True
    lock_mode: str = "mac"  # "lumos" | "mac" | "lumos+mac"

def load_presence_cfg(base_dir: Path) -> PresenceLockConfig:
    p = _cfg_path(Path(base_dir))
    if not p.exists():
        return PresenceLockConfig()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return PresenceLockConfig(**data)
    except Exception:
        return PresenceLockConfig()


def is_enabled_from_config(base_dir: Path) -> bool:
    cfg = load_presence_cfg(Path(base_dir))
    return bool(getattr(cfg, "enabled", False))


def recover_if_needed(
    base_dir: Path,
    log_event: Callable[[str], None],
    lock_cb: Optional[Callable[[], None]] = None,
    is_already_locked: Optional[Callable[[], bool]] = None,
) -> None:
    if not is_enabled_from_config(base_dir) or is_running():
        return
    try:
        cfg = load_presence_cfg(Path(base_dir))
        start_presence_lock(
            base_dir=Path(base_dir),
            lock_cb=lock_cb,
            is_already_locked=is_already_locked,
            timeout_sec=int(getattr(cfg, "timeout_sec", 30)),
            poll_sec=float(getattr(cfg, "poll_sec", 1.0)),
            camera_index=int(getattr(cfg, "camera_index", 0)),
            require_face=bool(getattr(cfg, "require_face", True)),
            silent_stop=False,
            reason="boot_desync",
        )
        log_event(logfmt("presence_autostarted", reason="boot_desync"))
    except Exception:
        pass


def watchdog_tick(
    base_dir: Path,
    log_event: Callable[[str], None],
    lock_cb: Optional[Callable[[], None]] = None,
    is_already_locked: Optional[Callable[[], bool]] = None,
) -> None:
    """If config enabled and thread not running, start and log presence_autostarted reason=watchdog_desync."""
    if is_already_locked is not None:
        try:
            if is_already_locked():
                return
        except Exception:
            pass
    if not is_enabled_from_config(base_dir) or is_running():
        return
    try:
        cfg = load_presence_cfg(Path(base_dir))
        start_presence_lock(
            base_dir=Path(base_dir),
            lock_cb=lock_cb,
            is_already_locked=is_already_locked,
            timeout_sec=int(getattr(cfg, "timeout_sec", 30)),
            poll_sec=float(getattr(cfg, "poll_sec", 1.0)),
            camera_index=int(getattr(cfg, "camera_index", 0)),
            require_face=bool(getattr(cfg, "require_face", True)),
            silent_stop=False,
            reason="watchdog_desync",
        )
        log_event(logfmt("presence_autostarted", reason="watchdog_desync"))
    except Exception as e:
        try:
            log_event(logfmt("presence_autostart_failed", reason="watchdog", err=str(e)))
        except Exception:
            pass

def save_presence_cfg(base_dir: Path, cfg: PresenceLockConfig) -> None:
    p = _cfg_path(Path(base_dir))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")

def _detect_face(frame) -> bool:
    """Yüz var/yok: OpenCV haarcascade_frontalface. Stricter params to reduce false positives."""
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=8, minSize=(70, 70))
        return len(faces) > 0
    except Exception:
        return False

def _presence_loop(*, base_dir: Path, lock_cb: Optional[Callable[[], None]], timeout_sec: int, poll_sec: float, camera_index: int, require_face: bool) -> None:
    _set_status("ON")
    last_seen = time.time()
    last_logged_present: Optional[bool] = None  # log only on state change

    cap = None
    try:
        if cv2 is None:
            _set_status("ERR:opencv_yok")
            return

        cap = cv2.VideoCapture(int(camera_index))
        if not cap.isOpened():
            _set_status("ERR:kamera_acilamadi")
            return

        while not _STOP.is_set():
            ok, frame = cap.read()
            present = False
            if ok and frame is not None:
                present = True
                if require_face:
                    present = _detect_face(frame)
                if present:
                    last_seen = time.time()

            # Log face state only on change (no spam)
            if last_logged_present is not None and last_logged_present != present:
                try:
                    _append_log(logfmt("face_present", value=present))
                except Exception:
                    pass
            last_logged_present = present

            # Always check timeout (even when ok=False: no frame = treat as absent)
            if (time.time() - last_seen) >= float(timeout_sec):
                if lock_cb:
                    try:
                        _append_log(logfmt("absence_timeout", timeout_sec=timeout_sec))
                    except Exception:
                        pass
                    try:
                        lock_cb()
                    except Exception:
                        _set_status("ERR:lock_cb")
                last_seen = time.time()

            time.sleep(max(0.2, float(poll_sec)))

    finally:
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass
        _set_status("OFF")

def start_presence_lock(*, base_dir: Path, lock_cb: Optional[Callable[[], None]] = None, is_already_locked: Optional[Callable[[], bool]] = None, timeout_sec: int = 30, poll_sec: float = 1.0, camera_index: int = 0, require_face: bool = True, silent_stop: bool = False, reason: Optional[str] = None) -> tuple[bool, str]:
    _orig_lock_cb = lock_cb
    def lock_cb():
        # Always log so absence_timeout is followed by device_locked trigger=presence; then run lock chain.
        try:
            _append_log(logfmt("device_locked", trigger="presence"))
        except Exception:
            pass
        if _orig_lock_cb:
            _orig_lock_cb()

    with _LOCK:
        global _THREAD
        stop_presence_lock(base_dir=base_dir, silent=silent_stop)

        _STOP.clear()
        t = threading.Thread(
            target=_presence_loop,
            kwargs=dict(
                base_dir=Path(base_dir),
                lock_cb=lock_cb,
                timeout_sec=int(timeout_sec),
                poll_sec=float(poll_sec),
                camera_index=int(camera_index),
                require_face=bool(require_face),
            ),
            daemon=True,
        )
        _THREAD = t
        t.start()
        if reason not in ("boot_desync", "internal"):
            try:
                _append_log(logfmt("presence_started", reason=reason or ""))
            except Exception:
                pass
    return True, "OK"

def stop_presence_lock(*, base_dir: Path, reason: Optional[str] = None, silent: bool = False) -> tuple[bool, str]:
    with _LOCK:
        was_running = is_running()
        if (not silent) and was_running:
            try:
                _append_log(logfmt("presence_stopped", reason=reason or ""))
            except Exception:
                pass

        global _THREAD
        _STOP.set()
        t = _THREAD
        if t and t.is_alive():
            try:
                t.join(timeout=2.0)
            except Exception:
                pass
        _THREAD = None
        _set_status("OFF")
    return True, "OK"
