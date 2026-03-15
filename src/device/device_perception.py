"""
Device perception: lightweight snapshots of CPU, memory, process count,
battery, network, and sensitive-access summary. Safe for periodic polling.

Read-only; no process termination or modification. Logic only; no UI.
Uses psutil when available; returns None-safe values when psutil is missing.

Feeds: system_monitor (lightweight path), device_guard (when to run full scan),
device_action_policy (threshold-based trigger).
"""

from __future__ import annotations

import time
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def _cpu_percent() -> float:
    """
    Single sample; interval=None for non-blocking.
    Returns 0.0 if psutil is unavailable or on error.
    """
    if psutil is None:
        return 0.0
    try:
        return float(psutil.cpu_percent(interval=None))
    except Exception:
        return 0.0


def _memory_percent() -> float:
    """
    Virtual memory usage as a percentage (0–100).
    Returns 0.0 if psutil is unavailable or on error.
    """
    if psutil is None:
        return 0.0
    try:
        return float(psutil.virtual_memory().percent)
    except Exception:
        return 0.0


def _process_count() -> int:
    """
    Number of running process PIDs.
    Returns 0 if psutil is unavailable or on error.
    """
    if psutil is None:
        return 0
    try:
        return len(psutil.pids())
    except Exception:
        return 0


def _battery_snapshot() -> dict[str, Any]:
    """
    Battery status when available via psutil.
    Returns {"percent": float | None, "plugged": bool | None};
    both keys are None when battery API is unavailable.
    """
    out: dict[str, Any] = {"percent": None, "plugged": None}
    if psutil is None:
        return out
    try:
        bat = getattr(psutil, "sensors_battery", None)
        if bat is None:
            return out
        b = bat()
        if b is None:
            return out
        pct = getattr(b, "percent", None)
        out["percent"] = float(pct) if pct is not None else None
        out["plugged"] = getattr(b, "power_plugged", None)
    except Exception:
        pass
    return out


def _network_summary() -> dict[str, int]:
    """
    Lightweight network summary: bytes sent and received only.
    No per-connection iteration. Returns 0 for each counter when unavailable.
    """
    out: dict[str, int] = {"bytes_sent": 0, "bytes_recv": 0}
    if psutil is None:
        return out
    try:
        io = psutil.net_io_counters()
        if io:
            out["bytes_sent"] = int(getattr(io, "bytes_sent", 0) or 0)
            out["bytes_recv"] = int(getattr(io, "bytes_recv", 0) or 0)
    except Exception:
        pass
    return out


def _sensitive_access_summary() -> dict[str, None]:
    """
    Stub for camera/microphone/location access. Always returns None for each.
    Full sensitive-access logic lives in system_monitor / device_guard.
    Keeps snapshot lightweight and cross-platform.
    """
    return {"camera": None, "microphone": None, "location": None}


def get_device_snapshot() -> dict[str, Any]:
    """
    Unified lightweight device snapshot for periodic polling.

    Read-only: does not terminate processes or modify the system.
    Uses psutil when available; all values are None-safe when psutil is missing.

    Returns a dict with the following shape (suitable for system_monitor,
    device_guard, and device_action_policy integration):

        {
          "cpu_percent": float,
          "memory_percent": float,
          "process_count": int,
          "battery": {"percent": float | None, "plugged": bool | None},
          "network": {"bytes_sent": int, "bytes_recv": int},
          "sensitive_access": {"camera": None, "microphone": None, "location": None},
          "timestamp": float
        }

    - cpu_percent, memory_percent: 0.0 if unavailable.
    - process_count: 0 if unavailable.
    - battery.percent / battery.plugged: None when no battery API.
    - network: 0 when counters unavailable.
    - sensitive_access: always stub (None); full data from system_monitor/device_guard.
    - timestamp: Unix time (float) of snapshot.
    """
    return {
        "cpu_percent": _cpu_percent(),
        "memory_percent": _memory_percent(),
        "process_count": _process_count(),
        "battery": _battery_snapshot(),
        "network": _network_summary(),
        "sensitive_access": _sensitive_access_summary(),
        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# How this module feeds system_monitor, device_guard, device_action_policy
# ---------------------------------------------------------------------------
#
# 1. system_monitor
#    - device_perception is the lightweight path; system_monitor is the full scan.
#    - Periodic polling should use get_device_snapshot() to avoid the cost of
#      scan_system_state() (which iterates all processes and builds per-process lists).
#    - When a full report is needed (e.g. user asks "what's using my CPU?"), the
#      runtime calls system_monitor.scan_system_state(). Optionally, a future
#      optimization could pass a recent snapshot into system_monitor so it can
#      reuse cpu_percent/memory_percent instead of recomputing, but that is not
#      required for the current design.
#
# 2. device_guard
#    - device_guard.run() uses system_monitor.scan_system_state() to build
#      DeviceGuardReport (efficiency, high_cpu, background_services, etc.).
#    - device_perception does not replace that. Snapshots are for dashboards and
#      live metrics; device_guard remains the source for classification and
#      suggestions. A runtime can use get_device_snapshot() for frequent
#      updates (e.g. status bar) and trigger device_guard only on demand or
#      at a lower frequency.
#
# 3. device_action_policy
#    - suggest_actions(report) expects a report from device_guard (full report
#      shape). device_perception snapshots are not passed to suggest_actions.
#    - The flow is: snapshot for display/trending; when the user wants actions,
#      run device_guard -> report -> suggest_actions(report). Snapshot can
#      inform when to run a full scan (e.g. if cpu_percent or process_count
#      crosses a threshold, trigger system_monitor + device_guard and then
#      suggest_actions).
