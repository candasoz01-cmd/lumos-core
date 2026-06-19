"""EC2-08: panel evidence correlation API + grouping — U1, U7–U11."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_BRIDGE_TASK_POST,
    OPERATION_GUARD_DECISION,
    OPERATION_PANEL_TASK_CREATE,
    OUTCOME_ERROR,
    OUTCOME_OK,
    PHASE_AFTER,
    PHASE_RESULT,
    SOURCE_GUARD_AUDIT,
    SOURCE_KANDO_BRIDGE,
    SOURCE_PANEL_TASKS_SERVER,
    STORE_BRIDGE_OUTBOX,
    STORE_GUARD,
    STORE_PANEL_TASKS,
    UI_PROJECTION_SCHEMA,
    append_evidence_event,
    build_evidence_record,
    generate_correlation_id,
    project_evidence_for_ui,
)

EVIDENCE_BRIDGE_PAIR_MAX_MS = 60000


def _load_panel_tasks_server():
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    return pts


def _iso_offset(base: datetime, seconds: float) -> str:
    dt = base + timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _parse_evidence_ts_ms(ts: str) -> float:
    raw = str(ts or "").strip()
    if not raw:
        return 0.0
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).timestamp()


def evidence_title_preview_prefix_match(a: str, b: str) -> bool:
    x = str(a or "").strip()
    y = str(b or "").strip()
    if not x or not y:
        return False
    px = x[:20]
    py = y[:20]
    return x.startswith(py) or y.startswith(px) or px == py


def build_evidence_ui_group(primary: dict, kind: str, label: str) -> dict:
    entity_ref = primary.get("entity_ref") if isinstance(primary.get("entity_ref"), dict) else None
    entity_id = str(entity_ref.get("id", "")).strip() if entity_ref else ""
    payload = primary.get("payload_summary") if isinstance(primary.get("payload_summary"), dict) else {}
    title_preview = str(payload.get("title_preview", "")).strip()
    continue_kind = None
    can_continue = False
    if entity_id:
        continue_kind = "task"
        can_continue = True
    elif title_preview and kind != "guard":
        continue_kind = "chat"
        can_continue = True
    elif kind == "guard":
        continue_kind = "info"
        can_continue = False
    return {
        "ts": str(primary.get("ts") or ""),
        "kind": kind,
        "label": label,
        "entityRefId": entity_id or None,
        "titlePreview": title_preview or None,
        "canContinue": can_continue,
        "continueKind": continue_kind,
    }


def group_evidence_events_for_ui(events: list[dict]) -> list[dict]:
    """panel.astro groupEvidenceEventsForUi Python aynası."""
    list_ev = list(events)
    list_ev.sort(key=lambda e: _parse_evidence_ts_ms(str(e.get("ts", ""))), reverse=True)
    used: set[int] = set()
    groups: list[dict] = []
    for i, ev in enumerate(list_ev):
        if i in used:
            continue
        op = str(ev.get("operation") or "")
        phase = str(ev.get("phase") or "")
        source = str(ev.get("source") or "")

        if op == "bridge.task.post" and phase == "result":
            for j in range(i + 1, len(list_ev)):
                if j in used:
                    continue
                cand = list_ev[j]
                if str(cand.get("operation") or "") != "bridge.task.post":
                    continue
                if str(cand.get("phase") or "") != "after":
                    continue
                dt = abs(_parse_evidence_ts_ms(ev.get("ts", "")) - _parse_evidence_ts_ms(cand.get("ts", "")))
                if dt > EVIDENCE_BRIDGE_PAIR_MAX_MS:
                    continue
                tp1 = str((ev.get("payload_summary") or {}).get("title_preview", ""))
                tp2 = str((cand.get("payload_summary") or {}).get("title_preview", ""))
                if tp1 and tp2 and not evidence_title_preview_prefix_match(tp1, tp2):
                    continue
                used.add(j)
                break
            outcome = str(ev.get("outcome") or "ok")
            preview = str((ev.get("payload_summary") or {}).get("title_preview", "")).strip()
            label = f"Köprü: {outcome}" + (f" · {preview}" if preview else "")
            groups.append(build_evidence_ui_group(ev, "bridge", label))
            used.add(i)
            continue

        if source == "panel_tasks_server" and phase == "after":
            mutation = str(ev.get("mutation") or "işlem")
            outcome = str(ev.get("outcome") or "ok")
            groups.append(build_evidence_ui_group(ev, "panel", f"Görev: {mutation} · {outcome}"))
            used.add(i)
            continue

        if op in ("guard.decision", "policy.blocked"):
            code = str((ev.get("error") or {}).get("code") or (ev.get("payload_summary") or {}).get("reason_code") or "koruma")
            groups.append(build_evidence_ui_group(ev, "guard", f"Koruma: {code}"))
            used.add(i)
            continue

        if source == "task_engine":
            groups.append(build_evidence_ui_group(ev, "engine", f"Motor · {ev.get('outcome', 'ok')}"))
            used.add(i)
            continue

        if phase == "before":
            used.add(i)
            continue

        groups.append(build_evidence_ui_group(ev, "other", f"{source} · {ev.get('outcome', 'ok')}"))
        used.add(i)

    groups.sort(key=lambda g: _parse_evidence_ts_ms(g["ts"]), reverse=True)
    return groups


def evidence_continue_target(group: dict | None) -> str | None:
    if not group or not group.get("canContinue"):
        return None
    if group.get("continueKind") == "task" and group.get("entityRefId"):
        return f"task:{group['entityRefId']}"
    if group.get("continueKind") == "chat" and group.get("titlePreview"):
        return f"chat:{group['titlePreview']}"
    return None


def test_u1_api_empty_journal(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    resp = pts.build_evidence_recent_response()
    assert resp["schema"] == UI_PROJECTION_SCHEMA
    assert resp["events"] == []
    assert resp["truncated"] is False


def test_u7_bridge_after_result_groups_to_one_chain():
    base = datetime(2026, 6, 19, 22, 5, 0, tzinfo=timezone.utc)
    result = project_evidence_for_ui(
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_KANDO_BRIDGE,
            store=STORE_BRIDGE_OUTBOX,
            operation=OPERATION_BRIDGE_TASK_POST,
            phase=PHASE_RESULT,
            outcome=OUTCOME_OK,
            payload_summary={"title_preview": "README düzelt", "route": "agent/async", "job_id": "j1"},
        )
    )
    after = project_evidence_for_ui(
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_KANDO_BRIDGE,
            store=STORE_BRIDGE_OUTBOX,
            operation=OPERATION_BRIDGE_TASK_POST,
            phase=PHASE_AFTER,
            outcome=OUTCOME_OK,
            payload_summary={"title_preview": "README düzelt", "route": "POST /task/agent"},
        )
    )
    result["ts"] = _iso_offset(base, 0)
    after["ts"] = _iso_offset(base, -5)
    groups = group_evidence_events_for_ui([result, after])
    assert len(groups) == 1
    assert groups[0]["kind"] == "bridge"
    assert "README" in groups[0]["label"]


def test_u8_guard_deny_no_task_continue():
    ev = project_evidence_for_ui(
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_GUARD_AUDIT,
            store=STORE_GUARD,
            operation=OPERATION_GUARD_DECISION,
            phase=PHASE_AFTER,
            outcome=OUTCOME_ERROR,
            error={"code": "sandbox_deny", "message": "denied"},
            payload_summary={"action": "write", "reason_code": "sandbox_deny", "route": "cli"},
        )
    )
    groups = group_evidence_events_for_ui([ev])
    assert len(groups) == 1
    assert groups[0]["kind"] == "guard"
    assert groups[0]["canContinue"] is False
    assert evidence_continue_target(groups[0]) is None


def test_u9_api_unreachable_returns_empty_events(tmp_path, monkeypatch):
    """UI: fetch fail → boş durum; journal yokken API 200 + events []."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    resp = pts.build_evidence_recent_response()
    assert resp["events"] == []
    assert resp["truncated"] is False


