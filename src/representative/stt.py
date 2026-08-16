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


# ADR-023 "Lumos bağlam sözlüğü" — STT tarafı: whisper'a bağlam ipucu olarak
# verilir; bench kanıtı olmadan genişletme (yanlış öncelik tanıma riski).
LUMOS_TERMS_PROMPT = (
    "Lumos, ChatLumos, We Lock AI, Lumos temsilcisi, toplantı, sözleşme, teklif."
)


class OpenAICloudSTT:
    """Cloud STT over the existing openai dependency.

    2026-08-14 bench kararı: gpt-4o-mini-transcribe E-sınıfı cümlelerde
    (elli bin / bir Ekim'de / yüzde kırk) birebir sonuç verdi, 0.9-1.8 sn;
    yerel medium hem 3 kat yavaş hem isabetsiz çıktı. Gizlilik notu: ses
    OpenAI'ye gider — çeviri katmanıyla aynı işlemci, kapalı prova için
    kabul; gerçek dış toplantı öncesi DPA değerlendirmesi zaten blokaj.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini-transcribe",
        language: str | None = None,
        prompt: str | None = None,
    ) -> None:
        from openai import OpenAI  # core dependency; deferred for CI'siz kullanım

        self._client = OpenAI()
        self._model = model
        self._language = language
        self._prompt = prompt

    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> SttResult:
        import io
        import wave

        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm)
        buf.seek(0)
        buf.name = "utterance.wav"  # openai SDK dosya adından format çıkarır
        result = self._client.audio.transcriptions.create(
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
