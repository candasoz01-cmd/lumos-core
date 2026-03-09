"""Scan sonuçlarına göre can / limited / cannot sınıflandırması."""
from __future__ import annotations

CAPABILITY_LEVELS = frozenset({"can", "limited", "cannot"})


def classify(data: dict) -> dict[str, str]:
    """
    Scan çıktısına göre yetenek sınıflandırması.
    Döner: { "repo": "can"|"limited"|"cannot", "python_env": ..., ... }
    """
    caps: dict[str, str] = {}

    # Repo işleri: git gerekli
    if data.get("git"):
        caps["repo"] = "can"
    else:
        caps["repo"] = "cannot"

    # Python ortamı: venv varsa can, yoksa limited (sistem python riski)
    py_info = data.get("python") or {}
    if py_info.get("venv"):
        caps["python_env"] = "can"
    elif py_info.get("version"):
        caps["python_env"] = "limited"
    else:
        caps["python_env"] = "cannot"

    # Node (opsiyonel): yoksa frontend/build işleri limited
    if data.get("node"):
        caps["node"] = "can"
    else:
        caps["node"] = "limited"

    # Disk: az yer varsa limited
    disk = data.get("disk")
    if disk and isinstance(disk, dict):
        free = disk.get("free_gb")
        if free is not None:
            if free < 1.0:
                caps["disk"] = "cannot"
            elif free < 5.0:
                caps["disk"] = "limited"
            else:
                caps["disk"] = "can"
        else:
            caps["disk"] = "limited"
    else:
        caps["disk"] = "limited"

    # Ağ
    net = data.get("network")
    if net == "unknown":
        caps["network"] = "limited"
    else:
        caps["network"] = "can" if net else "limited"

    # Rapor etiketleri (Lumos Environment Report için)
    caps["repo_management"] = caps["repo"]
    caps["test_build"] = "can" if (caps["repo"] == "can" and caps["python_env"] in ("can", "limited")) else "limited" if caps["python_env"] != "cannot" else "cannot"
    perms = data.get("permissions") or {}
    fda = (perms.get("full_disk_access") or "unknown").lower()
    caps["file_scanning"] = "can" if (caps["disk"] == "can" and fda == "granted") else "limited" if caps["disk"] == "can" else caps["disk"]
    ax = (perms.get("accessibility") or "unknown").lower()
    caps["ui_automation"] = "can" if ax == "granted" else "cannot" if ax == "denied" else "limited"

    return caps


def format_report(data: dict, caps: dict[str, str]) -> str:
    """Lumos Environment Report: Device, Permissions, Capabilities (✓/✗/⚠)."""
    lines: list[str] = ["Lumos Environment Report", ""]

    # Device
    lines.append("Device")
    os_info = data.get("os") or {}
    sys_name = os_info.get("system", "")
    release = os_info.get("release", "")
    if sys_name == "Darwin":
        try:
            maj = int(release.split(".")[0]) if release else 0
            os_label = f"macOS {maj}.x" if maj >= 10 else f"macOS {release}"
        except (ValueError, IndexError):
            os_label = f"macOS {release}"
    else:
        os_label = f"{sys_name} {release}"
    lines.append(f"  {'✓' if os_label else '✗'} {os_label}")

    cpu = data.get("cpu") or ""
    if "apple" in cpu.lower() or data.get("os", {}).get("machine") == "arm64":
        lines.append("  ✓ CPU: Apple Silicon")
    elif cpu:
        lines.append(f"  ✓ CPU: {cpu[:50]}")
    else:
        lines.append("  ✗ CPU: unknown")

    ram = data.get("ram_gb")
    if ram is not None:
        lines.append(f"  ✓ RAM: {int(ram)} GB")
    else:
        lines.append("  ✗ RAM: unknown")

    py_ver = (data.get("python") or {}).get("version", "")
    if py_ver:
        lines.append(f"  ✓ Python: {py_ver}")
    else:
        lines.append("  ✗ Python: —")
    lines.append("")

    # Permissions
    lines.append("Permissions")
    perms = data.get("permissions") or {}
    for key, label in [("accessibility", "Accessibility"), ("full_disk_access", "Full Disk Access"), ("screen_recording", "Screen Recording")]:
        val = (perms.get(key) or "unknown").lower()
        if val == "granted":
            lines.append(f"  ✓ {label}")
        elif val == "denied":
            lines.append(f"  ✗ {label}")
        else:
            lines.append(f"  ⚠ {label} (app cannot detect; check System Settings)")
    lines.append("")

    # Capabilities
    lines.append("Capabilities")
    for cap_key, label in [
        ("repo_management", "Repo management"),
        ("test_build", "Test / build"),
        ("file_scanning", "File scanning"),
        ("ui_automation", "UI automation"),
    ]:
        v = caps.get(cap_key, "limited")
        if v == "can":
            lines.append(f"  ✓ {label}")
        elif v == "limited":
            lines.append(f"  ⚠ {label} (limited)")
        else:
            lines.append(f"  ✗ {label}")

    # Erişilebilirlik yoksa "To unlock"; yoksa ui_automation: can ile çelişmez
    perms = data.get("permissions") or {}
    ax = (perms.get("accessibility") or "unknown").lower()
    if ax != "granted":
        lines.append("")
        lines.append("To unlock automation features:")
        lines.append("  1. Enable Accessibility")
        lines.append("  2. Enable Full Disk Access")
        lines.append("  3. Enable Screen Recording")
    else:
        fda = (perms.get("full_disk_access") or "unknown").lower()
        scr = (perms.get("screen_recording") or "unknown").lower()
        if fda != "granted" or scr != "granted":
            lines.append("")
            lines.append("For file scanning or screen capture, check Full Disk Access / Screen Recording in System Settings if needed.")

    return "\n".join(lines)
