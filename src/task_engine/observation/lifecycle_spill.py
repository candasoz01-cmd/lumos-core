"""
EC2-10: optional disk spill for ObservationEngine CLI step lifecycle events.
Best-effort JSONL append; separate from evidence continuity journal.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.log_rotation import DEFAULT_KEEP, DEFAULT_MAX_BYTES, append_jsonl_with_rotation
from core.workspace_contract import allow_write_to_core, logs_dir_path

from task_engine.observation.events import ObservationEvent

OBSERVATION_LIFECYCLE_SCHEMA = "lumos.observation_lifecycle.v1"
OBSERVATION_LIFECYCLE_FILENAME = "observation_lifecycle.jsonl"


def observation_lifecycle_path(base_dir: Path | str) -> Path:
    return logs_dir_path(base_dir) / OBSERVATION_LIFECYCLE_FILENAME


def observation_event_to_spill_record(event: ObservationEvent) -> dict[str, Any]:
    return {
        "schema": OBSERVATION_LIFECYCLE_SCHEMA,
        "ts": datetime.fromtimestamp(event.timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3]
        + "Z",
        "task_id": event.task_id,
        "event_type": event.event_type,
        "step_id": event.step_id,
        "payload": dict(event.payload),
    }


class ObservationLifecycleSpill:
    """Best-effort append-only spill; never raises to caller."""

    def __init__(
        self,
        base_dir: Path | str,
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
        keep: int = DEFAULT_KEEP,
        is_sandbox_mode: bool = False,
    ) -> None:
        self._base_dir = Path(base_dir)
        self._max_bytes = max_bytes
        self._keep = keep
        self._is_sandbox_mode = is_sandbox_mode

    def append(self, event: ObservationEvent) -> dict[str, Any]:
        result: dict[str, Any] = {
            "appended": False,
            "path": str(observation_lifecycle_path(self._base_dir)),
        }
        try:
            path = observation_lifecycle_path(self._base_dir)
            if not allow_write_to_core(
                self._base_dir, path, is_sandbox_mode=self._is_sandbox_mode
            ):
                return result
            record = observation_event_to_spill_record(event)
            append_result = append_jsonl_with_rotation(
                path,
                record,
                max_bytes=self._max_bytes,
                keep=self._keep,
            )
            result.update(append_result)
        except Exception:
            return result
        return result


def read_recent_observation_lifecycle(
    base_dir: Path | str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Read tail of spill file (current file only — v1 bilinçli sınır)."""
    limit_n = max(1, min(int(limit), 200))
    path = observation_lifecycle_path(base_dir)
    if not path.is_file():
        return []
    valid: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get("schema") == OBSERVATION_LIFECYCLE_SCHEMA:
                valid.append(rec)
    except OSError:
        return []
    return valid[-limit_n:]
