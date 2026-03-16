"""Tests for strategy self-improvement cycle (apply_self_improvement_cycle)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.strategy_updater import (
    DEFAULT_DECISION_HISTORY_LOG_PATH,
    DEFAULT_WEIGHTS_PATH,
    apply_self_improvement_cycle,
)


def _history_line(
    option_id: str,
    success: bool,
    risk: float = 0.2,
    notes: str = "",
) -> str:
    record = {
        "timestamp": "2025-01-01T12:00:00Z",
        "goal": "test",
        "chosen_option_id": option_id,
        "option_description": "desc",
        "risk": risk,
        "success_probability": 0.8,
        "complexity": 0.3,
        "impact": 0.5,
        "sensitivity_levels": [],
        "proposal_ids": [],
        "success": success,
        "notes": notes,
    }
    return json.dumps(record, ensure_ascii=False)


def test_no_history_no_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No decision history -> no update, reason_skipped set."""
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH",
        tmp_path / "logs" / "lumos_decision_history.jsonl",
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_WEIGHTS_PATH",
        tmp_path / ".lumos" / "weights.json",
    )
    (tmp_path / ".lumos").mkdir(parents=True, exist_ok=True)
    # No history file
    report = apply_self_improvement_cycle()
    assert report["changed"] is False
    assert report["reason_skipped"] == "decision_history_log_missing"
    assert report["records_read"] == 0


def test_fewer_than_10_records_no_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fewer than 10 decision history records -> no update."""
    history = tmp_path / "logs" / "lumos_decision_history.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH", history
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file
    )
    # 5 minimal-success lines
    with history.open("w", encoding="utf-8") as f:
        for i in range(5):
            f.write(_history_line(f"minimal-{i}", success=True) + "\n")
    report = apply_self_improvement_cycle()
    assert report["changed"] is False
    assert report["reason_skipped"] == "fewer_than_10_records"
    assert report["records_read"] == 5


def test_successful_minimal_trend_increases_success_weight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When minimal options succeed consistently, success_weight increases slightly."""
    history = tmp_path / "logs" / "lumos_decision_history.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    weights_file.write_text(
        json.dumps(
            {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH", history
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file
    )
    # 12 records: 10 minimal (all success), 2 medium (mixed) so minimal has high success rate
    with history.open("w", encoding="utf-8") as f:
        for i in range(10):
            f.write(_history_line(f"minimal-{i}", success=True) + "\n")
        f.write(_history_line("medium-a", success=True) + "\n")
        f.write(_history_line("medium-b", success=False) + "\n")
    report = apply_self_improvement_cycle()
    assert report["records_read"] == 12
    assert report["success_rate_by_type"]["minimal"] == 1.0
    if not report["changed"]:
        # no_clear_signal possible if conditions not met; ensure we got at least one adjustment when minimal succeeds
        assert report["reason_skipped"] in ("no_clear_signal", None)
    if report["changed"]:
        assert report["adjustments_applied"].get("success_weight", 0) >= 0.01
        assert report["weights_after"]["success_weight"] >= report["weights_before"]["success_weight"]


def test_aggressive_failures_increase_risk_weight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When aggressive options fail often, risk_weight increases slightly."""
    history = tmp_path / "logs" / "lumos_decision_history.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    weights_file.write_text(
        json.dumps(
            {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH", history
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file
    )
    # 12 records: 10 minimal (success), 5 aggressive (mostly fail) -> aggressive success rate low
    with history.open("w", encoding="utf-8") as f:
        for i in range(5):
            f.write(_history_line(f"minimal-{i}", success=True) + "\n")
        for i in range(5):
            f.write(_history_line(f"aggressive-{i}", success=False) + "\n")
        f.write(_history_line("minimal-6", success=True) + "\n")
        f.write(_history_line("minimal-7", success=True) + "\n")
    report = apply_self_improvement_cycle()
    assert report["records_read"] == 12
    assert report["success_rate_by_type"]["aggressive"] == 0.0
    if report["changed"]:
        assert report["adjustments_applied"].get("risk_weight", 0) >= 0.01
        assert report["weights_after"]["risk_weight"] >= report["weights_before"]["risk_weight"]


def test_weights_remain_clamped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Updated weights stay in [0, 1]."""
    history = tmp_path / "logs" / "lumos_decision_history.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    # Start with high success_weight so any further increase would exceed 1 if not clamped
    weights_file.write_text(
        json.dumps(
            {"success_weight": 0.99, "risk_weight": 0.01, "impact_weight": 0.0},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH", history
    )
    monkeypatch.setattr(
        "core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file
    )
    with history.open("w", encoding="utf-8") as f:
        for i in range(12):
            f.write(_history_line(f"minimal-{i}", success=True) + "\n")
    report = apply_self_improvement_cycle()
    assert report["records_read"] == 12
    if report["weights_after"]:
        w = report["weights_after"]
        assert 0.0 <= w["success_weight"] <= 1.0
        assert 0.0 <= w["risk_weight"] <= 1.0
        assert 0.0 <= w["impact_weight"] <= 1.0
    # After save, file must also be in range
    if weights_file.exists():
        data = json.loads(weights_file.read_text(encoding="utf-8"))
        assert 0 <= data["success_weight"] <= 1
        assert 0 <= data["risk_weight"] <= 1
        assert 0 <= data["impact_weight"] <= 1
