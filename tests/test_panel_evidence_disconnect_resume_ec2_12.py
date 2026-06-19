"""EC2-12: disconnect/resume integration harness — DR1–DR7 (panel.astro ile hizalı)."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TESTS = Path(__file__).resolve().parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_PANEL_TASK_COMPLETE,
    OPERATION_PANEL_TASK_CREATE,
    OPERATION_PANEL_TASK_DELETE,
    OPERATION_PANEL_TASK_RESTORE,
    PHASE_AFTER,
    PHASE_BEFORE,
    SOURCE_PANEL_TASKS_SERVER,
    STORE_PANEL_TASKS,
    evidence_continuity_path,
    title_preview_from,
    validate_evidence_record,
)

from test_panel_evidence_queue_ec2_02 import (  # noqa: E402
    PANEL_EVIDENCE_FLUSH_MAX_ATTEMPTS,
    enqueue_evidence_pending_op,
    find_task_by_title_in_doc,
    flush_create_op,
    _load_panel_tasks_server,
    _sanitize_evidence_queue_ref,
    _simulate_post_tasks_create,
)


@dataclass
class FlushApiResult:
    ok: bool
    status: int
    data: dict


def is_evidence_flush_idempotent_success(res: FlushApiResult | None, op: str) -> bool:
    """panel.astro isEvidenceFlushIdempotentSuccess Python aynası."""
    if not res:
        return False
    if res.ok and res.data.get("ok"):
        return True
    err = str(res.data.get("error") or "")
    if res.status == 404 and err == "not_found":
        return True
    if op == "complete" and res.status == 409 and err == "already_done":
        return True
    return False


def _journal_records(base: Path) -> list[dict]:
    p = evidence_continuity_path(base)
    if not p.is_file():
        return []
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _records_for_operation(records: list[dict], operation: str) -> list[dict]:
    return [r for r in records if r.get("operation") == operation]


def _assert_journal_pair_valid(records: list[dict], operation: str, *, entity_id: str | None = None) -> None:
    op_recs = _records_for_operation(records, operation)
    assert len(op_recs) >= 2, f"expected before+after for {operation}, got {len(op_recs)}"
    pair = op_recs[-2:]
    for rec in pair:
        assert validate_evidence_record(rec) == []
        assert rec["source"] == SOURCE_PANEL_TASKS_SERVER
        assert rec["store"] == STORE_PANEL_TASKS
        assert rec["operation"] == operation
    assert {r["phase"] for r in pair} == {PHASE_BEFORE, PHASE_AFTER}
    if entity_id is not None:
        after = next(r for r in pair if r["phase"] == PHASE_AFTER)
        assert after.get("entity_ref", {}).get("id") == entity_id


def simulate_post_tasks_complete(ref: str, doc: dict | None = None) -> tuple[FlushApiResult, str | None]:
    """POST /tasks/complete persist yolu — panel_tasks_server._post_complete ile hizalı."""
    pts = _load_panel_tasks_server()
    if doc is None:
        doc = pts._read_doc()
    rtrim = pts._normalize_ws(ref)
    t = pts._find_task_by_ref(doc, rtrim)
    if not t:
        return FlushApiResult(False, 404, {"ok": False, "error": "not_found"}), None
    tid = str(t.get("id") or "")
    if t.get("status") == "done":
        return FlushApiResult(False, 409, {"ok": False, "error": "already_done"}), tid
    now = pts._now_iso()
    t["status"] = "done"
    t["completedAt"] = now
    title = str(t.get("title") or "")
    ev = {
        "id": pts._new_event_id(),
        "type": "task_completed",
        "taskId": tid,
        "text": title,
        "ts": now,
    }
    doc.setdefault("events", []).append(ev)
    pts._write_doc(
        doc,
        evidence={
            "operation": OPERATION_PANEL_TASK_COMPLETE,
            "mutation": "complete",
            "entity_id": tid,
            "route": "POST /tasks/complete",
            "title_preview": title_preview_from(title),
            "events_appended": 1,
        },
    )
    return FlushApiResult(True, 200, {"ok": True, "task": t}), tid


def simulate_post_tasks_delete(
    *,
    ref: str = "",
    id_key: str = "",
    doc: dict | None = None,
) -> tuple[FlushApiResult, str | None]:
    """POST /tasks/delete persist yolu — panel_tasks_server._post_delete ile hizalı."""
    pts = _load_panel_tasks_server()
    if doc is None:
        doc = pts._read_doc()
    id_key = pts._normalize_ws(id_key)
    ref_key = pts._normalize_ws(ref)
    tasks = doc.get("tasks") if isinstance(doc.get("tasks"), list) else []
    hit = None
    idx = -1
    if id_key:
        for i, t in enumerate(tasks):
            if isinstance(t, dict) and str(t.get("id", "")) == id_key:
                hit = t
                idx = i
                break
    if hit is None and ref_key:
        hit = pts._find_task_by_ref(doc, ref_key)
        if hit is not None:
            for i, t in enumerate(tasks):
                if t is hit:
                    idx = i
                    break
    if hit is None or idx < 0:
        return FlushApiResult(False, 404, {"ok": False, "error": "not_found"}), None
    tid = str(hit.get("id", "")).strip()
    if not tid:
        return FlushApiResult(False, 404, {"ok": False, "error": "not_found"}), None
    title = str(hit.get("title") or "")
    now = pts._now_iso()
    payload = copy.deepcopy(hit)
    pts._write_trash_task_file(tid, payload, now)
    del tasks[idx]
    ev = {
        "id": pts._new_event_id(),
        "type": "task_deleted",
        "taskId": tid,
        "text": title,
        "ts": now,
    }
    doc.setdefault("events", []).append(ev)
    pts._write_doc(
        doc,
        evidence={
            "operation": OPERATION_PANEL_TASK_DELETE,
            "mutation": "delete",
            "entity_id": tid,
            "route": "POST /tasks/delete",
            "title_preview": title_preview_from(title),
            "events_appended": 1,
            "trash_written": True,
        },
    )
    return FlushApiResult(True, 200, {"ok": True}), tid


def simulate_post_tasks_restore(tid: str) -> tuple[FlushApiResult, str | None]:
    """POST /tasks/restore persist yolu — panel_tasks_server._post_restore ile hizalı."""
    pts = _load_panel_tasks_server()
    rid = pts._normalize_ws(tid)
    if not rid:
        return FlushApiResult(False, 400, {"ok": False, "error": "empty_id"}), None
    tpath = pts._find_trash_json_for_task_id(rid)
    if tpath is None or not tpath.is_file():
        return FlushApiResult(False, 404, {"ok": False, "error": "missing_trash_file"}), rid
    record = json.loads(tpath.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        return FlushApiResult(False, 400, {"ok": False, "error": "invalid_trash_file"}), rid
    task = pts._task_from_trash_record(record)
    if not task or not str(task.get("id", "")).strip():
        return FlushApiResult(False, 400, {"ok": False, "error": "invalid_payload"}), rid
    doc = pts._read_doc()
    tasks = doc.setdefault("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
        doc["tasks"] = tasks
    for existing in tasks:
        if isinstance(existing, dict) and str(existing.get("id", "")).strip() == rid:
            return FlushApiResult(False, 409, {"ok": False, "error": "task_already_exists"}), rid
    title = str(task.get("title") or "")
    now = pts._now_iso()
    tasks.append(task)
    ev = {
        "id": pts._new_event_id(),
        "type": "task_restored",
        "taskId": rid,
        "text": title,
        "ts": now,
    }
    doc.setdefault("events", []).append(ev)
    pts._write_doc(
        doc,
        evidence={
            "operation": OPERATION_PANEL_TASK_RESTORE,
            "mutation": "restore",
            "entity_id": rid,
            "route": "POST /tasks/restore",
            "title_preview": title_preview_from(title),
            "events_appended": 1,
        },
    )
    tpath.unlink()
    return FlushApiResult(True, 200, {"ok": True, "task": task}), rid


def replay_evidence_pending_op(
    item: dict,
    tasks_doc: dict | None = None,
    *,
    network_fail: bool = False,
) -> dict:
    """panel.astro replayEvidencePendingOp Python aynası (HTTP yerine doğrudan persist)."""
    if network_fail:
        return {"outcome": "fail", "network": True}
    op = str(item.get("op") or "")
    ref = _sanitize_evidence_queue_ref(item.get("ref"))
    if not ref:
        return {"outcome": "skip"}

    if op == "create":
        doc = tasks_doc
        pts = _load_panel_tasks_server()
        if doc is None:
            doc = pts._read_doc()
        if find_task_by_title_in_doc(doc, ref):
            return {"outcome": "success", "deduped": True}
        tid, _deduped = flush_create_op(item, doc)
        return {"outcome": "success", "tid": tid}

    if op == "complete":
        res, tid = simulate_post_tasks_complete(ref)
        if is_evidence_flush_idempotent_success(res, op):
            return {"outcome": "success", "res": res, "tid": tid}
        return {"outcome": "fail", "res": res, "network": False}

    if op == "delete":
        ref_kind = str(item.get("ref_kind") or "id")
        if ref_kind == "id":
            res, tid = simulate_post_tasks_delete(id_key=ref)
        else:
            res, tid = simulate_post_tasks_delete(ref=ref)
        if is_evidence_flush_idempotent_success(res, op):
            return {"outcome": "success", "res": res, "tid": tid}
        return {"outcome": "fail", "res": res, "network": False}

    if op == "restore":
        res, tid = simulate_post_tasks_restore(ref)
        if is_evidence_flush_idempotent_success(res, op):
            return {"outcome": "success", "res": res, "tid": tid}
        return {"outcome": "fail", "res": res, "network": False}

    return {"outcome": "skip"}


def flush_pending_evidence_ops(
    queue: list[dict],
    *,
    network_fail_for_op: str | None = None,
) -> tuple[list[dict], bool]:
    """panel.astro flushPendingEvidenceOps Python aynası (retry/backoff hariç — anında flush)."""
    if not queue:
        return queue, True

    tasks_doc = None
    stopped_on_network = False
    i = 0
    while i < len(queue):
        if stopped_on_network:
            break
        item = queue[i]
        if not item:
            i += 1
            continue
        if int(item.get("attempts") or 0) >= PANEL_EVIDENCE_FLUSH_MAX_ATTEMPTS:
            i += 1
            continue

        network_fail = network_fail_for_op is not None and str(item.get("op")) == network_fail_for_op
        result = replay_evidence_pending_op(item, tasks_doc, network_fail=network_fail)
        if result["outcome"] == "success":
            queue.pop(i)
            if item.get("op") == "create":
                tasks_doc = _load_panel_tasks_server()._read_doc()
            continue
        if result["outcome"] == "fail":
            item["attempts"] = int(item.get("attempts") or 0) + 1
            item["last_attempt_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
                "+00:00", "Z"
            )
            if result.get("network"):
                stopped_on_network = True
            i += 1
            continue
        i += 1

    return queue, not stopped_on_network


def engine_task_to_panel_row(t: dict) -> dict | None:
    """panel.astro engineTaskToPanelRow Python aynası."""
    if not isinstance(t, dict):
        return None
    title = str(t.get("title") or "").strip()
    if not title:
        return None
    st = str(t.get("status") or "active")
    status = "tamamlandi" if st == "done" else "bekliyor"
    row: dict = {"title": title, "priority": "orta", "status": status}
    tid = str(t.get("id") or "").strip()
    if tid:
        row["id"] = tid
    when = t.get("completedAt") or t.get("createdAt")
    if when:
        row["when"] = str(when)
    return row


def merge_panel_gorevler_meta_from_previous(prev_rows: list[dict], next_rows: list[dict]) -> None:
    """panel.astro mergePanelGorevlerMetaFromPrevious Python aynası (in-place)."""
    by_id: dict[str, dict] = {}
    by_title: dict[str, dict] = {}
    for r in prev_rows:
        if not r:
            continue
        if r.get("id"):
            by_id[str(r["id"])] = r
        if r.get("title"):
            by_title[str(r["title"]).strip().lower()] = r
    for r in next_rows:
        old = None
        if r.get("id"):
            old = by_id.get(str(r["id"]))
        if old is None and r.get("title"):
            old = by_title.get(str(r["title"]).strip().lower())
        if not old:
            continue
        if old.get("priority") in ("dusuk", "orta", "yuksek"):
            r["priority"] = old["priority"]
        if old.get("status") == "onay_bekliyor" and r.get("status") == "bekliyor":
            r["status"] = "onay_bekliyor"
        if old.get("bridgeLast"):
            r["bridgeLast"] = copy.deepcopy(old["bridgeLast"])
        if old.get("taskPlan"):
            r["taskPlan"] = copy.deepcopy(old["taskPlan"])


def _refresh_panel_rows_from_tasks_doc(doc: dict) -> list[dict]:
    rows: list[dict] = []
    for t in doc.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if str(t.get("status") or "") == "deleted":
            continue
        row = engine_task_to_panel_row(t)
        if row:
            rows.append(row)
    return rows


# --- DR1–DR7 ---


def test_dr1_server_create_offline_complete_enqueue_flush_journal(tmp_path, monkeypatch) -> None:
    """DR1: sunucuda create → offline complete enqueue → flush → panel.task.complete journal."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "DR1 tamamlanacak görev"
    tid = _simulate_post_tasks_create(title)
    journal_before = len(_journal_records(tmp_path))

    queue: list[dict] = []
    enqueue_evidence_pending_op(queue, "complete", tid, "id")
    assert len(queue) == 1
    assert not any(r.get("operation") == OPERATION_PANEL_TASK_COMPLETE for r in _journal_records(tmp_path))

    queue, finished = flush_pending_evidence_ops(queue)
    assert finished is True
    assert queue == []

    records = _journal_records(tmp_path)
    assert len(records) > journal_before
    _assert_journal_pair_valid(records, OPERATION_PANEL_TASK_COMPLETE, entity_id=tid)

    doc = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    task = next(t for t in doc["tasks"] if t.get("id") == tid)
    assert task.get("status") == "done"


