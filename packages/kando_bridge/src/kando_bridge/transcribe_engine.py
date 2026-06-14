"""Optional STT engine interface — faster-whisper wrap placeholder.

Normal runtime: unavailable unless ``KANDO_STT_ENABLED=1``, faster-whisper is
importable, and a real engine is wired. Tests may inject via ``set_engine_instance``.
"""
from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable


class EngineUnavailable(Exception):
    """STT engine is not installed, not enabled, or not wired."""


@runtime_checkable
class TranscribeEngine(Protocol):
    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Return structured transcript payload (``ok: true``, ``text``, …)."""
        ...


_engine_instance: TranscribeEngine | None = None


def set_engine_instance(engine: TranscribeEngine | None) -> None:
    """Replace engine implementation (tests / future faster-whisper wiring)."""
    global _engine_instance
    _engine_instance = engine


def _faster_whisper_importable() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def is_engine_available() -> bool:
    if _engine_instance is not None:
        return True
    if os.environ.get("KANDO_STT_ENABLED", "").strip() != "1":
        return False
    if not _faster_whisper_importable():
        return False
    # Env + dependency present; real Whisper wiring not implemented yet.
    return False


def transcribe_audio_bytes(
    audio_bytes: bytes,
    *,
    language: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    if _engine_instance is not None:
        return _engine_instance.transcribe(
            audio_bytes,
            language=language,
            filename=filename,
        )
    if not is_engine_available():
        raise EngineUnavailable("transcribe engine unavailable")
    raise EngineUnavailable("transcribe engine not wired")
