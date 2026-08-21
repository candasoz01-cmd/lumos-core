"""
ADR-031 — üç parça, tek kapı:

    1. Task Registry     — kabul edilmiş görevin resmi kaydı
    2. Capability Token  — göreve özel, kısa ömürlü, tek kullanımlık anahtar
    3. Immutable Ledger  — denemelerin hash-zincirli izi (kanıt; kapı değil)

Kapıyı kapatan şey registry + capability + policy'dir. Defter allow/deny
kararı vermez. Ajan anahtar üretmez; kullanıcıdan da istenmez. Görev kabul
edilince merkezi Task Authority üretir.

Varsayılan enforcement kapalı: LUMOS_TASK_EXECUTION_GRANT_ENABLED.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from core.lumos_base_dir import lumos_base_dir

SCHEMA_VERSION = "lumos.task_execution_grant.v1"
SCHEMA_GRANT = SCHEMA_VERSION
SCHEMA_REGISTRY = "lumos.task_registry.v1"
SCHEMA_LEDGER = "lumos.execution_ledger.v1"
GRANTS_DIR = "task_execution_grants"
REGISTRY_DIR = "task_registry"
AUDIT_REL = Path("ledgers") / "execution_ledger.jsonl"
LEDGER_REL = AUDIT_REL
LEDGER_TIP_REL = Path("ledgers") / "execution_ledger.tip"
TOKEN_PREFIX = "teg1"
DEFAULT_TTL_SECONDS = 120
MAX_TTL_SECONDS = 900
GRANT_ID_RE = re.compile(r"^[a-f0-9]{16}$")
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
GENESIS_HASH = "0" * 64
BINDING_FIELDS = (
    "subject_id",
    "agent_id",
    "session_id",
    "task_id",
    "action_key",
    "resource",
    "permission",
)

REASON_DISABLED = "task_execution_grant_disabled"
REASON_REQUIRED = "task_execution_grant_required"
REASON_MISSING = "task_execution_grant_missing"
REASON_MALFORMED = "task_execution_grant_malformed"
REASON_UNKNOWN = "task_execution_grant_unknown"
REASON_UNKNOWN_TASK = "task_execution_grant_unknown_task"
REASON_KEY_NOT_REGISTERED = "task_execution_grant_key_not_registered"
REASON_EXPIRED = "task_execution_grant_expired"
REASON_USED = "task_execution_grant_used"
REASON_MISMATCH = "task_execution_grant_mismatch"
REASON_BINDING_INCOMPLETE = "task_execution_grant_binding_incomplete"
REASON_IDENTITY_MISSING = "task_execution_grant_identity_missing"
REASON_SURFACE_BLOCKED = "task_execution_grant_surface_blocked"
REASON_INVALID_TTL = "task_execution_grant_invalid_ttl"
REASON_DUPLICATE_TASK = "task_execution_grant_duplicate_task"

SUSPICION_NONE = "none"
SUSPICION_MEDIUM = "medium"
SUSPICION_HIGH = "high"

CLASSIFICATION_NONE = ""
CLASSIFICATION_UNCLASSIFIED = "unclassified"

KIND_NONE = ""
KIND_MISSING_IDENTITY = "missing_identity"
KIND_UNKNOWN_TASK = "unknown_task"
KIND_UNREGISTERED_KEY = "unregistered_key"
KIND_CAPABILITY_DEVIATION = "capability_deviation"
KIND_REPLAY = "replay"
KIND_EXPIRED = "expired"
KIND_SURFACE_BLOCKED = "surface_blocked"

EVENT_ACCEPTED = "execution_task_accepted"
EVENT_ISSUED = "execution_capability_issued"
EVENT_CONSUMED = "execution_authorized"
EVENT_DENIED = "execution_denied"

ENV_ENABLED = "LUMOS_TASK_EXECUTION_GRANT_ENABLED"


@dataclass(frozen=True)
class ExecutionBinding:
    subject_id: str
    task_id: str
    action_key: str
    resource: str
    permission: str
    agent_id: str = "agent:unspecified"
    session_id: str = "session:unspecified"

    def __post_init__(self) -> None:
        for field_name in BINDING_FIELDS:
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{field_name} required")
        if not TASK_ID_RE.match(self.task_id):
            raise ValueError("task_id required")


@dataclass(frozen=True)
class IssuedGrant:
    grant_id: str
    token: str
    binding: ExecutionBinding
    binding_hash: str
    expires_at: str
    token_hash: str


@dataclass(frozen=True)
class GrantResult:
    allowed: bool
    reason: str = ""
    suspicion: str = SUSPICION_NONE
    classification: str = CLASSIFICATION_NONE
    grant_id: str = ""
    event_kind: str = KIND_NONE


def is_task_execution_grant_enabled() -> bool:
    raw = (os.environ.get(ENV_ENABLED) or "").strip().lower()
    return raw in ("1", "true", "yes")


def binding_hash(binding: ExecutionBinding) -> str:
    payload = json.dumps(
        {name: getattr(binding, name) for name in BINDING_FIELDS},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def action_is_grant_forbidden(action_key: str) -> bool:
    from task_engine.profiles import is_security_never_auto

    key = (action_key or "").strip()
    if not key:
        return True
    return is_security_never_auto(action_key=key, policy_action=key)


def binding_from_mapping(
    data: Mapping[str, Any],
    *,
    norm: Mapping[str, Any] | None = None,
) -> ExecutionBinding | None:
    """Gate bundle / test dict → bağ; eksik alanda None (fail-closed)."""
    subject_id = str(data.get("subject_id") or data.get("actor_id") or "").strip()
    if not subject_id:
        return None
    task_id = str(data.get("task_id") or "").strip()
    action_key = str(
        data.get("task_execution_action_key") or data.get("action_key") or ""
    ).strip()
    resource = ""
    nested = norm if norm is not None else data.get("norm")
    if isinstance(nested, Mapping):
        resource = str(nested.get("target_rel") or nested.get("resource") or "").strip()
    if not resource:
        resource = str(data.get("resource") or "").strip()
    permission = str(
        data.get("task_execution_permission") or data.get("permission") or "execute"
    ).strip()
    agent_id = str(data.get("agent_id") or "agent:unspecified").strip() or "agent:unspecified"
    session_id = str(data.get("session_id") or "session:unspecified").strip() or "session:unspecified"
    if not (task_id and action_key and resource and permission):
        return None
    try:
        return ExecutionBinding(
            subject_id=subject_id,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            action_key=action_key,
            resource=resource,
            permission=permission,
        )
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str) -> datetime | None:
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def _grants_dir(base: Path | None) -> Path:
    root = base if base is not None else lumos_base_dir()
    return root / GRANTS_DIR


def _grant_path(base: Path, grant_id: str) -> Path:
    if not GRANT_ID_RE.match(grant_id):
        raise ValueError("invalid grant_id")
    return _grants_dir(base) / f"{grant_id}.json"


def _atomic_write_json(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _audit_path(base: Path) -> Path:
    return base / AUDIT_REL


def _resource_audit_label(resource: str) -> str:
    name = Path(str(resource or "").strip()).name
    return name[:80] if name else "[REDACTED_PATH]"


def _hashes_equal(left: str, right: str) -> bool:
    a = (left or "").encode("utf-8")
    b = (right or "").encode("utf-8")
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def _registry_path(base: Path, task_id: str) -> Path:
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")
    safe = task_id.replace(":", "_")
    return base / REGISTRY_DIR / f"{safe}.json"


def load_registered_task(task_id: str, *, base_dir: Path | str | None = None) -> dict[str, Any] | None:
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    try:
        path = _registry_path(base, task_id)
    except ValueError:
        return None
    record = _load_json(path)
    if record is None or str(record.get("task_id") or "") != task_id:
        return None
    return record


def _read_tip(base: Path) -> str:
    path = base / LEDGER_TIP_REL
    if not path.is_file():
        return GENESIS_HASH
    tip = path.read_text(encoding="utf-8").strip()
    return tip if len(tip) == 64 else GENESIS_HASH


def append_ledger_entry(
    base: Path,
    event_type: str,
    *,
    grant_id: str = "",
    action_key: str = "",
    requested_action: str = "",
    task_id: str = "",
    subject_id: str = "",
    agent_id: str = "",
    session_id: str = "",
    resource: str = "",
    permission: str = "",
    reason: str = "",
    suspicion: str = SUSPICION_NONE,
    classification: str = CLASSIFICATION_NONE,
    event_kind: str = KIND_NONE,
    token_digest: str = "",
    policy_decision: str = "",
    approval_status: str = "",
    execution_result: str = "",
) -> dict[str, Any]:
    prev = _read_tip(base)
    body = {
        "schema_version": SCHEMA_LEDGER,
        "event_type": event_type,
        "at": _now_iso(),
        "grant_id": grant_id,
        "subject_id": subject_id,
        "agent_id": agent_id,
        "session_id": session_id,
        "task_id": task_id,
        "granted_action": action_key,
        "requested_action": requested_action or action_key,
        "resource": _resource_audit_label(resource),
        "permission": permission,
        "policy_decision": policy_decision,
        "approval_status": approval_status,
        "execution_result": execution_result or event_type,
        "reason": reason,
        "suspicion": suspicion,
        "classification": classification,
        "event_kind": event_kind,
        "token_hash": token_digest,
        "prev_hash": prev,
    }
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    entry_hash = hashlib.sha256((prev + payload_digest).encode("utf-8")).hexdigest()
    body["entry_hash"] = entry_hash
    path = base / LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
    tip = base / LEDGER_TIP_REL
    tip.parent.mkdir(parents=True, exist_ok=True)
    tip.write_text(entry_hash + "\n", encoding="utf-8")
    return body


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
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def verify_ledger_chain(base_dir: Path | str | None = None) -> bool:
    prev = GENESIS_HASH
    for row in load_ledger_entries(base_dir):
        stored = str(row.get("entry_hash") or "")
        body = {k: v for k, v in row.items() if k != "entry_hash"}
        if str(body.get("prev_hash") or "") != prev:
            return False
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        expected = hashlib.sha256((prev + payload_digest).encode("utf-8")).hexdigest()
        if stored != expected:
            return False
        prev = stored
    return True


def append_grant_audit(
    base: Path,
    event_type: str,
    *,
    grant_id: str = "",
    action_key: str = "",
    task_id: str = "",
    subject_id: str = "",
    resource: str = "",
    permission: str = "",
    reason: str = "",
    suspicion: str = SUSPICION_NONE,
    classification: str = CLASSIFICATION_NONE,
    token_digest: str = "",
    agent_id: str = "",
    session_id: str = "",
    event_kind: str = KIND_NONE,
    requested_action: str = "",
    policy_decision: str = "",
    approval_status: str = "",
    execution_result: str = "",
) -> None:
    append_ledger_entry(
        base,
        event_type,
        grant_id=grant_id,
        action_key=action_key,
        requested_action=requested_action,
        task_id=task_id,
        subject_id=subject_id,
        agent_id=agent_id,
        session_id=session_id,
        resource=resource,
        permission=permission,
        reason=reason,
        suspicion=suspicion,
        classification=classification,
        event_kind=event_kind,
        token_digest=token_digest,
        policy_decision=policy_decision,
        approval_status=approval_status,
        execution_result=execution_result,
    )


def _parse_token(token: str) -> tuple[str, str] | None:
    raw = (token or "").strip()
    parts = raw.split(".", 2)
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        return None
    grant_id, secret = parts[1], parts[2]
    if not GRANT_ID_RE.match(grant_id) or not secret:
        return None
    return grant_id, raw


def _deny(
    reason: str,
    *,
    suspicion: str,
    event_kind: str = KIND_NONE,
    grant_id: str = "",
    base: Path | None = None,
    binding: ExecutionBinding | None = None,
    token_digest: str = "",
    requested_action: str = "",
    audit: bool = True,
) -> GrantResult:
    result = GrantResult(
        allowed=False,
        reason=reason,
        suspicion=suspicion,
        classification=CLASSIFICATION_UNCLASSIFIED,
        grant_id=grant_id,
        event_kind=event_kind,
    )
    if audit and base is not None:
        append_grant_audit(
            base,
            EVENT_DENIED,
            grant_id=grant_id,
            action_key=binding.action_key if binding else "",
            requested_action=requested_action or (binding.action_key if binding else ""),
            task_id=binding.task_id if binding else "",
            subject_id=binding.subject_id if binding else "",
            agent_id=binding.agent_id if binding else "",
            session_id=binding.session_id if binding else "",
            resource=binding.resource if binding else "",
            permission=binding.permission if binding else "",
            reason=reason,
            suspicion=suspicion,
            classification=CLASSIFICATION_UNCLASSIFIED,
            event_kind=event_kind,
            token_digest=token_digest,
            execution_result="denied",
        )
    return result


def _kind_for_reason(reason: str) -> str:
    return {
        REASON_IDENTITY_MISSING: KIND_MISSING_IDENTITY,
        REASON_UNKNOWN_TASK: KIND_UNKNOWN_TASK,
        REASON_KEY_NOT_REGISTERED: KIND_UNREGISTERED_KEY,
        REASON_MISMATCH: KIND_CAPABILITY_DEVIATION,
        REASON_USED: KIND_REPLAY,
        REASON_EXPIRED: KIND_EXPIRED,
        REASON_SURFACE_BLOCKED: KIND_SURFACE_BLOCKED,
        REASON_MISSING: KIND_UNREGISTERED_KEY,
        REASON_UNKNOWN: KIND_UNREGISTERED_KEY,
        REASON_MALFORMED: KIND_UNREGISTERED_KEY,
    }.get(reason, KIND_NONE)


def issue_task_execution_grant(
    binding: ExecutionBinding,
    *,
    base_dir: Path | str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> IssuedGrant:
    """Yalnız Task Authority kabul yolu. Ajan/kullanıcı mint etmez."""
    return accept_execution_task(binding, base_dir=base_dir, ttl_seconds=ttl_seconds)


def accept_execution_task(
    binding: ExecutionBinding,
    *,
    base_dir: Path | str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    policy_decision: str = "allow",
    approval_status: str = "not_required",
) -> IssuedGrant:
    if not binding.subject_id.strip():
        raise ValueError(REASON_IDENTITY_MISSING)
    if action_is_grant_forbidden(binding.action_key):
        raise ValueError(REASON_SURFACE_BLOCKED)
    ttl = int(ttl_seconds)
    if ttl < 1 or ttl > MAX_TTL_SECONDS:
        raise ValueError(REASON_INVALID_TTL)
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    path = _registry_path(base, binding.task_id)
    if _load_json(path) is not None:
        raise ValueError(REASON_DUPLICATE_TASK)
    _atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_REGISTRY,
            "task_id": binding.task_id,
            "subject_id": binding.subject_id,
            "agent_id": binding.agent_id,
            "session_id": binding.session_id,
            "action_key": binding.action_key,
            "resource": binding.resource,
            "permission": binding.permission,
            "binding_hash": binding_hash(binding),
            "grant_id": "",
            "token_hash": "",
            "status": "accepted",
            "created_at": _now_iso(),
        },
    )
    grant_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(32)
    token = f"{TOKEN_PREFIX}.{grant_id}.{secret}"
    digest = token_hash(token)
    bind_h = binding_hash(binding)
    expires = _now() + timedelta(seconds=ttl)
    expires_at = expires.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    record = {
        "schema_version": SCHEMA_GRANT,
        "grant_id": grant_id,
        "token_hash": digest,
        "subject_id": binding.subject_id,
        "agent_id": binding.agent_id,
        "session_id": binding.session_id,
        "task_id": binding.task_id,
        "action_key": binding.action_key,
        "resource": binding.resource,
        "permission": binding.permission,
        "binding_hash": bind_h,
        "created_at": _now_iso(),
        "expires_at": expires_at,
        "consumed": False,
        "consumed_at": None,
    }
    _atomic_write_json(_grant_path(base, grant_id), record)
    registered = _load_json(path) or {}
    registered["grant_id"] = grant_id
    registered["token_hash"] = digest
    _atomic_write_json(path, registered)
    for event_type, result_label in (
        (EVENT_ACCEPTED, "accepted"),
        (EVENT_ISSUED, "issued"),
    ):
        append_grant_audit(
            base,
            event_type,
            grant_id=grant_id,
            action_key=binding.action_key,
            task_id=binding.task_id,
            subject_id=binding.subject_id,
            agent_id=binding.agent_id,
            session_id=binding.session_id,
            resource=binding.resource,
            permission=binding.permission,
            token_digest=digest,
            policy_decision=policy_decision,
            approval_status=approval_status,
            execution_result=result_label,
        )
    return IssuedGrant(
        grant_id=grant_id,
        token=token,
        binding=binding,
        binding_hash=bind_h,
        expires_at=expires_at,
        token_hash=digest,
    )


def _record_binding(record: Mapping[str, Any]) -> ExecutionBinding | None:
    try:
        return ExecutionBinding(
            subject_id=str(record.get("subject_id") or "").strip(),
            agent_id=str(record.get("agent_id") or "agent:unspecified").strip() or "agent:unspecified",
            session_id=str(record.get("session_id") or "session:unspecified").strip()
            or "session:unspecified",
            task_id=str(record.get("task_id") or "").strip(),
            action_key=str(record.get("action_key") or "").strip(),
            resource=str(record.get("resource") or "").strip(),
            permission=str(record.get("permission") or "").strip(),
        )
    except ValueError:
        return None


def _validate_record(
    record: Mapping[str, Any],
    *,
    token: str,
    expected: ExecutionBinding,
) -> tuple[str, str] | None:
    """None = geçerli; aksi halde (reason, suspicion)."""
    if action_is_grant_forbidden(expected.action_key):
        return REASON_SURFACE_BLOCKED, SUSPICION_HIGH
    stored = _record_binding(record)
    if stored is None:
        return REASON_MALFORMED, SUSPICION_HIGH
    if action_is_grant_forbidden(stored.action_key):
        return REASON_SURFACE_BLOCKED, SUSPICION_HIGH
    if binding_hash(stored) != binding_hash(expected):
        return REASON_MISMATCH, SUSPICION_HIGH
    if not _hashes_equal(str(record.get("token_hash") or ""), token_hash(token)):
        return REASON_KEY_NOT_REGISTERED, SUSPICION_HIGH
    if bool(record.get("consumed")):
        return REASON_USED, SUSPICION_HIGH
    expires_at = record.get("expires_at")
    if isinstance(expires_at, str):
        exp = _parse_iso(expires_at)
        if exp is not None and _now() > exp:
            return REASON_EXPIRED, SUSPICION_MEDIUM
    return None


def consume_task_execution_grant(
    token: str,
    expected: ExecutionBinding,
    *,
    base_dir: Path | str | None = None,
    audit: bool = True,
) -> GrantResult:
    """Executor kapısı: kayıtlı görev zincirine bağlanmayan işlem yürümez."""
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    if not expected.subject_id.strip():
        return _deny(
            REASON_IDENTITY_MISSING,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_MISSING_IDENTITY,
            base=base,
            binding=expected,
            audit=audit,
        )
    registered = load_registered_task(expected.task_id, base_dir=base)
    if registered is None:
        return _deny(
            REASON_UNKNOWN_TASK,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_UNKNOWN_TASK,
            base=base,
            binding=expected,
            audit=audit,
        )
    raw = (token or "").strip()
    if not raw:
        return _deny(
            REASON_MISSING,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_UNREGISTERED_KEY,
            base=base,
            binding=expected,
            audit=audit,
        )
    parsed = _parse_token(raw)
    if parsed is None:
        return _deny(
            REASON_MALFORMED,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_UNREGISTERED_KEY,
            base=base,
            binding=expected,
            token_digest=token_hash(raw),
            audit=audit,
        )
    grant_id, full_token = parsed
    digest = token_hash(full_token)
    registered_hash = str(registered.get("token_hash") or "")
    registered_grant = str(registered.get("grant_id") or "")
    if not registered_hash or not _hashes_equal(registered_hash, digest) or (
        registered_grant and registered_grant != grant_id
    ):
        return _deny(
            REASON_KEY_NOT_REGISTERED,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_UNREGISTERED_KEY,
            grant_id=grant_id,
            base=base,
            binding=expected,
            token_digest=digest,
            audit=audit,
        )
    try:
        path = _grant_path(base, grant_id)
    except ValueError:
        return _deny(
            REASON_MALFORMED,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_UNREGISTERED_KEY,
            grant_id=grant_id,
            base=base,
            binding=expected,
            token_digest=digest,
            audit=audit,
        )

    try:
        import fcntl
    except ImportError:
        fcntl = None  # type: ignore[assignment]

    if fcntl is not None:
        lock_path = path.with_name(f"{path.name}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                return _consume_locked(
                    path,
                    full_token,
                    expected,
                    base=base,
                    grant_id=grant_id,
                    digest=digest,
                    audit=audit,
                )
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    return _consume_locked(
        path,
        full_token,
        expected,
        base=base,
        grant_id=grant_id,
        digest=digest,
        audit=audit,
    )


def _consume_locked(
    path: Path,
    token: str,
    expected: ExecutionBinding,
    *,
    base: Path,
    grant_id: str,
    digest: str,
    audit: bool,
) -> GrantResult:
    record = _load_json(path)
    if record is None:
        return _deny(
            REASON_UNKNOWN,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_UNREGISTERED_KEY,
            grant_id=grant_id,
            base=base,
            binding=expected,
            token_digest=digest,
            audit=audit,
        )
    failed = _validate_record(record, token=token, expected=expected)
    if failed is not None:
        reason, suspicion = failed
        return _deny(
            reason,
            suspicion=suspicion,
            event_kind=_kind_for_reason(reason),
            grant_id=grant_id,
            base=base,
            binding=expected,
            token_digest=digest,
            requested_action=expected.action_key,
            audit=audit,
        )
    record["consumed"] = True
    record["consumed_at"] = _now_iso()
    _atomic_write_json(path, record)
    if audit:
        append_grant_audit(
            base,
            EVENT_CONSUMED,
            grant_id=grant_id,
            action_key=expected.action_key,
            task_id=expected.task_id,
            subject_id=expected.subject_id,
            agent_id=expected.agent_id,
            session_id=expected.session_id,
            resource=expected.resource,
            permission=expected.permission,
            token_digest=digest,
            execution_result="authorized",
        )
    return GrantResult(allowed=True, grant_id=grant_id)


def require_task_execution_grant(
    token: str,
    expected: ExecutionBinding | None,
    *,
    base_dir: Path | str | None = None,
    subject_id: str | None = None,
) -> GrantResult:
    """Enforcement. Devre dışıyken no-op. Aktifken default deny."""
    if not is_task_execution_grant_enabled():
        return GrantResult(allowed=True, reason=REASON_DISABLED)
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    identity = str(subject_id or (expected.subject_id if expected else "") or "").strip()
    if not identity:
        return _deny(
            REASON_IDENTITY_MISSING,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_MISSING_IDENTITY,
            base=base,
            binding=expected,
            audit=True,
        )
    if expected is None:
        return _deny(
            REASON_BINDING_INCOMPLETE,
            suspicion=SUSPICION_HIGH,
            base=base,
            audit=True,
        )
    return consume_task_execution_grant(token, expected, base_dir=base)


def authorize_execution(
    token: str,
    *,
    subject_id: str,
    task_id: str,
    action_key: str,
    resource: str,
    permission: str,
    agent_id: str = "agent:unspecified",
    session_id: str = "session:unspecified",
    base_dir: Path | str | None = None,
) -> GrantResult:
    """Gate yüzeyi: kimlik yoksa executor'a inmeden red."""
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    if not str(subject_id or "").strip():
        return _deny(
            REASON_IDENTITY_MISSING,
            suspicion=SUSPICION_HIGH,
            event_kind=KIND_MISSING_IDENTITY,
            base=base,
            audit=True,
        )
    try:
        expected = ExecutionBinding(
            subject_id=str(subject_id).strip(),
            agent_id=str(agent_id or "agent:unspecified").strip() or "agent:unspecified",
            session_id=str(session_id or "session:unspecified").strip() or "session:unspecified",
            task_id=str(task_id).strip(),
            action_key=str(action_key).strip(),
            resource=str(resource).strip(),
            permission=str(permission).strip(),
        )
    except ValueError:
        return _deny(
            REASON_BINDING_INCOMPLETE,
            suspicion=SUSPICION_HIGH,
            base=base,
            audit=True,
        )
    return consume_task_execution_grant(token, expected, base_dir=base)


def denied_executor_result(result: GrantResult) -> dict[str, Any]:
    """Yürütme katmanına geçilmeden dönecek dar red gövdesi."""
    return {
        "ok": False,
        "blocked": True,
        "status": "denied",
        "execution_result": "task_execution_grant_denied",
        "reason": result.reason,
        "suspicion": result.suspicion,
        "classification": result.classification,
        "event_kind": result.event_kind,
        "grant_id": result.grant_id,
    }
