"""
Kando görev akışından Cursor bridge dosyaları + paket üretimi.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kando.cursor_packet import (
    SCHEMA_EXECUTION,
    SCHEMA_RESULT,
    CursorExecutionPacketV1,
    CursorResultPacketV1,
    Outcome,
    PlannedStepV1,
)
from task_engine.profiles import may_execute_step_at_runtime

_SRC_PY_PATH_RE = re.compile(r"(src/[a-zA-Z0-9_/.\-]+\.py)")

logger = logging.getLogger(__name__)

# Bridge JSON / memory: tam dosya yedeği üst sınırı (disk .bak kullanılmaz)
_MAX_PREVIOUS_CONTENT_IN_EXECUTION = 512_000
# dry_run: last_execution JSON içinde önerilen tam içerik üst sınırı
_MAX_DRY_RUN_PROPOSED_TEXT = 512_000
# diff_preview: çıktı satırı ve diff girdisi üst sınırı (performans)
_DIFF_PREVIEW_MAX_OUT_LINES = 30
_DIFF_PREVIEW_MAX_SIDE_LINES = 3000
_DIFF_PREVIEW_MAX_TOTAL_BYTES = 2 * 1024 * 1024
_PATCH_APPLY_LOG_MAX_DETAIL = 800
_PATCH_APPLY_LOG_FILENAME = "patch_apply.jsonl"
MAX_PATCH_SECONDS = 5
MAX_TOTAL_PATCH_SECONDS = 10
# Policy gate: aynı dosyaya tekrar patch (spam) penceresi (saniye)
_POLICY_SPAM_SECONDS = 3.0

# SHOW_HISTORY: result=failed eşlemesi (blocked hariç yaygın başarısızlık sonuçları)
_HISTORY_RESULT_FAILED = frozenset(
    {
        "patch_failed",
        "write_failed",
        "rollback_failed",
        "timeout",
        "timeout_total",
        "locked",
        "target_required",
        "partial",
        "blocked_by_rollback",
        "rollback_not_possible",
    }
)
_SHOW_HISTORY_FILTER_RE = re.compile(
    r"\b(result|risk|file)=([^\s]+)",
    re.IGNORECASE,
)

# Bellek içi patch geçmişi (disk yedeği değil); rollback_patch_file ile çakışmaz.
_MAX_PATCH_MEMORY_ENTRIES = 50
_PATCH_MEMORY: OrderedDict[str, dict[str, Any]] = OrderedDict()
# Rollback sırasında True; eşzamanlı patch girişleri blocked_by_rollback ile reddedilir.
_is_rollback = False

# Yüksek risk policy → pending_approval; APPROVE <audit_id> ile goal tekrar oynatılır.
_MAX_PENDING_APPROVALS = 50
_PENDING_APPROVALS: OrderedDict[str, dict[str, Any]] = OrderedDict()
_APPROVE_GOAL_RE = re.compile(r"(?i)^APPROVE\s+([a-f0-9\-]{36})\s*$")
_REJECT_GOAL_RE = re.compile(r"(?i)^REJECT\s+([a-f0-9\-]{36})\s*$")

# Bridge execution_result / error_type (policy, decision, approval)
EXEC_RESULT_BLOCKED = "blocked"
EXEC_RESULT_PENDING_APPROVAL = "pending_approval"
EXEC_RESULT_APPROVED_AND_EXECUTED = "approved_and_executed"
EXEC_RESULT_PATCH_FAILED = "patch_failed"
EXEC_RESULT_REJECTED = "rejected"

EXEC_ERROR_POLICY_BLOCK = "policy_block"
EXEC_ERROR_APPROVAL_REQUIRED = "approval_required"
EXEC_ERROR_APPROVAL_NOT_FOUND = "approval_not_found"
EXEC_ERROR_APPROVAL_REJECTED = "approval_rejected"

_PATCH_APPLY_SUCCESS_RESULTS = frozenset({"patch_applied", "dry_run_success", "no_change"})


def _bounded_ordered_set(
    od: OrderedDict[str, Any],
    key: str,
    value: Any,
    *,
    max_size: int,
) -> None:
    """Sıra korunur; kapasite aşımında en eski kayıt düşer."""
    if key in od:
        del od[key]
    od[key] = value
    while len(od) > max_size:
        od.popitem(last=False)


def _record_patch_memory(
    rel: str,
    previous_content: str | None,
    *,
    repo_root: Path | str | None = None,
) -> None:
    ts = time.time()
    if rel in _PATCH_MEMORY:
        del _PATCH_MEMORY[rel]
    rr: str | None = None
    if repo_root is not None:
        try:
            rr = str(Path(repo_root).resolve())
        except OSError:
            rr = None
    _PATCH_MEMORY[rel] = {
        "previous_content": previous_content,
        "timestamp": ts,
        "repo_root": rr,
    }
    while len(_PATCH_MEMORY) > _MAX_PATCH_MEMORY_ENTRIES:
        _PATCH_MEMORY.popitem(last=False)


def get_patch_memory_entry(repo_relative_path: str) -> dict[str, Any] | None:
    """Test / okuyucular için: bellekteki son patch öncesi kayıt (yoksa None)."""
    e = _PATCH_MEMORY.get(repo_relative_path)
    return None if e is None else dict(e)


def _handle_rollback_last_goal(goal: str, exe: CursorExecutionPacketV1) -> bool:
    """
    goal içinde ROLLBACK_LAST varsa: bellekteki en son patch kaydını tek adımda geri alır.
    Disk üzerinde ayrı yedek kullanılmaz; başarıda ilgili bellek girişi silinir.
    """
    if "ROLLBACK_LAST" not in (goal or ""):
        return False
    global _is_rollback
    _is_rollback = True
    try:
        from task_engine.executors.patch_apply_executor import _repo_root

        repo_root = _repo_root()
        if not _PATCH_MEMORY:
            exe.target_file = ""
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "rollback_not_possible",
                    "detail": "patch belleğinde geri alınacak kayıt yok",
                    "error_type": "",
                    "retry_count": 0,
                },
            )
            return True
        rel = next(reversed(_PATCH_MEMORY))
        entry = _PATCH_MEMORY[rel]
        prev = entry.get("previous_content")
        exe.target_file = rel
        if prev is None:
            del _PATCH_MEMORY[rel]
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "rollback_not_possible",
                    "detail": "önceki içerik yok (yeni oluşturulan dosya için bellekte tam metin yok)",
                    "error_type": "",
                    "retry_count": 0,
                    "failed_path": rel,
                },
            )
            return True
        target = (repo_root / rel).resolve()
        ok, msg = rollback_patch_file(target, prev, file_existed_before=True)
        if ok:
            del _PATCH_MEMORY[rel]
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "rollback_applied",
                    "detail": (msg or "önceki içerik geri yazıldı")[:2000],
                    "applied_path": rel,
                    "error_type": "",
                    "retry_count": 0,
                },
            )
        else:
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "rollback_failed",
                    "detail": (msg or "geri alma yazımı başarısız")[:2000],
                    "failed_path": rel,
                    "error_type": "write_failed",
                    "retry_count": 0,
                },
            )
        return True
    finally:
        _is_rollback = False


def _handle_rollback_preview_goal(goal: str, exe: CursorExecutionPacketV1) -> bool:
    """
    goal içinde ROLLBACK_PREVIEW varsa: diske yazmadan, son patch belleğine göre
    mevcut dosya ile previous_content arasında diff önizlemesi üretir.
    """
    if "ROLLBACK_PREVIEW" not in (goal or ""):
        return False
    from task_engine.executors.patch_apply_executor import _repo_root

    repo_root = _repo_root()
    if not _PATCH_MEMORY:
        exe.target_file = ""
        _store_execution_and_log(
            exe,
            {
                "execution_result": "rollback_not_possible",
                "detail": "patch belleğinde önizleme için kayıt yok",
                "error_type": "",
                "retry_count": 0,
                "diff_preview": "",
            },
        )
        return True
    rel = next(reversed(_PATCH_MEMORY))
    entry = _PATCH_MEMORY[rel]
    prev = entry.get("previous_content")
    if prev is None:
        prev = ""
    exe.target_file = rel
    target = (repo_root / rel).resolve()
    if not target.is_file():
        dp = _diff_preview_short("", prev) if prev else "(dosya yok; geri alma dosyayı kaldırır)\n"
        _store_execution_and_log(
            exe,
            {
                "execution_result": "rollback_preview",
                "detail": f"rollback önizlemesi (disk yazılmadı); hedef şu an yok — {rel}",
                "error_type": "",
                "retry_count": 0,
                "applied_path": rel,
                "diff_preview": dp,
                "risk_level": _rollback_preview_risk_level_from_diff(dp),
            },
        )
        return True
    try:
        cur = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        _store_execution_and_log(
            exe,
            {
                "execution_result": "rollback_preview",
                "detail": f"rollback önizlemesi; hedef okunamadı — {e}"[:2000],
                "error_type": "parse_error",
                "retry_count": 0,
                "failed_path": rel,
                "diff_preview": "",
                "risk_level": "low",
            },
        )
        return True
    dp = _diff_preview_short(cur, prev)
    _store_execution_and_log(
        exe,
        {
            "execution_result": "rollback_preview",
            "detail": "rollback önizlemesi (disk yazılmadı)",
            "error_type": "",
            "retry_count": 0,
            "applied_path": rel,
            "diff_preview": dp,
            "risk_level": _rollback_preview_risk_level_from_diff(dp),
        },
    )
    return True


def _lumos_base_path_for_log(exe: CursorExecutionPacketV1) -> Path | None:
    raw = exe.constraints.get("lumos_base_resolved")
    if raw:
        try:
            return Path(str(raw)).resolve()
        except OSError:
            pass
    lb = os.environ.get("LUMOS_BASE_DIR", ".lumos")
    p = Path(lb)
    try:
        if not p.is_absolute():
            return (Path.cwd() / p).resolve()
        return p.resolve()
    except OSError:
        return None


def _patch_apply_log_file_field(execution: dict[str, Any]) -> str:
    file_rel = str(
        execution.get("applied_path")
        or execution.get("failed_path")
        or execution.get("stopped_at")
        or ""
    )
    if file_rel:
        return file_rel
    fr = execution.get("file_results")
    if isinstance(fr, list) and fr:
        first = fr[0]
        if isinstance(first, dict):
            fp = str(first.get("path") or first.get("applied_path") or "")
            if fp:
                return fp
    ao = execution.get("apply_order")
    if isinstance(ao, list) and ao and ao[0]:
        return str(ao[0])
    dps = execution.get("diff_previews")
    if isinstance(dps, list) and dps:
        d0 = dps[0]
        if isinstance(d0, dict):
            return str(d0.get("relative_path") or "")
    return ""


def _ensure_audit_id(execution: dict[str, Any]) -> None:
    execution.setdefault("audit_id", str(uuid.uuid4()))


def _normalize_patch_apply_row_to_history_entry(row: dict[str, Any]) -> dict[str, Any]:
    rl = row.get("risk_level")
    risk_level = str(rl) if rl is not None and str(rl).strip() else "unknown"
    return {
        "audit_id": str(row.get("audit_id") or ""),
        "execution_result": str(row.get("result") or ""),
        "target_file": str(row.get("file") or ""),
        "risk_level": risk_level,
        "timestamp": str(row.get("time") or ""),
    }


def _load_patch_apply_history_entries(lumos_base: Path | None) -> list[dict[str, Any]]:
    """logs/patch_apply.jsonl tüm satırları (dosya sırası, yalnızca okuma)."""
    if lumos_base is None:
        return []
    log_path = (lumos_base / "logs" / _PATCH_APPLY_LOG_FILENAME).resolve()
    if not log_path.is_file():
        return []
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(_normalize_patch_apply_row_to_history_entry(row))
    return out


def _parse_show_history_filters(goal: str) -> dict[str, list[str]]:
    """SHOW_HISTORY için result=…, risk=…, file=… (boşlukla ayrılmış, çoklu AND grupları)."""
    out: dict[str, list[str]] = {"result": [], "risk": [], "file": []}
    if "SHOW_HISTORY" not in (goal or ""):
        return out
    for m in _SHOW_HISTORY_FILTER_RE.finditer(goal):
        k = m.group(1).lower()
        v = m.group(2).strip()
        if k == "result":
            out["result"].append(v)
        elif k == "risk":
            out["risk"].append(v.lower())
        elif k == "file":
            out["file"].append(v)
    return out


def _has_show_history_filters(filters: dict[str, list[str]]) -> bool:
    return bool(filters["result"]) or bool(filters["risk"]) or bool(filters["file"])


def _matches_show_history_result_filter(execution_result: str, token: str) -> bool:
    er = (execution_result or "").strip()
    t = (token or "").strip().lower()
    if t == "blocked":
        return er == "blocked"
    if t == "failed":
        return er in _HISTORY_RESULT_FAILED
    return er == token.strip()


def _file_path_matches_history_filter(target_file: str, pattern: str) -> bool:
    t = target_file.replace("\\", "/").strip()
    p = pattern.replace("\\", "/").strip()
    if not p:
        return True
    return t == p or t.endswith("/" + p.lstrip("/")) or t.endswith(p)


def _entry_matches_show_history_filters(
    entry: dict[str, Any], filters: dict[str, list[str]]
) -> bool:
    """Aynı anahtar içinde OR; anahtarlar arasında AND."""
    er = str(entry.get("execution_result") or "")
    rl = str(entry.get("risk_level") or "").lower()
    tf = str(entry.get("target_file") or "")
    if filters["result"]:
        if not any(_matches_show_history_result_filter(er, r) for r in filters["result"]):
            return False
    if filters["risk"]:
        if not any(rl == x for x in filters["risk"]):
            return False
    if filters["file"]:
        if not any(_file_path_matches_history_filter(tf, fp) for fp in filters["file"]):
            return False
    return True


def read_filtered_patch_apply_history(
    lumos_base: Path | None,
    filters: dict[str, list[str]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Filtrelere uyan kayıtların en son `limit` tanesi (dosya sırası korunur)."""
    if lumos_base is None or limit <= 0:
        return []
    all_e = _load_patch_apply_history_entries(lumos_base)
    filtered = [e for e in all_e if _entry_matches_show_history_filters(e, filters)]
    return filtered[-limit:] if len(filtered) > limit else filtered


