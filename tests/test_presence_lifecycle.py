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
from unittest.mock import MagicMock, patch


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
    # Ensure presence was disabled so CLI logs presence_enabled (only logged when not was_enabled).
    # CI/order can leave presence.json enabled=True from other tests, causing this assert to fail.
    cfg_file = log_path.parent / "presence.json"
    if cfg_file.exists():
        cfg_file.unlink()
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


# ---- trigger_macos_screen_lock: success/fail logging (V1 physical lock) ----


def test_trigger_macos_screen_lock_non_darwin_returns_false_no_log():
    """On non-Darwin, trigger_macos_screen_lock returns False and does not log."""
    import lumos_core.security.presence_lock as pl
    log_calls = []
    with patch("platform.system", return_value="Linux"):
        with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
            out = pl.trigger_macos_screen_lock()
    assert out is False
    assert len(log_calls) == 0


def test_trigger_macos_screen_lock_darwin_sac_success_logs_triggered():
    """On Darwin with SACLockScreenImmediate success, logs macos_lock_triggered method=sac and returns True."""
    import lumos_core.security.presence_lock as pl
    log_calls = []
    mock_lib = MagicMock()
    mock_lib.SACLockScreenImmediate.return_value = 0
    with patch("platform.system", return_value="Darwin"):
        with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
            with patch("ctypes.CDLL", return_value=mock_lib):
                out = pl.trigger_macos_screen_lock()
    assert out is True
    assert len(log_calls) == 1
    assert "macos_lock_triggered" in log_calls[0] and "method=sac" in log_calls[0]


def test_trigger_macos_screen_lock_darwin_both_fail_logs_failed_or_error():
    """On Darwin when both SAC and pmset fail, logs macos_lock_failed or macos_lock_error and returns False."""
    import lumos_core.security.presence_lock as pl
    log_calls = []
    with patch("platform.system", return_value="Darwin"):
        with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
            with patch("ctypes.CDLL", side_effect=OSError("dlopen failed")):
                with patch("subprocess.run", return_value=MagicMock(returncode=1)):
                    out = pl.trigger_macos_screen_lock()
    assert out is False
    assert len(log_calls) >= 1
    has_fail_or_error = any(
        "macos_lock_failed" in m or "macos_lock_error" in m for m in log_calls
    )
    assert has_fail_or_error, f"expected fail/error log in {log_calls}"


def test_presence_timeout_locks_once_then_skips_when_already_locked():
    """Repeated timeout cycles must trigger lock_cb only once; once locked, is_already_locked prevents repeat."""
    import lumos_core.security.presence_lock as pl

    lock_cb_calls = []
    locked = [False]

    def is_already_locked():
        return locked[0]

    def user_lock_cb():
        lock_cb_calls.append(1)
        locked[0] = True

    time_call_count = [0]
    t0 = 1000.0
    step = 0.2
    timeout_sec = 30
    # Stop after ~100s simulated so we get at least 2 full timeout cycles (at 30s and 60s)
    stop_after_calls = 500

    def mock_time():
        time_call_count[0] += 1
        if time_call_count[0] >= stop_after_calls:
            pl._STOP.set()
        return t0 + (time_call_count[0] - 1) * step

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, object())

    with patch.object(pl, "_detect_face", return_value=False):
        with patch.object(pl, "cv2", MagicMock()) as mcv2:
            mcv2.VideoCapture.return_value = mock_cap
            with patch("lumos_core.security.presence_lock.time") as mtime:
                mtime.time = mock_time
                mtime.sleep = lambda x: None
                pl.start_presence_lock(
                    base_dir=Path(ROOT / ".lumos"),
                    lock_cb=user_lock_cb,
                    is_already_locked=is_already_locked,
                    timeout_sec=timeout_sec,
                    poll_sec=step,
                    camera_index=0,
                    require_face=True,
                    silent_stop=True,
                    reason="internal",
                )
                if pl._THREAD and pl._THREAD.is_alive():
                    pl._THREAD.join(timeout=5.0)
                pl.stop_presence_lock(base_dir=Path(ROOT / ".lumos"), silent=True)

    assert len(lock_cb_calls) == 1, "lock_cb must be invoked exactly once across repeated timeout cycles"


