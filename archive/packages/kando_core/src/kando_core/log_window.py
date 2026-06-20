"""
Bounded recent-history reading for JSONL log files.
Learning modules use this to avoid scanning full log files.
Stdlib only; never raises on missing or malformed files.
"""

from __future__ import annotations

import json
from pathlib import Path


def read_recent_jsonl_records(path: Path | str, limit: int) -> list[dict]:
    """
    Read only the most recent records from a JSONL file.

    - Returns at most `limit` records in original chronological order.
    - Missing file -> empty list.
    - Malformed JSON lines are ignored.
    - Only dict records are returned; non-dict parsed values are skipped.
    - Never raises.
    """
    path = Path(path).resolve()
    if limit <= 0:
        return []
    if not path.exists():
        return []
    records: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                records.append(obj)
                if len(records) > limit:
                    records = records[-limit:]
    except OSError:
        return []
    return records


def read_recent_jsonl_matching(
    path: Path | str,
    limit: int,
    required_keys: list[str] | None = None,
) -> list[dict]:
    """
    Read only the most recent records from a JSONL file, optionally
    requiring that each record contain all of `required_keys`.

    - Returns at most `limit` records in original chronological order.
    - If `required_keys` is None or empty, same as read_recent_jsonl_records.
    - Missing file -> empty list.
    - Malformed JSON lines are ignored.
    - Never raises.
    """
    path = Path(path).resolve()
    if limit <= 0:
        return []
    if not path.exists():
        return []
    keys_set = set(required_keys) if required_keys else None
    records: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                if keys_set and not keys_set.issubset(obj.keys()):
                    continue
                records.append(obj)
                if len(records) > limit:
                    records = records[-limit:]
    except OSError:
        return []
    return records
