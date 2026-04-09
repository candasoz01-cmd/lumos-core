"""Hazır izlenecek içerik: YouTube arama sayfasından ilk video kimliğini çıkarır."""
from __future__ import annotations

import re
from typing import Any

import requests

__all__ = ["run"]


def _extract_video_id(html: str) -> str | None:
    m = re.search(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
    return m.group(1) if m else None


def run(task_ctx: dict[str, Any]) -> dict[str, Any]:
    prompt = str(task_ctx.get("prompt") or "").strip()
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

    return {
        "status": "done",
        "output": {
            "type": "video",
            "url": video_url,
            "source": "youtube",
            "title": prompt or "video",
        },
    }
