"""Slice tests T1-T6 for the Representative Faz 0 local translation pipeline."""

from __future__ import annotations

import pytest

from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Utterance,
    summarize_latencies_ms,
)


class StubTranslator:
    def __init__(self, text: str, confidence: float | None) -> None:
        self._result = TranslationResult(text=text, confidence=confidence, provider="stub")

    def translate(self, utterance: Utterance) -> TranslationResult:
        return self._result


class RecordingTTS:
    def __init__(self) -> None:
        self.spoken: list[tuple[str, str]] = []

    def speak(self, text: str, lang: str) -> None:
        self.spoken.append((text, lang))


class FakeClock:
    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def make_utterance(text: str = "yarın görüşürüz", speech_end: float = 10.0) -> Utterance:
    return Utterance(text=text, source_lang="tr", target_lang="en", speech_end_ts=speech_end)


def run_pipeline(translator, speech_end=10.0, clock_at=10.5, text="yarın görüşürüz"):
    transcript = BilingualTranscript()
    flags = []
    pipeline = InterpreterPipeline(
        translator=translator,
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        on_flag=flags.append,
        clock=FakeClock(clock_at),
    )
    record = pipeline.process(make_utterance(text=text, speech_end=speech_end))
    return record, transcript, flags


def test_t1_low_confidence_is_flagged_not_silent():
    record, _, flags = run_pipeline(StubTranslator("see you tomorrow", confidence=0.4))
    assert record.flagged is True
    assert record.flag_reason == "below_threshold"
    assert flags == [record]  # uyarı kancası tetiklendi


def test_t2_missing_confidence_is_conservatively_flagged():
    record, _, flags = run_pipeline(StubTranslator("see you tomorrow", confidence=None))
    assert record.flagged is True
    assert record.flag_reason == "no_confidence_signal"
    assert len(flags) == 1


def test_high_confidence_is_not_flagged():
    record, _, flags = run_pipeline(StubTranslator("see you tomorrow", confidence=0.95))
    assert record.flagged is False
    assert flags == []


def test_t3_pipeline_delivers_translator_output_verbatim():
    translator = StubTranslator("see you tomorrow", confidence=0.95)
    transcript = BilingualTranscript()
    tts = RecordingTTS()
    pipeline = InterpreterPipeline(
        translator=translator,
        tts=tts,
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=FakeClock(10.5),
    )
    record = pipeline.process(make_utterance())
    assert tts.spoken == [("see you tomorrow", "en")]
    assert record.translated_text == "see you tomorrow"


def test_t4_commitment_sentence_passes_through_unaltered():
    # E-sınıfı vaka (kurucu, 2026-08-14): para/hukuk/taahhüt cümlesi eksiksiz
    # aktarılır, pipeline yeni taahhüt ekleyemez. Anlam düzeyi Aşama C'de insanla.
    commitment_tr = "Sözleşmeyi 50.000 dolara imzalayacağız ve teslim 1 Ekim."
    commitment_en = "We will sign the contract for $50,000 and delivery is October 1."
    record, transcript, _ = run_pipeline(
        StubTranslator(commitment_en, confidence=0.9), text=commitment_tr
    )
    assert record.translated_text == commitment_en
    assert record.source_text == commitment_tr
    assert transcript.records[-1].translated_text == commitment_en


def test_t5_transcript_is_append_only_and_complete():
    record, transcript, _ = run_pipeline(StubTranslator("see you tomorrow", confidence=0.4))
    assert transcript.records == (record,)
    entry = transcript.records[0]
    assert entry.source_lang == "tr" and entry.target_lang == "en"
    assert entry.confidence == 0.4 and entry.flagged is True
    assert "⚠ düşük güven" in transcript.to_markdown()
    with pytest.raises(AttributeError):
        transcript.records.append  # tuple: dışarıdan mutasyon yolu yok


def test_t6_latency_measurement_and_median():
    record, transcript, _ = run_pipeline(
        StubTranslator("see you tomorrow", confidence=0.9), speech_end=10.0, clock_at=10.5
    )
    assert record.latency_ms == pytest.approx(500.0)
    summary = summarize_latencies_ms(transcript)
    assert summary["count"] == 1
    assert summary["median_ms"] == pytest.approx(500.0)


