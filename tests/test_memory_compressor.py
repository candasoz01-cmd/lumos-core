"""Tests for memory compression: compress_runtime_memory()."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.memory_compressor import compress_runtime_memory
from core.memory_patterns import MemoryPattern


def _decision_history_line(
    chosen_option_id: str,
    success: bool,
) -> str:
    return json.dumps({
        "timestamp": "2026-01-01T12:00:00Z",
        "goal": "test",
        "chosen_option_id": chosen_option_id,
        "option_description": "desc",
        "risk": 0.2,
        "success_probability": 0.8,
        "success": success,
        "notes": "",
    }, ensure_ascii=False)


def _feedback_line(option_id: str, success: bool) -> str:
    return json.dumps({
        "option_id": option_id,
        "success": success,
        "risk": 0.1,
        "timestamp": "2026-01-01T12:00:00Z",
        "notes": "",
    }, ensure_ascii=False)


def _evolution_line(
    result: str = "ok",
    rollback_occurred: bool = False,
    sensitivity_levels: list[str] | None = None,
    affected_paths: list[str] | None = None,
) -> str:
    return json.dumps({
        "event_id": "test-id",
        "timestamp": "2026-01-01T12:00:00Z",
        "action_type": "PLAN_CREATED",
        "result": result,
        "rollback_occurred": rollback_occurred,
        "sensitivity_levels": sensitivity_levels or [],
        "affected_paths": affected_paths or [],
    }, ensure_ascii=False)


def test_no_logs_no_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No log files -> no patterns, status skipped."""
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_HISTORY_PATH", tmp_path / "logs" / "lumos_decision_history.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_FEEDBACK_PATH", tmp_path / "logs" / "lumos_decision_feedback.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_EVOLUTION_PATH", tmp_path / "logs" / "lumos_evolution.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_OUTPUT_PATH", tmp_path / ".lumos" / "memory_patterns.json")
    # No files created
    report = compress_runtime_memory()
    assert report["records_read"] == 0
    assert report["patterns_created"] == 0
    assert report["status"] == "skipped"
    assert report["reason"] == "fewer_than_20_records"
    assert not (tmp_path / ".lumos" / "memory_patterns.json").exists()


def test_too_few_records_no_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fewer than 20 combined records -> no patterns written."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    hist.write_text("\n".join(_decision_history_line(f"minimal-{i}", True) for i in range(10)), encoding="utf-8")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_HISTORY_PATH", hist)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_FEEDBACK_PATH", tmp_path / "logs" / "lumos_decision_feedback.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_EVOLUTION_PATH", tmp_path / "logs" / "lumos_evolution.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_OUTPUT_PATH", tmp_path / ".lumos" / "memory_patterns.json")
    report = compress_runtime_memory()
    assert report["records_read"] == 10
    assert report["patterns_created"] == 0
    assert report["status"] == "skipped"
    assert report["reason"] == "fewer_than_20_records"
    assert not (tmp_path / ".lumos" / "memory_patterns.json").exists()


def test_repeated_minimal_success_creates_one_pattern(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated minimal + success -> one pattern created."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    feed = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    evol = tmp_path / "logs" / "lumos_evolution.jsonl"
    out = tmp_path / ".lumos" / "memory_patterns.json"
    lines_hist = [_decision_history_line(f"minimal-{i}", True) for i in range(15)]
    lines_feed = [_feedback_line(f"minimal-{i}", True) for i in range(10)]
    hist.write_text("\n".join(lines_hist), encoding="utf-8")
    feed.write_text("\n".join(lines_feed), encoding="utf-8")
    evol.write_text("\n".join(_evolution_line() for _ in range(5)), encoding="utf-8")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_HISTORY_PATH", hist)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_FEEDBACK_PATH", feed)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_EVOLUTION_PATH", evol)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_OUTPUT_PATH", out)
    report = compress_runtime_memory()
    assert report["records_read"] == 30
    assert report["patterns_created"] >= 1
    assert report["status"] == "ok"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "patterns" in data
    summaries = [p["summary"] for p in data["patterns"]]
    assert "minimal decisions succeed often" in summaries


