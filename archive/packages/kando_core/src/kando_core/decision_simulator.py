from __future__ import annotations

from dataclasses import dataclass

from core.decision_model import MutationOption


@dataclass(frozen=True)
class SimulationResult:
    success_probability: float
    estimated_risk: float
    notes: str


def simulate_option(option: MutationOption) -> SimulationResult:
    """
    Basit, ilk sürüm simülasyon katmanı.

    Şimdilik yalnızca MutationOption içindeki mevcut tahmin alanlarını
    okuyup küçük bir özet döndürür; gerçek patch çalıştırma yapmaz.
    """
    # İlk versiyon: doğrudan mevcut tahminleri yansıt.
    return SimulationResult(
        success_probability=option.estimated_success_probability,
        estimated_risk=option.estimated_risk,
        notes=option.rationale,
    )

