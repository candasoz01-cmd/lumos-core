"""
Tek canlı panel okuma çıktısı: panel_tasks_server GET /lumos-read-state ve CLI --write.
llm/repl sürecinden bağımsız; disk + ENV + (varsa) kando runtime belleği.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.context_store import context_reuse_state, load_context, set_last_activity_state
from core.panel_bridge_state import build_panel_read_state
from core.runtime_state import get_feature_signal, get_kando_runtime, mark_feature_signal


def _status(flag_active: bool, flag_connected: bool = False) -> str:
    if flag_connected:
        return "connected"
    if flag_active:
        return "active"
    return "planned"


def _build_product_features_state(state: dict[str, Any], kando: dict[str, Any]) -> list[dict[str, Any]]:
    ls = state.get("lumos_status") if isinstance(state.get("lumos_status"), dict) else {}
    pm = state.get("panel_meta") if isinstance(state.get("panel_meta"), dict) else {}
    ctx = load_context()
    has_live = bool(ls.get("backend_live_at")) and bool(pm.get("live_state_fresh"))
    panel_bridge_sig = get_feature_signal("panel_bridge")
    has_bridge_sig = bool(panel_bridge_sig)
    has_bridge_payload = (
        isinstance(state.get("dashboard"), dict)
        and isinstance(state.get("system"), dict)
        and isinstance(state.get("lumos_status"), dict)
    )
    activity_sig = get_feature_signal("last_activity_card")
    has_activity_sig = bool(activity_sig)
    has_activity = bool(ctx.get("last_activity_has_activity")) is True
    activity_ts = str(ctx.get("last_activity_ts") or "").strip()
    activity_src = str(ctx.get("last_activity_source") or "—").strip()
    intent_signal_at = get_feature_signal("intent_engine")
    has_intent = bool(intent_signal_at)
    repo_search_sig = get_feature_signal("repo_search")
    has_repo_search_sig = bool(repo_search_sig)
    repo_search_query = str(ctx.get("repo_search_last_query") or "").strip()
    repo_search_has_results = bool(ctx.get("repo_search_has_results"))
    repo_search_last_at = str(ctx.get("repo_search_last_at") or "").strip()
    has_repo_search = bool(repo_search_query) or has_repo_search_sig
    context_state = str(ls.get("context_reuse_state") or "boş")
    pending_sig = get_feature_signal("pending_completion")
    has_pending_wait = bool(ctx.get("pending_repo")) is True
    has_pending_complete = bool(pending_sig)
    nav_sig = get_feature_signal("repo_navigation")
    has_nav_sig = bool(nav_sig)
    try:
        nav_results = int(ctx.get("repo_nav_results_count") or 0)
    except Exception:
        nav_results = 0
    try:
        nav_cursor = int(ctx.get("repo_nav_cursor_index") or 0)
    except Exception:
        nav_cursor = 0
    nav_action = str(ctx.get("repo_nav_last_action") or "").strip()
    has_nav_results = nav_results > 0
    has_nav_used = bool(nav_action) or has_nav_sig
    pending_state = "connected" if has_pending_wait else ("active" if has_pending_complete else "planned")
    nav_state = "connected" if (has_nav_results and has_nav_used) else ("active" if (has_nav_results or has_nav_used) else "planned")
    bridge_state = (
        "connected"
        if (has_live and has_bridge_payload and has_bridge_sig)
        else ("active" if (has_bridge_payload or has_bridge_sig) else "planned")
    )
    live_sig = get_feature_signal("live_backend_state")
    live_state = "connected" if (has_live and live_sig) else ("active" if live_sig else "planned")
    activity_state = "connected" if (has_live and has_activity and has_activity_sig) else ("active" if has_activity else "planned")
    return [
        {
            "key": "intent_engine",
            "ad": "Intent Engine",
            "durum": "connected" if (has_intent and has_live) else ("active" if has_intent else "planned"),
            "panelde_gorunuyor": True,
            "aciklama": ("Kalıcı kullanım sinyali: " + intent_signal_at) if has_intent else "Kullanım sinyali yok.",
        },
        {
            "key": "repo_search",
            "ad": "Repo Search",
            "durum": "connected" if (has_repo_search and repo_search_has_results and has_repo_search_sig) else ("active" if has_repo_search else "planned"),
            "panelde_gorunuyor": True,
            "aciklama": (
                f"Son sorgu: {repo_search_query or '—'}; sonuç: {'var' if repo_search_has_results else 'yok'}; "
                + (f"zaman: {repo_search_last_at or '—'}")
            ),
        },
        {
            "key": "context_reuse",
            "ad": "Context Reuse",
            "durum": "connected" if context_state == "aktif" else ("active" if context_state == "mevcut" else "planned"),
            "panelde_gorunuyor": True,
            "aciklama": f"Context durumu: {context_state}. Son repo sorgusu kalıcı store üzerinden okunur.",
        },
        {
            "key": "pending_completion",
            "ad": "Pending Completion",
            "durum": pending_state,
            "panelde_gorunuyor": True,
            "aciklama": ("Bekleyen repo sorgusu var." if has_pending_wait else (("Kalıcı sinyal: " + pending_sig) if pending_sig else "Sinyal yok.")),
        },
        {
            "key": "repo_navigation",
            "ad": "Repo Select/Next/Prev",
            "durum": nav_state,
            "panelde_gorunuyor": True,
            "aciklama": (
                f"Sonuç: {nav_results}, imleç: {nav_cursor + 1 if nav_results else 0}/{nav_results}. "
                + (("Kalıcı sinyal: " + nav_sig) if nav_sig else ("Son aksiyon: " + (nav_action or "—")))
            ),
        },
        {
            "key": "live_backend_state",
            "ad": "Live Backend State",
            "durum": live_state,
            "panelde_gorunuyor": True,
            "aciklama": ("Kalıcı sağlık sinyali: " + live_sig) if live_sig else "Sağlık sinyali yok.",
        },
        {
            "key": "panel_bridge",
            "ad": "Panel Bridge",
            "durum": bridge_state,
            "panelde_gorunuyor": True,
            "aciklama": ("Kalıcı sinyal: " + panel_bridge_sig) if panel_bridge_sig else "Sinyal yok.",
        },
        {
            "key": "last_activity_card",
            "ad": "Son Aktivite Kartı",
            "durum": activity_state,
            "panelde_gorunuyor": True,
            "aciklama": (
                f"Kaynak: {activity_src}; zaman: {activity_ts or '—'}; "
                + (("Kalıcı sinyal: " + activity_sig) if activity_sig else "Sinyal yok.")
            ),
        },
    ]


def get_live_read_state(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root if repo_root is not None else Path(__file__).resolve().parent.parent.parent
    state = build_panel_read_state(repo_root=repo)
    t = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["panel_meta"] = {
        "server_time_utc": t,
        "live_state_fresh": True,
    }
    ls = state.get("lumos_status")
    if isinstance(ls, dict):
        ls["backend_live_at"] = t
        ls["backend_runtime_ok"] = True
        ls["backend_live_signal_at"] = t
        ls["panel_bridge_payload_ok"] = bool(
            isinstance(state.get("dashboard"), dict)
            and isinstance(state.get("system"), dict)
            and isinstance(state.get("sandbox"), dict)
        )
    mark_feature_signal("live_backend_state")
    if isinstance(ls, dict) and ls.get("panel_bridge_payload_ok"):
        mark_feature_signal("panel_bridge")
        ls["panel_bridge_signal_at"] = get_feature_signal("panel_bridge")
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
    state["product_features"] = _build_product_features_state(state, kando)
    return state
