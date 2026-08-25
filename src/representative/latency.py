"""Aşama gecikmesi muhasebesi + prova kaydı çözümleyici.

Ürün zinciri (canlı insan testi 4, 2026-08-17):
    speech-end → STT-final → translation-ready → TTS-start → first-audio-in-Meet

Hedefler (doğal sohbet): **p50 ≤ 2.5 sn, p90 ≤ 4 sn** — speech-end → first-audio.
`evaluate_first_audio_budget` boş örneklemden veya bütçe aşımından ASLA PASS
uydurmaz; ölçüm yoksa cevap "PASS değil"dir.

Bu dosya iki işi birleştirir:
- **Bütçe çekirdeği** (Lumos PR #343 handoff yaması): aşama adları, yüzdelik,
  en büyük bekleme aşaması, bütçe kararı.
- **Çözümleyici** (lumos-core #751): kaydı okuyup insanın bakacağı raporu ve
  kapı olarak kullanılabilir çıkış kodunu üretir.

Kullanım:
    python -m representative.latency prova_bot.jsonl
    python -m representative.latency prova_bot.jsonl --p90-target-ms 5000

Çıkış kodu: bütçe tutuyorsa 0, tutmuyorsa 1 — kırmızı ölçüm sessizce "geçti"
diye raporlanamasın.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

FIRST_AUDIO_P50_TARGET_MS = 2500.0
FIRST_AUDIO_P90_TARGET_MS = 4000.0

# Geriye dönük adlar (çözümleyici CLI varsayılanları).
P50_TARGET_MS = FIRST_AUDIO_P50_TARGET_MS
P90_TARGET_MS = FIRST_AUDIO_P90_TARGET_MS

STAGE_STT = "stt"
STAGE_TRANSLATE = "translate"
STAGE_TTS_FIRST_AUDIO = "tts_to_first_audio"
STAGE_E2E = "e2e_first_audio"

# `tts_to_first_audio`ın alt kırılımı (2026-08-25). Adı yanıltıcı olan üst
# aşamanın GERÇEK sınırı `translation_ready -> teslim POST'u döndü`; bu üçü o
# aralığı böler ve toplamları ona eşittir:
#   synth  — OpenAI TTS gidiş-dönüşü
#   gate   — yarı-çift-yönlü kapının alınması
#   deliver— base64 + Recall output_audio POST'u
# Alan adı -> rapor adı. Eski jsonl'lerde bu alanlar YOKTUR; `r.get(f, 0.0)`
# sayesinde 0 okunur ve çözümleyici kırılmaz (üst aşamalarla aynı davranış).
TTS_SUBSTAGES: tuple[tuple[str, str], ...] = (
    ("tts_synth", "tts_synth_ms"),
    ("tts_gate_wait", "tts_gate_wait_ms"),
    ("tts_deliver", "tts_deliver_ms"),
)


def percentile_ms(values: Iterable[float], p: float) -> float:
    """Doğrusal interpolasyonlu yüzdelik. Boş → 0. p 0..100 aralığında."""
    if not 0.0 <= p <= 100.0:
        raise ValueError("percentile p must be within [0, 100]")
    data = sorted(float(v) for v in values)
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    rank = (len(data) - 1) * (p / 100.0)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return data[int(rank)]
    weight = rank - lo
    return data[lo] * (1.0 - weight) + data[hi] * weight


def largest_wait_stage(stt_p50: float, translate_p50: float, tts_p50: float) -> str:
    """p50'si en yüksek aşamayı adlandırır — optimizasyon hedefi."""
    scores = (
        (stt_p50, STAGE_STT),
        (translate_p50, STAGE_TRANSLATE),
        (tts_p50, STAGE_TTS_FIRST_AUDIO),
    )
    return max(scores, key=lambda item: item[0])[1]


def evaluate_first_audio_budget(p50_ms: float, p90_ms: float, *, count: int) -> dict[str, object]:
    """Yalnız boş olmayan örneklemde ve iki hedef de tutuyorsa PASS. Tahmin yok."""
    met = (
        count > 0
        and p50_ms <= FIRST_AUDIO_P50_TARGET_MS
        and p90_ms <= FIRST_AUDIO_P90_TARGET_MS
    )
    return {
        "pass": met,
        "count": count,
        "p50_ms": p50_ms,
        "p90_ms": p90_ms,
        "p50_target_ms": FIRST_AUDIO_P50_TARGET_MS,
        "p90_target_ms": FIRST_AUDIO_P90_TARGET_MS,
        "reason": "ok" if met else "over_budget_or_empty",
    }


