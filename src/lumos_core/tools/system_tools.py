"""
Minimal read-only system/device tools for Lumos v1 (personal use).
Read-only only: no file deletion, modification, or execution of user-supplied paths/commands.
All tools use the current working directory only; no user-supplied paths. Local inspection only.
Supported: current working directory, list files in current directory, Python version,
disk usage summary, basic system info (OS/platform). Returned strings are short, clear,
human-friendly; never raw tracebacks or exception text.
"""
from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path
from typing import Callable

# Turkish and English phrases that map to a supported read-only tool (order: more specific first).
# Each tuple: (list of substring patterns, tool_key).
_READONLY_TOOL_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    # Current working directory
    (
        ("hangi klasördeyim", "neredeyim", "şu an neredeyim", "cwd", "pwd", "current directory", "hangi dizindeyim"),
        "cwd",
    ),
    # List files in current directory
    (
        (
            "bu klasörde ne var",
            "buradaki dosyalar",
            "buradaki dosyaları göster",
            "dosyaları listele",
            "dosyaları göster",
            "listele",
            "list files",
            "bu dizinde ne var",
            "içeriği göster",
        ),
        "list_dir",
    ),
    # Python version
    (
        ("python versiyonu", "python version", "python kaç", "python sürümü", "py version"),
        "python_version",
    ),
    # Disk usage
    (
        (
            "diskte ne kadar yer var",
            "disk kullanımı",
            "disk usage",
            "yer var mı",
            "ne kadar yer var",
            "diskte yer",
        ),
        "disk_usage",
    ),
    # System info
    (
        (
            "sistem bilgisi",
            "sistem bilgisi ver",
            "system info",
            "platform",
            "işletim sistemi",
            "os bilgisi",
        ),
        "system_info",
    ),
]

# User-facing messages: short, clear, Lumos-prefixed when it's an error/limit. No exception text.
_NOT_AVAILABLE_MSG = "Lumos: Bu özellik şu an kullanılamıyor."
_PERMISSION_DENIED_MSG = "Lumos: Bu klasör için listeleme izni yok."
_LIST_DIR_CAP = 200  # max items to list; avoids flooding output; read-only
_MAX_OUTPUT_LEN = 2000  # cap total tool output; avoid unbounded response
_TRUNCATE_SUFFIX = "\n... (çıktı kısaltıldı)"


def _cap_output(text: str) -> str:
    """Ensure tool output never exceeds _MAX_OUTPUT_LEN; append short suffix if truncated."""
    if not text or len(text) <= _MAX_OUTPUT_LEN:
        return text
    return text[:_MAX_OUTPUT_LEN].rstrip() + _TRUNCATE_SUFFIX


def _run_cwd() -> str:
    """Return current working directory. Read-only; no user-supplied path."""
    try:
        path = str(Path.cwd())
        return f"Bulunduğunuz klasör:\n{path}"
    except Exception:
        return _NOT_AVAILABLE_MSG  # never leak exception text


def _run_list_dir() -> str:
    """List contents of current directory. Read-only; no modification. Capped for safety."""
    try:
        p = Path.cwd()
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        if not items:
            return "Bu klasördeki öğeler:\n  (bu klasör boş)"
        lines = [f"  {x.name}/" if x.is_dir() else f"  {x.name}" for x in items[: _LIST_DIR_CAP]]
        body = "\n".join(lines)
        if len(items) > _LIST_DIR_CAP:
            body += f"\n  (... ilk {_LIST_DIR_CAP} öğe; toplam {len(items)})"
        return f"Bu klasördeki öğeler:\n{body}"
    except PermissionError:
        return _PERMISSION_DENIED_MSG
    except Exception:
        return _NOT_AVAILABLE_MSG  # never leak exception text to user


def _run_python_version() -> str:
    """Return Python version. Read-only."""
    ver = sys.version.split()[0] if sys.version else str(sys.version_info[:3])
    return f"Python sürümü: {ver}"


def _run_disk_usage() -> str:
    """Return disk usage for current drive. Read-only."""
    try:
        cwd = Path.cwd()
        total, used, free = shutil.disk_usage(cwd)
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        return (
            "Disk kullanımı (bu sürücü):\n"
            f"  Toplam: {total_gb:.1f} GB\n"
            f"  Kullanılan: {used_gb:.1f} GB\n"
            f"  Boş: {free_gb:.1f} GB"
        )
    except Exception:
        return _NOT_AVAILABLE_MSG  # never leak exception text


def _run_system_info() -> str:
    """Return basic system info (OS, machine, platform). Read-only."""
    try:
        return (
            "Sistem bilgisi:\n"
            f"  İşletim sistemi: {platform.system()} {platform.release()}\n"
            f"  Makine: {platform.machine()}\n"
            f"  Platform: {platform.platform()}"
        )
    except Exception:
        return _NOT_AVAILABLE_MSG  # never leak exception text


_TOOL_RUNNERS: dict[str, Callable[[], str]] = {
    "cwd": _run_cwd,
    "list_dir": _run_list_dir,
    "python_version": _run_python_version,
    "disk_usage": _run_disk_usage,
    "system_info": _run_system_info,
}


def try_handle_readonly_tool(message: str) -> str | None:
    """
    If the message matches a supported read-only tool intent, run it and return the result.
    Otherwise return None (caller should route to provider or tool_not_implemented).
    Read-only hardening: message is used only for pattern matching; never passed to Path(),
    open(), subprocess, or any filesystem/command execution. All runners use Path.cwd() only.
    Returned strings are capped in length and never contain raw exception text.
    """
    msg = (message or "").strip()
    if not msg:
        return None
    lower = msg.lower()
    for patterns, tool_key in _READONLY_TOOL_PATTERNS:
        if any(p in lower for p in patterns):
            runner = _TOOL_RUNNERS.get(tool_key)
            if runner:
                return _cap_output(runner())
            return _NOT_AVAILABLE_MSG
    return None