def read_recent_patch_apply_history(
    lumos_base: Path | None, *, limit: int = 10
) -> list[dict[str, Any]]:
    """
    logs/patch_apply.jsonl içinden en son `limit` kaydı okur (yalnızca okuma).
    Her öğe: audit_id, execution_result, target_file, risk_level, timestamp.
    """
    if lumos_base is None or limit <= 0:
        return []
    all_e = _load_patch_apply_history_entries(lumos_base)
    return all_e[-limit:] if len(all_e) > limit else all_e


def _handle_show_history_goal(goal: str, exe: CursorExecutionPacketV1) -> bool:
    """goal içinde SHOW_HISTORY varsa: patch_apply.jsonl son kayıtlarını listeler (yazma yok)."""
    if "SHOW_HISTORY" not in (goal or ""):
        return False
    lumos_base = _lumos_base_path_for_log(exe)
    filters = _parse_show_history_filters(goal)
    if _has_show_history_filters(filters):
        history = read_filtered_patch_apply_history(lumos_base, filters, limit=10)
    else:
        history = read_recent_patch_apply_history(lumos_base, limit=10)
    exe.target_file = ""
    if not history:
        _set_execution_without_patch_log(
            exe,
            {
                "execution_result": "history_empty",
                "history": [],
                "error_type": "",
                "retry_count": 0,
            },
        )
    else:
        _set_execution_without_patch_log(
            exe,
            {
                "execution_result": "history_listed",
                "history": history,
                "error_type": "",
                "retry_count": 0,
            },
        )
    return True


def _set_execution_without_patch_log(
    exe: CursorExecutionPacketV1, execution: dict[str, Any]
) -> None:
    """Yalnızca exe.constraints['execution'] günceller; patch_apply.jsonl'e yazmaz."""
    _ensure_audit_id(execution)
    exe.constraints["execution"] = execution


def _append_patch_apply_log(lumos_base: Path | None, execution: dict[str, Any]) -> None:
    if lumos_base is None:
        return
    try:
        _ensure_audit_id(execution)
        result = str(execution.get("execution_result") or "")
        if not result:
            return
        entry = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "audit_id": str(execution.get("audit_id") or ""),
            "file": _patch_apply_log_file_field(execution),
            "result": result,
            "detail": str(execution.get("detail") or "")[:_PATCH_APPLY_LOG_MAX_DETAIL],
        }
        log_dir = (lumos_base / "logs").resolve()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / _PATCH_APPLY_LOG_FILENAME
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _constraint_force(exe: CursorExecutionPacketV1) -> bool:
    """Instruction apply: constraints['execution'] veya constraints['force'] ile force override."""
    ex = exe.constraints.get("execution")
    if isinstance(ex, dict) and "force" in ex:
        return bool(ex.get("force"))
    return bool(exe.constraints.get("force"))


def _lookup_pending_approval_key(aid: str) -> str | None:
    a = aid.strip().lower()
    for k in _PENDING_APPROVALS:
        if k.lower() == a:
            return k
    return None


def _register_pending_approval(audit_id: str, goal: str) -> None:
    _bounded_ordered_set(
        _PENDING_APPROVALS,
        audit_id,
        {"goal": goal},
        max_size=_MAX_PENDING_APPROVALS,
    )


def _finalize_approved_execution(exe: CursorExecutionPacketV1, approved_audit_id: str) -> None:
    ex = exe.constraints.get("execution")
    if not isinstance(ex, dict):
        ex = {}
    else:
        ex = dict(ex)
    ex["execution_result"] = EXEC_RESULT_APPROVED_AND_EXECUTED
    ex["error_type"] = ""
    ex["detail"] = f"onaylandı ve uygulandı (audit_id={approved_audit_id})"[:2000]
    ex["approved_audit_id"] = approved_audit_id
    _store_execution_and_log(exe, ex)


def _store_execution_outcome(
    exe: CursorExecutionPacketV1,
    *,
    execution_result: str,
    error_type: str,
    detail: str,
    retry_count: int = 0,
) -> None:
    _store_execution_and_log(
        exe,
        {
            "execution_result": execution_result,
            "error_type": error_type,
            "detail": detail,
            "retry_count": retry_count,
        },
    )


def _handle_approve_goal(goal: str, exe: CursorExecutionPacketV1) -> bool:
    """GOAL: APPROVE <audit_id> — bekleyen yüksek risk patch'ini force ile yeniden dener."""
    m = _APPROVE_GOAL_RE.match((goal or "").strip())
    if not m:
        return False
    aid_raw = m.group(1)
    aid_key = _lookup_pending_approval_key(aid_raw)
    if aid_key is None:
        _store_execution_outcome(
            exe,
            execution_result=EXEC_RESULT_PATCH_FAILED,
            error_type=EXEC_ERROR_APPROVAL_NOT_FOUND,
            detail=f"bekleyen onay kaydı yok: {aid_raw}",
        )
        exe.target_file = ""
        return True
    rec = _PENDING_APPROVALS.pop(aid_key)
    sub_goal = str(rec.get("goal") or "")
    if not sub_goal:
        _store_execution_outcome(
            exe,
            execution_result=EXEC_RESULT_PATCH_FAILED,
            error_type=EXEC_ERROR_APPROVAL_NOT_FOUND,
            detail="onay kaydında goal eksik",
        )
        _PENDING_APPROVALS[aid_key] = rec
        exe.target_file = ""
        return True
    exe.constraints["force"] = True
    exe.constraints["execution"] = {"force": True, "audit_id": aid_key}
    exe.constraints.pop("policy_gate_audit", None)
    try_instruction_patch_apply(sub_goal, exe)
    er = str((exe.constraints.get("execution") or {}).get("execution_result") or "")
    if er in _PATCH_APPLY_SUCCESS_RESULTS:
        _finalize_approved_execution(exe, aid_key)
    else:
        _PENDING_APPROVALS[aid_key] = rec
    return True


def _handle_reject_goal(goal: str, exe: CursorExecutionPacketV1) -> bool:
    """GOAL: REJECT <audit_id> — bekleyen onayı reddeder."""
    m = _REJECT_GOAL_RE.match((goal or "").strip())
    if not m:
        return False
    aid_raw = m.group(1)
    aid_key = _lookup_pending_approval_key(aid_raw)
    if aid_key is not None:
        _PENDING_APPROVALS.pop(aid_key, None)
    _store_execution_outcome(
        exe,
        execution_result=EXEC_RESULT_REJECTED,
        error_type=EXEC_ERROR_APPROVAL_REJECTED,
        detail=f"onay reddedildi (audit_id={aid_raw})",
    )
    exe.target_file = ""
    return True


def _policy_gate_set_force_bypass_audit(exe: CursorExecutionPacketV1) -> None:
    exe.constraints.pop("policy_gate_audit", None)
    exe.constraints["policy_gate_audit"] = {
        "layer": "policy_gate",
        "result": "bypass",
        "reason": "force",
        "audit_id": str((exe.constraints.get("execution") or {}).get("audit_id") or uuid.uuid4()),
    }


def _policy_gate_store_pending_high_risk(
    exe: CursorExecutionPacketV1,
    goal: str,
    *,
    aid: str,
    retry_count: int,
    audit_meta: dict[str, Any],
    detail: str,
) -> None:
    _store_execution_and_log(
        exe,
        {
            "audit_id": aid,
            "execution_result": EXEC_RESULT_PENDING_APPROVAL,
            "error_type": EXEC_ERROR_APPROVAL_REQUIRED,
            "detail": detail,
            "retry_count": retry_count,
            "forced": False,
            "risk_level": "high",
            "policy_gate": audit_meta,
        },
    )
    _register_pending_approval(aid, goal)


