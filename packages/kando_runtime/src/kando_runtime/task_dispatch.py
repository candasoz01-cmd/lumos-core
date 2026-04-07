"""
Execution dispatch: karar (Lumos gate) ile yürütme yönlendirmesi ayrı tutulur.

task_type alanı → doğru executor: file | shell | video | image | generic.
İstemci JSON'da task_type verirse (video|image|file|shell|generic|media) öncelikli kullanılır.

system / örtük mod: normalized_task, execution_plan (patch adımı), reasoning_snapshot.intent
ve metin ipuçları ile file_executor vs shell_executor seçilir; belirsiz / çakışma → generic
(system_execution çalıştırılmaz).

Görev tipi çıkarıldıktan sonra dispatch_execution_plan üretilir (action, target,
executor_type, risk, execution_permitted). file/shell için yalnızca low risk doğrudan
yürütülür; medium risk requires_dispatch_approval ile bekler (bridge onay dosyası).
high/blocked/bilinmeyen → execution_permitted false.

Onaydan sonra gate http_body risk_level düşürülerek (ör. low) aynı plan dispatch_task ile
yeniden çalıştırılır.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

DISPATCH_PENDING_APPROVAL_SCHEMA = "lumos.dispatch_pending_approval.v1"

TaskType = Literal["video", "image", "audio", "file", "shell", "generic"]
QueueName = Literal[
    "video_executor_pending",
    "image_executor_pending",
    "audio_executor_pending",
    "file_executor_pending",
    "file_approval_pending",
    "shell_executor_pending",
    "shell_approval_pending",
    "clarification_pending",
    "generic_pending",
]

_EXPLICIT_TASK_TYPES: frozenset[str] = frozenset(
    {"video", "image", "audio", "file", "shell", "generic", "media", "system"}
)

_VIDEO_HINT_RE = re.compile(
    r"(?:"
    r"\b(?:video|film|klip|ffmpeg|render)\b|"
    r"\b\d{3,4}p\b|\b\d+[.:]\d+p\b|\b\d{2,4}k\b|"
    r"\bfps\b|"
    r"\b(?:üret|oluştur|olustur)\b\s+\S*\s*\b(?:video|film|klip)\b|"
    r"\b(?:video|film|klip)\b\s+\S*\s*\b(?:üret|oluştur|olustur)\b"
    r")",
    re.I,
)
_IMAGE_HINT_RE = re.compile(
    r"\b(?:"
    r"görsel|gorsel|resim|thumbnail|logo|ikon|png|jpe?g|gif|webp|svg|image|ascii\s*art"
    r")\b",
    re.I,
)
_AUDIO_HINT_RE = re.compile(
    r"\b(?:ses|şarkı|sarki|podcast|müzik|muzik|audio|tts|konuşma|konusma|mp3|wav|ogg)\b",
    re.I,
)
_SHELL_HINT_RE = re.compile(
    r"(?:"
    r"^\s*(?:pwd|date|uname|echo|true|false)\b"
    r"|\b(?:komut|command)\s*(?:çalıştır|calistir|run)\b|"
    r"^\s*run\s*[:：]\s*.+"
    r"|\b(?:shell|terminal)\b"
    r"|\b(?:chmod|chown|sudo)\b"
    r")",
    re.I | re.M,
)
_FILE_HINT_RE = re.compile(
    r"(?:"
    r"\b(?:sil|delete|remove|unlink|trash)\b|"
    r"(^|\s)rm\s|"
    r"\b(?:dosya|dosyalar|klasör|klasor|file|folder)\b.*\b(?:sil|delete|remove|yaz|patch|düzenle|duzenle)\b|"
    r"\b(?:sil|delete|remove|yaz|patch)\b.*\b(?:dosya|dosyalar|klasör|klasor|file)\b|"
    r"\b(?:oluştur|olustur|yarat|create)\b.*\.\w{2,16}\b|"
    r"\.\w{2,16}\b.*\b(?:oluştur|olustur|yarat|create)\b|"
    r"\b(?:dosya|file)\b\s+\b(?:oluştur|olustur|yarat|create)\b|"
    r"TARGET:\s*\S+"
    r")",
    re.I,
)

_EXECUTOR_FOR_TYPE: dict[TaskType, str | None] = {
    "video": "video_executor",
    "image": "image_executor",
    "audio": "audio_executor",
    "file": "file_executor",
    "shell": "shell_executor",
    "generic": None,
}


def infer_media_subtype(text: str) -> Literal["video", "image", "audio"]:
    """Açık ipucu yoksa video kuyruğu (geniş medya varsayılanı)."""
    low = (text or "").strip().lower()
    if _VIDEO_HINT_RE.search(low):
        return "video"
    if _IMAGE_HINT_RE.search(low):
        return "image"
    if _AUDIO_HINT_RE.search(low):
        return "audio"
    return "video"


def infer_task_type(text: str) -> TaskType:
    """Öncelik: video → image → audio → shell → file → generic (metin-only; geriye dönük)."""
    low = (text or "").strip().lower()
    if not low:
        return "generic"
    if _VIDEO_HINT_RE.search(low):
        return "video"
    if _IMAGE_HINT_RE.search(low):
        return "image"
    if _AUDIO_HINT_RE.search(low):
        return "audio"
    if _SHELL_HINT_RE.search(low):
        return "shell"
    if _FILE_HINT_RE.search(low):
        return "file"
    return "generic"


def _normalized_task_dict_from_out(out: dict[str, Any]) -> dict[str, Any]:
    hb = out.get("http_body")
    if isinstance(hb, dict):
        nt = hb.get("normalized_task")
        if isinstance(nt, dict) and nt:
            return nt
    pr = out.get("pending_approval_record")
    if isinstance(pr, dict):
        nt = pr.get("normalized_task")
        if isinstance(nt, dict) and nt:
            return nt
    return {}


def _reasoning_snapshot_from_out(out: dict[str, Any]) -> dict[str, Any]:
    pr = out.get("pending_approval_record")
    if isinstance(pr, dict):
        rs = pr.get("reasoning_snapshot")
        if isinstance(rs, dict):
            return rs
    return {}


def _execution_plan_from_out(out: dict[str, Any]) -> dict[str, Any] | None:
    pr = out.get("pending_approval_record")
    if isinstance(pr, dict):
        pl = pr.get("execution_plan")
        if isinstance(pl, dict):
            return pl
    hb = out.get("http_body")
    if isinstance(hb, dict):
        pl = hb.get("execution_plan")
        if isinstance(pl, dict):
            return pl
    return None


def classify_file_shell_dispatch(
    text: str, out: dict[str, Any]
) -> Literal["file", "shell", "neither"]:
    """
    file_executor / shell_executor yönlendirmesi: önce normalized_task, plan ve reasoning;
    sonra metin ipuçları. Çakışma veya belirsiz → neither (executor çalıştırılmaz).
    """
    norm = _normalized_task_dict_from_out(out)
    reasoning = _reasoning_snapshot_from_out(out)
    plan = _execution_plan_from_out(out) or {}

    structured_file = False
    rel = str(norm.get("target_rel") or "").strip()
    mode = str(norm.get("mode") or "").strip().lower()
    frs = str(norm.get("file_read_status") or "").strip().lower()
    if rel and mode == "direct_patch":
        structured_file = True
    if frs == "create_intent":
        structured_file = True

    intent = str(reasoning.get("intent") or "").strip().lower()
    if intent == "structured_patch":
        structured_file = True

    for step in plan.get("steps") or []:
        if isinstance(step, dict) and str(step.get("type") or "").strip().lower() == "patch":
            structured_file = True
            break

    text_l = (text or "").strip()
    if not text_l:
        return "file" if structured_file else "neither"

    text_file = bool(_FILE_HINT_RE.search(text_l))
    text_shell = bool(_SHELL_HINT_RE.search(text_l))

    if structured_file:
        return "file"
    if text_file and text_shell:
        return "neither"
    if text_shell:
        return "shell"
    if text_file:
        return "file"
    return "neither"


def resolve_system_task_type(text: str, out: dict[str, Any]) -> TaskType:
    """system / örtük istemci: medya (metin varsa) → file/shell (yapı + metin) → generic."""
    low = (text or "").strip().lower()
    if low:
        if _VIDEO_HINT_RE.search(low):
            return "video"
        if _IMAGE_HINT_RE.search(low):
            return "image"
        if _AUDIO_HINT_RE.search(low):
            return "audio"
    fs = classify_file_shell_dispatch(text or "", out)
    if fs == "file":
        return "file"
    if fs == "shell":
        return "shell"
    return "generic"


def normalize_client_task_type(raw: str | None) -> TaskType | None:
    """İstemci task_type → dahili TaskType; geçersiz veya system ise None (çıkarsama)."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s or s not in _EXPLICIT_TASK_TYPES:
        return None
    if s in ("video", "image", "audio", "file", "shell", "generic"):
        return cast(TaskType, s)
    if s == "media":
        return None
    if s == "system":
        return None
    return None


