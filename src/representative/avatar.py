"""Google Meet-only, two-state Lumos avatar assets and state controller."""

from __future__ import annotations

import base64
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
        # Latest-wins slot, not a queue. Only the newest visual state is
        # meaningful: if publishing lags, an unbounded queue would replay a
        # stale "speaking" frame long after the speech ended, so the avatar
        # would drift further and further behind reality. Superseded frames
        # are dropped on purpose.
        self._background = background
        self._pending: str | None = None
        self._wake = threading.Event()
        if background:
            threading.Thread(target=self._publish_loop, daemon=True).start()

    def _try_publish(self, jpeg_b64: str) -> None:
        try:
            self._publish(jpeg_b64)
        except Exception as exc:
            self._on_error(exc)

    def _publish_loop(self) -> None:
        while True:
            self._wake.wait()
            with self._lock:
                pending = self._pending
                self._pending = None
                self._wake.clear()
            if pending is not None:
                self._try_publish(pending)

    def _stage_locked(self, jpeg_b64: str) -> str | None:
        """Record the newest frame. **Caller must hold ``_lock``.**

        Returns the frame when it must be published directly (no background
        thread); the caller publishes it *after* releasing the lock, because
        publishing does network I/O and must never run under the state lock.

        Staging happens under the same lock as the generation counter so a
        state change and its frame cannot be split. Without that, an ``idle``
        that wins the counter can still lose the frame race to a late
        ``speaking``, leaving the avatar stuck speaking.
        """
        if not self._background:
            return jpeg_b64
        self._pending = jpeg_b64
        self._wake.set()
        return None

    def _enqueue(self, jpeg_b64: str) -> None:
        with self._lock:
            direct = self._stage_locked(jpeg_b64)
        if direct is not None:
            self._try_publish(direct)

    def pending_frame(self) -> str | None:
        """Frame waiting to be published, if any. For tests and diagnostics."""
        with self._lock:
            return self._pending

    def speaking_for(self, seconds: float) -> None:
        with self._lock:
            self._generation += 1
            generation = self._generation
            direct = self._stage_locked(self._assets.speaking_jpeg_b64)
        if direct is not None:
            self._try_publish(direct)

        def restore() -> None:
            with self._lock:
                if generation != self._generation:
                    return
                pending = self._stage_locked(self._assets.idle_jpeg_b64)
            if pending is not None:
                self._try_publish(pending)

        timer = threading.Timer(max(0.1, seconds), restore)
        timer.daemon = True
        timer.start()

    def idle(self) -> None:
        with self._lock:
            self._generation += 1
            direct = self._stage_locked(self._assets.idle_jpeg_b64)
        if direct is not None:
            self._try_publish(direct)
