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

import copy
import hashlib
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

from kando_runtime.router import ROUTES, resolve_executor

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

# --- video_executor: bellek + disk önbellek (yalnızca task_dispatch) ---
VIDEO_DISK_CACHE_FILE = ".video_cache.json"
VIDEO_CACHE_TTL_SECONDS = int(os.getenv("VIDEO_CACHE_TTL_SECONDS", "3600"))
_VIDEO_MEMORY_CACHE: dict[str, dict[str, Any]] = {}


def _video_normalize_prompt(prompt: Any) -> str:
    p = str(prompt or "").strip().lower()
    p = " ".join(p.split())
    return p.replace(".", "")


def _video_disk_prompt_hash(prompt_norm: str) -> str:
    return hashlib.sha256(prompt_norm.encode()).hexdigest()


def _video_disk_cache_path() -> Path:
    return Path(os.getcwd()) / VIDEO_DISK_CACHE_FILE


def _load_video_disk_cache() -> dict[str, str]:
    p = _video_disk_cache_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str) and v.strip():
                out[k] = v.strip()
        return out
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def _save_video_disk_cache(prompt_hash: str, video_url: str) -> None:
    if not prompt_hash or not (video_url and str(video_url).strip()):
        return
    p = _video_disk_cache_path()
    cache = _load_video_disk_cache()
    cache[prompt_hash] = str(video_url).strip()
    try:
        p.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _apply_video_cache_meta(result: dict[str, Any], hit: bool) -> None:
    result["meta"] = {"cache_hit": hit}
    out = result.get("output")
    if isinstance(out, dict):
        om = out.setdefault("meta", {})
        if isinstance(om, dict):
            om["cache_hit"] = hit


def _video_memory_store_strip_meta(key: str, result: dict[str, Any]) -> None:
    stored: dict[str, Any] = dict(result)
    if isinstance(stored.get("output"), dict):
        stored["output"] = copy.deepcopy(stored["output"])
    stored.pop("meta", None)
    if isinstance(stored.get("output"), dict):
        stored["output"].pop("meta", None)
    _VIDEO_MEMORY_CACHE[key] = {
        "stored_at": time.time(),
        "result": stored,
    }


def _video_memory_cache_get(key: str) -> dict[str, Any] | None:
    entry = _VIDEO_MEMORY_CACHE.get(key)
    if not isinstance(entry, dict):
        return None
    stored_at = entry.get("stored_at")
    result = entry.get("result")
    if not isinstance(stored_at, (int, float)) or not isinstance(result, dict):
        _VIDEO_MEMORY_CACHE.pop(key, None)
        return None
    if time.time() - float(stored_at) > VIDEO_CACHE_TTL_SECONDS:
        _VIDEO_MEMORY_CACHE.pop(key, None)
        return None
    out = dict(result)
    if isinstance(out.get("output"), dict):
        out["output"] = copy.deepcopy(out["output"])
    return out


def _video_done_payload(url: str) -> dict[str, Any]:
    return {
        "status": "done",
        "output": {
            "type": "video",
            "url": url,
            "provider": "replicate",
        },
    }


def _run_video_executor_with_cache(
    params: dict[str, Any],
    video_run: Any,
) -> dict[str, Any]:
    """Anahtar json.dumps(params, sort_keys=True); bellek + disk; video_run saf çıktı."""
    if not isinstance(params, dict):
        params = {"prompt": str(params)}
    key = json.dumps(params, sort_keys=True, ensure_ascii=False)

    result = _video_memory_cache_get(key)
    if result is not None:
        _apply_video_cache_meta(result, True)
        return result

    pn = _video_normalize_prompt(params.get("prompt", ""))
    ph = _video_disk_prompt_hash(pn)
    disk = _load_video_disk_cache()
    cu = disk.get(ph, "")
    if cu:
        out = _video_done_payload(cu)
        _video_memory_store_strip_meta(key, out)
        result = _video_memory_cache_get(key)
        if result is None:
            result = _video_done_payload(cu)
        _apply_video_cache_meta(result, True)
        return result

    out = video_run(params)
    if not isinstance(out, dict):
        return out
    if out.get("status") == "done" and isinstance(out.get("output"), dict):
        u = str(out["output"].get("url") or "").strip()
        if u:
            _video_memory_store_strip_meta(key, out)
            _apply_video_cache_meta(out, False)
            _save_video_disk_cache(ph, u)
    return out


