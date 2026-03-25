"""
Tek canlı panel okuma çıktısı: panel_tasks_server GET /lumos-read-state ve CLI --write.
llm/repl sürecinden bağımsız; disk + ENV + (varsa) kando runtime belleği.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.context_store import context_reuse_state, load_context
from core.panel_bridge_state import build_panel_read_state
from core.runtime_state import get_feature_signal, get_kando_runtime


def _status(flag_active: bool, flag_connected: bool = False) -> str:
    if flag_connected:
        return "connected"
    if flag_active:
        return "active"
    return "planned"


def _build_product_features_state(state: dict[str, Any], kando: dict[str, Any]) -> list[dict[str, Any]]:
    dash = state.get("dashboard") if isinstance(state.get("dashboard"), dict) else {}
    ls = state.get("lumos_status") if isinstance(state.get("lumos_status"), dict) else {}
    pm = state.get("panel_meta") if isinstance(state.get("panel_meta"), dict) else {}
    ctx = load_context()
    events = kando.get("recent_events") or []
    event_types = {str(ev.get("type") or "").strip() for ev in events if isinstance(ev, dict)}
    has_live = bool(ls.get("backend_live_at")) and bool(pm.get("live_state_fresh"))
    has_bridge = isinstance(state.get("dashboard"), dict) and isinstance(state.get("system"), dict) and isinstance(state.get("lumos_status"), dict)
    has_activity = bool(dash.get("recent_events")) and str((dash.get("recent_events") or [{}])[0].get("text") or "") != "Henüz aktivite yok."
    intent_signal_at = get_feature_signal("intent_engine")
    has_intent = bool(intent_signal_at)
    has_repo_search = bool(kando.get("last_repo_query")) or "repo_search" in event_types
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
    bridge_state = "connected" if (has_bridge and has_live) else ("active" if has_bridge else "planned")
    live_state = "connected" if has_live else "in_progress"
    activity_state = "connected" if has_activity else ("active" if bool(dash.get("last_activity")) else "planned")
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
            "durum": _status(has_repo_search),
            "panelde_gorunuyor": True,
            "aciklama": "Repo arama sinyali son repo sorgusu veya arama olayıyla doğrulanır.",
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
            "aciklama": "Panel canlı state endpointinden periyodik veri çekiyor.",
        },
        {
            "key": "panel_bridge",
            "ad": "Panel Bridge",
            "durum": bridge_state,
            "panelde_gorunuyor": True,
            "aciklama": "__LUMOS_READ_STATE__ köprüsü backend payload alanlarıyla doğrulanır.",
        },
        {
            "key": "last_activity_card",
            "ad": "Son Aktivite Kartı",
            "durum": activity_state,
            "panelde_gorunuyor": True,
            "aciklama": "Dashboard Son Aktivite alanı backend olaylarından besleniyor.",
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
        else:
            dash["recent_events"] = [
                {
                    "ts": t,
                    "text": "Henüz aktivite yok.",
                }
            ]
            dash["last_activity"] = t
    state["product_features"] = _build_product_features_state(state, kando)
    return state
