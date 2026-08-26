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


# --- Seslendirilmeyen kayıtlar teslim metriklerini kirletmemeli ---------------
# 2026-08-24: fail-closed susturma `delivered=false` satırları üretmeye başladı.
# Bu satırlar çeviri/TTS hattına hiç girmediği için gecikmeleri 0 ms; havuza
# karıştıklarında p50'yi AŞAĞI çekiyorlardı (gerçek ölçüm: 5.41 sn → 4.91 sn,
# yalnız 5 sessiz kayıtla). Kirlenme İYİ yönde olduğu için gözden kaçması
# kolaydı ve fail-closed çalıştıkça büyüyordu.


def make_unspoken(count: int, flag_reason: str = "fallback_unknown") -> list[dict]:
    """record_unspoken() satırının şekli: yön yok, zamanlama yok."""
    return [
        {
            "source_text": f"sessiz {i}",
            "source_lang": "",
            "target_lang": "",
            "translated_text": "",
            "latency_ms": 0.0,
            "delivered": False,
            "flag_reason": flag_reason,
            "e2e_first_audio_ms": 0.0,
            "stt_ms": 0.0,
            "translate_ms": 0.0,
            "tts_to_first_audio_ms": 0.0,
        }
        for i in range(count)
    ]


@pytest.mark.parametrize("unspoken_count", [1, 3, 5, 20])
def test_unspoken_records_do_not_move_latency_percentiles(unspoken_count: int) -> None:
    spoken = make_records([5000.0] * 10 + [8000.0] * 2)
    clean = analyze(spoken)
    polluted = analyze(spoken + make_unspoken(unspoken_count))

    assert polluted.p50_ms == clean.p50_ms
    assert polluted.p90_ms == clean.p90_ms
    assert polluted.max_ms == clean.max_ms


def test_unspoken_records_stay_visible_in_counts_and_flag_summary() -> None:
    """Gizleme YOK: olay sayımda ve işaret dağılımında görünmeye devam eder."""
    report = analyze(make_records([5000.0] * 4) + make_unspoken(3, "held_partial_hold_timeout"))

    assert report.count == 7, "toplam kayıt sayısı olayı saklamamalı"
    assert report.delivered == 4, "gecikme örneklemi yalnız teslim edilenler"
    assert report.by_flag_reason["held_partial_hold_timeout"] == 3


def test_unspoken_records_do_not_create_a_direction_bucket() -> None:
    """Yönü olmayan kayıt yön kırılımında '->' diye kova açmamalı."""
    report = analyze(make_records([5000.0] * 4) + make_unspoken(3))

    assert list(report.by_direction) == ["tr->en"]
    assert report.by_direction["tr->en"]["count"] == 4


def test_unspoken_records_do_not_deflate_stage_breakdown() -> None:
    """Aşama kırılımı en tehlikelisi: ŞEKİL korunurken büyüklükler küçülüyordu."""
    spoken = make_records([5000.0] * 10)
    clean = analyze(spoken)
    polluted = analyze(spoken + make_unspoken(5))

    assert polluted.stage_p50_ms == clean.stage_p50_ms
    assert polluted.largest_wait == clean.largest_wait


def test_all_unspoken_file_does_not_fake_a_pass() -> None:
    """Boş örneklem PASS uydurmaz: p50/p90 0.0 dönerdi, `count > 0` geçirirdi."""
    report = analyze(make_unspoken(4))

    assert report.count == 4
    assert report.delivered == 0
    assert report.passed is False


def test_records_without_delivered_key_are_still_measured() -> None:
    """Eski prova dosyaları (`delivered` alanı yok) aynen okunmaya devam eder."""
    legacy = make_records([5000.0] * 5)
    for record in legacy:
        del record["delivered"]

    report = analyze(legacy)
    assert report.count == 5
    assert report.delivered == 5
    assert report.p50_ms == 5000.0


