"""Video executor: yalnızca yapılandırılmış çıktı; açıklama / karar metni yok."""
from __future__ import annotations

from typing import Any

__all__ = ["run"]


def run(task_ctx: dict[str, Any]) -> dict[str, Any]:
    _ = task_ctx
    return {
        "status": "done",
        "output": {
            "type": "video",
            "url": "/out.mp4",
            "title": "generated_video",
        },
    }
