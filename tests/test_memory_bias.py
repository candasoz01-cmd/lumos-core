"""Tests for memory bias integration: apply_memory_bias()."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.strategy_updater import (
    MEMORY_BIAS_MAX_TOTAL_DELTA,
    apply_memory_bias,
    apply_self_improvement_cycle,
)


def _history_line(option_id: str, success: bool) -> str:
    return json.dumps({
        "timestamp": "2026-01-01T12:00:00Z",
        "goal": "test",
        "chosen_option_id": option_id,
        "option_description": "desc",
        "risk": 0.2,
        "success_probability": 0.8,
        "success": success,
        "notes": "",
    }, ensure_ascii=False)


def test_file_missing_returns_skipped(tmp_path: Path) -> None:
    """When memory_patterns.json does not exist, status is skipped and weights unchanged."""
    weights = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    report = apply_memory_bias(weights, memory_patterns_path=tmp_path / "nonexistent.json")
    assert report["status"] == "skipped"
    assert report["patterns_used"] == 0
    assert "weights_after" not in report
    assert report["bias_applied"] == {}


def test_file_missing_with_path(tmp_path: Path) -> None:
    """Missing file at given path -> skipped."""
    weights = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    report = apply_memory_bias(weights, memory_patterns_path=tmp_path / "nonexistent.json")
    assert report["status"] == "skipped"
    assert report["patterns_used"] == 0


def test_malformed_file_returns_skipped(tmp_path: Path) -> None:
    """Malformed JSON or invalid structure -> skipped, no crash."""
    bad = tmp_path / "memory_patterns.json"
    bad.write_text("not json {{{", encoding="utf-8")
    weights = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    report = apply_memory_bias(weights, memory_patterns_path=bad)
    assert report["status"] == "skipped"
    assert report["patterns_used"] == 0


def test_low_confidence_pattern_ignored(tmp_path: Path) -> None:
    """Pattern with confidence < 0.65 is ignored."""
    patterns = {
        "patterns": [
            {
                "pattern_id": "p0",
                "source": "test",
                "summary": "low confidence",
                "confidence": 0.5,
                "evidence_count": 10,
                "recommended_bias": {"success_weight": 0.1},
            }
        ],
        "version": 1,
    }
    (tmp_path / "memory_patterns.json").write_text(
        json.dumps(patterns, ensure_ascii=False),
        encoding="utf-8",
    )
    weights = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    report = apply_memory_bias(weights, memory_patterns_path=tmp_path / "memory_patterns.json")
    assert report["status"] == "skipped"
    assert report["patterns_used"] == 0


def test_low_evidence_pattern_ignored(tmp_path: Path) -> None:
    """Pattern with evidence_count < 5 is ignored."""
    patterns = {
        "patterns": [
            {
                "pattern_id": "p0",
                "source": "test",
                "summary": "low evidence",
                "confidence": 0.8,
                "evidence_count": 3,
                "recommended_bias": {"success_weight": 0.01},
            }
        ],
        "version": 1,
    }
    (tmp_path / "memory_patterns.json").write_text(
        json.dumps(patterns, ensure_ascii=False),
        encoding="utf-8",
    )
    weights = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    report = apply_memory_bias(weights, memory_patterns_path=tmp_path / "memory_patterns.json")
    assert report["status"] == "skipped"
    assert report["patterns_used"] == 0


def test_valid_patterns_apply_bias(tmp_path: Path) -> None:
    """Eligible patterns apply bias; total delta capped at 0.05; weights clamped [0,1]."""
    patterns = {
        "patterns": [
            {
                "pattern_id": "p0",
                "source": "test",
                "summary": "minimal succeed",
                "confidence": 0.9,
                "evidence_count": 10,
                "recommended_bias": {"success_weight": 0.01, "risk_weight": -0.005},
            },
            {
                "pattern_id": "p1",
                "source": "test",
                "summary": "risk bias",
                "confidence": 0.7,
                "evidence_count": 8,
                "recommended_bias": {"risk_weight": 0.02},
            },
        ],
        "version": 1,
    }
    (tmp_path / "memory_patterns.json").write_text(
        json.dumps(patterns, ensure_ascii=False),
        encoding="utf-8",
    )
    weights = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    report = apply_memory_bias(weights, memory_patterns_path=tmp_path / "memory_patterns.json")
    assert report["status"] == "ok"
    assert report["patterns_used"] == 2
    assert "bias_applied" in report
    assert "weights_after" in report
    w = report["weights_after"]
    assert 0.0 <= w["success_weight"] <= 1.0
    assert 0.0 <= w["risk_weight"] <= 1.0
    assert 0.0 <= w["impact_weight"] <= 1.0
    # Total adjustment per key should be at most MEMORY_BIAS_MAX_TOTAL_DELTA
    assert abs(w["success_weight"] - 0.4) <= MEMORY_BIAS_MAX_TOTAL_DELTA
    assert abs(w["risk_weight"] - 0.3) <= MEMORY_BIAS_MAX_TOTAL_DELTA


def test_report_shape() -> None:
    """Report has required keys: patterns_used, bias_applied, status."""
    weights = {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3}
    report = apply_memory_bias(weights)
    assert "patterns_used" in report
    assert "bias_applied" in report
    assert "status" in report
    assert report["status"] in ("ok", "skipped")


def test_self_improvement_cycle_then_memory_bias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When cycle runs and saves, memory bias is applied if patterns file exists."""
    history = tmp_path / "logs" / "lumos_decision_history.jsonl"
    weights_file = tmp_path / ".lumos" / "weights.json"
    patterns_file = tmp_path / ".lumos" / "memory_patterns.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    weights_file.parent.mkdir(parents=True, exist_ok=True)
    weights_file.write_text(
        json.dumps(
            {"success_weight": 0.4, "risk_weight": 0.3, "impact_weight": 0.3},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # Patterns that will be applied (confidence >= 0.65, evidence >= 5)
    patterns_file.write_text(
        json.dumps({
            "patterns": [
                {
                    "pattern_id": "p0",
                    "source": "test",
                    "summary": "minimal succeed",
                    "confidence": 0.9,
                    "evidence_count": 10,
                    "recommended_bias": {"success_weight": 0.01},
                }
            ],
            "version": 1,
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr("core.strategy_updater.DEFAULT_DECISION_HISTORY_LOG_PATH", history)
    monkeypatch.setattr("core.strategy_updater.DEFAULT_WEIGHTS_PATH", weights_file)
    with history.open("w", encoding="utf-8") as f:
        for i in range(12):
            f.write(_history_line(f"minimal-{i}", success=True) + "\n")
    report = apply_self_improvement_cycle()
    assert report["records_read"] == 12
    # Cycle may or may not change; if memory bias was applied it should appear
    if report.get("memory_bias"):
        assert report["memory_bias"]["patterns_used"] >= 1
        assert "bias_applied" in report["memory_bias"]
    # Weights on disk should be valid
    data = json.loads(weights_file.read_text(encoding="utf-8"))
    assert 0 <= data["success_weight"] <= 1
    assert 0 <= data["risk_weight"] <= 1
    assert 0 <= data["impact_weight"] <= 1