def _apply_policy_gate(goal: str, exe: CursorExecutionPacketV1) -> bool:
    """
    Üst politika katmanı (pre-check): profil-benzeri risk sınıflandırma.
    True = patch durduruldu (execution yazıldı). False = alt decision gate + execution.
    _constraint_force True ise bypass (blok yok).
    """
    if _constraint_force(exe):
        _policy_gate_set_force_bypass_audit(exe)
        return False

    ex = exe.constraints.get("execution")
    if not isinstance(ex, dict):
        ex = {}
    _ensure_audit_id(ex)
    exe.constraints["execution"] = ex
    aid = str(ex.get("audit_id") or "")

    rk = str(ex.get("risk_level") or "").strip().lower()
    er = str(ex.get("execution_result") or "")
    et = str(ex.get("execution_type") or "").strip().lower()

    audit_meta: dict[str, Any] = {
        "layer": "policy_gate",
        "audit_id": aid,
    }

    if rk == "high":
        if et == "rollback" or er in ("rollback_preview", "rollback_applied"):
            detail = (
                "yüksek risk + rollback bağlamı; açık onay gerekli — "
                "APPROVE <audit_id> ile onaylayın"
            )
            audit_meta["result"] = "pending"
            audit_meta["assessment"] = "rollback_high_risk"
        else:
            detail = (
                "yüksek risk; açık onay gerekli — APPROVE <audit_id> ile onaylayın"
            )
            audit_meta["result"] = "pending"
            audit_meta["assessment"] = "high_risk_approval_required"
        _policy_gate_store_pending_high_risk(
            exe,
            goal,
            aid=aid,
            retry_count=int(ex.get("retry_count") or 0),
            audit_meta=audit_meta,
            detail=detail,
        )
        return True

    if rk in ("", "unknown") or rk not in ("low", "medium", "high"):
        audit_meta["result"] = "allow"
        audit_meta["assessment"] = "unknown_risk_proceed"
        audit_meta["detail"] = "risk sınıfı bilinmiyor; alt karar katmanına iletildi"
        exe.constraints["policy_gate_audit"] = audit_meta
        return False

    audit_meta["result"] = "allow"
    audit_meta["assessment"] = "known_risk"
    audit_meta["risk_level"] = rk
    exe.constraints["policy_gate_audit"] = audit_meta
    return False


def _should_block_execution(exe: CursorExecutionPacketV1) -> tuple[bool, str]:
    """
    Karar katmanı: risk / tekrar / retry politikası.
    Dönüş: (True, gerekçe) patch uygulanmamalı; force True ise (False, '').
    """
    if _constraint_force(exe):
        return False, ""
    ex = exe.constraints.get("execution")
    if not isinstance(ex, dict):
        ex = {}
    if int(ex.get("retry_count") or 0) > 1:
        return True, "policy_block: retry_count > 1"
    rels: list[str] = []
    tf = getattr(exe, "target_files", None) or []
    if isinstance(tf, list) and len(tf) >= 2:
        rels = [str(x).strip().replace("\\", "/") for x in tf[:2] if str(x).strip()]
    else:
        r = (exe.target_file or "").strip()
        if r:
            rels.append(r.replace("\\", "/"))
    rroot: str | None = None
    try:
        from task_engine.executors.patch_apply_executor import _repo_root

        rroot = str(_repo_root().resolve())
    except Exception:
        rroot = None
    if rels and rroot and _POLICY_SPAM_SECONDS > 0:
        now = time.time()
        for r in rels:
            mem = _PATCH_MEMORY.get(r)
            if mem is None:
                continue
            stored_rr = mem.get("repo_root")
            if stored_rr is None or stored_rr != rroot:
                continue
            ts = float(mem.get("timestamp") or 0)
            if now - ts < _POLICY_SPAM_SECONDS:
                return True, "policy_block: aynı dosyaya kısa sürede tekrar patch"
    risk = str(ex.get("risk_level") or "").strip().lower()
    er = str(ex.get("execution_result") or "")
    et = str(ex.get("execution_type") or "").strip().lower()
    if risk == "high":
        if et == "rollback" or er in ("rollback_preview", "rollback_applied"):
            return True, "policy_block: rollback + yüksek risk"
        return True, "policy_block: risk_level=high"
    return False, ""


def _decision_gate_blocked_payload(exe: CursorExecutionPacketV1, detail: str) -> dict[str, Any]:
    prev = exe.constraints.get("execution")
    payload: dict[str, Any] = {
        "execution_result": EXEC_RESULT_BLOCKED,
        "error_type": EXEC_ERROR_POLICY_BLOCK,
        "detail": detail,
        "retry_count": int((prev or {}).get("retry_count") or 0) if isinstance(prev, dict) else 0,
        "forced": False,
    }
    if isinstance(prev, dict):
        if prev.get("risk_level") is not None:
            payload["risk_level"] = prev.get("risk_level")
        fp = (exe.target_file or "").strip() or prev.get("failed_path")
        if fp:
            payload["failed_path"] = fp
    pga = exe.constraints.get("policy_gate_audit")
    if isinstance(pga, dict) and pga.get("result") == "allow":
        payload["policy_gate"] = dict(pga)
    return payload


def _decision_gate_apply(exe: CursorExecutionPacketV1) -> bool:
    """
    Decision gate (mevcut): retry / spam / risk / force — patch apply öncesi.
    True dönerse execution yazıldı ve patch çalıştırılmamalı.
    """
    block, detail = _should_block_execution(exe)
    if not block:
        return False
    _store_execution_and_log(exe, _decision_gate_blocked_payload(exe, detail))
    return True


def _apply_patch_instruction_gates(goal: str, exe: CursorExecutionPacketV1) -> bool:
    """Policy + decision gate. True = patch akışını durdur."""
    if _apply_policy_gate(goal, exe):
        return True
    if _decision_gate_apply(exe):
        return True
    return False


def _store_execution_and_log(exe: CursorExecutionPacketV1, execution: dict[str, Any]) -> None:
    _ensure_audit_id(execution)
    pga = exe.constraints.get("policy_gate_audit")
    if isinstance(pga, dict) and pga.get("result") == "allow":
        execution = dict(execution)
        execution["policy_gate"] = pga
    exe.constraints["execution"] = execution
    _append_patch_apply_log(_lumos_base_path_for_log(exe), execution)


def _error_type_from_instruction_kind(kind: str) -> str:
    """_instruction_apply_one hata kind → execution error_type."""
    k = (kind or "").strip()
    if k == "verify":
        return "verification_failed"
    if k == "validate":
        return "parse_error"
    if k == "timeout":
        return "write_failed"
    if k == "timeout_total":
        return "write_failed"
    if k == "high_risk_blocked":
        return "high_risk_blocked"
    return "write_failed"


def _diff_preview_short(before: str, after: str) -> str:
    """Önce/sonra kısa unified diff; patch uygulanmadan önceki önizleme."""
    if len(before) + len(after) > _DIFF_PREVIEW_MAX_TOTAL_BYTES:
        return "diff_preview: (içerik çok büyük, atlandı)\n"
    a = before.splitlines(keepends=True)
    b = after.splitlines(keepends=True)
    if len(a) > _DIFF_PREVIEW_MAX_SIDE_LINES:
        omitted = len(a) - _DIFF_PREVIEW_MAX_SIDE_LINES
        a = a[:_DIFF_PREVIEW_MAX_SIDE_LINES] + [
            f"... ({omitted} satır before tarafında atlandı)\n"
        ]
    if len(b) > _DIFF_PREVIEW_MAX_SIDE_LINES:
        omitted_b = len(b) - _DIFF_PREVIEW_MAX_SIDE_LINES
        b = b[:_DIFF_PREVIEW_MAX_SIDE_LINES] + [
            f"... ({omitted_b} satır after tarafında atlandı)\n"
        ]
    lines: list[str] = []
    for i, line in enumerate(
        difflib.unified_diff(a, b, fromfile="before", tofile="after", n=2)
    ):
        if i >= _DIFF_PREVIEW_MAX_OUT_LINES:
            lines.append("... (diff önizlemesi kısaltıldı)\n")
            break
        lines.append(line if line.endswith("\n") else line + "\n")
    return "".join(lines) if lines else "(değişiklik yok)\n"


def _count_unified_diff_changed_lines(diff_text: str) -> int:
    """diff_preview (unified diff) içinde ekleme/silme satırları; ---/+++ başlıkları sayılmaz."""
    n = 0
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("+"):
            n += 1
        elif line.startswith("-") and not line.startswith("--"):
            n += 1
    return n


def _risk_level_from_changed_line_count(n: int) -> str:
    """>20 high, 5–20 medium, <5 low."""
    if n > 20:
        return "high"
    if n >= 5:
        return "medium"
    return "low"


def _rollback_preview_risk_level_from_diff(diff_text: str) -> str:
    return _risk_level_from_changed_line_count(_count_unified_diff_changed_lines(diff_text))


def rollback_patch_file(
    target: Path,
    previous_text: str,
    *,
    file_existed_before: bool,
) -> tuple[bool, str]:
    """
    Bellekte tutulan patch öncesi içeriği geri yazar. .bak dosyası kullanılmaz.
    Patch sırasında yeni oluşturulmuş dosya için (patch öncesi yoktu) hedef dosyayı siler.
    """
    try:
        tp = target.resolve()
        if not file_existed_before:
            if tp.is_file():
                tp.unlink()
            return True, "patch ile oluşturulmuş dosya kaldırıldı"
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text(previous_text, encoding="utf-8")
        return True, "önceki içerik geri yazıldı"
    except OSError as e:
        return False, str(e)


def _atomic_write_text_utf8(target: Path, text: str) -> bool:
    """
    Hedef dosyaya doğrudan yazmak yerine aynı klasörde *.tmp + os.replace.
    Hata: temp silinir, False döner.
    """
    tp = target.resolve()
    parent = tp.parent
    temp_path = parent / (tp.name + ".tmp")
    try:
        parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(text, encoding="utf-8")
        os.replace(temp_path, tp)
    except OSError:
        try:
            if temp_path.is_file():
                temp_path.unlink()
        except OSError:
            pass
        return False
    return True


def _explicit_single_lock_path(text: str) -> str | None:
    """Metinde tam bir adet src/...py yolu varsa döndür (kando_core ile aynı kural)."""
    ms = _SRC_PY_PATH_RE.findall(text or "")
    if len(ms) != 1:
        return None
    return ms[0]


def _extract_src_py_from_instruction(goal: str) -> str | None:
    m = _SRC_PY_PATH_RE.search(goal or "")
    return m.group(1) if m else None


# brain.run → persist_bridge_after_brain sonrası paketler (run_brain_and_persist_bridge / llm okur)
_last_bridge_packets: (
    tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1] | None
) = None


def resolve_lumos_base_for_bridge(base_dir: Path | str) -> Path:
    """TaskEngine base_dir tasks/ ise üst .lumos; aksi halde genelde .lumos kökü."""
    p = Path(base_dir).resolve()
    if p.name == "tasks":
        return p.parent
    return p


def clear_last_bridge_packets() -> None:
    global _last_bridge_packets
    _last_bridge_packets = None


def pop_last_bridge_packets() -> (
    tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1] | None
):
    """Son persist edilen bridge paketini alır ve sıfırlar."""
    global _last_bridge_packets
    t = _last_bridge_packets
    _last_bridge_packets = None
    return t


