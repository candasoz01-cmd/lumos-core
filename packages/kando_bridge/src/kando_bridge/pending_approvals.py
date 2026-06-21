"""
PC remote bridge — `.lumos/pending_approvals/` disk sözleşmesi.

Legacy `/task` pending kayıtlarıyla aynı dizini paylaşır; `schema_version` ve `source`
ile ayrışır. Token doğrulama zorunlu; `approval_granted` bayrağı yeterli değil.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

PC_REMOTE_PENDING_SCHEMA = "lumos.pc_remote_pending_approval.v1"
PC_REMOTE_SOURCE = "pc_remote"

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"

PendingStatus = Literal["pending", "approved", "rejected", "expired"]

DEFAULT_TTL_SECONDS = 900


def pending_approvals_dir(repo_root: Path) -> Path:
    return (repo_root / ".lumos" / "pending_approvals").resolve()


def safe_pending_approval_path(repo_root: Path, rel: str) -> Path | None:
    """Path traversal koruması — `server._safe_pending_approval_path` ile aynı kural."""
    r = (rel or "").strip().replace("\\", "/")
    if not r or ".." in r.split("/"):
        return None
    if os.path.isabs(r):
        return None
    pending_root = pending_approvals_dir(repo_root)
    cand = (repo_root / r).resolve()
    try:
        cand.relative_to(pending_root)
    except ValueError:
        return None
    return cand if cand.is_file() else None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def new_approval_id() -> str:
    return f"pc_remote_{int(time.time() * 1000)}_{secrets.token_hex(4)}"


def new_approval_token() -> str:
    return secrets.token_hex(16)


def write_pending_approval(record: dict[str, Any], repo_root: Path) -> Path:
    """Kaydı `.lumos/pending_approvals/<approval_id>.json` altına yazar."""
    approval_id = str(record.get("approval_id") or "").strip()
    if not approval_id:
        raise ValueError("approval_id required")
    pending_dir = pending_approvals_dir(repo_root)
    pending_dir.mkdir(parents=True, exist_ok=True)
    rel = f".lumos/pending_approvals/{approval_id}.json"
    record.setdefault("approval_file", rel)
    path = pending_dir / f"{approval_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from kando_bridge.pc_remote_audit import EVENT_PENDING_CREATED, append_pc_remote_audit

        append_pc_remote_audit(
            repo_root,
            EVENT_PENDING_CREATED,
            approval_id=approval_id,
            command=str(record.get("command") or ""),
            status=str(record.get("status") or STATUS_PENDING),
            requested_by=str(record.get("requested_by") or ""),
            target_device=str(record.get("target_device") or ""),
            risk_level=str(record.get("risk_level") or ""),
        )
    except ImportError:
        pass
    return path


def _load_json_path(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def find_pending_by_approval_id(
    repo_root: Path,
    approval_id: str,
) -> tuple[Path, dict[str, Any]] | None:
    tid = (approval_id or "").strip()
    if not tid:
        return None
    pending_dir = pending_approvals_dir(repo_root)
    direct = pending_dir / f"{tid}.json"
    if direct.is_file():
        data = _load_json_path(direct)
        if data is not None:
            return direct, data
    try:
        for p in sorted(pending_dir.glob("*.json")):
            data = _load_json_path(p)
            if data is None:
                continue
            if str(data.get("approval_id") or "").strip() == tid:
                return p, data
    except OSError:
        return None
    return None


def find_pending_by_token(
    repo_root: Path,
    token: str,
) -> tuple[Path, dict[str, Any]] | None:
    tok = (token or "").strip()
    if not tok:
        return None
    pending_dir = pending_approvals_dir(repo_root)
    try:
        for p in sorted(pending_dir.glob("*.json")):
            data = _load_json_path(p)
            if data is None:
                continue
            if str(data.get("approval_token") or "").strip() == tok:
                return p, data
    except OSError:
        return None
    return None


def is_pc_remote_pending(record: dict[str, Any]) -> bool:
    if str(record.get("source") or "") == PC_REMOTE_SOURCE:
        return True
    return str(record.get("schema_version") or "") == PC_REMOTE_PENDING_SCHEMA


def _parse_expires_at(record: dict[str, Any]) -> datetime | None:
    raw = str(record.get("expires_at") or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def mark_expired_if_needed(path: Path, record: dict[str, Any]) -> bool:
    """Süresi dolmuş pending kaydını `expired` olarak işaretler."""
    if str(record.get("status") or "") != STATUS_PENDING:
        return False
    exp = _parse_expires_at(record)
    if exp is None or _utc_now() <= exp:
        return False
    record["status"] = STATUS_EXPIRED
    record["expired_at"] = _iso(_utc_now())
    try:
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    try:
        from kando_bridge.pc_remote_audit import EVENT_PENDING_EXPIRED, append_pc_remote_audit

        append_pc_remote_audit(
            path.parent.parent.parent,
            EVENT_PENDING_EXPIRED,
            approval_id=str(record.get("approval_id") or ""),
            command=str(record.get("command") or ""),
            status=STATUS_EXPIRED,
        )
    except (ImportError, OSError):
        pass
    return True


def validate_approval_token(
    repo_root: Path,
    approval_id: str,
    token: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    """
  Token/signature doğrulama — yürütme öncesi zorunlu.

  Başarı için: kayıt var, token eşleşir, status==approved, used==False, süre dolmamış.
  """
    tok = (token or "").strip()
    if not tok:
        return False, "approval_token_required", None

    found = find_pending_by_approval_id(repo_root, approval_id)
    if found is None:
        found = find_pending_by_token(repo_root, tok)
    if found is None:
        return False, "approval_not_found", None

    path, record = found
    if not is_pc_remote_pending(record):
        return False, "not_pc_remote_pending", None

    mark_expired_if_needed(path, record)
    if tok != str(record.get("approval_token") or "").strip():
        return False, "invalid_approval_token", None

    status = str(record.get("status") or STATUS_PENDING)
    if status == STATUS_EXPIRED:
        return False, "approval_expired", None
    if status == STATUS_REJECTED:
        return False, "approval_rejected", None
    if status != STATUS_APPROVED:
        return False, "approval_not_approved", None
    if bool(record.get("used")):
        return False, "approval_already_used", None

    exp = _parse_expires_at(record)
    if exp is not None and _utc_now() > exp:
        record["status"] = STATUS_EXPIRED
        record["expired_at"] = _iso(_utc_now())
        try:
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        return False, "approval_expired", None

    return True, "", record


def _audit_from_pending_path(path: Path, record: dict[str, Any], *, event: str) -> None:
    try:
        from kando_bridge.pc_remote_audit import append_pc_remote_audit

        repo_root = path.parent.parent.parent
        append_pc_remote_audit(
            repo_root,
            event,
            approval_id=str(record.get("approval_id") or ""),
            command=str(record.get("command") or ""),
            status=str(record.get("status") or ""),
            requested_by=str(record.get("requested_by") or ""),
            target_device=str(record.get("target_device") or ""),
            risk_level=str(record.get("risk_level") or ""),
        )
    except (ImportError, OSError):
        return


def approve_pending_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    record["status"] = STATUS_APPROVED
    record["approved_at"] = _iso(_utc_now())
    record["used"] = False
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _audit_from_pending_path(path, record, event="pending_approved")
    return record


def reject_pending_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    record["status"] = STATUS_REJECTED
    record["rejected_at"] = _iso(_utc_now())
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _audit_from_pending_path(path, record, event="pending_rejected")
    return record


def consume_pending_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    record["used"] = True
    record["consumed_at"] = _iso(_utc_now())
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def try_consume_approval_token(
    repo_root: Path,
    approval_id: str,
    token: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Validate approved token and mark ``used=True`` before stub execute (replay guard).

    Re-reads disk under an exclusive lock when available (Unix) to reduce TOCTOU races.
    """
    tok = (token or "").strip()
    aid = (approval_id or "").strip()
    if not tok:
        return False, "approval_token_required", None

    found = find_pending_by_approval_id(repo_root, aid)
    if found is None:
        found = find_pending_by_token(repo_root, tok)
    if found is None:
        return False, "approval_not_found", None

    path, _record = found
    if not is_pc_remote_pending(_record):
        return False, "not_pc_remote_pending", None

    try:
        import fcntl  # Unix-only; CI runs on Linux
    except ImportError:
        fcntl = None  # type: ignore[assignment]

    if fcntl is not None:
        with path.open("r+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.seek(0)
                raw = fh.read()
                fresh = json.loads(raw) if raw.strip() else {}
                if not isinstance(fresh, dict):
                    return False, "approval_not_found", None
                mark_expired_if_needed(path, fresh)
                ok, reason, _ = _validate_record_for_execute(fresh, tok)
                if not ok:
                    return False, reason, None
                fresh["used"] = True
                fresh["consumed_at"] = _iso(_utc_now())
                fh.seek(0)
                fh.truncate()
                fh.write(json.dumps(fresh, ensure_ascii=False, indent=2))
                fh.flush()
                return True, "", fresh
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    ok, reason, record = validate_approval_token(repo_root, aid, tok)
    if not ok or record is None:
        return False, reason, None
    if bool(record.get("used")):
        return False, "approval_already_used", None
    return True, "", consume_pending_record(path, record)


def _validate_record_for_execute(
    record: dict[str, Any],
    token: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    """In-lock validation helper for :func:`try_consume_approval_token`."""
    tok = (token or "").strip()
    if tok != str(record.get("approval_token") or "").strip():
        return False, "invalid_approval_token", None
    status = str(record.get("status") or STATUS_PENDING)
    if status == STATUS_EXPIRED:
        return False, "approval_expired", None
    if status == STATUS_REJECTED:
        return False, "approval_rejected", None
    if status != STATUS_APPROVED:
        return False, "approval_not_approved", None
    if bool(record.get("used")):
        return False, "approval_already_used", None
    exp = _parse_expires_at(record)
    if exp is not None and _utc_now() > exp:
        record["status"] = STATUS_EXPIRED
        record["expired_at"] = _iso(_utc_now())
        return False, "approval_expired", None
    return True, "", record


def build_pc_remote_pending_record(
    *,
    command: str,
    arguments: dict[str, Any],
    arguments_preview: dict[str, Any],
    risk_level: str,
    required_user_action: str,
    action_key: str | None,
    requested_by: str,
    target_device: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    now = _utc_now()
    expires = now + timedelta(seconds=max(60, ttl_seconds))
    approval_id = new_approval_id()
    token = new_approval_token()
    rel = f".lumos/pending_approvals/{approval_id}.json"
    title = f"{command}: {required_user_action[:120]}"
    return {
        "schema_version": PC_REMOTE_PENDING_SCHEMA,
        "source": PC_REMOTE_SOURCE,
        "approval_id": approval_id,
        "approval_file": rel,
        "approval_token": token,
        "command": command,
        "arguments": dict(arguments),
        "arguments_preview": dict(arguments_preview),
        "requested_by": requested_by,
        "target_device": target_device,
        "created_at": _iso(now),
        "expires_at": _iso(expires),
        "risk_level": risk_level,
        "required_user_action": required_user_action,
        "status": STATUS_PENDING,
        "action_key": action_key or "",
        "used": False,
        "stub_only": True,
        "title": title,
        "raw_text": title,
        "goal": title,
        "pending_summary": required_user_action,
        "reasoning_summary": required_user_action[:2000],
    }
