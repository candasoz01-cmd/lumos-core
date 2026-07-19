"""KA-001 ikinci dilim: Board projeksiyonu — kaynak güvenliği, maskeleme, sinyaller.

Sözleşme davranışı (doğrulama, legacy normalize, çakışma semantiği)
`tests/test_agent_status_contract.py` içinde test edilir; burada yalnız
projeksiyon katmanının kendi sorumlulukları test edilir.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.agent_status_contract import LEGACY_AGENT_ID, SCHEMA_VERSION  # noqa: E402
from lumos_board.agent_status import (  # noqa: E402
    MAX_STATUS_FILE_BYTES,
    AgentState,
    read_agent_status_projection,
)

_NOW = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)


def _write_legacy(directory: Path, job_id: str, *, status: str = "running", task: str | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    payload: dict = {"job_id": job_id, "phase": "plan", "status": status, "errors": []}
    if task is not None:
        payload["final_report"] = {"task": task, "status": "ok"}
    path = directory / f"agent_status_{job_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_v1(
    directory: Path,
    job_id: str,
    *,
    agent_id: str,
    owner: str,
    status: str = "running",
    started_at: str | None = "2026-07-19T11:00:00+00:00",
    updated_at: str | None = "2026-07-19T11:59:00+00:00",
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SCHEMA_VERSION,
        "agent_id": agent_id,
        "job_id": job_id,
        "status": status,
        "owner": owner,
        "started_at": started_at,
        "updated_at": updated_at,
        "evidence_ref": f"outbox/agent_status_{job_id}.json",
    }
    path = directory / f"agent_status_{job_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_legacy_record_is_projected_via_canonical_contract(tmp_path: Path) -> None:
    _write_legacy(tmp_path / "kando", "abc1", task="api_key=sk-verysecret123 ile mail kur")
    projection = read_agent_status_projection({"kando": tmp_path / "kando"}, now=_NOW)
    assert projection.invalid_records == 0
    assert len(projection.records) == 1
    projected = projection.records[0]
    assert projected.record.agent_id == LEGACY_AGENT_ID
    assert projected.record.version == SCHEMA_VERSION
    assert projected.state is AgentState.WORKING
    assert projected.source == "kando"
    assert "sk-verysecret123" not in projected.task_title
    assert "[redacted]" in projected.task_title
    assert projected.display_ref == "kando/agent_status_abc1.json"
    assert str(tmp_path) not in projected.display_ref


def test_projection_combines_explicit_sources_without_discovery(tmp_path: Path) -> None:
    _write_legacy(tmp_path / "kando", "j1")
    _write_v1(tmp_path / "claude", "j2", agent_id="claude.code", owner="claude.code")
    _write_legacy(tmp_path / "unregistered", "j3")
    projection = read_agent_status_projection(
        {"kando": tmp_path / "kando", "claude": tmp_path / "claude"}, now=_NOW
    )
    assert projection.sources_scanned == 2
    assert {p.source for p in projection.records} == {"kando", "claude"}
    assert all(p.record.job_id != "j3" for p in projection.records)


def test_skips_malformed_oversized_and_symlink_records(tmp_path: Path) -> None:
    source = tmp_path / "kando"
    good = _write_legacy(source, "good")
    (source / "agent_status_bad.json").write_text("{not json", encoding="utf-8")
    (source / "agent_status_big.json").write_text(
        json.dumps({"job_id": "big", "status": "running", "pad": "x" * MAX_STATUS_FILE_BYTES}),
        encoding="utf-8",
    )
    (source / "agent_status_link.json").symlink_to(good)
    projection = read_agent_status_projection({"kando": source}, now=_NOW)
    assert [p.record.job_id for p in projection.records] == ["good"]
    assert projection.invalid_records == 3
    assert projection.read_errors == ("kando/agent_status_bad.json",)


def test_newest_identity_wins_stale_and_truncation_signaled(tmp_path: Path) -> None:
    source = tmp_path / "claude"
    _write_v1(source, "old1", agent_id="claude.code", owner="claude.code", started_at="2026-07-19T08:00:00+00:00", updated_at="2026-07-19T10:00:00+00:00")
    _write_v1(source, "new1", agent_id="claude.code", owner="claude.code", started_at="2026-07-19T08:00:00+00:00", updated_at="2026-07-19T11:59:30+00:00")
    _write_v1(source, "other", agent_id="codex.cli", owner="codex.cli", started_at="2026-07-19T08:00:00+00:00", updated_at="2026-07-19T09:00:00+00:00")
    projection = read_agent_status_projection({"claude": source}, limit=1, stale_after_seconds=120.0, now=_NOW)
    assert projection.truncated is True
    assert len(projection.records) == 1
    newest = projection.records[0]
    assert newest.record.job_id == "new1"
    assert newest.stale is False


def test_stale_flag_set_after_ttl(tmp_path: Path) -> None:
    source = tmp_path / "codex"
    _write_v1(source, "j1", agent_id="codex.cli", owner="codex.cli", updated_at="2026-07-19T11:00:00+00:00")
    projection = read_agent_status_projection({"codex": source}, stale_after_seconds=60.0, now=_NOW)
    assert projection.records[0].stale is True


def test_zero_limit_is_valid_and_missing_source_not_created(tmp_path: Path) -> None:
    source = tmp_path / "kando"
    _write_legacy(source, "j1")
    missing = tmp_path / "yok"
    projection = read_agent_status_projection({"kando": source, "yok": missing}, limit=0, now=_NOW)
    assert projection.records == ()
    assert projection.truncated is True
    assert projection.sources_scanned == 1
    assert not missing.exists()


def test_same_job_conflicting_owners_reported_with_sources(tmp_path: Path) -> None:
    _write_v1(tmp_path / "claude", "shared", agent_id="claude.code", owner="claude.code")
    _write_v1(tmp_path / "codex", "shared", agent_id="codex.cli", owner="codex.cli")
    projection = read_agent_status_projection(
        {"claude": tmp_path / "claude", "codex": tmp_path / "codex"}, now=_NOW
    )
    assert len(projection.conflicts) == 1
    conflict = projection.conflicts[0]
    assert conflict.job_id == "shared"
    assert conflict.owners == ("claude.code", "codex.cli")
    assert conflict.sources == ("claude", "codex")
    assert conflict.to_dict()["type"] == "OWNER_CONFLICT"


def test_time_order_violation_rejected_without_dropping_valid(tmp_path: Path) -> None:
    source = tmp_path / "claude"
    _write_v1(source, "bad", agent_id="a1", owner="a1", started_at="2026-07-19T11:30:00+00:00", updated_at="2026-07-19T11:00:00+00:00")
    _write_v1(source, "ok", agent_id="a2", owner="a2")
    projection = read_agent_status_projection({"claude": source}, now=_NOW)
    assert [p.record.job_id for p in projection.records] == ["ok"]
    assert projection.invalid_records == 1


def test_unreadable_record_isolated_from_other_source(tmp_path: Path) -> None:
    bad_source = tmp_path / "bad"
    bad_source.mkdir()
    (bad_source / "agent_status_x.json").write_bytes(b"\xff\xfe\x00garbage")
    _write_legacy(tmp_path / "kando", "good")
    projection = read_agent_status_projection(
        {"bad": bad_source, "kando": tmp_path / "kando"}, now=_NOW
    )
    assert [p.record.job_id for p in projection.records] == ["good"]
    assert projection.read_errors == ("bad/agent_status_x.json",)


def test_unreadable_source_dir_isolated_from_other_source(tmp_path: Path) -> None:
    locked = tmp_path / "locked"
    _write_legacy(locked, "hidden")
    _write_legacy(tmp_path / "kando", "good")
    os.chmod(locked, 0o000)
    try:
        projection = read_agent_status_projection(
            {"locked": locked, "kando": tmp_path / "kando"}, now=_NOW
        )
    finally:
        os.chmod(locked, 0o755)
    assert [p.record.job_id for p in projection.records] == ["good"]
    assert "locked/*" in projection.read_errors


def test_projection_never_writes(tmp_path: Path) -> None:
    source = tmp_path / "kando"
    path = _write_legacy(source, "abc1")
    before = path.read_bytes()
    read_agent_status_projection({"kando": source}, now=_NOW)
    assert path.read_bytes() == before
    assert sorted(p.name for p in source.iterdir()) == ["agent_status_abc1.json"]
