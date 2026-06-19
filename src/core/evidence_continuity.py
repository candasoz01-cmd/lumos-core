"""
Evidence Continuity v1 — append-only journal for server-side task mutations.

Schema: lumos.evidence_continuity.v1
Path: {base_dir}/logs/evidence_continuity.jsonl

Best-effort append; journal failure must not break main mutations.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from core.guard_audit import GuardEvent

from core.log_rotation import DEFAULT_KEEP, DEFAULT_MAX_BYTES, append_jsonl_with_rotation
from core.workspace_contract import allow_write_to_core, logs_dir_path

SCHEMA_V1 = "lumos.evidence_continuity.v1"

SOURCE_PANEL_TASKS_SERVER = "panel_tasks_server"
SOURCE_TASK_ENGINE = "task_engine"
SOURCE_KANDO_BRIDGE = "kando_bridge"
SOURCE_GUARD_AUDIT = "guard_audit"
SOURCE_ACTION_POLICY = "action_policy"

STORE_PANEL_TASKS = "panel_tasks"
STORE_TASK_ENGINE = "task_engine"
STORE_BRIDGE_OUTBOX = "bridge_outbox"
STORE_GUARD = "guard"
STORE_POLICY_LOG = "policy_log"

# EC2-05: journal store enum → relative path under lumos base (parallel truth; no merge v1)
PANEL_TASKS_STORE_REL_PATH = "tasks.json"
TASK_ENGINE_STORE_REL_PATH = "tasks/tasks.json"

TASK_STORE_REGISTRY: dict[str, str] = {
    STORE_PANEL_TASKS: PANEL_TASKS_STORE_REL_PATH,
    STORE_TASK_ENGINE: TASK_ENGINE_STORE_REL_PATH,
}

OPERATION_PANEL_TASK_CREATE = "panel.task.create"
OPERATION_PANEL_TASK_COMPLETE = "panel.task.complete"
OPERATION_PANEL_TASK_DELETE = "panel.task.delete"
OPERATION_PANEL_TASK_RESTORE = "panel.task.restore"
OPERATION_PANEL_TASK_PUT = "panel.task.put"
OPERATION_ENGINE_TASK_MUTATION = "engine.task.mutation"
OPERATION_BRIDGE_TASK_POST = "bridge.task.post"
OPERATION_GUARD_DECISION = "guard.decision"
OPERATION_POLICY_BLOCKED = "policy.blocked"

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

SOURCES = frozenset(
    {
        SOURCE_PANEL_TASKS_SERVER,
        SOURCE_TASK_ENGINE,
        SOURCE_KANDO_BRIDGE,
        SOURCE_GUARD_AUDIT,
        SOURCE_ACTION_POLICY,
    }
)
STORES = frozenset(
    {
        STORE_PANEL_TASKS,
        STORE_TASK_ENGINE,
        STORE_BRIDGE_OUTBOX,
        STORE_GUARD,
        STORE_POLICY_LOG,
    }
)
OPERATIONS = frozenset(
    {
        OPERATION_PANEL_TASK_CREATE,
        OPERATION_PANEL_TASK_COMPLETE,
        OPERATION_PANEL_TASK_DELETE,
        OPERATION_PANEL_TASK_RESTORE,
        OPERATION_PANEL_TASK_PUT,
        OPERATION_ENGINE_TASK_MUTATION,
        OPERATION_BRIDGE_TASK_POST,
        OPERATION_GUARD_DECISION,
        OPERATION_POLICY_BLOCKED,
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
        "action",
        "reason_code",
        "job_id",
    }
)

_POLICY_BLOCKED_ROUTE = "cli:task_mutation"

_MIRROR_CTX = threading.local()

EVIDENCE_CONTINUITY_FILENAME = "evidence_continuity.jsonl"

# EC2-09: evidence-specific retention (v1 — aliases log_rotation defaults; no config override)
EVIDENCE_RETENTION_POLICY_ID = "lumos.evidence_continuity.retention.v1"
EVIDENCE_CONTINUITY_MAX_BYTES = DEFAULT_MAX_BYTES
EVIDENCE_CONTINUITY_KEEP = DEFAULT_KEEP
EVIDENCE_READ_SCOPE_CURRENT_ONLY = "current_file_only"

# EC2-07: tasks.json events[] — UI projection metadata (v1; no migration)
TASKS_JSON_EVENTS_PROJECTION_POLICY_ID = "lumos.tasks_json.events_projection.v1"
AUDIT_TRUTH_EVIDENCE_JOURNAL = "evidence_continuity_journal"
EVENTS_PROJECTION_ROLE = "ui_projection"
EVENTS_DEPRECATION_SOFT_V1 = "soft_deprecated_v1"


def generate_correlation_id() -> str:
    return str(uuid4())


def evidence_continuity_path(base_dir: Path | str) -> Path:
    return logs_dir_path(base_dir) / EVIDENCE_CONTINUITY_FILENAME


def task_store_rel_path(store: str) -> str | None:
    """Relative path under lumos base for a journal `store` enum, or None if not a task store."""
    return TASK_STORE_REGISTRY.get(store)


def resolve_task_store_path(base_dir: Path | str, store: str) -> Path | None:
    """Absolute path for a task store enum under base_dir, or None if unknown store."""
    rel = task_store_rel_path(store)
    if rel is None:
        return None
    return Path(base_dir) / rel


def evidence_retention_policy() -> dict[str, Any]:
    """Read-only v1 retention policy DTO (no config override)."""
    return {
        "policy_id": EVIDENCE_RETENTION_POLICY_ID,
        "max_bytes_per_file": EVIDENCE_CONTINUITY_MAX_BYTES,
        "rotated_files_kept": EVIDENCE_CONTINUITY_KEEP,
        "max_file_slots": EVIDENCE_CONTINUITY_KEEP + 1,
        "read_scope": EVIDENCE_READ_SCOPE_CURRENT_ONLY,
    }


def tasks_json_events_projection_meta(*, events_count: int | None = None) -> dict[str, Any]:
    """Read-only v1 DTO: tasks.json events[] is UI projection; journal is audit truth."""
    meta: dict[str, Any] = {
        "policy_id": TASKS_JSON_EVENTS_PROJECTION_POLICY_ID,
        "role": EVENTS_PROJECTION_ROLE,
        "audit_truth": AUDIT_TRUTH_EVIDENCE_JOURNAL,
        "reconcile_with_journal": False,
        "deprecation_status": EVENTS_DEPRECATION_SOFT_V1,
    }
    if events_count is not None:
        meta["events_count"] = max(0, int(events_count))
    return meta


def enrich_tasks_doc_api_response(doc: dict[str, Any]) -> dict[str, Any]:
    """HTTP GET wrapper: attach events_meta without mutating on-disk tasks.json."""
    out = dict(doc)
    events = out.get("events")
    count = len(events) if isinstance(events, list) else 0
    out["events_meta"] = tasks_json_events_projection_meta(events_count=count)
    return out


def _evidence_journal_file_paths(base_dir: Path | str) -> list[Path]:
    """Current + rotated evidence journal paths that exist on disk."""
    current = evidence_continuity_path(base_dir)
    paths: list[Path] = []
    if current.is_file():
        paths.append(current)
    for n in range(1, EVIDENCE_CONTINUITY_KEEP + 1):
        rotated = Path(str(current) + f".{n}")
        if rotated.is_file():
            paths.append(rotated)
    return paths


def evidence_journal_storage_summary(base_dir: Path | str) -> dict[str, Any]:
    """Read-only storage footprint for evidence journal files."""
    files = _evidence_journal_file_paths(base_dir)
    total_bytes = 0
    for p in files:
        try:
            total_bytes += p.stat().st_size
        except OSError:
            pass
    return {
        "journal_path": str(evidence_continuity_path(base_dir)),
        "file_count": len(files),
        "total_bytes": total_bytes,
    }


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
        elif key in ("action", "reason_code"):
            out[key] = str(value)[:80]
        elif key == "job_id":
            out[key] = str(value)[:32]
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


def is_evidence_mirror_active() -> bool:
    return bool(getattr(_MIRROR_CTX, "active", False))


def _set_evidence_mirror_active(active: bool) -> None:
    _MIRROR_CTX.active = active


def _guard_deny_error_message(reason: str | None) -> str:
    if reason == "core_state_under_live_base":
        return "sandbox core write denied"
    return "guard deny"


def mirror_guard_event_record(event: GuardEvent) -> dict[str, Any]:
    reason_code = (event.reason or "unknown")[:80]
    return build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_GUARD_AUDIT,
        store=STORE_GUARD,
        operation=OPERATION_GUARD_DECISION,
        phase=PHASE_AFTER,
        outcome=OUTCOME_ERROR,
        error={
            "code": reason_code,
            "message": _guard_deny_error_message(event.reason),
        },
        payload_summary={
            "action": event.action,
            "reason_code": reason_code,
            "route": event.caller or "",
            "title_preview": event.path.name,
        },
    )


def mirror_guard_event_to_evidence_journal(
    event: GuardEvent,
    *,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    from core.lumos_base_dir import lumos_base_dir

    record = mirror_guard_event_record(event)
    target = base_dir if base_dir is not None else lumos_base_dir()
    _set_evidence_mirror_active(True)
    try:
        return append_evidence_event(target, record)
    finally:
        _set_evidence_mirror_active(False)


def mirror_policy_blocked_record(action: str, reason: str) -> dict[str, Any]:
    reason_code = str(reason)[:80]
    return build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_ACTION_POLICY,
        store=STORE_POLICY_LOG,
        operation=OPERATION_POLICY_BLOCKED,
        phase=PHASE_AFTER,
        outcome=OUTCOME_ERROR,
        error={"code": reason_code, "message": "policy blocked"},
        payload_summary={
            "action": action,
            "reason_code": reason_code,
            "route": _POLICY_BLOCKED_ROUTE,
        },
    )


def mirror_policy_blocked_to_evidence_journal(
    base_dir: Path | str,
    action: str,
    reason: str,
) -> dict[str, Any]:
    record = mirror_policy_blocked_record(action, reason)
    _set_evidence_mirror_active(True)
    try:
        return append_evidence_event(base_dir, record)
    finally:
        _set_evidence_mirror_active(False)


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


_BRIDGE_AGENT_RESULT_ROUTE = "agent/async"


def _bridge_agent_result_outcome(final_report: dict[str, Any]) -> tuple[str, dict[str, str] | None]:
    status = str(final_report.get("status") or "").strip().lower()
    if status == "ok":
        return OUTCOME_OK, None
    errors = final_report.get("errors")
    code = "agent_failed"
    if isinstance(errors, list) and errors:
        code = str(errors[0])[:80]
    elif status == "partial":
        code = "agent_partial"
    return OUTCOME_ERROR, {"code": code, "message": "agent pipeline failed"}


def mirror_bridge_agent_result_record(
    job_id: str,
    final_report: dict[str, Any],
) -> dict[str, Any]:
    task_text = str(final_report.get("task") or final_report.get("selected_target") or "")
    outcome, error = _bridge_agent_result_outcome(final_report)
    return build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_KANDO_BRIDGE,
        store=STORE_BRIDGE_OUTBOX,
        operation=OPERATION_BRIDGE_TASK_POST,
        phase=PHASE_RESULT,
        outcome=outcome,
        payload_summary={
            "title_preview": task_text,
            "route": _BRIDGE_AGENT_RESULT_ROUTE,
            "job_id": job_id,
        },
        error=error,
    )


def mirror_bridge_agent_result_to_evidence_journal(
    job_id: str,
    final_report: dict[str, Any],
    *,
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    from core.lumos_base_dir import lumos_base_dir

    record = mirror_bridge_agent_result_record(job_id, final_report)
    target = base_dir if base_dir is not None else lumos_base_dir()
    return append_evidence_event(target, record)


UI_PROJECTION_SCHEMA = "lumos.evidence_continuity.ui_projection.v1"
DEFAULT_READ_LIMIT = 20
MAX_READ_LIMIT = 50
_ERROR_MESSAGE_UI_MAX = 80

_UI_PROJECTION_FIELDS = frozenset(
    {
        "ts",
        "source",
        "store",
        "operation",
        "phase",
        "outcome",
        "mutation",
        "entity_ref",
        "payload_summary",
        "error",
    }
)


def _parse_evidence_ts_ms(ts: str) -> float:
    raw = str(ts or "").strip()
    if not raw:
        return 0.0
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return 0.0


def read_recent_evidence_events(
    base_dir: Path | str,
    limit: int = DEFAULT_READ_LIMIT,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Tail-read validated journal records, newest first.
    Returns (records, truncated) where truncated is True when more valid rows exist than limit.
    """
    try:
        limit_n = int(limit)
    except (TypeError, ValueError):
        limit_n = DEFAULT_READ_LIMIT
    limit_n = max(1, min(limit_n, MAX_READ_LIMIT))

    path = evidence_continuity_path(base_dir)
    if not path.is_file():
        return [], False

    valid: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict) or validate_evidence_record(rec):
                continue
            valid.append(rec)
    except OSError:
        return [], False

    truncated = len(valid) > limit_n
    tail = valid[-limit_n:]
    tail.sort(key=lambda r: _parse_evidence_ts_ms(str(r.get("ts", ""))), reverse=True)
    return tail, truncated


