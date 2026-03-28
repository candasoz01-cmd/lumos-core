"""Patch sonrası zorunlu doğrulama: her zaman python -m py_compile hedef; istenirse VERIFY: komutu."""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


def repo_root_for_verify() -> Path:
    env = (os.environ.get("LUMOS_REPO_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    base = os.environ.get("LUMOS_BASE_DIR", ".lumos")
    p = Path(base)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    if p.name == ".lumos":
        return p.parent
    return Path.cwd().resolve()


def mandatory_py_compile(
    target: Path,
    *,
    cwd: Path | None = None,
) -> tuple[bool, str]:
    """python -m py_compile <target> — tek dosya apply sonrası zorunlu."""
    root = cwd or repo_root_for_verify()
    tp = target.resolve()
    try:
        rr = subprocess.run(
            [sys.executable, "-m", "py_compile", str(tp)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60.0,
        )
        out = ((rr.stdout or "") + (rr.stderr or "")).strip()
        ok = rr.returncode == 0
        msg = f"py_compile exit={rr.returncode}"
        if out:
            msg += f" | {out[:1500]}"
        return ok, msg
    except Exception as e:
        return False, f"py_compile_error: {e!s}"[:2000]


def run_integration_verify_command(
    verify_cmd: str,
    *,
    cwd: Path | None = None,
    timeout_sec: float = 120.0,
) -> tuple[bool, str]:
    """VERIFY: satırı (pytest vb.); cwd genelde repo kökü."""
    root = cwd or repo_root_for_verify()
    cmd = (verify_cmd or "").strip()
    if not cmd:
        return True, ""
    try:
        rr = subprocess.run(
            shlex.split(cmd),
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        out = ((rr.stdout or "") + (rr.stderr or "")).strip()
        ok = rr.returncode == 0
        msg = f"verify_cmd exit={rr.returncode}"
        if out:
            msg += f" | {out[:2000]}"
        return ok, msg
    except Exception as e:
        return False, f"verify_cmd_error: {e!s}"[:2000]


def run_post_apply_verify(
    target: Path,
    verify_cmd: str | None,
    *,
    cwd: Path | None = None,
    timeout_sec: float = 120.0,
) -> tuple[bool, str]:
    """
    1) Zorunlu: python -m py_compile <target>.
    2) VERIFY: varsa ek komut (repo kökünde).

    Dönüş: (ok, özet mesaj).
    """
    root = cwd or repo_root_for_verify()
    ok, pmsg = mandatory_py_compile(target, cwd=root)
    if not ok:
        return False, pmsg

    cmd = (verify_cmd or "").strip()
    if not cmd:
        return True, pmsg

    ok2, vmsg = run_integration_verify_command(cmd, cwd=root, timeout_sec=timeout_sec)
    if not ok2:
        return False, f"{pmsg} | {vmsg}"

    return True, f"{pmsg} | {vmsg}"
