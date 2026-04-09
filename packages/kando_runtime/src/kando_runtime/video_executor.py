from __future__ import annotations

import hashlib
from typing import Any


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:20]


def run(task_ctx: dict[str, Any]) -> dict[str, Any]:
    """Video yürütücü çıktısı: type video + url + title (üretim bağlandığında içerik aynı yolu kullanır)."""
    params = task_ctx.get("params") if isinstance(task_ctx.get("params"), dict) else {}
    prompt = str(params.get("prompt") or task_ctx.get("prompt") or "").strip()
    h = _hash_prompt(prompt) if prompt else _hash_prompt("")
    url = f"/videos/{h}.mp4"
    return {
        "status": "done",
        "output": {
            "type": "video",
            "url": url,
            "title": "generated_video",
        },
    }