def _video_params_from_task(task: dict[str, Any]) -> dict[str, Any]:
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    p = str(params.get("prompt") or task.get("prompt") or "").strip()
    return {"prompt": p}


def generate_id() -> str:
    return f"task_{int(time.time() * 1000)}_{secrets.token_hex(4)}"


approval_store: dict[str, str] = {}


def is_approved(task_id: str) -> bool:
    return approval_store.get(task_id) == "approved"


def infer_risk(task):
    task_type = task.get("task_type")

    if task_type == "text.generate":
        return "low"

    return "low"


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

    task_id = str(loaded.get("task_id") or generate_id())
    result: dict[str, Any] = {
        "task_id": task_id,
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
    task_id: str,
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
        "task_id": str(task_id or ""),
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
        "approval": {
            "task_id": str(task_id or ""),
            "risk": "medium",
            "status": "pending",
        },
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


def build_execution_plan(task: dict[str, Any]) -> dict[str, Any]:
    """
    Backend yürütme planı (özellikle medya işleri için) üretir.
    Şimdilik video taleplerini video.generate adımına indirger.
    """
    task_type = str(task.get("task_type") or "").strip().lower()
    if task_type != "video":
        return {"steps": []}
    prompt = str(task.get("prompt") or "").strip()
    if not prompt:
        return {"steps": []}
    return {
        "steps": [
            {
                "type": "video.generate",
                "params": {
                    "prompt": prompt,
                    "duration": 10,
                    "resolution": "720p",
                },
            }
        ]
    }


def run_video_executor(task: dict[str, Any]) -> Any:
    from kando_runtime.video_executor import run

    return _run_video_executor_with_cache(_video_params_from_task(task), run)


def _video_keyword_bypass_dispatch_return(
    task: dict[str, Any],
    *,
    text: str,
    out: dict[str, Any],
    task_id: str,
) -> dict[str, Any]:
    """Anahtar kelime ile clarity/vague atlanır; video_executor çıktısı + dispatch zarfı."""
    try:
        exec_out = run_video_executor(task)
    except Exception:
        from kando_runtime.executors.video_executor import run as _video_run

        exec_out = _run_video_executor_with_cache(_video_params_from_task(task), _video_run)
    if not isinstance(exec_out, dict):
        exec_out = {"status": "done", "output": exec_out}
    executor = _EXECUTOR_FOR_TYPE.get("video")
    plan = build_dispatch_execution_plan(
        task_type="video",
        text=text,
        out=out,
        executor=executor,
    )
    task["execution_plan"] = build_execution_plan(
        {
            "task_type": "video",
            "prompt": str(task.get("prompt") or text).strip(),
        }
    )
    return {
        "status": exec_out.get("status", "done"),
        "output": exec_out.get("output"),
        "task_id": task_id,
        "task_type": "video",
        "dispatch_execution_plan": plan,
        "execution_dispatch": {
            "queue": "video_executor_pending",
            "label_tr": "Video yürütücüsüne gönderildi",
            "executor": executor,
        },
        "execution_plan": task.get("execution_plan"),
    }


_VIDEO_VAGUE_TOKENS: tuple[str, ...] = (
    "bir şey",
    "birsey",
    "şey",
    "garip",
    "bilinmeyen",
    "ilginç",
    "farklı",
    "bir şeyler",
    "bi şey",
)
_VIDEO_STRUCTURE_TOKENS: tuple[str, ...] = (
    "adam",
    "kadın",
    "çocuk",
    "uçuyor",
    "koşuyor",
    "deniz",
    "çöl",
    "orman",
    "şehir",
    "gece",
    "gündüz",
)

_VIDEO_VAGUE_SINGLE_WORDS: frozenset[str] = frozenset(
    w for phrase in _VIDEO_VAGUE_TOKENS for w in phrase.split()
) | frozenset({"birsey"})

# Genel belirsizlik ipuçları (clarity skoru): video listesi + kısa genel ifadeler
_DISPATCH_VAGUE_HINTS: tuple[str, ...] = _VIDEO_VAGUE_TOKENS + (
    "falan",
    "filan",
    "herhangi",
    "ne olursa",
    "bilmem",
    "falan filan",
    "falan fistan",
    "rastgele",
)

# Niyet sinyali: anahtar kelime varlığı (hafif sezgisel liste)
_INTENT_KEYWORD_HINTS: tuple[str, ...] = (
    "oluştur",
    "olustur",
    "üret",
    "uret",
    "sil",
    "çalıştır",
    "calistir",
    "yap",
    "göster",
    "goster",
    "patch",
    "run",
    "komut",
    "dosya",
    "klasör",
    "klasor",
    "video",
    "klip",
    "film",
    "resim",
    "ses",
    "audio",
    "shell",
    "terminal",
    "düzenle",
    "duzenle",
    "ekle",
    "kaldır",
    "kaldir",
    "oku",
    "yaz",
    "target",
    "ffmpeg",
)

_CLARITY_NEED_INPUT_THRESHOLD = 0.4


def _normalize_prompt(task: dict[str, Any]) -> str:
    """task içinden prompt / yüzey metnini güvenli şekilde çıkarır."""
    raw = task.get("prompt")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return str(task.get("text") or "").strip()


_CONTENT_WATCH_POSITIVE_PHRASES: tuple[str, ...] = (
    "izlemek istiyorum",
    "bir şey aç",
    "bir şey izlet",
    "seyredeceğim bir şey",
    "gerçekten seyredeceğim bir şey",
    "sen seç",
    "farketmez",
    "ne olduğu önemli değil",
    "bir şey sun",
    "bir şey öner",
    "bir video aç",
)
_CONTENT_WATCH_NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "oluştur",
    "üret",
    "generate",
    "hazırla",
    "render",
    "video yap",
)


