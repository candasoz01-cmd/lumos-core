"""
Option B: presence lifecycle + logging.
- stop_presence_lock(silent=True) must not log presence_stopped
- stop_presence_lock(silent=False) logs presence_stopped only if was_running
- recover_if_needed logs presence_autostarted only when config enabled + not running
- EOF on stdin exits cleanly (no traceback)
"""
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch


# Run tests with src in path so "security.presence_lock" resolves
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_stop_presence_lock_silent_true_does_not_log_presence_stopped():
    """stop_presence_lock(silent=True) must not log presence_stopped."""
    import lumos_core.security.presence_lock as pl
    log_calls = []
    with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
        pl.stop_presence_lock(base_dir=Path(ROOT / ".lumos"), silent=True)
    for msg in log_calls:
        assert "event=presence_stopped" not in msg, "silent=True must not log presence_stopped"


def test_stop_presence_lock_silent_false_logs_presence_stopped_only_if_was_running():
    """stop_presence_lock(silent=False) logs presence_stopped only when was_running."""
    import lumos_core.security.presence_lock as pl
    log_calls = []
    with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
        with patch.object(pl, "is_running", return_value=True):
            pl.stop_presence_lock(base_dir=Path(ROOT / ".lumos"), silent=False)
    stopped = [m for m in log_calls if "event=presence_stopped" in m]
    assert len(stopped) == 1, "silent=False and was_running=True should log presence_stopped once"


def test_stop_presence_lock_silent_false_no_log_when_not_running():
    """stop_presence_lock(silent=False) must not log presence_stopped when was_running=False."""
    import lumos_core.security.presence_lock as pl
    log_calls = []
    with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
        with patch.object(pl, "is_running", return_value=False):
            pl.stop_presence_lock(base_dir=Path(ROOT / ".lumos"), silent=False)
    for msg in log_calls:
        assert "event=presence_stopped" not in msg, "was_running=False must not log presence_stopped"


def test_recover_if_needed_logs_presence_autostarted_only_when_enabled_and_not_running():
    """Boot recovery logs presence_autostarted only when config enabled and thread not running."""
    import lumos_core.security.presence_lock as pl
    log_events = []
    def capture(msg):
        log_events.append(msg)
    with patch.object(pl, "is_enabled_from_config", return_value=True):
        with patch.object(pl, "is_running", return_value=False):
            with patch.object(pl, "start_presence_lock", return_value=(True, "OK")):
                pl.recover_if_needed(Path(ROOT / ".lumos"), capture, lock_cb=None, is_already_locked=None)
    assert any("presence_autostarted" in e and "boot_desync" in e for e in log_events), \
        "recover_if_needed should log presence_autostarted | reason=boot_desync"
    assert not any("presence_disabled" in e for e in log_events), \
        "recover_if_needed must not log presence_disabled"


def test_recover_if_needed_does_nothing_when_disabled():
    """When config disabled, recover_if_needed does not start or log presence_autostarted."""
    import lumos_core.security.presence_lock as pl
    log_events = []
    start_called = []
    def capture(msg):
        log_events.append(msg)
    def track_start(**kwargs):
        start_called.append(1)
        return (True, "OK")
    with patch.object(pl, "is_enabled_from_config", return_value=False):
        with patch.object(pl, "start_presence_lock", side_effect=track_start):
            pl.recover_if_needed(Path(ROOT / ".lumos"), capture, lock_cb=None, is_already_locked=None)
    assert not start_called, "should not start when config disabled"
    assert not any("presence_autostarted" in e for e in log_events)


def test_eof_exits_cleanly_no_traceback():
    """Stdin EOF exits with OK and no traceback (same as typing çık)."""
    import os
    result = subprocess.run(
        [sys.executable, "-m", "lumos_core"],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(SRC)},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=15,
    )
    out = result.stdout + result.stderr
    assert "OK" in out, "EOF exit should print OK"
    assert "Traceback" not in out, "No traceback on EOF exit"
    assert result.returncode == 0


