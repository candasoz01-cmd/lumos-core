"""Speech-to-text adapter for the local rig (Aşama B).

faster-whisper is an optional dependency (`pip install .[representative]`);
this module defers the import so text-mode and CI never need it.

Cloud STT follows docs/contracts/stt-data-boundary-v1.md (ADR-025):
batch /v1/audio/transcriptions only; OPENAI_MODEL_STT; real Meet audio
fail-closed until written EU residency + MAM/ZDR confirmation.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

STT_AUDIO_SYNTHETIC = "synthetic"
STT_AUDIO_REAL = "real"
STT_NOT_CONFIGURED = "not_configured"
STT_BAD_MODEL = "bad_model"
STT_REAL_BLOCKED = "real_audio_blocked"
STT_EU_BASE_REQUIRED = "eu_base_url_required"
_STT_ALLOWED_MODELS = frozenset(
    {
        "whisper-1",
        "gpt-4o-transcribe",
        "gpt-4o-mini-transcribe",
    }
)
_EU_STT_BASE_URL = "https://eu.api.openai.com/v1"


@dataclass(frozen=True)
class SttResult:
    text: str
    language: str


class SttBoundaryError(Exception):
    """Fail-closed STT data-boundary error. status is a bounded token."""

    def __init__(self, status: str, model: str = "") -> None:
        self.status = status
        self.model = model
        super().__init__(status)


def resolve_openai_stt_model(explicit: str | None = None) -> tuple[str, str | None]:
    """STT model from OPENAI_MODEL_STT only. No chat/cyber fallback."""
    model = (explicit or os.getenv("OPENAI_MODEL_STT") or "").strip()
    if not model:
        return "", STT_NOT_CONFIGURED
    if model not in _STT_ALLOWED_MODELS:
        return model, STT_BAD_MODEL
    return model, None


def stt_residency_written() -> bool:
    """Operator flag after written org confirmation — does not create the approval."""
    return (os.getenv("LUMOS_STT_RESIDENCY_WRITTEN") or "").strip() == "1"


def resolve_stt_base_url(audio_source: str) -> tuple[str | None, str | None]:
    """Real Meet audio must hit eu.api.openai.com. Synthetic may use the default client."""
    source = (audio_source or STT_AUDIO_REAL).strip().lower()
    if source != STT_AUDIO_REAL:
        return None, None
    if not stt_residency_written():
        return None, STT_REAL_BLOCKED
    base = (os.getenv("OPENAI_STT_BASE_URL") or "").strip().rstrip("/")
    if base != _EU_STT_BASE_URL:
        return None, STT_EU_BASE_REQUIRED
    return base, None


# ADR-023 "Lumos bağlam sözlüğü" — STT tarafı: whisper'a bağlam ipucu olarak
# verilir; bench kanıtı olmadan genişletme (yanlış öncelik tanıma riski).
LUMOS_TERMS_PROMPT = (
    "Lumos, ChatLumos, We Lock AI, Lumos temsilcisi, toplantı, sözleşme, teklif."
)


class OpenAICloudSTT:
    """Batch cloud STT: POST /v1/audio/transcriptions. Realtime is out of scope.

    Default audio_source is real (fail-closed). Synthetic tests must opt in.
    Model comes from OPENAI_MODEL_STT (or an explicit allowed constructor arg).
    """

    def __init__(
        self,
        model: str | None = None,
        language: str | None = None,
        prompt: str | None = None,
        audio_source: str = STT_AUDIO_REAL,
    ) -> None:
        resolved, err = resolve_openai_stt_model(model)
        if err:
            raise SttBoundaryError(err, resolved)
        self._model = resolved
        self._language = language
        self._prompt = prompt
        self._audio_source = (audio_source or STT_AUDIO_REAL).strip().lower() or STT_AUDIO_REAL

    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> SttResult:
        import io
        import wave

        from openai import OpenAI

        base_url, gate = resolve_stt_base_url(self._audio_source)
        if gate:
            logger.info("stt_boundary status=%s model=%s", gate, self._model)
            raise SttBoundaryError(gate, self._model)
        client_kw: dict[str, str] = {}
        if base_url:
            client_kw["base_url"] = base_url
        client = OpenAI(**client_kw)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm)
        buf.seek(0)
        buf.name = "utterance.wav"  # openai SDK dosya adından format çıkarır
        result = client.audio.transcriptions.create(
            model=self._model, file=buf, language=self._language, prompt=self._prompt
        )
        return SttResult(text=result.text.strip(), language=self._language or "")


class FasterWhisperSTT:
    """Local whisper STT over raw 16 kHz mono int16 PCM."""

    def __init__(
        self,
        model_size: str = "small",
        language: str | None = None,
        initial_prompt: str | None = None,
    ) -> None:
        from faster_whisper import WhisperModel  # optional dep, deferred

        self._model = WhisperModel(model_size, compute_type="int8")
        self._language = language
        self._initial_prompt = initial_prompt

    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> SttResult:
        import numpy as np  # ships with faster-whisper's dependencies

        if sample_rate != 16000:
            raise ValueError("rig captures at 16 kHz; resampling is out of scope")
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        # vad_filter + no_speech eleme (test 2 bulgusu): gürültü kesitleri
        # whisper'a girince "Teşekkürler."/"Altyazı M.K." halüsinasyonları
        # üretiyordu; konuşma olmayan kesitler modele hiç gitmez / elenir.
        segments, info = self._model.transcribe(
            audio,
            language=self._language,
            initial_prompt=self._initial_prompt,
            vad_filter=True,
        )
        texts = [
            segment.text.strip()
            for segment in segments
            if getattr(segment, "no_speech_prob", 0.0) <= 0.6
        ]
        return SttResult(text=" ".join(texts).strip(), language=info.language)
