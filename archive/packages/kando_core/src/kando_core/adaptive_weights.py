"""
Adaptive decision weights: strategy_updater analizlerine göre
ranking ağırlıklarını saklamak.

Bu modül sadece ağırlıkları okumak için kullanılır;
hiçbir mevcut modülü değiştirmez.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


# Varsayılan weights dosyası (.lumos altında)
DEFAULT_WEIGHTS_PATH: Path = Path(".lumos") / "weights.json"


@dataclass
class DecisionWeights:
    """Ranking için karar ağırlıkları."""

    success_weight: float = 0.4
    risk_weight: float = 0.3
    impact_weight: float = 0.3


def load_weights(weights_path: Path | str | None = None) -> DecisionWeights:
    """
    weights.json varsa okuyup DecisionWeights döndürür;
    yoksa varsayılan DecisionWeights döndürür.

    Path verilmezse DEFAULT_WEIGHTS_PATH (.lumos/weights.json) kullanılır.
    """
    path = Path(weights_path) if weights_path is not None else DEFAULT_WEIGHTS_PATH
    path = path.resolve()

    if not path.exists():
        return DecisionWeights()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DecisionWeights()

    if not isinstance(data, dict):
        return DecisionWeights()

    return DecisionWeights(
        success_weight=float(data.get("success_weight", 0.4)),
        risk_weight=float(data.get("risk_weight", 0.3)),
        impact_weight=float(data.get("impact_weight", 0.3)),
    )
