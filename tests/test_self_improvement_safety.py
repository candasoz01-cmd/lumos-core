"""Tests for self-improvement safety governor: freeze, rollback, drift cap."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.strategy_updater import (
    MAX_TOTAL_DRIFT,
    RECENT_FEEDBACK_WINDOW,
    SUCCESS_RATE_FREEZE_THRESHOLD,
    SUCCESS_RATE_ROLLBACK_THRESHOLD,
    apply_decision_feedback_updates,
    apply_self_improvement_cycle,
    evaluate_weight_update_safety,
    update_weights_from_outcome,
    _append_weights_to_history,
    _load_weights_history,
)


def _feedback_line(success: bool, option_id: str = "minimal-x") -> str:
    return json.dumps(
        {"option_id": option_id, "success": success, "risk": 0.2, "timestamp": "2025-01-01T12:00:00Z", "notes": ""},
        ensure_ascii=False,
    )


def _history_line(option_id: str, success: bool) -> str:
    return json.dumps(
        {
            "timestamp": "2025-01-01T12:00:00Z",
            "goal": "test",
            "chosen_option_id": option_id,
            "success": success,
            "risk": 0.2,
            "notes": "",
        },
        ensure_ascii=False,
    )


def test_evaluate_weight_update_safety_drift_cap_exceeded(tmp_path: Path) -> None:
    """When proposed weights drift too far from baseline, safety check fails with drift_cap_exceeded."""
    baseline = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    # Propose weights that sum to > MAX_TOTAL_DRIFT drift (e.g. 0.5 total)
    proposed = {"success_weight": 0.7, "risk_weight": 0.2, "impact_weight": 0.1}
    history_file = tmp_path / "weights_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        json.dumps({"entries": [{"timestamp": "2025-01-01T00:00:00Z", "weights": baseline}]}),
        encoding="utf-8",
    )
    feedback_file = tmp_path / "feedback.jsonl"
    # High success rate so we don't trigger freeze/rollback
    for _ in range(15):
        feedback_file.write_text(_feedback_line(True) + "\n", encoding="utf-8")
    result = evaluate_weight_update_safety(
        baseline,
        proposed,
        feedback_log_path=feedback_file,
        weights_history_path=history_file,
    )
    assert result["safe"] is False
    assert result["reason"] == "drift_cap_exceeded"
    assert result["report"]["drift"] > MAX_TOTAL_DRIFT


def test_evaluate_weight_update_safety_freeze_mode(tmp_path: Path) -> None:
    """When recent success rate is below threshold, safety check fails with freeze_success_rate_below_threshold."""
    current = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    proposed = {"success_weight": 0.42, "risk_weight": 0.28, "impact_weight": 0.3}
    feedback_file = tmp_path / "feedback.jsonl"
    # Low success rate: mostly failures
    with feedback_file.open("w", encoding="utf-8") as f:
        for i in range(RECENT_FEEDBACK_WINDOW):
            f.write(_feedback_line(success=(i < 4)) + "\n")  # 4/20 = 0.2 < 0.4
    result = evaluate_weight_update_safety(
        current,
        proposed,
        feedback_log_path=feedback_file,
        weights_history_path=tmp_path / "nonexistent_history.json",
    )
    assert result["safe"] is False
    assert result["reason"] == "freeze_success_rate_below_threshold"
    assert result["report"]["recent_success_rate"] < SUCCESS_RATE_FREEZE_THRESHOLD


def test_evaluate_weight_update_safety_rollback_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When success rate is above freeze but below rollback and history exists, safety fails with rollback_worse_outcomes."""
    # Rollback threshold above freeze (0.4) so rollback path is reachable: rate in (0.4, 0.5) triggers rollback only.
    monkeypatch.setattr(
        "core.strategy_updater.SUCCESS_RATE_ROLLBACK_THRESHOLD",
        0.5,
    )
    previous = {"success_weight": 0.38, "risk_weight": 0.32, "impact_weight": 0.3}
    current = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    proposed = {"success_weight": 0.42, "risk_weight": 0.28, "impact_weight": 0.3}
    history_file = tmp_path / "weights_history.json"
    history_file.write_text(
        json.dumps({
            "entries": [
                {"timestamp": "2025-01-01T00:00:00Z", "weights": {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}},
                {"timestamp": "2025-01-02T00:00:00Z", "weights": previous},
            ]
        }),
        encoding="utf-8",
    )
    feedback_file = tmp_path / "feedback.jsonl"
    # 9/20 = 0.45: above freeze (0.4), below patched rollback (0.5) -> rollback path
    with feedback_file.open("w", encoding="utf-8") as f:
        for i in range(RECENT_FEEDBACK_WINDOW):
            f.write(_feedback_line(success=(i < 9)) + "\n")
    result = evaluate_weight_update_safety(
        current,
        proposed,
        feedback_log_path=feedback_file,
        weights_history_path=history_file,
    )
    assert result["safe"] is False
    assert result["reason"] == "rollback_worse_outcomes"
    assert result["report"]["previous_weights"] is not None
    assert result["report"]["previous_weights"]["success_weight"] == 0.38