def test_gate_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        ConfidenceGate(1.5)


def test_transcript_jsonl_roundtrip():
    import json

    record, transcript, _ = run_pipeline(StubTranslator("see you tomorrow", confidence=0.4))
    lines = transcript.to_jsonl().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["source_text"] == record.source_text
    assert data["translated_text"] == "see you tomorrow"
    assert data["flagged"] is True and data["confidence"] == 0.4


def test_incremental_jsonl_append_is_crash_safe(tmp_path):
    # 2026-08-14 stres testi bulgusu: kayıt yalnız temiz çıkışta yazılırsa
    # çökmede tüm prova verisi kaybolur; her söz anında diske düşmeli.
    import json

    path = str(tmp_path / "prova.jsonl")
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("see you tomorrow", confidence=0.9),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        on_record=lambda r: BilingualTranscript.append_jsonl(path, r),
        clock=FakeClock(10.5),
    )
    pipeline.process(make_utterance("birinci cümle"))
    pipeline.process(make_utterance("ikinci cümle"))
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["source_text"] == "birinci cümle"
    assert json.loads(lines[1])["source_text"] == "ikinci cümle"


def test_utterance_context_reaches_translator():
    seen = {}

    class ContextSpy:
        def translate(self, utterance):
            seen["context"] = utterance.context
            return TranslationResult(text="ok", confidence=0.9, provider="spy")

    pipeline = InterpreterPipeline(
        translator=ContextSpy(),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=BilingualTranscript(),
        clock=FakeClock(10.5),
    )
    utt = Utterance(
        text="devam cümlesi",
        source_lang="tr",
        target_lang="en",
        speech_end_ts=10.0,
        context=("önceki cümle",),
    )
    pipeline.process(utt)
    assert seen["context"] == ("önceki cümle",)


def _run_with_tts(translator_text: str, confidence: float | None):
    """Meta-sızıntı testleri TTS'e ulaşan metni görmek zorunda."""
    tts = RecordingTTS()
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator(translator_text, confidence),
        tts=tts,
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=FakeClock(10.5),
    )
    record = pipeline.process(make_utterance())
    return record, tts


# Canlı insan testi 4 (2026-08-17): üç gerçek meta-sızıntı vakası — iç güven
# etiketi botun sesinden toplantıya okundu. Bu vakalar birebir sabitlenir.
@pytest.mark.parametrize(
    "leaked",
    ["LOW", "Low", "Translation not clear; LOW confidence.", "low confidence"],
)
def test_meta_output_is_never_spoken(leaked):
    record, tts = _run_with_tts(leaked, 0.2)
    assert tts.spoken == []
    assert record.delivered is False
    assert record.flagged is True
    assert record.flag_reason == "meta_output"
    # Denetim izi: metin transkriptte aynen kalır, yalnız seslendirilmez.
    assert record.translated_text == leaked


@pytest.mark.parametrize(
    "legit",
    [
        "We have full confidence in this plan.",
        "The low offer was rejected.",
        "Lower the price to fifty thousand dollars.",
    ],
)
def test_real_translations_containing_low_or_confidence_are_delivered(legit):
    record, tts = _run_with_tts(legit, 0.9)
    assert tts.spoken == [(legit, "en")]
    assert record.delivered is True
    assert record.flag_reason == "ok"

class QueueClock:
    def __init__(self, values: list[float]) -> None:
        self._values = list(values)
        self._i = 0

    def __call__(self) -> float:
        value = self._values[min(self._i, len(self._values) - 1)]
        self._i += 1
        return value


def test_stage_timestamps_speech_end_to_first_audio():
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("see you tomorrow", confidence=0.95),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=QueueClock([10.8, 10.8, 12.0]),
    )
    record = pipeline.process(
        Utterance(
            text="yarın görüşürüz",
            source_lang="tr",
            target_lang="en",
            speech_end_ts=10.0,
            stt_final_ts=10.4,
        )
    )
    assert record.stt_ms == pytest.approx(400.0)
    assert record.translate_ms == pytest.approx(400.0)
    assert record.tts_to_first_audio_ms == pytest.approx(1200.0)
    assert record.e2e_first_audio_ms == pytest.approx(2000.0)
    assert record.latency_ms == pytest.approx(2000.0)


