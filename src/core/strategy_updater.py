"""
Strategy updater layer: evolution log kayıtlarını analiz ederek
decision ranking stratejisini geliştirmek için rapor üretir;
karar sonuçlarına göre weights.json ile stratejiyi küçük adımlarla günceller.

Bu modül mevcut evolution/decision modüllerini değiştirmez;
sadece logs/lumos_evolution.jsonl ve .lumos/weights.json üzerinde çalışır.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


# Varsayılan log path (evolution_log ile aynı dosya)
DEFAULT_EVOLUTION_LOG_PATH: Path = Path("logs") / "lumos_evolution.jsonl"

# Weights dosyası (decision_ranker / adaptive_weights ile aynı path)
DEFAULT_WEIGHTS_PATH: Path = Path(".lumos") / "weights.json"

# Strateji güncelleme state (hangi satırlara kadar işlendi)
DEFAULT_STRATEGY_STATE_PATH: Path = Path(".lumos") / "strategy_updater_state.json"

# Küçük güncelleme adımları (0.01–0.05); değerler 0–1 aralığında kalır
REWARD_DELTA = 0.02
PENALTY_DELTA = 0.02

# Sensitivity → risk skoru (decision ranking için proxy)
_SENSITIVITY_RISK = {"CRITICAL": 3, "HIGH": 2, "LOW": 1}


@dataclass
class StrategyReport:
    """Evolution log analizinden çıkan strateji raporu."""

    total_runs: int
    success_rate: float
    avg_risk: float
    rollback_rate: float
    notes: str


def _risk_from_sensitivity_levels(levels: list[str]) -> float:
    """Bir event'in sensitivity_levels listesinden 0–3 arası risk skoru döner."""
    if not levels:
        return 0.0
    return float(max(_SENSITIVITY_RISK.get(lev.upper(), 0) for lev in levels))


def _is_success_result(result: str) -> bool:
    """result alanı başarılı sayılıyor mu?"""
    return result in ("ok", "applied", "rolled_back")


def _clamp01(x: float) -> float:
    """Değeri [0, 1] aralığına kısıtla."""
    return max(0.0, min(1.0, x))


def _load_weights_dict(weights_path: Path) -> dict:
    """weights.json'dan dict oku; yoksa varsayılan döndür."""
    if not weights_path.resolve().exists():
        return {
            "success_weight": 0.4,
            "risk_weight": 0.3,
            "impact_weight": 0.3,
        }
    try:
        data = json.loads(weights_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    if not isinstance(data, dict):
        return {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    return {
        "success_weight": float(data.get("success_weight", 0.4)),
        "risk_weight": float(data.get("risk_weight", 0.3)),
        "impact_weight": float(data.get("impact_weight", 0.3)),
    }


def _save_weights_dict(weights_path: Path, data: dict) -> None:
    """weights.json'a sadece ağırlık alanlarını yaz."""
    weights_path = weights_path.resolve()
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "success_weight": data["success_weight"],
        "risk_weight": data["risk_weight"],
        "impact_weight": data["impact_weight"],
    }
    weights_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def update_weights_from_outcome(
    success: bool,
    weights_path: Path | str | None = None,
) -> None:
    """
    Tek bir karar sonucuna göre strateji ağırlıklarını küçük adımla güncelle.

    - Başarılı ise: success_weight artır, risk_weight azalt (risk tolerance ödülü).
    - Başarısız ise: risk_weight artır (risk penalty).

    Tüm değerler [0, 1] aralığında kalır.
    """
    path = Path(weights_path) if weights_path is not None else DEFAULT_WEIGHTS_PATH
    path = path.resolve()
    data = _load_weights_dict(path)
    if success:
        data["success_weight"] = _clamp01(data["success_weight"] + REWARD_DELTA)
        data["risk_weight"] = _clamp01(data["risk_weight"] - REWARD_DELTA)
    else:
        data["risk_weight"] = _clamp01(data["risk_weight"] + PENALTY_DELTA)
    data["impact_weight"] = _clamp01(data["impact_weight"])
    _save_weights_dict(path, data)


def _load_strategy_state(state_path: Path) -> dict:
    """Son işlenen satır numarasını oku."""
    if not state_path.resolve().exists():
        return {"last_processed_line": -1}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "last_processed_line" in data:
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"last_processed_line": -1}


def _save_strategy_state(state_path: Path, last_processed_line: int) -> None:
    """State dosyasına son işlenen satırı yaz."""
    state_path = state_path.resolve()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"last_processed_line": last_processed_line}, ensure_ascii=False),
        encoding="utf-8",
    )