def resolve_task_type(
    text: str, explicit: str | None, out: dict[str, Any] | None = None
) -> TaskType:
    """explicit (JSON task_type) varsa ve media değilse doğrudan kullan; media → alt tür; system/örtük → yapılandırmalı."""
    n = normalize_client_task_type(explicit)
    if n is not None:
        return n
    o = out if isinstance(out, dict) else {}
    if explicit and str(explicit).strip().lower() == "media":
        return cast(TaskType, infer_media_subtype(text))
    if explicit and str(explicit).strip().lower() == "system":
        return resolve_system_task_type(text, o)
    return resolve_system_task_type(text, o)


def _dispatch_risk_from_out(out: dict[str, Any]) -> str:
    hb = out.get("http_body")
    if isinstance(hb, dict):
        for key in ("risk_level", "risk"):
            v = hb.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip().lower()
        lg = hb.get("lumos_gate")
        if isinstance(lg, dict):
            v = lg.get("risk_level")
            if isinstance(v, str) and v.strip():
                return v.strip().lower()
    pr = out.get("pending_approval_record")
    if isinstance(pr, dict):
        v = pr.get("risk_level")
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    ex = str(out.get("risk_level") or "").strip().lower()
    return ex if ex else "unknown"


def _gate_blocked_for_execution(out: dict[str, Any]) -> bool:
    if str(out.get("execution_mode") or "").strip().lower() == "blocked":
        return True
    hb = out.get("http_body")
    if not isinstance(hb, dict):
        return False
    return str(hb.get("decision_kind") or "").strip().lower() == "blocked"


