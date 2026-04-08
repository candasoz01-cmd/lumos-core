"""
Shell / terminal: beyaz liste argv[0]; «komut çalıştır:» veya tek satır pwd/echo/… .

stderr ayrı alan; onay beklerken gate_blocks_execution çalıştırmaz.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kando_runtime.executor_gate import gate_blocks_execution

_ARGV0_WHITELIST = frozenset({"echo", "pwd", "date", "uname", "true", "false"})
_SHELL_INJECTION_RE = re.compile(r"[;&|`$()<>\n\r]")

_CMD_RE = re.compile(
    r"(?:komut|command)\s*(?:çalıştır|calistir|run)\s*[:：]\s*(.+)$|^run\s*[:：]\s*(.+)$",
    re.I | re.M,
)
# Tek satır: yalnızca beyaz listede tek komut (+ argümanlar)
_BARE_LINE = re.compile(
    r"^\s*(echo|pwd|date|uname|true|false)\b(.*)$",
    re.I,
)


def _tokens_safe(parts: list[str]) -> bool:
    for p in parts:
        if not p or _SHELL_INJECTION_RE.search(p):
            return False
    return True


def _argv0_ok(name: str) -> bool:
    n = (name or "").strip().lower()
    if not n or "/" in n or "\\" in n or n.startswith("."):
        return False
    return n in _ARGV0_WHITELIST


def _parse_shell_parts(text: str) -> list[str] | None:
    t = (text or "").strip()
    if not t:
        return None
    cm = _CMD_RE.search(t)
    if cm:
        raw = next((g.strip() for g in cm.groups() if g), "")
        parts = raw.split()
        return parts if parts else None
    m = _BARE_LINE.match(t)
    if not m:
        return None
    cmd = m.group(1).strip().lower()
    rest = (m.group(2) or "").strip()
    parts = [cmd]
    if rest:
        parts.extend(rest.split())
    return parts


def _safe_workspace_dir(repo_root: Path) -> Path:
    d = (repo_root / ".lumos" / "system_workspace").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_path(repo_root: Path) -> Path:
    p = repo_root / ".lumos" / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p / "shell_executor.log"


def _append_log(repo_root: Path, line: str) -> str:
    lp = _log_path(repo_root)
    ts = datetime.now(timezone.utc).isoformat()
    with lp.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")
    return str(lp.resolve())


def run(task_ctx: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    if task_ctx.get("mock"):
        return {
            "outcome": "applied",
            "result": "mock_ok",
        }
    text = str(task_ctx.get("text") or "").strip()
    out = task_ctx.get("out") or {}
    repo_root = repo_root.resolve()

    base = {
        "executor": "shell_executor",
    }

    if gate_blocks_execution(out):
        return {
            **base,
            "executed": False,
            "status": "rejected",
            "outcome_tr": "reddedildi",
            "action": "blocked_by_gate",
            "stdout": "",
            "stderr": "",
            "detail": "Onay veya netleştirme gerekli; shell yürütücüsü çalıştırılmadı.",
        }

    if not text:
        return {
            **base,
            "executed": False,
            "status": "skipped",
            "outcome_tr": "reddedildi",
            "action": "none",
            "stdout": "",
            "stderr": "",
            "detail": "Boş komut",
        }

    parts = _parse_shell_parts(text)
    if not parts:
        return {
            **base,
            "executed": False,
            "status": "skipped",
            "outcome_tr": "reddedildi",
            "action": "unhandled",
            "stdout": "",
            "stderr": "",
            "detail": "Shell komutu tanınmadı (ör. «pwd» veya «komut çalıştır: pwd»).",
        }
    if not _tokens_safe(parts):
        return {
            **base,
            "executed": False,
            "status": "rejected",
            "outcome_tr": "reddedildi",
            "action": "command",
            "stdout": "",
            "stderr": "",
            "detail": "Komutta izin verilmeyen karakter.",
        }
    bin0 = parts[0]
    if not _argv0_ok(bin0):
        return {
            **base,
            "executed": False,
            "status": "rejected",
            "outcome_tr": "reddedildi",
            "action": "command",
            "stdout": "",
            "stderr": "",
            "detail": f"İzin verilmeyen komut (whitelist dışı): {bin0!r}",
        }
    cwd = _safe_workspace_dir(repo_root)
    try:
        cp = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=12,
            cwd=str(cwd),
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return {
            **base,
            "executed": False,
            "status": "rejected",
            "outcome_tr": "reddedildi",
            "action": "command",
            "stdout": "",
            "stderr": "",
            "detail": str(e),
        }

    out_txt = (cp.stdout or "").rstrip()
    err_txt = (cp.stderr or "").rstrip()
    ok = cp.returncode == 0
    _append_log(
        repo_root,
        f"CMD {' '.join(parts)} exit={cp.returncode} out={(out_txt or '-')[:200]} err={(err_txt or '-')[:120]}",
    )
    detail = f"exit={cp.returncode}"
    if out_txt:
        detail += f" stdout={out_txt[:2000]}"
    if err_txt:
        detail += f" stderr={err_txt[:2000]}"
    return {
        **base,
        "executed": True,
        "status": "success" if ok else "rejected",
        "outcome_tr": "başarılı" if ok else "reddedildi",
        "action": "command",
        "stdout": out_txt,
        "stderr": err_txt,
        "returncode": cp.returncode,
        "detail": detail.strip(),
        "cwd": str(cwd),
    }
