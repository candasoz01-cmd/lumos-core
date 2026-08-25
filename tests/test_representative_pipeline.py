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


# --------------------------------------------------------------------------
# Alt-aşama kırılımı kaydı (2026-08-25). Ölçüm işi: `record_unspoken()` bu
# alanların hiçbirini yazmaz, bu yüzden hepsi VARSAYILANLI olmak zorundadır.
# --------------------------------------------------------------------------


def test_record_carries_tts_substages_and_they_sum_to_the_parent_stage():
    from representative.tts_playback import TtsPlayback

    class _StampingTts:
        def speak(self, text, lang):
            # tts_start 20.0; synth 0.8 sn, kapı 0.1 sn, teslim 0.6 sn.
            return TtsPlayback(
                tts_start_ts=20.0,
                first_audio_ts=21.5,
                chunks_planned=1,
                chunks_started=1,
                synth_done_ts=20.8,
                gate_acquired_ts=20.9,
                deliver_done_ts=21.5,
            )

    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("see you", confidence=0.95),
        tts=_StampingTts(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
    )
    record = pipeline.process(
        Utterance(text="görüşürüz", source_lang="tr", target_lang="en", speech_end_ts=19.0)
    )

    assert record.tts_synth_ms == pytest.approx(800.0)
    assert record.tts_gate_wait_ms == pytest.approx(100.0)
    assert record.tts_deliver_ms == pytest.approx(600.0)
    assert record.tts_to_first_audio_ms == pytest.approx(1500.0)
    parts = record.tts_synth_ms + record.tts_gate_wait_ms + record.tts_deliver_ms
    assert parts == pytest.approx(record.tts_to_first_audio_ms)


def test_record_unspoken_still_builds_without_any_timing_fields():
    """Alt-aşamalar ZORUNLU olsaydı bu yol TypeError ile patlardı."""

    class _NeverCalledTts:
        def speak(self, text, lang):  # pragma: no cover - çağrılmamalı
            raise AssertionError("record_unspoken TTS'e dokunmamalı")

    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("x", confidence=1.0),
        tts=_NeverCalledTts(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
    )
    record = pipeline.record_unspoken("What?", flag_reason="fallback_unknown")

    assert record.delivered is False
    assert (record.tts_synth_ms, record.tts_gate_wait_ms, record.tts_deliver_ms) == (
        0.0,
        0.0,
        0.0,
    )


def test_unstamped_tts_leaves_substages_zero_without_breaking_parent_stage():
    """Damgasız oynatıcı (stub/eski TTS): üst aşama eskisi gibi hesaplanır."""
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=StubTranslator("see you", confidence=0.95),
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

    assert record.tts_to_first_audio_ms == pytest.approx(1200.0)
    assert (record.tts_synth_ms, record.tts_gate_wait_ms, record.tts_deliver_ms) == (
        0.0,
        0.0,
        0.0,
    )


def test_summary_substage_p50_ignores_unspoken_records():
    """`records` değil `measured`: sessiz satırlar üçünü birden aşağı çekerdi."""
    from representative.pipeline import UtteranceRecord

    transcript = BilingualTranscript()
    for i in range(6):
        transcript.append(
            UtteranceRecord(
                source_text=f"s{i}",
                source_lang="tr",
                translated_text=f"t{i}",
                target_lang="en",
                confidence=0.9,
                flagged=False,
                flag_reason="ok",
                latency_ms=3000.0,
                recorded_at=0.0,
                stt_ms=500.0,
                translate_ms=1000.0,
                tts_to_first_audio_ms=1500.0,
                tts_synth_ms=1200.0,
                tts_gate_wait_ms=20.0,
                tts_deliver_ms=280.0,
                e2e_first_audio_ms=3000.0,
            )
        )
    clean = summarize_latencies_ms(transcript)

    for i in range(6):
        transcript.append(
            UtteranceRecord(
                source_text=f"sessiz{i}",
                source_lang="",
                translated_text="",
                target_lang="",
                confidence=None,
                flagged=True,
                flag_reason="fallback_unknown",
                latency_ms=0.0,
                recorded_at=0.0,
                delivered=False,
            )
        )
    polluted = summarize_latencies_ms(transcript)

    assert clean["tts_synth_p50_ms"] == pytest.approx(1200.0)
    assert clean["tts_gate_wait_p50_ms"] == pytest.approx(20.0)
    assert clean["tts_deliver_p50_ms"] == pytest.approx(280.0)
    for key in ("tts_synth_p50_ms", "tts_gate_wait_p50_ms", "tts_deliver_p50_ms"):
        assert polluted[key] == clean[key], f"{key} sessiz kayıtlarla deflate oldu"
    assert polluted["count"] == 12, "olaylar sayımda görünmeye devam etmeli"


def test_empty_measured_summary_still_exposes_substage_keys():
    """Yalnız sessiz kayıt: anahtarlar var, hepsi 0.0, PASS uydurulmaz."""
    from representative.pipeline import UtteranceRecord

    transcript = BilingualTranscript()
    transcript.append(
        UtteranceRecord(
            source_text="What?",
            source_lang="",
            translated_text="",
            target_lang="",
            confidence=None,
            flagged=True,
            flag_reason="fallback_unknown",
            latency_ms=0.0,
            recorded_at=0.0,
            delivered=False,
        )
    )
    summary = summarize_latencies_ms(transcript)

    assert summary["tts_synth_p50_ms"] == 0.0
    assert summary["tts_gate_wait_p50_ms"] == 0.0
    assert summary["tts_deliver_p50_ms"] == 0.0
    assert summary["first_audio_budget_pass"] is False
