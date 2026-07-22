"""EC2-02: panel evidence pending-op kuyruğu — enqueue + flush (panel.astro ile hizalı)."""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

from tests.test_panel_component_split import read_panel_source

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_PANEL_TASK_CREATE,
    PHASE_AFTER,
    PHASE_BEFORE,
    SOURCE_PANEL_TASKS_SERVER,
    STORE_PANEL_TASKS,
    evidence_continuity_path,
    validate_evidence_record,
)

PANEL_EVIDENCE_PENDING_OPS_LS_KEY = "lumos_panel_evidence_pending_ops_v1"
PANEL_EVIDENCE_QUEUE_MAX = 64
PANEL_EVIDENCE_FLUSH_MAX_ATTEMPTS = 5


def _sanitize_evidence_queue_ref(ref: str) -> str:
    s = str(ref or "").strip()
    if not s:
        return ""
    return s[:200] if len(s) > 200 else s


def _evidence_op_pair_key(op: str, ref: str) -> str:
    return f"{op}\0{_sanitize_evidence_queue_ref(ref)}"


def enqueue_evidence_pending_op(
    queue: list[dict],
    op: str,
    ref: str,
    ref_kind: str = "id",
) -> dict:
    """panel.astro enqueueEvidencePendingOp Python aynası."""
    r = _sanitize_evidence_queue_ref(ref)
    if not r or op not in ("create", "complete", "delete", "restore"):
        raise ValueError("invalid enqueue")
    rk = "title" if ref_kind == "title" else "id"
    pair = _evidence_op_pair_key(op, r)
    kept = [x for x in queue if _evidence_op_pair_key(x["op"], x["ref"]) != pair]
    queue.clear()
    queue.extend(kept)
    item = {
        "v": 1,
        "op_id": str(uuid.uuid4()),
        "op": op,
        "ref": r,
        "ref_kind": rk,
        "enqueued_at": "2026-06-19T16:00:00.000Z",
        "attempts": 0,
        "last_attempt_at": None,
    }
    queue.append(item)
    while len(queue) > PANEL_EVIDENCE_QUEUE_MAX:
        queue.pop(0)
    return item


def find_task_by_title_in_doc(doc: dict, title: str) -> dict | None:
    tt = str(title or "").strip().casefold()
    if not tt:
        return None
    for t in doc.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if str(t.get("status") or "") == "deleted":
            continue
        if str(t.get("title") or "").strip().casefold() == tt:
            return t
    return None


def _load_panel_tasks_server():
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    return pts


def _simulate_post_tasks_create(title: str) -> str:
    pts = _load_panel_tasks_server()
    doc = pts._read_doc()
    now = pts._now_iso()
    tid = pts._new_task_id()
    task = {
        "id": tid,
        "title": title,
        "status": "active",
        "createdAt": now,
        "completedAt": None,
    }
    ev = {
        "id": pts._new_event_id(),
        "type": "task_created",
        "taskId": tid,
        "text": title,
        "ts": now,
    }
    doc.setdefault("tasks", []).append(task)
    doc.setdefault("events", []).append(ev)
    pts._write_doc(
        doc,
        evidence={
            "operation": OPERATION_PANEL_TASK_CREATE,
            "mutation": "create",
            "entity_id": tid,
            "route": "POST /tasks",
            "title_preview": title[:40],
            "events_appended": 1,
        },
    )
    return tid


def flush_create_op(item: dict, doc: dict | None = None) -> tuple[str, bool]:
    """Flush tek create öğesi — title dedup + POST /tasks persist yolu."""
    pts = _load_panel_tasks_server()
    ref = _sanitize_evidence_queue_ref(item["ref"])
    if doc is None:
        doc = pts._read_doc()
    existing = find_task_by_title_in_doc(doc, ref)
    if existing:
        return str(existing.get("id") or ""), True
    tid = _simulate_post_tasks_create(ref)
    return tid, False


def _panel_astro_has_evidence_queue() -> bool:
    text = read_panel_source()
    required = [
        PANEL_EVIDENCE_PENDING_OPS_LS_KEY,
        "enqueueEvidencePendingOp",
        "flushPendingEvidenceOps",
        "wireEvidenceQueueFlushTriggers",
    ]
    return all(token in text for token in required)


def test_panel_astro_evidence_queue_symbols() -> None:
    assert _panel_astro_has_evidence_queue()


def test_offline_enqueue_create_queue_item_no_journal(tmp_path, monkeypatch) -> None:
    """Offline create → kuyrukta create öğesi; sunucu/journal yok."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    queue: list[dict] = []
    title = "Alışveriş listesi"
    item = enqueue_evidence_pending_op(queue, "create", title, "title")
    assert item["op"] == "create"
    assert item["ref"] == title
    assert item["ref_kind"] == "title"
    assert item["v"] == 1
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        item["op_id"],
    )
    stored = {PANEL_EVIDENCE_PENDING_OPS_LS_KEY: json.dumps([item])}
    assert len(stored[PANEL_EVIDENCE_PENDING_OPS_LS_KEY]) > 0
    assert "token" not in stored[PANEL_EVIDENCE_PENDING_OPS_LS_KEY]
    assert not evidence_continuity_path(tmp_path).exists()


def test_flush_replays_post_tasks_tsk_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "EC2-02 flush görev"
    item = {"op": "create", "ref": title}
    tid, deduped = flush_create_op(item)
    assert not deduped
    assert tid.startswith("tsk_")

    tasks_path = tmp_path / "tasks.json"
    doc = json.loads(tasks_path.read_text(encoding="utf-8"))
    assert any(t.get("id") == tid and t.get("title") == title for t in doc.get("tasks", []))

    journal = evidence_continuity_path(tmp_path)
    assert journal.is_file()
    lines = journal.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    for rec in records:
        assert validate_evidence_record(rec) == []
    assert {r["phase"] for r in records} == {PHASE_BEFORE, PHASE_AFTER}
    assert records[0]["source"] == SOURCE_PANEL_TASKS_SERVER
    assert records[0]["store"] == STORE_PANEL_TASKS
    assert records[0]["operation"] == OPERATION_PANEL_TASK_CREATE
    after = next(r for r in records if r["phase"] == PHASE_AFTER)
    assert after.get("entity_ref", {}).get("id") == tid


def test_flush_create_dedup_existing_title_skips_post(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "Mevcut başlık"
    existing_id = _simulate_post_tasks_create(title)
    journal_before = evidence_continuity_path(tmp_path).read_text(encoding="utf-8")

    pts = _load_panel_tasks_server()
    doc = pts._read_doc()
    item = {"op": "create", "ref": title}
    tid, deduped = flush_create_op(item, doc)
    assert deduped is True
    assert tid == existing_id

    journal_after = evidence_continuity_path(tmp_path).read_text(encoding="utf-8")
    assert journal_after == journal_before


def test_enqueue_dedup_same_op_ref_replaces_pending() -> None:
    queue: list[dict] = []
    enqueue_evidence_pending_op(queue, "complete", "tsk_abc", "id")
    enqueue_evidence_pending_op(queue, "complete", "tsk_abc", "id")
    assert len(queue) == 1
    assert queue[0]["op"] == "complete"
    assert queue[0]["ref"] == "tsk_abc"


def test_offline_complete_enqueue_ref_kind_id() -> None:
    queue: list[dict] = []
    item = enqueue_evidence_pending_op(queue, "complete", "tsk_xyz", "id")
    assert item["op"] == "complete"
    assert item["ref_kind"] == "id"
