from __future__ import annotations

import os
from importlib.util import find_spec
from typing import Any

from core.context_store import load_context
from core.runtime_state import get_feature_signal


def _capability_import(module: str, attr: str | None = None) -> bool:
    # Capability check MUST NOT execute imports (circular risk).
    # `attr` is kept for call-site readability; we only validate module presence here.
    try:
        return find_spec(module) is not None
    except Exception:
        return False


def _can_write_base_dir() -> bool:
    base = os.environ.get("LUMOS_BASE_DIR", ".lumos")
    parent = os.path.abspath(os.path.join(base, os.pardir))
    try:
        return os.access(parent, os.W_OK)
    except Exception:
        return False


def build_product_features(state: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Tek kaynak ürün feature durumu builder'ı.
    Çıktı: panelin direkt render ettiği `product_features` listesi.
    """
    ls = state.get("lumos_status") if isinstance(state.get("lumos_status"), dict) else {}
    pm = state.get("panel_meta") if isinstance(state.get("panel_meta"), dict) else {}
    ctx = load_context()

    has_live = bool(ls.get("backend_live_at")) and bool(pm.get("live_state_fresh"))

    # --- panel_api ---
    panel_api_cap = True
    panel_api_sig = get_feature_signal("panel_api")
    panel_api_last_ok = str(ctx.get("panel_api_last_ok_at") or "").strip()
    panel_api_last_err = str(ctx.get("panel_api_last_error_at") or "").strip()
    panel_api_err = str(ctx.get("panel_api_last_error") or "").strip()
    panel_api_connected = bool(panel_api_last_ok) and (not panel_api_last_err)
    panel_api_active = bool(panel_api_last_ok) and bool(panel_api_last_err)
    panel_api_health = "ok" if panel_api_connected else ("fail" if panel_api_active else "unknown")
    panel_api_state = "planned" if not panel_api_cap else ("connected" if panel_api_connected else ("active" if panel_api_active else "planned"))

    # --- intent_engine ---
    intent_cap = _capability_import("kando.intent_engine", "engine")
    intent_sig = get_feature_signal("intent_engine")
    intent_health = "ok" if intent_cap else "fail"
    intent_state = (
        "planned"
        if not intent_cap
        else ("connected" if (has_live and intent_sig) else ("active" if intent_sig else "planned"))
    )

    # --- repo_search ---
    repo_search_cap = _capability_import("kando.tools", "repo_search")
    repo_search_sig = get_feature_signal("repo_search")
    repo_search_query = str(ctx.get("repo_search_last_query") or "").strip()
    repo_search_has_results = bool(ctx.get("repo_search_has_results"))
    repo_search_last_at = str(ctx.get("repo_search_last_at") or "").strip()
    has_repo_search = bool(repo_search_query) or bool(repo_search_sig)
    repo_search_health = "ok" if repo_search_cap else "fail"
    repo_search_state = (
        "planned"
        if not repo_search_cap
        else (
        "connected"
        if (has_repo_search and repo_search_has_results and repo_search_sig)
        else ("active" if has_repo_search else "planned")
        )
    )

    # --- context_reuse ---
    context_cap = _can_write_base_dir()
    context_state = str(ls.get("context_reuse_state") or "boş")
    context_health = "ok" if context_cap else "fail"
    context_feat_state = (
        "planned"
        if not context_cap
        else ("connected" if context_state == "aktif" else ("active" if context_state == "mevcut" else "planned"))
    )

    # --- pending_completion ---
    pending_sig = get_feature_signal("pending_completion")
    has_pending_wait = bool(ctx.get("pending_repo")) is True
    has_pending_complete = bool(pending_sig)
    pending_state = "connected" if has_pending_wait else ("active" if has_pending_complete else "planned")

    # --- repo_navigation ---
    nav_sig = get_feature_signal("repo_navigation")
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
    has_nav_used = bool(nav_action) or bool(nav_sig)
    nav_state = (
        "connected"
        if (has_nav_results and has_nav_used and nav_sig)
        else ("active" if (has_nav_results or has_nav_used) else "planned")
    )

    # --- live_backend_state ---
    live_cap = True
    live_sig = get_feature_signal("live_backend_state")
    live_ok = bool(ls.get("backend_runtime_ok")) is True
    live_health = "ok" if live_ok else "fail"
    live_state = (
        "planned"
        if not live_cap
        else (
            "connected"
            if (has_live and live_sig and live_ok)
            else ("active" if (live_sig or live_ok) else "planned")
        )
    )

    # --- panel_bridge ---
    panel_bridge_sig = get_feature_signal("panel_bridge")
    panel_bridge_payload_ok = bool(ls.get("panel_bridge_payload_ok"))
    panel_bridge_state = (
        "connected"
        if (has_live and panel_bridge_payload_ok and panel_bridge_sig)
        else ("active" if (panel_bridge_payload_ok or panel_bridge_sig) else "planned")
    )

    # --- last_activity_card ---
    activity_sig = get_feature_signal("last_activity_card")
    has_activity = bool(ctx.get("last_activity_has_activity")) is True
    activity_ts = str(ctx.get("last_activity_ts") or "").strip()
    activity_src = str(ctx.get("last_activity_source") or "—").strip()
    activity_state = (
        "connected"
        if (has_live and has_activity and activity_sig)
        else ("active" if has_activity else "planned")
    )

    return [
        {
            "key": "panel_api",
            "ad": "Panel API",
            "durum": panel_api_state,
            "panelde_gorunuyor": True,
            "aciklama": (
                (
                    ("Başarılı: " + panel_api_last_ok)
                    if panel_api_connected
                    else (
                        ("Geçici hata: " + (panel_api_err or "—") + " (" + panel_api_last_err + ")")
                        if panel_api_active
                        else "Henüz bağlantı yok."
                    )
                )
                + (f" · cap:{'var' if panel_api_cap else 'yok'} · health:{panel_api_health}")
                + ((" · sinyal: " + panel_api_sig) if panel_api_sig else "")
            ),
        },
        {
            "key": "intent_engine",
            "ad": "Intent Engine",
            "durum": intent_state,
            "panelde_gorunuyor": True,
            "aciklama": (
                (("Kalıcı kullanım sinyali: " + intent_sig) if intent_sig else "Kullanım sinyali yok.")
                + (f" · cap:{'var' if intent_cap else 'yok'} · health:{intent_health}")
            ),
        },
        {
            "key": "repo_search",
            "ad": "Repo Search",
            "durum": repo_search_state,
            "panelde_gorunuyor": True,
            "aciklama": (
                f"Son sorgu: {repo_search_query or '—'}; sonuç: {'var' if repo_search_has_results else 'yok'}; "
                + (f"zaman: {repo_search_last_at or '—'}")
                + (f" · cap:{'var' if repo_search_cap else 'yok'} · health:{repo_search_health}")
            ),
        },
        {
            "key": "context_reuse",
            "ad": "Context Reuse",
            "durum": context_feat_state,
            "panelde_gorunuyor": True,
            "aciklama": (
                f"Context durumu: {context_state}. Son repo sorgusu kalıcı store üzerinden okunur."
                + (f" · cap:{'var' if context_cap else 'yok'} · health:{context_health}")
            ),
        },
        {
            "key": "pending_completion",
            "ad": "Pending Completion",
            "durum": pending_state,
            "panelde_gorunuyor": True,
            "aciklama": (
                "Bekleyen repo sorgusu var."
                if has_pending_wait
                else (("Kalıcı sinyal: " + pending_sig) if pending_sig else "Sinyal yok.")
            ),
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
            "aciklama": (
                (("Kalıcı sağlık sinyali: " + live_sig) if live_sig else "Sağlık sinyali yok.")
                + (f" · cap:{'var' if live_cap else 'yok'} · health:{live_health}")
            ),
        },
        {
            "key": "panel_bridge",
            "ad": "Panel Bridge",
            "durum": panel_bridge_state,
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

