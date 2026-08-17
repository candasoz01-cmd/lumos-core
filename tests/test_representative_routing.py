"""Çift yön routing testleri — canlı insan testi 4'ün papağan bulgusuna karşı.

Botsuz doğrulama: gerçek toplantıda duyulmuş cümlelerin metinleri üzerinden
yön kararı sınanır; ses/ağ gerekmez.
"""

import pytest

from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Utterance,
)
from representative.routing import Direction, DirectionRouter

# Canlı insan testi 4'te (2026-08-17) fiilen duyulan cümlelerden alınmış
# örnekler; papağan vakasının kaynağı buydu.
TR_LINES = [
    "Telaffuz mükemmel olmak zorunda değil, gerçek toplantıda da olmayacak.",
    "Sen şimdi yabancı muhatap rolündesin.",
    "Toplantıya beş dakika sonra başlayalım.",
]
EN_LINES = [
    "The pronunciation doesn't have to be perfect, it won't be in the real meeting either.",
    "We can start the meeting in five minutes.",
    "I have not seen that document yet.",
]


def make_router(bidirectional: bool = True) -> DirectionRouter:
    return DirectionRouter(Direction("tr", "en"), bidirectional=bidirectional)


@pytest.mark.parametrize("line", TR_LINES)
def test_turkish_is_routed_to_english(line: str) -> None:
    decision = make_router().route(line)
    assert decision.direction == Direction("tr", "en")
    assert decision.reason == "detected"


@pytest.mark.parametrize("line", EN_LINES)
def test_english_is_routed_to_turkish(line: str) -> None:
    """Canlı testin ana bulgusu: bu satırlar önce EN→EN'e düşüyordu."""
    decision = make_router().route(line)
    assert decision.direction == Direction("en", "tr")
    assert decision.reason == "detected"


def test_source_and_target_can_never_be_equal() -> None:
    """Papağan yapısal olarak imkânsız: kaynak == hedef üretilemez."""
    router = make_router()
    for line in TR_LINES + EN_LINES + ["Okay.", "", "12 %40", "Mmm..."]:
        decision = router.route(line)
        assert decision.direction.source_lang != decision.direction.target_lang


def test_unknown_text_falls_back_to_default_direction() -> None:
    decision = make_router().route("...")
    assert decision.direction == Direction("tr", "en")
    assert decision.reason == "fallback_unknown"


def test_fixed_mode_keeps_the_old_single_direction_behaviour() -> None:
    decision = make_router(bidirectional=False).route(EN_LINES[0])
    assert decision.direction == Direction("tr", "en")
    assert decision.reason == "fixed"


def test_default_direction_can_be_english_first() -> None:
    router = DirectionRouter(Direction("en", "tr"))
    assert router.route("...").direction == Direction("en", "tr")
    assert router.route(TR_LINES[0]).direction == Direction("tr", "en")


@pytest.mark.parametrize("bad", [Direction("tr", "tr"), Direction("tr", "de")])
def test_invalid_pairs_are_rejected_early(bad: Direction) -> None:
    with pytest.raises(ValueError):
        DirectionRouter(bad)


def test_realtime_stt_omits_language_when_direction_is_auto() -> None:
    """Dil sabitlenirse sağlayıcı karşı tarafın dilini de zorla çevirir."""
    from representative.realtime_stt import RealtimeSTTStream

    assert "language" not in RealtimeSTTStream(language=None).transcription_config()
    assert RealtimeSTTStream(language="tr").transcription_config()["language"] == "tr"


class EchoTranslator:
    """Yön etiketini görünür kılan sahte çevirmen (ağ yok)."""

    def translate(self, utterance: Utterance) -> TranslationResult:
        text = "Bu bir çeviridir." if utterance.target_lang == "tr" else "This is a translation."
        return TranslationResult(text=text, confidence=0.95, provider="fake")


def test_mixed_conversation_alternates_direction_per_utterance() -> None:
    """İki insanlı toplantının sentetik provası: sırayla TR ve EN konuşulur."""
    router = make_router()
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=EchoTranslator(),
        tts=type("T", (), {"speak": lambda self, text, lang: None})(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=lambda: 0.0,
    )
    for tr_line, en_line in zip(TR_LINES, EN_LINES):
        for line in (tr_line, en_line):
            decision = router.route(line)
            pipeline.process(
                Utterance(
                    text=line,
                    source_lang=decision.direction.source_lang,
                    target_lang=decision.direction.target_lang,
                    speech_end_ts=0.0,
                )
            )

    directions = [(r.source_lang, r.target_lang) for r in transcript.records]
    assert directions == [("tr", "en"), ("en", "tr")] * 3
    # Her söz teslim edildi: yön doğruysa çıktı-dili post-check hiçbirini düşürmez.
    assert all(r.delivered for r in transcript.records)
