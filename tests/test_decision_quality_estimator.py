"""Tests for decision quality estimator: estimate_decision_quality()."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.decision_quality_estimator import estimate_decision_quality


def _history_line(option_id: str, success: bool, notes: str = "") -> str:
    return json.dumps({
        "timestamp": "2026-01-01T12:00:00Z",
        "goal": "test",
        "chosen_option_id": option_id,
        "success": success,
        "notes": notes,
    }, ensure_ascii=False)


def _feedback_line(option_id: str, success: bool) -> str:
    return json.dumps({
        "option_id": option_id,
        "success": success,
        "timestamp": "2026-01-01T12:00:00Z",
        "notes": "",
    }, ensure_ascii=False)


def test_no_logs_neutral_prediction(tmp_path: Path) -> None:
    """No or insufficient history -> neutral prediction."""
    option = {"strategy": "minimal", "target_path": "/a/b", "estimated_impact": 0.3}
    context = {"sensitivity": "LOW", "file_type": "py"}
    report = estimate_decision_quality(
        option,
        context,
        history_path=tmp_path / "nonexistent_history.jsonl",
        feedback_path=tmp_path / "nonexistent_feedback.jsonl",
        memory_patterns_path=tmp_path / "nonexistent_patterns.json",
    )
    assert report["predicted_success"] == 0.5
    assert report["predicted_risk"] == 0.5
    assert report["confidence"] == 0.2
    assert "insufficient" in report["explanation"].lower()


def test_fewer_than_20_records_neutral(tmp_path: Path) -> None:
    """Fewer than MIN_HISTORY_RECORDS -> neutral."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    hist.write_text(
        "\n".join(_history_line(f"minimal-{i}", True) for i in range(10)),
        encoding="utf-8",
    )
    option = {"strategy": "minimal"}
    context = {}
    report = estimate_decision_quality(
        option,
        context,
        history_path=hist,
        feedback_path=tmp_path / "nofeed.jsonl",
        memory_patterns_path=tmp_path / "nopatterns.json",
    )
    assert report["predicted_success"] == 0.5
    assert report["predicted_risk"] == 0.5
    assert report["confidence"] == 0.2


def test_minimal_success_trend_success_above_06(tmp_path: Path) -> None:
    """When minimal options succeed often, predicted_success > 0.6."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    feed = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    lines = [_history_line(f"minimal-{i}", True) for i in range(15)]
    lines += [_feedback_line(f"minimal-{i}", True) for i in range(10)]
    hist.write_text("\n".join(lines[:15]), encoding="utf-8")
    feed.write_text("\n".join(lines[15:]), encoding="utf-8")
    option = {"strategy": "minimal", "target_path": "/x", "estimated_impact": 0.2}
    context = {"sensitivity": "LOW"}
    report = estimate_decision_quality(
        option,
        context,
        history_path=hist,
        feedback_path=feed,
        memory_patterns_path=tmp_path / "nopatterns.json",
    )
    assert report["predicted_success"] > 0.6
    assert report["predicted_risk"] < 0.5
    assert report["confidence"] >= 0.2


def test_aggressive_rollback_trend_risk_above_06(tmp_path: Path) -> None:
    """When aggressive options fail/rollback often, predicted_risk > 0.6."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    feed = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    history_lines = [
        _history_line(f"aggressive-{i}", False, "rolled_back")
        for i in range(15)
    ]
    feedback_lines = [_feedback_line(f"aggressive-{i}", False) for i in range(10)]
    hist.write_text("\n".join(history_lines), encoding="utf-8")
    feed.write_text("\n".join(feedback_lines), encoding="utf-8")
    option = {"strategy": "aggressive"}
    context = {}
    report = estimate_decision_quality(
        option,
        context,
        history_path=hist,
        feedback_path=feed,
        memory_patterns_path=tmp_path / "nopatterns.json",
    )
    assert report["predicted_risk"] > 0.6
    assert report["predicted_success"] < 0.5


def test_memory_pattern_bias_modifies_prediction(tmp_path: Path) -> None:
    """Memory pattern matching strategy can boost success or risk."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    feed = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    # 25 minimal successes
    hist.write_text(
        "\n".join(_history_line(f"minimal-{i}", True) for i in range(15)),
        encoding="utf-8",
    )
    feed.write_text(
        "\n".join(_feedback_line(f"minimal-{i}", True) for i in range(10)),
        encoding="utf-8",
    )
    patterns_file = tmp_path / ".lumos" / "memory_patterns.json"
    patterns_file.parent.mkdir(parents=True, exist_ok=True)
    patterns_file.write_text(
        json.dumps({
            "patterns": [
                {
                    "pattern_id": "p0",
                    "source": "test",
                    "summary": "minimal decisions succeed often",
                    "confidence": 0.9,
                    "evidence_count": 20,
                    "recommended_bias": {"success_weight": 0.01},
                }
            ],
            "version": 1,
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    option = {"strategy": "minimal"}
    context = {}
    report_with = estimate_decision_quality(
        option,
        context,
        history_path=hist,
        feedback_path=feed,
        memory_patterns_path=patterns_file,
    )
    report_without = estimate_decision_quality(
        option,
        context,
        history_path=hist,
        feedback_path=feed,
        memory_patterns_path=tmp_path / "nonexistent_patterns.json",
    )
    assert report_with["predicted_success"] >= report_without["predicted_success"]


def test_values_always_clamped(tmp_path: Path) -> None:
    """All numeric outputs are in [0, 1]."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    feed = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    hist.write_text(
        "\n".join(_history_line(f"minimal-{i}", True) for i in range(25)),
        encoding="utf-8",
    )
    feed.write_text("", encoding="utf-8")
    for strategy in ("minimal", "medium", "aggressive"):
        report = estimate_decision_quality(
            {"strategy": strategy},
            {},
            history_path=hist,
            feedback_path=feed,
            memory_patterns_path=tmp_path / "nopatterns.json",
        )
        assert 0.0 <= report["predicted_success"] <= 1.0
        assert 0.0 <= report["predicted_risk"] <= 1.0
        assert 0.0 <= report["confidence"] <= 1.0
        assert isinstance(report["explanation"], str)


def test_never_raises(tmp_path: Path) -> None:
    """Invalid inputs or missing keys do not raise."""
    for opt in [{}, {"strategy": "x"}, None]:
        for ctx in [{}, None]:
            try:
                report = estimate_decision_quality(
                    opt if opt is not None else {},
                    ctx if ctx is not None else {},
                    history_path=tmp_path / "no.jsonl",
                    feedback_path=tmp_path / "no2.jsonl",
                    memory_patterns_path=tmp_path / "no3.json",
                )
            except Exception as e:
                pytest.fail(f"estimate_decision_quality raised {e}")
            assert "predicted_success" in report
            assert "predicted_risk" in report
            assert "confidence" in report
            assert "explanation" in report
