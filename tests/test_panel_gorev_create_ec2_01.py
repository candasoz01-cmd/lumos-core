"""EC2-01: panel chat görev oluştur — parse + POST /tasks persist (panel.astro ile hizalı)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

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


def _normalize_user_task_message(s: str) -> str:
    out = str(s or "")
    out = re.sub(r"\bgorev\b", "görev", out, flags=re.I)
    out = re.sub(r"\bolustur\b", "oluştur", out, flags=re.I)
    out = re.sub(r"\byarain\b", "yarın", out, flags=re.I)
    out = re.sub(r"\byarin\b", "yarın", out, flags=re.I)
    out = re.sub(r"\bsaar\b", "saat", out, flags=re.I)
    out = re.sub(r"\bbugun\b", "bugün", out, flags=re.I)
    return out


def _pad2(n: str | int) -> str:
    x = str(int(n))
    return x if len(x) >= 2 else "0" + x


def _canonicalize_task_input(raw: str) -> str:
    s = str(raw or "").replace("\u00a0", " ").strip()
    s = _normalize_user_task_message(s)
    return s.lower().strip()


def _parse_olustur_rest(rest_raw: str) -> dict[str, str | None]:
    rest = _normalize_user_task_message(str(rest_raw or "").strip())
    if not rest:
        return {"title": "", "whenSummary": None}
    parts: list[str] = []
    if re.search(r"\byarın\b", rest, re.I):
        parts.append("Yarın")
    elif re.search(r"\bbugün\b", rest, re.I):
        parts.append("Bugün")
    tm = re.search(r"\bsaat\s*(\d{1,2})(?:\s*[:.]\s*(\d{2}))?\b", rest, re.I)
    if tm:
        parts.append(
            f"{_pad2(tm.group(1))}:{tm.group(2)}"
            if tm.group(2) is not None
            else f"{_pad2(tm.group(1))}:00"
        )
    title_work = rest
    title_work = re.sub(r"\byarın\b", " ", title_work, flags=re.I)
    title_work = re.sub(r"\bbugün\b", " ", title_work, flags=re.I)
    title_work = re.sub(r"\bsaat\s*\d{1,2}(?:\s*[:.]\s*\d{2})?\b", " ", title_work, flags=re.I)
    title_work = re.sub(r"\s+", " ", title_work).strip()
    if not title_work:
        title_work = _normalize_user_task_message(str(rest_raw or "").strip())
    when_summary = " ".join(parts) if parts else None
    return {"title": title_work, "whenSummary": when_summary}


def _parse_schedule_prefix(prefix_raw: str) -> dict[str, str | None]:
    prefix = _normalize_user_task_message(str(prefix_raw or "").strip())
    if not prefix:
        return {"whenSummary": None}
    pl = prefix.lower()
    parts: list[str] = []
    if re.search(r"\byarın\b|\byarain\b|\byarin\b", pl, re.I):
        parts.append("Yarın")
    elif re.search(r"\bbugün\b|\bbugun\b", pl, re.I):
        parts.append("Bugün")
    tm = re.search(r"(?:saat\s*)?(\d{1,2})(?:\s*[:.]\s*(\d{2}))?\b", pl)
    if tm:
        parts.append(
            f"{_pad2(tm.group(1))}:{tm.group(2)}"
            if tm.group(2) is not None
            else f"{_pad2(tm.group(1))}:00"
        )
    when_summary = " ".join(parts) if parts else prefix
    return {"whenSummary": when_summary}


def parse_panel_gorev_komutu(raw: str) -> dict | None:
    """panel.astro parsePanelGorevKomutu Python aynası."""
    s0 = str(raw or "").strip()
    if not s0:
        return None
    s = _canonicalize_task_input(s0)

    m = re.match(r"^(?:görev|gorev)\s+sil(?=\s|:|$)", s, re.I)
    if m:
        ref = re.sub(r"^\s*:+\s*", "", s[m.end() :]).strip()
        return {"verb": "sil", "ref": ref}

    m = re.match(r"^\s*mini\s+görev\s+ekle\s+(.+)$", s, re.I)
    if m:
        title = m.group(1).strip()
        return {"title": title, "whenSummary": None, "replyKind": "mini"} if title else None

    m = re.match(r"^\s*görev\s+oluştur\s+(.+)$", s, re.I)
    if m:
        parsed = _parse_olustur_rest(m.group(1))
        return (
            {"title": parsed["title"], "whenSummary": parsed["whenSummary"]}
            if parsed["title"]
            else None
        )

    m = re.match(r"^\s*(?:([\s\S]*?)\s+)?görev\s+ekle\s+(.+)$", s, re.I)
    if not m:
        return None
    pre = (m.group(1) or "").strip()
    title = (m.group(2) or "").strip()
    if not title:
        return None
    when = _parse_schedule_prefix(pre)
    return {"title": title, "whenSummary": when["whenSummary"]}


def _simulate_post_tasks_create(title: str) -> str:
    """panel_tasks_server._post_create ile aynı persist yolu (chat → POST /tasks)."""
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

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


def test_parse_panel_gorev_komutu_olustur() -> None:
    assert parse_panel_gorev_komutu("görev oluştur alışveriş") == {
        "title": "alışveriş",
        "whenSummary": None,
    }
    assert parse_panel_gorev_komutu("gorev olustur yarın saat 14 rapor") == {
        "title": "rapor",
        "whenSummary": "Yarın 14:00",
    }


def test_parse_panel_gorev_komutu_mini_and_prefix() -> None:
    assert parse_panel_gorev_komutu("mini görev ekle tiss") == {
        "title": "tiss",
        "whenSummary": None,
        "replyKind": "mini",
    }
    assert parse_panel_gorev_komutu("yarın saat 14:00 görev ekle rapor") == {
        "title": "rapor",
        "whenSummary": "Yarın 14:00",
    }


def test_parse_panel_gorev_komutu_sil_unchanged() -> None:
    assert parse_panel_gorev_komutu("görev sil alışveriş") == {"verb": "sil", "ref": "alışveriş"}


def test_chat_create_post_tasks_persists_tsk_id_and_journal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    title = "Alışveriş listesi"
    tid = _simulate_post_tasks_create(title)
    assert tid.startswith("tsk_")

    tasks_path = tmp_path / "tasks.json"
    assert tasks_path.is_file()
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
