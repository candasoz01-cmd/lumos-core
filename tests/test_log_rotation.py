"""Tests for JSONL log rotation (log_rotation)."""
from __future__ import annotations

import json
from pathlib import Path

from core.log_rotation import (
    append_jsonl_with_rotation,
    rotate_jsonl_log,
)


def test_append_to_new_file(tmp_path: Path) -> None:
    """Append to non-existent file creates it and writes one line."""
    p = tmp_path / "new.jsonl"
    rec = {"a": 1, "b": "test"}
    out = append_jsonl_with_rotation(p, rec, max_bytes=1000, keep=2)
    assert out["appended"] is True
    assert out["rotated"] is False
    assert p.exists()
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == rec


def test_append_without_rotation(tmp_path: Path) -> None:
    """Append when under size limit does not rotate."""
    p = tmp_path / "small.jsonl"
    p.write_text('{"x": 1}\n', encoding="utf-8")
    out = append_jsonl_with_rotation(p, {"x": 2}, max_bytes=10_000, keep=3)
    assert out["appended"] is True
    assert out["rotated"] is False
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1]) == {"x": 2}


def test_rotate_when_size_limit_exceeded(tmp_path: Path) -> None:
    """When file size >= max_bytes, rotation happens before append."""
    p = tmp_path / "big.jsonl"
    # Write enough to exceed a small limit (e.g. 50 bytes)
    chunk = '{"id": 1, "data": "hello"}\n'
    p.write_text(chunk * 5, encoding="utf-8")
    assert p.stat().st_size >= 50
    out = append_jsonl_with_rotation(p, {"id": 6}, max_bytes=50, keep=3)
    assert out["appended"] is True
    assert out["rotated"] is True
    # Current file should only have the new line
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"id": 6}
    # Rotated file .1 should exist with old content
    p1 = Path(str(p) + ".1")
    assert p1.exists()
    old_lines = p1.read_text(encoding="utf-8").strip().splitlines()
    assert len(old_lines) == 5


def test_keep_three_active_rotations_and_all_older_records(tmp_path: Path) -> None:
    """The active window is bounded while all older content remains available."""
    p = tmp_path / "log.jsonl"
    max_b = 40
    keep = 3
    # Force multiple rotations by appending and growing
    for i in range(10):
        rec = {"i": i, "payload": "x" * 20}
        append_jsonl_with_rotation(p, rec, max_bytes=max_b, keep=keep)
    # We should have at most: log.jsonl, log.jsonl.1, log.jsonl.2, log.jsonl.3
    rotated = [Path(str(p) + f".{n}") for n in range(1, keep + 1)]
    for r in rotated:
        assert r.exists(), f"expected {r} to exist"
    # .4 should not exist
    assert not Path(str(p) + ".4").exists()
    archived = list((tmp_path / ".retained-logs/log.jsonl").glob("*.jsonl"))
    rows = [json.loads(line) for f in [p, *rotated, *archived]
            for line in f.read_text().splitlines()]
    assert sorted(row["i"] for row in rows) == list(range(10))


def test_non_positive_max_bytes_clamped_to_default(tmp_path: Path) -> None:
    """max_bytes <= 0 is invalid; treat as DEFAULT_MAX_BYTES so rotation logic is safe."""
    p = tmp_path / "clamp.jsonl"
    p.write_text('{"n": 1}\n', encoding="utf-8")
    out = rotate_jsonl_log(p, max_bytes=0, keep=3)
    assert out["rotated"] is False
    out2 = append_jsonl_with_rotation(p, {"n": 2}, max_bytes=-1, keep=3)
    assert out2["appended"] is True
    assert out2["rotated"] is False


def test_rotate_jsonl_log_missing_file_never_raises(tmp_path: Path) -> None:
    """rotate_jsonl_log on missing file returns rotated=False, does not raise."""
    p = tmp_path / "missing.jsonl"
    out = rotate_jsonl_log(p, max_bytes=100, keep=3)
    assert out["rotated"] is False
    assert out["size_before"] == 0