def _risk_allows_system_execution(risk: str, out: dict[str, Any]) -> bool:
    """Doğrudan (onaysız) file/shell: yalnızca low risk; gate blocked → hayır."""
    if _gate_blocked_for_execution(out):
        return False
    r = (risk or "").strip().lower()
    if r in ("high", "blocked"):
        return False
    return r == "low"


def validate_dispatch_pending_for_approval(loaded: dict[str, Any]) -> None:
    """Orta risk dispatch onayı: dosya şeması + orta risk + snapshot."""
    if loaded.get("schema_version") != DISPATCH_PENDING_APPROVAL_SCHEMA:
        raise ValueError("geçersiz dispatch pending şeması")
    if loaded.get("policy_ok") is False:
        raise ValueError("policy_ok gerekli")
    if str(loaded.get("risk_level") or "").strip().lower() != "medium":
        raise ValueError("beklenen medium-risk dispatch onayı")
    ds = loaded.get("dispatch_snapshot")
    if not isinstance(ds, dict):
        raise ValueError("dispatch_snapshot gerekli")
    snap_t = str(ds.get("text") or "").strip()
    orig_t = str(loaded.get("original_payload") or "").strip()
    if not snap_t and not orig_t:
        raise ValueError("dispatch_snapshot.text veya original_payload gerekli")
    if not isinstance(loaded.get("normalized_task"), dict):
        raise ValueError("normalized_task eksik")
    ghb = loaded.get("gate_http_body_snapshot")
    if ghb is not None and not isinstance(ghb, dict):
        raise ValueError("gate_http_body_snapshot geçersiz")
    ps = loaded.get("dispatch_execution_plan_snapshot")
    if not isinstance(ps, dict) or ps.get("schema_version") != "lumos.dispatch_execution_plan.v1":
        raise ValueError("dispatch_execution_plan_snapshot eksik veya geçersiz")
    if ps.get("ok") is not True:
        raise ValueError("dispatch_execution_plan_snapshot ok değil")
    tt = str(loaded.get("task_type_snapshot") or "").strip().lower()
    if tt not in ("file", "shell"):
        raise ValueError("task_type_snapshot file|shell olmalı")