def test_p50_p90_and_largest_wait_identify_tts():
    from representative.pipeline import UtteranceRecord

    transcript = BilingualTranscript()
    # Five utterances: TTS first-audio is the dominant wait.
    samples = (1800.0, 1900.0, 2000.0, 2100.0, 5000.0)
    for i, tts_ms in enumerate(samples):
        transcript.append(
            UtteranceRecord(
                source_text=f"s{i}",
                source_lang="tr",
                translated_text=f"t{i}",
                target_lang="en",
                confidence=0.9,
                flagged=False,
                flag_reason="ok",
                latency_ms=400.0 + 300.0 + tts_ms,
                recorded_at=0.0,
                stt_ms=400.0,
                translate_ms=300.0,
                tts_to_first_audio_ms=tts_ms,
                e2e_first_audio_ms=700.0 + tts_ms,
            )
        )
    summary = summarize_latencies_ms(transcript)
    assert summary["count"] == 5
    assert summary["largest_wait"] == "tts_to_first_audio"
    assert summary["p50_ms"] == pytest.approx(2700.0)
    assert summary["p90_ms"] == pytest.approx(4540.0)
    assert summary["first_audio_budget_pass"] is False


def test_historical_prova_does_not_pass_new_budget():
    """2026-08-14 test 3: median 3.49s p90 5.79s — new target 2.5/4. Do not PASS."""
    from representative.latency import evaluate_first_audio_budget
    from representative.pipeline import UtteranceRecord

    transcript = BilingualTranscript()
    # Ten samples whose p50≈3490 and p90≈5790 (linear interp on sorted list).
    e2e = [2800, 3000, 3200, 3400, 3490, 3600, 4000, 4800, 5790, 7190]
    for i, ms in enumerate(e2e):
        transcript.append(
            UtteranceRecord(
                source_text=f"s{i}",
                source_lang="tr",
                translated_text=f"t{i}",
                target_lang="en",
                confidence=0.9,
                flagged=False,
                flag_reason="ok",
                latency_ms=ms,
                recorded_at=0.0,
                e2e_first_audio_ms=ms,
            )
        )
    summary = summarize_latencies_ms(transcript)
    budget = evaluate_first_audio_budget(
        summary["p50_ms"], summary["p90_ms"], count=summary["count"]
    )
    assert budget["pass"] is False
    assert summary["first_audio_budget_pass"] is False
    assert summary["p50_ms"] > 2500
    assert summary["p90_ms"] > 4000


def test_budget_pass_requires_both_targets_and_nonempty():
    from representative.latency import evaluate_first_audio_budget

    assert evaluate_first_audio_budget(0.0, 0.0, count=0)["pass"] is False
    assert evaluate_first_audio_budget(2400.0, 3900.0, count=8)["pass"] is True
    assert evaluate_first_audio_budget(2400.0, 4100.0, count=8)["pass"] is False
    assert evaluate_first_audio_budget(2600.0, 3900.0, count=8)["pass"] is False


# --- Kalem 4: zamanlama alanları tek ondalığa yuvarlanır ---------------------
# Kurucu kararı (2026-08-24). Gerçek prova kaydında süre alanları satırın
# %44'ünü tutuyordu ve "latency_ms": 9983.732249998866 gibi yazılıyordu;
# milisaniye altı hassasiyet ölçülmüyor.


def test_timing_fields_are_derived_from_the_record_not_hand_listed():
    """Türetme testi: kural kaynağı `UtteranceRecord`'un kendisi olmalı.

    Elle tutulan bir liste, ileride eklenen bir `*_ms` alanını sessizce tam
    hassasiyette bırakırdı. İki yönde de kilitlenir: listedeki her ad gerçek
    bir alan, `_ms` ile biten her alan da listede.
    """
    import dataclasses

    from representative.pipeline import TIMING_FIELDS, UtteranceRecord

    names = {f.name for f in dataclasses.fields(UtteranceRecord)}
    assert set(TIMING_FIELDS) <= names, "listede var olmayan alan adı yok"
    assert {n for n in names if n.endswith("_ms")} <= set(TIMING_FIELDS)
    assert "recorded_at" in TIMING_FIELDS, "saniye cinsinden damga da yuvarlanır"


