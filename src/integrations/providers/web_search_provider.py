from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from integrations.models import IntegrationRequest, IntegrationResult

SUPPORTED_ENGINES = ("brave", "google", "bing", "duckduckgo")


@dataclass(frozen=True)
class EngineConfig:
    name: str
    configured: bool
    reason: str = ""


def _engine_config(name: str) -> EngineConfig:
    normalized = name.strip().lower()
    if normalized == "brave":
        return EngineConfig(
            name="brave",
            configured=bool(os.getenv("BRAVE_SEARCH_API_KEY")),
            reason="" if os.getenv("BRAVE_SEARCH_API_KEY") else "BRAVE_SEARCH_API_KEY missing",
        )
    if normalized == "google":
        gk = os.getenv("GOOGLE_SEARCH_API_KEY")
        gcx = os.getenv("GOOGLE_SEARCH_CX")
        return EngineConfig(
            name="google",
            configured=bool(gk and gcx),
            reason="" if gk and gcx else "GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_CX missing",
        )
    if normalized == "bing":
        return EngineConfig(
            name="bing",
            configured=bool(os.getenv("BING_SEARCH_API_KEY")),
            reason="" if os.getenv("BING_SEARCH_API_KEY") else "BING_SEARCH_API_KEY missing",
        )
    if normalized == "duckduckgo":
        return EngineConfig(
            name="duckduckgo",
            configured=False,
            reason="official_search_api_not_configured",
        )
    return EngineConfig(name=normalized, configured=False, reason="unsupported_engine")


def _requested_engines(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("engines") or payload.get("engine") or list(SUPPORTED_ENGINES)
    if isinstance(raw, str):
        engines = [raw]
    elif isinstance(raw, list):
        engines = [x for x in raw if isinstance(x, str)]
    else:
        engines = []
    cleaned: list[str] = []
    for engine in engines:
        e = engine.strip().lower()
        if e and e not in cleaned:
            cleaned.append(e)
    return cleaned or list(SUPPORTED_ENGINES)


def _optional_nonempty_str(payload: dict[str, Any], key: str) -> str | None:
    v = payload.get(key)
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


def _search_routing_hints(payload: dict[str, Any]) -> dict[str, str]:
    """Ülke / dil / dikey: gerçek HTTP yok; yönlendirme ve ilerideki motor seçimi için taşınır."""
    out: dict[str, str] = {}
    if (c := _optional_nonempty_str(payload, "country")) is not None:
        out["country"] = c.upper()[:8]
    if (lang := _optional_nonempty_str(payload, "language")) is not None:
        out["language"] = lang.lower()[:16]
    if (vert := _optional_nonempty_str(payload, "vertical")) is not None:
        out["vertical"] = vert[:128]
    return out


def run_web_search_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action != "search":
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="unsupported_web_action",
        )
    query = request.payload.get("query")
    if not isinstance(query, str) or not query.strip():
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="query_required",
        )
    engines = _requested_engines(request.payload)
    engine_status = [_engine_config(engine) for engine in engines]
    routing = _search_routing_hints(request.payload)
    data: dict[str, Any] = {
        "query": query.strip(),
        **routing,
        "engines": [
            {
                "name": engine.name,
                "configured": engine.configured,
                "reason": engine.reason,
            }
            for engine in engine_status
        ],
        "results": [],
    }
    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data=data,
        error="web_search_provider_not_configured",
    )


def register_web_search_provider(register) -> None:
    register("web", "search", run_web_search_action)
