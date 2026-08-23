"""Kalem 2 testleri: deterministik dil tespiti + tek-retry + fail-closed."""

from __future__ import annotations

import pytest

from representative.langcheck import detect_lang
from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Utterance,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Test 6'nın gerçek yön-kaçağı çıktıları:
        ("English is better than such incomplete translation. We will measure.", "en"),
        ("Are you there?", "en"),
        ("My forty percent.", "en"),
        # Doğru TR çıktılar:
        ("Ödemenin %40'ı onaylandı, geri kalanı teslimatta.", "tr"),
        ("$50,000'lık sözleşmeyi imzalayacağız ve teslimat 1 Ekim'de yapılacak.", "tr"),
        ("Toplantı bildirimini yarın sabah göndereceğim.", "tr"),
        # Kısa çıktılar: karşı sinyal sıfırsa tek kelime yeter
        ("Okay.", "en"),
        ("Evet.", "tr"),
        # Sinyalsiz: unknown (bloklanmaz)
        ("Rit.", "unknown"),
        ("five hundred.", "unknown"),
    ],
)
def test_detect_lang_on_real_field_outputs(text, expected):
    assert detect_lang(text) == expected


# Genişletme (2026-08-23): canlı provada sinyalsiz kalıp sessizce varsayılan
# yöne düşen gerçek cümleler.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hey Hasan, speak English!", "en"),  # provada unknown'dı → TR sayıldı
        ("What's up, uncle?", "en"),
        ("That's right.", "en"),
        ("Bekliyorum.", "tr"),  # biçimbirim izi: -yorum
        ("Bakıyordum.", "tr"),
        ("Gelecekmiş.", "tr"),
        ("Tamam.", "tr"),
        # Faz 0 çifti dışındaki dil hâlâ unknown olmalı — tekrar istenecek.
        ("네.", "unknown"),
        ("Rit.", "unknown"),
    ],
)
def test_detect_lang_after_signal_expansion(text, expected):
    assert detect_lang(text) == expected


def test_domain_words_are_not_memorised_from_the_rehearsal_log():
    """Kaydı ezberlemek çözüm değil: alan sözcüğü sinyal sayılmaz.

    "Translate." provada unknown'dı; doğru çözüm onu sözlüğe eklemek değil,
    parçayı devamıyla birleştirmektir (segmentation dilimi).
    """
    assert detect_lang("Translate.") == "unknown"


class FlippingTranslator:
    """İlk çağrıda yanlış dilde, sonraki çağrılarda istenen çıktı."""

    def __init__(self, wrong: str, right: str) -> None:
        self._outputs = [wrong, right]
        self.calls = 0

    def translate(self, utterance: Utterance) -> TranslationResult:
        text = self._outputs[min(self.calls, len(self._outputs) - 1)]
        self.calls += 1
        return TranslationResult(text=text, confidence=0.9, provider="stub")


class RecordingTTS:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str, lang: str) -> None:
        self.spoken.append(text)


def make_pipeline(translator, tts):
    return InterpreterPipeline(
        translator=translator,
        tts=tts,
        gate=ConfidenceGate(0.8),
        transcript=BilingualTranscript(),
    )


EN_WRONG = "The remaining amount will be paid upon delivery."
TR_RIGHT = "Geri kalan tutar teslimatta ödenecek."


def test_single_retry_recovers_wrong_language():
    translator = FlippingTranslator(wrong=EN_WRONG, right=TR_RIGHT)
    tts = RecordingTTS()
    record = make_pipeline(translator, tts).process(
        Utterance(text="kalanı teslimatta ödenecek", source_lang="en", target_lang="tr", speech_end_ts=0.0)
    )
    assert translator.calls == 2  # tam 1 retry
    assert record.delivered is True and record.retried is True
    assert record.postcheck_ms >= 0.0
    assert tts.spoken == [TR_RIGHT]


def test_fail_closed_when_retry_is_also_wrong():
    translator = FlippingTranslator(wrong=EN_WRONG, right=EN_WRONG)
    tts = RecordingTTS()
    record = make_pipeline(translator, tts).process(
        Utterance(text="kalanı teslimatta ödenecek", source_lang="en", target_lang="tr", speech_end_ts=0.0)
    )
    assert translator.calls == 2  # döngü YOK: ikinciden sonra durur
    assert record.delivered is False
    assert record.flagged is True and record.flag_reason == "wrong_output_language"
    assert tts.spoken == []  # TTS'e verilmedi


def test_correct_language_passes_without_retry():
    translator = FlippingTranslator(wrong=TR_RIGHT, right=TR_RIGHT)
    tts = RecordingTTS()
    record = make_pipeline(translator, tts).process(
        Utterance(text="the rest on delivery", source_lang="en", target_lang="tr", speech_end_ts=0.0)
    )
    assert translator.calls == 1
    assert record.retried is False and record.postcheck_ms == 0.0
    assert record.delivered is True


def test_realtime_speech_end_backdates_vad_silence():
    from representative.realtime_stt import speech_end_from_stop_event

    # speech_stopped olayı gerçek söz sonundan VAD sessizliği kadar sonra gelir
    assert speech_end_from_stop_event(100.0, vad_silence_ms=600) == 99.4
    assert speech_end_from_stop_event(50.0, vad_silence_ms=0) == 50.0


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_conf"),
    [
        # Normal iki satırlı format
        ("Merhaba dünya.\nconfidence: 0.9", "Merhaba dünya.", 0.9),
        # Test 7 bug'ı: yalnız güven satırı → metin BOŞ (seslendirilmez)
        ("confidence: 0.3", "", 0.3),
        # Test 7 bug'ı: güven metinle aynı satırda
        ("Ne dedin? confidence: 0.5", "Ne dedin?", 0.5),
        # Güven satırı hiç yok
        ("Sadece çeviri.", "Sadece çeviri.", None),
        # Aralık dışı güven kırpılır
        ("Metin.\nconfidence: 1.7", "Metin.", 1.0),
    ],
)
def test_translator_reply_parsing_is_robust(raw, expected_text, expected_conf):
    from representative.local_rig import OpenAITranslator

    text, conf = OpenAITranslator.parse_reply(raw)
    assert text == expected_text
    assert conf == expected_conf


def test_empty_translation_is_never_spoken():
    class EmptyTranslator:
        def translate(self, utterance):
            return TranslationResult(text="", confidence=0.3, provider="stub")

    tts = RecordingTTS()
    record = make_pipeline(EmptyTranslator(), tts).process(
        Utterance(text="mırıltı", source_lang="en", target_lang="tr", speech_end_ts=0.0)
    )
    assert tts.spoken == []
    assert record.delivered is False
    assert record.flag_reason == "empty_translation"
