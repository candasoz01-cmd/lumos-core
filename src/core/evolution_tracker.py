"""
Evolution feedback layer: DecisionExecutionResult sonuçlarını kaydedip
gelecek kararlar için geri bildirim üretmek.
Minimal ilk versiyon — sadece kayıt; mevcut modüllere dokunmaz.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.decision_runner import DecisionExecutionResult

# Decision execution feedback için ayrı log (evolution_log ile şema farkı; karışıklığı önlemek için ayrı dosya)
DECISION_FEEDBACK_LOG_PATH: Path = Path("logs") / "lumos_decision_feedback.jsonl"


@dataclass(frozen=True)
class EvolutionRecord:
    option_id: str
    success: bool
    risk: float
    timestamp: str
    notes: str


def record_execution(result: DecisionExecutionResult) -> None:
    """
    DecisionExecutionResult'ı EvolutionRecord'a dönüştürüp
    logs/lumos_decision_feedback.jsonl dosyasına append eder.
    Best-effort; yazma hatası ana akışı kesmez.
    """
    record = EvolutionRecord(
        option_id=result.option.option_id,
        success=result.success,
        risk=result.option.estimated_risk,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=result.notes or "",
    )
    try:
        DECISION_FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DECISION_FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    except Exception:
        return
