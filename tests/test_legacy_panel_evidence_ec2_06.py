"""EC2-06: legacy panel evidence correlation strip — L1–L6."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    OPERATION_BRIDGE_TASK_POST,
    OPERATION_PANEL_TASK_CREATE,
    OUTCOME_OK,
    PHASE_AFTER,
    PHASE_RESULT,
    SOURCE_KANDO_BRIDGE,
    SOURCE_PANEL_TASKS_SERVER,
    STORE_BRIDGE_OUTBOX,
    STORE_PANEL_TASKS,
    append_evidence_event,
    build_evidence_record,
    generate_correlation_id,
)

EVIDENCE_BRIDGE_PAIR_MAX_MS = 60000


def _load_panel_tasks_server():
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    return pts


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


def group_evidence_events_for_ui(events: list[dict]) -> list[dict]:
    """Python mirror of panel/js/evidence-correlation-strip.js grouping (L4)."""
    listing = list(events)
    listing.sort(key=lambda e: _parse_evidence_ts_ms(str(e.get("ts", ""))), reverse=True)
    used: set[int] = set()
    groups: list[dict] = []

    for i, ev in enumerate(listing):
        if i in used or not isinstance(ev, dict):
            used.add(i)
            continue
        op = str(ev.get("operation", ""))
        phase = str(ev.get("phase", ""))
        source = str(ev.get("source", ""))

        if op == OPERATION_BRIDGE_TASK_POST and phase == PHASE_RESULT:
            matched_after = None
            for j in range(i + 1, len(listing)):
                if j in used:
                    continue
                cand = listing[j]
                if str(cand.get("operation", "")) != OPERATION_BRIDGE_TASK_POST:
                    continue
                if str(cand.get("phase", "")) != PHASE_AFTER:
                    continue
                dt = abs(
                    _parse_evidence_ts_ms(str(ev.get("ts", "")))
                    - _parse_evidence_ts_ms(str(cand.get("ts", "")))
                )
                if dt * 1000 > EVIDENCE_BRIDGE_PAIR_MAX_MS:
                    continue
                tp1 = str((ev.get("payload_summary") or {}).get("title_preview", ""))
                tp2 = str((cand.get("payload_summary") or {}).get("title_preview", ""))
                if tp1 and tp2 and not evidence_title_preview_prefix_match(tp1, tp2):
                    continue
                matched_after = cand
                used.add(j)
                break
            preview = str((ev.get("payload_summary") or {}).get("title_preview", "")).strip()
            label = f"Köprü: {ev.get('outcome', 'ok')}" + (
                f" · {preview}" if preview else (" · iletim" if matched_after else "")
            )
            groups.append({"kind": "bridge", "label": label, "ts": ev.get("ts")})
            used.add(i)
            continue

        if source == SOURCE_PANEL_TASKS_SERVER and phase == PHASE_AFTER:
            mutation = str(ev.get("mutation", "işlem"))
            groups.append(
                {
                    "kind": "panel",
                    "label": f"Görev: {mutation} · {ev.get('outcome', 'ok')}",
                    "ts": ev.get("ts"),
                }
            )
            used.add(i)
            continue

        if phase in (PHASE_AFTER, PHASE_RESULT):
            groups.append({"kind": "other", "label": str(ev.get("outcome", "ok")), "ts": ev.get("ts")})
            used.add(i)
            continue

        used.add(i)

    groups.sort(key=lambda g: _parse_evidence_ts_ms(str(g.get("ts", ""))), reverse=True)
    return groups


def test_l1_evidence_correlation_strip_module_exists() -> None:
    path = _REPO_ROOT / "panel" / "js" / "evidence-correlation-strip.js"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "LumosEvidenceCorrelationStrip" in text
    assert "groupEvidenceEventsForUi" in text


def test_l2_index_html_script_order() -> None:
    html = (_REPO_ROOT / "panel" / "index.html").read_text(encoding="utf-8")
    strip_pos = html.index("evidence-correlation-strip.js")
    app_pos = html.index("js/app.js")
    assert strip_pos < app_pos


def test_l3_app_js_legacy_strip_mount() -> None:
    app = (_REPO_ROOT / "panel" / "js" / "app.js").read_text(encoding="utf-8")
    assert "legacy-evidence-continue" in app
    assert "wireLegacyEvidenceStrip" in app
    assert "buildLegacyEvidenceStripHtml" in app
    strip = (_REPO_ROOT / "panel" / "js" / "evidence-correlation-strip.js").read_text(encoding="utf-8")
    assert "legacy-evidence-strip" in strip


def test_l4_bridge_pair_grouping_parity(tmp_path: Path) -> None:
    cid_after = generate_correlation_id()
    cid_result = generate_correlation_id()
    title = "Legacy parity test görev"
    append_evidence_event(
        tmp_path,
        build_evidence_record(
            correlation_id=cid_after,
            source=SOURCE_KANDO_BRIDGE,
            store=STORE_BRIDGE_OUTBOX,
            operation=OPERATION_BRIDGE_TASK_POST,
            phase=PHASE_AFTER,
            outcome=OUTCOME_OK,
            payload_summary={"title_preview": title, "route": "post_task"},
        ),
    )
    append_evidence_event(
        tmp_path,
        build_evidence_record(
            correlation_id=cid_result,
            source=SOURCE_KANDO_BRIDGE,
            store=STORE_BRIDGE_OUTBOX,
            operation=OPERATION_BRIDGE_TASK_POST,
            phase=PHASE_RESULT,
            outcome=OUTCOME_OK,
            payload_summary={"title_preview": title, "job_id": "job_ec2_06"},
        ),
    )
    append_evidence_event(
        tmp_path,
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_PANEL_TASKS_SERVER,
            store=STORE_PANEL_TASKS,
            operation=OPERATION_PANEL_TASK_CREATE,
            phase=PHASE_AFTER,
            outcome=OUTCOME_OK,
            mutation="create",
            entity_id="tsk_ec2_06",
            payload_summary={"title_preview": "Panel create"},
        ),
    )
    journal = tmp_path / "logs" / "evidence_continuity.jsonl"
    events = []
    for line in journal.read_text(encoding="utf-8").strip().splitlines():
        import json

        events.append(json.loads(line))
    groups = group_evidence_events_for_ui(events)
    assert groups
    bridge_groups = [g for g in groups if g["kind"] == "bridge"]
    assert bridge_groups
    assert "Köprü:" in bridge_groups[0]["label"]


def test_l5_evidence_recent_route_exists() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert "/evidence/recent" in src
    assert "build_evidence_recent_response" in src


def test_l6_panel_create_still_journals(tmp_path: Path) -> None:
    """Regression: legacy strip does not alter journal write path."""
    append_evidence_event(
        tmp_path,
        build_evidence_record(
            correlation_id=generate_correlation_id(),
            source=SOURCE_PANEL_TASKS_SERVER,
            store=STORE_PANEL_TASKS,
            operation=OPERATION_PANEL_TASK_CREATE,
            phase=PHASE_AFTER,
            outcome=OUTCOME_OK,
            mutation="create",
            entity_id="tsk_l6",
        ),
    )
    journal = tmp_path / "logs" / "evidence_continuity.jsonl"
    assert journal.is_file()
    assert "panel_tasks_server" in journal.read_text(encoding="utf-8")
