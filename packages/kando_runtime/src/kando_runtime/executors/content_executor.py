"""Hazır izlenecek içerik: YouTube arama sayfasından ilk video kimliğini çıkarır."""
from __future__ import annotations

import hashlib
import re
import time
from typing import Any

import requests

__all__ = ["run"]

_CACHE = {}
_TTL = 300
_CACHE_HITS = 0
_CACHE_MISSES = 0


def _hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def _extract_video_id(html: str) -> str | None:
    m = re.search(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
    return m.group(1) if m else None


def run(task_ctx: dict[str, Any]) -> dict[str, Any]:
    global _CACHE_HITS, _CACHE_MISSES

    prompt = str(task_ctx.get("prompt") or "").strip()
    key = "content:" + _hash(prompt)
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.time() - ts < _TTL:
            _CACHE_HITS += 1
            return {
                **val,
                "meta": {
                    "cache_hits": _CACHE_HITS,
                    "cache_misses": _CACHE_MISSES,
                },
            }
        else:
            del _CACHE[key]
            _CACHE_MISSES += 1
    else:
        _CACHE_MISSES += 1

    q = prompt.replace(" ", "+")

    search_url = f"https://www.youtube.com/results?search_query={q}"

    try:
        r = requests.get(search_url, timeout=5)
        vid = _extract_video_id(r.text)
        if vid:
            video_url = f"https://www.youtube.com/watch?v={vid}"
        else:
            video_url = search_url
    except Exception:
        video_url = search_url

    result: dict[str, Any] = {
        "status": "done",
        "output": {
            "type": "video",
            "url": video_url,
            "source": "youtube",
            "title": prompt or "video",
        },
    }
    _CACHE[key] = (time.time(), result)
    return {
        **result,
        "meta": {
            "cache_hits": _CACHE_HITS,
            "cache_misses": _CACHE_MISSES,
        },
    }
