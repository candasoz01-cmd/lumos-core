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


# --- 2026-08-24 Meet provası (prova_meet_1.jsonl, 11 kayıt) --------------------
# Bulgu: 11 kaydın TAMAMI source_lang=tr/target_lang=en ile gitti. İçlerinden
# biri İngilizce "What?" idi; tr sanılıp EN'e "çevrildi" ve aynen geri
# seslendirildi (papağan). Kurucu bunu toplantıda fark edip bir sonraki sözde
# söyledi.
#
# Bu testlerin amacı DAVRANIŞI DOĞRU İLAN ETMEK DEĞİL, teşhisi sabitlemektir:
# "What?" yanlış TESPİT edilmedi — tespit hiç karar veremedi (unknown) ve
# yapılandırılmış varsayılan yöne düşüldü. Yani kusur algoritmada değil,
# iki dilli toplantıda yanlış olan SABİT VARSAYILAN yöndedir. Varsayılanın
# ne olacağı ürün kararıdır ve bu testler o karar verildiğinde bilinçli
# olarak güncellenmelidir.

PROVA_MEET_1_TR = [
    "Ne dediğini sen konuşuyorsun habire bir şeyler ama ne diyorsun ben anlamıyorum.",
    "Nasıl dedin yahu, anlayamadım.",
    "Evet, şimdi anladım.",
    "Nasıl bir daha söyle.",
    "Seslerin sakin, güzel, bir öncekine göre daha iyi.",
    "Müzik dinle bakalım biraz.",
    "Ben de what İngilizce onu Türkçeye çevirmen gerekmiyor muydu?",
]
PROVA_MEET_1_EN_SHORT = "What?"


@pytest.mark.parametrize("line", PROVA_MEET_1_TR)
def test_prova_meet_1_turkish_lines_are_detected_not_defaulted(line):
    """TR sözler gerçekten TESPİT edilmeli; varsayılana düşerek değil.

    Aynı sonucu (tr→en) varsayılan da üretirdi; bu yüzden yönü değil
    `reason`ı sınıyoruz — aksi hâlde tespit tamamen bozulsa bile test yeşil
    kalırdı.
    """
    decision = DirectionRouter(Direction("tr", "en")).route(line)
    assert decision.detected == "tr"
    assert decision.reason == "detected"
    assert (decision.direction.source_lang, decision.direction.target_lang) == ("tr", "en")


def test_prova_meet_1_short_turkish_line_is_detected():
    """Kısa TR söz de tespit edilebilmeli — "kısa olan her şey unknown" değil."""
    decision = DirectionRouter(Direction("tr", "en")).route("Evet, şimdi anladım.")
    assert decision.detected == "tr"
    assert decision.reason == "detected"


def test_prova_meet_1_english_what_abstains_and_falls_back_to_default():
    """KUSURUN ta kendisi: "What?" için tespit YANLIŞ değil, YOK.

    `detect_lang` "what" kelimesini EN sözlüğünde bulamaz → skorlar 0-0 →
    unknown. Router da varsayılan yöne (tr→en) düşer. Sonuç kullanıcı
    açısından yanlıştır (EN girdi EN'e "çevrilir"), ama sebep yanlış tespit
    DEĞİL, karar verilemeyen sözde sabit varsayılana düşülmesidir.
    """
    decision = DirectionRouter(Direction("tr", "en")).route(PROVA_MEET_1_EN_SHORT)

    assert decision.detected == "unknown", "tespit yanlış dil dönmedi; hiç karar vermedi"
    assert decision.reason == "fallback_unknown", "varsayılan yön kullanıldı"
    # Provada fiilen kaydedilen (ve yanlış olan) sonuç:
    assert (decision.direction.source_lang, decision.direction.target_lang) == ("tr", "en")


def test_default_direction_decides_the_unknown_case():
    """Sonucun tespitten değil VARSAYILANDAN geldiğinin kanıtı.

    Varsayılan ters çevrildiğinde aynı "What?" girdisi en→tr'ye gider. Bu,
    kusurun konumunu tek başına gösterir: sorun varsayılanın kendisidir.
    """
    decision = DirectionRouter(Direction("en", "tr")).route(PROVA_MEET_1_EN_SHORT)
    assert decision.reason == "fallback_unknown"
    assert (decision.direction.source_lang, decision.direction.target_lang) == ("en", "tr")


def _unspoken_pipeline():
    """Gerçek pipeline; çevirmen ÇAĞRILIRSA test patlar."""

    class _NeverTranslate:
        def translate(self, utterance):
            raise AssertionError("seslendirilmeyen söz çeviriye gönderilmemeliydi")

    class _Tts:
        def __init__(self):
            self.spoken = []

        def speak(self, text, lang):
            self.spoken.append((text, lang))
            return None

    written = []
    tts = _Tts()
    pipeline = InterpreterPipeline(
        translator=_NeverTranslate(),
        tts=tts,
        gate=ConfidenceGate(0.8),
        transcript=BilingualTranscript(),
        on_record=written.append,
    )
    return pipeline, tts, written