def test_disable_silent_true_no_presence_stopped_in_log():
    """disable(silent=True) must not emit presence_stopped (Option B)."""
    import os
    log_path = ROOT / ".lumos" / "log.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    try:
        # Run smoke flow: kamera aç -> evet -> 10 -> kapat -> çık (disable uses silent=True)
        _ = subprocess.run(
            [sys.executable, "-m", "lumos_core"],
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": str(SRC)},
            capture_output=True,
            text=True,
            timeout=20,
            input="kamera aç\nevet\n10\nkapat\nçık\n",
        )
        log_content = log_path.read_text(encoding="utf-8", errors="replace")
        assert "presence_stopped" not in log_content, "Option B: presence_stopped must not appear in disable flow"
    finally:
        if log_path.exists():
            log_path.write_text("", encoding="utf-8")


def test_enable_then_disable_log_order_option_b():
    """After enable: presence_enabled, presence_started; then presence_disabled (no presence_stopped)."""
    import os
    log_path = ROOT / ".lumos" / "log.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    try:
        _ = subprocess.run(
            [sys.executable, "-m", "lumos_core"],
            cwd=str(ROOT),
            env={**os.environ, "PYTHONPATH": str(SRC)},
            capture_output=True,
            text=True,
            timeout=20,
            input="kamera aç\nevet\n10\nkapat\nçık\n",
        )
        lines = [ln for ln in log_path.read_text(encoding="utf-8", errors="replace").splitlines() if "|" in ln]
        # Log line format: "timestamp | event=... key=val ..."; extract event name from logfmt
        def event_name(log_part: str) -> str:
            if "event=" in log_part:
                return log_part.split("event=", 1)[1].split()[0]
            return log_part
        events = [ln.split("|", 2)[1].strip() for ln in lines]
        names = [event_name(e) for e in events]
        idx = {}
        for i, n in enumerate(names):
            if n not in idx:
                idx[n] = i
        assert "presence_enabled" in idx, "log must contain presence_enabled"
        assert "presence_started" in idx, "log must contain presence_started"
        assert "presence_disabled" in idx, "log must contain presence_disabled"
        assert idx["presence_enabled"] < idx["presence_started"], "presence_enabled before presence_started"
        assert idx["presence_started"] < idx["presence_disabled"], "presence_started before presence_disabled"
        assert "presence_stopped" not in names, "Option B: no presence_stopped in this flow"
    finally:
        if log_path.exists():
            log_path.write_text("", encoding="utf-8")


def test_presence_fsm_get_state_disabled():
    """FSM get_state returns DISABLED when config enabled=False."""
    import lumos_core.security.presence_fsm as fsm_mod
    import lumos_core.security.presence_lock as pl
    with patch.object(pl, "is_enabled_from_config", return_value=False):
        with patch.object(pl, "is_running", return_value=False):
            s = fsm_mod.get_state(Path(ROOT / ".lumos"), pl)
    assert s == fsm_mod.PresenceState.DISABLED


def test_presence_fsm_get_state_enabled_idle():
    """FSM get_state returns ENABLED_IDLE when config enabled=True and thread not running."""
    import lumos_core.security.presence_fsm as fsm_mod
    import lumos_core.security.presence_lock as pl
    with patch.object(pl, "is_enabled_from_config", return_value=True):
        with patch.object(pl, "is_running", return_value=False):
            s = fsm_mod.get_state(Path(ROOT / ".lumos"), pl)
    assert s == fsm_mod.PresenceState.ENABLED_IDLE


def test_format_status_line_from_snapshot():
    """format_status_line produces 'LOCKED | Presence: ... | Mode: ... | Log: ...' from snapshot."""
    from lumos_core.core.state import format_status_line
    snap = {
        "lock_status": "LOCKED",
        "presence_enabled": True,
        "presence_running": True,
        "mode": "offline",
        "last_log_ts": "2026-01-01 12:00:00",
    }
    line = format_status_line(snap)
    assert "LOCKED" in line and "Presence:" in line and "ON (running)" in line and "offline" in line and "Log:" in line
    snap2 = {"lock_status": "UNLOCKED", "presence_enabled": False, "presence_running": False, "mode": "offline", "last_log_ts": ""}
    line2 = format_status_line(snap2)
    assert "UNLOCKED" in line2 and "OFF" in line2


def test_presence_fsm_get_state_running():
    """FSM get_state returns RUNNING when config enabled=True and thread running."""
    import lumos_core.security.presence_fsm as fsm_mod
    import lumos_core.security.presence_lock as pl
    with patch.object(pl, "is_enabled_from_config", return_value=True):
        with patch.object(pl, "is_running", return_value=True):
            s = fsm_mod.get_state(Path(ROOT / ".lumos"), pl)
    assert s == fsm_mod.PresenceState.RUNNING