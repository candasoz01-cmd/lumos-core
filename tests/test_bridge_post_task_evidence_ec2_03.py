"""EC2-03: köprü POST /task outbox sonrası evidence journal mirror (T1–T9)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_BRIDGE_TASK_POST,
    OUTCOME_ERROR,
    OUTCOME_OK,
    PHASE_AFTER,
    SOURCE_KANDO_BRIDGE,
    STORE_BRIDGE_OUTBOX,
    evidence_continuity_path,
    mirror_post_task_outbox_record,
    mirror_post_task_outbox_to_evidence_journal,
    title_preview_from,
    validate_evidence_record,
)
from kando_bridge.server import persist_post_task_outbox_snapshots  # noqa: E402


def _read_journal_records(tmp_path: Path) -> list[dict]:
    journal = evidence_continuity_path(tmp_path)
    if not journal.is_file():
        return []
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").strip().splitlines() if line.strip()]


def _setup_outbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from kando_bridge import server as srv

    outbox = tmp_path / ".lumos" / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "OUTBOX_DIR", outbox)
    monkeypatch.setattr(srv, "LAST_EXECUTION_FILE", outbox / "last_execution.json")
    monkeypatch.setattr(srv, "LAST_RESULT_FILE", outbox / "last_result.json")


def _persist_and_mirror(
    tmp_path: Path,
    envelope_meta: dict,
    snapshot: dict | None,
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> list[dict]:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    _setup_outbox(tmp_path, monkeypatch)
    persist_post_task_outbox_snapshots(envelope_meta, snapshot)
    mirror_post_task_outbox_to_evidence_journal(envelope_meta, snapshot, base_dir=tmp_path)
    return _read_journal_records(tmp_path)


def test_t1_isolated_mirror_after_outbox_persist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T1: persist + mirror → tek journal satırı."""
    raw = json.dumps({"goal": "README düzelt", "source": "panel_chat"}, ensure_ascii=False).encode()
    records = _persist_and_mirror(
        tmp_path,
        {"raw": raw, "route": "agent"},
        {"http_status": 200, "response": {"accepted": True, "ok": True, "mode": "agent"}},
        monkeypatch=monkeypatch,
    )
    assert len(records) == 1
    assert (tmp_path / ".lumos" / "outbox" / "last_execution.json").is_file()


def test_t2_successful_agent_post_after_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T2: başarılı agent POST /task → after + ok + bridge enum."""
    raw = json.dumps({"goal": "README düzelt", "source": "panel_gorevler"}, ensure_ascii=False).encode()
    records = _persist_and_mirror(
        tmp_path,
        {"raw": raw, "route": "agent"},
        {"http_status": 200, "response": {"accepted": True, "ok": True, "mode": "agent"}},
        monkeypatch=monkeypatch,
    )
    rec = records[0]
    assert rec["phase"] == PHASE_AFTER
    assert rec["outcome"] == OUTCOME_OK
    assert rec["source"] == SOURCE_KANDO_BRIDGE
    assert rec["store"] == STORE_BRIDGE_OUTBOX
    assert rec["operation"] == OPERATION_BRIDGE_TASK_POST


def test_t3_accepted_false_or_4xx_outcome_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T3: accepted false / 4xx → outcome error + kısa error.code."""
    raw = json.dumps({"goal": "sil her şeyi"}, ensure_ascii=False).encode()
    records = _persist_and_mirror(
        tmp_path,
        {"raw": raw, "route": "agent"},
        {
            "http_status": 403,
            "response": {"accepted": False, "error": "blocked by lumos"},
        },
        monkeypatch=monkeypatch,
    )
    rec = records[0]
    assert rec["outcome"] == OUTCOME_ERROR
    assert rec.get("error", {}).get("code") == "blocked by lumos"
    assert "secret" not in json.dumps(rec).lower()

    raw2 = json.dumps({"goal": "test"}, ensure_ascii=False).encode()
    records2 = _persist_and_mirror(
        tmp_path,
        {"raw": raw2, "route": "agent"},
        {
            "http_status": 200,
            "response": {"accepted": False, "error": "pending_approval"},
        },
        monkeypatch=monkeypatch,
    )
    assert records2[-1]["outcome"] == OUTCOME_ERROR


