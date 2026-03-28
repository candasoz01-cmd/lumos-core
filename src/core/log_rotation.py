"""
Safe JSONL log rotation for Lumos runtime logs.
Prevents unlimited growth while preserving old records. Stdlib only; never raises on missing file.
"""

from __future__ import annotations

import json
from pathlib import Path

# Defaults for runtime JSONL logs (evolution, decision_feedback, decision_history)
DEFAULT_MAX_BYTES = 1_000_000  # 1 MB
DEFAULT_KEEP = 3


def _rotated_path(base: Path, n: int) -> Path:
    """Path for the n-th rotated file (e.g. base.jsonl -> base.jsonl.1)."""
    return Path(str(base) + f".{n}")


def rotate_jsonl_log(
    path: Path | str,
    max_bytes: int,
    keep: int = 3,
) -> dict:
    """
    Rotate the JSONL log at path if its size is >= max_bytes.

    Rotation: current -> .1, .1 -> .2, .2 -> .3, etc. Only the newest `keep`
    rotated files are retained. The current file is renamed to .1; a new
    empty current file is not created (next append will create it).

    Never raises on missing file. Returns a dict with keys:
      - rotated: bool
      - size_before: int (0 if missing)
      - files_removed: list of str (paths removed)
      - error: str | None (if something went wrong)
    """
    path = Path(path).resolve()
    result: dict = {
        "rotated": False,
        "size_before": 0,
        "files_removed": [],
        "error": None,
    }
    if max_bytes <= 0:
        max_bytes = DEFAULT_MAX_BYTES
    if keep <= 0:
        return result
    try:
        if not path.exists() or not path.is_file():
            return result
        size = path.stat().st_size
        result["size_before"] = size
        if size < max_bytes:
            return result
        # Rotate from highest index down: remove .keep, then .(k-1) -> .k, ..., current -> .1
        for n in range(keep, 0, -1):
            dst = _rotated_path(path, n)
            if n == keep and dst.exists():
                dst.unlink()
                result["files_removed"].append(str(dst))
            src = path if n == 1 else _rotated_path(path, n - 1)
            if src.exists():
                src.rename(dst)
        result["rotated"] = True
    except OSError as e:
        result["error"] = str(e)
    return result


def append_jsonl_with_rotation(
    path: Path | str,
    record: dict,
    max_bytes: int = DEFAULT_MAX_BYTES,
    keep: int = DEFAULT_KEEP,
) -> dict:
    """
    Append one JSON line to the JSONL file at path, rotating first if size >= max_bytes.

    If the file does not exist, it is created. Uses UTF-8. Never raises on
    missing file. Does not parse or rewrite existing content; only renames
    files during rotation.

    Returns a dict with keys:
      - appended: bool
      - rotated: bool (whether rotation was performed before append)
      - path: str
      - error: str | None
    """
    path = Path(path).resolve()
    result: dict = {
        "appended": False,
        "rotated": False,
        "path": str(path),
        "error": None,
    }
    if max_bytes <= 0:
        max_bytes = DEFAULT_MAX_BYTES
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.is_file() and path.stat().st_size >= max_bytes:
            rot = rotate_jsonl_log(path, max_bytes, keep)
            result["rotated"] = rot.get("rotated", False)
            if rot.get("error"):
                result["error"] = rot["error"]
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
        result["appended"] = True
    except OSError as e:
        result["error"] = str(e)
    except (TypeError, ValueError) as e:
        result["error"] = str(e)
    return result