# --------------------------------------------------------------------------
# Kayıt çözümleyici
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LatencyReport:
    count: int
    delivered: int
    p50_ms: float
    p90_ms: float
    max_ms: float
    p50_target_ms: float
    p90_target_ms: float
    by_direction: dict[str, dict[str, float]]
    by_flag_reason: dict[str, int]
    stage_p50_ms: dict[str, float]
    largest_wait: str
    slowest: list[tuple[float, str]]
    # Alt-aşama kırılımı. Varsayılan boş: alanı geçmeyen çağıranlar (ve
    # tarihsel testler) kırılmaz, yalnız kırılım görünmez.
    tts_substage_p50_ms: dict[str, float] = field(default_factory=dict)
    tts_substage_p90_ms: dict[str, float] = field(default_factory=dict)

    @property
    def p50_ok(self) -> bool:
        return self.p50_ms <= self.p50_target_ms

    @property
    def p90_ok(self) -> bool:
        return self.p90_ms <= self.p90_target_ms

    @property
    def passed(self) -> bool:
        # `count` değil `delivered`: gecikmeler yalnız teslim edilen kayıtlardan
        # hesaplanıyor. Yalnızca seslendirilmeyen satırlardan oluşan bir dosyada
        # örneklem boş kalır, p50/p90 0.0 döner ve `count > 0` sahte PASS
        # üretirdi. Eski dosyalarda `delivered` anahtarı yok → hepsi teslim
        # sayılır → davranış aynı.
        return self.delivered > 0 and self.p50_ok and self.p90_ok


def _e2e_ms(record: dict) -> float:
    """first-audio ölçümü varsa o; yoksa eski kayıtların toplam gecikmesi."""
    return float(record.get("e2e_first_audio_ms") or record.get("latency_ms", 0.0))


def delivered_records(records: list[dict]) -> list[dict]:
    """Yalnız seslendirilmiş kayıtlar — teslim başarımı metriklerinin örneklemi.

    `delivered=false` satırları (yarım söz tutma, tekrar bastırma, yön
    belirlenemeyen söz) çeviri/TTS hattına hiç girmediği için gecikmeleri
    0 ms'dir. Havuza karıştıklarında p50/p90'ı AŞAĞI çeker, yani suite
    gerçekte olduğundan iyi görünür ve kimse iyileşmeyi soruşturmaz. Üstelik
    fail-closed davranışı çalıştıkça sayıları artar: özellik iyi çalıştıkça
    ölçüm daha çok yalan söyler.

    Anahtar YOKSA teslim edilmiş sayılır — `delivered` alanından önceki prova
    dosyaları aynı şekilde okunmaya devam eder.
    """
    return [r for r in records if r.get("delivered", True)]


def load_records(path: str) -> list[dict]:
    """Bozuk satır çözümlemeyi durdurmaz; prova kaydı çökmede yarım kalabilir."""
    records: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def analyze(
    records: list[dict],
    p50_target_ms: float = FIRST_AUDIO_P50_TARGET_MS,
    p90_target_ms: float = FIRST_AUDIO_P90_TARGET_MS,
) -> LatencyReport:
    # Kurucu kararı (2026-08-24, seçenek A): işletimsel görünürlük ile teslim
    # başarımı AYRI. Seslendirilmeyen kayıtlar `count` ve `by_flag_reason`da
    # tam görünür kalır (kaynak dosya tek doğruluk kaynağıdır, hiçbir olay
    # gizlenmez) ama gecikme hesaplarının HİÇBİRİNE girmez.
    measured = delivered_records(records)
    latencies = [_e2e_ms(r) for r in measured]
    by_direction: dict[str, dict[str, float]] = {}
    for record in measured:
        key = f"{record.get('source_lang', '?')}->{record.get('target_lang', '?')}"
        by_direction.setdefault(key, {"count": 0, "p50_ms": 0.0, "p90_ms": 0.0})
        by_direction[key]["count"] += 1
    for key in by_direction:
        values = [
            _e2e_ms(r)
            for r in measured
            if f"{r.get('source_lang', '?')}->{r.get('target_lang', '?')}" == key
        ]
        by_direction[key]["p50_ms"] = percentile_ms(values, 50)
        by_direction[key]["p90_ms"] = percentile_ms(values, 90)

    # Aşama kırılımı yalnız yeni kayıtlarda var; eski dosyalarda 0 görünür.
    stage_p50 = {
        stage: percentile_ms([float(r.get(field, 0.0)) for r in measured], 50)
        for stage, field in (
            (STAGE_STT, "stt_ms"),
            (STAGE_TRANSLATE, "translate_ms"),
            (STAGE_TTS_FIRST_AUDIO, "tts_to_first_audio_ms"),
        )
    }
    # Alt-aşamalar da `measured` üzerinden — `records` kullanmak, aşama
    # alanlarında düzeltilen sıfır-kirlenmesini alt kırılıma geri sokardı.
    tts_substage_p50 = {
        name: percentile_ms([float(r.get(f, 0.0)) for r in measured], 50)
        for name, f in TTS_SUBSTAGES
    }
    tts_substage_p90 = {
        name: percentile_ms([float(r.get(f, 0.0)) for r in measured], 90)
        for name, f in TTS_SUBSTAGES
    }
    slowest = sorted(
        ((_e2e_ms(r), str(r.get("source_text", ""))[:60]) for r in measured),
        reverse=True,
    )[:5]
    return LatencyReport(
        count=len(records),
        delivered=sum(1 for r in records if r.get("delivered", True)),
        p50_ms=percentile_ms(latencies, 50),
        p90_ms=percentile_ms(latencies, 90),
        max_ms=max(latencies) if latencies else 0.0,
        p50_target_ms=p50_target_ms,
        p90_target_ms=p90_target_ms,
        by_direction=by_direction,
        by_flag_reason=dict(Counter(str(r.get("flag_reason", "?")) for r in records)),
        stage_p50_ms=stage_p50,
        largest_wait=largest_wait_stage(
            stage_p50[STAGE_STT],
            stage_p50[STAGE_TRANSLATE],
            stage_p50[STAGE_TTS_FIRST_AUDIO],
        ),
        slowest=slowest,
        tts_substage_p50_ms=tts_substage_p50,
        tts_substage_p90_ms=tts_substage_p90,
    )