def test_in_memory_summary_also_excludes_unspoken_records() -> None:
    """`analyze()`'in bellekteki ikizi de aynı ayrımı uygulamalı."""

    class _Echo:
        def translate(self, utterance):
            return TranslationResult(text="ok", confidence=1.0, provider="stub")

    class _Tts:
        def speak(self, text, lang):
            return None

    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=_Echo(),
        tts=_Tts(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
    )
    pipeline.process(Utterance(text="Evet.", source_lang="tr", target_lang="en", speech_end_ts=0.0))
    spoken_only = summarize_latencies_ms(transcript)

    pipeline.record_unspoken("What?", flag_reason="fallback_unknown")
    with_unspoken = summarize_latencies_ms(transcript)

    assert with_unspoken["count"] == 2, "olay sayımda görünmeli"
    assert with_unspoken["p50_ms"] == spoken_only["p50_ms"]
    assert with_unspoken["stt_p50_ms"] == spoken_only["stt_p50_ms"]
    assert with_unspoken["translate_p50_ms"] == spoken_only["translate_p50_ms"]


# --- Kalem 4: yuvarlanmış kayıt çözümleyiciyi kaydırmamalı -------------------
# Yuvarlama KAYIT üretilirken yapılıyor (pipeline.TIMING_DECIMALS). Buradaki
# soru: `percentile_ms`/`analyze` yolu aynı dosyayı yuvarlanmış değerlerle
# okuduğunda aynı cevabı veriyor mu? Yüzdelik iki komşu değerin doğrusal
# ara değeri olduğundan, her değer ≤0.05 ms kaydığında sonuç da ≤0.05 ms kayar
# — yani karar (GEÇTİ/KALDI) asla değişemez.

RAW_LATENCIES = [
    2130.4472849998, 2871.1109999998, 3402.9997310001, 4440.7773100002,
    5411.0028839999, 6090.3324379998, 7490.8880019999, 9983.7322499988,
    1988.1230000001, 2503.6660009998, 3099.9999999999, 4001.0490000002,
]


def _round_timings(records: list[dict]) -> list[dict]:
    fields = (
        "latency_ms", "e2e_first_audio_ms", "stt_ms", "translate_ms",
        "tts_to_first_audio_ms", "postcheck_ms",
    )
    return [{**r, **{f: round(r[f], 1) for f in fields if f in r}} for r in records]


def test_percentiles_are_unchanged_by_one_decimal_rounding() -> None:
    raw = analyze(make_records(RAW_LATENCIES))
    rounded = analyze(_round_timings(make_records(RAW_LATENCIES)))

    assert rounded.p50_ms == pytest.approx(raw.p50_ms, abs=0.05)
    assert rounded.p90_ms == pytest.approx(raw.p90_ms, abs=0.05)
    assert rounded.max_ms == pytest.approx(raw.max_ms, abs=0.05)
    assert rounded.p50_ok is raw.p50_ok
    assert rounded.p90_ok is raw.p90_ok
    assert rounded.passed is raw.passed


def test_stage_breakdown_and_largest_wait_survive_rounding() -> None:
    raw = analyze(make_records(RAW_LATENCIES))
    rounded = analyze(_round_timings(make_records(RAW_LATENCIES)))

    assert rounded.largest_wait == raw.largest_wait
    for stage, value in raw.stage_p50_ms.items():
        assert rounded.stage_p50_ms[stage] == pytest.approx(value, abs=0.05)


def test_percentile_of_rounded_values_stays_within_half_a_tenth() -> None:
    """Doğrudan `percentile_ms` üzerinde: ara değer de ≤0.05 ms kayar."""
    for p in (0, 25, 50, 90, 100):
        raw = percentile_ms(RAW_LATENCIES, p)
        rounded = percentile_ms([round(v, 1) for v in RAW_LATENCIES], p)
        assert rounded == pytest.approx(raw, abs=0.05)


def test_verdict_can_only_change_within_a_twentieth_of_a_millisecond() -> None:
    """Sınırın DÜRÜST hali: karar yalnız hedefin ≤0.05 ms yakınında değişebilir.

    "Karar asla değişmez" demek yanlış olurdu. Yuvarlama bir değeri en çok
    0.05 ms kaydırdığı için, p90'ı hedefin 0.05 ms üstünde olan bir örneklem
    yuvarlandığında hedefin üstünde OLMAKTAN çıkar. Aşağıdaki kayıt bunu
    gösteriyor: 4 sn hedefinin 0.04 ms üstü — bütçenin %0.000001'i. Bu
    pencerenin dışında (aşağıdaki 1 ms'lik örnek) karar aynen korunur.
    """
    hairline = [1000.0] * 9 + [4000.04, 5000.0]
    assert analyze(make_records(hairline)).p90_ok is False
    assert analyze(_round_timings(make_records(hairline))).p90_ok is True

    outside = [1000.0] * 9 + [4001.0, 5000.0]
    assert analyze(make_records(outside)).p90_ok is False
    assert analyze(_round_timings(make_records(outside))).p90_ok is False