def execute_approved_dispatch_pending(
    loaded: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """
    Onaylanmış orta risk dispatch: risk/plan yeniden hesaplanmaz; snapshot + doğrudan executor.
    Önce validate_dispatch_pending_for_approval(loaded) çağrılmalıdır.
    """
    ds = loaded["dispatch_snapshot"]
    if not isinstance(ds, dict):
        raise ValueError("dispatch_snapshot gerekli")
    text = str(ds.get("text") or loaded.get("original_payload") or "").strip()
    explicit = ds.get("explicit_task_type")
    if isinstance(explicit, str):
        explicit = explicit.strip() or None
    elif explicit is not None:
        explicit = str(explicit).strip() or None

    ghb = loaded.get("gate_http_body_snapshot")
    hb = dict(ghb) if isinstance(ghb, dict) else {}

    out: dict[str, Any] = {
        "execution_mode": str(loaded.get("original_gate_execution_mode") or "restricted"),
        "policy_ok": loaded.get("policy_ok") is not False,
        "http_body": hb,
        "http_status": 200,
    }
    if explicit is not None:
        out["_client_task_type"] = explicit

    task_type = cast(TaskType, str(loaded.get("task_type_snapshot") or "").strip().lower())
    saved_plan = dict(loaded["dispatch_execution_plan_snapshot"])
    plan_out = {
        **saved_plan,
        "execution_permitted": True,
        "requires_dispatch_approval": False,
        "reason": "user_approved",
    }

    executor = _EXECUTOR_FOR_TYPE[task_type]
    if task_type == "file":
        queue = cast(QueueName, "file_executor_pending")
        label_tr = "Dosya yürütücüsüne yönlendirildi"
    else:
        queue = cast(QueueName, "shell_executor_pending")
        label_tr = "Shell yürütücüsüne yönlendirildi"

    result: dict[str, Any] = {
        "task_type": task_type,
        "dispatch_execution_plan": plan_out,
        "execution_dispatch": {
            "queue": queue,
            "label_tr": label_tr,
            "executor": executor,
        },
    }

    rr = repo_root
    if task_type == "file":
        from kando_runtime.file_executor import run as file_run

        if rr is None:
            result["system_execution"] = {
                "executed": False,
                "status": "skipped",
                "outcome_tr": "reddedildi",
                "executor": "file_executor",
                "detail": "repo_root verilmedi; dosya yürütücüsü çalışmadı",
            }
        else:
            result["system_execution"] = file_run(
                {"text": text, "out": out},
                repo_root=rr if isinstance(rr, Path) else Path(str(rr)),
            )
    else:
        from kando_runtime.shell_executor import run as shell_run

        if rr is None:
            result["system_execution"] = {
                "executed": False,
                "status": "skipped",
                "outcome_tr": "reddedildi",
                "executor": "shell_executor",
                "detail": "repo_root verilmedi; shell yürütücüsü çalışmadı",
            }
        else:
            result["system_execution"] = shell_run(
                {"text": text, "out": out},
                repo_root=rr if isinstance(rr, Path) else Path(str(rr)),
            )

    se = result["system_execution"]
    otr = str(se.get("outcome_tr") or "").strip()
    if otr:
        result["execution_dispatch"] = {
            **result["execution_dispatch"],
            "outcome_tr": otr,
        }
    return result


def _short_pending_summary(text: str, *, limit: int = 240) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    return t[: limit - 1] + "…"


def _gate_http_body_snapshot(hb: dict[str, Any]) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for k in (
        "normalized_task",
        "execution_plan",
        "reasoning_snapshot",
        "lumos_gate",
        "risk_level",
        "decision_kind",
    ):
        if k in hb:
            snap[k] = hb[k]
    return snap


def _persist_medium_dispatch_pending(
    out: dict[str, Any],
    *,
    text: str,
    explicit: str | None,
    repo_root: Path,
    dispatch_execution_plan_snapshot: dict[str, Any],
    task_type_snapshot: str,
    execution_dispatch_snapshot: dict[str, Any],
) -> None:
    """Orta risk file/shell için .lumos/pending_approvals kaydı + out alanları."""
    hb = out.get("http_body") if isinstance(out.get("http_body"), dict) else {}
    nt = hb.get("normalized_task") if isinstance(hb.get("normalized_task"), dict) else {}
    hb_snap = _gate_http_body_snapshot(hb)

    pending_root = repo_root / ".lumos" / "pending_approvals"
    pending_root.mkdir(parents=True, exist_ok=True)
    fname = f"approval_{int(time.time() * 1000)}.json"
    p = pending_root / fname
    approval_rel = f".lumos/pending_approvals/{fname}"

    rec: dict[str, Any] = {
        "schema_version": DISPATCH_PENDING_APPROVAL_SCHEMA,
        "final_decision": "await_user_approval",
        "risk_level": "medium",
        "execution_mode": "pending_approval",
        "policy_ok": out.get("policy_ok") is not False,
        "original_payload": text[:8000],
        "normalized_task": nt,
        "dispatch_snapshot": {
            "text": text,
            "explicit_task_type": explicit,
        },
        "dispatch_execution_plan_snapshot": dict(dispatch_execution_plan_snapshot),
        "task_type_snapshot": str(task_type_snapshot),
        "execution_dispatch_snapshot": dict(execution_dispatch_snapshot),
        "gate_http_body_snapshot": hb_snap,
        "original_gate_execution_mode": str(out.get("execution_mode") or ""),
        "pending_summary": _short_pending_summary(text),
        "title": (text or "")[:500],
        "raw_text": text[:8000],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval_file": approval_rel,
        "approval_token": secrets.token_hex(16),
        "used": False,
    }
    rs = hb_snap.get("reasoning_snapshot") if isinstance(hb_snap.get("reasoning_snapshot"), dict) else {}
    summ = str(rs.get("summary") or "").strip()
    if summ:
        rec["reasoning_summary"] = summ
    try:
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return
    out["execution_mode"] = "pending_approval"
    out["pending_approval_record"] = rec
    out["approval_file"] = approval_rel
    out["approval_token"] = str(rec["approval_token"])


def _dispatch_target_hint(task_type: TaskType, text: str, out: dict[str, Any]) -> str:
    norm = _normalized_task_dict_from_out(out)
    rel = str(norm.get("target_rel") or "").strip()
    raw = (text or "").strip()
    if task_type == "file":
        if rel:
            return rel[:500]
        return raw[:500] if raw else ""
    if task_type == "shell":
        return raw[:500] if raw else ""
    if task_type in ("video", "image", "audio"):
        return raw[:500] if raw else ""
    return raw[:500] if raw else ""


DispatchPlanAction = Literal[
    "none",
    "file_operation",
    "shell_command",
    "media_video",
    "media_image",
    "media_audio",
]


def build_dispatch_execution_plan(
    *,
    task_type: TaskType,
    text: str,
    out: dict[str, Any],
    executor: str | None,
) -> dict[str, Any]:
    """
    Parse sonrası yürütme planı: action, target, executor_type, risk.
    ok=False → sync system executor (file/shell) çalıştırılmaz.
    file/shell: low → execution_permitted; medium → requires_dispatch_approval (sync yok).
    """
    risk = _dispatch_risk_from_out(out)
    target = _dispatch_target_hint(task_type, text, out)
    r = (risk or "").strip().lower()

    if task_type == "generic":
        return {
            "schema_version": "lumos.dispatch_execution_plan.v1",
            "ok": False,
            "action": "none",
            "target": target,
            "executor_type": None,
            "risk": risk,
            "execution_permitted": False,
            "requires_dispatch_approval": False,
            "reason": "no_system_or_media_route",
        }

    action: DispatchPlanAction
    if task_type == "file":
        action = "file_operation"
    elif task_type == "shell":
        action = "shell_command"
    elif task_type == "video":
        action = "media_video"
    elif task_type == "image":
        action = "media_image"
    else:
        action = "media_audio"

    exec_perm = False
    requires_dispatch_approval = False
    reason = ""
    if task_type in ("file", "shell"):
        if _risk_allows_system_execution(risk, out):
            exec_perm = True
        elif not _gate_blocked_for_execution(out) and r == "medium":
            requires_dispatch_approval = True
            reason = "medium_risk_requires_user_approval"
        else:
            reason = "risk_enforcement"

    return {
        "schema_version": "lumos.dispatch_execution_plan.v1",
        "ok": True,
        "action": action,
        "target": target,
        "executor_type": executor,
        "risk": risk,
        "execution_permitted": exec_perm,
        "requires_dispatch_approval": requires_dispatch_approval,
        "reason": reason,
    }


def extract_text_for_dispatch(out: dict[str, Any]) -> str:
    """Gate çıktısından kullanıcı görev metnini çıkarır."""
    chunks: list[str] = []
    pr = out.get("pending_approval_record")
    if isinstance(pr, dict):
        s = str(pr.get("original_payload") or "").strip()
        if s:
            chunks.append(s)
        nt0 = pr.get("normalized_task")
        if isinstance(nt0, dict):
            for k in ("ingest_raw_text", "ingest_title", "target_body", "agent_blob"):
                v = str(nt0.get(k) or "").strip()
                if v:
                    chunks.append(v)
    hb = out.get("http_body")
    if isinstance(hb, dict):
        for k in ("task", "goal", "raw_text", "message", "user_task_surface"):
            v = hb.get(k)
            if isinstance(v, str) and v.strip():
                chunks.append(v.strip())
        nt = hb.get("normalized_task")
        if isinstance(nt, dict):
            for k in (
                "ingest_raw_text",
                "ingest_title",
                "target_body",
                "agent_blob",
            ):
                v = str(nt.get(k) or "").strip()
                if v:
                    chunks.append(v)
    pl = str(out.get("payload") or "").strip()
    if pl:
        chunks.append(pl)
    return "\n".join(dict.fromkeys(chunks)).strip() if chunks else ""


def dispatch_task(task: dict[str, Any]) -> dict[str, Any]:
    """
    task: «text», gate «out», isteğe bağlı repo_root (Path), explicit_task_type (str).
    Dönüş: task_type, dispatch_execution_plan, execution_dispatch (executor, queue);
    file/shell için plan ok ve execution_permitted ise gerçek yürütme; aksi halde atlanmış kayıt.
    """
    text = str(task.get("text") or "").strip()
    if not text:
        text = extract_text_for_dispatch(task.get("out") or task.get("gate_out") or {})
    out = task.get("out") or task.get("gate_out") or {}
    repo_root = task.get("repo_root")
    explicit = task.get("explicit_task_type")
    task_type: TaskType = resolve_task_type(
        text, str(explicit).strip() if explicit else None, out
    )

    execution_mode = str(out.get("execution_mode") or "").lower()
    hb = out.get("http_body") if isinstance(out.get("http_body"), dict) else {}
    lg = hb.get("lumos_gate") if isinstance(hb.get("lumos_gate"), dict) else {}
    ex_nested = str(lg.get("execution_mode") or "").lower()
    pending = execution_mode == "pending_approval" or ex_nested == "pending_approval"
    req_clar = hb.get("requires_clarification") is True

    queue: QueueName
    label_tr: str
    executor = _EXECUTOR_FOR_TYPE[task_type]

    if task_type == "video":
        queue = "video_executor_pending"
        label_tr = "Video yürütücüsüne gönderildi"
    elif task_type == "image":
        queue = "image_executor_pending"
        label_tr = "Görsel yürütücüsüne gönderildi"
    elif task_type == "audio":
        queue = "audio_executor_pending"
        label_tr = "Ses yürütücüsüne gönderildi"
    elif task_type == "file":
        if pending:
            queue = "file_approval_pending"
            label_tr = "Dosya işlemi onayına gönderildi"
        else:
            queue = "file_executor_pending"
            label_tr = "Dosya yürütücüsüne yönlendirildi"
    elif task_type == "shell":
        if pending:
            queue = "shell_approval_pending"
            label_tr = "Shell onayına gönderildi"
        else:
            queue = "shell_executor_pending"
            label_tr = "Shell yürütücüsüne yönlendirildi"
    else:
        if req_clar or pending:
            queue = "clarification_pending"
            label_tr = "Ek bilgi bekleniyor"
        else:
            queue = "generic_pending"
            label_tr = "İşlem kuyruğuna alındı"

    plan = build_dispatch_execution_plan(
        task_type=task_type,
        text=text,
        out=out,
        executor=executor,
    )
    plan_ok = plan.get("ok") is True
    run_system_executor = (
        plan_ok
        and plan.get("execution_permitted") is True
        and not plan.get("requires_dispatch_approval")
    )

    result: dict[str, Any] = {
        "task_type": task_type,
        "dispatch_execution_plan": plan,
        "execution_dispatch": {
            "queue": queue,
            "label_tr": label_tr,
            "executor": executor,
        },
    }

    if task_type == "file" and plan_ok and run_system_executor:
        from kando_runtime.file_executor import run as file_run

        rr = repo_root
        if rr is None:
            result["system_execution"] = {
                "executed": False,
                "status": "skipped",
                "outcome_tr": "reddedildi",
                "executor": "file_executor",
                "detail": "repo_root verilmedi; dosya yürütücüsü çalışmadı",
            }
        else:
            result["system_execution"] = file_run(
                {"text": text, "out": out},
                repo_root=rr if isinstance(rr, Path) else Path(str(rr)),
            )
        se = result["system_execution"]
        otr = str(se.get("outcome_tr") or "").strip()
        if otr:
            result["execution_dispatch"] = {
                **result["execution_dispatch"],
                "outcome_tr": otr,
            }

    elif task_type == "file" and plan_ok and not run_system_executor:
        if not plan.get("requires_dispatch_approval"):
            result["system_execution"] = {
                "executed": False,
                "status": "skipped",
                "outcome_tr": "reddedildi",
                "executor": "file_executor",
                "detail": (
                    "Risk enforcement: yalnızca low risk ve engelli olmayan gate ile "
                    "dosya yürütücüsü doğrudan çalışır; orta risk için onay gerekir."
                ),
            }
            otr = str(result["system_execution"].get("outcome_tr") or "").strip()
            if otr:
                result["execution_dispatch"] = {
                    **result["execution_dispatch"],
                    "outcome_tr": otr,
                }

    elif task_type == "shell" and plan_ok and run_system_executor:
        from kando_runtime.shell_executor import run as shell_run

        rr = repo_root
        if rr is None:
            result["system_execution"] = {
                "executed": False,
                "status": "skipped",
                "outcome_tr": "reddedildi",
                "executor": "shell_executor",
                "detail": "repo_root verilmedi; shell yürütücüsü çalışmadı",
            }
        else:
            result["system_execution"] = shell_run(
                {"text": text, "out": out},
                repo_root=rr if isinstance(rr, Path) else Path(str(rr)),
            )
        se = result["system_execution"]
        otr = str(se.get("outcome_tr") or "").strip()
        if otr:
            result["execution_dispatch"] = {
                **result["execution_dispatch"],
                "outcome_tr": otr,
            }

    elif task_type == "shell" and plan_ok and not run_system_executor:
        if not plan.get("requires_dispatch_approval"):
            result["system_execution"] = {
                "executed": False,
                "status": "skipped",
                "outcome_tr": "reddedildi",
                "executor": "shell_executor",
                "detail": (
                    "Risk enforcement: yalnızca low risk ve engelli olmayan gate ile "
                    "shell yürütücüsü doğrudan çalışır; orta risk için onay gerekir."
                ),
            }
            otr = str(result["system_execution"].get("outcome_tr") or "").strip()
            if otr:
                result["execution_dispatch"] = {
                    **result["execution_dispatch"],
                    "outcome_tr": otr,
                }

    return result


def attach_execution_dispatch_to_out(
    out: dict[str, Any], *, repo_root: Path | None = None
) -> None:
    """out['http_body'] üzerine task_type, execution_dispatch ve system_execution yazar."""
    text = extract_text_for_dispatch(out)
    explicit = out.get("_client_task_type")
    if explicit is not None and not isinstance(explicit, str):
        explicit = str(explicit).strip() or None
    disp = dispatch_task(
        {
            "text": text,
            "out": out,
            "repo_root": repo_root,
            "explicit_task_type": explicit,
        }
    )
    hb = out.get("http_body")
    if not isinstance(hb, dict):
        hb = {}
        out["http_body"] = hb
    hb["task_type"] = disp["task_type"]
    hb["dispatch_execution_plan"] = disp["dispatch_execution_plan"]
    hb["execution_dispatch"] = disp["execution_dispatch"]
    if "system_execution" in disp:
        hb["system_execution"] = disp["system_execution"]

    plan = disp.get("dispatch_execution_plan") or {}
    if (
        repo_root is not None
        and plan.get("requires_dispatch_approval") is True
        and str(out.get("execution_mode") or "").strip().lower() != "pending_approval"
    ):
        _persist_medium_dispatch_pending(
            out,
            text=text,
            explicit=explicit,
            repo_root=repo_root,
            dispatch_execution_plan_snapshot=dict(disp["dispatch_execution_plan"]),
            task_type_snapshot=str(disp["task_type"]),
            execution_dispatch_snapshot=dict(disp["execution_dispatch"]),
        )
