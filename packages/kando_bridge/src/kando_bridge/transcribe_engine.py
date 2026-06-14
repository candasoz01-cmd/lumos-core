"""Optional STT engine interface — faster-whisper wrap.

Normal runtime: unavailable unless ``KANDO_STT_ENABLED=1``, faster-whisper is
importable, and a real engine is wired. Tests may inject via ``set_engine_instance``.
"""
from __future__ import annotations

import os
import tempfile
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
_default_engine: TranscribeEngine | None = None


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


def _stt_enabled() -> bool:
    return os.environ.get("KANDO_STT_ENABLED", "").strip() == "1"


def is_engine_available() -> bool:
    if _engine_instance is not None:
        return True
    if not _stt_enabled():
        return False
    return _faster_whisper_importable()


def _audio_suffix(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ".wav"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in {"wav", "webm", "ogg", "mp3", "m4a", "flac", "mp4", "mpeg", "mpga"}:
        return f".{ext}"
    return ".wav"


class FasterWhisperEngine:
    """Local faster-whisper backend; config via ``KANDO_STT_*`` env vars."""

    def __init__(self) -> None:
        self._model_name = (
            os.environ.get("KANDO_STT_MODEL", "tiny").strip() or "tiny"
        )
        self._device = os.environ.get("KANDO_STT_DEVICE", "cpu").strip() or "cpu"
        self._compute_type = (
            os.environ.get("KANDO_STT_COMPUTE_TYPE", "int8").strip() or "int8"
        )
        lang = os.environ.get("KANDO_STT_LANGUAGE", "tr").strip()
        self._default_language: str | None = lang if lang else None
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        suffix = _audio_suffix(filename)
        lang = language if language is not None else self._default_language

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()

            model = self._get_model()
            segments, info = model.transcribe(tmp.name, language=lang)
            parts = [segment.text.strip() for segment in segments]
            text = " ".join(part for part in parts if part).strip()

        return {
            "ok": True,
            "text": text,
            "transcript": text,
            "language": info.language,
            "duration_sec": info.duration,
            "engine": "faster-whisper",
            "model": self._model_name,
        }


def _get_default_engine() -> TranscribeEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = FasterWhisperEngine()
    return _default_engine


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
    return _get_default_engine().transcribe(
        audio_bytes,
        language=language,
        filename=filename,
    )