def test_dr2_offline_delete_enqueue_flush_journal_and_trash(tmp_path, monkeypatch) -> None:
    """DR2: offline delete enqueue → flush → panel.task.delete + trash."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "DR2 silinecek görev"
    tid = _simulate_post_tasks_create(title)

    queue: list[dict] = []
    enqueue_evidence_pending_op(queue, "delete", title, "title")
    assert len(queue) == 1

    queue, finished = flush_pending_evidence_ops(queue)
    assert finished is True
    assert queue == []

    records = _journal_records(tmp_path)
    _assert_journal_pair_valid(records, OPERATION_PANEL_TASK_DELETE, entity_id=tid)
    delete_after = next(
        r for r in _records_for_operation(records, OPERATION_PANEL_TASK_DELETE) if r["phase"] == PHASE_AFTER
    )
    assert delete_after.get("payload_summary", {}).get("trash_written") is True

    pts = _load_panel_tasks_server()
    assert pts._find_trash_json_for_task_id(tid) is not None
    doc = pts._read_doc()
    assert not any(t.get("id") == tid for t in doc.get("tasks", []))


def test_dr3_offline_restore_enqueue_flush_journal(tmp_path, monkeypatch) -> None:
    """DR3: offline restore enqueue → flush → panel.task.restore journal."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "DR3 geri yüklenecek"
    tid = _simulate_post_tasks_create(title)
    simulate_post_tasks_delete(id_key=tid)

    queue: list[dict] = []
    enqueue_evidence_pending_op(queue, "restore", tid, "id")
    assert len(queue) == 1

    queue, finished = flush_pending_evidence_ops(queue)
    assert finished is True
    assert queue == []

    records = _journal_records(tmp_path)
    _assert_journal_pair_valid(records, OPERATION_PANEL_TASK_RESTORE, entity_id=tid)

    doc = _load_panel_tasks_server()._read_doc()
    restored = next((t for t in doc.get("tasks", []) if t.get("id") == tid), None)
    assert restored is not None
    assert restored.get("status") == "active"
    assert _load_panel_tasks_server()._find_trash_json_for_task_id(tid) is None


