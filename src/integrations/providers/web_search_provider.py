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
        return EngineConfig(
            name="google",
            configured=bool(os.getenv("GOOGLE_SEARCH_API_KEY") and os.getenv("GOOGLE_SEARCH_CX")),
            reason="" if os.getenv("GOOGLE_SEARCH_API_KEY") and os.getenv("GOOGLE_SEARCH_CX") else "GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_CX missing",
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
    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data={
            "query": query.strip(),
            "engines": [
                {
                    "name": engine.name,
                    "configured": engine.configured,
                    "reason": engine.reason,
                }
                for engine in engine_status
            ],
            "results": [],
        },
        error="web_search_provider_not_configured",
    )
def register_web_search_provider(register) -> None:
    register("web", "search", run_web_search_action)