def _is_content_watch_request(prompt: str) -> bool:
    """Hazır izlenecek içerik niyeti (üretim anahtar kelimesi yoksa True)."""
    p = (prompt or "").strip().lower()
    if not p:
        return False
    for neg in _CONTENT_WATCH_NEGATIVE_KEYWORDS:
        if neg in p:
            return False
    for pos in _CONTENT_WATCH_POSITIVE_PHRASES:
        if pos in p:
            return True
    return False


def _risk_for_snapshot(task: dict[str, Any], out: dict[str, Any]) -> str:
    """Gate risk öncelikli; yoksa infer_risk."""
    if isinstance(out, dict) and out:
        r = _dispatch_risk_from_out(out).strip().lower()
        if r and r != "unknown":
            return r
    return infer_risk(task)


def _is_vague_request(task_type: TaskType, prompt: str) -> bool:
    """Belirsiz istek (video vague listesi tek merkezde)."""
    if task_type != "video":
        return False
    pl = (prompt or "").lower()
    if not pl:
        return False
    vague = any(k in pl for k in _VIDEO_VAGUE_TOKENS)
    has_structure = any(k in pl for k in _VIDEO_STRUCTURE_TOKENS)
    return vague and not has_structure


def _video_prompt_only_vague_words(prompt: str) -> bool:
    """Tüm anlamlı kelimeler yalnızca video belirsizlik sözlüğündeyse True."""
    pl = (prompt or "").lower()
    words = re.findall(r"\w+", pl)
    if not words:
        return False
    return all(w in _VIDEO_VAGUE_SINGLE_WORDS for w in words)


def _is_feasible_request(
    task_type: TaskType,
    prompt: str,
    task: dict[str, Any],
    out: dict[str, Any],
) -> bool:
    """Açıkça yapılamaz / eksik / hedefsiz işler → False."""
    p = (prompt or "").strip()
    norm = _normalized_task_dict_from_out(out)
    rel = str(norm.get("target_rel") or "").strip()

    if task_type == "video":
        return bool(p)

    if task_type == "file":
        if rel:
            return True
        if str(norm.get("target_body") or "").strip():
            return True
        if re.search(r"\b[\w./\\-]+\.\w{2,16}\b", p):
            return True
        if _FILE_HINT_RE.search(p):
            return True
        return bool(p)

    if task_type == "shell":
        return bool(p)

    if task_type in ("image", "audio"):
        return bool(p)

    return True


def _video_need_input_reason(prompt: str) -> str | None:
    """Video: kısa / boş / yalnızca belirsiz kelimeler → netleştirme; executor yok."""
    p = (prompt or "").strip()
    if not p or len(p) < 10:
        return "VIDEO_PROMPT_VAGUE"
    if _video_prompt_only_vague_words(p):
        return "VIDEO_PROMPT_VAGUE"
    if _is_vague_request("video", p):
        return "VIDEO_PROMPT_VAGUE"
    return None


