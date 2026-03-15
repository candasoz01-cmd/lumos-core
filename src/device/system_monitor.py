"""
Lumos system efficiency monitor: observe processes, CPU, memory, network, and
sensitive resource access. Read-only; no process termination.

Uses psutil when available (pip install psutil) for cross-platform process and
network data. Without psutil, returns the same report structure with empty
collections. Sensitive access (camera, mic, location) is platform-specific and
stubbed where not implemented.
"""
from __future__ import annotations

import platform
import time
from dataclasses import dataclass
from typing import Any

# Optional: psutil provides cross-platform process/CPU/memory/network.
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

# Thresholds for "high" resource usage (tunable).
HIGH_CPU_PERCENT = 15.0
HIGH_MEMORY_MB = 200.0
MIN_RUNTIME_SECONDS = 60.0  # consider "background" if running this long with significant use

# Efficiency score: start at 100, subtract for high CPU/memory/background (capped so score in 0-100).
EFF_SCORE_PENALTY_PER_HIGH_CPU = 2
EFF_SCORE_PENALTY_PER_HIGH_MEM = 2
EFF_SCORE_PENALTY_PER_SUSPICIOUS = 3
EFF_SCORE_MAX_PENALTY_CPU = 30
EFF_SCORE_MAX_PENALTY_MEM = 30
EFF_SCORE_MAX_PENALTY_BG = 40


@dataclass
class ProcessInfo:
    """Lightweight process snapshot for reporting."""

    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    create_time: float | None = None
    status: str = ""


