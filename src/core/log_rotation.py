"""
Safe JSONL log rotation for Lumos runtime logs.
Bounds active log size while retaining older records indefinitely. Stdlib only; never raises on missing file.
"""

from __future__ import annotations

import json
import os
import shutil
import hashlib
from pathlib import Path

# Defaults for runtime JSONL logs (evolution, decision_feedback, decision_history)
DEFAULT_MAX_BYTES = 1_000_000  # 1 MB
DEFAULT_KEEP = 3


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


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
    rotated files stay in the active window; older files are archived without expiry.
    The current file is renamed to .1; a new
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
        "files_archived": [],
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
        # Preserve the oldest bytes before reusing its active-window name.
        for n in range(keep, 0, -1):
            dst = _rotated_path(path, n)
            if n == keep and dst.exists():
                archive = path.parent / ".retained-logs" / path.name
                archive.mkdir(parents=True, exist_ok=True, mode=0o700)
                identity = dst.stat()
                digest = _digest(dst)
                retained = archive / f"{identity.st_ino}-{identity.st_mtime_ns}-{digest}.jsonl"
                pending = retained.with_suffix(".pending")
                if not pending.exists() and not retained.exists():
                    with dst.open("rb") as source, pending.open("xb") as target:
                        os.chmod(pending, 0o600)
                        shutil.copyfileobj(source, target)
                        target.flush()
                        os.fsync(target.fileno())
                candidate = retained if retained.exists() else pending
                if _digest(candidate) != digest:
                    raise OSError("Retained log copy incomplete; recovery required")
                # Retry publication/durability without allocating another copy.
                with candidate.open("rb") as target:
                    os.fsync(target.fileno())
                if not retained.exists():
                    os.link(pending, retained)
                if _digest(dst) != digest:
                    raise OSError("Source log changed during archival")
                fd = os.open(archive, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                result["files_archived"].append(str(retained))
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