def apply_evolution_updates(
    log_path: Path | str | None = None,
    weights_path: Path | str | None = None,
    state_path: Path | str | None = None,
) -> int:
    """
    Evolution log'daki yeni DECISION_OPTION_SELECTED event'lerini işle;
    her biri için başarı/başarısızlığa göre weights'ı güncelle.
    Her event yalnızca bir kez işlenir (last_processed_line ile takip).

    Dönen değer: bu çağrıda güncelleme uygulanan event sayısı.
    """
    log_p = Path(log_path) if log_path is not None else DEFAULT_EVOLUTION_LOG_PATH
    weights_p = Path(weights_path) if weights_path is not None else DEFAULT_WEIGHTS_PATH
    state_p = Path(state_path) if state_path is not None else DEFAULT_STRATEGY_STATE_PATH
    log_p = log_p.resolve()
    weights_p = weights_p.resolve()
    state_p = state_p.resolve()

    state = _load_strategy_state(state_p)
    last_line = state["last_processed_line"]
    data = _load_weights_dict(weights_p)
    updates = 0
    current_line = -1

    if not log_p.exists():
        return 0
    try:
        with log_p.open("r", encoding="utf-8") as f:
            for line in f:
                current_line += 1
                if current_line <= last_line:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("action_type") != "DECISION_OPTION_SELECTED":
                    continue
                success = _is_success_result(obj.get("result", ""))
                if success:
                    data["success_weight"] = _clamp01(data["success_weight"] + REWARD_DELTA)
                    data["risk_weight"] = _clamp01(data["risk_weight"] - REWARD_DELTA)
                else:
                    data["risk_weight"] = _clamp01(data["risk_weight"] + PENALTY_DELTA)
                data["success_weight"] = _clamp01(data["success_weight"])
                data["risk_weight"] = _clamp01(data["risk_weight"])
                data["impact_weight"] = _clamp01(data["impact_weight"])
                updates += 1
    except OSError:
        return 0

    if updates > 0:
        _save_weights_dict(weights_p, data)
    _save_strategy_state(state_p, current_line)
    return updates


def analyze_evolution_log(
    log_path: Path | str | None = None,
) -> StrategyReport:
    """
    logs/lumos_evolution.jsonl dosyasını okuyup success oranları, risk–success
    ilişkisi ve basit bir rapor üretir.

    - total_runs: toplam event sayısı
    - success_rate: başarılı sonuç (ok/applied/rolled_back) oranı [0, 1]
    - avg_risk: ortalama risk skoru (sensitivity_levels'tan türetilir)
    - rollback_rate: result == "rolled_back" oranı [0, 1]
    - notes: kısa özet metni

    Log dosyası yoksa veya boşsa total_runs=0, success_rate=0.0, avg_risk=0.0,
    rollback_rate=0.0 ve uygun notes döner.
    """
    path = Path(log_path) if log_path is not None else DEFAULT_EVOLUTION_LOG_PATH
    path = path.resolve()

    total_runs = 0
    success_count = 0
    rollback_count = 0
    risk_sum = 0.0

    if not path.exists():
        return StrategyReport(
            total_runs=0,
            success_rate=0.0,
            avg_risk=0.0,
            rollback_rate=0.0,
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
                if result == "rolled_back":
                    rollback_count += 1
                levels = obj.get("sensitivity_levels") or []
                risk_sum += _risk_from_sensitivity_levels(
                    levels if isinstance(levels, list) else []
                )
    except OSError:
        return StrategyReport(
            total_runs=0,
            success_rate=0.0,
            avg_risk=0.0,
            rollback_rate=0.0,
            notes="Log dosyası okunamadı.",
        )

    if total_runs == 0:
        return StrategyReport(
            total_runs=0,
            success_rate=0.0,
            avg_risk=0.0,
            rollback_rate=0.0,
            notes="Log dosyası boş.",
        )

    success_rate = success_count / total_runs
    rollback_rate = rollback_count / total_runs
    avg_risk = risk_sum / total_runs
    notes = (
        f"Toplam {total_runs} event; başarı oranı {success_rate:.2%}; "
        f"rollback oranı {rollback_rate:.2%}; ortalama risk {avg_risk:.2f}. "
        "Yüksek risk (CRITICAL/HIGH) ile düşük risk event'lerinin success "
        "oranları ileride ayrı kırılabilir."
    )
    return StrategyReport(
        total_runs=total_runs,
        success_rate=success_rate,
        avg_risk=avg_risk,
        rollback_rate=rollback_rate,
        notes=notes,
    )