def _get_processes_snapshot() -> list[ProcessInfo]:
    """Collect a snapshot of processes with CPU and memory. Returns [] if psutil unavailable."""
    if psutil is None:
        return []
    result: list[ProcessInfo] = []
    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "create_time", "status"]):
            try:
                pinfo = proc.info
                cpu = float(pinfo.get("cpu_percent") or 0.0)
                mem = pinfo.get("memory_info")
                rss_mb = (mem.rss / (1024 * 1024)) if mem else 0.0
                result.append(
                    ProcessInfo(
                        pid=pinfo["pid"],
                        name=(pinfo.get("name") or "").strip() or f"pid:{pinfo['pid']}",
                        cpu_percent=cpu,
                        memory_mb=round(rss_mb, 2),
                        create_time=float(pinfo["create_time"]) if pinfo.get("create_time") else None,
                        status=(pinfo.get("status") or ""),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                continue
    except Exception:
        pass
    return result


def _get_network_activity() -> list[dict[str, Any]]:
    """Summarize network connections by process. Returns [] if psutil unavailable or on error."""
    if psutil is None:
        return []
    out: list[dict[str, Any]] = []
    try:
        conns = psutil.net_connections(kind="inet")
        now = time.time()
        for c in conns:
            if c.status not in ("ESTABLISHED", "SYN_SENT", "SYN_RECV", "LISTEN"):
                continue
            try:
                pid = c.pid or 0
                name = ""
                if pid and psutil:
                    try:
                        p = psutil.Process(pid)
                        name = p.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else ""
                raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else ""
                out.append(
                    {
                        "pid": pid,
                        "name": name,
                        "status": c.status,
                        "local": laddr,
                        "remote": raddr,
                        "timestamp": now,
                    }
                )
            except Exception:
                continue
    except (psutil.AccessDenied, AttributeError):
        pass
    return out[:500]  # cap to avoid huge reports


def _detect_sensitive_access() -> list[dict[str, Any]]:
    """
    Detect camera, microphone, or location access when possible.
    Platform-specific; returns empty where not implemented. Can be extended
    with platform hooks (e.g. macOS AVFoundation, Linux V4L2, Windows MF).
    """
    # Stub: no standard cross-platform API. Sensitive access detection would
    # require platform-specific code (e.g. macOS lsof on camera/mic devices,
    # or OS permission APIs). Return empty so report shape is fixed.
    return []


def _compute_efficiency_score(
    high_cpu: list[dict[str, Any]],
    high_mem: list[dict[str, Any]],
    suspicious_background: list[dict[str, Any]],
) -> int:
    """
    Lightweight score 0-100: start at 100, subtract for high CPU, high memory,
    and excessive suspicious background processes. Capped so score stays in [0, 100].
    """
    penalty = 0
    # High CPU: penalty per process, capped
    p_cpu = min(EFF_SCORE_MAX_PENALTY_CPU, len(high_cpu) * EFF_SCORE_PENALTY_PER_HIGH_CPU)
    penalty += p_cpu
    # High memory: penalty per process, capped
    p_mem = min(EFF_SCORE_MAX_PENALTY_MEM, len(high_mem) * EFF_SCORE_PENALTY_PER_HIGH_MEM)
    penalty += p_mem
    # Suspicious background (long-running + high resource): extra penalty, capped
    p_bg = min(EFF_SCORE_MAX_PENALTY_BG, len(suspicious_background) * EFF_SCORE_PENALTY_PER_SUSPICIOUS)
    penalty += p_bg
    return max(0, min(100, 100 - penalty))


def scan_system_state() -> dict[str, Any]:
    """
    Observe system state and return a structured efficiency report.
    Does not terminate any process; read-only.

    Returns a dict with:
      - efficiency_score: int 0-100 (device health signal; 100 = best)
      - high_cpu_processes: list of {pid, name, cpu_percent, memory_mb, ...}
      - high_memory_processes: list of {pid, name, cpu_percent, memory_mb, ...}
      - suspicious_background: list of processes that are high-resource and long-running
      - network_activity: list of {pid, name, status, local, remote, timestamp}
      - sensitive_access: list of {type, pid, ...} for camera/mic/location when detectable
      - collector_available: bool (False if psutil not installed or collection failed)
      - platform: str (e.g. Darwin, Linux, Windows)
    """
    report: dict[str, Any] = {
        "efficiency_score": 100,
        "high_cpu_processes": [],
        "high_memory_processes": [],
        "suspicious_background": [],
        "network_activity": [],
        "sensitive_access": [],
        "collector_available": psutil is not None,
        "platform": platform.system(),
    }

    procs = _get_processes_snapshot()
    if not procs:
        return report

    # One pass: tag high CPU and high memory
    high_cpu: list[dict[str, Any]] = []
    high_mem: list[dict[str, Any]] = []
    suspicious: list[dict[str, Any]] = []
    now = time.time()

    for p in procs:
        rec = {
            "pid": p.pid,
            "name": p.name,
            "cpu_percent": round(p.cpu_percent, 2),
            "memory_mb": p.memory_mb,
            "status": p.status,
        }
        if p.cpu_percent >= HIGH_CPU_PERCENT:
            high_cpu.append(rec)
        if p.memory_mb >= HIGH_MEMORY_MB:
            high_mem.append(rec)

        # Suspicious: high resource and long-running (likely background without user focus).
        runtime_sec = (now - p.create_time) if p.create_time else 0
        if runtime_sec >= MIN_RUNTIME_SECONDS and (p.cpu_percent >= HIGH_CPU_PERCENT or p.memory_mb >= HIGH_MEMORY_MB):
            rec_bg = dict(rec)
            rec_bg["runtime_seconds"] = round(runtime_sec, 1)
            suspicious.append(rec_bg)

    # Sort by severity (CPU or memory descending).
    high_cpu.sort(key=lambda x: -x["cpu_percent"])
    high_memory_processes = sorted(high_mem, key=lambda x: -x["memory_mb"])
    suspicious.sort(key=lambda x: -(x.get("cpu_percent", 0) + x.get("memory_mb", 0) / 100.0))

    report["high_cpu_processes"] = high_cpu[:50]
    report["high_memory_processes"] = high_memory_processes[:50]
    report["suspicious_background"] = suspicious[:30]
    report["efficiency_score"] = _compute_efficiency_score(
        report["high_cpu_processes"],
        report["high_memory_processes"],
        report["suspicious_background"],
    )
    report["network_activity"] = _get_network_activity()
    report["sensitive_access"] = _detect_sensitive_access()

    return report


# ---------------------------------------------------------------------------
# Integration: Lumos runtime can call scan_system_state() periodically, e.g.:
#
#   - From a background thread started in lumos_runtime.create_runtime():
#       threading.Thread(target=_monitor_loop, daemon=True).start()
#     where _monitor_loop sleeps N seconds, calls scan_system_state(), then
#     passes the report to a callback (e.g. log summary, or store last report
#     for "durum" / efficiency UI).
#
#   - From the CLI router's watchdog_tick(): call scan_system_state() every
#     M ticks to avoid overhead on every keypress.
#
#   - From a dedicated scheduler (e.g. every 60s) that only runs when Lumos
#     is in "efficiency monitoring" mode, so default runs stay lightweight.
#
# Optional dependency: pip install psutil for real data; without it, the
# report keeps the same shape but collections are empty and
# collector_available is False.
