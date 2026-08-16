"""Interpreter pipeline core: stage contracts, confidence gate, latency.

Contract rules (ADR-023 Faz 0, slice doc T1-T6):
- The pipeline never adds to or rewrites translator output (T3/T4).
- Low or missing confidence is flagged, never silently passed (T1/T2).
- Every utterance is appended to a bilingual transcript with latency (T5).
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class Utterance:
    """One finished source-language utterance entering the pipeline."""

    text: str
    source_lang: str  # "tr" | "en"
    target_lang: str
    speech_end_ts: float  # seconds, from the pipeline clock
    # Son birkaç önceki söz (kaynak metin) — çevirmen bağlamı; marka onarımı
    # ve gönderme çözümü için (test 6 sonrası eklendi). Boş olabilir.
    context: tuple[str, ...] = ()


@dataclass(frozen=True)
class TranslationResult:
    text: str
    confidence: float | None  # None = provider gave no signal
    provider: str


class Translator(Protocol):
    def translate(self, utterance: Utterance) -> TranslationResult: ...


class TextToSpeech(Protocol):
    def speak(self, text: str, lang: str) -> None: ...


@dataclass(frozen=True)
class GateDecision:
    deliver: bool
    flagged: bool
    reason: str


class ConfidenceGate:
    """Marks low-confidence translations; missing confidence is treated as low.

    Faz 0 behaviour: flagged utterances are still delivered (the human
    interpreter-owner is in the meeting), but the flag is surfaced via the
    on_flag hook and recorded in the transcript. Delivery is never blocked
    here; blocking policies belong to later phases.
    """

    def __init__(self, threshold: float) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be within [0, 1]")
        self.threshold = threshold

    def evaluate(self, result: TranslationResult) -> GateDecision:
        if result.confidence is None:
            return GateDecision(deliver=True, flagged=True, reason="no_confidence_signal")
        if result.confidence < self.threshold:
            return GateDecision(deliver=True, flagged=True, reason="below_threshold")
        return GateDecision(deliver=True, flagged=False, reason="ok")


@dataclass(frozen=True)
class UtteranceRecord:
    source_text: str
    source_lang: str
    translated_text: str
    target_lang: str
    confidence: float | None
    flagged: bool
    flag_reason: str
    latency_ms: float
    recorded_at: float
    # Kalem 2 (2026-08-16): çıktı-dili post-check muhasebesi.
    # delivered=False → çıktı TTS'e verilmedi (fail-closed);
    # postcheck_ms = post-check'in eklediği süre (retry çevirisi dahil) —
    # kalem 3 gecikme optimizasyonunda maliyet ayrı görülsün diye ayrı alan.
    delivered: bool = True
    postcheck_ms: float = 0.0
    retried: bool = False


class BilingualTranscript:
    """Append-only transcript; records are never edited or removed."""

    def __init__(self) -> None:
        self._records: list[UtteranceRecord] = []

    def append(self, record: UtteranceRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[UtteranceRecord, ...]:
        return tuple(self._records)

    def to_jsonl(self) -> str:
        """One JSON object per utterance — Aşama C ölçüm kaydı formatı."""
        return "\n".join(json.dumps(asdict(r), ensure_ascii=False) for r in self._records)

    @staticmethod
    def append_jsonl(path: str, record: UtteranceRecord) -> None:
        """Crash-safe incremental log: one line per utterance, flushed at once.

        Prova düzeneği çökse bile o ana kadarki her söz diskte kalır (2026-08-14
        stres testi bulgusu: yalnız çıkışta yazmak çökmede tüm veriyi kaybetti).
        """
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def to_markdown(self) -> str:
        lines = ["| src | çeviri | güven | işaret | gecikme (ms) |", "|---|---|---|---|---|"]
        for r in self._records:
            flag = "⚠ düşük güven" if r.flagged else ""
            conf = "-" if r.confidence is None else f"{r.confidence:.2f}"
            lines.append(
                f"| {r.source_text} | {r.translated_text} | {conf} | {flag} | {r.latency_ms:.0f} |"
            )
        return "\n".join(lines)


def summarize_latencies_ms(transcript: BilingualTranscript) -> dict[str, float]:
    values = [r.latency_ms for r in transcript.records]
    if not values:
        return {"count": 0, "median_ms": 0.0, "max_ms": 0.0}
    return {
        "count": len(values),
        "median_ms": statistics.median(values),
        "max_ms": max(values),
    }


class InterpreterPipeline:
    """Consecutive interpretation for one utterance at a time.

    The delivered text is exactly the translator's output — this class must
    never concatenate, prefix, or rewrite it (slice tests T3/T4 pin this).
    """

    def __init__(
        self,
        translator: Translator,
        tts: TextToSpeech,
        gate: ConfidenceGate,
        transcript: BilingualTranscript,
        on_flag: Callable[[UtteranceRecord], None] | None = None,
        on_record: Callable[[UtteranceRecord], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._translator = translator
        self._tts = tts
        self._gate = gate
        self._transcript = transcript
        self._on_flag = on_flag
        self._on_record = on_record
        self._clock = clock

    def process(self, utterance: Utterance) -> UtteranceRecord:
        from representative.langcheck import detect_lang

        result = self._translator.translate(utterance)
        postcheck_ms = 0.0
        retried = False
        lang_ok = detect_lang(result.text) in ("unknown", utterance.target_lang)
        if not lang_ok:
            # Kurucu kuralı (2026-08-16): EN FAZLA 1 yeniden çeviri; döngü yok.
            retried = True
            retry_start = self._clock()
            retry_result = self._translator.translate(utterance)
            postcheck_ms = (self._clock() - retry_start) * 1000.0
            if detect_lang(retry_result.text) in ("unknown", utterance.target_lang):
                result = retry_result
                lang_ok = True

        decision = self._gate.evaluate(result)
        now = self._clock()
        if not result.text.strip():
            # Test 7 bug'ı: model boş çeviri döndürebilir — boş metin
            # seslendirilmez, işaretli düşer (fail-closed).
            lang_ok = False
            flagged, reason = True, "empty_translation"
        elif lang_ok:
            self._tts.speak(result.text, utterance.target_lang)
            flagged, reason = decision.flagged, decision.reason
        else:
            # Fail-closed: ikinci çıktı da yanlış dilde — TTS'e verilmez.
            flagged, reason = True, "wrong_output_language"
        record = UtteranceRecord(
            source_text=utterance.text,
            source_lang=utterance.source_lang,
            translated_text=result.text,
            target_lang=utterance.target_lang,
            confidence=result.confidence,
            flagged=flagged,
            flag_reason=reason,
            latency_ms=(now - utterance.speech_end_ts) * 1000.0,
            recorded_at=now,
            delivered=lang_ok,
            postcheck_ms=postcheck_ms,
            retried=retried,
        )
        self._transcript.append(record)
        if self._on_record is not None:
            self._on_record(record)
        if record.flagged and self._on_flag is not None:
            self._on_flag(record)
        return record
