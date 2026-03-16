"""
Runtime health check: verify environment is ready before Lumos runs.

Uses only stdlib (pathlib, json, os). Does not modify other modules.
"""
from __future__ import annotations

import json
from pathlib import Path

LUMOS_DIR = Path(".lumos")
LUMOS_LOGS = LUMOS_DIR / "logs"
REPO_LOGS = Path("logs")
WEIGHTS_PATH = LUMOS_DIR / "weights.json"


def run_health_check() -> dict:
    """
    Ensure .lumos/, .lumos/logs/, logs/ exist; weights readable if present;
    log location writable. Returns status dict with overall "ready" or "warning".
    """
    result: dict = {}
    all_ok = True

    # 1 & 2. .lumos/ and .lumos/logs/
    try:
        LUMOS_DIR.mkdir(parents=True, exist_ok=True)
        LUMOS_LOGS.mkdir(parents=True, exist_ok=True)
        result["lumos_dir"] = "ok"
    except OSError as e:
        result["lumos_dir"] = str(e)[:80]
        all_ok = False

    # 3. logs/
    try:
        REPO_LOGS.mkdir(parents=True, exist_ok=True)
        result["logs_dir"] = "ok"
    except OSError as e:
        result["logs_dir"] = str(e)[:80]
        all_ok = False

    # 4. weights readable if present
    if WEIGHTS_PATH.exists():
        try:
            with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
                json.load(f)
            result["weights"] = "ok"
        except (OSError, json.JSONDecodeError) as e:
            result["weights"] = str(e)[:80]
            all_ok = False
    else:
        result["weights"] = "ok"

    # 5. log file can be written (write to .lumos/logs then remove)
    write_ok = False
    if LUMOS_LOGS.exists():
        probe = LUMOS_LOGS / ".health_write_probe"
        try:
            probe.write_text("", encoding="utf-8")
            probe.unlink(missing_ok=True)
            write_ok = True
        except OSError:
            pass
    result["write_test"] = "ok" if write_ok else "unable to write"
    if not write_ok:
        all_ok = False

    result["overall"] = "ready" if all_ok else "warning"
    return result
