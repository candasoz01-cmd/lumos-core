"""
Bridge sonrası yürütme özeti (Cursor CLI yok).
task / patch execution_mode için last_cursor_executor.json yazar.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run_after_bridge(lumos_base: Path, exe: Any) -> None:
    """execution_mode task veya patch ise disk kanıtı üret."""
    mode = getattr(exe, "execution_mode", "") or ""
    if mode not in ("task", "patch"):
        return
    d = lumos_base / "cursor_bridge"
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "kando.cursor_executor.v1",
        "execution_mode": mode,
        "execution": (getattr(exe, "constraints", None) or {}).get("execution"),
    }
    (d / "last_cursor_executor.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_cursor_apply(
    instruction: str,
    *,
    target_relative: str = "",
) -> dict[str, Any]:
    """Kullanılmıyor; cursor --apply yok."""
    return {"ran": False, "reason": "cursor_cli_removed"}


def run_from_execution_packet(exe: Any) -> dict[str, Any]:
    return {"ran": False, "reason": "cursor_cli_removed"}
