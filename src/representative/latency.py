"""Prova kaydı (jsonl) gecikme çözümleyicisi — canlı insan testi 4 sonrası.

Canlı testte tek bir toplam süre vardı: p90 7.49 sn FAIL göründü ama sivrilme
HANGİ aşamadan geliyor okunamadı. Bu modül kaydı okur, hedeflere göre açık bir
PASS/FAIL verir ve kuyruk ucunu ayrıştırır.

Hedefler (runbook, kurucu): **p50 ≤ 2.5 sn, p90 ≤ 4 sn.**

Kullanım:
    python -m representative.latency prova_bot.jsonl
    python -m representative.latency prova_bot.jsonl --p90-target-ms 5000

Çıkış kodu: hedefler tutuyorsa 0, tutmuyorsa 1 — kapı olarak kullanılabilir
(kırmızı ölçüm sessizce "geçti" diye raporlanamasın).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass

from representative.pipeline import percentile_ms

P50_TARGET_MS = 2500.0
P90_TARGET_MS = 4000.0


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
    stage_p90_ms: dict[str, float]
    slowest: list[tuple[float, str]]

    @property
    def p50_ok(self) -> bool:
        return self.p50_ms <= self.p50_target_ms

    @property
    def p90_ok(self) -> bool:
        return self.p90_ms <= self.p90_target_ms

    @property
    def passed(self) -> bool:
        return self.count > 0 and self.p50_ok and self.p90_ok


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
    p50_target_ms: float = P50_TARGET_MS,
    p90_target_ms: float = P90_TARGET_MS,
) -> LatencyReport:
    latencies = [float(r.get("latency_ms", 0.0)) for r in records]
    by_direction: dict[str, dict[str, float]] = {}
    for record in records:
        key = f"{record.get('source_lang', '?')}->{record.get('target_lang', '?')}"
        by_direction.setdefault(key, {"count": 0, "p50_ms": 0.0, "p90_ms": 0.0})
        by_direction[key]["count"] += 1
    for key in by_direction:
        values = [
            float(r.get("latency_ms", 0.0))
            for r in records
            if f"{r.get('source_lang', '?')}->{r.get('target_lang', '?')}" == key
        ]
        by_direction[key]["p50_ms"] = percentile_ms(values, 50)
        by_direction[key]["p90_ms"] = percentile_ms(values, 90)

    # Aşama kırılımı yalnız yeni kayıtlarda var; eski dosyalarda 0 görünür.
    stage_p90 = {
        stage: percentile_ms([float(r.get(stage, 0.0)) for r in records], 90)
        for stage in ("translate_ms", "tts_ms", "postcheck_ms")
    }
    slowest = sorted(
        ((float(r.get("latency_ms", 0.0)), str(r.get("source_text", ""))[:60]) for r in records),
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
        stage_p90_ms=stage_p90,
        slowest=slowest,
    )


def format_report(report: LatencyReport) -> str:
    if report.count == 0:
        return "Kayıt yok — ölçüm dosyası boş."

    def verdict(ok: bool) -> str:
        return "GEÇTİ" if ok else "KALDI"

    lines = [
        f"Kayıt: {report.count} söz ({report.delivered} teslim edildi)",
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
    lines.append("Aşama p90 (yalnız aşama kırılımı olan kayıtlarda anlamlı):")
    for stage, value in report.stage_p90_ms.items():
        lines.append(f"  {stage}: {value / 1000:.2f} sn")
    lines.append("")
    lines.append("İşaret dağılımı: " + ", ".join(f"{k}={v}" for k, v in sorted(
        report.by_flag_reason.items())))
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
    parser.add_argument("--p50-target-ms", type=float, default=P50_TARGET_MS)
    parser.add_argument("--p90-target-ms", type=float, default=P90_TARGET_MS)
    args = parser.parse_args(argv)

    report = analyze(load_records(args.path), args.p50_target_ms, args.p90_target_ms)
    print(format_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
