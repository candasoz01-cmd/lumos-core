from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _context_file() -> Path:
    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))
    return base / "context.json"


def context_reuse_gate() -> dict[str, str | bool]:
    p = _context_file()
    try:
        capability = os.access(str(p.parent), os.W_OK)
    except Exception:
        capability = False
    if not capability:
        return {"capability": False, "health": "fail", "mode": "disabled"}
    if not p.is_file():
        return {"capability": True, "health": "ok", "mode": "persistent"}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {"capability": True, "health": "ok", "mode": "persistent"}
    except Exception:
        pass
    return {"capability": True, "health": "fail", "mode": "session_only"}


def load_context() -> dict[str, Any]:
    p = _context_file()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_context(ctx: dict[str, Any]) -> dict[str, Any]:
    p = _context_file()
    out = dict(ctx) if isinstance(ctx, dict) else {}
    if "updated_at" not in out:
        out["updated_at"] = _now_iso()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return out


def update_last_repo_query(query: str) -> dict[str, Any]:
    ctx = load_context()
    ctx["last_repo_query"] = (query or "").strip()
    ctx["updated_at"] = _now_iso()
    ctx.pop("pending_repo", None)
    ctx.pop("pending_repo_since", None)
    if "reuse_active_at" in ctx:
        ctx.pop("reuse_active_at", None)
    return save_context(ctx)


def mark_reuse_active() -> dict[str, Any]:
    ctx = load_context()
    if (ctx.get("last_repo_query") or "").strip():
        ctx["reuse_active_at"] = _now_iso()
        ctx["updated_at"] = _now_iso()
        return save_context(ctx)
    return ctx


def set_pending_repo_waiting(waiting: bool) -> dict[str, Any]:
    ctx = load_context()
    if waiting:
        ctx["pending_repo"] = True
        ctx["pending_repo_since"] = _now_iso()
    else:
        ctx.pop("pending_repo", None)
        ctx.pop("pending_repo_since", None)
    ctx["updated_at"] = _now_iso()
    return save_context(ctx)


def set_repo_navigation_state(*, results_count: int, cursor_index: int, action: str | None = None) -> dict[str, Any]:
    ctx = load_context()
    try:
        rc = int(results_count)
    except Exception:
        rc = 0
    try:
        ci = int(cursor_index)
    except Exception:
        ci = 0
    if rc < 0:
        rc = 0
    if ci < 0:
        ci = 0
    ctx["repo_nav_results_count"] = rc
    ctx["repo_nav_cursor_index"] = ci
    ctx["repo_nav_updated_at"] = _now_iso()
    if action:
        ctx["repo_nav_last_action"] = str(action)
        ctx["repo_nav_last_action_at"] = _now_iso()
    ctx["updated_at"] = _now_iso()
    return save_context(ctx)


def set_repo_search_state(*, query: str, has_results: bool) -> dict[str, Any]:
    ctx = load_context()
    q = (query or "").strip()
    ctx["repo_search_last_query"] = q
    ctx["repo_search_has_results"] = bool(has_results)
    ctx["repo_search_last_at"] = _now_iso()
    ctx["updated_at"] = _now_iso()
    return save_context(ctx)


def set_last_activity_state(*, has_activity: bool, ts: str | None, source: str) -> dict[str, Any]:
    ctx = load_context()
    ctx["last_activity_has_activity"] = bool(has_activity)
    ctx["last_activity_ts"] = str(ts or "").strip() or None
    ctx["last_activity_source"] = (source or "").strip() or "—"
    ctx["last_activity_updated_at"] = _now_iso()
    ctx["updated_at"] = _now_iso()
    return save_context(ctx)


def set_panel_api_health(*, ok: bool, error: str | None = None, ts: str | None = None) -> dict[str, Any]:
    ctx = load_context()
    t = str(ts or "").strip() or _now_iso()
    if ok:
        ctx["panel_api_last_ok_at"] = t
        ctx.pop("panel_api_last_error_at", None)
        ctx.pop("panel_api_last_error", None)
    else:
        ctx["panel_api_last_error_at"] = t
        ctx["panel_api_last_error"] = (str(error or "").strip() or "—")[:240]
    ctx["updated_at"] = _now_iso()
    return save_context(ctx)


def context_reuse_state(ctx: dict[str, Any] | None = None) -> str:
    c = ctx if isinstance(ctx, dict) else load_context()
    if not (c.get("last_repo_query") or "").strip():
        return "boş"
    if (c.get("reuse_active_at") or "").strip():
        return "aktif"
    return "mevcut"
