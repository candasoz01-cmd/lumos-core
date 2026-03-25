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


def context_reuse_state(ctx: dict[str, Any] | None = None) -> str:
    c = ctx if isinstance(ctx, dict) else load_context()
    if not (c.get("last_repo_query") or "").strip():
        return "boş"
    if (c.get("reuse_active_at") or "").strip():
        return "aktif"
    return "mevcut"
