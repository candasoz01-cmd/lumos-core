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