def test_evolution_log_still_writes(tmp_path: Path, monkeypatch) -> None:
    """Integration: evolution log record_event still writes via rotation."""
    from core.evolution_log import record_event, get_recent_events

    monkeypatch.setattr("core.evolution_log.LOG_PATH", tmp_path / "lumos_evolution.jsonl")
    record_event(
        plan_id=None,
        patch_ids=[],
        action_type="PLAN_CREATED",
        result="ok",
        affected_paths=[],
        sensitivity_levels=[],
        rollback_occurred=False,
        conflict_detected=False,
    )
    events = get_recent_events(5)
    assert len(events) >= 1
    assert events[-1]["action_type"] == "PLAN_CREATED"


def test_decision_feedback_log_still_writes(tmp_path: Path, monkeypatch) -> None:
    """Integration: decision feedback log record_execution still writes."""
    from core.decision_runner import DecisionExecutionResult
    from core.decision_model import MutationOption
    from core.evolution_tracker import record_execution

    feedback_log = tmp_path / "logs" / "lumos_decision_feedback.jsonl"
    monkeypatch.setattr(
        "core.evolution_tracker.DECISION_FEEDBACK_LOG_PATH",
        feedback_log,
    )
    option = MutationOption(
        option_id="test-opt",
        description="Minimal",
        target_paths=[],
        estimated_risk=0.1,
        estimated_complexity=0.2,
        estimated_success_probability=0.9,
        estimated_impact=0.3,
        sensitivity_summary=[],
        score=0.5,
        rationale="test",
    )
    result = DecisionExecutionResult(
        option=option,
        success=True,
        notes="",
        proposal_ids=(),
        decision_explanation="",
    )
    record_execution(result)
    assert feedback_log.exists()
    lines = [
        ln
        for ln in feedback_log.read_text(encoding="utf-8").strip().splitlines()
        if ln
    ]
    assert len(lines) >= 1
    rec = json.loads(lines[-1])
    assert rec.get("option_id") == "test-opt"
    assert rec.get("success") is True


def test_decision_history_log_still_writes(tmp_path: Path, monkeypatch) -> None:
    """Integration: decision history record_decision_history still writes."""
    from core.change_sensitivity import ChangeSensitivity
    from core.decision_history import record_decision_history
    from core.decision_model import MutationOption
    from core.decision_runner import DecisionExecutionResult

    history_log = tmp_path / "logs" / "lumos_decision_history.jsonl"
    monkeypatch.setattr(
        "core.decision_history.DECISION_HISTORY_LOG_PATH",
        history_log,
    )
    option = MutationOption(
        option_id="minimal-abc",
        description="Minimal",
        target_paths=[Path("src/foo.py")],
        estimated_risk=0.1,
        estimated_complexity=0.2,
        estimated_success_probability=0.9,
        estimated_impact=0.4,
        sensitivity_summary=[ChangeSensitivity.LOW],
        score=0.5,
        rationale="minimal",
    )
    result = DecisionExecutionResult(
        option=option,
        success=True,
        notes="",
        proposal_ids=("p1",),
        decision_explanation="Ok",
    )
    record_decision_history(result, "test goal")
    assert history_log.exists()
    lines = [
        ln
        for ln in history_log.read_text(encoding="utf-8").strip().splitlines()
        if ln
    ]
    assert len(lines) >= 1
    rec = json.loads(lines[-1])
    assert rec.get("goal") == "test goal"
    assert rec.get("chosen_option_id") == "minimal-abc"


