"""İlk açılış environment scan — sadece read-only bilgi toplar."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], timeout: int = 5) -> str:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _app_names_from_dir(path: Path) -> list[str]:
    names: list[str] = []
    if not path.is_dir():
        return names
    try:
        for item in path.iterdir():
            if item.suffix == ".app":
                names.append(item.stem)
    except OSError:
        pass
    return sorted(names)


def scan() -> dict:
    """Read-only: OS, CPU, RAM, disk, python/node/git, shell, ağ, uygulamalar."""
    out: dict = {}

    # OS
    out["os"] = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }

    # CPU
    out["cpu"] = platform.processor() or _run(["sysctl", "-n", "machdep.cpu.brand_string"]) or ""

    # RAM (Mac: sysctl hw.memsize)
    ram_bytes: int | None = None
    if platform.system() == "Darwin":
        s = _run(["sysctl", "-n", "hw.memsize"])
        if s and s.isdigit():
            ram_bytes = int(s)
    if ram_bytes is not None:
        out["ram_gb"] = round(ram_bytes / (1024**3), 2)
    else:
        out["ram_gb"] = None

    # Disk (cwd veya home)
    try:
        root = Path(os.path.expanduser("~"))
        usage = shutil.disk_usage(root)
        out["disk"] = {
            "path": str(root),
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
        }
    except Exception:
        out["disk"] = None

    # Python
    out["python"] = {
        "version": platform.python_version(),
        "executable": sys.executable,
        "venv": os.environ.get("VIRTUAL_ENV") or None,
    }

    # Node
    node_ver = _run(["node", "--version"])
    out["node"] = node_ver if node_ver else None

    # Git
    git_ver = _run(["git", "--version"])
    out["git"] = git_ver if git_ver else None

    # Shell
    out["shell"] = os.environ.get("SHELL") or ""

    # Ağ (basit: env var veya "unknown" — gerçek ping yapmıyoruz, read-only)
    out["network"] = "unknown"

    # Uygulamalar: /Applications + ~/Applications (eksik olabilir; pkg/dağınık uygulamalar sayılmaz)
    apps: list[str] = []
    for base in [Path("/Applications"), Path.home() / "Applications"]:
        apps.extend(_app_names_from_dir(base))
    out["applications"] = sorted(set(apps))
    out["applications_note"] = "Sadece /Applications ve ~/Applications; eksik olabilir."

    # macOS izinleri: env_scan ile tek kaynak (Full Disk / Screen Recording tespiti orada)
    from lumos_core.system.env_scan import scan_permissions_mac

    perms = scan_permissions_mac()
    out["permissions"] = {
        k: perms.get(k, "unknown")
        for k in ("accessibility", "full_disk_access", "screen_recording")
    }

    return out