def test_dr4_multi_op_fifo_partial_flush_on_network_fail(tmp_path, monkeypatch) -> None:
    """DR4: create+complete FIFO; 2. op ağ fail → 1. flushed, 2. kuyrukta attempts=1."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "DR4 kısmi flush"

    queue: list[dict] = []
    enqueue_evidence_pending_op(queue, "create", title, "title")
    enqueue_evidence_pending_op(queue, "complete", title, "title")
    assert len(queue) == 2

    queue, finished = flush_pending_evidence_ops(queue, network_fail_for_op="complete")
    assert finished is False
    assert len(queue) == 1
    assert queue[0]["op"] == "complete"
    assert queue[0]["attempts"] == 1
    assert queue[0]["last_attempt_at"] is not None

    doc = _load_panel_tasks_server()._read_doc()
    assert find_task_by_title_in_doc(doc, title) is not None
    task = find_task_by_title_in_doc(doc, title)
    assert task is not None
    assert task.get("status") == "active"

    records = _journal_records(tmp_path)
    assert _records_for_operation(records, OPERATION_PANEL_TASK_CREATE)


def test_dr5_duplicate_idempotent_flush_already_done_and_not_found(tmp_path, monkeypatch) -> None:
    """DR5: idempotent flush — already_done ve not_found kuyruğu temizler."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "DR5 idempotent"
    tid = _simulate_post_tasks_create(title)

    simulate_post_tasks_complete(tid)
    complete_count_before = len(_records_for_operation(_journal_records(tmp_path), OPERATION_PANEL_TASK_COMPLETE))

    queue: list[dict] = []
    enqueue_evidence_pending_op(queue, "complete", tid, "id")
    queue, _ = flush_pending_evidence_ops(queue)
    assert queue == []

    complete_count_after = len(_records_for_operation(_journal_records(tmp_path), OPERATION_PANEL_TASK_COMPLETE))
    assert complete_count_after == complete_count_before

    queue = []
    enqueue_evidence_pending_op(queue, "complete", "tsk_nonexistent_9999", "id")
    queue, _ = flush_pending_evidence_ops(queue)
    assert queue == []