def test_archive_failure_keeps_rotation_sources(tmp_path, monkeypatch):
    import core.log_rotation as rotation
    p = tmp_path / "events.jsonl"
    p.write_bytes(b'current\r\n')
    oldest = Path(str(p) + '.1')
    oldest.write_bytes(b'oldest\r\n')
    def fail(*args, **kwargs):
        raise OSError('archive unavailable')
    monkeypatch.setattr(rotation.os, 'link', fail)
    result = rotate_jsonl_log(p, max_bytes=1, keep=1)
    assert result['error'] == 'archive unavailable'
    assert not result['rotated']
    assert not result['files_removed']
    assert p.read_bytes() == b'current\r\n'
    assert oldest.read_bytes() == b'oldest\r\n'


def test_rotation_archive_is_independent_exact_copy(tmp_path):
    p = tmp_path / 'events.jsonl'
    p.write_bytes(b'new')
    oldest = Path(str(p) + '.1')
    old = b'unknown legacy content\r\n\xff'
    oldest.write_bytes(old)
    result = rotate_jsonl_log(p, max_bytes=1, keep=1)
    assert result['rotated']
    assert result['files_removed'] == []
    saved = Path(result['files_archived'][0])
    assert saved.read_bytes() == old
    oldest.write_bytes(b'changed later')
    assert saved.read_bytes() == old


def test_repeated_publication_failure_reuses_one_pending_copy(tmp_path, monkeypatch):
    import core.log_rotation as rotation
    p = tmp_path / 'events.jsonl'
    p.write_bytes(b'current\n')
    Path(str(p) + '.1').write_bytes(b'oldest\r\n')
    original = rotation.os.link
    def fail(*args, **kwargs):
        raise OSError('publication unavailable')
    monkeypatch.setattr(rotation.os, 'link', fail)
    for i in range(8):
        result = append_jsonl_with_rotation(p, {'i': i}, max_bytes=1, keep=1)
        assert result['error'] == 'publication unavailable'
    archive = tmp_path / '.retained-logs/events.jsonl'
    pending = list(archive.glob('*.pending'))
    assert len(pending) == 1
    assert pending[0].read_bytes() == b'oldest\r\n'
    monkeypatch.setattr(rotation.os, 'link', original)
    assert rotate_jsonl_log(p, max_bytes=1, keep=1)['rotated']
    assert len(list(archive.glob('*.pending'))) == 1
    assert len(list(archive.glob('*.jsonl'))) == 1


def test_incomplete_copy_stops_retries_without_new_copies(tmp_path, monkeypatch):
    import core.log_rotation as rotation
    p = tmp_path / 'events.jsonl'
    p.write_bytes(b'current')
    Path(str(p) + '.1').write_bytes(b'oldest')
    def partial(source, target):
        target.write(b'o')
        raise OSError('copy interrupted')
    monkeypatch.setattr(rotation.shutil, 'copyfileobj', partial)
    assert rotate_jsonl_log(p, 1, 1)['error'] == 'copy interrupted'
    for _ in range(5):
        assert 'recovery required' in rotate_jsonl_log(p, 1, 1)['error']
    assert len(list((tmp_path / '.retained-logs/events.jsonl').glob('*.pending'))) == 1
    assert p.read_bytes() == b'current'
    assert Path(str(p) + '.1').read_bytes() == b'oldest'


def test_repeated_fsync_failure_does_not_allocate_copies(tmp_path, monkeypatch):
    import core.log_rotation as rotation
    p = tmp_path / 'events.jsonl'
    p.write_bytes(b'current')
    Path(str(p) + '.1').write_bytes(b'oldest')
    original = rotation.os.fsync
    def fail(*args):
        raise OSError('fsync unavailable')
    monkeypatch.setattr(rotation.os, 'fsync', fail)
    for _ in range(6):
        assert rotate_jsonl_log(p, 1, 1)['error'] == 'fsync unavailable'
    archive = tmp_path / '.retained-logs/events.jsonl'
    assert len(list(archive.glob('*.pending'))) == 1
    monkeypatch.setattr(rotation.os, 'fsync', original)
    assert rotate_jsonl_log(p, 1, 1)['rotated']
    assert len(list(archive.glob('*.jsonl'))) == 1
