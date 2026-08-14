"""Speech-to-text adapter for the local rig (Aşama B).

faster-whisper is an optional dependency (`pip install .[representative]`);
this module defers the import so text-mode and CI never need it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SttResult:
    text: str
    language: str


class FasterWhisperSTT:
    """Local whisper STT over raw 16 kHz mono int16 PCM."""

    def __init__(self, model_size: str = "small", language: str | None = None) -> None:
        from faster_whisper import WhisperModel  # optional dep, deferred

        self._model = WhisperModel(model_size, compute_type="int8")
        self._language = language

    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> SttResult:
        import numpy as np  # ships with faster-whisper's dependencies

        if sample_rate != 16000:
            raise ValueError("rig captures at 16 kHz; resampling is out of scope")
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, info = self._model.transcribe(audio, language=self._language)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return SttResult(text=text, language=info.language)