def persist_bridge_after_brain(
    *,
    goal: str,
    task: Any,
    brain_success: bool,
    pipeline: dict[str, Any] | None,
    permission_profile: str,
    general_approval: bool,
    lumos_base: Path,
    dry_run: bool = False,
) -> tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1]:
    """
    TaskEngine.run_task sonrası: execution paketi + last_execution/last_result + cursor_executor kancası.
    core.brain.run içinden çağrılır (tek doğruluk kaynağı).
    """
    global _last_bridge_packets
    base = lumos_base.resolve()
    base.mkdir(parents=True, exist_ok=True)

    exe = build_execution_packet(
        goal,
        task,
        permission_profile=permission_profile,
        general_approval=general_approval,
    )
    exe.constraints["lumos_base_resolved"] = str(base)
    if dry_run:
        exe.constraints["dry_run"] = True
    try_instruction_patch_apply(goal, exe)
    record_bridge_execution(exe, task)
    from core.patch_pipeline_lifecycle import (
        enrich_pipeline_with_execution,
        merge_pipeline_into_execution,
    )

    ex_dict = exe.constraints.get("execution")
    pl = pipeline
    try:
        if isinstance(ex_dict, dict):
            pl = enrich_pipeline_with_execution(pl, ex_dict, goal)
        if pl:
            exe.constraints["pipeline"] = pl
        if isinstance(ex_dict, dict) and pl:
            merge_pipeline_into_execution(ex_dict, pl)
    except Exception:
        if pipeline:
            exe.constraints["pipeline"] = pipeline
    ex_payload = exe.constraints.get("execution") if isinstance(exe.constraints.get("execution"), dict) else None
    res_pkt = build_result_packet(
        goal=goal,
        brain_success=brain_success,
        task=task,
        execution=ex_payload,
    )
    p_exec, p_res = persist_cursor_bridge(base, exe, res_pkt)
    _last_bridge_packets = (p_exec, p_res, exe, res_pkt)
    try:
        from kando.cursor_executor import run_after_bridge

        run_after_bridge(base, exe)
    except Exception:
        pass
    return _last_bridge_packets


_LUMOS_SAFE_TOUCH_PY = "# lumos:instruction-pipeline safe touch"


def _safe_fallback_new_content(target: Path, *, max_bytes: int = 512_000) -> str | None:
    """Küçük, sözdizimini bozmayan yama: yorum satırı / güvenli ek (docstring veya marker)."""
    try:
        st = target.stat()
    except OSError:
        return None
    if st.st_size > max_bytes:
        return None
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    ext = target.suffix.lower()
    if ext == ".py":
        add = f"\n{_LUMOS_SAFE_TOUCH_PY}\n"
        if _LUMOS_SAFE_TOUCH_PY in text:
            add = f"\n{_LUMOS_SAFE_TOUCH_PY} (resync)\n"
        if not text.endswith("\n"):
            text += "\n"
        return text + add
    if ext == ".md":
        add = "\n\n<!-- lumos:instruction-pipeline safe touch -->\n"
        if "lumos:instruction-pipeline safe touch" in text:
            add = "\n\n<!-- lumos:instruction-pipeline resync -->\n"
        return text + add
    if ext == ".json":
        return None
    if ext in (".txt", ".toml", ".yaml", ".yml", ".rs", ".go", ".ts", ".tsx", ".jsx", ".sh"):
        sep = "#"
        add = f"\n{sep} lumos:instruction-pipeline safe touch\n"
        if "lumos:instruction-pipeline safe touch" in text:
            add = f"\n{sep} lumos:instruction-pipeline resync\n"
        if not text.endswith("\n"):
            text += "\n"
        return text + add
    return None


def _parse_target_instruction_patch(goal: str) -> tuple[str, str, str | None] | None:
    """
    Task metninden patch üretmek için biçim (patch: öneki yokken):
      TARGET: göreli/yol.txt
      <dosya içeriği>
      İsteğe bağlı:
      VERIFY:
      komut satırı
    """
    lines = (goal or "").strip().splitlines()
    if len(lines) < 2:
        return None
    first = lines[0].strip()
    if not first.upper().startswith("TARGET:"):
        return None
    rel = first.split(":", 1)[1].strip()
    from kando.patch_scope import _split_verify_block

    body_lines, verify_cmd = _split_verify_block(lines[1:])
    body = "\n".join(body_lines).strip("\n")
    if not rel or not body:
        return None
    return rel, body, verify_cmd