def project_evidence_for_ui(record: dict[str, Any]) -> dict[str, Any]:
    """Demo-safe DTO for panel UI; correlation_id and unknown keys omitted."""
    out: dict[str, Any] = {}
    for key in _UI_PROJECTION_FIELDS:
        if key not in record:
            continue
        value = record[key]
        if key == "entity_ref":
            if isinstance(value, dict) and value.get("id"):
                out[key] = {"kind": "task", "id": str(value["id"])[:80]}
            continue
        if key == "payload_summary":
            summary = sanitize_payload_summary(value if isinstance(value, dict) else None)
            if summary:
                out[key] = summary
            continue
        if key == "error":
            if isinstance(value, dict) and value.get("code"):
                err: dict[str, str] = {"code": str(value["code"])[:80]}
                msg = str(value.get("message", ""))[:_ERROR_MESSAGE_UI_MAX]
                if msg:
                    err["message"] = msg
                out[key] = err
            continue
        if value is not None and value != "":
            out[key] = value
    return out


def build_ui_projection_response(
    events: list[dict[str, Any]],
    *,
    truncated: bool = False,
) -> dict[str, Any]:
    return {
        "schema": UI_PROJECTION_SCHEMA,
        "events": [project_evidence_for_ui(e) for e in events],
        "truncated": bool(truncated),
    }


