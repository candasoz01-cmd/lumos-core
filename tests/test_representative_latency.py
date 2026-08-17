"""Gecikme ölçüm altyapısı testleri (canlı insan testi 4 sonrası, 2026-08-17).

Canlı testin sayıları (p50 2.13 sn GEÇTİ, p90 7.49 sn KALDI, max 15.07 sn)
sentetik olarak yeniden üretilir: çözümleyici o kayda "KALDI" demek zorunda.
"""

import json

import pytest

from representative.latency import P50_TARGET_MS, P90_TARGET_MS, analyze, format_report, load_records
from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Utterance,
    percentile_ms,
    summarize_latencies_ms,
)


def test_percentile_is_linear_interpolated() -> None:
    """Tek tanım: Lumos #343 yamasının doğrusal yüzdeliği.

    (Bu dosya önce en-yakın-sıra kullanıyordu; bütçe kararı ile çözümleyici
    aynı sayıyı vermek zorunda olduğu için yamanın tanımı esas alındı.)
    """
    values = [1.0, 2.0, 3.0, 4.0, 10.0]
    assert percentile_ms(values, 50) == 3.0
    assert percentile_ms(values, 100) == 10.0
    assert percentile_ms([], 90) == 0.0
    assert percentile_ms([5.0], 90) == 5.0
    assert percentile_ms([0.0, 10.0], 50) == 5.0


def make_records(latencies_ms: list[float], direction: tuple[str, str] = ("tr", "en")) -> list[dict]:
    return [
        {
            "source_text": f"söz {i}",
            "source_lang": direction[0],
            "target_lang": direction[1],
            "latency_ms": value,
            "delivered": True,
            "flag_reason": "ok",
            "e2e_first_audio_ms": value,
            "stt_ms": value * 0.2,
            "translate_ms": value * 0.4,
            "tts_to_first_audio_ms": value * 0.3,
            "postcheck_ms": 0.0,
        }
        for i, value in enumerate(latencies_ms)
    ]


def test_live_test_4_numbers_are_reported_as_failed() -> None:
    """p50 hedefte, p90 hedef dışı → sonuç KALDI olmalı (kısmi geçiş yok)."""
    latencies = [2130.0] * 53 + [7490.0] * 6 + [15070.0]
    report = analyze(make_records(latencies))
    assert report.p50_ok is True
    assert report.p90_ok is False
    assert report.passed is False
    assert report.max_ms == 15070.0


def test_healthy_measurement_passes() -> None:
    report = analyze(make_records([1800.0] * 50 + [3200.0] * 10))
    assert report.p50_ms <= P50_TARGET_MS
    assert report.p90_ms <= P90_TARGET_MS
    assert report.passed is True


def test_targets_can_be_overridden() -> None:
    latencies = [2130.0] * 53 + [7490.0] * 7
    assert analyze(make_records(latencies)).passed is False
    assert analyze(make_records(latencies), p90_target_ms=8000.0).passed is True


def test_direction_breakdown_separates_the_two_ways() -> None:
    records = make_records([1000.0, 1200.0], ("tr", "en")) + make_records(
        [6000.0, 7000.0], ("en", "tr")
    )
    report = analyze(records)
    assert report.by_direction["tr->en"]["count"] == 2
    assert report.by_direction["en->tr"]["count"] == 2
    assert report.by_direction["en->tr"]["p90_ms"] == pytest.approx(6900.0)
    # Tek yön iyiyken diğeri kötüyse toplam sayı bunu gizlememeli.
    assert report.by_direction["tr->en"]["p90_ms"] < report.by_direction["en->tr"]["p90_ms"]


def test_empty_and_corrupt_lines_do_not_break_analysis(tmp_path) -> None:
    path = tmp_path / "prova.jsonl"
    good = json.dumps({"latency_ms": 1000.0, "source_lang": "tr", "target_lang": "en"})
    path.write_text(f"{good}\n\n{{bozuk json\n{good}\n", encoding="utf-8")
    records = load_records(str(path))
    assert len(records) == 2
    assert analyze(records).count == 2


def test_report_names_the_slowest_utterances() -> None:
    records = make_records([1000.0, 9000.0])
    records[1]["source_text"] = "çok uzun süren cümle"
    text = format_report(analyze(records))
    assert "çok uzun süren cümle" in text
    assert "KALDI" in text


def test_empty_file_reports_no_records() -> None:
    assert "Kayıt yok" in format_report(analyze([]))
    assert analyze([]).passed is False


class SlowTranslator:
    """Ölçülebilir aşama süresi üreten sahte çevirmen (sahte saatle)."""

    def __init__(self, clock) -> None:
        self._clock = clock

    def translate(self, utterance: Utterance) -> TranslationResult:
        self._clock.advance(1.5)
        return TranslationResult(text="Hello.", confidence=0.9, provider="stub")


class SlowTTS:
    def __init__(self, clock) -> None:
        self._clock = clock

    def speak(self, text: str, lang: str) -> None:
        self._clock.advance(2.0)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def test_stage_timings_are_recorded_separately() -> None:
    """Aşama damgaları ayrı; toplam artık söz sonu → İLK SES (first-audio)."""
    clock = FakeClock()
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=SlowTranslator(clock),
        tts=SlowTTS(clock),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=clock,
    )
    record = pipeline.process(
        Utterance(text="Merhaba.", source_lang="tr", target_lang="en", speech_end_ts=0.0)
    )
    assert record.translate_ms == 1500.0
    # Chunked TTS'te ölçülen "paragraf bitti" değil, ilk klibin duyulduğu an.
    assert record.tts_to_first_audio_ms == 2000.0
    # latency_ms artık söz sonu → first-audio (Lumos #343 ile bilinçli değişti;
    # eski tanım yalnız çeviri-hazır'ı ölçüyor, TTS beklemesini gizliyordu).
    assert record.latency_ms == 3500.0
    assert record.e2e_first_audio_ms == 3500.0


def test_summary_now_carries_p50_and_p90() -> None:
    clock = FakeClock()
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=SlowTranslator(clock),
        tts=SlowTTS(clock),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        clock=clock,
    )
    for _ in range(3):
        pipeline.process(
            Utterance(
                text="Merhaba.", source_lang="tr", target_lang="en", speech_end_ts=clock.now
            )
        )
    summary = summarize_latencies_ms(transcript)
    assert summary["count"] == 3
    assert "p50_ms" in summary and "p90_ms" in summary
    assert summary["p90_ms"] >= summary["p50_ms"]