def _instruction_apply_one(
    *,
    repo_root: Path,
    lumos_base: Path,
    rel: str,
    body: str,
    verify_cmd: str | None,
    source: str,
    dry_run: bool = False,
    force: bool = False,
    deadline_abs: float | None = None,
    patch_flow_start: float | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Tek dosya: propose → apply → verify. dry_run=True iken disk yazılmaz, doğrulama atlanır."""
    from core.patch_pipeline import (
        ProtectedApplyForbidden,
        apply_patch,
        propose_text_patch,
        validate_proposal_against_filesystem,
    )
    from core.workspace_contract import is_core_state_path
    from kando.patch_verify_runner import run_post_apply_verify

    dline = deadline_abs if deadline_abs is not None else time.time() + MAX_PATCH_SECONDS

    def _deadline_exceeded() -> bool:
        return time.time() > dline

    def _total_budget_exceeded() -> bool:
        if patch_flow_start is None:
            return False
        return time.time() - patch_flow_start > MAX_TOTAL_PATCH_SECONDS

    target = (repo_root / rel).resolve()
    if is_core_state_path(lumos_base, target):
        return False, {
            "detail": "patch başarısız: hedef .lumos çekirdek state yolunda (yazma yasak)",
            "kind": "core_state",
            "had_previous": False,
        }
    if _total_budget_exceeded():
        return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": False}
    if _deadline_exceeded():
        return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": False}
    file_existed_before = target.is_file()
    previous_text = ""
    if file_existed_before:
        try:
            previous_text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return False, {
                "detail": f"patch başarısız: hedef okunamadı ({rel}): {e}",
                "kind": "read_error",
                "had_previous": True,
            }
    if _total_budget_exceeded():
        return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": file_existed_before}
    if _deadline_exceeded():
        return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": file_existed_before}
    had_previous = file_existed_before
    mutated = False
    lock_path = target.parent / (target.name + ".lock")
    lock_acquired = False
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.touch(exist_ok=False)
        lock_acquired = True
    except FileExistsError:
        return False, {"kind": "locked", "detail": "file is locked", "had_previous": had_previous}

    try:
        _record_patch_memory(
            rel,
            previous_text if file_existed_before else None,
            repo_root=repo_root,
        )
        proposal = propose_text_patch(
            target,
            body,
            reason="kando.cursor_bridge.try_instruction_patch_apply",
            caller="kando.cursor_bridge.try_instruction_patch_apply",
            source="kando",
            user_initiated=True,
            protected_target=False,
        )
        val = validate_proposal_against_filesystem(proposal)
        if val.status != "ok":
            return False, {
                "detail": f"patch başarısız: öneri dosya sistemi doğrulamasında reddedildi — {val.message}",
                "kind": "validate",
                "patch_id": proposal.id,
                "had_previous": had_previous,
            }

        if _total_budget_exceeded():
            return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": had_previous}
        if _deadline_exceeded():
            return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": had_previous}

        diff_preview = _diff_preview_short(previous_text, proposal.proposed_text)

        if dry_run:
            prop_full = proposal.proposed_text
            prop_exec = prop_full
            prop_trunc = False
            if len(prop_exec) > _MAX_DRY_RUN_PROPOSED_TEXT:
                prop_exec = prop_exec[:_MAX_DRY_RUN_PROPOSED_TEXT]
                prop_trunc = True
            prev_for_exec = previous_text
            prev_trunc = False
            if len(prev_for_exec) > _MAX_PREVIOUS_CONTENT_IN_EXECUTION:
                prev_for_exec = prev_for_exec[:_MAX_PREVIOUS_CONTENT_IN_EXECUTION]
                prev_trunc = True
            v_msg = "dry_run: disk yazılmadı, doğrulama atlandı"
            logger.info(
                "Instruction patch dry-run: relative_path=%s patch_id=%s",
                rel,
                proposal.id,
            )
            if _total_budget_exceeded():
                return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": had_previous}
            if _deadline_exceeded():
                return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": had_previous}
            return True, {
                "patch_id": proposal.id,
                "verify_msg": v_msg,
                "source": source,
                "applied_path": rel,
                "previous_content": prev_for_exec,
                "previous_content_truncated": prev_trunc,
                "dry_run": True,
                "proposed_text": prop_exec,
                "proposed_text_truncated": prop_trunc,
                "diff_preview": diff_preview,
                "had_previous": had_previous,
                "forced": False,
            }

        if _total_budget_exceeded():
            return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": had_previous}
        if _deadline_exceeded():
            return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": had_previous}

        risk_level = _rollback_preview_risk_level_from_diff(diff_preview)
        if risk_level == "high" and not force:
            return False, {
                "kind": "high_risk_blocked",
                "detail": "yüksek riskli yama uygulanmadı (önizleme diff risk_level=high)",
                "patch_id": proposal.id,
                "diff_preview": diff_preview,
                "risk_level": "high",
                "had_previous": had_previous,
            }
        forced_apply = bool(risk_level == "high" and force)

        if previous_text == proposal.proposed_text:
            if _total_budget_exceeded():
                return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": had_previous}
            if _deadline_exceeded():
                return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": had_previous}
            v_ok, v_msg = run_post_apply_verify(target, verify_cmd)
            if not v_ok:
                fail_detail = (
                    f"patch başarısız: doğrulama başarısız — {v_msg}"[:2000]
                )
                return False, {
                    "detail": fail_detail,
                    "verify_detail": v_msg[:1500],
                    "patch_id": proposal.id,
                    "kind": "verify",
                    "source": source,
                    "had_previous": had_previous,
                }
            prev_for_exec = previous_text
            truncated = False
            if len(prev_for_exec) > _MAX_PREVIOUS_CONTENT_IN_EXECUTION:
                prev_for_exec = prev_for_exec[:_MAX_PREVIOUS_CONTENT_IN_EXECUTION]
                truncated = True
            logger.info(
                "Instruction patch no-op (already applied): relative_path=%s patch_id=%s",
                rel,
                proposal.id,
            )
            if _total_budget_exceeded():
                return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": had_previous}
            if _deadline_exceeded():
                return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": had_previous}
            return True, {
                "patch_id": proposal.id,
                "verify_msg": v_msg,
                "source": source,
                "applied_path": rel,
                "previous_content": prev_for_exec,
                "previous_content_truncated": truncated,
                "diff_preview": diff_preview,
                "already_applied": True,
                "had_previous": had_previous,
                "forced": False,
            }

        apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)
        mutated = True
        try:
            on_disk = target.read_text(encoding="utf-8")
        except OSError:
            on_disk = ""
        if on_disk != proposal.proposed_text:
            if not _atomic_write_text_utf8(target, proposal.proposed_text):
                rb_ok, rb_msg = rollback_patch_file(
                    target,
                    previous_text,
                    file_existed_before=file_existed_before,
                )
                if rb_ok:
                    return False, {
                        "detail": "atomic write failed",
                        "kind": "atomic_write",
                        "patch_id": proposal.id,
                        "source": source,
                        "rollback_applied": True,
                        "rollback_detail": rb_msg,
                        "had_previous": had_previous,
                    }
                return False, {
                    "detail": "atomic write failed",
                    "kind": "atomic_write",
                    "patch_id": proposal.id,
                    "source": source,
                    "had_previous": had_previous,
                }
        if _total_budget_exceeded():
            return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": had_previous}
        if _deadline_exceeded():
            return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": had_previous}
        v_ok, v_msg = run_post_apply_verify(target, verify_cmd)
        if not v_ok:
            fail_detail = (
                f"patch başarısız: doğrulama başarısız — {v_msg}"[:2000]
            )
            rb_ok, rb_msg = rollback_patch_file(
                target,
                previous_text,
                file_existed_before=file_existed_before,
            )
            if rb_ok:
                logger.info(
                    "Instruction patch rolled back after verify failure: relative_path=%s (%s)",
                    rel,
                    rb_msg,
                )
                return False, {
                    "detail": f"{fail_detail}; disk geri alındı — {rb_msg}",
                    "verify_detail": v_msg[:1500],
                    "patch_id": proposal.id,
                    "kind": "verify",
                    "source": source,
                    "rollback_applied": True,
                    "rollback_detail": rb_msg,
                    "had_previous": had_previous,
                }
            return False, {
                "detail": f"{fail_detail}; geri alma başarısız — {rb_msg}"[:2000],
                "verify_detail": v_msg[:1500],
                "patch_id": proposal.id,
                "kind": "verify",
                "source": source,
                "had_previous": had_previous,
            }
        prev_for_exec = previous_text
        truncated = False
        if len(prev_for_exec) > _MAX_PREVIOUS_CONTENT_IN_EXECUTION:
            prev_for_exec = prev_for_exec[:_MAX_PREVIOUS_CONTENT_IN_EXECUTION]
            truncated = True
        logger.info(
            "Instruction patch applied: relative_path=%s patch_id=%s verify_ok",
            rel,
            proposal.id,
        )
        if _total_budget_exceeded():
            return False, {"detail": "total patch timeout", "kind": "timeout_total", "had_previous": had_previous}
        if _deadline_exceeded():
            return False, {"detail": "patch timeout", "kind": "timeout", "had_previous": had_previous}
        return True, {
            "patch_id": proposal.id,
            "verify_msg": v_msg,
            "source": source,
            "applied_path": rel,
            "previous_content": prev_for_exec,
            "previous_content_truncated": truncated,
            "diff_preview": diff_preview,
            "had_previous": had_previous,
            "forced": forced_apply,
        }
    except ProtectedApplyForbidden as e:
        if mutated:
            rb_ok, rb_msg = rollback_patch_file(
                target,
                previous_text,
                file_existed_before=file_existed_before,
            )
            if rb_ok:
                logger.info(
                    "Instruction patch rolled back after protected error: relative_path=%s (%s)",
                    rel,
                    rb_msg,
                )
                return False, {
                    "detail": f"patch başarısız: korumalı hedefe yazma reddedildi — {e}; disk geri alındı — {rb_msg}"[
                        :2000
                    ],
                    "kind": "protected",
                    "rollback_applied": True,
                    "rollback_detail": rb_msg,
                    "had_previous": had_previous,
                }
        return False, {
            "detail": f"patch başarısız: korumalı hedefe yazma reddedildi — {e}"[:800],
            "kind": "protected",
            "had_previous": had_previous,
        }
    except Exception as e:
        if mutated:
            rb_ok, rb_msg = rollback_patch_file(
                target,
                previous_text,
                file_existed_before=file_existed_before,
            )
            if rb_ok:
                logger.info(
                    "Instruction patch rolled back after error relative_path=%s (%s)",
                    rel,
                    rb_msg,
                )
                return False, {
                    "detail": f"patch başarısız: beklenmeyen hata ({rel}) — {e}; disk geri alındı — {rb_msg}"[
                        :2000
                    ],
                    "kind": "exception",
                    "rollback_applied": True,
                    "rollback_detail": rb_msg,
                    "had_previous": had_previous,
                }
        return False, {
            "detail": f"patch başarısız: beklenmeyen hata ({rel}) — {e}"[:800],
            "kind": "exception",
            "had_previous": had_previous,
        }
    finally:
        if lock_acquired:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def _instruction_apply_one_with_retry(
    *,
    repo_root: Path,
    lumos_base: Path,
    rel: str,
    body: str,
    verify_cmd: str | None,
    source: str,
    dry_run: bool = False,
    force: bool = False,
    deadline_abs: float | None = None,
    patch_flow_start: float | None = None,
) -> tuple[bool, dict[str, Any], int]:
    """İlk deneme başarısızsa yalnızca bir kez daha dener. retry_count: 0 veya 1."""
    ok, info = _instruction_apply_one(
        repo_root=repo_root,
        lumos_base=lumos_base,
        rel=rel,
        body=body,
        verify_cmd=verify_cmd,
        source=source,
        dry_run=dry_run,
        force=force,
        deadline_abs=deadline_abs,
        patch_flow_start=patch_flow_start,
    )
    if ok:
        return True, info, 0
    if info.get("kind") in ("timeout", "timeout_total", "locked", "high_risk_blocked"):
        return False, info, 0
    ok2, info2 = _instruction_apply_one(
        repo_root=repo_root,
        lumos_base=lumos_base,
        rel=rel,
        body=body,
        verify_cmd=verify_cmd,
        source=source,
        dry_run=dry_run,
        force=force,
        deadline_abs=deadline_abs,
        patch_flow_start=patch_flow_start,
    )
    if ok2:
        return True, info2, 1
    if info2.get("kind") in ("timeout", "timeout_total", "locked", "high_risk_blocked"):
        return False, info2, 1
    return False, info2, 1


def _run_instruction_apply_to_exe(
    exe: CursorExecutionPacketV1,
    rel: str,
    body: str,
    verify_cmd: str | None,
    source: str,
    *,
    repo_root: Path,
    lumos_base: Path,
    dry_run: bool = False,
    force: bool = False,
    patch_flow_start: float | None = None,
) -> bool:
    """exe.constraints['execution'] yazar. Başarıda True."""
    exe.target_file = rel
    ok, info, retry_count = _instruction_apply_one_with_retry(
        repo_root=repo_root,
        lumos_base=lumos_base,
        rel=rel,
        body=body,
        verify_cmd=verify_cmd,
        source=source,
        dry_run=dry_run,
        force=force,
        patch_flow_start=patch_flow_start,
    )
    hp = bool(info.get("had_previous"))
    if not ok and info.get("kind") == "high_risk_blocked":
        _store_execution_and_log(
            exe,
            {
                "execution_result": "blocked",
                "error_type": "high_risk_blocked",
                "risk_level": "high",
                "detail": str(info.get("detail") or "yüksek riskli yama uygulanmadı")[:2000],
                "diff_preview": str(info.get("diff_preview") or ""),
                "patch_id": info.get("patch_id", ""),
                "source": source,
                "failed_path": rel,
                "retry_count": retry_count,
                "had_previous": hp,
                "forced": False,
            },
        )
        return False
    if ok:
        v_msg = str(info.get("verify_msg") or "")
        if info.get("dry_run"):
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "dry_run_success",
                    "detail": f"{source}; {v_msg}"[:2000],
                    "verify_detail": v_msg[:1500],
                    "source": source,
                    "patch_id": info.get("patch_id", ""),
                    "applied_path": rel,
                    "dry_run": True,
                    "proposed_text": info.get("proposed_text", ""),
                    "proposed_text_truncated": bool(info.get("proposed_text_truncated")),
                    "previous_content": info.get("previous_content", ""),
                    "previous_content_truncated": bool(info.get("previous_content_truncated")),
                    "diff_preview": str(info.get("diff_preview") or ""),
                    "error_type": "",
                    "retry_count": retry_count,
                    "had_previous": hp,
                    "forced": bool(info.get("forced")),
                },
            )
            return True
        if info.get("already_applied"):
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "no_change",
                    "detail": "patch already applied",
                    "verify_detail": v_msg[:1500],
                    "source": source,
                    "patch_id": info.get("patch_id", ""),
                    "applied_path": rel,
                    "previous_content": info.get("previous_content", ""),
                    "previous_content_truncated": bool(info.get("previous_content_truncated")),
                    "diff_preview": str(info.get("diff_preview") or ""),
                    "error_type": "",
                    "retry_count": retry_count,
                    "had_previous": hp,
                    "forced": bool(info.get("forced")),
                },
            )
            return True
        _store_execution_and_log(
            exe,
            {
                "execution_result": "patch_applied",
                "detail": f"{source}; {v_msg}"[:2000],
                "verify_detail": v_msg[:1500],
                "source": source,
                "patch_id": info.get("patch_id", ""),
                "applied_path": rel,
                "previous_content": info.get("previous_content", ""),
                "previous_content_truncated": bool(info.get("previous_content_truncated")),
                "diff_preview": str(info.get("diff_preview") or ""),
                "error_type": "",
                "retry_count": retry_count,
                "had_previous": hp,
                "forced": bool(info.get("forced")),
            },
        )
        return True
    kind = info.get("kind", "")
    if kind == "timeout_total":
        _store_execution_and_log(
            exe,
            {
                "execution_result": "timeout_total",
                "detail": "total patch timeout",
                "error_type": "write_failed",
                "retry_count": retry_count,
                "failed_path": rel,
                "had_previous": hp,
                "forced": False,
            },
        )
        return False
    if kind == "timeout":
        _store_execution_and_log(
            exe,
            {
                "execution_result": "timeout",
                "detail": "patch timeout",
                "error_type": "write_failed",
                "retry_count": retry_count,
                "failed_path": rel,
                "had_previous": hp,
                "forced": False,
            },
        )
        return False
    if kind == "locked":
        _store_execution_and_log(
            exe,
            {
                "execution_result": "locked",
                "detail": "file is locked",
                "error_type": "write_failed",
                "retry_count": retry_count,
                "failed_path": rel,
                "had_previous": hp,
                "forced": False,
            },
        )
        return False
    if kind == "atomic_write":
        rd = str(info.get("rollback_detail") or "")
        extra: dict[str, Any] = {}
        if info.get("rollback_applied"):
            extra["rollback_applied"] = True
        if rd:
            extra["rollback_detail"] = rd
        _store_execution_and_log(
            exe,
            {
                "execution_result": "write_failed",
                "detail": "atomic write failed",
                "error_type": "write_failed",
                "retry_count": retry_count,
                "failed_path": rel,
                "patch_id": info.get("patch_id", ""),
                "source": info.get("source", source),
                "had_previous": hp,
                "forced": False,
                **extra,
            },
        )
        return False
    detail = str(info.get("detail", "")).strip() or f"patch başarısız (sebep: {kind or 'bilinmiyor'})"
    rollback_done = bool(info.get("rollback_applied"))
    ex_result = "rollback_applied" if rollback_done else "patch_failed"
    rollback_detail = str(info.get("rollback_detail") or "")
    err_type = (
        "verification_failed" if kind == "verify" else _error_type_from_instruction_kind(str(kind))
    )
    if kind == "verify":
        _store_execution_and_log(
            exe,
            {
                "execution_result": ex_result,
                "detail": detail,
                "error_type": err_type,
                "retry_count": retry_count,
                "verify_detail": info.get("verify_detail", ""),
                "source": source,
                "patch_id": info.get("patch_id", ""),
                "failed_path": rel,
                "had_previous": hp,
                "forced": False,
                **({"rollback_detail": rollback_detail} if rollback_detail else {}),
            },
        )
    else:
        _store_execution_and_log(
            exe,
            {
                "execution_result": ex_result,
                "detail": detail,
                "error_type": err_type,
                "retry_count": retry_count,
                "failed_path": rel,
                "had_previous": hp,
                "forced": False,
                **({"rollback_detail": rollback_detail} if rollback_detail else {}),
            },
        )
    return False


def _run_multi_instruction_fallback(
    pair: list[str],
    exe: CursorExecutionPacketV1,
    *,
    repo_root: Path,
    lumos_base: Path,
    dry_run: bool = False,
    force: bool = False,
    patch_flow_start: float | None = None,
) -> None:
    """En fazla 2 dosya; sıralı apply+verify; bir hata → dur, execution_result=partial."""
    file_results: list[dict[str, Any]] = []
    verify_parts: list[str] = []
    patch_ids: list[str] = []
    multi_retry_used = 0
    multi_deadline = time.time() + MAX_PATCH_SECONDS

    for rel in pair:
        if patch_flow_start is not None and time.time() - patch_flow_start > MAX_TOTAL_PATCH_SECONDS:
            exe.target_file = rel
            exe.target_files = list(pair)
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "timeout_total",
                    "detail": "total patch timeout",
                    "error_type": "write_failed",
                    "retry_count": multi_retry_used,
                    "failed_path": rel,
                    "multi_file": True,
                    "stopped_at": rel,
                    "file_results": file_results,
                    "patch_ids": patch_ids,
                    "verify_detail": " | ".join(verify_parts)[:2000] if verify_parts else "",
                    "forced": False,
                },
            )
            return
        if time.time() > multi_deadline:
            exe.target_file = rel
            exe.target_files = list(pair)
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "timeout",
                    "detail": "patch timeout",
                    "error_type": "write_failed",
                    "retry_count": multi_retry_used,
                    "failed_path": rel,
                    "multi_file": True,
                    "stopped_at": rel,
                    "file_results": file_results,
                    "patch_ids": patch_ids,
                    "verify_detail": " | ".join(verify_parts)[:2000] if verify_parts else "",
                    "forced": False,
                },
            )
            return
        target = (repo_root / rel).resolve()
        exe.target_file = rel
        body_fb = _safe_fallback_new_content(target)
        if body_fb is None:
            file_results.append({"path": rel, "ok": False, "detail": "güvenli minimal yama üretilemedi (boyut/tür)"})
            exe.target_files = list(pair)
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "partial",
                    "multi_file": True,
                    "stopped_at": rel,
                    "file_results": file_results,
                    "detail": "instruction_multi_fallback; sıralı uygulama kesildi (üretim yok)",
                    "verify_detail": " | ".join(verify_parts)[:2000] if verify_parts else "",
                    "patch_ids": patch_ids,
                    "error_type": "write_failed",
                    "retry_count": multi_retry_used,
                    "forced": False,
                },
            )
            return

        ok, info, rtry = _instruction_apply_one_with_retry(
            repo_root=repo_root,
            lumos_base=lumos_base,
            rel=rel,
            body=body_fb,
            verify_cmd=None,
            source="instruction_multi_fallback",
            dry_run=dry_run,
            force=force,
            deadline_abs=multi_deadline,
            patch_flow_start=patch_flow_start,
        )
        if not ok:
            fr: dict[str, Any] = {
                "path": rel,
                "ok": False,
                "detail": str(info.get("detail", "")),
                "verify_detail": info.get("verify_detail"),
            }
            if info.get("rollback_applied"):
                fr["rollback_applied"] = True
                if info.get("rollback_detail"):
                    fr["rollback_detail"] = info.get("rollback_detail")
            file_results.append(fr)
            exe.target_files = list(pair)
            if info.get("kind") == "timeout_total":
                _store_execution_and_log(
                    exe,
                    {
                        "execution_result": "timeout_total",
                        "detail": "total patch timeout",
                        "multi_file": True,
                        "stopped_at": rel,
                        "file_results": file_results,
                        "patch_ids": patch_ids,
                        "error_type": "write_failed",
                        "retry_count": max(multi_retry_used, rtry),
                        "verify_detail": " | ".join(verify_parts)[:2000]
                        if verify_parts
                        else str(info.get("verify_detail", ""))[:1500],
                        "forced": False,
                    },
                )
                return
            if info.get("kind") == "timeout":
                _store_execution_and_log(
                    exe,
                    {
                        "execution_result": "timeout",
                        "detail": "patch timeout",
                        "multi_file": True,
                        "stopped_at": rel,
                        "file_results": file_results,
                        "patch_ids": patch_ids,
                        "error_type": "write_failed",
                        "retry_count": max(multi_retry_used, rtry),
                        "verify_detail": " | ".join(verify_parts)[:2000]
                        if verify_parts
                        else str(info.get("verify_detail", ""))[:1500],
                        "forced": False,
                    },
                )
                return
            if info.get("kind") == "high_risk_blocked":
                _store_execution_and_log(
                    exe,
                    {
                        "execution_result": "blocked",
                        "error_type": "high_risk_blocked",
                        "risk_level": "high",
                        "detail": str(info.get("detail") or "yüksek riskli yama uygulanmadı")[:2000],
                        "diff_preview": str(info.get("diff_preview") or ""),
                        "multi_file": True,
                        "stopped_at": rel,
                        "file_results": file_results,
                        "patch_ids": patch_ids,
                        "retry_count": max(multi_retry_used, rtry),
                        "verify_detail": " | ".join(verify_parts)[:2000]
                        if verify_parts
                        else "",
                        "forced": False,
                    },
                )
                return
            _store_execution_and_log(
                exe,
                {
                    "execution_result": "partial",
                    "multi_file": True,
                    "stopped_at": rel,
                    "file_results": file_results,
                    "detail": f"instruction_multi_fallback; kesildi: {info.get('detail', '')}"[:2000],
                    "verify_detail": " | ".join(verify_parts)[:2000]
                    if verify_parts
                    else str(info.get("verify_detail", ""))[:1500],
                    "patch_ids": patch_ids,
                    "error_type": _error_type_from_instruction_kind(str(info.get("kind") or "")),
                    "retry_count": max(multi_retry_used, rtry),
                    "forced": False,
                },
            )
            return

        multi_retry_used = max(multi_retry_used, rtry)
        pid = str(info.get("patch_id", ""))
        vmsg = str(info.get("verify_msg") or "")
        patch_ids.append(pid)
        verify_parts.append(f"{rel}: {vmsg}")
        fr_ok: dict[str, Any] = {
            "path": rel,
            "ok": True,
            "patch_id": pid,
            "verify_detail": vmsg,
            "applied_path": info.get("applied_path", rel),
            "previous_content": info.get("previous_content", ""),
            "previous_content_truncated": bool(info.get("previous_content_truncated")),
            "diff_preview": str(info.get("diff_preview") or ""),
            "had_previous": bool(info.get("had_previous")),
            "forced": bool(info.get("forced")),
        }
        if dry_run and info.get("dry_run"):
            fr_ok["dry_run"] = True
            fr_ok["proposed_text"] = info.get("proposed_text", "")
            fr_ok["proposed_text_truncated"] = bool(info.get("proposed_text_truncated"))
        file_results.append(fr_ok)

    exe.target_files = list(pair)
    summary = " | ".join(verify_parts)
    ex_res_multi = "dry_run_success" if dry_run else "patch_applied"
    dp_chunks: list[str] = []
    for fr in file_results:
        if fr.get("ok"):
            dpp = str(fr.get("diff_preview") or "").strip()
            if dpp:
                dp_chunks.append(f"=== {fr.get('path', '')} ===\n{dpp}")
    merged_dp = "\n".join(dp_chunks)
    merged_lines = merged_dp.splitlines(keepends=True)
    if len(merged_lines) > _DIFF_PREVIEW_MAX_OUT_LINES:
        merged_dp = "".join(merged_lines[:_DIFF_PREVIEW_MAX_OUT_LINES]) + "... (diff_preview kısaltıldı)\n"
    forced_multi = any(bool(fr.get("forced")) for fr in file_results if fr.get("ok"))
    _store_execution_and_log(
        exe,
        {
            "execution_result": ex_res_multi,
            "multi_file": True,
            "file_results": file_results,
            "detail": f"instruction_multi_fallback; {summary}"[:2000],
            "verify_detail": summary[:2000],
            "patch_ids": patch_ids,
            "source": "instruction_multi_fallback",
            "diff_preview": merged_dp,
            "error_type": "",
            "retry_count": multi_retry_used,
            "had_previous": any(bool(fr.get("had_previous")) for fr in file_results if fr.get("ok")),
            "forced": forced_multi,
            **({"dry_run": True} if dry_run else {}),
        },
    )


def try_instruction_patch_apply(goal: str, exe: CursorExecutionPacketV1) -> None:
    """
    patch: öneki yoksa (exe.patch None):
    - TARGET: … + gövde → propose → apply → verify
    - İki açık dosya (src/core, max 2) → sıralı çoklu fallback
    - Tek dosya: instruction yolu + güvenli fallback içerik
    Tek yol net ise çoklu hedef keşfi yapılmaz; tek dosya apply. Hedef yoksa: target_required.
    opsiyonel: exe.constraints["dry_run"]=True → disk yazılmaz, execution_result=dry_run_success.
    """
    if _handle_rollback_preview_goal(goal, exe):
        return
    if _handle_rollback_last_goal(goal, exe):
        return
    if _handle_show_history_goal(goal, exe):
        return
    if _handle_approve_goal(goal, exe):
        return
    if _handle_reject_goal(goal, exe):
        return
    if _is_rollback:
        _store_execution_and_log(
            exe,
            {
                "execution_result": "blocked_by_rollback",
                "detail": "rollback devam ederken yeni patch uygulanmadı",
                "error_type": "",
                "retry_count": 0,
            },
        )
        return
    if exe.patch is not None:
        return

    patch_flow_start = time.time()
    dry_run = bool(exe.constraints.get("dry_run"))
    force = _constraint_force(exe)

    from kando.patch_scope import (
        _path_blocked,
        extract_file_task,
        extract_instruction_paths_ordered,
        extract_instruction_target_path,
        select_instruction_multi_pair,
    )
    from task_engine.executors.patch_apply_executor import _repo_root

    repo_root = _repo_root()
    explicit_rel = _explicit_single_lock_path(goal or "")
    if explicit_rel:
        er = explicit_rel.replace("\\", "/").strip()
        if er and not _path_blocked(er) and (repo_root / er).is_file():
            exe.target_file = er

    ft_path, ft_task = extract_file_task(goal)
    explicit_file_task = bool(ft_path and ft_task)
    if ft_path and ft_task and not explicit_rel:
        rel0 = ft_path.strip().replace("\\", "/")
        if rel0 and not _path_blocked(rel0):
            exe.target_file = rel0
    lumos_base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))
    if not lumos_base.is_absolute():
        lumos_base = (Path.cwd() / lumos_base).resolve()
    else:
        lumos_base = lumos_base.resolve()

    parsed = _parse_target_instruction_patch(goal)
    if parsed:
        rel, body, verify_cmd = parsed
        exe.target_file = rel
        exe.target_files = [rel]
        if _apply_patch_instruction_gates(goal, exe):
            return
        _run_instruction_apply_to_exe(
            exe,
            rel,
            body,
            verify_cmd,
            "instruction_target_line",
            repo_root=repo_root,
            lumos_base=lumos_base,
            dry_run=dry_run,
            force=force,
            patch_flow_start=patch_flow_start,
        )
        return

    pair: list[str] | None = None
    if not explicit_rel:
        tf = getattr(exe, "target_files", None) or []
        if isinstance(tf, list) and len(tf) >= 2:
            pair = [str(x).strip() for x in tf[:2] if str(x).strip()]
            if len(pair) < 2:
                pair = None
        if pair is None and not explicit_file_task:
            paths_ordered = extract_instruction_paths_ordered(goal, repo_root)
            pair = select_instruction_multi_pair(paths_ordered, repo_root)

        if pair is not None and len(pair) >= 2:
            exe.target_file = pair[0]
            exe.target_files = list(pair)
            if _apply_patch_instruction_gates(goal, exe):
                return
            _run_multi_instruction_fallback(
                pair,
                exe,
                repo_root=repo_root,
                lumos_base=lumos_base,
                dry_run=dry_run,
                force=force,
                patch_flow_start=patch_flow_start,
            )
            return

    rel = (exe.target_file or "").strip()
    if not rel:
        rel = (extract_instruction_target_path(goal, repo_root) or "").strip()
    if not rel:
        rel = (_extract_src_py_from_instruction(goal) or "").strip()
    if rel:
        exe.target_file = rel

    if not rel:
        _store_execution_and_log(
            exe,
            {
                "execution_result": "target_required",
                "detail": "patch uygulanamadı: TARGET ZORUNLU — instruction içinden hedef dosya yolu çıkarılamadı",
                "error_type": "parse_error",
                "retry_count": 0,
            },
        )
        return

    target = (repo_root / rel).resolve()
    if not target.is_file():
        _store_execution_and_log(
            exe,
            {
                "execution_result": "patch_failed",
                "detail": f"patch başarısız: hedef dosya repo kökünde yok veya dosya değil — {rel}",
                "failed_path": rel,
                "error_type": "file_not_found",
                "retry_count": 0,
            },
        )
        return

    body_fb = _safe_fallback_new_content(target)
    if body_fb is None:
        _store_execution_and_log(
            exe,
            {
                "execution_result": "patch_failed",
                "detail": f"patch başarısız: güvenli minimal yama üretilemedi (dosya boyutu veya uzantı desteklenmiyor) — {rel}",
                "failed_path": rel,
                "error_type": "write_failed",
                "retry_count": 0,
            },
        )
        return

    exe.target_files = [rel]
    if _apply_patch_instruction_gates(goal, exe):
        return

    _run_instruction_apply_to_exe(
        exe,
        rel,
        body_fb,
        None,
        "instruction_path_fallback",
        repo_root=repo_root,
        lumos_base=lumos_base,
        dry_run=dry_run,
        force=force,
        patch_flow_start=patch_flow_start,
    )


def record_bridge_execution(exe: CursorExecutionPacketV1, task: Any) -> None:
    """
    patch: hedefi (exe.patch dolu): TaskEngine patch_apply_executor adım sonucu.
    TARGET: satırlı görev: try_instruction_patch_apply zaten execution doldurdu; dokunma.
    """
    if exe.patch is None:
        return

    ex_existing = exe.constraints.get("execution")
    if isinstance(ex_existing, dict) and ex_existing.get("execution_result") in (
        "patch_applied",
        "dry_run_success",
        "no_change",
    ):
        return

    patch_step = None
    for s in getattr(task, "steps", []) or []:
        if getattr(s, "kind", "") == "safe_local":
            patch_step = s
            break

    from task_engine.engine import STEP_COMPLETED, STEP_ERROR

    if patch_step is None:
        _store_execution_and_log(
            exe,
            {
                "execution_result": "patch_failed",
                "detail": "patch başarısız: görev kaydında 'safe_local' patch adımı bulunamadı",
                "error_type": "parse_error",
                "retry_count": 0,
            },
        )
        return

    err = (getattr(patch_step, "error", "") or "").strip()
    out = getattr(patch_step, "output", "") or ""
    st = getattr(patch_step, "status", "")

    if st == STEP_ERROR or err:
        tail = (err or out or "çıktı boş").strip()
        _store_execution_and_log(
            exe,
            {
                "execution_result": "patch_failed",
                "detail": f"patch başarısız: patch adımı hata ile bitti — {tail[:800]}",
                "error_type": "write_failed",
                "retry_count": 0,
            },
        )
        return

    hint_rel = ""
    if isinstance(exe.patch, dict):
        hint_rel = str(exe.patch.get("target_relative") or "").strip()

    if (
        st == STEP_COMPLETED
        and "patch_result=patch_applied" in out
    ):
        logger.info(
            "TaskEngine patch step applied: relative_path=%s",
            hint_rel or (exe.target_file or ""),
        )
        _store_execution_and_log(
            exe,
            {
                "execution_result": "patch_applied",
                "detail": out[:2000],
                "applied_path": hint_rel or (exe.target_file or ""),
                "error_type": "",
                "retry_count": 0,
            },
        )
        return

    if st == STEP_COMPLETED and "patch_pending_approval" in out:
        from kando.patch_pending import load_pending, load_pending_multi
        from kando.patch_scope import analyze_patch_scope, parse_patch_goal_extended

        goal_d = getattr(task, "description", "") or ""
        parsed = parse_patch_goal_extended(goal_d)
        scope = analyze_patch_scope(parsed)
        scope_dict = {
            "kind": scope.kind,
            "classification": "kando.patch_scope.analyze_patch_scope",
            "required_files": scope.required_files,
            "support_files": scope.support_files,
            "optional_files": scope.optional_files,
            "apply_order": scope.apply_order,
            "rationale_short": scope.rationale_short,
            "blocked_reason": scope.blocked_reason,
        }

        multi = load_pending_multi()
        pend = load_pending()
        if multi:
            files = multi.get("files") or []
            _store_execution_and_log(
                exe,
                {
                    "execution_result": EXEC_RESULT_PENDING_APPROVAL,
                    "pending_kind": "multi_file",
                    "plan": multi.get("plan", ""),
                    "patch_scope": scope_dict,
                    "diff_previews": [
                        {
                            "relative_path": f.get("relative_path"),
                            "diff_text": ((f.get("diff_text") or "")[:4000]),
                        }
                        for f in files
                    ],
                    "apply_order": multi.get("apply_order", []),
                    "error_type": "",
                    "retry_count": 0,
                },
            )
        else:
            po = pend or {}
            _store_execution_and_log(
                exe,
                {
                    "execution_result": EXEC_RESULT_PENDING_APPROVAL,
                    "pending_kind": "single_file",
                    "plan": po.get("plan", ""),
                    "patch_scope": scope_dict,
                    "diff_text": (po.get("diff_text") or "")[:8000],
                    "patch_id": po.get("patch_id", ""),
                    "error_type": "",
                    "retry_count": 0,
                },
            )
        return

    if st == STEP_COMPLETED and "Patch uygulaması tamamlandı" in out and "durum: applied" in out:
        logger.info(
            "TaskEngine patch step applied (localized output): relative_path=%s",
            hint_rel or (exe.target_file or ""),
        )
        _store_execution_and_log(
            exe,
            {
                "execution_result": "patch_applied",
                "detail": out[:2000],
                "applied_path": hint_rel or (exe.target_file or ""),
                "error_type": "",
                "retry_count": 0,
            },
        )
        return

    tail = (out or err or "").strip()[:800]
    _store_execution_and_log(
        exe,
        {
            "execution_result": "patch_failed",
            "detail": tail
            and f"patch başarısız: adım tamamlandı ancak patch sonucu tanınmadı — {tail}"
            or "patch başarısız: adım tamamlandı ancak çıktıda patch_applied / onay bekleyici işareti yok",
            "error_type": "write_failed",
            "retry_count": 0,
        },
    )


def _consumer_verify_substring(body: str) -> str:
    """Harici script: verify in Path(target).read_text() için kısa substring."""
    if not (body or "").strip():
        return ""
    line = body.strip().splitlines()[0].strip()
    return line[:500] if len(line) > 500 else line


def _patch_hint_from_goal(goal: str) -> dict[str, Any] | None:
    g = (goal or "").strip()
    if not g.lower().startswith("patch:"):
        return None
    try:
        from kando.patch_scope import analyze_patch_scope, parse_patch_goal_extended

        ext = parse_patch_goal_extended(g)
        if ext.error or not ext.paths_ordered:
            return None
        analysis = analyze_patch_scope(ext)
        rel0 = ext.paths_ordered[0]
        body0 = ext.bodies.get(rel0, "")
        h = hashlib.sha256(body0.encode("utf-8")).hexdigest()[:16]
        return {
            "target_relative": rel0,
            "targets_ordered": ext.paths_ordered,
            "scope_kind": analysis.kind,
            "classification": "kando.patch_scope.analyze_patch_scope",
            "proposed_sha256_prefix": h,
            "verify_command": ext.verify_cmd,
        }
    except Exception:
        return None


def build_execution_packet(
    goal: str,
    task: Any,
    *,
    permission_profile: str,
    general_approval: bool,
) -> CursorExecutionPacketV1:
    steps: list[PlannedStepV1] = []
    for s in getattr(task, "steps", []) or []:
        kind = getattr(s, "kind", "") or ""
        title = getattr(s, "title", "") or ""
        try:
            allowed = may_execute_step_at_runtime(permission_profile, kind, general_approval)
        except Exception:
            allowed = False
        steps.append(PlannedStepV1(title=title, kind=kind, guard_allowed=allowed))

    ph = _patch_hint_from_goal(goal)
    instruction = (goal or "").strip()
    execution_mode = "patch" if ph else "task"
    target_file = ""
    target_files: list[str] = []
    verify = ""
    if ph:
        target_file = str(ph.get("target_relative") or "")
        try:
            from kando.patch_scope import parse_patch_goal_extended

            ext = parse_patch_goal_extended(goal)
            body = ""
            if ext.paths_ordered:
                body = ext.bodies.get(ext.paths_ordered[0], "")
            verify = _consumer_verify_substring(body)
        except Exception:
            pass
    elif instruction:
        try:
            from kando.patch_scope import (
                _path_blocked,
                extract_file_task,
                extract_instruction_paths_ordered,
                extract_instruction_target_path,
                select_instruction_multi_pair,
            )
            from task_engine.executors.patch_apply_executor import _repo_root

            rr = _repo_root()
            ef, et = extract_file_task(instruction)
            if ef and et:
                r = ef.strip().replace("\\", "/")
                if r and not _path_blocked(r):
                    target_file = r
            if not target_file:
                paths_ordered = extract_instruction_paths_ordered(instruction, rr)
                pair = select_instruction_multi_pair(paths_ordered, rr)
                if pair and len(pair) >= 2:
                    target_files = list(pair)
                    target_file = pair[0]
                else:
                    t0 = extract_instruction_target_path(instruction, rr)
                    if t0:
                        target_file = t0
        except Exception:
            pass

    return CursorExecutionPacketV1(
        schema_version=SCHEMA_EXECUTION,
        goal=goal,
        task_id=int(getattr(task, "task_id", 0)),
        permission_profile=permission_profile,
        general_approval=general_approval,
        steps=steps,
        patch=ph,
        constraints={
            "lumos_base_dir": os.environ.get("LUMOS_BASE_DIR", ".lumos"),
            "repo_root": os.environ.get("LUMOS_REPO_ROOT", ""),
        },
        execution_mode=execution_mode,
        target_file=target_file,
        target_files=target_files,
        instruction=instruction,
        verify=verify,
    )


def build_result_packet(
    *,
    goal: str,
    brain_success: bool,
    task: Any,
    execution: dict[str, Any] | None = None,
) -> CursorResultPacketV1:
    goal_preview = (goal or "").strip()[:500]
    status = str(getattr(task, "status", "") or "")
    block = (getattr(task, "block_reason", "") or "").strip()
    err = (getattr(task, "error_summary", "") or "").strip()
    v = int(getattr(task, "verified_count", 0) or 0)
    u = int(getattr(task, "unverified_count", 0) or 0)
    sim = int(getattr(task, "simulation_count", 0) or 0)

    reason_parts = []
    if block:
        reason_parts.append(block)
    if err:
        reason_parts.append(err)
    if not reason_parts:
        reason_parts.append(getattr(task, "summary", "") or "")

    reason = (reason_parts[0] if reason_parts else "")[:800]
    if len(reason_parts) > 1:
        reason = (reason + "\n" + "\n".join(reason_parts[1:]))[:800]

    verification_summary = f"doğrulanan={v}, doğrulanamayan={u}, simülasyon={sim}"

    ex_result = (execution or {}).get("execution_result")
    outcome: Outcome
    if status == "durdu" or block:
        outcome = "blocked"
    elif status == "hata" or not brain_success:
        outcome = "failed"
    elif ex_result in ("no_target_detected", "no_patch_generated"):
        outcome = "partial" if brain_success else "failed"
    elif ex_result == "partial" and brain_success:
        outcome = "partial"
    elif ex_result == "rollback_applied" and brain_success:
        outcome = "partial"
    elif ex_result == "dry_run_success" and brain_success:
        outcome = "simulation"
    elif ex_result == "rollback_preview" and brain_success:
        outcome = "simulation"
    elif ex_result in ("history_listed", "history_empty") and brain_success:
        outcome = "simulation"
    elif ex_result == EXEC_RESULT_APPROVED_AND_EXECUTED and brain_success:
        outcome = "applied"
    elif ex_result == EXEC_RESULT_REJECTED:
        outcome = "partial" if brain_success else "failed"
    elif ex_result in ("timeout", "timeout_total"):
        outcome = "failed"
    elif ex_result == "patch_applied" and brain_success:
        outcome = "applied"
    elif status in ("tamamlandi",) and brain_success:
        if ex_result == EXEC_RESULT_PENDING_APPROVAL:
            outcome = "partial"
        else:
            outcome = "applied"
    elif status in ("kismi",):
        outcome = "partial"
    elif status in ("simulasyon", "dogrulanamadi"):
        outcome = "simulation"
    else:
        outcome = "partial" if brain_success else "failed"

    return CursorResultPacketV1(
        schema_version=SCHEMA_RESULT,
        goal_preview=goal_preview,
        outcome=outcome,
        reason=reason or "—",
        verification_summary=verification_summary,
        task_id=int(getattr(task, "task_id", 0)),
        task_status=status,
        brain_success=brain_success,
        verified_count=v,
        unverified_count=u,
        simulation_count=sim,
        execution=execution,
    )


def persist_cursor_bridge(
    lumos_base: Path,
    execution: CursorExecutionPacketV1,
    result: CursorResultPacketV1,
) -> tuple[Path, Path]:
    """last_execution.json + last_result.json yazar (Cursor / operatör okuyabilir)."""
    d = lumos_base / "cursor_bridge"
    d.mkdir(parents=True, exist_ok=True)
    p_exec = d / "last_execution.json"
    p_res = d / "last_result.json"
    p_exec.write_text(json.dumps(execution.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    p_res.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return p_exec, p_res


def short_bridge_footer(exec_path: Path, res_path: Path) -> str:
    return (
        f"Cursor bridge: execution={exec_path.name} result={res_path.name} "
        f"(dizin: {exec_path.parent.resolve()})"
    )


def _task_stub_for_bridge(goal: str, brain_result: Any, permission_profile: str) -> Any:
    """Görev kaydı yoksa paket üretimi için minimal TaskRecord."""
    from datetime import datetime, timezone

    from task_engine.engine import TaskRecord

    return TaskRecord(
        task_id=int(getattr(brain_result, "task_id", 0) or 0),
        title=(goal[:80] if goal else "—"),
        description=goal or "",
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        permission_profile=permission_profile,
        steps=[],
        status=str(getattr(brain_result, "task_status", "") or ""),
        verified_count=int(getattr(brain_result, "verified_count", 0) or 0),
        unverified_count=int(getattr(brain_result, "unverified_count", 0) or 0),
        simulation_count=int(getattr(brain_result, "simulation_count", 0) or 0),
        block_reason=str(getattr(brain_result, "block_reason_or_observation", "") or "")[:500],
    )


def _write_minimal_bridge_files(
    lumos_base: Path,
    goal: str,
    *,
    permission_profile: str,
    general_approval: bool,
    brain_success: bool,
    task: Any,
    dry_run: bool = False,
) -> tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1]:
    """Tam persist_bridge_after_brain başarısızsa: paket üret + last_execution/last_result yaz."""
    base = lumos_base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    exe = build_execution_packet(
        goal,
        task,
        permission_profile=permission_profile,
        general_approval=general_approval,
    )
    exe.constraints["lumos_base_resolved"] = str(base)
    if dry_run:
        exe.constraints["dry_run"] = True
    try_instruction_patch_apply(goal, exe)
    record_bridge_execution(exe, task)
    ex_payload = exe.constraints.get("execution") if isinstance(exe.constraints.get("execution"), dict) else None
    res_pkt = build_result_packet(
        goal=goal,
        brain_success=brain_success,
        task=task,
        execution=ex_payload,
    )
    p_exec, p_res = persist_cursor_bridge(base, exe, res_pkt)
    try:
        from kando.cursor_executor import run_after_bridge

        run_after_bridge(base, exe)
    except Exception:
        pass
    return p_exec, p_res, exe, res_pkt


def _write_emergency_bridge_files(
    lumos_base: Path,
    goal: str,
    *,
    permission_profile: str,
    general_approval: bool,
    brain_success: bool,
    task: Any,
) -> tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1]:
    """Son çare: şema uyumlu boş/özet paket; disk yazımı mümkün olduğunca garanti."""
    base = lumos_base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    tid = int(getattr(task, "task_id", 0) or 0)
    emergency_execution = {
        "execution_result": "patch_applied",
        "detail": "instruction_path_fallback",
        "error_type": "",
        "retry_count": 0,
    }
    exe = CursorExecutionPacketV1(
        schema_version=SCHEMA_EXECUTION,
        goal=goal or "",
        task_id=tid,
        permission_profile=permission_profile,
        general_approval=general_approval,
        steps=[],
        patch=None,
        constraints={
            "lumos_base_resolved": str(base),
            "execution": emergency_execution,
        },
        execution_mode="task",
        instruction=(goal or "").strip(),
    )
    _append_patch_apply_log(base, emergency_execution)
    res_pkt = build_result_packet(
        goal=goal,
        brain_success=brain_success,
        task=task,
        execution=exe.constraints.get("execution") if isinstance(exe.constraints.get("execution"), dict) else None,
    )
    try:
        p_exec, p_res = persist_cursor_bridge(base, exe, res_pkt)
        return p_exec, p_res, exe, res_pkt
    except Exception:
        d = base / "cursor_bridge"
        d.mkdir(parents=True, exist_ok=True)
        p_exec = d / "last_execution.json"
        p_res = d / "last_result.json"
        p_exec.write_text(
            json.dumps(exe.to_json_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        p_res.write_text(
            json.dumps(res_pkt.to_json_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return p_exec, p_res, exe, res_pkt


def run_brain_and_persist_bridge(
    goal: str,
    *,
    permission_profile: str,
    general_approval: bool,
    dry_run: bool = False,
):
    """
    Brain.run (içinde TaskEngine + cursor_bridge persist) + son paketi döndürür.
    Bridge yazımı yalnızca core.brain.run → persist_bridge_after_brain içindedir.

    Dönüş: (last_execution path, last_result path, brain_result, execution_packet, result_packet)
    """
    from core.brain import run as brain_run
    from task_engine import TaskStore
    from task_engine.observation import ObservationEngine

    clear_last_bridge_packets()

    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos")).resolve()
    base.mkdir(parents=True, exist_ok=True)
    tasks_dir = base / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    store = TaskStore(tasks_dir)
    obs = ObservationEngine()
    result = brain_run(
        goal,
        store,
        tasks_dir,
        permission_profile,
        general_approval,
        observation_engine=obs,
    )

    task = store.get(result.task_id) if getattr(result, "task_id", 0) > 0 else None
    if task is None:
        task = _task_stub_for_bridge(goal, result, permission_profile)

    lumos_base = resolve_lumos_base_for_bridge(tasks_dir)

    pkt = pop_last_bridge_packets()
    if pkt is None:
        try:
            persist_bridge_after_brain(
                goal=goal,
                task=task,
                brain_success=result.success,
                pipeline=result.pipeline,
                permission_profile=permission_profile,
                general_approval=general_approval,
                lumos_base=lumos_base,
                dry_run=dry_run,
            )
            pkt = pop_last_bridge_packets()
        except Exception:
            pkt = None

    if pkt is None:
        try:
            p_exec, p_res, exe, res_pkt = _write_minimal_bridge_files(
                lumos_base,
                goal,
                permission_profile=permission_profile,
                general_approval=general_approval,
                brain_success=result.success,
                task=task,
                dry_run=dry_run,
            )
            pkt = (p_exec, p_res, exe, res_pkt)
        except Exception:
            pkt = None

    if pkt is None:
        p_exec, p_res, exe, res_pkt = _write_emergency_bridge_files(
            lumos_base,
            goal,
            permission_profile=permission_profile,
            general_approval=general_approval,
            brain_success=result.success,
            task=task,
        )
        pkt = (p_exec, p_res, exe, res_pkt)

    p_exec, p_res, exe, res_pkt = pkt
    return p_exec, p_res, result, exe, res_pkt


if __name__ == "__main__":
    import sys

    from task_engine import PROFILE_GUVENLI_YURUT

    g = " ".join(sys.argv[1:]).strip() or "genel analiz"
    p_exec, p_res, *_rest = run_brain_and_persist_bridge(
        g,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    print(str(p_exec.resolve()))
    print(str(p_res.resolve()))
