"""ADR-032 Shadow Watch kernel — incident ledger, scope checksum, re-entry bind.

Bu modül Sentinel'in gözlem kipidir; ajan/orkestrasyon katmanı değildir.
Gate, panel, TEG consume ve varsayılan-on wiring **yok**. Hiçbir production
yolu burayı çağırmaz; çağrı test veya ilerideki opt-in dilimindir.

Gözcü yazmaz. Niyet alanı yoktur. Re-entry yalnız doğrulanabilir oturum,
iş yükü (job) veya Board lease soyuna bağlanır; subject_id + agent_id yetmez.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from core.lumos_base_dir import lumos_base_dir

SCHEMA_INCIDENT = "lumos.shadow_watch.incident.v1"
SCHEMA_LEDGER = "lumos.shadow_watch.ledger.v1"
SCHEMA_MANIFEST = "lumos.shadow_watch.manifest.v1"
LEDGER_REL = Path("ledgers") / "shadow_watch.jsonl"
LEDGER_TIP_REL = Path("ledgers") / "shadow_watch.tip"
GENESIS_HASH = "0" * 64

ACTION_OBSERVE = "shadow_watch_observe"
WATCHER_ALLOWED_ACTIONS = frozenset({ACTION_OBSERVE})

STATE_IN_SCOPE = "IN_SCOPE"
STATE_INCIDENT_OPEN = "INCIDENT_OPEN"
STATE_RECALL_ISSUED = "RECALL_ISSUED"
STATE_RETURNED = "RETURNED_TO_SCOPE"
STATE_WATCH_ARMED = "WATCH_ARMED"
STATE_WATCHING = "WATCHING"
STATE_SURFACE_EXIT = "SURFACE_EXIT"
STATE_QUARANTINED = "QUARANTINED"
STATE_BLOCKED = "BLOCKED"
STATE_FAIL_CLOSED_BLOCK = "FAIL_CLOSED_BLOCK"
STATE_CLOSED = "CLOSED"

EVENT_OPEN = "incident_open"
EVENT_RECALL = "recall_issued"
EVENT_RETURNED = "returned_to_scope"
EVENT_WATCHING = "watching"
EVENT_TELEMETRY = "telemetry"
EVENT_SURFACE_EXIT = "surface_exit"
EVENT_BLOCK = "fail_closed_block"

CORRELATE = "correlated_reentry"
NO_INHERIT = "no_inherit"

REASON_SUBJECT_MISMATCH = "subject_mismatch"
REASON_AGENT_MISMATCH = "agent_mismatch"
REASON_IDENTITY_UNVERIFIED = "identity_unverified"
REASON_SESSION_CONFLICT = "session_conflict_without_lease"
REASON_CORRELATED_SESSION = "correlated_session"
REASON_CORRELATED_LEASE = "correlated_lease"
REASON_CORRELATED_JOB = "correlated_job"
REASON_RECALL_REQUIRED = "recall_required"
REASON_OBSERVE_GRANT_MISSING = "observe_grant_missing"
REASON_WATCHER_WRITE = "watcher_write_forbidden"
REASON_CHASE_FORBIDDEN = "chase_forbidden"
REASON_INTENT_FORBIDDEN = "intent_field_forbidden"
REASON_MANIFEST_MISSING = "manifest_missing"
REASON_SINK_UNAVAILABLE = "sink_unavailable"
REASON_IN_SCOPE = "in_scope"
REASON_SCOPE_VIOLATION = "scope_violation"

_PLACEHOLDER_IDS = frozenset(
    {
        "",
        "unknown",
        "unspecified",
        "n/a",
        "none",
        "session:unspecified",
        "session:unknown",
        "job:unspecified",
        "job:unknown",
        "claim:unspecified",
        "claim:unknown",
    }
)

_TELEMETRY_FORBIDDEN_KEYS = frozenset(
    {
        "content",
        "body",
        "payload",
        "token",
        "secret",
        "passphrase",
        "title",
        "text",
        "prompt",
        "headers",
    }
)

_LABEL_MAY = frozenset(
    {
        "quarantine",
        "narrower_scope",
        "read_only",
        "extra_confirmation",
        "auto_block",
    }
)
_LABEL_MUST_NOT = frozenset(
    {
        "chase",
        "never_auto",
        "standing_merge",
        "consent_bypass",
        "grant_widen",
        "unlock",
        "external_track",
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(data: Mapping[str, Any]) -> str:
    return json.dumps(dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_verifiable_id(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.lower() in _PLACEHOLDER_IDS:
        return False
    return True


def _with_sidecar_lock(lock_path: Path, action: Callable[[], Any]) -> Any:
    try:
        import fcntl
    except ImportError:
        fcntl = None  # type: ignore[assignment]
    if fcntl is None:
        return action()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        try:
            return action()
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


@dataclass(frozen=True)
class ScopeManifest:
    tools: tuple[str, ...] = ()
    path_prefixes: tuple[str, ...] = ()
    network_classes: tuple[str, ...] = ()
    action_keys: tuple[str, ...] = ()
    task_id: str = ""
    profile: str = "rapor"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_MANIFEST,
            "tools": list(self.tools),
            "path_prefixes": list(self.path_prefixes),
            "network_classes": list(self.network_classes),
            "action_keys": list(self.action_keys),
            "task_id": self.task_id,
            "profile": self.profile,
        }


def manifest_sha256(manifest: ScopeManifest) -> str:
    return _sha256_hex(_canonical(manifest.as_dict()))


@dataclass(frozen=True)
class ObservedAction:
    tool: str = ""
    path: str = ""
    network_class: str = ""
    action_key: str = ""
    task_op: str = ""


@dataclass(frozen=True)
class WorkloadIdentity:
    """Re-entry bağının doğrulanabilir parçası.

    subject_id + agent_id zorunlu ama **yeterli değil**. En az bir doğrulanabilir
    iş yükü kimliği gerekir: session_id, Board claim/lease soyu veya job_id.
    """

    subject_id: str
    agent_id: str
    session_id: str = ""
    claim_id: str = ""
    lease_lineage: tuple[str, ...] = ()
    job_id: str = ""

    def __post_init__(self) -> None:
        if not str(self.subject_id or "").strip():
            raise ValueError("subject_id required")
        if not str(self.agent_id or "").strip():
            raise ValueError("agent_id required")

    def lineage_ids(self) -> frozenset[str]:
        found: set[str] = set()
        if _is_verifiable_id(self.claim_id):
            found.add(self.claim_id.strip())
        for item in self.lease_lineage:
            if _is_verifiable_id(item):
                found.add(item.strip())
        return frozenset(found)

    def has_verifiable_lineage(self) -> bool:
        return (
            _is_verifiable_id(self.session_id)
            or bool(self.lineage_ids())
            or _is_verifiable_id(self.job_id)
        )


@dataclass(frozen=True)
class CorrelationDecision:
    decision: str
    reason: str
    inherit_incident: bool


@dataclass(frozen=True)
class GateDecision:
    allow: bool
    reason: str
    state: str = STATE_IN_SCOPE
    incident_id: str = ""
    entry: dict[str, Any] | None = None


def evaluate_observed(manifest: ScopeManifest | None, observed: ObservedAction) -> GateDecision:
    if manifest is None:
        return GateDecision(allow=False, reason=REASON_MANIFEST_MISSING, state=STATE_BLOCKED)
    if observed.tool and observed.tool not in manifest.tools:
        return GateDecision(allow=False, reason=REASON_SCOPE_VIOLATION)
    if observed.action_key and observed.action_key not in manifest.action_keys:
        return GateDecision(allow=False, reason=REASON_SCOPE_VIOLATION)
    if observed.network_class and observed.network_class not in manifest.network_classes:
        return GateDecision(allow=False, reason=REASON_SCOPE_VIOLATION)
    if observed.path:
        relative = observed.path.replace("\\", "/").lstrip("/")
        prefixes = tuple(item.rstrip("/") for item in manifest.path_prefixes)
        if prefixes and not any(
            relative == prefix or relative.startswith(prefix + "/") for prefix in prefixes
        ):
            return GateDecision(allow=False, reason=REASON_SCOPE_VIOLATION)
    return GateDecision(allow=True, reason=REASON_IN_SCOPE, state=STATE_IN_SCOPE)


def correlate_reentry(
    prior: WorkloadIdentity, incoming: WorkloadIdentity
) -> CorrelationDecision:
    """Önceki incident'ı miras alıp almayacağına fail-closed karar verir.

    Yalnız subject_id + agent_id eşleşmesi **miras vermez**.
    """
    if prior.subject_id.strip() != incoming.subject_id.strip():
        return CorrelationDecision(NO_INHERIT, REASON_SUBJECT_MISMATCH, False)
    if prior.agent_id.strip() != incoming.agent_id.strip():
        return CorrelationDecision(NO_INHERIT, REASON_AGENT_MISMATCH, False)
    if not prior.has_verifiable_lineage() or not incoming.has_verifiable_lineage():
        return CorrelationDecision(NO_INHERIT, REASON_IDENTITY_UNVERIFIED, False)

    session_match = (
        _is_verifiable_id(prior.session_id)
        and _is_verifiable_id(incoming.session_id)
        and prior.session_id.strip() == incoming.session_id.strip()
    )
    session_conflict = (
        _is_verifiable_id(prior.session_id)
        and _is_verifiable_id(incoming.session_id)
        and prior.session_id.strip() != incoming.session_id.strip()
    )
    lease_match = bool(prior.lineage_ids() & incoming.lineage_ids())
    job_match = (
        _is_verifiable_id(prior.job_id)
        and _is_verifiable_id(incoming.job_id)
        and prior.job_id.strip() == incoming.job_id.strip()
    )

    if session_match:
        return CorrelationDecision(CORRELATE, REASON_CORRELATED_SESSION, True)
    if lease_match:
        return CorrelationDecision(CORRELATE, REASON_CORRELATED_LEASE, True)
    if job_match:
        return CorrelationDecision(CORRELATE, REASON_CORRELATED_JOB, True)
    if session_conflict:
        return CorrelationDecision(NO_INHERIT, REASON_SESSION_CONFLICT, False)
    return CorrelationDecision(NO_INHERIT, REASON_IDENTITY_UNVERIFIED, False)


def _redact_path(path: str) -> str:
    name = Path(str(path or "").replace("\\", "/")).name
    return name[:80] if name else ""


def telemetry_record(observed: ObservedAction, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(extra or {})
    leaked = sorted(key for key in payload if key.lower() in _TELEMETRY_FORBIDDEN_KEYS)
    for key in leaked:
        payload.pop(key, None)
    path = observed.path.replace("\\", "/").lstrip("/")
    record = {
        "tool": observed.tool,
        "action_key": observed.action_key,
        "task_op": observed.task_op,
        "path_basename": _redact_path(path),
        "path_hash": _sha256_hex(path) if path else "",
        "network_class": observed.network_class,
    }
    record.update(payload)
    if "intent" in record:
        raise ValueError(REASON_INTENT_FORBIDDEN)
    return record


def score_behavior(signals: Mapping[str, int | bool]) -> dict[str, Any]:
    """Davranış zinciri bandı. Niyet hükmü yok."""
    if "intent" in signals or "intentional" in signals or "kasıtlı" in signals:
        raise ValueError(REASON_INTENT_FORBIDDEN)
    scope_distance = int(signals.get("scope_distance") or 0)
    persistence = bool(signals.get("persistence_after_recall"))
    grant_deviation = bool(signals.get("grant_deviation"))
    privilege = bool(signals.get("privilege_seeking"))
    returned = bool(signals.get("return_after_recall"))
    band = 0
    if scope_distance > 0:
        band = 1
    if persistence:
        band = max(band, 2)
    if grant_deviation or privilege:
        band = max(band, 3)
    if persistence and (grant_deviation or privilege):
        band = 4
    if returned and band <= 2:
        band = min(band, 1)
    return {"band": band, "classification": "unclassified"}


def handling_tag_effects(tag: str) -> dict[str, Any]:
    allowed = sorted(_LABEL_MAY)
    forbidden = sorted(_LABEL_MUST_NOT)
    active = allowed if tag == "malicious_behavior_suspected" else []
    return {
        "tag": tag,
        "may": active,
        "must_not": forbidden,
        "chase": False,
        "never_auto": False,
        "standing_merge": False,
    }


def watcher_may(action_key: str) -> GateDecision:
    if action_key in WATCHER_ALLOWED_ACTIONS:
        return GateDecision(allow=True, reason=ACTION_OBSERVE, state=STATE_WATCHING)
    return GateDecision(
        allow=False,
        reason=REASON_WATCHER_WRITE,
        state=STATE_FAIL_CLOSED_BLOCK,
    )


def chase_after_exit(_host: str) -> GateDecision:
    return GateDecision(allow=False, reason=REASON_CHASE_FORBIDDEN, state=STATE_SURFACE_EXIT)


def load_ledger_entries(base_dir: Path | str | None = None) -> list[dict[str, Any]]:
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    path = base / LEDGER_REL
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return []
        if not isinstance(row, dict):
            return []
        out.append(row)
    return out


def verify_ledger_chain(base_dir: Path | str | None = None) -> bool:
    prev = GENESIS_HASH
    rows = load_ledger_entries(base_dir)
    path = (
        Path(base_dir).resolve() / LEDGER_REL
        if base_dir is not None
        else lumos_base_dir() / LEDGER_REL
    )
    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError:
                return False
    for row in rows:
        stored = str(row.get("entry_hash") or "")
        body = {k: v for k, v in row.items() if k != "entry_hash"}
        if str(body.get("prev_hash") or "") != prev:
            return False
        payload_digest = _sha256_hex(_canonical(body))
        expected = _sha256_hex(prev + payload_digest)
        if stored != expected:
            return False
        prev = stored
    return True


def _read_tip(base: Path) -> str:
    tip = base / LEDGER_TIP_REL
    if not tip.is_file():
        return GENESIS_HASH
    text = tip.read_text(encoding="utf-8").strip()
    return text or GENESIS_HASH


def _append_ledger(base: Path, body: dict[str, Any]) -> dict[str, Any]:
    if "intent" in body:
        raise ValueError(REASON_INTENT_FORBIDDEN)

    def _append_locked() -> dict[str, Any]:
        prev = _read_tip(base)
        record = dict(body)
        record["schema_version"] = SCHEMA_LEDGER
        record["at"] = record.get("at") or _now_iso()
        record["prev_hash"] = prev
        canonical = _canonical(record)
        payload_digest = _sha256_hex(canonical)
        entry_hash = _sha256_hex(prev + payload_digest)
        record["entry_hash"] = entry_hash
        path = base / LEDGER_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        tip = base / LEDGER_TIP_REL
        tip.parent.mkdir(parents=True, exist_ok=True)
        tip.write_text(entry_hash + "\n", encoding="utf-8")
        return record

    ledger_path = base / LEDGER_REL
    try:
        return _with_sidecar_lock(ledger_path.with_name(f"{ledger_path.name}.lock"), _append_locked)
    except OSError as exc:
        raise RuntimeError(REASON_SINK_UNAVAILABLE) from exc


def latest_incident_state(incident_id: str, base_dir: Path | str | None = None) -> str:
    state = ""
    for row in load_ledger_entries(base_dir):
        if str(row.get("incident_id") or "") == incident_id:
            state = str(row.get("state") or state)
    return state


def open_incident(
    identity: WorkloadIdentity,
    manifest: ScopeManifest,
    observed: ObservedAction,
    *,
    base_dir: Path | str | None = None,
) -> GateDecision:
    if "intent" in manifest.as_dict():
        return GateDecision(allow=False, reason=REASON_INTENT_FORBIDDEN, state=STATE_BLOCKED)
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    incident_id = uuid.uuid4().hex[:16]
    body = {
        "event_type": EVENT_OPEN,
        "state": STATE_INCIDENT_OPEN,
        "incident_id": incident_id,
        "incident_schema": SCHEMA_INCIDENT,
        "subject_id": identity.subject_id,
        "agent_id": identity.agent_id,
        "session_id": identity.session_id,
        "claim_id": identity.claim_id,
        "lease_lineage": list(identity.lease_lineage),
        "job_id": identity.job_id,
        "manifest_sha256": manifest_sha256(manifest),
        "telemetry": telemetry_record(observed),
        "classification": "unclassified",
    }
    try:
        entry = _append_ledger(base, body)
    except (OSError, RuntimeError):
        return GateDecision(
            allow=False,
            reason=REASON_SINK_UNAVAILABLE,
            state=STATE_FAIL_CLOSED_BLOCK,
        )
    return GateDecision(
        allow=False,
        reason=REASON_SCOPE_VIOLATION,
        state=STATE_INCIDENT_OPEN,
        incident_id=incident_id,
        entry=entry,
    )


def issue_recall(incident_id: str, *, base_dir: Path | str | None = None) -> GateDecision:
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    state = latest_incident_state(incident_id, base)
    if state != STATE_INCIDENT_OPEN:
        return GateDecision(allow=False, reason=REASON_RECALL_REQUIRED, state=state or STATE_BLOCKED)
    entry = _append_ledger(
        base,
        {
            "event_type": EVENT_RECALL,
            "state": STATE_RECALL_ISSUED,
            "incident_id": incident_id,
        },
    )
    return GateDecision(
        allow=False,
        reason=EVENT_RECALL,
        state=STATE_RECALL_ISSUED,
        incident_id=incident_id,
        entry=entry,
    )


def note_returned(incident_id: str, *, base_dir: Path | str | None = None) -> GateDecision:
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    state = latest_incident_state(incident_id, base)
    if state != STATE_RECALL_ISSUED:
        return GateDecision(allow=False, reason=REASON_RECALL_REQUIRED, state=state or STATE_BLOCKED)
    entry = _append_ledger(
        base,
        {
            "event_type": EVENT_RETURNED,
            "state": STATE_RETURNED,
            "incident_id": incident_id,
        },
    )
    return GateDecision(
        allow=True,
        reason=EVENT_RETURNED,
        state=STATE_RETURNED,
        incident_id=incident_id,
        entry=entry,
    )


def arm_watch(
    incident_id: str,
    *,
    observe_granted: bool,
    base_dir: Path | str | None = None,
) -> GateDecision:
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    state = latest_incident_state(incident_id, base)
    if state != STATE_RECALL_ISSUED:
        return GateDecision(
            allow=False,
            reason=REASON_RECALL_REQUIRED,
            state=STATE_FAIL_CLOSED_BLOCK,
            incident_id=incident_id,
        )
    if not observe_granted:
        entry = _append_ledger(
            base,
            {
                "event_type": EVENT_BLOCK,
                "state": STATE_FAIL_CLOSED_BLOCK,
                "incident_id": incident_id,
                "reason": REASON_OBSERVE_GRANT_MISSING,
            },
        )
        return GateDecision(
            allow=False,
            reason=REASON_OBSERVE_GRANT_MISSING,
            state=STATE_FAIL_CLOSED_BLOCK,
            incident_id=incident_id,
            entry=entry,
        )
    entry = _append_ledger(
        base,
        {
            "event_type": EVENT_WATCHING,
            "state": STATE_WATCHING,
            "incident_id": incident_id,
            "watcher_action": ACTION_OBSERVE,
        },
    )
    return GateDecision(
        allow=True,
        reason=ACTION_OBSERVE,
        state=STATE_WATCHING,
        incident_id=incident_id,
        entry=entry,
    )


def record_telemetry(
    incident_id: str,
    observed: ObservedAction,
    extra: Mapping[str, Any] | None = None,
    *,
    base_dir: Path | str | None = None,
) -> GateDecision:
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    state = latest_incident_state(incident_id, base)
    if state != STATE_WATCHING:
        return GateDecision(allow=False, reason=REASON_RECALL_REQUIRED, state=state or STATE_BLOCKED)
    try:
        payload = telemetry_record(observed, extra)
    except ValueError as exc:
        return GateDecision(allow=False, reason=str(exc), state=STATE_WATCHING)
    entry = _append_ledger(
        base,
        {
            "event_type": EVENT_TELEMETRY,
            "state": STATE_WATCHING,
            "incident_id": incident_id,
            "telemetry": payload,
        },
    )
    return GateDecision(
        allow=True,
        reason=EVENT_TELEMETRY,
        state=STATE_WATCHING,
        incident_id=incident_id,
        entry=entry,
    )


def surface_exit(incident_id: str, *, base_dir: Path | str | None = None) -> GateDecision:
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    state = latest_incident_state(incident_id, base)
    if state != STATE_WATCHING:
        return GateDecision(allow=False, reason=REASON_RECALL_REQUIRED, state=state or STATE_BLOCKED)
    entry = _append_ledger(
        base,
        {
            "event_type": EVENT_SURFACE_EXIT,
            "state": STATE_SURFACE_EXIT,
            "incident_id": incident_id,
            "chase": False,
        },
    )
    return GateDecision(
        allow=False,
        reason=EVENT_SURFACE_EXIT,
        state=STATE_SURFACE_EXIT,
        incident_id=incident_id,
        entry=entry,
    )


def on_scope_violation(
    identity: WorkloadIdentity,
    manifest: ScopeManifest | None,
    observed: ObservedAction,
    *,
    base_dir: Path | str | None = None,
) -> GateDecision:
    """Sapmada incident + recall. Watch spawn etmez."""
    verdict = evaluate_observed(manifest, observed)
    if verdict.allow:
        return verdict
    if verdict.reason == REASON_MANIFEST_MISSING or manifest is None:
        return GateDecision(allow=False, reason=REASON_MANIFEST_MISSING, state=STATE_BLOCKED)
    opened = open_incident(identity, manifest, observed, base_dir=base_dir)
    if opened.state == STATE_FAIL_CLOSED_BLOCK:
        return opened
    recalled = issue_recall(opened.incident_id, base_dir=base_dir)
    return GateDecision(
        allow=False,
        reason=REASON_SCOPE_VIOLATION,
        state=recalled.state,
        incident_id=opened.incident_id,
        entry=recalled.entry,
    )


__all__ = (
    "ACTION_OBSERVE",
    "CORRELATE",
    "NO_INHERIT",
    "ObservedAction",
    "ScopeManifest",
    "WorkloadIdentity",
    "arm_watch",
    "chase_after_exit",
    "correlate_reentry",
    "evaluate_observed",
    "handling_tag_effects",
    "issue_recall",
    "manifest_sha256",
    "note_returned",
    "on_scope_violation",
    "open_incident",
    "record_telemetry",
    "score_behavior",
    "surface_exit",
    "telemetry_record",
    "verify_ledger_chain",
    "watcher_may",
)