def test_presence_flapping_face_triggers_absence_timeout():
    """Flapping face_present (true/false every frame) must not reset last_seen; after timeout_sec absence_timeout and lock_cb must run."""
    import lumos_core.security.presence_lock as pl

    lock_cb_calls = []
    log_calls = []

    timeout_sec = 30
    poll_sec = 0.2
    t0 = 1000.0
    time_calls = [0]
    frame_idx = [0]  # increment per _detect_face call so flapping is true/false per frame, not per time.time()

    def mock_time():
        time_calls[0] += 1
        if time_calls[0] >= 200:
            pl._STOP.set()
        return t0 + (time_calls[0] - 1) * poll_sec

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, object())

    # Alternate True/False per frame so consecutive_present never reaches 2; absence_start never cleared
    def flip_face(_frame):
        frame_idx[0] += 1
        return (frame_idx[0] % 2) == 0

    with patch.object(pl, "_detect_face", side_effect=flip_face):
        with patch.object(pl, "cv2", MagicMock()) as mcv2:
            mcv2.VideoCapture.return_value = mock_cap
            with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
                with patch("lumos_core.security.presence_lock.time") as mtime:
                    mtime.time = mock_time
                    mtime.sleep = lambda x: None
                    pl.start_presence_lock(
                        base_dir=Path(ROOT / ".lumos"),
                        lock_cb=lambda: lock_cb_calls.append(1),
                        is_already_locked=lambda: False,
                        timeout_sec=timeout_sec,
                        poll_sec=poll_sec,
                        camera_index=0,
                        require_face=True,
                        silent_stop=True,
                        reason="internal",
                    )
                    if pl._THREAD and pl._THREAD.is_alive():
                        pl._THREAD.join(timeout=5.0)
                    pl.stop_presence_lock(base_dir=Path(ROOT / ".lumos"), silent=True)

    assert len(lock_cb_calls) == 1, "lock_cb must run once when flapping face never stabilizes"
    assert any("absence_timeout" in m for m in log_calls), "absence_timeout must be logged"


def test_unified_lock_log_format_device_locked():
    """Unified lock backbone: device_locked log must include event and trigger (manual|presence|recovery)."""
    from lumos_core.core.logfmt import logfmt

    for trigger in ("manual", "presence", "recovery"):
        msg = logfmt("device_locked", trigger=trigger)
        assert "event=device_locked" in msg, msg
        assert f"trigger={trigger}" in msg, msg


def test_lock_chain_error_log_format():
    """Unified lock backbone: lock_chain_error log must include trigger, step, err for diagnosis."""
    from lumos_core.core.logfmt import logfmt

    msg = logfmt("lock_chain_error", trigger="manual", step="do_lock", err="test err")
    assert "event=lock_chain_error" in msg
    assert "trigger=manual" in msg
    assert "step=do_lock" in msg
    assert "err=" in msg


