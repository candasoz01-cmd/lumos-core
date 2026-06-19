"""
Evidence Continuity v1 — append-only journal for server-side task mutations.

Schema: lumos.evidence_continuity.v1
Path: {base_dir}/logs/evidence_continuity.jsonl

Best-effort append; journal failure must not break main mutations.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.log_rotation import DEFAULT_KEEP, DEFAULT_MAX_BYTES, append_jsonl_with_rotation
from core.workspace_contract import allow_write_to_core, logs_dir_path

SCHEMA_V1 = "lumos.evidence_continuity.v1"

SOURCE_PANEL_TASKS_SERVER = "panel_tasks_server"
SOURCE_TASK_ENGINE = "task_engine"
SOURCE_KANDO_BRIDGE = "kando_bridge"

STORE_PANEL_TASKS = "panel_tasks"
STORE_TASK_ENGINE = "task_engine"
STORE_BRIDGE_OUTBOX = "bridge_outbox"

OPERATION_PANEL_TASK_CREATE = "panel.task.create"
OPERATION_PANEL_TASK_COMPLETE = "panel.task.complete"
OPERATION_PANEL_TASK_DELETE = "panel.task.delete"
OPERATION_PANEL_TASK_RESTORE = "panel.task.restore"
OPERATION_PANEL_TASK_PUT = "panel.task.put"
OPERATION_ENGINE_TASK_MUTATION = "engine.task.mutation"
OPERATION_BRIDGE_TASK_POST = "bridge.task.post"

PHASE_BEFORE = "before"
PHASE_AFTER = "after"
PHASE_ERROR = "error"
PHASE_RESULT = "result"

OUTCOME_OK = "ok"
OUTCOME_ERROR = "error"

MUTATION_CREATE = "create"
MUTATION_COMPLETE = "complete"
MUTATION_DELETE = "delete"
MUTATION_RESTORE = "restore"
MUTATION_UPDATE = "update"
MUTATION_ARCHIVE = "archive"

SOURCES = frozenset({SOURCE_PANEL_TASKS_SERVER, SOURCE_TASK_ENGINE, SOURCE_KANDO_BRIDGE})
STORES = frozenset({STORE_PANEL_TASKS, STORE_TASK_ENGINE, STORE_BRIDGE_OUTBOX})
OPERATIONS = frozenset(
    {
        OPERATION_PANEL_TASK_CREATE,
        OPERATION_PANEL_TASK_COMPLETE,
        OPERATION_PANEL_TASK_DELETE,
        OPERATION_PANEL_TASK_RESTORE,
        OPERATION_PANEL_TASK_PUT,
        OPERATION_ENGINE_TASK_MUTATION,
        OPERATION_BRIDGE_TASK_POST,
    }
)
PHASES = frozenset({PHASE_BEFORE, PHASE_AFTER, PHASE_ERROR, PHASE_RESULT})
OUTCOMES = frozenset({OUTCOME_OK, OUTCOME_ERROR})

PAYLOAD_SUMMARY_ALLOWED_KEYS = frozenset(
    {
        "title_preview",
        "route",
        "task_count",
        "events_appended",
        "trash_written",
        "step_count",
    }
)

EVIDENCE_CONTINUITY_FILENAME = "evidence_continuity.jsonl"


def generate_correlation_id() -> str:
    return str(uuid4())


def evidence_continuity_path(base_dir: Path | str) -> Path:
    return logs_dir_path(base_dir) / EVIDENCE_CONTINUITY_FILENAME


def _now_iso_ms() -> str:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def title_preview_from(text: str) -> str:
    cleaned = text.replace("\n", " ").replace("\r", " ").strip()
    return cleaned[:40]


def sanitize_payload_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not summary:
        return None
    out: dict[str, Any] = {}
    for key, value in summary.items():
        if key not in PAYLOAD_SUMMARY_ALLOWED_KEYS:
            continue
        if key == "title_preview":
            out[key] = title_preview_from(str(value))
        elif key in ("task_count", "events_appended", "step_count"):
            try:
                out[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif key == "trash_written":
            out[key] = bool(value)
        elif key == "route":
            out[key] = str(value)[:80]
        else:
            out[key] = value
    return out or None


def validate_evidence_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "schema",
        "ts",
        "correlation_id",
        "source",
        "store",
        "operation",
        "phase",
        "outcome",
    )
    for field in required:
        if field not in record or record[field] in (None, ""):
            errors.append(f"missing:{field}")
    if record.get("schema") != SCHEMA_V1:
        errors.append("invalid:schema")
    if record.get("source") not in SOURCES:
        errors.append("invalid:source")
    if record.get("store") not in STORES:
        errors.append("invalid:store")
    if record.get("operation") not in OPERATIONS:
        errors.append("invalid:operation")
    if record.get("phase") not in PHASES:
        errors.append("invalid:phase")
    if record.get("outcome") not in OUTCOMES:
        errors.append("invalid:outcome")
    entity_ref = record.get("entity_ref")
    if entity_ref is not None:
        if not isinstance(entity_ref, dict):
            errors.append("invalid:entity_ref")
        elif entity_ref.get("kind") != "task" or not str(entity_ref.get("id", "")).strip():
            errors.append("invalid:entity_ref")
    payload = record.get("payload_summary")
    if payload is not None:
        if not isinstance(payload, dict):
            errors.append("invalid:payload_summary")
        else:
            for key in payload:
                if key not in PAYLOAD_SUMMARY_ALLOWED_KEYS:
                    errors.append(f"invalid:payload_summary_key:{key}")
    return errors


def build_evidence_record(
    *,
    correlation_id: str,
    source: str,
    store: str,
    operation: str,
    phase: str,
    outcome: str,
    mutation: str | None = None,
    entity_id: str | None = None,
    payload_summary: dict[str, Any] | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": SCHEMA_V1,
        "ts": _now_iso_ms(),
        "correlation_id": correlation_id,
        "source": source,
        "store": store,
        "operation": operation,
        "phase": phase,
        "outcome": outcome,
    }
    if mutation:
        record["mutation"] = mutation
    if entity_id:
        record["entity_ref"] = {"kind": "task", "id": str(entity_id)}
    summary = sanitize_payload_summary(payload_summary)
    if summary:
        record["payload_summary"] = summary
    if error:
        record["error"] = {
            "code": str(error.get("code", "unknown")),
            "message": str(error.get("message", ""))[:200],
        }
    return record


def _bridge_goal_preview_from_raw(raw: bytes | bytearray | None) -> str:
    if not raw:
        return ""
    try:
        dec = bytes(raw).decode("utf-8").strip()
    except UnicodeDecodeError:
        return ""
    if not dec:
        return ""
    if dec.startswith("{"):
        try:
            obj = json.loads(dec)
        except json.JSONDecodeError:
            return dec
        if isinstance(obj, dict):
            for key in ("task", "goal", "text", "raw_text", "title", "instruction", "prompt"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return dec
    return dec


def _bridge_post_task_route(envelope_meta: dict) -> str:
    route_o = envelope_meta.get("route")
    if route_o is not None and str(route_o).strip():
        return f"POST /task/{route_o}"
    return "POST /task"


def _bridge_post_task_outcome(snapshot: dict | None) -> tuple[str, dict[str, str] | None]:
    if snapshot is None:
        return OUTCOME_ERROR, {
            "code": "snapshot_incomplete",
            "message": "no_json_response_sent",
        }
    http_status = snapshot.get("http_status")
    try:
        http_status = int(http_status) if http_status is not None else None
    except (TypeError, ValueError):
        http_status = None
    resp = snapshot.get("response")
    accepted = resp.get("accepted") if isinstance(resp, dict) else None
    if http_status is None:
        return OUTCOME_ERROR, {
            "code": "snapshot_incomplete",
            "message": "missing_http_status",
        }
    if http_status >= 400 or accepted is False:
        err_code = "bridge_task_rejected"
        err_msg = "request not accepted"
        if isinstance(resp, dict):
            if resp.get("error"):
                err_code = str(resp.get("error"))[:80]
            if resp.get("destructive_code"):
                err_code = str(resp.get("destructive_code"))[:80]
        return OUTCOME_ERROR, {"code": err_code, "message": err_msg}
    if 200 <= http_status < 400:
        return OUTCOME_OK, None
    return OUTCOME_ERROR, {"code": "http_error", "message": f"status {http_status}"}


def mirror_post_task_outbox_record(
    envelope_meta: dict,
    snapshot: dict | None,
    *,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    raw = envelope_meta.get("raw")
    if not isinstance(raw, (bytes, bytearray)):
        raw = b""
    goal_preview = _bridge_goal_preview_from_raw(raw)
    outcome, error = _bridge_post_task_outcome(snapshot)
    return build_evidence_record(
        correlation_id=correlation_id or generate_correlation_id(),
        source=SOURCE_KANDO_BRIDGE,
        store=STORE_BRIDGE_OUTBOX,
        operation=OPERATION_BRIDGE_TASK_POST,
        phase=PHASE_AFTER,
        outcome=outcome,
        payload_summary={
            "title_preview": goal_preview,
            "route": _bridge_post_task_route(envelope_meta),
        },
        error=error,
    )


def mirror_post_task_outbox_to_evidence_journal(
    envelope_meta: dict,
    snapshot: dict | None,
    *,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    from core.lumos_base_dir import lumos_base_dir

    record = mirror_post_task_outbox_record(envelope_meta, snapshot)
    target = base_dir if base_dir is not None else lumos_base_dir()
    return append_evidence_event(target, record)


def append_evidence_event(
    base_dir: Path | str,
    record: dict[str, Any],
    *,
    is_sandbox_mode: bool = False,
) -> dict[str, Any]:
    """
    Append one evidence continuity event. Best-effort; never raises.
    """
    result: dict[str, Any] = {"appended": False, "path": str(evidence_continuity_path(base_dir))}
    try:
        if validate_evidence_record(record):
            return result
        path = evidence_continuity_path(base_dir)
        if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
            return result
        append_result = append_jsonl_with_rotation(
            path,
            record,
            max_bytes=DEFAULT_MAX_BYTES,
            keep=DEFAULT_KEEP,
        )
        result.update(append_result)
    except Exception:
        return result
    return result
