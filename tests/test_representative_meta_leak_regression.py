"""Meta-sızıntı regresyon takımı — canlı insan testi 4 bulgusu 3 (2026-08-17).

Canlıda olan: modelin iç güven etiketi çeviri sanıldı ve bot onu toplantıya
sesli okudu ("LOW"). `is_meta_output` kapısı #749'da eklendi; bu dosya kapının
etrafından dolaşan yolları da kapatır ve ölçülen davranışı sabitler:

- etiket hangi biçimde gelirse gelsin (büyük/küçük harf, noktalama, güven
  değeri yüksek olsa bile) sese çıkmaz,
- ham model yanıtından etiketin ayrıştırılma yolu (parse_reply) sınanır,
- eşik altı sözlerin teslim edilmesi ölçülen ve BİLİNÇLİ davranıştır —
  değişecekse karar olarak değişsin diye teste çakılır.

Hepsi botsuz/ağsız: sahte çevirmen + sahte TTS.
"""

import pytest

from representative.local_rig import OpenAITranslator
from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Utterance,
    is_meta_output,
)


class StubTranslator:
    def __init__(self, text: str, confidence: float | None) -> None:
        self._text = text
        self._confidence = confidence

    def translate(self, utterance: Utterance) -> TranslationResult:
        return TranslationResult(text=self._text, confidence=self._confidence, provider="stub")


class RecordingTTS:
    def __init__(self) -> None:
        self.spoken: list[tuple[str, str]] = []

    def speak(self, text: str, lang: str) -> None:
        self.spoken.append((text, lang))


def run(text: str, confidence: float | None, threshold: float = 0.8, target: str = "en"):
    tts = RecordingTTS()
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator(text, confidence),
        tts=tts,
        gate=ConfidenceGate(threshold),
        transcript=transcript,
        clock=lambda: 0.0,
    )
    record = pipeline.process(
        Utterance(
            text="Kaynak cümle.",
            source_lang="en" if target == "tr" else "tr",
            target_lang=target,
            speech_end_ts=0.0,
        )
    )
    return record, tts


# Etiketin canlıda görülen ve görülebilecek biçimleri.
LEAK_FORMS = [
    "LOW",
    "low",
    "Low.",
    "LOW!",
    "  LOW  ",
    "MEDIUM",
    "High",
    "low confidence",
    "LOW CONFIDENCE.",
    "Translation not clear; LOW confidence.",
]


@pytest.mark.parametrize("leaked", LEAK_FORMS)
def test_every_label_form_is_blocked(leaked: str) -> None:
    record, tts = run(leaked, 0.2)
    assert tts.spoken == []
    assert record.flag_reason == "meta_output"


@pytest.mark.parametrize("leaked", LEAK_FORMS)
def test_label_is_blocked_even_with_high_confidence(leaked: str) -> None:
    """Sızıntı yüksek güvenle de geldi: kapı güvene bakmaz."""
    record, tts = run(leaked, 0.99)
    assert tts.spoken == []
    assert record.delivered is False
    assert record.flag_reason == "meta_output"


def test_leaked_label_survives_in_transcript_for_audit() -> None:
    record, _ = run("LOW", 0.2)
    assert record.translated_text == "LOW"


@pytest.mark.parametrize(
    "raw, expected_text, expected_conf",
    [
        # Model yalnız güven satırı döndürdü → metin boş kalır, sese çıkmaz.
        ("confidence: 0.3", "", 0.3),
        # Etiket metin olarak geldi, güven satırı yok → meta kapısı yakalar.
        ("LOW", "LOW", None),
        # Normal yanıt: metin + güven.
        ("Hello everyone.\nconfidence: 0.9", "Hello everyone.", 0.9),
    ],
)
def test_parse_reply_paths_that_led_to_the_leak(raw, expected_text, expected_conf) -> None:
    text, confidence = OpenAITranslator.parse_reply(raw)
    assert text == expected_text
    assert confidence == expected_conf


def test_empty_text_from_confidence_only_reply_is_not_spoken() -> None:
    text, confidence = OpenAITranslator.parse_reply("confidence: 0.3")
    record, tts = run(text, confidence)
    assert tts.spoken == []
    assert record.flag_reason == "empty_translation"