def test_presence_timeout_path_logs_device_locked_trigger_presence():
    """Presence timeout must invoke lock_cb; unified contract: lock_cb logs device_locked trigger=presence."""
    import lumos_core.security.presence_lock as pl
    from lumos_core.core.logfmt import logfmt

    lock_cb_calls = []
    log_calls = []

    def unified_style_lock_cb():
        lock_cb_calls.append(1)
        log_calls.append(logfmt("device_locked", trigger="presence"))

    timeout_sec = 30
    poll_sec = 0.2
    t0 = 1000.0
    time_calls = [0]
    frame_idx = [0]

    def mock_time():
        time_calls[0] += 1
        if time_calls[0] >= 200:
            pl._STOP.set()
        return t0 + (time_calls[0] - 1) * poll_sec

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, object())

    def flip_face(_frame):
        frame_idx[0] += 1
        return (frame_idx[0] % 2) == 0

    with patch.object(pl, "_detect_face", side_effect=flip_face):
        with patch.object(pl, "cv2", MagicMock()) as mcv2:
            mcv2.VideoCapture.return_value = mock_cap
            with patch("lumos_core.security.presence_lock.time") as mtime:
                mtime.time = mock_time
                mtime.sleep = lambda x: None
                pl.start_presence_lock(
                    base_dir=Path(ROOT / ".lumos"),
                    lock_cb=unified_style_lock_cb,
                    is_already_locked=lambda: False,
                    timeout_sec=timeout_sec,
                    poll_sec=poll_sec,
                    camera_index=0,
                    require_face=True,
                    silent_stop=True,
                    reason="internal",
                )
                if pl._THREAD and pl._THREAD.is_alive():
                    pl._THREAD.join(timeout=5.0)
                pl.stop_presence_lock(base_dir=Path(ROOT / ".lumos"), silent=True)

    assert len(lock_cb_calls) == 1, "lock_cb must run once"
    assert len(log_calls) == 1, "unified lock_cb must log device_locked once"
    assert "event=device_locked" in log_calls[0] and "trigger=presence" in log_calls[0], log_calls


def test_realistic_flapping_triggers_absence_timeout_and_lock():
    """Realistic sequence: stable present, then 3s absent with 1-frame true blips; must trigger absence_timeout and lock_cb (device_locked trigger=presence)."""
    import lumos_core.security.presence_lock as pl
    from lumos_core.core.logfmt import logfmt

    lock_cb_calls = []
    log_calls = []

    def unified_style_lock_cb():
        lock_cb_calls.append(1)
        log_calls.append(logfmt("device_locked", trigger="presence"))
        pl._STOP.set()  # stop after first trigger so we only get one lock

    timeout_sec = 3
    poll_sec = 0.5
    t0 = 1000.0
    time_calls = [0]
    frame_idx = [0]

    # Frames 1–2 present (stabilized), then absent; frame 6 one true (blip), then absent until timeout
    def face_for_iter(_frame):
        frame_idx[0] += 1
        n = frame_idx[0]
        if n <= 2 or n == 6:
            return True
        return False

    def mock_time():
        time_calls[0] += 1
        if time_calls[0] >= 25:
            pl._STOP.set()
        return t0 + (time_calls[0] - 1) * poll_sec

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, object())

    with patch.object(pl, "_detect_face", side_effect=face_for_iter):
        with patch.object(pl, "cv2", MagicMock()) as mcv2:
            mcv2.VideoCapture.return_value = mock_cap
            with patch.object(pl, "_append_log", side_effect=lambda msg: log_calls.append(msg)):
                with patch("lumos_core.security.presence_lock.time") as mtime:
                    mtime.time = mock_time
                    mtime.sleep = lambda x: None
                    pl.start_presence_lock(
                        base_dir=Path(ROOT / ".lumos"),
                        lock_cb=unified_style_lock_cb,
                        is_already_locked=lambda: False,
                        timeout_sec=timeout_sec,
                        poll_sec=poll_sec,
                        camera_index=0,
                        require_face=True,
                        silent_stop=True,
                        reason="internal",
                    )
                    if pl._THREAD and pl._THREAD.is_alive():
                        pl._THREAD.join(timeout=5.0)
                    pl.stop_presence_lock(base_dir=Path(ROOT / ".lumos"), silent=True)

    assert len(lock_cb_calls) == 1, "lock_cb must run once after realistic flapping + 3s absence"
    assert any("absence_timeout" in m for m in log_calls), "absence_timeout must be logged"
    assert any("device_locked" in m and "trigger=presence" in m for m in log_calls), "device_locked trigger=presence must be logged"