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
from datetime import datetime, timezone

from core.log_window import read_recent_jsonl_records


# Varsayılan log path (evolution_log ile aynı dosya)
DEFAULT_EVOLUTION_LOG_PATH: Path = Path("logs") / "lumos_evolution.jsonl"

# Decision execution feedback log (evolution_tracker yazar; ayrı şema)
DEFAULT_DECISION_FEEDBACK_LOG_PATH: Path = Path("logs") / "lumos_decision_feedback.jsonl"

# Weights dosyası (decision_ranker / adaptive_weights ile aynı path)
DEFAULT_WEIGHTS_PATH: Path = Path(".lumos") / "weights.json"

# Strateji güncelleme state (evolution log için; hangi satırlara kadar işlendi)
DEFAULT_STRATEGY_STATE_PATH: Path = Path(".lumos") / "strategy_updater_state.json"

# Decision feedback log için ayrı state (çift işlemeyi önlemek için)
DEFAULT_FEEDBACK_STATE_PATH: Path = Path(".lumos") / "strategy_feedback_state.json"

# Decision history (readable audit log; used for self-improvement cycle)
DEFAULT_DECISION_HISTORY_LOG_PATH: Path = Path("logs") / "lumos_decision_history.jsonl"

# Compressed memory patterns (from memory_compressor); used to softly bias weights
DEFAULT_MEMORY_PATTERNS_PATH: Path = Path(".lumos") / "memory_patterns.json"

# Memory bias: min confidence and evidence to apply a pattern; max total delta per weight
MEMORY_BIAS_MIN_CONFIDENCE = 0.65
MEMORY_BIAS_MIN_EVIDENCE = 5
MEMORY_BIAS_MAX_TOTAL_DELTA = 0.05

# Küçük güncelleme adımları (0.01–0.05); değerler 0–1 aralığında kalır
REWARD_DELTA = 0.02
PENALTY_DELTA = 0.02

# Self-improvement: max delta per cycle, small step, min records to act
SELF_IMPROVE_MAX_DELTA = 0.03
SELF_IMPROVE_STEP = 0.01
SELF_IMPROVE_MIN_RECORDS = 10

# Safety governor: prevent self-reinforcing bad updates
DEFAULT_WEIGHTS_HISTORY_PATH: Path = Path(".lumos") / "weights_history.json"
WEIGHTS_HISTORY_MAX_ENTRIES = 50
MAX_TOTAL_DRIFT = 0.35  # max sum of |proposed - baseline| over the three weights
SUCCESS_RATE_FREEZE_THRESHOLD = 0.4  # freeze updates if recent success rate below this
SUCCESS_RATE_ROLLBACK_THRESHOLD = 0.35  # rollback to previous weights if below this
RECENT_FEEDBACK_WINDOW = 20  # last N feedback records for success rate
# Bounded recent-history: max records read for decision/feedback and evolution analysis
STRATEGY_RECENT_RECORDS_LIMIT = 200

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


def _load_weights_history(weights_history_path: Path) -> list[dict]:
    """Load weights history; return list of {timestamp, weights}."""
    path = weights_history_path.resolve()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    entries = data.get("entries")
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict) and "weights" in e and "timestamp" in e]