def test_t4_snapshot_none_still_appends_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T4: snapshot None → journal satırı var, outcome error."""
    raw = json.dumps({"goal": "no response"}, ensure_ascii=False).encode()
    records = _persist_and_mirror(
        tmp_path,
        {"raw": raw, "route": "agent"},
        None,
        monkeypatch=monkeypatch,
    )
    assert len(records) == 1
    assert records[0]["outcome"] == OUTCOME_ERROR


def test_t5_two_consecutive_posts_append_two_journal_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T5: iki POST → outbox overwrite, journal iki satır."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    _setup_outbox(tmp_path, monkeypatch)
    for i in range(2):
        raw = json.dumps({"goal": f"görev {i}"}, ensure_ascii=False).encode()
        meta = {"raw": raw, "route": "agent"}
        snap = {"http_status": 200, "response": {"accepted": True, "ok": True}}
        persist_post_task_outbox_snapshots(meta, snap)
        mirror_post_task_outbox_to_evidence_journal(meta, snap, base_dir=tmp_path)
    outbox = tmp_path / ".lumos" / "outbox"
    assert outbox.joinpath("last_execution.json").is_file()
    assert outbox.joinpath("last_result.json").is_file()
    records = _read_journal_records(tmp_path)
    assert len(records) == 2
    assert records[0]["payload_summary"]["title_preview"] != records[1]["payload_summary"]["title_preview"]


def test_t6_long_goal_title_preview_truncated() -> None:
    """T6: uzun goal → title_preview ≤40, ham metin journal builder'da yok."""
    long_goal = "x" * 200
    raw = json.dumps({"goal": long_goal}, ensure_ascii=False).encode()
    rec = mirror_post_task_outbox_record(
        {"raw": raw, "route": "agent"},
        {"http_status": 200, "response": {"accepted": True}},
    )
    preview = rec["payload_summary"]["title_preview"]
    assert len(preview) <= 40
    assert preview == title_preview_from(long_goal)
    assert long_goal not in json.dumps(rec)


def test_t7_large_gate_body_not_in_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T7: büyük lumos_gate gövdesi outbox'ta kalır; journal'da lumos_http_response yok."""
    big_body = {"lumos_gate": {"detail": "z" * 5000}, "accepted": True, "ok": True}
    raw = json.dumps({"goal": "gate test"}, ensure_ascii=False).encode()
    records = _persist_and_mirror(
        tmp_path,
        {"raw": raw, "route": "agent"},
        {"http_status": 200, "response": big_body},
        monkeypatch=monkeypatch,
    )
    rec = records[0]
    assert "lumos_http_response" not in rec
    assert "lumos_gate" not in json.dumps(rec)
    outbox_ex = json.loads(
        (tmp_path / ".lumos" / "outbox" / "last_execution.json").read_text(encoding="utf-8")
    )
    assert outbox_ex.get("lumos_http_response") is not None


def test_t8_every_journal_line_validates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T8: her journal satırı validate_evidence_record == []."""
    raw = json.dumps({"goal": "validate me"}, ensure_ascii=False).encode()
    records = _persist_and_mirror(
        tmp_path,
        {"raw": raw, "route": "direct"},
        {"http_status": 200, "response": {"accepted": True}},
        monkeypatch=monkeypatch,
    )
    for rec in records:
        assert validate_evidence_record(rec) == []


def test_t9_bridge_enum_values_accepted_by_validator() -> None:
    """T9: yeni enum değerleri frozenset validator'dan geçer."""
    raw = json.dumps({"goal": "enum"}, ensure_ascii=False).encode()
    rec = mirror_post_task_outbox_record(
        {"raw": raw, "route": "agent"},
        {"http_status": 200, "response": {"accepted": True}},
    )
    assert rec["source"] == SOURCE_KANDO_BRIDGE
    assert rec["store"] == STORE_BRIDGE_OUTBOX
    assert rec["operation"] == OPERATION_BRIDGE_TASK_POST
    assert validate_evidence_record(rec) == []
