from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from integrations.models import IntegrationRequest, IntegrationResult

SUPPORTED_ENGINES = ("brave", "google", "bing", "duckduckgo")

_BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


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


def _brave_http_enabled(payload: dict[str, Any], engines: list[str]) -> bool:
    """Brave REST yalnızca açıkça brave seçildiğinde (tek motor veya `engine: brave`)."""
    if "brave" not in engines or not _engine_config("brave").configured:
        return False
    raw_engine = payload.get("engine")
    if isinstance(raw_engine, str) and raw_engine.strip().lower() == "brave":
        return True
    return engines == ["brave"]


def _search_routing_hints(payload: dict[str, Any]) -> dict[str, str]:
    """Ülke / dil / dikey: Brave `country` / `search_lang` ve ilerideki motor seçimi için taşınır."""
    out: dict[str, str] = {}
    if (c := _optional_nonempty_str(payload, "country")) is not None:
        out["country"] = c.upper()[:8]
    if (lang := _optional_nonempty_str(payload, "language")) is not None:
        out["language"] = lang.lower()[:16]
    if (vert := _optional_nonempty_str(payload, "vertical")) is not None:
        out["vertical"] = vert[:128]
    return out


def _normalize_brave_web_result(raw: dict[str, Any]) -> dict[str, str] | None:
    title = raw.get("title")
    url = raw.get("url")
    desc = raw.get("description")
    if not isinstance(title, str) or not isinstance(url, str):
        return None
    d = desc if isinstance(desc, str) else ""
    return {
        "title": title.strip(),
        "url": url.strip(),
        "description": d.strip(),
    }


def _fetch_brave_web_search(
    query: str,
    *,
    country: str | None,
    language: str | None,
    count: int = 10,
) -> tuple[list[dict[str, str]], str]:
    key = (os.getenv("BRAVE_SEARCH_API_KEY") or "").strip()
    if not key:
        return [], "BRAVE_SEARCH_API_KEY missing"
    params: dict[str, str] = {"q": query, "count": str(max(1, min(count, 20)))}
    if country:
        params["country"] = country.upper()
    if language:
        params["search_lang"] = language.lower()
    url = f"{_BRAVE_WEB_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": key,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw_body = resp.read()
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")[:500]
        except OSError:
            detail = ""
        return [], f"brave_http_{e.code}:{detail or e.reason}"
    except urllib.error.URLError as e:
        return [], f"brave_url_error:{e.reason!s}"
    except OSError as e:
        return [], f"brave_io_error:{e!s}"

    try:
        obj = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return [], f"brave_bad_json:{e!s}"

    web = obj.get("web") if isinstance(obj, dict) else None
    rows = web.get("results") if isinstance(web, dict) else None
    if not isinstance(rows, list):
        return [], ""

    out: list[dict[str, str]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        norm = _normalize_brave_web_result(item)
        if norm:
            out.append(norm)
    return out, ""


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

    brave_ran = False
    brave_fetch_error = ""
    if _brave_http_enabled(request.payload, engines):
        brave_ran = True
        count_raw = request.payload.get("count")
        count = 10
        if isinstance(count_raw, int) and not isinstance(count_raw, bool):
            count = count_raw
        elif isinstance(count_raw, str) and count_raw.strip().isdigit():
            count = int(count_raw.strip())
        items, brave_fetch_error = _fetch_brave_web_search(
            query.strip(),
            country=routing.get("country"),
            language=routing.get("language"),
            count=count,
        )
        if items:
            data["results"].append({"engine": "brave", "items": items})
        elif brave_fetch_error:
            data["brave_error"] = brave_fetch_error

    brave_only = engines == ["brave"]
    if brave_only and brave_ran and not brave_fetch_error:
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data=data,
            error="",
        )

    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data=data,
        error="web_search_provider_not_configured",
    )


def register_web_search_provider(register) -> None:
    register("web", "search", run_web_search_action)
