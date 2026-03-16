"""Tests for bounded recent-history JSONL reading (log_window)."""
from __future__ import annotations

import json
from pathlib import Path

from core.log_window import read_recent_jsonl_records, read_recent_jsonl_matching


def test_missing_file_returns_empty_list(tmp_path: Path) -> None:
    """Missing file -> empty list, never raise."""
    missing = tmp_path / "nonexistent.jsonl"
    assert read_recent_jsonl_records(missing, 10) == []
    assert read_recent_jsonl_matching(missing, 10) == []
    assert read_recent_jsonl_matching(missing, 10, required_keys=["x"]) == []


def test_malformed_lines_ignored(tmp_path: Path) -> None:
    """Malformed JSON lines are skipped; valid ones returned."""
    p = tmp_path / "mixed.jsonl"
    p.write_text(
        '{"a": 1}\n'
        "not json\n"
        '{"b": 2}\n'
        "{}\n"
        '{"c": 3}\n',
        encoding="utf-8",
    )
    got = read_recent_jsonl_records(p, 10)
    assert len(got) == 4
    assert got[0].get("a") == 1
    assert got[1].get("b") == 2
    assert got[3].get("c") == 3
    assert got[3] == {"c": 3}


def test_returns_only_newest_n_records(tmp_path: Path) -> None:
    """Only the most recent N records are returned."""
    p = tmp_path / "many.jsonl"
    lines = [json.dumps({"i": i}, ensure_ascii=False) for i in range(50)]
    p.write_text("\n".join(lines), encoding="utf-8")
    got = read_recent_jsonl_records(p, 5)
    assert len(got) == 5
    assert [r["i"] for r in got] == [45, 46, 47, 48, 49]


def test_preserves_chronological_order(tmp_path: Path) -> None:
    """Returned records are in original chronological order (oldest to newest in window)."""
    p = tmp_path / "order.jsonl"
    p.write_text(
        "\n".join(json.dumps({"n": n}) for n in range(10)),
        encoding="utf-8",
    )
    got = read_recent_jsonl_records(p, 4)
    assert [r["n"] for r in got] == [6, 7, 8, 9]


def test_limit_zero_returns_empty(tmp_path: Path) -> None:
    """limit <= 0 -> empty list."""
    p = tmp_path / "any.jsonl"
    p.write_text('{"a": 1}\n', encoding="utf-8")
    assert read_recent_jsonl_records(p, 0) == []
    assert read_recent_jsonl_records(p, -1) == []


def test_fewer_than_limit_returns_all(tmp_path: Path) -> None:
    """If fewer than limit records exist, all are returned."""
    p = tmp_path / "few.jsonl"
    p.write_text('{"x": 1}\n{"x": 2}\n', encoding="utf-8")
    got = read_recent_jsonl_records(p, 10)
    assert len(got) == 2
    assert [r["x"] for r in got] == [1, 2]


def test_read_recent_jsonl_matching_required_keys(tmp_path: Path) -> None:
    """read_recent_jsonl_matching filters by required_keys when provided."""
    p = tmp_path / "keys.jsonl"
    p.write_text(
        '{"a": 1, "b": 2}\n'
        '{"a": 3}\n'
        '{"a": 4, "b": 5, "c": 6}\n',
        encoding="utf-8",
    )
    got = read_recent_jsonl_matching(p, 10, required_keys=["a", "b"])
    assert len(got) == 2
    assert got[0] == {"a": 1, "b": 2}
    assert got[1] == {"a": 4, "b": 5, "c": 6}


def test_read_recent_jsonl_matching_no_required_keys_same_as_records(
    tmp_path: Path,
) -> None:
    """When required_keys is None or empty, same as read_recent_jsonl_records."""
    p = tmp_path / "same.jsonl"
    p.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")
    r1 = read_recent_jsonl_records(p, 10)
    r2 = read_recent_jsonl_matching(p, 10, required_keys=None)
    r3 = read_recent_jsonl_matching(p, 10, required_keys=[])
    assert r1 == r2 == r3


def test_non_dict_lines_ignored(tmp_path: Path) -> None:
    """Non-dict JSON values (array, number) are skipped."""
    p = tmp_path / "nondict.jsonl"
    p.write_text('[1, 2]\n42\n{"ok": true}\n', encoding="utf-8")
    got = read_recent_jsonl_records(p, 10)
    assert len(got) == 1
    assert got[0] == {"ok": True}


def test_str_path_accepted(tmp_path: Path) -> None:
    """path can be str or Path."""
    p = tmp_path / "str_path.jsonl"
    p.write_text('{"k": 1}\n', encoding="utf-8")
    assert len(read_recent_jsonl_records(str(p), 5)) == 1
    assert len(read_recent_jsonl_records(p, 5)) == 1