_VIDEO_SOURCE_URL_RE = re.compile(r"https?://\S+", re.I)
_VIDEO_SOURCE_FILE_EXT_RE = re.compile(
    r"\b[\w./\\-]+\.(?:mp4|mov|webm|mkv|m4v|avi)\b",
    re.I,
)
_VIDEO_SOURCE_LABEL_RE = re.compile(
    r"(?:dosya\s*yolu|kaynak\s*url)\s*:",
    re.I,
)
# API / uç nokta (URL olmadan seyrek)
_VIDEO_SOURCE_API_HINT_RE = re.compile(
    r"\b(?:api\.[a-z0-9.-]+|/v\d+/|graphql|webhook|endpoint|rest\s*api)\b",
    re.I,
)


def _video_task_has_external_source(
    *,
    text: str,
    prompt: str,
    task: dict[str, Any],
) -> bool:
    """
    YouTube / URL, yerel dosya yolu veya API ipucu — gerçek medya veya dış kaynak yoksa False.
    """
    chunks = [
        str(text or ""),
        str(prompt or ""),
        str(task.get("prompt") or ""),
    ]
    blob = "\n".join(c for c in chunks if (c or "").strip())
    if not blob.strip():
        return False
    low = blob.lower()
    if "youtube.com" in low or "youtu.be/" in low or "m.youtube.com" in low:
        return True
    if _VIDEO_SOURCE_URL_RE.search(blob):
        return True
    if _VIDEO_SOURCE_FILE_EXT_RE.search(blob):
        return True
    if _VIDEO_SOURCE_LABEL_RE.search(blob):
        return True
    if blob.strip().startswith("file://"):
        return True
    if _VIDEO_SOURCE_API_HINT_RE.search(blob):
        return True
    return False


def _video_has_production_intent(*, text: str, prompt: str) -> bool:
    """Üret / göster / video niyeti — vague ve clarity kaynaklı durdurmayı bypass etmek için."""
    blob = f"{prompt or ''}\n{text or ''}".lower()
    return any(
        k in blob
        for k in (
            "oluştur",
            "olustur",
            "video",
            "göster",
            "goster",
        )
    )


def _decision_snapshot(
    task_type: TaskType,
    prompt: str,
    risk: str,
    *,
    task: dict[str, Any],
    out: dict[str, Any],
    needs_clarification: bool,
) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "is_vague": _is_vague_request(task_type, prompt),
        "is_feasible": _is_feasible_request(task_type, prompt, task, out),
        "risk": risk,
        "needs_clarification": needs_clarification,
    }