# --------------------------------------------------------------------------
# `tts_to_first_audio` alt kırılımı (2026-08-25). Üst aşamada düzeltilen
# sıfır-kirlenmesi alt kırılıma geri sızmamalı; eski dosyalar kırılmamalı.
# --------------------------------------------------------------------------


def add_substages(records: list[dict], synth: float, gate: float, deliver: float) -> list[dict]:
    for record in records:
        record["tts_synth_ms"] = synth
        record["tts_gate_wait_ms"] = gate
        record["tts_deliver_ms"] = deliver
        record["tts_to_first_audio_ms"] = synth + gate + deliver
    return records


def test_substage_percentiles_are_reported_from_delivered_records_only() -> None:
    spoken = add_substages(make_records([5000.0] * 10), 2000.0, 30.0, 400.0)
    clean = analyze(spoken)
    polluted = analyze(spoken + make_unspoken(8))

    assert clean.tts_substage_p50_ms["tts_synth"] == 2000.0
    assert clean.tts_substage_p50_ms["tts_gate_wait"] == 30.0
    assert clean.tts_substage_p50_ms["tts_deliver"] == 400.0
    assert polluted.tts_substage_p50_ms == clean.tts_substage_p50_ms
    assert polluted.tts_substage_p90_ms == clean.tts_substage_p90_ms
    assert polluted.count == 18, "sessiz kayıtlar sayımda görünmeye devam etmeli"


def test_old_records_without_substage_fields_read_as_zero() -> None:
    """52 tarihsel kayıt bu alanları içermez — 0 okunur, çözümleyici kırılmaz."""
    legacy = make_records([5000.0] * 6)
    for record in legacy:
        assert "tts_synth_ms" not in record

    report = analyze(legacy)

    assert report.tts_substage_p50_ms == {
        "tts_synth": 0.0,
        "tts_gate_wait": 0.0,
        "tts_deliver": 0.0,
    }
    assert report.stage_p50_ms["tts_to_first_audio"] == 1500.0, "üst aşama etkilenmemeli"
    text = format_report(report)
    assert "alt-aşama damgası yok" in text


def test_report_renders_substage_split_when_stamps_exist() -> None:
    report = analyze(add_substages(make_records([5000.0] * 5), 2000.0, 30.0, 400.0))
    text = format_report(report)

    assert "tts_synth: p50 2.00 sn" in text
    assert "tts_gate_wait: p50 0.03 sn" in text
    assert "tts_deliver: p50 0.40 sn" in text
    # Ad yanıltıcı olduğu için sınır raporda açıkça yazılı olmalı.
    assert "translation_ready" in text


def test_substage_field_name_of_parent_stage_is_not_renamed() -> None:
    """`tts_to_first_audio_ms` adı sabit: yeniden adlandırma SESSİZ sıfır üretir.

    `latency.py` alanı adıyla okur ve eksik alanı `0.0` sayar — hata değil.
    Bu yüzden ad değişikliği testte değil, canlı raporda yalan olarak çıkar.
    """
    from dataclasses import fields

    from representative.pipeline import UtteranceRecord

    names = {f.name for f in fields(UtteranceRecord)}
    assert "tts_to_first_audio_ms" in names
    assert {"tts_synth_ms", "tts_gate_wait_ms", "tts_deliver_ms"} <= names
    # Alt-aşamalar ek alan: hepsi varsayılanlı olmalı (record_unspoken yolu).
    defaults = {f.name: f.default for f in fields(UtteranceRecord)}
    for name in ("tts_synth_ms", "tts_gate_wait_ms", "tts_deliver_ms"):
        assert defaults[name] == 0.0, f"{name} zorunlu alan olamaz"
