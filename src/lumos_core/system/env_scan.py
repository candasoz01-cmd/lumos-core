"""First-run environment scan (preview mode). Read-only; no disk/memory/log writes."""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout: int = 5) -> str:
    """Run command, return stripped stdout on success else ''."""
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


def _which(name: str) -> bool:
    """Check if executable is on PATH (read-only)."""
    try:
        r = subprocess.run(
            [name, "--version"] if name != "cursor" else ["cursor", "--version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass
    # Fallback: try which/where
    try:
        cmd = ["which", name] if platform.system() != "Windows" else ["where", name]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        return r.returncode == 0 and bool((r.stdout or "").strip())
    except Exception:
        return False


def detect_ram() -> str | int | None:
    """Detect RAM (read-only). Returns human string or bytes count or None."""
    if platform.system() == "Darwin":
        s = _run(["sysctl", "-n", "hw.memsize"])
        if s and s.isdigit():
            return int(s)
    if platform.system() == "Linux":
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            return int(parts[1]) * 1024  # kB -> bytes
                        break
        except (OSError, ValueError):
            pass
    return None


def scan_system() -> dict[str, Any]:
    """Read-only: OS, CPU, RAM, Python."""
    return {
        "os": platform.system(),
        "cpu": platform.processor()
        or _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        or "unknown",
        "ram": detect_ram(),
        "python": sys.version,
    }


def scan_dev_environment() -> dict[str, bool]:
    """Check presence of dev tools (read-only)."""
    tools = [
        "git",
        "python",
        "node",
        "docker",
        "ollama",
        "cursor",
        "vscode",
        "jupyter",
    ]
    out: dict[str, bool] = {}
    for name in tools:
        if name == "vscode":
            out[name] = _which("code")
        elif name == "cursor":
            out[name] = _which("cursor")
        elif name == "python":
            out[name] = _which("python") or _which("python3")
        else:
            out[name] = _which(name)
    return out


def scan_apps_mac() -> list[str]:
    """Scan /Applications and ~/Applications for .app names (read-only). Safe on non-Mac: returns []."""
    if platform.system() != "Darwin":
        return []
    names: list[str] = []
    for base in [Path("/Applications"), Path.home() / "Applications"]:
        if not base.is_dir():
            continue
        try:
            for item in base.iterdir():
                if item.suffix == ".app":
                    names.append(item.stem)
        except OSError:
            pass
    return sorted(set(names))


def scan_permissions_mac() -> dict[str, str]:
    """Heuristic detection of accessibility / terminal / screen recording / full disk (read-only). Do not request permissions."""
    out: dict[str, str] = {
        "accessibility": "unknown",
        "terminal": "unknown",
        "screen_recording": "unknown",
        "full_disk_access": "unknown",
    }
    if platform.system() != "Darwin":
        return out
    try:
        r = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first process',
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        ax = "granted" if r.returncode == 0 else "denied"
        out["accessibility"] = ax
        out["terminal"] = ax  # same process capability
    except Exception:
        pass
    # Screen recording / full disk access: no safe programmatic check without triggering prompt; leave unknown
    return out


def _permission_status(raw: str) -> str:
    """Map raw permission value to ready/missing/unknown."""
    v = (raw or "unknown").lower()
    if v == "granted":
        return "ready"
    if v == "denied":
        return "missing"
    return "unknown"


def _readiness_items(perms: dict[str, str]) -> list[dict[str, Any]]:
    """Build structured items for accessibility, terminal, screen_recording, full_disk_access."""
    labels = [
        ("accessibility", "Erişilebilirlik (kilit/presence)"),
        ("terminal", "Terminal komut çalıştırma"),
        ("screen_recording", "Ekran kaydı (isteğe bağlı)"),
        ("full_disk_access", "Tam disk erişimi (isteğe bağlı, dosya tarama)"),
    ]
    return [
        {"name": key, "status": _permission_status(perms.get(key)), "description": desc}
        for key, desc in labels
    ]


def _readiness_message(perms: dict[str, str], items: list[dict[str, Any]]) -> str:
    """Kısa kullanıcı mesajı: hazır/eksik ve nasıl açılır."""
    ax = (perms.get("accessibility") or "unknown").lower()
    term = (perms.get("terminal") or "unknown").lower()
    required_ok = ax == "granted" and term == "granted"

    if required_ok:
        return "macOS izinleri: Hazır."
    missing_display = []
    if ax != "granted":
        missing_display.append("Erişilebilirlik")
    if term != "granted":
        missing_display.append("Terminal")
    msg = "macOS izinleri: Eksik — " + ", ".join(missing_display) + "."
    msg += "\n  Açmak için: Sistem Ayarları > Gizlilik ve Güvenlik > Erişilebilirlik (ve Terminal) — Lumos/Python/Terminal ekleyin."
    return msg


def get_macos_permission_readiness() -> dict[str, Any]:
    """
    macOS izin durumu: ready, missing, message, items, permissions.
    full_disk_access her zaman permissions ve items içinde yer alır.
    macOS dışında: ready=True, missing=[], message fallback, items=[], permissions dolu.
    """
    perms = scan_permissions_mac()
    # full_disk_access her zaman sonuçta olsun
    if "full_disk_access" not in perms:
        perms["full_disk_access"] = "unknown"
    if platform.system() != "Darwin":
        return {
            "ready": True,
            "missing": [],
            "message": "macOS izinleri bu sistemde uygulanmıyor (macOS only).",
            "permissions": perms,
            "items": [],
            "full_disk_access": perms["full_disk_access"],
        }
    items = _readiness_items(perms)
    ax = (perms.get("accessibility") or "unknown").lower()
    term = (perms.get("terminal") or "unknown").lower()
    required_ok = ax == "granted" and term == "granted"
    missing: list[str] = []
    if ax != "granted":
        missing.append("Erişilebilirlik")
    if term != "granted":
        missing.append("Terminal")
    msg = _readiness_message(perms, items)
    return {
        "ready": required_ok,
        "missing": missing,
        "message": msg,
        "permissions": perms,
        "items": items,
        "full_disk_access": perms["full_disk_access"],
    }


def print_permission_readiness() -> None:
    """Print permission readiness: one status line, then optional details. Non-macOS: fallback message only."""
    r = get_macos_permission_readiness()
    print(r["message"])
    items = r.get("items") or []
    if items:
        for i in items:
            status_label = {
                "ready": "hazır",
                "missing": "eksik",
                "unknown": "bilinmiyor",
            }.get(i["status"], i["status"])
            print(f"  • {i['name']}: {status_label} — {i['description']}")


def _infer_capabilities(dev: dict[str, bool], apps: list[str]) -> list[str]:
    """Infer capability labels from detected tools."""
    caps: list[str] = []
    if dev.get("git") and dev.get("python"):
        caps.append("project_analysis")
    if dev.get("docker"):
        caps.append("container_support")
    if dev.get("ollama"):
        caps.append("local_llm")
    if dev.get("cursor") or "Cursor" in apps:
        caps.append("cursor_ide")
    if dev.get("vscode") or "Visual Studio Code" in apps:
        caps.append("vscode_ide")
    if dev.get("jupyter"):
        caps.append("notebooks")
    if dev.get("node"):
        caps.append("node_runtime")
    return caps


def build_capability_report() -> dict[str, Any]:
    """Build full report: system, dev_environment, applications, permissions, capabilities."""
    system = scan_system()
    dev_environment = scan_dev_environment()
    applications = scan_apps_mac()
    permissions = scan_permissions_mac()
    capabilities = _infer_capabilities(dev_environment, applications)
    return {
        "system": system,
        "dev_environment": dev_environment,
        "applications": applications,
        "permissions": permissions,
        "capabilities": capabilities,
    }


def _features_requiring_permissions() -> list[str]:
    """Features that need permissions (for onboarding message)."""
    return [
        "Erişilebilirlik (kilit / presence)",
        "Ekran kaydı (isteğe bağlı)",
    ]


def print_onboarding_preview(report: dict[str, Any] | None = None) -> None:
    """Console onboarding output (human style). No disk write."""
    if report is None:
        report = build_capability_report()
    print("Merhaba.")
    print("Cihazını hızlıca inceledim.\n")
    print("Şu anda yapabileceklerim:")
    caps = report.get("capabilities") or []
    if caps:
        for c in caps:
            print(f"  • {c}")
    else:
        print("  (henüz ek araç tespit edilmedi)")
    print("\nHenüz aktif olmayan özellikler:")
    for f in _features_requiring_permissions():
        print(f"  • {f}")
    print("\nNot: Bu bilgiler henüz kaydedilmedi.")