def test_repeated_aggressive_rollback_creates_one_pattern(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated aggressive + failure -> one pattern created."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    feed = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    evol = tmp_path / "logs" / "lumos_evolution.jsonl"
    out = tmp_path / ".lumos" / "memory_patterns.json"
    lines_hist = [_decision_history_line(f"aggressive-{i}", False) for i in range(15)]
    lines_feed = [_feedback_line(f"aggressive-{i}", False) for i in range(10)]
    hist.write_text("\n".join(lines_hist), encoding="utf-8")
    feed.write_text("\n".join(lines_feed), encoding="utf-8")
    evol.write_text("\n".join(_evolution_line() for _ in range(5)), encoding="utf-8")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_HISTORY_PATH", hist)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_FEEDBACK_PATH", feed)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_EVOLUTION_PATH", evol)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_OUTPUT_PATH", out)
    report = compress_runtime_memory()
    assert report["records_read"] == 30
    assert report["patterns_created"] >= 1
    assert report["status"] == "ok"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    summaries = [p["summary"] for p in data["patterns"]]
    assert "aggressive decisions rollback often" in summaries


def test_output_is_valid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Output file is valid JSON with expected structure."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    hist.write_text("\n".join(_decision_history_line(f"minimal-{i}", True) for i in range(25)), encoding="utf-8")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_HISTORY_PATH", hist)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_FEEDBACK_PATH", tmp_path / "logs" / "nofeed.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_EVOLUTION_PATH", tmp_path / "logs" / "noevol.jsonl")
    out = tmp_path / ".lumos" / "memory_patterns.json"
    monkeypatch.setattr("core.memory_compressor.DEFAULT_OUTPUT_PATH", out)
    report = compress_runtime_memory()
    assert report["status"] == "ok"
    raw = out.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert "patterns" in data
    assert isinstance(data["patterns"], list)
    for p in data["patterns"]:
        assert "pattern_id" in p
        assert "summary" in p
        assert "confidence" in p
        assert "evidence_count" in p
        assert "recommended_bias" in p


def test_max_patterns_capped_at_10(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """At most 10 patterns are produced."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    evol = tmp_path / "logs" / "lumos_evolution.jsonl"
    out = tmp_path / ".lumos" / "memory_patterns.json"
    # Many minimal success + many evolution lines with different path groups and sensitivities
    hist_lines = [_decision_history_line(f"minimal-{i}", True) for i in range(30)]
    evol_lines = []
    for i in range(30):
        evol_lines.append(_evolution_line(
            result="ok",
            rollback_occurred=(i % 3 == 0),
            sensitivity_levels=["CRITICAL"] if i % 2 == 0 else ["LOW"],
            affected_paths=[f"/some/core/file_{i}.py", f"/some/tools/run_{i}.py"],
        ))
    hist.write_text("\n".join(hist_lines), encoding="utf-8")
    evol.write_text("\n".join(evol_lines), encoding="utf-8")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_HISTORY_PATH", hist)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_FEEDBACK_PATH", tmp_path / "logs" / "nofeed.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_EVOLUTION_PATH", evol)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_OUTPUT_PATH", out)
    report = compress_runtime_memory()
    assert report["status"] == "ok"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["patterns"]) <= 10


def test_missing_or_malformed_logs_do_not_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing or malformed log files never raise."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    hist = tmp_path / "logs" / "lumos_decision_history.jsonl"
    hist.write_text("not json\n{}\n" + "\n".join(_decision_history_line(f"minimal-{i}", True) for i in range(25)), encoding="utf-8")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_HISTORY_PATH", hist)
    monkeypatch.setattr("core.memory_compressor.DEFAULT_DECISION_FEEDBACK_PATH", tmp_path / "nonexistent_feedback.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_EVOLUTION_PATH", tmp_path / "nonexistent_evolution.jsonl")
    monkeypatch.setattr("core.memory_compressor.DEFAULT_OUTPUT_PATH", tmp_path / ".lumos" / "memory_patterns.json")
    report = compress_runtime_memory()
    assert "records_read" in report
    assert report["records_read"] >= 25
    assert "status" in report


def test_memory_pattern_serialization() -> None:
    """MemoryPattern to_dict/from_dict roundtrip."""
    p = MemoryPattern(
        pattern_id="p0",
        source="test",
        summary="test summary",
        confidence=0.85,
        evidence_count=10,
        recommended_bias={"success_weight": 0.01},
    )
    d = p.to_dict()
    assert d["pattern_id"] == "p0"
    assert d["confidence"] == 0.85
    assert d["recommended_bias"]["success_weight"] == 0.01
    p2 = MemoryPattern.from_dict(d)
    assert p2.pattern_id == p.pattern_id
    assert p2.confidence == p.confidence
    assert p2.to_json()
    p3 = MemoryPattern.from_json(p2.to_json())
    assert p3.summary == p.summary
