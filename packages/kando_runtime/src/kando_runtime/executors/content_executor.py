"""Hazır izlenecek içerik önerileri (stub; gerçek API sonra bağlanır)."""
from __future__ import annotations

from typing import Any

__all__ = ["run"]


def run(task_ctx: dict[str, Any]) -> dict[str, Any]:
    prompt = str(task_ctx.get("prompt") or "").strip()
    q = prompt.replace(" ", "+")
    return {
        "status": "done",
        "output": {
            "type": "content_list",
            "mode": "watch",
            "query": prompt,
            "items": [
                {
                    "title": "Hazır içerik 1",
                    "url": "https://www.youtube.com/results?search_query=" + q,
                    "source": "youtube",
                }
            ],
        },
    }
