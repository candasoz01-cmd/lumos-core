"""
Strategy updater layer: evolution log kayıtlarını analiz ederek
decision ranking stratejisini geliştirmek için rapor üretir.

Bu modül mevcut evolution/decision modüllerini değiştirmez;
sadece logs/lumos_evolution.jsonl üzerinde analiz yapar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


# Varsayılan log path (evolution_log ile aynı dosya)
DEFAULT_EVOLUTION_LOG_PATH: Path = Path("logs") / "lumos_evolution.jsonl"

# Sensitivity → risk skoru (decision ranking için proxy)
_SENSITIVITY_RISK = {"CRITICAL": 3, "HIGH": 2, "LOW": 1}


@dataclass
class StrategyReport:
    """Evolution log analizinden çıkan strateji raporu."""

    total_runs: int
    success_rate: float
    avg_risk: float
    notes: str


def _risk_from_sensitivity_levels(levels: list[str]) -> float:
    """Bir event'in sensitivity_levels listesinden 0–3 arası risk skoru döner."""
    if not levels:
        return 0.0
    return float(max(_SENSITIVITY_RISK.get(lev.upper(), 0) for lev in levels))


def _is_success_result(result: str) -> bool:
    """result alanı başarılı sayılıyor mu?"""
    return result in ("ok", "applied", "rolled_back")


def analyze_evolution_log(
    log_path: Path | str | None = None,
) -> StrategyReport:
    """
    logs/lumos_evolution.jsonl dosyasını okuyup success oranları, risk–success
    ilişkisi ve basit bir rapor üretir.

    - total_runs: toplam event sayısı
    - success_rate: başarılı sonuç (ok/applied/rolled_back) oranı [0, 1]
    - avg_risk: ortalama risk skoru (sensitivity_levels'tan türetilir)
    - notes: kısa özet metni

    Log dosyası yoksa veya boşsa total_runs=0, success_rate=0.0, avg_risk=0.0
    ve uygun notes döner.
    """
    path = Path(log_path) if log_path is not None else DEFAULT_EVOLUTION_LOG_PATH
    path = path.resolve()

    total_runs = 0
    success_count = 0
    risk_sum = 0.0

    if not path.exists():
        return StrategyReport(
            total_runs=0,
            success_rate=0.0,
            avg_risk=0.0,
            notes="Log dosyası bulunamadı.",
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total_runs += 1
                result = obj.get("result", "")
                if _is_success_result(result):
                    success_count += 1
                levels = obj.get("sensitivity_levels") or []
                risk_sum += _risk_from_sensitivity_levels(
                    levels if isinstance(levels, list) else []
                )
    except OSError:
        return StrategyReport(
            total_runs=0,
            success_rate=0.0,
            avg_risk=0.0,
            notes="Log dosyası okunamadı.",
        )

    if total_runs == 0:
        return StrategyReport(
            total_runs=0,
            success_rate=0.0,
            avg_risk=0.0,
            notes="Log dosyası boş.",
        )

    success_rate = success_count / total_runs
    avg_risk = risk_sum / total_runs
    notes = (
        f"Toplam {total_runs} event; başarı oranı {success_rate:.2%}; "
        f"ortalama risk {avg_risk:.2f}. Yüksek risk (CRITICAL/HIGH) ile "
        "düşük risk event'lerinin success oranları ileride ayrı kırılabilir."
    )
    return StrategyReport(
        total_runs=total_runs,
        success_rate=success_rate,
        avg_risk=avg_risk,
        notes=notes,
    )