def format_report(report: LatencyReport) -> str:
    if report.count == 0:
        return "Kayıt yok — ölçüm dosyası boş. (PASS uydurulmaz: SONUÇ KALDI)"

    def verdict(ok: bool) -> str:
        return "GEÇTİ" if ok else "KALDI"

    lines = [
        f"Kayıt: {report.count} söz ({report.delivered} teslim edildi)",
        "Ölçülen: söz sonu → Meet'te ilk ses (first-audio)",
        f"Gecikme örneklemi: {report.delivered} teslim edilen kayıt "
        f"({report.count - report.delivered} seslendirilmeyen kayıt hesaba katılmadı)",
        "",
        f"p50 {report.p50_ms / 1000:.2f} sn  (hedef ≤ {report.p50_target_ms / 1000:.2f}) "
        f"→ {verdict(report.p50_ok)}",
        f"p90 {report.p90_ms / 1000:.2f} sn  (hedef ≤ {report.p90_target_ms / 1000:.2f}) "
        f"→ {verdict(report.p90_ok)}",
        f"max {report.max_ms / 1000:.2f} sn",
        "",
        "Yön kırılımı:",
    ]
    for key, stats in sorted(report.by_direction.items()):
        lines.append(
            f"  {key}: n={int(stats['count'])}  p50 {stats['p50_ms'] / 1000:.2f} sn  "
            f"p90 {stats['p90_ms'] / 1000:.2f} sn"
        )
    lines.append("")
    lines.append("Aşama p50 (yalnız aşama damgası olan kayıtlarda anlamlı):")
    for stage, value in report.stage_p50_ms.items():
        lines.append(f"  {stage}: {value / 1000:.2f} sn")
    lines.append(f"  → en büyük bekleme: {report.largest_wait}")
    lines.append("")
    lines.append(
        "tts_to_first_audio kırılımı "
        "(sınır: translation_ready → teslim POST'u döndü; "
        "Meet'te DUYULMA anı ölçülmüyor):"
    )
    if any(report.tts_substage_p50_ms.values()):
        for name, _f in TTS_SUBSTAGES:
            p50v = report.tts_substage_p50_ms.get(name, 0.0)
            p90v = report.tts_substage_p90_ms.get(name, 0.0)
            share = (
                f"  (üst aşamanın %{100.0 * p50v / report.stage_p50_ms[STAGE_TTS_FIRST_AUDIO]:.0f}'i)"
                if report.stage_p50_ms.get(STAGE_TTS_FIRST_AUDIO)
                else ""
            )
            lines.append(f"  {name}: p50 {p50v / 1000:.2f} sn  p90 {p90v / 1000:.2f} sn{share}")
    else:
        lines.append("  (bu kayıtta alt-aşama damgası yok — ölçüm öncesi dosya)")
    lines.append("")
    lines.append(
        "İşaret dağılımı: " + ", ".join(f"{k}={v}" for k, v in sorted(report.by_flag_reason.items()))
    )
    lines.append("")
    lines.append("En yavaş 5 söz:")
    for value, text in report.slowest:
        lines.append(f"  {value / 1000:5.2f} sn  {text}")
    lines.append("")
    lines.append(f"SONUÇ: {'GEÇTİ' if report.passed else 'KALDI'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prova gecikme kaydı çözümleyici")
    parser.add_argument("path", help="prova jsonl kaydı")
    parser.add_argument("--p50-target-ms", type=float, default=FIRST_AUDIO_P50_TARGET_MS)
    parser.add_argument("--p90-target-ms", type=float, default=FIRST_AUDIO_P90_TARGET_MS)
    args = parser.parse_args(argv)

    report = analyze(load_records(args.path), args.p50_target_ms, args.p90_target_ms)
    print(format_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