def test_dr6_ec2_01_tsk_id_offline_complete_flush(tmp_path, monkeypatch) -> None:
    """DR6: EC2-01 tsk_* id + offline complete + flush."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "DR6 id hedefli complete"
    tid = _simulate_post_tasks_create(title)
    assert tid.startswith("tsk_")

    queue: list[dict] = []
    item = enqueue_evidence_pending_op(queue, "complete", tid, "id")
    assert item["ref_kind"] == "id"
    assert item["ref"] == tid

    queue, finished = flush_pending_evidence_ops(queue)
    assert finished is True
    assert queue == []

    records = _journal_records(tmp_path)
    _assert_journal_pair_valid(records, OPERATION_PANEL_TASK_COMPLETE, entity_id=tid)


def test_dr7_meta_overlay_preserved_after_flush_refresh(tmp_path, monkeypatch) -> None:
    """DR7: flush sonrası refresh + merge — taskPlan/bridgeLast korunur."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "DR7 meta overlay"
    tid = _simulate_post_tasks_create(title)

    prev_rows = [
        {
            "id": tid,
            "title": title,
            "priority": "yuksek",
            "status": "bekliyor",
            "when": "Yarın 14:00",
            "taskPlan": {
                "tur": "Rapor",
                "risk": "Orta",
                "onerilenAlan": "Görevler",
                "sonrakiAdim": "Taslak",
            },
            "bridgeLast": {"lastBridgeAt": "2026-06-19T10:00:00.000Z", "route": "POST /tasks"},
        }
    ]

    queue: list[dict] = []
    enqueue_evidence_pending_op(queue, "complete", tid, "id")
    queue, finished = flush_pending_evidence_ops(queue)
    assert finished is True
    assert queue == []

    doc = _load_panel_tasks_server()._read_doc()
    next_rows = _refresh_panel_rows_from_tasks_doc(doc)
    merge_panel_gorevler_meta_from_previous(prev_rows, next_rows)

    merged = next(r for r in next_rows if r.get("id") == tid)
    assert merged["priority"] == "yuksek"
    assert merged["status"] == "tamamlandi"
    assert merged.get("taskPlan", {}).get("tur") == "Rapor"
    assert merged.get("bridgeLast", {}).get("route") == "POST /tasks"

    records = _journal_records(tmp_path)
    for rec in records:
        assert "taskPlan" not in json.dumps(rec)
        assert "bridgeLast" not in json.dumps(rec)