def test_every_timing_field_is_rounded_at_record_creation():
    from representative.pipeline import TIMING_FIELDS, UtteranceRecord

    noisy = 9983.732249998866
    record = UtteranceRecord(
        source_text="s",
        source_lang="tr",
        translated_text="t",
        target_lang="en",
        confidence=0.9,
        flagged=False,
        flag_reason="ok",
        latency_ms=noisy,
        recorded_at=1234.5678901,
        postcheck_ms=12.345678,
        stt_ms=1.26,
        translate_ms=4001.049,
        tts_to_first_audio_ms=0.04,
        e2e_first_audio_ms=noisy,
    )
    for name in TIMING_FIELDS:
        value = getattr(record, name)
        assert round(value, 1) == value, f"{name} tek ondalığa yuvarlanmadı"
    assert record.latency_ms == 9983.7
    assert record.recorded_at == 1234.6
    assert record.stt_ms == 1.3
    assert record.tts_to_first_audio_ms == 0.0


def test_confidence_is_not_rounded():
    """Yuvarlama YALNIZ zamanlama alanlarında; güven skoru olduğu gibi kalır."""
    from representative.pipeline import UtteranceRecord

    record = UtteranceRecord(
        source_text="s",
        source_lang="tr",
        translated_text="t",
        target_lang="en",
        confidence=0.912345,
        flagged=False,
        flag_reason="ok",
        latency_ms=1.0,
        recorded_at=0.0,
        language_detection_confidence=0.87654,
    )
    assert record.confidence == 0.912345
    assert record.language_detection_confidence == 0.87654


def test_rounding_happens_when_the_record_is_built_not_during_measurement():
    """Ara hesaplar tam hassasiyette kalır: aşama toplamı e2e'yi tutturmalı.

    Saat değerleri yuvarlanmış olsaydı (hesap sırasında yuvarlama) her aşamada
    ±0.05 ms'lik hata birikirdi. Kayıt üretilirken yuvarlandığı için her alan
    kendi TAM değerinden bir kez kısalır.
    """

    class _Clock:
        def __init__(self, values):
            self._values = list(values)

        def __call__(self):
            return self._values.pop(0) if len(self._values) > 1 else self._values[0]

    # speech_end=0; stt_final=0.0004003s; translation_ready/tts/first_audio
    stamps = [0.0004003003, 0.0004003003, 1.2345678901]
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("see you tomorrow", confidence=0.9),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=_Clock(stamps),
    )
    record = pipeline.process(
        Utterance(
            text="yarın görüşürüz",
            source_lang="tr",
            target_lang="en",
            speech_end_ts=0.0,
            stt_final_ts=0.0004003003,
        )
    )
    stage_sum = record.stt_ms + record.translate_ms + record.tts_to_first_audio_ms
    assert stage_sum == pytest.approx(record.e2e_first_audio_ms, abs=0.15)
    assert record.stt_ms == 0.4


def test_jsonl_lines_carry_at_most_one_decimal(tmp_path):
    import json

    from representative.pipeline import TIMING_FIELDS

    path = str(tmp_path / "prova.jsonl")
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("see you tomorrow", confidence=0.9),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        on_record=lambda r: BilingualTranscript.append_jsonl(path, r),
        clock=FakeClock(10.5123456789),
    )
    pipeline.process(make_utterance("yarın görüşürüz", speech_end=0.0123456789))
    with open(path, encoding="utf-8") as f:
        data = json.loads(f.read().splitlines()[0])
    for name in TIMING_FIELDS:
        text = repr(data[name])
        assert len(text.split(".")[1]) <= 1, f"{name} dosyaya uzun yazıldı: {text}"


def test_unspoken_records_are_rounded_too():
    """`record_unspoken()` de aynı yoldan geçer — ikinci bir kayıt yolu yok."""
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("x", confidence=0.9),
        tts=RecordingTTS(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=FakeClock(4321.987654321),
    )
    record = pipeline.record_unspoken("What?", flag_reason="fallback_unknown")
    assert record.recorded_at == 4322.0