def _decision_layer_dispatch_shell(
    task_type: TaskType, *, reason: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Karar katmanı erken dönüşü için minimal plan + execution_dispatch."""
    plan: dict[str, Any] = {
        "schema_version": "lumos.dispatch_execution_plan.v1",
        "ok": False,
        "action": "none",
        "target": "",
        "executor_type": _EXECUTOR_FOR_TYPE.get(task_type),
        "risk": "low",
        "execution_permitted": False,
        "requires_dispatch_approval": False,
        "reason": reason,
    }
    exec_disp: dict[str, Any] = {
        "queue": "clarification_pending",
        "label_tr": "Karar katmanı: netlik / uygulanabilirlik",
        "executor": _EXECUTOR_FOR_TYPE.get(task_type),
    }
    return plan, exec_disp


def now() -> str:
    """UTC ISO-8601 zaman damgası (dispatch meta)."""
    return datetime.now(timezone.utc).isoformat()


def _dispatch_vague_hit_count(prompt: str) -> int:
    pl = (prompt or "").lower()
    return sum(1 for h in _DISPATCH_VAGUE_HINTS if h in pl)


def estimate_intent(task: dict[str, Any]) -> float:
    """0.0–1.0: anahtar kelime varlığına dayalı hafif niyet skoru (harici model yok)."""
    text = str(task.get("text") or "").strip()
    if not text:
        text = extract_text_for_dispatch(task.get("out") or task.get("gate_out") or {})
    t = text.lower().strip()
    if not t:
        return 0.0
    hits = sum(1 for k in _INTENT_KEYWORD_HINTS if k in t)
    explicit_bonus = 0.14 if str(task.get("explicit_task_type") or "").strip() else 0.0
    return float(min(1.0, 0.06 + 0.1 * hits + explicit_bonus))


def estimate_clarity(task: dict[str, Any]) -> float:
    """0.0–1.0: prompt uzunluğu + belirsiz kelime/öbek isabeti (hafif sezgisel)."""
    p = (_normalize_prompt(task) or "").strip()
    if not p:
        return 0.0
    # Uzunluk bileşeni (kısa talimatlar doğal olarak daha düşük)
    len_norm = min(len(p), 220) / 220.0
    hits = _dispatch_vague_hit_count(p)
    vague_component = max(0.0, 1.0 - 0.13 * hits)
    combined = 0.58 * len_norm + 0.42 * vague_component
    # Çok kısa metin ek cezası (12 altı; ~14 karakterlik net dosya talimatı 0.4 üstünde kalsın)
    if len(p) < 12:
        combined *= len(p) / 12.0
    return float(max(0.0, min(1.0, combined)))


def dispatch_task(task):
    depth = int(task.get("_depth", 0))

    if depth > 3:
        return {
            "status": "error",
            "reason": "MAX_DEPTH_EXCEEDED",
        }

    task["_depth"] = depth + 1

    if len(task.get("_trace", [])) > 5:
        return {
            "status": "error",
            "reason": "MAX_TRACE_EXCEEDED",
        }

    task_type = task.get("task_type") or task.get("type")

    if task_type == "text.generate" and "plan" in str(task.get("prompt", "")).lower():
        return {
            "status": "routed",
            "target": "agent",
            "task": {
                "type": "text.agent",
                "prompt": task.get("prompt"),
            },
        }

    if "text" in str(task_type or ""):
        return {
            "status": "done",
            "output": {
                "type": "text",
                "value": task.get("prompt"),
            },
        }

    if task_type:
        task["task_type"] = task_type
    task_id = str(task.get("id") or generate_id())
    task["id"] = task_id
    text = str(task.get("text") or "").strip()
    if not text:
        text = extract_text_for_dispatch(task.get("out") or task.get("gate_out") or {})
    task["text"] = text
    out = task.get("out") or task.get("gate_out") or {}
    repo_root = task.get("repo_root")
    explicit = task.get("explicit_task_type")
    task_type: TaskType = resolve_task_type(
        text, str(explicit).strip() if explicit else None, out
    )
    task["task_type"] = task_type

    prompt = _normalize_prompt(task)
    if _is_content_watch_request(prompt):
        from kando_runtime.executors.content_executor import run as _content_run

        _cr = _content_run({"prompt": prompt})
        _out = _cr.get("output") if isinstance(_cr, dict) else {}
        risk_snap_cw = _dispatch_risk_from_out(out)
        cw_ret: dict[str, Any] = {
            "status": "done",
            "task_id": task_id,
            "task_type": "content.watch",
            "output": _out,
            "dispatch_execution_plan": {
                "schema_version": "lumos.dispatch_execution_plan.v1",
                "ok": True,
                "action": "content_watch",
                "target": "content",
                "executor_type": "content_executor",
                "risk": risk_snap_cw,
                "execution_permitted": False,
                "requires_dispatch_approval": False,
                "reason": "",
            },
            "execution_dispatch": {
                "queue": "generic_pending",
                "label_tr": "İzlenecek içerik önerisi",
                "executor": "content_executor",
            },
        }
        if isinstance(_cr, dict) and isinstance(_cr.get("meta"), dict):
            cw_ret["meta"] = _cr["meta"]
        return cw_ret

    if task_type == "video":
        pl = str(task.get("prompt", "") or "").lower()
        if not pl.strip():
            pl = str(task.get("text") or "").lower()
        if pl.strip() and any(
            k in pl for k in ("video", "oluştur", "üret", "göster")
        ):
            return _video_keyword_bypass_dispatch_return(
                task, text=text, out=out, task_id=task_id
            )

    if task_type == "agent":
        executor_name = resolve_executor("agent")
    else:
        executor_name = resolve_executor(task_type)

    task["_meta"] = {
        "received_at": now(),
        "user_intent_score": estimate_intent(task),
        "clarity_score": estimate_clarity(task),
    }
    risk_snap = _risk_for_snapshot(task, out)
    prompt_stripped = (prompt or "").strip()
    bypass_video_gates = (
        task_type == "video"
        and bool(prompt_stripped)
        and _video_has_production_intent(text=text, prompt=prompt)
    )
    vni_reason = (
        None
        if bypass_video_gates
        else (_video_need_input_reason(prompt) if task_type == "video" else None)
    )
    clarity_sc = float(task["_meta"]["clarity_score"])
    clarity_blocks = clarity_sc < _CLARITY_NEED_INPUT_THRESHOLD
    if task_type == "video" and bypass_video_gates:
        clarity_blocks = False
    video_needs_source = (
        task_type == "video"
        and not bypass_video_gates
        and not _video_task_has_external_source(
            text=text, prompt=prompt, task=task
        )
    )
    needs_clarification = (
        vni_reason is not None or clarity_blocks or video_needs_source
    )
    decision_snapshot = _decision_snapshot(
        task_type,
        prompt,
        risk_snap,
        task=task,
        out=out,
        needs_clarification=needs_clarification,
    )
    if vni_reason:
        plan, exec_disp = _decision_layer_dispatch_shell(
            task_type, reason="VIDEO_PROMPT_VAGUE"
        )
        return {
            "status": "need_input",
            "reason": vni_reason,
            "question": "Nasıl bir sahne istiyorsun?",
            "decision": decision_snapshot,
            "task_id": task_id,
            "task_type": task_type,
            "dispatch_execution_plan": plan,
            "execution_dispatch": exec_disp,
        }

    if clarity_blocks:
        plan, exec_disp = _decision_layer_dispatch_shell(
            task_type, reason="LOW_CLARITY"
        )
        return {
            "status": "need_input",
            "reason": "LOW_CLARITY",
            "question": "Ne yapmak istediğinizi biraz daha açık yazar mısınız?",
            "decision": decision_snapshot,
            "task_id": task_id,
            "task_type": task_type,
            "dispatch_execution_plan": plan,
            "execution_dispatch": exec_disp,
        }

    if video_needs_source:
        plan, exec_disp = _decision_layer_dispatch_shell(
            task_type, reason="NO_VIDEO_SOURCE"
        )
        return {
            "status": "need_source",
            "reason": "NO_VIDEO_SOURCE",
            "message": (
                "Gerçek video için kaynak gerekli. "
                "Üreteyim mi yoksa dış kaynak mı kullanayım?"
            ),
            "decision": decision_snapshot,
            "task_id": task_id,
            "task_type": task_type,
            "dispatch_execution_plan": plan,
            "execution_dispatch": exec_disp,
        }

    if not _is_feasible_request(task_type, prompt, task, out):
        plan, exec_disp = _decision_layer_dispatch_shell(
            task_type, reason="not_feasible"
        )
        return {
            "status": "done",
            "output": {
                "type": "text",
                "value": "Bu görev şu haliyle net veya uygulanabilir görünmüyor.",
            },
            "decision": decision_snapshot,
            "task_id": task_id,
            "task_type": task_type,
            "dispatch_execution_plan": plan,
            "execution_dispatch": exec_disp,
        }

    if task_type == "video.generate":
        task_id = task.get("id") or generate_id()
        task["id"] = task_id

        task_type = task.get("task_type")

        if "text" in str(task_type or ""):
            return {
                "status": "done",
                "output": {
                    "type": "text",
                    "value": task.get("prompt"),
                },
            }

        risk = infer_risk(task)

        if risk != "low":
            if not is_approved(task_id):
                return {
                    "status": "done",
                    "output": {
                        "type": "text",
                        "value": "TEST: executor bypass çalıştı",
                    },
                }

        return {
            "status": "planned",
            "execution_plan": {
                "steps": [
                    {
                        "type": "video.generate",
                        "params": task,
                    }
                ]
            },
        }

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
    task["execution_plan"] = build_execution_plan(
        {
            "task_type": task_type,
            "prompt": str(task.get("prompt") or text).strip(),
        }
    )
    if not task.get("execution_plan") or not task["execution_plan"].get("steps"):
        task["execution_plan"] = {
            "steps": [
                {
                    "type": "noop",
                    "params": {},
                }
            ]
        }
    plan_ok = plan.get("ok") is True
    run_system_executor = (
        plan_ok
        and plan.get("execution_permitted") is True
        and not plan.get("requires_dispatch_approval")
    )

    result: dict[str, Any] = {
        "task_id": task_id,
        "task_type": task_type,
        "dispatch_execution_plan": plan,
        "execution_dispatch": {
            "queue": queue,
            "label_tr": label_tr,
            "executor": executor,
        },
    }
    result["execution_plan"] = task["execution_plan"]
    exec_plan = result.get("execution_plan")
    if exec_plan and isinstance(exec_plan, dict) and "steps" in exec_plan:
        for step in exec_plan["steps"]:
            if not isinstance(step, dict):
                continue
            st = step.get("type")
            st_str = str(st or "")
            if st_str not in ROUTES:
                continue
            executor_name = resolve_executor(st_str)
            risk = infer_risk(task)

            if risk == "high":
                return {
                    "status": "blocked",
                    "reason": "HIGH_RISK",
                }

            if risk == "unknown":
                return {
                    "status": "needs_review",
                    "reason": "UNKNOWN_RISK",
                }

            if executor_name == "agent_executor":
                from kando_runtime.agent_executor import run

                result = run(task)

                if isinstance(result, dict):
                    if "risk" in result:
                        risk = max(risk, result.get("risk", 0))

                trace = task.get("_trace", [])
                trace = trace + [task.get("type")]
                task["_trace"] = trace

                # ROUTE çıktıysa → yeniden dispatch et
                if isinstance(result, dict):
                    output = result.get("output", {})
                    if output.get("type") == "route":
                        new_task = output.get("task")
                        if new_task:
                            return dispatch_task(new_task)

                if isinstance(result, dict):
                    result["risk"] = risk
                    output = result.get("output")
                    if isinstance(output, dict):
                        output["risk"] = risk

                return result

            # low ise devam
            if executor_name == "text_executor":
                from kando_runtime.executors.text_executor import run

                out = run(step.get("params") or {})

                if isinstance(out, dict):
                    if "risk" in out:
                        risk = max(risk, out.get("risk", 0))

                trace = task.get("_trace", [])
                trace = trace + [task.get("type")]
                task["_trace"] = trace

                # ROUTE çıktıysa → yeniden dispatch et
                if isinstance(out, dict):
                    output = out.get("output", {})
                    if output.get("type") == "route":
                        new_task = output.get("task")
                        if new_task:
                            return dispatch_task(new_task)

                if isinstance(out, dict):
                    out["risk"] = risk
                    output = out.get("output")
                    if isinstance(output, dict):
                        output["risk"] = risk

                return {**result, **out} if isinstance(out, dict) else result
            elif executor_name == "video_executor":
                from kando_runtime.executors.video_executor import run as video_run

                out = _run_video_executor_with_cache(step.get("params") or {}, video_run)

                if isinstance(out, dict):
                    if "risk" in out:
                        risk = max(risk, out.get("risk", 0))

                trace = task.get("_trace", [])
                trace = trace + [task.get("type")]
                task["_trace"] = trace

                # ROUTE çıktıysa → yeniden dispatch et
                if isinstance(out, dict):
                    output = out.get("output", {})
                    if output.get("type") == "route":
                        new_task = output.get("task")
                        if new_task:
                            return dispatch_task(new_task)

                if isinstance(out, dict):
                    out["risk"] = risk
                    output = out.get("output")
                    if isinstance(output, dict):
                        output["risk"] = risk

                return {**result, **out} if isinstance(out, dict) else result
            elif executor_name == "content_executor":
                from kando_runtime.executors.content_executor import run as content_run

                out = content_run(step.get("params") or {})

                if isinstance(out, dict):
                    if "risk" in out:
                        risk = max(risk, out.get("risk", 0))

                trace = task.get("_trace", [])
                trace = trace + [task.get("type")]
                task["_trace"] = trace

                if isinstance(out, dict):
                    output = out.get("output", {})
                    if output.get("type") == "route":
                        new_task = output.get("task")
                        if new_task:
                            return dispatch_task(new_task)

                if isinstance(out, dict):
                    out["risk"] = risk
                    output = out.get("output")
                    if isinstance(output, dict):
                        output["risk"] = risk

                return {**result, **out} if isinstance(out, dict) else result

    if os.getenv("KANDO_MOCK") == "1":
        task["mock"] = True
        result["mock"] = True

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
    if disp.get("status") == "need_input":
        hb["lumos_dispatch_need_input"] = {
            "status": "need_input",
            "reason": disp.get("reason"),
            "question": disp.get("question"),
        }
    if disp.get("status") == "need_source":
        hb["lumos_dispatch_need_source"] = {
            "status": "need_source",
            "reason": disp.get("reason"),
            "message": disp.get("message"),
        }

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
            task_id=str(disp.get("task_id") or ""),
        )