def test_unknown_direction_utterance_is_not_spoken_but_is_recorded():
    """Kurucu kararı (2026-08-24): yön belirlenemeyen söz fail-closed.

    Provada "What?" tr sanılıp EN'e "çevrildi" ve aynen geri seslendirildi.
    Artık: ses YOK, ama kaynak metin + gerekçe kayda geçer.
    """
    from collections import deque

    from representative.bot_rig import speak_assembled_turns
    from representative.turns import AssembledTurn

    pipeline, tts, written = _unspoken_pipeline()
    spoken = speak_assembled_turns(
        [
            AssembledTurn(
                text=PROVA_MEET_1_EN_SHORT,
                speech_end_ts=1.0,
                speakable=True,
                reason="complete",
            )
        ],
        pipeline=pipeline,
        router=DirectionRouter(Direction("tr", "en")),
        suppressor=_NeverDrop(),
        recent=deque(),
        now=1.0,
    )

    assert spoken == 0
    assert tts.spoken == [], "papağan geri döndü: söz seslendirilmemeliydi"
    assert len(written) == 1, "susturulan söz kayıtsız kaybolmamalı"
    record = written[0]
    assert record.source_text == PROVA_MEET_1_EN_SHORT
    assert record.delivered is False
    assert record.flag_reason == "fallback_unknown"
    assert record.detected_language == "unknown"
    assert record.translated_text == "", "çeviri hiç yapılmamalıydı"


@pytest.mark.parametrize("line", PROVA_MEET_1_TR)
def test_turkish_lines_are_still_spoken_after_suppression_lands(line):
    """Susturma kapsamı genişlemesin: tespit edilen sözler normal akmalı."""
    from collections import deque

    from representative.bot_rig import speak_assembled_turns
    from representative.turns import AssembledTurn

    class _Echo:
        def translate(self, utterance):
            return TranslationResult(text="translated", confidence=1.0, provider="stub")

    class _Tts:
        def __init__(self):
            self.spoken = []

        def speak(self, text, lang):
            self.spoken.append((text, lang))
            return None

    written = []
    tts = _Tts()
    pipeline = InterpreterPipeline(
        translator=_Echo(),
        tts=tts,
        gate=ConfidenceGate(0.8),
        transcript=BilingualTranscript(),
        on_record=written.append,
    )
    spoken = speak_assembled_turns(
        [AssembledTurn(text=line, speech_end_ts=1.0, speakable=True, reason="complete")],
        pipeline=pipeline,
        router=DirectionRouter(Direction("tr", "en")),
        suppressor=_NeverDrop(),
        recent=deque(),
        now=1.0,
    )
    assert spoken == 1
    assert tts.spoken == [("translated", "en")]
    assert written[0].delivered is True
    assert written[0].direction_reason == "detected"


def test_suppressed_duplicate_leaves_a_record():
    """Tekrar bastırma dalı eskiden konsola bile bir şey basmıyordu."""
    from collections import deque

    from representative.bot_rig import speak_assembled_turns
    from representative.turns import AssembledTurn

    class _AlwaysDrop:
        def should_drop(self, _text, _now):
            return True

    pipeline, tts, written = _unspoken_pipeline()
    spoken = speak_assembled_turns(
        [AssembledTurn(text="Evet.", speech_end_ts=1.0, speakable=True, reason="complete")],
        pipeline=pipeline,
        router=DirectionRouter(Direction("tr", "en")),
        suppressor=_AlwaysDrop(),
        recent=deque(),
        now=1.0,
    )
    assert spoken == 0
    assert tts.spoken == []
    assert [(r.source_text, r.flag_reason, r.delivered) for r in written] == [
        ("Evet.", "suppressed_duplicate", False)
    ]


def test_held_partial_leaves_a_record_without_changing_audio_behaviour():
    """PR #797'nin asıl konusu: tutulan yarım söz artık dosyadan ölçülebilir."""
    from collections import deque

    from representative.bot_rig import speak_assembled_turns
    from representative.turns import AssembledTurn

    pipeline, tts, written = _unspoken_pipeline()
    spoken = speak_assembled_turns(
        [
            AssembledTurn(
                text="Ben de what",
                speech_end_ts=1.0,
                speakable=False,
                reason="hold_timeout",
            )
        ],
        pipeline=pipeline,
        router=DirectionRouter(Direction("tr", "en")),
        suppressor=_NeverDrop(),
        recent=deque(),
        now=1.0,
    )
    assert spoken == 0
    assert tts.spoken == [], "ses davranışı değişmemeli"
    assert [(r.source_text, r.flag_reason) for r in written] == [
        ("Ben de what", "held_partial_hold_timeout")
    ]


class _NeverDrop:
    def should_drop(self, _text, _now):
        return False


def test_direction_reason_is_persisted_into_the_record():
    """Teşhis dosyadan yapılabilmeli: yön/sebep/tespit jsonl'e yazılmalı.

    Provada `reason` yalnız konsola basılıyordu; jsonl'de olmadığı için
    "What?" satırının neden tr→en gittiği dosyadan okunamadı.
    """

    class _Echo:
        def translate(self, utterance):
            return TranslationResult(text=utterance.text, confidence=1.0, provider="stub")

    class _Tts:
        def speak(self, text, lang):
            return None

    pipeline = InterpreterPipeline(
        translator=_Echo(),
        tts=_Tts(),
        gate=ConfidenceGate(0.8),
        transcript=BilingualTranscript(),
    )
    # Seslendirilen yol: yön belirlenemeyen söz artık pipeline'a hiç
    # girmiyor (fail-closed, bkz. üstteki susturma testleri), bu yüzden
    # kalıcılık tespit EDİLEN bir sözle sınanır.
    line = PROVA_MEET_1_TR[2]
    decision = DirectionRouter(Direction("tr", "en")).route(line)
    record = pipeline.process(
        Utterance(
            text=line,
            source_lang=decision.direction.source_lang,
            target_lang=decision.direction.target_lang,
            speech_end_ts=0.0,
            direction_reason=decision.reason,
            detected_language=decision.detected,
        )
    )

    assert record.direction == "tr->en"
    assert record.direction_reason == "detected"
    assert record.detected_language == "tr"
    # Çeviri güveni ile dil-tespit güveni AYRI alanlardır; ikincisi için
    # `detect_lang` kalibre skor üretmediğinden None yazılır.
    assert record.confidence == 1.0
    assert record.language_detection_confidence is None
