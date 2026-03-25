"""
Process-wide Kando runtime (kando.llm ile senkron; llm çağrısı olmadan boş/varsayılan).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_KANDO: dict[str, Any] = {}
_EVENTS: list[dict[str, Any]] = []
_MAX_EVENTS = 30


def _events_file() -> Path:
    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))
    return base / "runtime_events.jsonl"


def _read_file_events() -> list[dict[str, Any]]:
    p = _events_file()
    if not p.is_file():
        return []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for raw in reversed(lines):
        s = raw.strip()
        if not s:
            continue
        try:
            ev = json.loads(s)
        except Exception:
            continue
        if isinstance(ev, dict) and "ts" in ev and "text" in ev:
            out.append(ev)
        if len(out) >= _MAX_EVENTS:
            break
    return out


def sync_kando_from_globals(
    last_output: str,
    context: dict,
    pending: dict,
    last_repo_results: list,
    last_repo_index: int,
) -> None:
    global _KANDO
    ctx = dict(context) if context else {}
    pend = dict(pending) if pending else {}
    nav = {
        "results_count": len(last_repo_results),
        "cursor_index": last_repo_index,
        "has_results": len(last_repo_results) > 0,
    }
    _KANDO = {
        "last_repo_query": (ctx.get("last_repo_query") or ""),
        "pending": pend,
        "last_output_preview": (last_output or "")[:500],
        "context_summary": str(ctx) if ctx else "",
        "repo_nav": nav,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def add_runtime_event(event_type: str, summary: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ev = {
        "ts": ts,
        "type": str(event_type or "event").strip() or "event",
        "text": (str(summary or "").strip() or "Aktivite işlendi.")[:220],
    }
    _EVENTS.insert(0, ev)
    if len(_EVENTS) > _MAX_EVENTS:
        del _EVENTS[_MAX_EVENTS:]
    p = _events_file()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except OSError:
        pass


def get_kando_runtime() -> dict[str, Any]:
    recent_events = _read_file_events() or list(_EVENTS)
    last_activity = recent_events[0]["ts"] if recent_events else None
    if not _KANDO:
        return {
            "last_repo_query": "",
            "pending": {},
            "last_output_preview": "",
            "context_summary": "",
            "repo_nav": {"results_count": 0, "cursor_index": 0, "has_results": False},
            "updated_at": None,
            "recent_events": recent_events,
            "last_activity": last_activity,
        }
    out = dict(_KANDO)
    out["recent_events"] = recent_events
    out["last_activity"] = last_activity
    return out