def _append_weights_to_history(
    weights_history_path: Path,
    weights: dict,
    *,
    max_entries: int = WEIGHTS_HISTORY_MAX_ENTRIES,
) -> None:
    """Append a weights snapshot to history; trim to max_entries."""
    path = weights_history_path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "weights": {
            "success_weight": float(weights.get("success_weight", 0.4)),
            "risk_weight": float(weights.get("risk_weight", 0.3)),
            "impact_weight": float(weights.get("impact_weight", 0.3)),
        },
    }
    history = _load_weights_history(path)
    history.append(entry)
    if len(history) > max_entries:
        history = history[-max_entries:]
    path.write_text(
        json.dumps({"entries": history}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _recent_success_rate(feedback_log_path: Path, window: int = RECENT_FEEDBACK_WINDOW) -> float:
    """Last N feedback records: success rate in [0, 1]. If no records, return 1.0 (allow)."""
    path = feedback_log_path.resolve()
    if not path.exists() or window <= 0:
        return 1.0
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
    except OSError:
        return 1.0
    recent = lines[-window:] if len(lines) >= window else lines
    if not recent:
        return 1.0
    success_count = 0
    for line in recent:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("success") is True:
                success_count += 1
        except json.JSONDecodeError:
            continue
    return success_count / len(recent)


def evaluate_weight_update_safety(
    current_weights: dict,
    proposed_weights: dict,
    *,
    feedback_log_path: Path | str | None = None,
    weights_history_path: Path | str | None = None,
) -> dict:
    """
    Evaluate whether applying proposed_weights is safe. Prevents drift, freeze, and enables rollback.

    Returns dict with:
      - safe: bool
      - reason: str | None (e.g. "freeze_success_rate_below_threshold", "drift_cap_exceeded", "rollback_worse_outcomes")
      - report: dict with drift, recent_success_rate, previous_weights (if rollback), baseline_weights
    If safe is False, do not apply proposed_weights; if reason is rollback_worse_outcomes, apply previous_weights instead.
    """
    feed_p = Path(feedback_log_path) if feedback_log_path is not None else DEFAULT_DECISION_FEEDBACK_LOG_PATH
    hist_p = Path(weights_history_path) if weights_history_path is not None else DEFAULT_WEIGHTS_HISTORY_PATH
    feed_p = feed_p.resolve()
    hist_p = hist_p.resolve()

    report: dict = {
        "drift": 0.0,
        "drift_cap": MAX_TOTAL_DRIFT,
        "recent_success_rate": 1.0,
        "freeze_threshold": SUCCESS_RATE_FREEZE_THRESHOLD,
        "rollback_threshold": SUCCESS_RATE_ROLLBACK_THRESHOLD,
        "baseline_weights": {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3},
        "previous_weights": None,
    }

    # Baseline from first history entry or default
    history = _load_weights_history(hist_p)
    if history:
        report["baseline_weights"] = dict(history[0]["weights"])
        report["previous_weights"] = dict(history[-1]["weights"])
    keys = ("success_weight", "risk_weight", "impact_weight")
    baseline = report["baseline_weights"]
    total_drift = sum(
        abs(float(proposed_weights.get(k, 0)) - float(baseline.get(k, 0)))
        for k in keys
    )
    report["drift"] = round(total_drift, 6)

    recent_rate = _recent_success_rate(feed_p, RECENT_FEEDBACK_WINDOW)
    report["recent_success_rate"] = round(recent_rate, 4)

    # 1) Drift cap
    if total_drift > MAX_TOTAL_DRIFT:
        return {
            "safe": False,
            "reason": "drift_cap_exceeded",
            "report": report,
        }

    # 2) Freeze: success rate below threshold
    if recent_rate < SUCCESS_RATE_FREEZE_THRESHOLD:
        return {
            "safe": False,
            "reason": "freeze_success_rate_below_threshold",
            "report": report,
        }

    # 3) Rollback: success rate very low and we have previous snapshot
    if recent_rate < SUCCESS_RATE_ROLLBACK_THRESHOLD and report["previous_weights"] is not None:
        return {
            "safe": False,
            "reason": "rollback_worse_outcomes",
            "report": report,
        }

    return {"safe": True, "reason": None, "report": report}


def update_weights_from_outcome(
    success: bool,
    weights_path: Path | str | None = None,
    feedback_log_path: Path | str | None = None,
    weights_history_path: Path | str | None = None,
) -> None:
    """
    Tek bir karar sonucuna göre strateji ağırlıklarını küçük adımla güncelle.

    - Başarılı ise: success_weight artır, risk_weight azalt (risk tolerance ödülü).
    - Başarısız ise: risk_weight artır (risk penalty).
    - Safety governor: drift cap, freeze, rollback apply; may skip or rollback.

    Tüm değerler [0, 1] aralığında kalır.
    """
    path = Path(weights_path) if weights_path is not None else DEFAULT_WEIGHTS_PATH
    path = path.resolve()
    data = _load_weights_dict(path)
    current = dict(data)
    if success:
        data["success_weight"] = _clamp01(data["success_weight"] + REWARD_DELTA)
        data["risk_weight"] = _clamp01(data["risk_weight"] - REWARD_DELTA)
    else:
        data["risk_weight"] = _clamp01(data["risk_weight"] + PENALTY_DELTA)
    data["impact_weight"] = _clamp01(data["impact_weight"])
    proposed = dict(data)
    hist_path = Path(weights_history_path) if weights_history_path is not None else path.parent / "weights_history.json"
    safety = evaluate_weight_update_safety(
        current,
        proposed,
        feedback_log_path=feedback_log_path or DEFAULT_DECISION_FEEDBACK_LOG_PATH,
        weights_history_path=hist_path,
    )
    if safety["safe"]:
        _append_weights_to_history(hist_path, current)
        _save_weights_dict(path, proposed)
        return
    if safety["reason"] == "rollback_worse_outcomes" and safety["report"].get("previous_weights"):
        _save_weights_dict(path, safety["report"]["previous_weights"])
        return
    # freeze or drift_cap: do not apply


def _load_strategy_state(state_path: Path) -> dict:
    """Load state dict (last_processed_line and/or last_processed_timestamp)."""
    if not state_path.resolve().exists():
        return {"last_processed_line": -1}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"last_processed_line": -1}


def _save_strategy_state(state_path: Path, state: dict) -> None:
    """State dosyasına state dict yaz (last_processed_line ve/veya last_processed_timestamp)."""
    state_path = state_path.resolve()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, ensure_ascii=False),
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
    Yalnızca son STRATEGY_RECENT_RECORDS_LIMIT kayıt okunur; her event
    last_processed_timestamp ile yalnızca bir kez işlenir.

    Dönen değer: bu çağrıda güncelleme uygulanan event sayısı.
    """
    log_p = Path(log_path) if log_path is not None else DEFAULT_EVOLUTION_LOG_PATH
    weights_p = Path(weights_path) if weights_path is not None else DEFAULT_WEIGHTS_PATH
    state_p = Path(state_path) if state_path is not None else DEFAULT_STRATEGY_STATE_PATH
    log_p = log_p.resolve()
    weights_p = weights_p.resolve()
    state_p = state_p.resolve()

    state = _load_strategy_state(state_p)
    last_ts = state.get("last_processed_timestamp") or ""
    data = _load_weights_dict(weights_p)
    updates = 0
    processed_ts: list[str] = []

    records = read_recent_jsonl_records(log_p, STRATEGY_RECENT_RECORDS_LIMIT)
    for obj in records:
        if obj.get("action_type") != "DECISION_OPTION_SELECTED":
            continue
        ts = obj.get("timestamp") or ""
        if ts <= last_ts:
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
        processed_ts.append(ts)

    if updates > 0:
        _save_weights_dict(weights_p, data)
    if processed_ts:
        state["last_processed_timestamp"] = max(processed_ts)
    _save_strategy_state(state_p, state)
    return updates


def apply_decision_feedback_updates(
    feedback_log_path: Path | str | None = None,
    weights_path: Path | str | None = None,
    state_path: Path | str | None = None,
    weights_history_path: Path | str | None = None,
) -> int:
    """
    logs/lumos_decision_feedback.jsonl dosyasındaki yeni kayıtları işle;
    her biri için success alanına göre weights'ı küçük adımla güncelle.
    Yalnızca son STRATEGY_RECENT_RECORDS_LIMIT kayıt okunur; her kayıt
    last_processed_timestamp ile yalnızca bir kez işlenir.
    Safety governor: if safety check fails, weights are not updated (or rollback applied).

    Dönen değer: bu çağrıda güncelleme uygulanan kayıt sayısı.
    """
    log_p = (
        Path(feedback_log_path)
        if feedback_log_path is not None
        else DEFAULT_DECISION_FEEDBACK_LOG_PATH
    )
    weights_p = Path(weights_path) if weights_path is not None else DEFAULT_WEIGHTS_PATH
    state_p = (
        Path(state_path) if state_path is not None else DEFAULT_FEEDBACK_STATE_PATH
    )
    hist_p = Path(weights_history_path) if weights_history_path is not None else weights_p.parent / "weights_history.json"
    log_p = log_p.resolve()
    weights_p = weights_p.resolve()
    state_p = state_p.resolve()
    hist_p = hist_p.resolve()

    state = _load_strategy_state(state_p)
    last_ts = state.get("last_processed_timestamp") or ""
    data = _load_weights_dict(weights_p)
    current_weights = dict(data)
    updates = 0
    processed_ts: list[str] = []

    records = read_recent_jsonl_records(log_p, STRATEGY_RECENT_RECORDS_LIMIT)
    for obj in records:
        ts = obj.get("timestamp") or ""
        if ts <= last_ts:
            continue
        success = bool(obj.get("success", False))
        if success:
            data["success_weight"] = _clamp01(
                data["success_weight"] + REWARD_DELTA
            )
            data["risk_weight"] = _clamp01(
                data["risk_weight"] - REWARD_DELTA
            )
        else:
            data["risk_weight"] = _clamp01(
                data["risk_weight"] + PENALTY_DELTA
            )
        data["success_weight"] = _clamp01(data["success_weight"])
        data["risk_weight"] = _clamp01(data["risk_weight"])
        data["impact_weight"] = _clamp01(data["impact_weight"])
        updates += 1
        processed_ts.append(ts)

    if updates > 0:
        proposed = dict(data)
        safety = evaluate_weight_update_safety(
            current_weights,
            proposed,
            feedback_log_path=log_p,
            weights_history_path=hist_p,
        )
        if safety["safe"]:
            _append_weights_to_history(hist_p, current_weights)
            _save_weights_dict(weights_p, proposed)
        elif safety["reason"] == "rollback_worse_outcomes" and safety["report"].get("previous_weights"):
            _save_weights_dict(weights_p, safety["report"]["previous_weights"])
        # else: freeze or drift_cap — do not apply
    if processed_ts:
        state["last_processed_timestamp"] = max(processed_ts)
    _save_strategy_state(state_p, state)
    return updates


def analyze_evolution_log(
    log_path: Path | str | None = None,
) -> StrategyReport:
    """
    logs/lumos_evolution.jsonl dosyasının son STRATEGY_RECENT_RECORDS_LIMIT
    kaydını okuyup success oranları, risk–success ilişkisi ve basit bir rapor üretir.

    - total_runs: toplam event sayısı (en fazla STRATEGY_RECENT_RECORDS_LIMIT)
    - success_rate: başarılı sonuç (ok/applied/rolled_back) oranı [0, 1]
    - avg_risk: ortalama risk skoru (sensitivity_levels'tan türetilir)
    - rollback_rate: result == "rolled_back" oranı [0, 1]
    - notes: kısa özet metni

    Log dosyası yoksa veya boşsa total_runs=0, success_rate=0.0, avg_risk=0.0,
    rollback_rate=0.0 ve uygun notes döner.
    """
    path = Path(log_path) if log_path is not None else DEFAULT_EVOLUTION_LOG_PATH
    path = path.resolve()

    records = read_recent_jsonl_records(path, STRATEGY_RECENT_RECORDS_LIMIT)
    total_runs = 0
    success_count = 0
    rollback_count = 0
    risk_sum = 0.0

    for obj in records:
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


def apply_memory_bias(
    weights: dict,
    memory_patterns_path: Path | str | None = None,
) -> dict:
    """
    Apply soft bias from .lumos/memory_patterns.json to weights.
    Only uses patterns with confidence >= 0.65 and evidence_count >= 5.
    Total adjustment per weight key is capped at 0.05; result clamped to [0, 1].
    If file missing or malformed, returns report with status 'skipped' and no change.

    Returns report: { patterns_used, bias_applied, status, [weights_after] }.
    """
    path = (
        Path(memory_patterns_path)
        if memory_patterns_path is not None
        else DEFAULT_MEMORY_PATTERNS_PATH
    )
    path = path.resolve()
    report: dict = {
        "patterns_used": 0,
        "bias_applied": {},
        "status": "skipped",
    }

    if not path.exists():
        return report

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return report

    if not isinstance(data, dict):
        return report

    patterns = data.get("patterns")
    if not isinstance(patterns, list):
        return report

    # Accumulate deltas from eligible patterns; cap total per key at MEMORY_BIAS_MAX_TOTAL_DELTA
    deltas: dict[str, float] = {}
    patterns_used = 0
    for item in patterns:
        if not isinstance(item, dict):
            continue
        conf = item.get("confidence")
        evidence = item.get("evidence_count")
        bias = item.get("recommended_bias")
        if not isinstance(bias, dict):
            continue
        try:
            c = float(conf)
            e = int(evidence)
        except (TypeError, ValueError):
            continue
        if c < MEMORY_BIAS_MIN_CONFIDENCE or e < MEMORY_BIAS_MIN_EVIDENCE:
            continue
        patterns_used += 1
        for key, val in bias.items():
            if not isinstance(key, str) or key not in ("success_weight", "risk_weight", "impact_weight"):
                continue
            try:
                delta = float(val)
            except (TypeError, ValueError):
                continue
            deltas[key] = deltas.get(key, 0.0) + delta

    if patterns_used == 0:
        return report

    # Cap total adjustment per weight
    for key in list(deltas.keys()):
        deltas[key] = max(
            -MEMORY_BIAS_MAX_TOTAL_DELTA,
            min(MEMORY_BIAS_MAX_TOTAL_DELTA, deltas[key]),
        )
    report["bias_applied"] = deltas
    report["patterns_used"] = patterns_used
    report["status"] = "ok"

    # Apply to copy of weights and clamp
    out = dict(weights)
    for key, delta in deltas.items():
        if key in out:
            out[key] = _clamp01(out[key] + delta)
    report["weights_after"] = out
    return report


# Max absolute memory bias score added per option (so ranking stays stable)
MEMORY_BIAS_SCORE_CAP = 0.1


def _pattern_matches_strategy_for_bias(summary: str, strategy: str) -> bool:
    """True if pattern summary is about this strategy (for per-option bias score)."""
    if not summary or not strategy:
        return False
    s = summary.lower()
    if strategy == "minimal" and "minimal" in s:
        return True
    if strategy == "aggressive" and "aggressive" in s:
        return True
    if strategy == "medium" and "medium" in s:
        return True
    return False


def get_memory_bias_score_for_option(
    option_id: str,
    memory_patterns_path: Path | str | None = None,
) -> float:
    """
    Return a scalar bias score for this option based on memory patterns.
    Uses same eligibility as apply_memory_bias (confidence >= 0.65, evidence >= 5).
    Only patterns whose summary matches the option's strategy contribute.
    Capped to [-MEMORY_BIAS_SCORE_CAP, MEMORY_BIAS_SCORE_CAP]. Never raises; returns 0 on missing data.
    """
    path = (
        Path(memory_patterns_path)
        if memory_patterns_path is not None
        else DEFAULT_MEMORY_PATTERNS_PATH
    )
    path = path.resolve()
    if not path.exists():
        return 0.0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0.0
    if not isinstance(data, dict):
        return 0.0
    patterns = data.get("patterns")
    if not isinstance(patterns, list):
        return 0.0
    strategy = _option_type_from_id(option_id)
    if strategy == "other":
        return 0.0
    total = 0.0
    for item in patterns:
        if not isinstance(item, dict):
            continue
        conf = item.get("confidence")
        evidence = item.get("evidence_count")
        bias = item.get("recommended_bias")
        if not isinstance(bias, dict):
            continue
        try:
            c = float(conf)
            e = int(evidence)
        except (TypeError, ValueError):
            continue
        if c < MEMORY_BIAS_MIN_CONFIDENCE or e < MEMORY_BIAS_MIN_EVIDENCE:
            continue
        summary = str(item.get("summary") or "")
        if not _pattern_matches_strategy_for_bias(summary, strategy):
            continue
        for key, val in bias.items():
            if key in ("success_weight", "risk_weight", "impact_weight"):
                try:
                    total += float(val)
                except (TypeError, ValueError):
                    pass
    return max(
        -MEMORY_BIAS_SCORE_CAP,
        min(MEMORY_BIAS_SCORE_CAP, total),
    )


def _option_type_from_id(option_id: str) -> str:
    """Extract option type from option_id (e.g. minimal-xxx -> minimal)."""
    if not option_id or "-" not in option_id:
        return "other"
    return option_id.split("-")[0].lower()


def _is_rollback(notes: str) -> bool:
    """True if notes indicate a rollback occurred."""
    if not notes:
        return False
    n = notes.lower()
    return "rollback" in n or "rolled_back" in n


def apply_self_improvement_cycle(
    history_log_path: Path | str | None = None,
    feedback_log_path: Path | str | None = None,
    weights_path: Path | str | None = None,
    weights_history_path: Path | str | None = None,
) -> dict:
    """
    Read decision history (and feedback if needed), measure success rate by option
    type, average risk by type, rollback frequency; compute very small weight
    adjustments; save to .lumos/weights.json. Safe: no update if < 10 records or
    data noisy/unclear. Returns a report dict explaining what changed.

    Does NOT run automatically at startup; call explicitly.
    """
    history_p = (
        Path(history_log_path)
        if history_log_path is not None
        else DEFAULT_DECISION_HISTORY_LOG_PATH
    )
    weights_p = Path(weights_path) if weights_path is not None else DEFAULT_WEIGHTS_PATH
    history_p = history_p.resolve()
    weights_p = weights_p.resolve()

    report: dict = {
        "changed": False,
        "records_read": 0,
        "reason_skipped": None,
        "success_rate_by_type": {},
        "avg_risk_by_type": {},
        "rollback_frequency": 0.0,
        "adjustments_applied": {},
        "weights_before": None,
        "weights_after": None,
    }

    # Load history (bounded to recent STRATEGY_RECENT_RECORDS_LIMIT)
    records = read_recent_jsonl_records(history_p, STRATEGY_RECENT_RECORDS_LIMIT)
    if not records and not history_p.exists():
        report["reason_skipped"] = "decision_history_log_missing"
        return report

    report["records_read"] = len(records)

    if len(records) < SELF_IMPROVE_MIN_RECORDS:
        report["reason_skipped"] = "fewer_than_10_records"
        return report

    # Aggregate by option type (minimal, medium, aggressive)
    by_type: dict[str, list[dict]] = {"minimal": [], "medium": [], "aggressive": []}
    rollback_count = 0
    for r in records:
        opt_type = _option_type_from_id(r.get("chosen_option_id") or "")
        if opt_type in by_type:
            by_type[opt_type].append(r)
        if _is_rollback(str(r.get("notes") or "")):
            rollback_count += 1

    total = len(records)
    report["rollback_frequency"] = rollback_count / total if total else 0.0

    for kind in ("minimal", "medium", "aggressive"):
        lst = by_type[kind]
        if not lst:
            report["success_rate_by_type"][kind] = 0.0
            report["avg_risk_by_type"][kind] = 0.0
            continue
        success_count = sum(1 for r in lst if r.get("success") is True)
        report["success_rate_by_type"][kind] = success_count / len(lst)
        risk_sum = sum(float(r.get("risk", 0) or 0) for r in lst)
        report["avg_risk_by_type"][kind] = risk_sum / len(lst)

    # Load current weights
    data = _load_weights_dict(weights_p)
    report["weights_before"] = dict(data)

    delta_success = 0.0
    delta_risk = 0.0
    delta_impact = 0.0

    # Minimal options succeed consistently -> slightly increase success_weight
    minimal_list = by_type["minimal"]
    if len(minimal_list) >= 2:
        sr_min = report["success_rate_by_type"]["minimal"]
        if sr_min >= 0.8:
            delta_success += SELF_IMPROVE_STEP

    # Aggressive options fail or rollback often -> slightly increase risk_weight
    aggressive_list = by_type["aggressive"]
    if len(aggressive_list) >= 2:
        sr_agg = report["success_rate_by_type"]["aggressive"]
        if sr_agg <= 0.5 or report["rollback_frequency"] >= 0.2:
            delta_risk += SELF_IMPROVE_STEP

    # Medium options balanced outcomes -> slightly increase impact_weight
    medium_list = by_type["medium"]
    if len(medium_list) >= 2:
        sr_med = report["success_rate_by_type"]["medium"]
        if 0.5 <= sr_med <= 0.9:
            delta_impact += SELF_IMPROVE_STEP

    # Cap deltas
    delta_success = min(delta_success, SELF_IMPROVE_MAX_DELTA)
    delta_risk = min(delta_risk, SELF_IMPROVE_MAX_DELTA)
    delta_impact = min(delta_impact, SELF_IMPROVE_MAX_DELTA)

    if delta_success == 0 and delta_risk == 0 and delta_impact == 0:
        report["reason_skipped"] = "no_clear_signal"
        return report

    # Apply and clamp
    data["success_weight"] = _clamp01(data["success_weight"] + delta_success)
    data["risk_weight"] = _clamp01(data["risk_weight"] + delta_risk)
    data["impact_weight"] = _clamp01(data["impact_weight"] + delta_impact)

    weights_after_cycle = dict(data)
    hist_p = Path(weights_history_path) if weights_history_path is not None else weights_p.parent / "weights_history.json"
    hist_p = hist_p.resolve()
    feedback_p = Path(feedback_log_path) if feedback_log_path is not None else DEFAULT_DECISION_FEEDBACK_LOG_PATH
    feedback_p = feedback_p.resolve()
    safety = evaluate_weight_update_safety(
        report["weights_before"],
        weights_after_cycle,
        feedback_log_path=feedback_p,
        weights_history_path=hist_p,
    )
    if not safety["safe"]:
        report["changed"] = False
        report["reason_skipped"] = safety["reason"]
        report["safety_report"] = safety["report"]
        if safety["reason"] == "rollback_worse_outcomes" and safety["report"].get("previous_weights"):
            weights_p.parent.mkdir(parents=True, exist_ok=True)
            _save_weights_dict(weights_p, safety["report"]["previous_weights"])
            report["rollback_applied"] = True
            report["weights_after"] = dict(safety["report"]["previous_weights"])
        return report

    report["changed"] = True
    report["adjustments_applied"] = {
        "success_weight": delta_success,
        "risk_weight": delta_risk,
        "impact_weight": delta_impact,
    }
    report["weights_after"] = weights_after_cycle
    report["reason_skipped"] = None

    weights_p.parent.mkdir(parents=True, exist_ok=True)
    _append_weights_to_history(hist_p, report["weights_before"])
    _save_weights_dict(weights_p, data)

    # Apply memory bias from compressed patterns (if any) after self-improvement
    memory_patterns_path = weights_p.parent / "memory_patterns.json"
    bias_report = apply_memory_bias(data, memory_patterns_path=memory_patterns_path)
    if bias_report.get("status") == "ok" and bias_report.get("weights_after") is not None:
        _save_weights_dict(weights_p, bias_report["weights_after"])
        report["weights_after"] = dict(bias_report["weights_after"])
        report["memory_bias"] = {
            "patterns_used": bias_report.get("patterns_used", 0),
            "bias_applied": dict(bias_report.get("bias_applied", {})),
        }

    return report

# lumos:instruction-pipeline safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)
