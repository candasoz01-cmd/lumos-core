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
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._translator = translator
        self._tts = tts
        self._gate = gate
        self._transcript = transcript
        self._on_flag = on_flag
        self._clock = clock

    def process(self, utterance: Utterance) -> UtteranceRecord:
        result = self._translator.translate(utterance)
        decision = self._gate.evaluate(result)
        tts_start = self._clock()
        self._tts.speak(result.text, utterance.target_lang)
        record = UtteranceRecord(
            source_text=utterance.text,
            source_lang=utterance.source_lang,
            translated_text=result.text,
            target_lang=utterance.target_lang,
            confidence=result.confidence,
            flagged=decision.flagged,
            flag_reason=decision.reason,
            latency_ms=(tts_start - utterance.speech_end_ts) * 1000.0,
            recorded_at=tts_start,
        )
        self._transcript.append(record)
        if record.flagged and self._on_flag is not None:
            self._on_flag(record)
        return record