def test_evaluate_weight_update_safety_safe_passes(tmp_path: Path) -> None:
    """When drift is within cap and success rate is ok, safety check passes."""
    current = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    proposed = {"success_weight": 0.42, "risk_weight": 0.28, "impact_weight": 0.3}
    feedback_file = tmp_path / "feedback.jsonl"
    with feedback_file.open("w", encoding="utf-8") as f:
        for _ in range(15):
            f.write(_feedback_line(True) + "\n")
    result = evaluate_weight_update_safety(
        current,
        proposed,
        feedback_log_path=feedback_file,
        weights_history_path=tmp_path / "no_history.json",
    )
    assert result["safe"] is True
    assert result["reason"] is None


def test_weights_history_append_and_load(tmp_path: Path) -> None:
    """_append_weights_to_history and _load_weights_history round-trip."""
    hist_path = tmp_path / "weights_history.json"
    w1 = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    _append_weights_to_history(hist_path, w1)
    loaded = _load_weights_history(hist_path)
    assert len(loaded) == 1
    assert loaded[0]["weights"]["success_weight"] == 0.4
    w2 = {"success_weight": 0.42, "risk_weight": 0.28, "impact_weight": 0.3}
    _append_weights_to_history(hist_path, w2, max_entries=10)
    loaded = _load_weights_history(hist_path)
    assert len(loaded) == 2
    assert loaded[1]["weights"]["success_weight"] == 0.42