def test_label_only_reply_is_not_spoken_end_to_end() -> None:
    text, confidence = OpenAITranslator.parse_reply("LOW")
    record, tts = run(text, confidence)
    assert tts.spoken == []
    assert record.flag_reason == "meta_output"


# Kapının darlığı: bunlar gerçek toplantı cümleleri, bloklanmamalı.
@pytest.mark.parametrize(
    "legit",
    [
        "Our confidence in the schedule is high.",
        "The low season starts in November.",
        "Highlight the first row, please.",
        "Medium roast, thank you.",
    ],
)
def test_ordinary_sentences_are_not_treated_as_labels(legit: str) -> None:
    assert is_meta_output(legit) is False
    record, tts = run(legit, 0.9)
    assert tts.spoken == [(legit, "en")]


@pytest.mark.parametrize("legit", ["Güvenimiz tam.", "Düşük teklif reddedildi."])
def test_turkish_translations_are_not_treated_as_labels(legit: str) -> None:
    """EN→TR yönünde de kapı dar kalmalı (çift yön routing sonrası gerçek yol)."""
    assert is_meta_output(legit) is False
    record, tts = run(legit, 0.9, target="tr")
    assert tts.spoken == [(legit, "tr")]


def test_below_threshold_utterances_are_still_delivered_by_design() -> None:
    """Canlı testte 60 sözün 23'ü eşik altıydı ve yine de teslim edildi.

    Bu Faz 0'ın BİLİNÇLİ davranışıdır (ConfidenceGate: işaretle, blokla değil —
    toplantıda tercümanın sahibi zaten oradadır). Sessizce değişmesin diye
    çakılıyor: teslim politikası değişecekse karar olarak değişir.
    """
    record, tts = run("A quiet, uncertain sentence.", 0.2)
    assert record.flagged is True
    assert record.flag_reason == "below_threshold"
    assert record.delivered is True
    assert tts.spoken == [("A quiet, uncertain sentence.", "en")]


def test_missing_confidence_signal_is_flagged_but_delivered() -> None:
    record, tts = run("No confidence signal from the provider.", None)
    assert record.flag_reason == "no_confidence_signal"
    assert record.delivered is True
    assert len(tts.spoken) == 1


# Kurucu kararı 2026-08-17 (seçenek C): eşik altı çeviri seslendirilir AMA
# transkript/panelde düşük güven olarak işaretlenir.
def test_low_confidence_is_delivered_and_visibly_marked() -> None:
    from representative.pipeline import flag_label

    record, tts = run("A quiet, uncertain sentence.", 0.2)
    assert record.delivered is True  # (b) sessizlik değil
    assert len(tts.spoken) == 1
    assert flag_label(record) == "⚠ düşük güven"  # (a) işaretsiz teslim de değil


def test_transcript_separates_heard_from_swallowed() -> None:
    """"İşaretli ama duyuldu" ile "hiç seslendirilmedi" aynı görünmemeli."""
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("A quiet, uncertain sentence.", 0.2),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=lambda: 0.0,
    )
    pipeline.process(
        Utterance(text="Kaynak.", source_lang="tr", target_lang="en", speech_end_ts=0.0)
    )
    InterpreterPipeline(
        translator=StubTranslator("LOW", 0.2),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=lambda: 0.0,
    ).process(Utterance(text="Kaynak 2.", source_lang="tr", target_lang="en", speech_end_ts=0.0))

    table = transcript.to_markdown()
    assert "✓ duyuldu" in table and "⚠ düşük güven" in table
    assert "✕ seslendirilmedi" in table and "iç etiket" in table


def test_every_flag_reason_has_a_human_label() -> None:
    from representative.pipeline import _FLAG_LABELS, flag_label

    for reason in (
        "ok",
        "below_threshold",
        "no_confidence_signal",
        "empty_translation",
        "meta_output",
        "non_translation_output",
        "wrong_output_language",
    ):
        assert reason in _FLAG_LABELS
    # Bilinmeyen sebep sessizce kaybolmaz, ham hâliyle görünür.
    record, _ = run("ok text", 0.9)
    assert flag_label(record) == ""