def test_u10_entity_ref_continue_targets_task():
    ev = project_evidence_for_ui(
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_PANEL_TASKS_SERVER,
            store=STORE_PANEL_TASKS,
            operation=OPERATION_PANEL_TASK_CREATE,
            phase=PHASE_AFTER,
            outcome=OUTCOME_OK,
            mutation="create",
            entity_id="tsk_abc99",
        )
    )
    groups = group_evidence_events_for_ui([ev])
    assert evidence_continue_target(groups[0]) == "task:tsk_abc99"


def test_u11_title_preview_continue_targets_chat_prefill():
    ev = project_evidence_for_ui(
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_KANDO_BRIDGE,
            store=STORE_BRIDGE_OUTBOX,
            operation=OPERATION_BRIDGE_TASK_POST,
            phase=PHASE_RESULT,
            outcome=OUTCOME_OK,
            payload_summary={"title_preview": "README düzelt", "route": "agent/async", "job_id": "j2"},
        )
    )
    groups = group_evidence_events_for_ui([ev])
    assert groups[0]["canContinue"] is True
    assert evidence_continue_target(groups[0]) == "chat:README düzelt"


def test_api_response_via_server_helper(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_PANEL_TASKS_SERVER,
        store=STORE_PANEL_TASKS,
        operation=OPERATION_PANEL_TASK_CREATE,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_api",
    )
    append_evidence_event(tmp_path, rec)
    resp = pts.build_evidence_recent_response(limit=20)
    assert len(resp["events"]) == 1
    assert resp["events"][0]["entity_ref"]["id"] == "tsk_api"
    assert "correlation_id" not in resp["events"][0]
