"""
Device guard: higher-level device protection and optimization layer on top of
system_monitor. Read-only analysis; no process termination; CLI-independent.

Architecture
------------
  system_monitor.scan_system_state()
           │
           ▼
  DeviceGuard.run()
           │
           ├── ingest monitor report
           ├── classify processes (system / user_app / background_service / suspicious)
           ├── detect issues (excessive CPU/memory, sensitive access, unusual network)
           └── emit structured DeviceGuardReport

  - Single dependency: device.system_monitor (no core/, cli/, main).
  - All logic is pure classification and aggregation; no side effects.
  - Report shape is fixed so Lumos (CLI, web, or agent) can consume it uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Only device-layer dependency.
from device.system_monitor import scan_system_state


class ProcessKind(str, Enum):
    """Process classification for device guard reporting."""

    SYSTEM = "system"
    USER_APP = "user_app"
    BACKGROUND_SERVICE = "background_service"
    SUSPICIOUS = "suspicious"


# Heuristic: name patterns that suggest system or background (platform-agnostic).
_SYSTEM_NAME_PATTERNS = (
    "kernel", "systemd", "launchd", "WindowServer", "loginwindow",
    "kext", "mdworker", "mds_", "cfprefsd", "distnoted", "apsd",
    "trustd", "syspolicyd", "securityd", "powerd", "configd",
)
_BACKGROUND_NAME_PATTERNS = (
    "Helper", "Agent", "Service", "Daemon", "daemon", "Update",
    "Backup", "Sync", "Index", "Notification", "Extension",
)


def _classify_process(name: str, pid: int, cpu_percent: float, memory_mb: float) -> ProcessKind:
    """
    Classify a process from its name and resource usage.
    Lightweight heuristics; no external calls.
    """
    n = (name or "").strip().lower()
    if any(p in n for p in (p.lower() for p in _SYSTEM_NAME_PATTERNS)):
        return ProcessKind.SYSTEM
    if any(p.lower() in n for p in _BACKGROUND_NAME_PATTERNS):
        return ProcessKind.BACKGROUND_SERVICE
    # High resource + unknown name -> suspicious until proven otherwise
    if cpu_percent >= 25.0 or memory_mb >= 500.0:
        return ProcessKind.SUSPICIOUS
    return ProcessKind.USER_APP


@dataclass
class DeviceGuardReport:
    """Structured device protection and optimization report. Read-only."""

    device_efficiency: int  # 0-100
    high_cpu: list[dict[str, Any]] = field(default_factory=list)
    high_memory: list[dict[str, Any]] = field(default_factory=list)
    background_services: list[dict[str, Any]] = field(default_factory=list)
    sensitive_access: list[dict[str, Any]] = field(default_factory=list)
    suspicious: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Export as dict for JSON or Lumos consumers."""
        return {
            "device_efficiency": self.device_efficiency,
            "high_cpu": self.high_cpu,
            "high_memory": self.high_memory,
            "background_services": self.background_services,
            "sensitive_access": self.sensitive_access,
            "suspicious": self.suspicious,
        }


class DeviceGuard:
    """
    Higher-level device protection and optimization.
    Consumes system_monitor output; classifies processes; detects issues; produces DeviceGuardReport.
    """

    def __init__(self) -> None:
        pass

    def run(self) -> DeviceGuardReport:
        """
        Collect from system_monitor, classify, detect issues, and return a DeviceGuardReport.
        Read-only; no process termination.
        """
        raw = scan_system_state()
        return self._build_report(raw)

    def _build_report(self, raw: dict[str, Any]) -> DeviceGuardReport:
        """Build DeviceGuardReport from system_monitor output."""
        device_efficiency = int(raw.get("efficiency_score", 100))
        high_cpu = list(raw.get("high_cpu_processes") or [])
        high_memory = list(raw.get("high_memory_processes") or [])
        sensitive_access = list(raw.get("sensitive_access") or [])

        # Classify high-CPU and high-memory processes into background_services vs suspicious.
        background_services: list[dict[str, Any]] = []
        suspicious: list[dict[str, Any]] = []

        seen_pids: set[int] = set()
        for rec in raw.get("suspicious_background") or []:
            pid = rec.get("pid", 0)
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            name = rec.get("name", "")
            cpu = float(rec.get("cpu_percent", 0))
            mem = float(rec.get("memory_mb", 0))
            kind = _classify_process(name, pid, cpu, mem)
            entry = {**rec, "kind": kind.value}
            if kind == ProcessKind.BACKGROUND_SERVICE:
                background_services.append(entry)
            elif kind == ProcessKind.SUSPICIOUS:
                suspicious.append(entry)
            else:
                background_services.append(entry)

        # Also add high_cpu/high_memory entries that weren't in suspicious_background
        for rec in high_cpu + high_memory:
            pid = rec.get("pid", 0)
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            kind = _classify_process(
                rec.get("name", ""),
                pid,
                float(rec.get("cpu_percent", 0)),
                float(rec.get("memory_mb", 0)),
            )
            entry = {**rec, "kind": kind.value}
            if kind == ProcessKind.SUSPICIOUS:
                suspicious.append(entry)
            elif kind == ProcessKind.BACKGROUND_SERVICE:
                background_services.append(entry)

        return DeviceGuardReport(
            device_efficiency=device_efficiency,
            high_cpu=high_cpu,
            high_memory=high_memory,
            background_services=background_services,
            sensitive_access=sensitive_access,
            suspicious=suspicious,
        )


def device_guard_scan() -> dict[str, Any]:
    """
    One-shot device guard scan: calls system_monitor, then builds and returns
    the structured report as a dict. Convenience API for Lumos runtime or CLI.

    Returns:
        {
          "device_efficiency": 0-100,
          "high_cpu": [...],
          "high_memory": [...],
          "background_services": [...],
          "sensitive_access": [...],
          "suspicious": [...]
        }
    """
    guard = DeviceGuard()
    return guard.run().to_dict()
