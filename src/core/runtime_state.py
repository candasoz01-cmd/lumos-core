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


def _signals_file() -> Path:
    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))
    return base / "feature_signals.json"


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


def _read_signals() -> dict[str, Any]:
    p = _signals_file()
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def mark_feature_signal(key: str) -> None:
    if not (key or "").strip():
        return
    d = _read_signals()
    d[str(key).strip()] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    p = _signals_file()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def get_feature_signal(key: str) -> str | None:
    d = _read_signals()
    v = d.get(key)
    return str(v) if isinstance(v, str) and v.strip() else None


def sync_kando_from_globals(
    last_output: str,
    context: dict,
    pending: dict,
    last_repo_results: list,
    last_repo_index: int,
    *,
    cursor_bridge: dict | None = None,
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
        "cursor_bridge": cursor_bridge if isinstance(cursor_bridge, dict) else None,
    }


def add_runtime_event(event_type: str, summary: str) -> None:
    event = {
        "type": event_type,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _EVENTS.append(event)
    if len(_EVENTS) > _MAX_EVENTS:
        _EVENTS.pop(0)

# lumos:instruction-pipeline safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)
