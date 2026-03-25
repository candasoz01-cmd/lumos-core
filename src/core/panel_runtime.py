"""
Tek canlı panel okuma çıktısı: panel_tasks_server GET /lumos-read-state ve CLI --write.
llm/repl sürecinden bağımsız; disk + ENV + (varsa) kando runtime belleği.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.context_store import context_reuse_state, load_context, set_last_activity_state
from core.product_features import build_product_features
from core.panel_bridge_state import build_panel_read_state
from core.runtime_state import get_feature_signal, get_kando_runtime, mark_feature_signal


def _status(flag_active: bool, flag_connected: bool = False) -> str:
    if flag_connected:
        return "connected"
    if flag_active:
        return "active"
    return "planned"


def _live_backend_cache_file() -> Path:
    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))
    return base / "live_read_state_cache.json"


def _live_backend_capability_ok(repo: Path) -> bool:
    try:
        return repo.exists() and repo.is_dir()
    except Exception:
        return False


def _read_cached_live_state() -> dict[str, Any] | None:
    p = _live_backend_cache_file()
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def _write_cached_live_state(state: dict[str, Any]) -> None:
    p = _live_backend_cache_file()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def get_live_read_state(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root if repo_root is not None else Path(__file__).resolve().parent.parent.parent
    t = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not _live_backend_capability_ok(repo):
        cached = _read_cached_live_state() or {}
        cached["panel_meta"] = {
            "server_time_utc": t,
            "live_state_fresh": False,
        }
        ls0 = cached.get("lumos_status")
        if not isinstance(ls0, dict):
            ls0 = {}
            cached["lumos_status"] = ls0
        ls0["backend_runtime_ok"] = False
        ls0["backend_live_at"] = ls0.get("backend_live_at") or "—"
        cached["product_features"] = build_product_features(cached)
        return cached
    try:
        state = build_panel_read_state(repo_root=repo)
        live_backend_ok = True
    except Exception:
        state = _read_cached_live_state() or {}
        live_backend_ok = False
    state["panel_meta"] = {
        "server_time_utc": t,
        "live_state_fresh": live_backend_ok,
    }
    ls = state.get("lumos_status")
    if isinstance(ls, dict):
        if live_backend_ok:
            ls["backend_live_at"] = t
        ls["backend_runtime_ok"] = live_backend_ok
        if live_backend_ok:
            ls["backend_live_signal_at"] = t
        ls["panel_bridge_payload_ok"] = bool(
            isinstance(state.get("dashboard"), dict)
            and isinstance(state.get("system"), dict)
            and isinstance(state.get("sandbox"), dict)
        )
    if live_backend_ok:
        mark_feature_signal("live_backend_state")
    if isinstance(ls, dict) and ls.get("panel_bridge_payload_ok"):
        mark_feature_signal("panel_bridge")
        ls["panel_bridge_signal_at"] = get_feature_signal("panel_bridge")
    mark_feature_signal("panel_api")
    kando = get_kando_runtime()
    ctx = load_context()
    if isinstance(ls, dict):
        ls["last_activity"] = kando.get("last_activity")
        ls["context_reuse_state"] = context_reuse_state(ctx)
        ls["context_last_repo_query"] = (ctx.get("last_repo_query") or "—")
    state["internal_events"] = kando.get("recent_events") or []
    dash = state.get("dashboard")
    logs = state.get("logs")
    if isinstance(dash, dict):
        if isinstance(logs, dict) and (logs.get("log_items") or []):
            last = logs["log_items"][-1]
            dash["recent_events"] = [
                {
                    "ts": last.get("ts") or t,
                    "text": str(last.get("text") or "")[:300],
                }
            ]
            dash["last_activity"] = last.get("ts") or t
            set_last_activity_state(has_activity=True, ts=dash["last_activity"], source="logs")
            mark_feature_signal("last_activity_card")
        else:
            dash["recent_events"] = [
                {
                    "ts": t,
                    "text": "Henüz aktivite yok.",
                }
            ]
            dash["last_activity"] = t
            set_last_activity_state(has_activity=False, ts=None, source="—")
    state["product_features"] = build_product_features(state)
    if live_backend_ok:
        _write_cached_live_state(state)
    return state
