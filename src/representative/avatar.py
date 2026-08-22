"""Google Meet-only, two-state Lumos avatar assets and state controller."""

from __future__ import annotations

import base64
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

MAX_RECALL_JPEG_BYTES = 1_300_000
_ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "representative"


@dataclass(frozen=True)
class MeetAvatarAssets:
    idle_jpeg_b64: str
    speaking_jpeg_b64: str


def _load_jpeg(path: Path) -> str:
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise ValueError(f"avatar asset is not a JPEG: {path}")
    if len(data) > MAX_RECALL_JPEG_BYTES:
        raise ValueError(f"avatar asset exceeds Recall's 1.3 MB limit: {path}")
    return base64.b64encode(data).decode("ascii")


def load_meet_avatar_assets(asset_dir: Path = _ASSET_DIR) -> MeetAvatarAssets:
    """Load the fixed Meet avatar; missing/invalid assets fail before bot creation."""
    return MeetAvatarAssets(
        idle_jpeg_b64=_load_jpeg(asset_dir / "lumos-meet-idle.jpg"),
        speaking_jpeg_b64=_load_jpeg(asset_dir / "lumos-meet-speaking.jpg"),
    )


class AvatarStateController:
    """Publish speaking/idle states without letting visual failures stop audio."""

    def __init__(
        self,
        publish: Callable[[str], None],
        assets: MeetAvatarAssets,
        on_error: Callable[[Exception], None] | None = None,
        background: bool = True,
    ) -> None:
        self._publish = publish
        self._assets = assets
        self._on_error = on_error or (lambda _exc: None)
        self._generation = 0
        self._lock = threading.Lock()
        self._updates: queue.Queue[str] | None = queue.Queue() if background else None
        if self._updates is not None:
            threading.Thread(target=self._publish_loop, daemon=True).start()

    def _try_publish(self, jpeg_b64: str) -> None:
        try:
            self._publish(jpeg_b64)
        except Exception as exc:
            self._on_error(exc)

    def _publish_loop(self) -> None:
        assert self._updates is not None
        while True:
            self._try_publish(self._updates.get())

    def _enqueue(self, jpeg_b64: str) -> None:
        if self._updates is None:
            self._try_publish(jpeg_b64)
        else:
            self._updates.put(jpeg_b64)

    def speaking_for(self, seconds: float) -> None:
        with self._lock:
            self._generation += 1
            generation = self._generation
        self._enqueue(self._assets.speaking_jpeg_b64)

        def restore() -> None:
            with self._lock:
                if generation != self._generation:
                    return
            self._enqueue(self._assets.idle_jpeg_b64)

        timer = threading.Timer(max(0.1, seconds), restore)
        timer.daemon = True
        timer.start()

    def idle(self) -> None:
        with self._lock:
            self._generation += 1
        self._enqueue(self._assets.idle_jpeg_b64)
