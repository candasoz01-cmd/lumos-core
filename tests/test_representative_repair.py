"""Belirsizlikte tekrar isteme kuralları (kurucu kararı, 2026-08-23).

Canlı prova kanıtı: eşik altı çeviriler seslendirildi, dili belirlenemeyen
sözler sessizce Türkçe sayıldı. Bu testler yeni kuralı çakar.
"""

import pytest

from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Utterance,
    flag_label,
    undetected_language_record,
)
from representative.repair import REPAIR_LINES, bilingual_repair_line, repair_line
from representative.routing import Direction, DirectionRouter


class StubTranslator:
    def __init__(self, text: str, confidence: float | None) -> None:
        self._text, self._confidence = text, confidence

    def translate(self, utterance: Utterance) -> TranslationResult:
        return TranslationResult(text=self._text, confidence=self._confidence, provider="stub")


class RecordingTTS:
    def __init__(self) -> None:
        self.spoken: list[tuple[str, str]] = []

    def speak(self, text: str, lang: str) -> None:
        self.spoken.append((text, lang))


def run(translated: str, confidence: float | None, source_lang: str = "tr"):
    tts = RecordingTTS()
    pipeline = InterpreterPipeline(
        translator=StubTranslator(translated, confidence),
        tts=tts,
        gate=ConfidenceGate(0.8),
        transcript=BilingualTranscript(),
        clock=lambda: 0.0,
    )
    record = pipeline.process(
        Utterance(
            text="Kaynak cümle.",
            source_lang=source_lang,
            target_lang="en" if source_lang == "tr" else "tr",
            speech_end_ts=0.0,
        )
    )
    return record, tts


def test_repair_is_asked_in_the_speakers_own_language() -> None:
    """Tekrar edecek olan konuşandır; istek onun dilinde gitmeli."""
    _, tts_tr = run("An uncertain sentence.", 0.5, source_lang="tr")
    assert tts_tr.spoken == [(REPAIR_LINES["tr"], "tr")]
    _, tts_en = run("Belirsiz bir cümle.", 0.5, source_lang="en")
    assert tts_en.spoken == [(REPAIR_LINES["en"], "en")]


@pytest.mark.parametrize("confidence", [0.5, 0.6, 0.7, 0.79, None])
def test_live_rehearsal_confidence_band_is_no_longer_spoken(confidence) -> None:
    """2026-08-23 provasında duyulan bant (0.50-0.70) ve sinyalsiz hâl."""
    record, tts = run("A quiet, uncertain sentence.", confidence)
    assert record.delivered is False
    assert record.repair_spoken is True
    assert ("A quiet, uncertain sentence.", "en") not in tts.spoken


def test_confident_translation_is_still_spoken_normally() -> None:
    record, tts = run("Hello there.", 0.95)
    assert record.delivered is True
    assert record.repair_spoken is False
    assert tts.spoken == [("Hello there.", "en")]
    assert flag_label(record) == ""


def test_repair_line_refuses_unknown_language() -> None:
    with pytest.raises(ValueError):
        repair_line("de")


def test_bilingual_line_is_used_when_language_is_unknown() -> None:
    line = bilingual_repair_line()
    assert REPAIR_LINES["tr"] in line and REPAIR_LINES["en"] in line


def test_undetected_language_still_falls_back_in_the_router() -> None:
    """Router davranışı korunur; kararı rig verir (yön değil, tekrar isteği)."""
    decision = DirectionRouter(Direction("tr", "en")).route("Translate.")
    assert decision.detected == "unknown"
    assert decision.reason == "fallback_unknown"


def test_undetected_record_leaves_an_honest_trace() -> None:
    record = undetected_language_record("Translate.", latency_ms=1450.0, recorded_at=12.0)
    assert record.delivered is False
    assert record.repair_spoken is True
    assert record.source_lang == "unknown"
    assert record.translated_text == ""
    assert "dil belirlenemedi" in flag_label(record)
    # Uydurma sıfır gecikme yazılmaz — çözümleme kendini kandırmasın.
    assert record.latency_ms == 1450.0