EVIDENCE_QUERY_SCHEMA = "lumos.evidence_continuity.query.v1"
EVIDENCE_QUERY_READ_SCOPE = "recent_tail_only"


def filter_evidence_events(
    events: list[dict[str, Any]],
    *,
    entity_id: str | None = None,
    operation: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """Filter journal records by optional entity_id / operation / source (EC2-11 v1)."""
    eid = str(entity_id).strip() if entity_id else None
    op = str(operation).strip() if operation else None
    src = str(source).strip() if source else None
    if not eid and not op and not src:
        return list(events)
    out: list[dict[str, Any]] = []
    for rec in events:
        if not isinstance(rec, dict):
            continue
        if op and str(rec.get("operation", "")) != op:
            continue
        if src and str(rec.get("source", "")) != src:
            continue
        if eid:
            entity_ref = rec.get("entity_ref")
            rid = ""
            if isinstance(entity_ref, dict):
                rid = str(entity_ref.get("id", "")).strip()
            if rid != eid:
                continue
        out.append(rec)
    return out


def build_evidence_query_response(
    events: list[dict[str, Any]],
    *,
    truncated: bool = False,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resp = build_ui_projection_response(events, truncated=truncated)
    resp["schema"] = EVIDENCE_QUERY_SCHEMA
    resp["filters"] = dict(filters) if filters else {}
    resp["read_scope"] = EVIDENCE_QUERY_READ_SCOPE
    return resp


def query_evidence_events(
    base_dir: Path | str,
    *,
    entity_id: str | None = None,
    operation: str | None = None,
    source: str | None = None,
    limit: int = DEFAULT_READ_LIMIT,
) -> dict[str, Any]:
    """Read recent journal tail and apply structured filters (v1 — no full reconstruct)."""
    limit_n = max(1, min(int(limit), MAX_READ_LIMIT))
    events, truncated = read_recent_evidence_events(base_dir, MAX_READ_LIMIT)
    filtered = filter_evidence_events(
        events,
        entity_id=entity_id,
        operation=operation,
        source=source,
    )
    filters = {
        k: v
        for k, v in {
            "entity_id": entity_id,
            "operation": operation,
            "source": source,
        }.items()
        if v
    }
    return build_evidence_query_response(
        filtered[:limit_n],
        truncated=truncated,
        filters=filters,
    )


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
            max_bytes=EVIDENCE_CONTINUITY_MAX_BYTES,
            keep=EVIDENCE_CONTINUITY_KEEP,
        )
        result.update(append_result)
    except Exception:
        return result
    return result
