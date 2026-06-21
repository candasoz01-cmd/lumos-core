"""
CU4 confirmation policy infrastructure (PR-C1).

İşlem bazlı onay katmanı — consent ve general_approval'dan ayrı (ADR-010).
Varsayılan: devre dışı (LUMOS_CONFIRMATION_ENABLED yok/false → no-op).
Enforcement wiring: PR-C2 (delete-permanent), PR-C3 (panel mutasyonlar).
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from core.lumos_base_dir import lumos_base_dir

# Reason codes (PR-C0 sözleşmesi)
REASON_CONFIRMATION_REQUIRED = "confirmation_required"
REASON_CONFIRMATION_EXPIRED = "confirmation_expired"
REASON_SCOPE_MISMATCH = "scope_mismatch"
REASON_CONFIRMATION_DISABLED = "confirmation_disabled"

SCHEMA_VERSION = "lumos.confirmation.v1"
PENDING_CONFIRMATIONS_DIR = "pending_confirmations"
DEFAULT_TTL_SECONDS = 900

# Panel / CLI / CU operasyonları — confirmation gerektiren action_key kaydı
REQUIRES_CONFIRMATION_ACTIONS: frozenset[str] = frozenset({
    "create_task",
    "complete_task",
    "delete_task",
    "restore_task",
    "write_local",
    "delete_permanent",
    "external_write",
    "cu_act_click",
    "cu_act_type",
    "cu_act_navigate",
    "cu_act_send",
    "cu_act_purchase",
    "cu_act_delete",
    "cu_act_domain",
    "cu_act_email",
    "cu_act_file_send",
})

# Gelecek enforcement hook noktaları (PR-C2+ — şimdilik yalnızca işaret)
INTEGRATION_MARKERS: dict[str, str] = {
    "panel_delete_permanent": (
        "panel/scripts/panel_tasks_server.py::_post_delete_permanent — "
        "PR-C2: confirm=true → consume_confirmation('delete_permanent', scope)"
    ),
    "panel_task_mutations": (
        "panel/scripts/panel_tasks_server.py — POST /tasks, /complete, /delete, "
        "PUT /tasks.json, /restore — PR-C3: task_action_gate 3. kapı + confirmation_id"
    ),
    "panel_bridge_gate": (
        "src/core/panel_bridge_state.py::task_action_gate — "
        "PR-C3: check_confirmation after policy+profil"
    ),
    "cli_task_mutations": (
        "src/cli/cli_tasks_mutation.py — PR-C4: check_confirmation before persist"
    ),
    "external_cu_gateway": (
        "integrations / Computer Use act modu — PR-C5+: cu_act_* + external_write hooks"
    ),
    "bridge_pending_approval": (
        "packages/kando_runtime/lumos_gate.py pending_approval — "
        "PR-C6: köprü namespace hizalama (confirmation ≠ consent)"
    ),
}


@dataclass(frozen=True)
class ConfirmationResult:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class PendingConfirmation:
    confirmation_id: str
    action_key: str
    scope_hash: str
    preview: dict[str, Any]
    expires_at: str
    schema_version: str = SCHEMA_VERSION


def is_confirmation_enabled() -> bool:
    """LUMOS_CONFIRMATION_ENABLED=true|1|yes → aktif; aksi halde no-op."""
    raw = (os.environ.get("LUMOS_CONFIRMATION_ENABLED") or "").strip().lower()
    return raw in ("1", "true", "yes")


def requires_confirmation_for_action(action_key: str) -> bool:
    """action_key confirmation kaydında mı? (SECURITY_NEVER_AUTO ayrı katman.)"""
    return action_key in REQUIRES_CONFIRMATION_ACTIONS


def _pending_dir(base: Path | None = None) -> Path:
    root = base if base is not None else lumos_base_dir()
    return root / PENDING_CONFIRMATIONS_DIR


def _scope_hash(scope: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(scope), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str) -> datetime | None:
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def _grant_path(base: Path, confirmation_id: str) -> Path:
    safe_id = confirmation_id.replace("/", "").replace("\\", "").strip()
    return base / f"{safe_id}.json"


def _load_grant(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_grant(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def check_confirmation(
    action_key: str,
    scope: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> ConfirmationResult:
    """
    Confirmation kapısı. Devre dışıyken her zaman allowed=True (no-op).
    Aktifken REQUIRES_CONFIRMATION_ACTIONS için geçerli grant gerekir.
    """
    if not is_confirmation_enabled():
        return ConfirmationResult(True, REASON_CONFIRMATION_DISABLED)

    if not requires_confirmation_for_action(action_key):
        return ConfirmationResult(True, "")

    ctx = context or {}
    confirmation_id = str(ctx.get("confirmation_id") or "").strip()
    if not confirmation_id:
        return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)

    base_raw = ctx.get("base_dir")
    base = Path(str(base_raw)).resolve() if base_raw else None
    grant = _load_grant(_grant_path(_pending_dir(base), confirmation_id))
    if grant is None:
        return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)

    if grant.get("action_key") != action_key:
        return ConfirmationResult(False, REASON_SCOPE_MISMATCH)

    expected_hash = _scope_hash(scope)
    if grant.get("scope_hash") != expected_hash:
        return ConfirmationResult(False, REASON_SCOPE_MISMATCH)

    if grant.get("consumed"):
        return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)

    expires_at = grant.get("expires_at")
    if isinstance(expires_at, str):
        exp = _parse_iso(expires_at)
        if exp is not None and datetime.now(timezone.utc) > exp:
            return ConfirmationResult(False, REASON_CONFIRMATION_EXPIRED)

    return ConfirmationResult(True, "")


def request_confirmation(
    action_key: str,
    scope: Mapping[str, Any],
    preview: Mapping[str, Any] | None = None,
    *,
    base_dir: Path | str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> PendingConfirmation:
    """
    Bekleyen confirmation kaydı oluşturur (.lumos/pending_confirmations/<id>.json).
    Yalnızca test ve gelecek UI/CLI akışları için; enforcement PR-C2+.
    """
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    confirmation_id = uuid.uuid4().hex[:12]
    scope_h = _scope_hash(scope)
    created = datetime.now(timezone.utc)
    expires = created + timedelta(seconds=max(1, ttl_seconds))
    expires_at = expires.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    preview_payload = dict(preview or {})
    record = {
        "schema_version": SCHEMA_VERSION,
        "confirmation_id": confirmation_id,
        "action_key": action_key,
        "scope_hash": scope_h,
        "scope": dict(scope),
        "preview": preview_payload,
        "created_at": _now_iso(),
        "expires_at": expires_at,
        "consumed": False,
        "granted_by": None,
    }
    _write_grant(_grant_path(_pending_dir(base), confirmation_id), record)
    return PendingConfirmation(
        confirmation_id=confirmation_id,
        action_key=action_key,
        scope_hash=scope_h,
        preview=preview_payload,
        expires_at=expires_at,
    )


DELETE_PERMANENT_ACTION = "delete_permanent"


def panel_action_to_confirmation_key(
    action: str,
    *,
    full_doc_replace: bool = False,
    restore: bool = False,
) -> str:
    """
    Panel policy action → CU4 confirmation action_key (PR-C3).
    PUT /tasks.json → write_local; POST /tasks/restore → restore_task.
    """
    from policy.action_policy import COMPLETE_TASK, CREATE_TASK, DELETE_TASK

    if restore:
        return "restore_task"
    if action == CREATE_TASK and full_doc_replace:
        return "write_local"
    if action == CREATE_TASK:
        return "create_task"
    if action == COMPLETE_TASK:
        return "complete_task"
    if action == DELETE_TASK:
        return "delete_task"
    return action


def cli_action_to_confirmation_key(route: str) -> str | None:
    """CLI route → CU4 action_key (PR-C4)."""
    if route == "gorev_olustur":
        return "create_task"
    if route == "gorev_sil":
        return "delete_task"
    return None


def cli_mutation_confirmation_spec(
    route: str,
    args: list[str],
) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
    """CLI mutasyon route → action_key, scope, CU7 preview."""
    action_key = cli_action_to_confirmation_key(route)
    if action_key is None:
        return None
    if route == "gorev_olustur":
        title = (args[0] if args else "").strip()
        if not title:
            return None
        scope = {"title": title}
        preview = {
            "what": "create_task",
            "where": title,
            "effect": "local_task_create",
        }
        return action_key, scope, preview
    if route == "gorev_sil":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            return None
        scope = {"id": id_str}
        preview = {
            "what": "delete_task",
            "where": id_str,
            "effect": "local_task_soft_delete",
        }
        return action_key, scope, preview
    return None


def format_cli_confirmation_message(preview: Mapping[str, Any], confirmation_id: str) -> str:
    """CU7 önizleme metni + onayla komutu (CLI)."""
    what = str(preview.get("what") or "")
    where = str(preview.get("where") or "")
    effect = str(preview.get("effect") or "")
    return (
        "Onay gerekli (CU4).\n"
        f"  Ne: {what}\n"
        f"  Nerede: {where}\n"
        f"  Etki: {effect}\n"
        f"Onay için: onayla {confirmation_id}"
    )


def ensure_cli_mutation_confirmation(
    action_key: str,
    scope: Mapping[str, Any],
    confirmation_id: str | None,
    *,
    base_dir: Path | str | None = None,
) -> ConfirmationResult:
    """
    PR-C4: CLI mutasyon yolu confirmation enforcement (create/delete soft).
    Devre dışıyken no-op. Aktifken confirmation_id → check+consume; aksi halde confirmation_required.
    """
    if not is_confirmation_enabled():
        return ConfirmationResult(True, REASON_CONFIRMATION_DISABLED)

    if not requires_confirmation_for_action(action_key):
        return ConfirmationResult(True, "")

    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    scope_hash = _scope_hash(scope)
    cid = str(confirmation_id or "").strip()

    if not cid:
        return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)

    result = check_confirmation(
        action_key,
        scope,
        {"confirmation_id": cid, "base_dir": str(base)},
    )
    if not result.allowed:
        return result
    if consume_confirmation(cid, scope_hash, base_dir=base):
        return ConfirmationResult(True, "")
    return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)


def ensure_panel_mutation_confirmation(
    action_key: str,
    scope: Mapping[str, Any],
    body: Mapping[str, Any],
    *,
    base_dir: Path | str | None = None,
) -> ConfirmationResult:
    """
    PR-C3: panel mutasyon yolu confirmation enforcement (create/complete/delete/restore/PUT).
    Devre dışıyken no-op. Aktifken confirmation_id → check+consume; aksi halde confirmation_required.
    """
    if not is_confirmation_enabled():
        return ConfirmationResult(True, REASON_CONFIRMATION_DISABLED)

    if not requires_confirmation_for_action(action_key):
        return ConfirmationResult(True, "")

    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    scope_hash = _scope_hash(scope)
    confirmation_id = str(body.get("confirmation_id") or "").strip()

    if not confirmation_id:
        return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)

    result = check_confirmation(
        action_key,
        scope,
        {"confirmation_id": confirmation_id, "base_dir": str(base)},
    )
    if not result.allowed:
        return result
    if consume_confirmation(confirmation_id, scope_hash, base_dir=base):
        return ConfirmationResult(True, "")
    return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)


def ensure_delete_permanent_confirmation(
    body: Mapping[str, Any],
    scope: Mapping[str, Any],
    *,
    base_dir: Path | str | None = None,
    legacy_confirm: bool = False,
) -> ConfirmationResult:
    """
    PR-C2: delete_permanent panel yolu confirmation enforcement.
    Devre dışıyken no-op. Aktifken confirmation_id → check+consume;
    confirm=true legacy alias → request+consume; aksi halde confirmation_required.
    """
    if not is_confirmation_enabled():
        return ConfirmationResult(True, REASON_CONFIRMATION_DISABLED)

    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    scope_hash = _scope_hash(scope)
    confirmation_id = str(body.get("confirmation_id") or "").strip()

    if confirmation_id:
        result = check_confirmation(
            DELETE_PERMANENT_ACTION,
            scope,
            {"confirmation_id": confirmation_id, "base_dir": str(base)},
        )
        if not result.allowed:
            return result
        if consume_confirmation(confirmation_id, scope_hash, base_dir=base):
            return ConfirmationResult(True, "")
        return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)

    if legacy_confirm:
        pending = request_confirmation(DELETE_PERMANENT_ACTION, scope, base_dir=base)
        if consume_confirmation(pending.confirmation_id, scope_hash, base_dir=base):
            return ConfirmationResult(True, "")
        return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)

    return ConfirmationResult(False, REASON_CONFIRMATION_REQUIRED)


def consume_confirmation(
    confirmation_id: str,
    scope_hash: str,
    *,
    base_dir: Path | str | None = None,
) -> bool:
    """Tek kullanımlık grant tüketimi; scope_hash eşleşmezse False."""
    if not confirmation_id.strip():
        return False
    base = Path(base_dir).resolve() if base_dir is not None else lumos_base_dir()
    path = _grant_path(_pending_dir(base), confirmation_id)
    grant = _load_grant(path)
    if grant is None:
        return False
    if grant.get("scope_hash") != scope_hash:
        return False
    if grant.get("consumed"):
        return False
    expires_at = grant.get("expires_at")
    if isinstance(expires_at, str):
        exp = _parse_iso(expires_at)
        if exp is not None and datetime.now(timezone.utc) > exp:
            return False
    grant["consumed"] = True
    grant["consumed_at"] = _now_iso()
    _write_grant(path, grant)
    return True