def test_apply_decision_feedback_updates_freeze_does_not_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When safety fails (freeze), apply_decision_feedback_updates does not write new weights."""
    weights_file = tmp_path / ".lumos" / "weights.json"
    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    state_file = tmp_path / ".lumos" / "strategy_feedback_state.json"
    history_file = tmp_path / ".lumos" / "weights_history.json"
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_log.parent.mkdir(parents=True, exist_ok=True)
    weights_file.write_text(
        json.dumps({"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}),
        encoding="utf-8",
    )
    # Low success rate feedback so safety will freeze
    with feedback_log.open("w", encoding="utf-8") as f:
        for i in range(5):
            f.write(_feedback_line(success=(i < 1)) + "\n")
    monkeypatch.setattr("core.strategy_updater.DEFAULT_DECISION_FEEDBACK_LOG_PATH", feedback_log)
    monkeypatch.setattr("core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file)
    monkeypatch.setattr("core.strategy_updater.DEFAULT_FEEDBACK_STATE_PATH", state_file)
    n = apply_decision_feedback_updates(weights_history_path=history_file)
    assert n == 5
    # Weights should still be original (no update applied due to freeze)
    data = json.loads(weights_file.read_text(encoding="utf-8"))
    assert data["success_weight"] == 0.4
    assert data["risk_weight"] == 0.3


def test_apply_self_improvement_cycle_freeze_does_not_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When safety fails (freeze), apply_self_improvement_cycle does not change weights."""
    history = tmp_path / "logs" / "lumos_decision_history.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_log.parent.mkdir(parents=True, exist_ok=True)
    weights_file.write_text(
        json.dumps({"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}),
        encoding="utf-8",
    )
    with feedback_log.open("w", encoding="utf-8") as f:
        for i in range(25):
            f.write(_feedback_line(success=(i < 6)) + "\n")  # 0.24 < 0.4
    with history.open("w", encoding="utf-8") as f:
        for i in range(12):
            f.write(_history_line(f"minimal-{i}", success=True) + "\n")
    monkeypatch.setattr("core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH", history)
    monkeypatch.setattr("core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file)
    report = apply_self_improvement_cycle(
        feedback_log_path=feedback_log,
        weights_history_path=weights_file.parent / "weights_history.json",
    )
    assert report["changed"] is False
    assert report["reason_skipped"] == "freeze_success_rate_below_threshold"
    data = json.loads(weights_file.read_text(encoding="utf-8"))
    assert data["success_weight"] == 0.4


def test_apply_self_improvement_cycle_rollback_applies_previous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When safety fails with rollback_worse_outcomes, previous weights are written."""
    # Rollback threshold above freeze (0.4) so rollback path is reachable: rate in (0.4, 0.5) triggers rollback only.
    monkeypatch.setattr(
        "core.strategy_updater.SUCCESS_RATE_ROLLBACK_THRESHOLD",
        0.5,
    )
    history = tmp_path / "logs" / "lumos_decision_history.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    history_file = tmp_path / ".lumos" / "weights_history.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_log.parent.mkdir(parents=True, exist_ok=True)
    # Current weights on disk (e.g. after some bad drift)
    weights_file.write_text(
        json.dumps({"success_weight": 0.45, "risk_weight": 0.28, "impact_weight": 0.27}),
        encoding="utf-8",
    )
    # Last entry in history is the "previous good" state we rollback to
    previous = {"success_weight": 0.38, "risk_weight": 0.32, "impact_weight": 0.3}
    history_file.write_text(
        json.dumps({
            "entries": [
                {"timestamp": "2025-01-01T00:00:00Z", "weights": {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}},
                {"timestamp": "2025-01-02T00:00:00Z", "weights": previous},
            ]
        }),
        encoding="utf-8",
    )
    # Last RECENT_FEEDBACK_WINDOW (20) entries must have rate in (0.4, 0.5). 9/20 = 0.45.
    # So last 20 = indices 5..24; need 9 successes there -> success for i in 5..13 -> success=(i < 14).
    with feedback_log.open("w", encoding="utf-8") as f:
        for i in range(25):
            f.write(_feedback_line(success=(i < 14)) + "\n")
    with history.open("w", encoding="utf-8") as f:
        for i in range(12):
            f.write(_history_line(f"minimal-{i}", success=True) + "\n")
    monkeypatch.setattr("core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH", history)
    monkeypatch.setattr("core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file)
    report = apply_self_improvement_cycle(
        feedback_log_path=feedback_log,
        weights_history_path=history_file,
    )
    assert report.get("rollback_applied") is True
    assert report["reason_skipped"] == "rollback_worse_outcomes"
    data = json.loads(weights_file.read_text(encoding="utf-8"))
    assert data["success_weight"] == previous["success_weight"]
    assert data["risk_weight"] == previous["risk_weight"]


def test_update_weights_from_outcome_drift_cap_does_not_apply(tmp_path: Path) -> None:
    """When drift would exceed cap, update_weights_from_outcome does not apply."""
    weights_file = tmp_path / ".lumos" / "weights.json"
    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    history_file = tmp_path / ".lumos" / "weights_history.json"
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_log.parent.mkdir(parents=True, exist_ok=True)
    # Start at baseline
    weights_file.write_text(
        json.dumps({"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}),
        encoding="utf-8",
    )
    history_file.write_text(
        json.dumps({"entries": [{"timestamp": "2025-01-01T00:00:00Z", "weights": {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}}]}),
        encoding="utf-8",
    )
    # Proposed = huge drift (e.g. 0.9, 0.05, 0.05) - we can't get there in one update_weights_from_outcome step (only +0.02), so drift cap won't trigger in a single call.
    # Instead test: after many updates we'd drift; but each update_weights_from_outcome only adds 0.02. So drift cap is 0.35; after ~17 success updates we'd add 0.34 to success and subtract 0.34 from risk -> drift 0.68. So we need to simulate many calls or test via evaluate_weight_update_safety directly. For update_weights_from_outcome the drift in one step is 0.02+0.02=0.04, so safe. So "drift cap does not apply" for a single update_weights_from_outcome is already satisfied (single step is always within cap). So we test that when we artificially have high drift (e.g. weights file was manually set to something far, and we have history with baseline), then one more update might push drift over. Actually: current = 0.5, 0.25, 0.25; baseline in history = 0.4, 0.3, 0.3. Drift of current from baseline = 0.1+0.05+0.05 = 0.2. Proposed = current + (0.02, -0.02, 0) = 0.52, 0.23, 0.25. Drift of proposed from baseline = 0.12+0.07+0.05 = 0.24. Still under 0.35. To exceed 0.35 in one step we need baseline and current such that one step pushes total drift > 0.35. E.g. baseline 0.4,0.3,0.3 and current 0.5,0.25,0.25 (drift 0.2). Proposed 0.52,0.23,0.25 -> drift 0.24. So we need current that's already at 0.35 drift and then any positive delta pushes over. E.g. baseline 0.4,0.3,0.3; current 0.55,0.25,0.2 (drift 0.15+0.05+0.1=0.3). Proposed 0.57,0.23,0.2 -> drift 0.17+0.07+0.1=0.34. Still 0.34. Let's try current 0.6, 0.2, 0.2 -> drift 0.2+0.1+0.1=0.4. So if weights are 0.6,0.2,0.2 and baseline is 0.4,0.3,0.3, then proposed 0.62,0.18,0.2 has drift 0.22+0.12+0.1=0.44 > 0.35. So we need to set weights to 0.6, 0.2, 0.2 and history with baseline 0.4,0.3,0.3. Then update_weights_from_outcome(True) would try to add reward -> proposed 0.62, 0.18, 0.2. Safety would fail with drift_cap_exceeded. So weights should stay 0.6, 0.2, 0.2.
    weights_file.write_text(
        json.dumps({"success_weight": 0.6, "risk_weight": 0.2, "impact_weight": 0.2}),
        encoding="utf-8",
    )
    history_file.write_text(
        json.dumps({"entries": [{"timestamp": "2025-01-01T00:00:00Z", "weights": {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}}]}),
        encoding="utf-8",
    )
    with feedback_log.open("w", encoding="utf-8") as f:
        for _ in range(15):
            f.write(_feedback_line(True) + "\n")
    update_weights_from_outcome(
        True,
        weights_path=weights_file,
        feedback_log_path=feedback_log,
        weights_history_path=history_file,
    )
    data = json.loads(weights_file.read_text(encoding="utf-8"))
    assert data["success_weight"] == 0.6
    assert data["risk_weight"] == 0.2


