"""
Lumos gate: bridge görevleri önce LLM reasoning ile planlanır; executor yalnızca üretilmiş içeriği alır.
Ham kullanıcı metni file_patch_executor'a iletilmez.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from kando_runtime.lumos_audit import (
    LumosAuditCollector,
    compare_audit_entries,
    plan_execution_failed,
)

_MAX_FILE_READ = 120_000
_LLM_TIMEOUT = 90.0

_TR_CHARS_RE = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
_TR_HINT_RE = re.compile(
    r"\b(ve|ile|için|bir|bu|şu|veya|ancak|olarak|göre|kadar|mi|mı|mu|mü|dır|dir|tır|tir)\b",
    re.IGNORECASE,
)

_GATE_SYSTEM = """Sen Lumos köprü reasoning katmanısın. Çıktın kontrollü ve öngörülebilir olmalı; rastgele veya şişirilmiş metin üretme.
Yalnızca geçerli bir JSON nesnesi döndür; başka metin yok.

Şema (tüm anahtarlar zorunlu):
{
  "intent": "kısa niyet özeti (çıktı dili kurallarına uygun)",
  "mode": "agent | direct_patch | no_op",
  "needs_file": true veya false,
  "generated_content": "dosyaya yazılacak gövde (yalnızca doğrudan patch için; başka modlarda boş string)",
  "reason": "kısa gerekçe: risk düzeyi (düşük/orta/yüksek); belirsizlikte açıkça yaz; gerekirse 2-3 kısa alternatif (A/B/C) özetle"
}

Risk, analiz ve onay (uygulamayı sen yapmazsın; köprü/onay katmanı yürütür):
- Riskli veya yıkıcı işler (silme, toplu değişiklik, prod/secret, belirsiz hedef): önce analiz et; direct_patch kullanma.
  mode=no_op veya mode=agent ile generated_content="" tercih et; reason içinde risk + mümkünse 2-3 alternatif.
- Kullanıcı onayı olmadan yürütme varsayma; otomatik uygulama iddiasında bulunma.
- direct_patch yalnızca hedef tek dosya, talimat net ve yama güvenliyse; şüphe varsa no_op veya agent.

Zorunlu dil ve içerik kuralları:
- Çıktı dili, kullanıcı mesajında belirtilen hedef dil ile AYNı olmalı (tr veya en). Aksi belirtilmediyse, dosya/giriş metninin dili ne ise çıktı da o dilde olmalı.
- Ham task metnini (kullanıcı talimatını) ASLA generated_content içinde tekrar etme; yalnızca istenen işin sonucunu yaz.
- Sadece istenen işi yap: özet ise özet, açıklama ise kısa açıklama, liste ise madde listesi, kod ise yama satırları.
- Kısa ve doğrudan: önsöz, özür, "işte sonuç" gibi meta cümleler yok.
- Özet: en fazla 3-5 cümle (isteğe bağlı tek satır "## Özet" başlığı).
- Açıklama: tek kısa paragraf.
- Liste gerekiyorsa satır başına "- " veya "* " kullan.
- Dosya içeriği yok veya kullanılamıyorsa mode=no_op ve generated_content boş.

Görev kuralları:
- "dosya_icerigi" varsa önce onu kullan; özet/açıklama bu içeriğe dayanmalı.
- Belirsiz veya güvensizsen mode=no_op ve reason'da emin olmadığını belirt.
- Çok adımlı işler için mode=agent; generated_content="".
"""

_SUBSTEP_VALIDATOR_SYSTEM = """Sen Lumos substep validator'sın.
Görevin, verilen step'in güvenli, mantıklı ve üst task (parent_task) ile uyumlu olup olmadığını kontrol etmek.
Yalnızca geçerli bir JSON nesnesi döndür; başka metin yok.

Şema:
{
  "ok": true veya false,
  "reason": "kısa gerekçe",
  "risk_hint": "low" veya "medium" veya "high"
}

Kurallar:
- Tehlikeli veya alakasız step -> ok=false
- Üst task ile ilgisiz step -> ok=false
- Yıkıcı / silici / veri kaybettirici step -> risk_hint=high ve ok=false
- Yalnızca güvenli ve parent_task ile uyumlu adımlarda ok=true
"""


@dataclass
class GateContext:
    ingress_payload: dict[str, Any] = field(default_factory=dict)
    normalized_task: str = ""
    policy_ok: bool = False
    reasoning_summary: str = ""
    execution_mode: str = ""
    generated_content: str | None = None
    verification_summary: str = ""


def _parse_target_instruction(payload: str) -> tuple[str | None, str]:
    lines = (payload or "").strip().splitlines()
    if not lines:
        return None, ""
    head = lines[0].strip()
    if not head.upper().startswith("TARGET:"):
        return None, (payload or "").strip()
    rel = head.split(":", 1)[1].strip()
    body = "\n".join(lines[1:]).strip()
    return rel, body


_CREATE_VERB_RE_GATE = re.compile(
    r"\b(?:oluştur|olustur|yarat|create)\b",
    re.I,
)


def _body_implies_new_file_creation(body: str) -> bool:
    """Yeni dosya oluşturma; dosya henüz yokken okuma/precheck tetiklenmesin."""
    return bool(_CREATE_VERB_RE_GATE.search(body or ""))


def _normalized_implies_file_create(normalized: dict[str, Any]) -> bool:
    """target_body, ham payload ve agent_blob birleşiminde oluşturma fiili var mı."""
    parts: list[str] = []
    for key in ("target_body", "raw_payload", "agent_blob"):
        v = normalized.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return _body_implies_new_file_creation("\n".join(parts))


def _safe_read_file(repo_root: Path, rel: str, limit: int = _MAX_FILE_READ) -> str | None:
    if not rel or ".." in rel.replace("\\", "/"):
        return None
    try:
        path = (repo_root / rel).resolve()
        root = repo_root.resolve()
        if path != root and root not in path.parents:
            return None
        if not path.is_file():
            return None
        data = path.read_bytes()
        if len(data) > limit:
            data = data[:limit]
        return data.decode("utf-8", errors="replace")
    except OSError:
        return None


def _heuristic_content_language(text: str) -> str:
    """Giriş metnine göre tr | en (basit sezgisel)."""
    s = (text or "").strip()
    if not s:
        return "en"
    sample = s[:12_000]
    if _TR_CHARS_RE.search(sample):
        return "tr"
    if _TR_HINT_RE.search(sample):
        return "tr"
    return "en"


def _task_language_override(task: str) -> str | None:
    low = (task or "").lower()
    if re.search(r"\b(in english|english only|translate to english)\b", low):
        return "en"
    if re.search(r"\b(türkçe|turkce|türkçeye|turkceye)\b", low):
        return "tr"
    return None


def _task_output_profile(body: str) -> dict[str, Any]:
    low = (body or "").lower()
    if any(x in low for x in ("özet", "summarize", "summary", "özeti", "kısaca özet")):
        return {"kind": "summary", "max_sentences": 5}
    if any(x in low for x in ("açıkla", "explain", "açıklama", "nedir")):
        return {"kind": "explain", "max_paragraphs": 1}
    if any(x in low for x in ("liste", "madde", "bullet", "maddeler")):
        return {"kind": "list", "bullets": True}
    return {"kind": "generic"}


def enrich_output_language(normalized: dict[str, Any]) -> dict[str, Any]:
    """Dosya/görev metnine göre içerik dili ve zorunlu çıktı dili (görevde açık dil varsa öncelik)."""
    out = dict(normalized)
    body = (out.get("target_body") or "").strip()
    blob = (out.get("agent_blob") or "").strip()
    fc = out.get("file_content_for_reasoning")
    task_text = body or blob
    if isinstance(fc, str) and fc.strip():
        content_lang = _heuristic_content_language(fc)
    elif task_text:
        content_lang = _heuristic_content_language(task_text)
    else:
        content_lang = "en"
    override = _task_language_override(task_text)
    out["content_language"] = content_lang
    out["output_language"] = override or content_lang
    out["task_output_profile"] = _task_output_profile(task_text)
    return out


def _sentence_count(text: str) -> int:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return 0
    chunks = re.split(r"(?<=[.!?…])\s+", t)
    return len([c for c in chunks if c.strip()])


def _looks_like_code_snippet(s: str) -> bool:
    return bool(
        re.search(r"(?:^|\n)\s*(?:def |class |import |from |\w+\s*=[^=])", s or "", re.MULTILINE)
    )


_EN_STOPWORDS = frozenset(
    {
        "the",
        "is",
        "are",
        "and",
        "or",
        "of",
        "to",
        "in",
        "it",
        "as",
        "be",
        "for",
        "on",
        "at",
        "by",
        "an",
        "a",
        "this",
        "that",
        "with",
        "from",
        "was",
        "has",
        "have",
    }
)

_FORBIDDEN_TASK_ECHO = (
    "özet çıkar",
    "summarize this",
    "only summarize",
    "just summarize",
    "summarize the",
    "please summarize",
)


def normalize_llm_generated_content(text: str) -> str:
    """Executor öncesi: trim, markdown h2–h6 başlık satırlarını at, fazla boşlukları sadeleştir."""
    raw = (text or "").strip()
    if not raw:
        return ""
    out_lines: list[str] = []
    for ln in raw.splitlines():
        stripped = ln.strip()
        if re.match(r"^#{2,6}\s+\S", stripped):
            continue
        out_lines.append(ln.rstrip())
    s = "\n".join(out_lines).strip()
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _word_alnum_tokens(s: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿçğıöşüÇĞİÖŞÜ]+", s)


def validate_llm_output(
    result: str,
    task: str,
    input_language: str,
    normalized: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """
    Kod seviyesinde LLM çıktı denetimi. (True, '') = geçerli; (False, 'validation_failed') = noop.
    """
    norm = normalized or {}
    r = (result or "").strip()
    if not r:
        return False, "validation_failed"

    is_code = _looks_like_code_snippet(r)
    rl = r.lower()
    task_s = (task or "").strip()
    tl = task_s.lower()

    if task_s:
        if tl == rl:
            return False, "validation_failed"
        if len(tl) >= 4 and tl in rl:
            return False, "validation_failed"
        if len(tl) >= 4 and rl.startswith(tl) and len(r) <= len(task_s) + 10:
            return False, "validation_failed"
    for phrase in _FORBIDDEN_TASK_ECHO:
        if phrase in rl:
            return False, "validation_failed"
    compact = re.sub(r"\s+", " ", rl).strip().rstrip(".!?")
    if compact in {"özet çıkar", "summarize", "summarize this", "only summarize", "just summarize"}:
        return False, "validation_failed"

    tokens = _word_alnum_tokens(r)
    if not is_code and len(tokens) < 5:
        return False, "validation_failed"

    il = (input_language or "en").lower()
    letters = [c for c in r if c.isalpha()]
    n_letters = len(letters)
    if not is_code and n_letters >= 12:
        if il == "tr":
            en_hits = sum(1 for t in tokens if t.lower() in _EN_STOPWORDS)
            if len(tokens) >= 8 and en_hits / len(tokens) > 0.35:
                return False, "validation_failed"
        elif il == "en":
            tr_letters = sum(1 for c in letters if _TR_CHARS_RE.match(c))
            if tr_letters / n_letters > 0.12:
                return False, "validation_failed"

    profile = norm.get("task_output_profile") or {}
    kind = profile.get("kind", "generic")
    if kind == "summary" and not is_code:
        max_s = int(profile.get("max_sentences", 5))
        if _sentence_count(r) > max_s + 1:
            return False, "validation_failed"
    if kind == "explain" and not is_code:
        max_p = int(profile.get("max_paragraphs", 1))
        paras = [p for p in r.split("\n\n") if p.strip()]
        if len(paras) > max_p + 1:
            return False, "validation_failed"
    if kind == "list" and profile.get("bullets") and not is_code:
        lines = [ln.strip() for ln in r.splitlines() if ln.strip()]
        if len(lines) >= 3:
            if not any(
                ln.startswith(("- ", "* ", "• ")) or re.match(r"^\d+\.\s", ln)
                for ln in lines[:15]
            ):
                return False, "validation_failed"

    return True, ""


def _extract_json_object(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    if not s:
        return None
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    i = s.find("{")
    j = s.rfind("}")
    if i >= 0 and j > i:
        try:
            obj = json.loads(s[i : j + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _call_openai_gate_json(user_message: str) -> tuple[dict[str, Any] | None, str | None]:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return None, "OPENAI_API_KEY yok"
    model = (os.getenv("OPENAI_MODEL") or "").strip() or "gpt-4.1-mini"
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _GATE_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                timeout=_LLM_TIMEOUT,
            )
        except TypeError:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _GATE_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                timeout=_LLM_TIMEOUT,
            )
        txt = (resp.choices[0].message.content or "").strip()
        parsed = _extract_json_object(txt)
        if not parsed:
            return None, "llm_json_parse"
        return parsed, None
    except Exception as e:
        return None, f"llm_error:{type(e).__name__}"


def _call_openai_substep_validator(
    user_message: str,
) -> tuple[dict[str, Any] | None, str | None]:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return None, "OPENAI_API_KEY yok"
    model = (os.getenv("OPENAI_MODEL") or "").strip() or "gpt-4.1-mini"
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SUBSTEP_VALIDATOR_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                timeout=_LLM_TIMEOUT,
            )
        except TypeError:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SUBSTEP_VALIDATOR_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                timeout=_LLM_TIMEOUT,
            )
        txt = (resp.choices[0].message.content or "").strip()
        parsed = _extract_json_object(txt)
        if not parsed:
            return None, "llm_json_parse"
        return parsed, None
    except Exception as e:
        return None, f"llm_error:{type(e).__name__}"


def _normalize_substep_llm_risk_hint(s: str) -> str:
    x = (s or "").strip().lower()
    if x in ("low", "medium", "high"):
        return x
    return "medium"


def validate_substep_with_llm(
    step: dict[str, Any],
    parent_task: dict[str, Any],
    *,
    fallback_marker_key: str = "llm_substep_validation",
) -> dict[str, Any]:
    """Plan / yürütme öncesi adımı LLM ile doğrular. API/parse hatasında policy+risk fallback (ok=true)."""
    user_msg = (
        "step = "
        + json.dumps(step, ensure_ascii=False, default=str)
        + "\n\nparent_task = "
        + json.dumps(parent_task, ensure_ascii=False, default=str)
    )
    parsed, err = _call_openai_substep_validator(user_msg)

    def _fallback(reason: str) -> dict[str, Any]:
        gr = classify_step_risk(step)
        rh = gr if gr in ("low", "medium", "high") else "medium"
        return {
            "ok": True,
            "reason": reason,
            "risk_hint": rh,
            fallback_marker_key: "fallback",
        }

    if parsed is None:
        return _fallback(
            f"LLM kullanılamadı; mevcut policy/risk uygulandı ({err or 'unknown'})"
        )
    if not isinstance(parsed.get("ok"), bool):
        return _fallback("LLM çıktısı geçersiz (ok alanı yok); mevcut policy/risk uygulandı")

    ok = bool(parsed.get("ok"))
    reason = str(parsed.get("reason") or "")
    risk_hint = _normalize_substep_llm_risk_hint(str(parsed.get("risk_hint") or "medium"))
    if risk_hint == "high":
        ok = False
        if not reason.strip():
            reason = "risk_hint=high (yıkıcı veya kritik risk)"
    return {"ok": ok, "reason": reason, "risk_hint": risk_hint}


def build_parent_task_context(
    *,
    mode: str,
    payload: str,
    norm: dict[str, Any],
    reasoning: dict[str, Any],
    reasoning_summary: str,
) -> dict[str, Any]:
    """execute_plan / substep LLM için üst görev özeti."""
    return {
        "mode": mode,
        "payload": (payload or "")[:4000],
        "reasoning_summary": reasoning_summary,
        "intent": reasoning.get("intent"),
        "target_rel": norm.get("target_rel"),
        "llm_mode": reasoning.get("llm_mode"),
        "reasoning_source": reasoning.get("source"),
    }


def _validate_llm_gate(o: dict[str, Any]) -> bool:
    mode = str(o.get("mode") or "").strip().lower().replace("-", "_")
    if mode == "no-op":
        mode = "no_op"
    if mode not in ("agent", "direct_patch", "no_op"):
        return False
    if mode == "direct_patch":
        gc = o.get("generated_content")
        if not isinstance(gc, str) or not gc.strip():
            return False
    return True


def _normalize_llm_mode(o: dict[str, Any]) -> str:
    mode = str(o.get("mode") or "").strip().lower().replace("-", "_")
    if mode == "no-op":
        return "no_op"
    return mode


def _format_mandatory_rules_block(norm: dict[str, Any]) -> str:
    ol = str(norm.get("output_language") or "en")
    cl = str(norm.get("content_language") or "en")
    prof = norm.get("task_output_profile") or {}
    kind = str(prof.get("kind", "generic"))
    lang_name = "Türkçe" if ol == "tr" else "English"
    lines = [
        "## Zorunlu çıktı kuralları (bunlara uy; aksi halde no_op seç)",
        f"- Hedef çıktı dili: {ol} ({lang_name}). Giriş/dosya dili tespiti: {cl}.",
        "- Çıktı dili, yukarıdaki hedef dil ile aynı olmalı (task içinde açık dil isteği varsa o önceliklidir).",
        "- Ham task / kullanici_gorevi metnini ASLA generated_content olarak yazma.",
        "- Sadece istenen işlemi yap; önsöz, özür veya 'işte sonuç' gibi meta cümleler yok.",
        f"- Görev profili: {kind}.",
    ]
    if kind == "summary":
        lines.append("- Özet: en fazla 3-5 cümle; isteğe bağlı tek satır '## Özet' başlığı.")
    elif kind == "explain":
        lines.append("- Açıklama: tek kısa paragraf.")
    elif kind == "list":
        lines.append("- Liste: satır başı '- ', '*' veya numaralı madde kullan.")
    lines.append("- Dosya içeriği yok veya kullanılamıyorsa mode=no_op.")
    return "\n".join(lines)


def _build_llm_user_prompt(normalized: dict[str, Any], repo_root: Path) -> str:
    mode = normalized.get("mode")
    parts: list[str] = []
    parts.append(f"bridge_mode={mode!r}")
    rel = normalized.get("target_rel")
    body = (normalized.get("target_body") or "").strip()
    blob = (normalized.get("agent_blob") or "").strip()
    tname = normalized.get("target_file_name")
    if rel:
        parts.append(f"hedef_dosya_adi={tname!r}")
        parts.append(f"hedef_dosya_goreceli_yol={rel!r}")
        parts.append(f"kullanici_gorevi=(ham_metin_executora_gitmez_yalnizca_niyet):\n{body}")
        st = normalized.get("file_read_status")
        fc = normalized.get("file_content_for_reasoning")
        if st == "create_intent":
            parts.append(
                "dosya_icerigi: (henüz yok — kullanıcı yeni dosya oluşturmayı istiyor; "
                "oluşturma amaçlı içerik üret veya no_op.)"
            )
        elif st == "ok" and isinstance(fc, str) and fc.strip():
            # Yalnızca diskten enrich ile gelen gerçek içerik
            parts.append(f"dosya_icerigi:\n{fc}")
        # ok/boş, eksik veya okunamadı: placeholder veya ikinci disk okuması yok —
        # zorunlu kurallar mode=no_op ile kapanır.
    elif blob:
        parts.append(f"serbest_metin_giris=(analiz_et):\n{blob}")
    else:
        parts.append("(bos)")
    parts.append(_format_mandatory_rules_block(normalized))
    parts.append(
        "Yanıtın yalnızca şemada belirtilen JSON olmalı. "
        "Ham kullanıcı cümlesini generated_content olarak verme."
    )
    return "\n\n".join(parts)


def _body_looks_like_code_patch(body: str) -> bool:
    b = (body or "").strip()
    if not b:
        return False
    if re.search(r"[çğıöşüÇĞİÖŞÜ]", b) and not re.search(
        r"(=|def\s|class\s|import\s|from\s|#\s*[\w\[]|\(|\)|\[|\])", b
    ):
        return False
    low = b.lower()
    nl_markers = (
        " özet",
        "özet ",
        "çıkar",
        "oluştur",
        "açıkla",
        "explain",
        "summarize",
        "describe ",
        "write a",
        "please ",
    )
    if any(m in low for m in nl_markers) and "=" not in b and "def " not in low:
        return False
    if re.match(r"^#+\s", b) or re.match(r"^[\w.]+\s*=", b):
        return True
    if "import " in b or b.startswith("from ") or re.search(r"\bdef\s+\w+", b):
        return True
    if "(" in b and ")" in b and len(b) < 500:
        return True
    if b.startswith("#") and len(b) < 240:
        return True
    return False


def normalize_request(mode: str | None, payload: str) -> dict[str, Any]:
    rel, body = _parse_target_instruction(payload)
    return {
        "mode": mode or "",
        "raw_payload": payload,
        "target_rel": rel,
        "target_body": body,
        "agent_blob": (payload or "").strip() if mode == "agent" else "",
    }


def enrich_normalized_with_target_file(
    normalized: dict[str, Any], repo_root: Path
) -> dict[str, Any]:
    """file+task (direct_patch) için hedef dosyayı oku; normalize payload'a snapshot ekle."""
    out = dict(normalized)
    mode = out.get("mode")
    rel = out.get("target_rel")
    if mode != "direct_patch" or not rel:
        out["file_read_status"] = "not_applicable"
        out["file_content_for_reasoning"] = None
        out["target_file_name"] = None
        return out
    # create_file: hiç okuma / yoklama; dosya yokluğu hata değil
    if _normalized_implies_file_create(out):
        out["file_read_status"] = "create_intent"
        out["file_content_for_reasoning"] = ""
        out["target_file_name"] = Path(str(rel).replace("\\", "/")).name
        return out
    text = _safe_read_file(repo_root, rel)
    if text is None:
        out["file_read_status"] = "missing_or_unreadable"
        out["file_content_for_reasoning"] = None
    elif not text.strip():
        out["file_read_status"] = "empty"
        out["file_content_for_reasoning"] = ""
    else:
        out["file_read_status"] = "ok"
        out["file_content_for_reasoning"] = text
    out["target_file_name"] = Path(str(rel).replace("\\", "/")).name
    return out


def _precheck_file_before_reasoning(norm: dict[str, Any]) -> dict[str, Any] | None:
    """Dosya yok/boşsa LLM çağrılmadan güvenli no_op. None = devam.

    create_intent (create_file) için reason_task önceden precheck çağırmaz; bu fonksiyon
    yine de create_intent görürse kısa devre eder.
    """
    if norm.get("mode") != "direct_patch" or not norm.get("target_rel"):
        return None
    st = norm.get("file_read_status")
    if st == "create_intent":
        return None
    if st == "missing_or_unreadable":
        return {
            "ok": True,
            "source": "precheck",
            "summary": "Hedef dosya okunamadı veya bulunamadı.",
            "llm_mode": "no_op",
            "generated_content": "",
            "intent": "precheck_file",
            "reason": "dosya okunamadı veya yok",
        }
    if st == "empty":
        return {
            "ok": True,
            "source": "precheck",
            "summary": "Hedef dosya boş; içerik üretilemez.",
            "llm_mode": "no_op",
            "generated_content": "",
            "intent": "precheck_file",
            "reason": "dosya boş",
        }
    return None


HIGH_RISK_KEYWORDS = (
    "sil",
    "delete",
    "remove",
    "unlink",
)


def is_high_risk_keyword_text(text: str) -> bool:
    """Tehlikeli komut / silme ifadeleri → yüksek risk (onay gerekir)."""
    t = (text or "").lower()
    if any(k in t for k in HIGH_RISK_KEYWORDS):
        return True
    # "rm" yalnızca kelime sınırında (term, worm vb. yanlış pozitif olmasın)
    return bool(re.search(r"(?<![a-z0-9_])rm(?![a-z0-9_])", t))


def merge_text_for_risk_assessment(norm: dict[str, Any], payload: str) -> str:
    """Ham istek + hedef gövde + agent metni birlikte taranır."""
    chunks: list[str] = []
    p = (payload or "").strip()
    if p:
        chunks.append(p)
    for key in ("raw_payload", "target_body", "agent_blob"):
        v = norm.get(key)
        if isinstance(v, str) and v.strip():
            chunks.append(v.strip())
    seen: set[str] = set()
    out: list[str] = []
    for c in chunks:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return "\n".join(out)


_MEANINGFUL_TOKEN_RE = re.compile(
    r"[0-9]+[A-Za-z]+|[0-9A-Za-zçğıöşüÇĞİÖŞÜ]+", re.UNICODE
)
_VAGUE_BIGRAMS = frozenset({
    ("devam", "et"),
    ("keep", "going"),
})

# Yalnızca ritüel niyet; «başlat» fiili nesne ile birlikte ayrıca ele alınır (explicit_action_object).
_VAGUE_ONLY_UNIGRAMS = frozenset({
    "başla",
    "başlayalım",
    "başlayın",
    "başlayalı",
    "yap",
    "yapalım",
    "yapın",
    "devam",
    "haydi",
    "hadi",
    "gel",
    "gidelim",
    "gidin",
    "gelin",
    "ok",
    "tamam",
    "tamamdır",
    "şimdi",
    "lütfen",
    "evet",
    "evt",
    "go",
    "start",
    "continue",
    "begin",
    "help",
    "yardım",
    "pls",
    "please",
    "et",  # yalnızca "devam et" bigramında anlamlı; tek başına ritüel
})

_PATH_OR_FILENAME_RE = re.compile(r"[\w./\\~-]+\.\w{2,16}\b")
# 720p, 0.10p, 4k, 16:9 — görev yapısını düşürmez; yalnızca ek nitelik.
_MEDIA_QUALITY_OR_RATIO_RE = re.compile(
    r"(?:"
    r"\b\d{3,4}p\b|"
    r"\b\d+[.:]\d+p\b|"
    r"\b\d{2,4}k\b|"
    r"\b\d+:\d+\b"
    r")",
    re.I,
)
_OBJECT_OR_DELIVERABLE_RE = re.compile(
    r"\b(?:"
    r"dosya|klasör|klasor|video|görsel|gorsel|mesaj|resim|image|audio|ses|özet|ozet|rapor|readme|"
    r"dokümantasyon|dokuman|api|endpoint|sayfa|site|web|kod|test|modül|modul|docker|db|sql|"
    r"commit|branch|issue|patch|logo|ikon|thumbnail|pdf|csv|json|yaml|html|css|"
    r"proje|uygulama|servis|paket|plugin|kütüphane|kutuphane|"
    r"fonksiyon|metot|method|sınıf|sinif|class|değişken|degisken|buton|ekran|liste|satır|satir|"
    r"log|versiyon|build|release|işlem|islem|özellik|ozellik|kural|kayıt|kayit|komut|talimat"
    r")\w*",
    re.I,
)
_ACTION_RE = re.compile(
    r"\b(?:"
    r"sil|kaldır|kaldir|ekle|güncelle|guncelle|düzenle|duzenle|değiştir|degistir|yaz|oluştur|"
    r"olustur|üret|uret|gönder|yolla|aç|ac|kapat|başlat|baslat|kaydet|"
    r"özetle|ozetle|açıkla|acikla|taşı|tasi|kopyala|çalıştır|calistir|düzelt|"
    r"duzelt|yeniden|adlandır|adlandir|birleştir|birlestir|ayıkla|ayikla|çıkar|cikar|aktar|"
    r"delete|remove|add|update|edit|create|make|generate|fix|run|build|deploy|install|refactor|"
    r"extract|merge|split|rename|move"
    r")\w*",
    re.I,
)
_CONTEXT_RE = re.compile(
    r"\b(?:"
    r"bu|şu|su|o|bunu|şunu|sunu|onu|bunda|şunda|tüm|tum|her|bazı|bazi|hiçbir|hicbir|"
    r"hepsi|hepsini|herşeyi|herseyi|içindeki|icindeki|altındaki|altindaki|listesini|arasındaki|"
    r"arasindaki|sonraki|önceki|onceki|birinci|ikinci|üçüncü|ucuncu|"
    r"this|that|these|those|all|every|any|the"
    r")\w*",
    re.I,
)


def _text_has_path_or_ext_signal(text: str) -> bool:
    t = text or ""
    if _PATH_OR_FILENAME_RE.search(t):
        return True
    return "/" in t or "\\" in t


def _text_has_resolution_signal(text: str) -> bool:
    """720p, 0.10p, 4k, 16:9 vb. — nesne yokken bile görev niteliği sayılır; düşürme yapmaz."""
    return bool(_MEDIA_QUALITY_OR_RATIO_RE.search(text or ""))


def _token_is_media_or_numeric_attribute(tok: str) -> bool:
    """Anlamlı sözcük sayımında çözünürlük/fiyat/oran parçalarını çıkar."""
    t = (tok or "").strip().lower()
    if not t:
        return True
    if t.isdigit():
        return True
    if _MEDIA_QUALITY_OR_RATIO_RE.search(t):
        return True
    if re.fullmatch(r"\d+[.:]\d+p", t):
        return True
    return False


# Emir kipi fiil + çekirdek nesne — sayı/nitelik araya girse de geçerli.
_EXPLICIT_CORE_ACTION_RE = re.compile(
    r"\b(?:"
    r"üret|uret|oluştur|olustur|sil|gönder|yolla|aç|ac|kapat|başlat|baslat|kaydet|"
    r"güncelle|guncelle|düzenle|duzenle|değiştir|degistir|yaz|ekle|özetle|ozetle|"
    r"kopyala|çalıştır|calistir|düzelt|duzelt|taşı|tasi"
    r")\b",
    re.I,
)
_EXPLICIT_CORE_OBJECT_RE = re.compile(
    r"\b(?:"
    r"video|dosya|rapor|görsel|gorsel|mesaj|klasör|klasor|özet|ozet|readme|"
    r"fonksiyon|metot|method|sınıf|sinif|class|log|"
    r"resim|image|audio|ses|pdf|csv|json|commit|branch|issue|patch"
    r")\w*",
    re.I,
)


def explicit_imperative_action_and_object(text: str) -> bool:
    """
    Açık emir fiili + açık nesne kökü (ör. «video üret», «720p video üret», «tüm dosyaları sil»).
    Soru cümlesi ayrıca bridge tarafında elenir.
    """
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    if not (_EXPLICIT_CORE_ACTION_RE.search(low) and _EXPLICIT_CORE_OBJECT_RE.search(low)):
        return False
    return bool(_ACTION_RE.search(low))


def meaningful_tokens(task_text: str) -> list[str]:
    return [m.group(0).lower() for m in _MEANINGFUL_TOKEN_RE.finditer(task_text or "")]


def _strip_target_lines(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    rest = [ln for ln in lines if not ln.upper().startswith("TARGET:")]
    return "\n".join(rest).strip() if rest else (text or "").strip()


def _user_command_surface_for_vagueness(norm: dict[str, Any], payload: str) -> str:
    """TARGET: gibi köprü gövdelerini çıkar; yalnızca kullanıcı komutunu değerlendir."""
    # Köprü plain-text gönderiminde ingest bazen tüm "TARGET:\\n<görev>" gövdesi;
    # normalize_request ise target_body'yi zaten ayırmış olur — önce onu kullan.
    tb = str(norm.get("target_body") or "").strip()
    if tb:
        return tb
    ing = str(norm.get("ingest_raw_text") or norm.get("ingest_title") or "").strip()
    if ing:
        stripped = _strip_target_lines(ing)
        if stripped:
            return stripped
        return ing
    ab = str(norm.get("agent_blob") or "").strip()
    if ab:
        stripped = _strip_target_lines(ab)
        if stripped:
            return stripped
        return ab
    p = (payload or "").strip()
    stripped = _strip_target_lines(p)
    return stripped if stripped else p


def lumos_intent_decision_kind(reasoning: dict[str, Any]) -> str:
    """
    Karar (proceed | unclear) yalnızca niyet netliği ile; yürütme / LLM / özellik
    eksikliği burada reddedilmez — kapasite ayrıca özet ve yürütme modunda bildirilir.
    """
    intent = str(reasoning.get("intent") or "").strip().lower()
    if intent == "vague_intent":
        return "unclear"
    return "proceed"


def user_command_meets_task_structure(text: str) -> bool:
    """
    Görev yapısı: nesne ipucu VEYA eylem+bağlam VEYA eylem + en az iki anlamlı parça
    (örn. «video üret», «fonksiyonu güncelle», «logları sil»).
    """
    t = (text or "").strip()
    if not t:
        return False
    if explicit_imperative_action_and_object(t):
        return True
    toks = meaningful_tokens(t)
    uniq = list(dict.fromkeys(toks))
    if len(uniq) == 2 and (uniq[0], uniq[1]) in _VAGUE_BIGRAMS:
        return False

    substantive = [t for t in uniq if t not in _VAGUE_ONLY_UNIGRAMS]
    substantive_core = [x for x in substantive if not _token_is_media_or_numeric_attribute(x)]
    if not substantive_core:
        return False

    has_obj = bool(
        _OBJECT_OR_DELIVERABLE_RE.search(t)
        or _text_has_path_or_ext_signal(t)
        or _text_has_resolution_signal(t)
    )
    has_act = bool(_ACTION_RE.search(t))
    structural_n = len(substantive_core)
    has_ctx = bool(_CONTEXT_RE.search(t) or structural_n >= 3)
    path_or_res = _text_has_path_or_ext_signal(t) or _text_has_resolution_signal(t)

    if has_obj:
        return True
    if has_act and (has_ctx or path_or_res):
        return True
    if has_act and structural_n >= 2:
        return True
    return False


def user_intent_text_is_too_vague_for_action(norm: dict[str, Any], payload: str) -> bool:
    """
    Belirsiz komutlar (hedef/niyet yok): yalnızca "başla / yap / başlayalım" vb. kabul edilmez.

    En az biri gerekir:
    - Nesne / teslimat ipucu (ne yapılacak? — dosya, video, özet, yol, çözünürlük, …)
    - VEYA eylem + bağlam (ör. "tüm dosyaları sil", "bu dosyayı düzenle", "şunu özetle").
    - VEYA eylem + ikinci anlamlı kelime (eylem+nesne sırası serbest).
    """
    text = _user_command_surface_for_vagueness(norm, payload).strip()
    if not text:
        return True
    return not user_command_meets_task_structure(text)


def classify_risk(task_text: str, file_path: str | None) -> str:
    _ = file_path
    t = (task_text or "").lower()
    if is_high_risk_keyword_text(t):
        return "high"
    if any(x in t for x in ["taşı", "move", "rename"]):
        return "high"
    if any(x in t for x in ["değiştir", "replace", "overwrite"]):
        return "medium"
    if any(x in t for x in ["özet", "summarize", "analiz", "incele"]):
        return "low"
    return "unknown"


def _risk_gate_execution_mode(risk: str) -> str:
    if risk == "high":
        return "pending_approval"
    if risk == "medium":
        return "restricted"
    if risk == "low":
        return "direct_patch"
    return "restricted"


def _inject_risk_fields(
    body: dict[str, Any], risk: str, *, approved_high: bool = False
) -> None:
    lg = body.get("lumos_gate")
    if risk == "high" and approved_high:
        body["risk_level"] = risk
        ex_mode = str((isinstance(lg, dict) and lg.get("execution_mode")) or "direct_patch")
        body["execution_mode"] = ex_mode
        if isinstance(lg, dict):
            lg["risk_level"] = risk
            prev = str(lg.get("execution_mode") or ex_mode)
            lg["risk_execution_mode"] = f"approved:{prev}"
        return
    gate = _risk_gate_execution_mode(risk)
    body["risk_level"] = risk
    body["execution_mode"] = gate
    if isinstance(lg, dict):
        lg["risk_level"] = risk
        lg["risk_execution_mode"] = gate


def _jsonable_normalized(norm: dict[str, Any]) -> dict[str, Any]:
    def conv(x: Any) -> Any:
        if isinstance(x, dict):
            return {k: conv(v) for k, v in x.items()}
        if isinstance(x, list):
            return [conv(i) for i in x]
        if isinstance(x, Path):
            return str(x)
        if isinstance(x, (str, int, float, bool)) or x is None:
            return x
        return str(x)

    d = conv(dict(norm))
    fc = d.get("file_content_for_reasoning")
    if isinstance(fc, str) and len(fc) > 8000:
        d["file_content_for_reasoning"] = fc[:8000] + "\n... [truncated]"
    return d


def _pending_user_facing_title(*, payload: str, norm: dict[str, Any]) -> str:
    """UI / onay kartı: köprüden gelen ham metin, sonra gövde / payload."""
    ir = str(norm.get("ingest_raw_text") or "").strip()
    if ir:
        return ir
    it = str(norm.get("ingest_title") or "").strip()
    if it:
        return it
    tb = str(norm.get("target_body") or "").strip()
    if tb:
        return tb
    ab = str(norm.get("agent_blob") or "").strip()
    if ab:
        return ab
    p = (payload or "").strip()
    if p:
        return p
    rp = str(norm.get("raw_payload") or "").strip()
    if rp:
        return rp
    return ""


def _pending_approval_record(
    *,
    mode: str,
    payload: str,
    norm: dict[str, Any],
    ctx: GateContext,
    plan: dict[str, Any],
    reasoning: dict[str, Any],
) -> dict[str, Any]:
    title = _pending_user_facing_title(payload=payload, norm=norm).strip()
    return {
        "schema_version": "lumos.pending_approval.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "original_payload": payload,
        "title": title,
        "goal": title,
        "raw_text": title,
        "mode": mode,
        "normalized_task": _jsonable_normalized(norm),
        "execution_plan": dict(plan),
        "reasoning_snapshot": dict(reasoning),
        "risk_level": "high",
        "reasoning_summary": ctx.reasoning_summary,
        "policy_ok": True,
        "execution_mode": "pending_approval",
        "final_decision": "await_user_approval",
    }


def _build_high_risk_pending_http_body(
    ctx: GateContext,
    reasoning: dict[str, Any],
) -> dict[str, Any]:
    """High risk: executor çağrılmaz; onay beklenir (approval_granted ile aşılır)."""
    summ = ctx.reasoning_summary
    suffix = "HIGH RISK → kullanıcı onayı gerekli"
    if suffix not in summ:
        ctx.reasoning_summary = f"{summ} | {suffix}".strip(" |")
    lg: dict[str, Any] = {
        "policy_ok": ctx.policy_ok,
        "reasoning_summary": ctx.reasoning_summary,
        "reasoning_source": reasoning.get("source"),
        "risk_level": "high",
        "risk_execution_mode": "pending_approval",
        "final_decision": "await_user_approval",
        "enforced": True,
        "decision_kind": "blocked",
    }
    return {
        "accepted": True,
        "requires_approval": True,
        "error": "",
        "message": "Lumos: yüksek riskli işlem, kullanıcı onayı bekleniyor",
        "risk_level": "high",
        "execution_mode": "pending_approval",
        "final_decision": "await_user_approval",
        "enforced": True,
        "decision_kind": "blocked",
        "lumos_gate": lg,
    }


def _return_high_risk_pending(
    ctx: GateContext,
    reasoning: dict[str, Any],
    mode: str,
    payload: str,
    norm: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    body = _build_high_risk_pending_http_body(ctx, reasoning)
    out = _handle_task_return(
        http_body=body,
        last_ex=None,
        last_res=None,
        risk="high",
        approval_granted=False,
    )
    out["pending_approval_record"] = _pending_approval_record(
        mode=mode,
        payload=payload,
        norm=norm,
        ctx=ctx,
        plan=plan,
        reasoning=reasoning,
    )
    return out


def _handle_task_return(
    *,
    http_body: dict[str, Any],
    last_ex: dict[str, Any] | None,
    last_res: dict[str, Any] | None,
    risk: str,
    approval_granted: bool = False,
) -> dict[str, Any]:
    """Üst seviye meta: bridge guard'ları out üzerinden okuyabilsin."""
    if risk == "high" and not approval_granted:
        return {
            "http_status": 200,
            "http_body": http_body,
            "last_execution": None,
            "last_result": None,
            "risk_level": "high",
            "execution_mode": "pending_approval",
            "final_decision": "await_user_approval",
            "enforced": True,
        }
    return {
        "http_status": 200,
        "http_body": http_body,
        "last_execution": last_ex,
        "last_result": last_res,
        "risk_level": risk,
        "execution_mode": http_body.get(
            "execution_mode", _risk_gate_execution_mode(risk)
        ),
        "final_decision": "allow",
        "enforced": False,
    }


def policy_check(normalized: dict[str, Any]) -> bool:
    return True


def reason_task_heuristic(normalized: dict[str, Any], *, llm_error: str | None) -> dict[str, Any]:
    mode = normalized.get("mode")
    rel = normalized.get("target_rel")
    body = (normalized.get("target_body") or "").strip()
    fb = f"heuristic_fallback({llm_error or 'n/a'})"
    if mode == "direct_patch" and rel:
        if _body_looks_like_code_patch(body):
            return {
                "ok": True,
                "source": "heuristic",
                "summary": f"Lumos gate: kod/patch şeklinde gövde; LLM yok/hata — {fb}.",
                "llm_mode": "direct_patch",
                "generated_content": body,
                "intent": "structured_patch",
                "reason": fb,
            }
        return {
            "ok": True,
            "source": "heuristic",
            "summary": f"Lumos gate: doğal dil görevi; LLM yok/hata — uygulanmadı ({fb}).",
            "llm_mode": "no_op",
            "generated_content": "",
            "intent": "blocked_nl",
            "reason": fb,
        }
    if mode == "agent":
        return {
            "ok": False,
            "source": "heuristic",
            "summary": f"Lumos gate: agent hattı LLM olmadan ham metin gönderilmez — {fb}.",
            "llm_mode": "no_op",
            "generated_content": "",
            "intent": "agent_requires_llm",
            "reason": fb,
        }
    return {
        "ok": False,
        "source": "heuristic",
        "summary": "Lumos gate: bilinmeyen mod.",
        "llm_mode": "no_op",
        "generated_content": "",
        "intent": "unknown",
        "reason": fb,
    }


def reason_task(
    normalized: dict[str, Any], repo_root: Path, payload: str = ""
) -> dict[str, Any]:
    # create_file: precheck tamamen devre dışı (dosya yokluğu / boş okuma yoklaması yok)
    shortcut = None
    if normalized.get("file_read_status") != "create_intent":
        shortcut = _precheck_file_before_reasoning(normalized)
    if shortcut is not None:
        return shortcut

    if user_intent_text_is_too_vague_for_action(normalized, payload):
        return {
            "ok": False,
            "source": "heuristic",
            "summary": (
                "Görev net değil; lütfen netleştirin. Hangi dosya, video, özet veya API gibi "
                "bir nesne ya da hedef yazın; ya da eylem ile bağlam birlikte verin "
                "(örn. «tüm testleri çalıştır», «bu dosyayı sil»). "
                "«Başla», «yap», «başlayalım» gibi tek başına genel komutlar yeterli değildir; "
                "otomatik ilerleme yapılmaz."
            ),
            "llm_mode": "no_op",
            "generated_content": "",
            "intent": "vague_intent",
            "reason": "no_object_or_action_context",
        }

    llm_parsed: dict[str, Any] | None = None
    llm_err: str | None = None
    if (os.getenv("OPENAI_API_KEY") or "").strip():
        um = _build_llm_user_prompt(normalized, repo_root)
        llm_parsed, llm_err = _call_openai_gate_json(um)
    if llm_parsed and _validate_llm_gate(llm_parsed):
        mode = _normalize_llm_mode(llm_parsed)
        gc_for_exec = ""
        if mode == "direct_patch":
            gc_for_exec = normalize_llm_generated_content(
                str(llm_parsed.get("generated_content") or "")
            )
            inp_lang = str(
                normalized.get("output_language")
                or normalized.get("content_language")
                or "en"
            )
            task_txt = (
                normalized.get("target_body") or normalized.get("agent_blob") or ""
            ).strip()
            ok_val, vreason = validate_llm_output(
                gc_for_exec, task_txt, inp_lang, normalized
            )
            if False and not ok_val:
                return {
                    "ok": True,
                    "source": "validation",
                    "summary": "Çıktı doğrulama katmanından geçmedi (kod denetimi).",
                    "llm_mode": "no_op",
                    "generated_content": "",
                    "intent": "validation_failed",
                    "reason": vreason,
                }
        return {
            "ok": True,
            "source": "llm",
            "summary": str(llm_parsed.get("reason") or llm_parsed.get("intent") or ""),
            "llm_mode": mode,
            "generated_content": gc_for_exec if mode == "direct_patch" else "",
            "intent": str(llm_parsed.get("intent") or ""),
            "reason": str(llm_parsed.get("reason") or ""),
        }
    return reason_task_heuristic(normalized, llm_error=llm_err or "invalid_llm_response")


def build_execution_plan(
    normalized: dict[str, Any],
    reasoning: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    if not reasoning.get("ok"):
        return {"steps": [], "detail": reasoning.get("summary", "reasoning blocked")}
    lm = str(reasoning.get("llm_mode") or "no_op")
    rel = normalized.get("target_rel")

    if lm == "no_op":
        return {"steps": [], "detail": reasoning.get("summary", "no_op")}

    if lm == "agent":
        intent = str(reasoning.get("intent") or "").strip()
        rs = str(reasoning.get("reason") or reasoning.get("summary") or "").strip()
        goal = f"Lumos bridge (LLM plan)\nIntent: {intent}\nReason: {rs}"
        if rel:
            goal += f"\nTarget file (context): {rel}"
        return {
            "steps": [{"type": "agent", "goal": goal}],
            "detail": reasoning.get("summary", ""),
        }

    if lm == "direct_patch":
        gen = (reasoning.get("generated_content") or "").strip()
        if not gen:
            return {"steps": [], "detail": "direct_patch without generated_content"}
        if not rel:
            return {"steps": [], "detail": "direct_patch without target path"}
        r = str(rel).replace("\\", "/")
        return {
            "steps": [
                {"type": "patch", "file": r, "content": gen},
                {"type": "log", "message": "Lumos: patch step completed"},
            ],
            "detail": reasoning.get("summary", ""),
        }

    return {"steps": [], "detail": "unknown llm_mode"}


def _plan_step_mutating(step: dict[str, Any]) -> bool:
    return step.get("type") in ("patch", "agent", "agent_auto")


def _plan_steps_mutating(plan: dict[str, Any]) -> bool:
    for s in plan.get("steps") or []:
        if isinstance(s, dict) and _plan_step_mutating(s):
            return True
    return False


def _merge_risk_class(a: str, b: str) -> str:
    order = {"low": 0, "unknown": 1, "medium": 2, "high": 3}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def classify_step_risk(step: dict[str, Any]) -> str:
    t = str(step.get("type") or "")
    extra = str(step.get("task") or "").strip()
    extra_risk = classify_risk(extra, None) if extra else "low"
    if t == "log":
        msg = str(step.get("message") or "")
        return _merge_risk_class(classify_risk(msg, None), extra_risk)
    if t == "patch":
        c = str(step.get("content") or "")
        fp = step.get("file")
        r = classify_risk(c, str(fp) if fp else None)
        return _merge_risk_class(r, extra_risk)
    if t == "agent":
        r = classify_risk(str(step.get("goal") or ""), None)
        return _merge_risk_class(r, extra_risk)
    if t == "agent_auto":
        r = classify_risk(str(step.get("agent_blob") or ""), None)
        return _merge_risk_class(r, extra_risk)
    return _merge_risk_class("unknown", extra_risk)


def plan_has_high_risk_step(plan: dict[str, Any]) -> bool:
    for s in plan.get("steps") or []:
        if isinstance(s, dict) and classify_step_risk(s) == "high":
            return True
    return False


def _plan_step_to_mode_payload(step: dict[str, Any]) -> tuple[str, str]:
    t = step.get("type")
    if t == "patch":
        rel = str(step.get("file") or "").strip().replace("\\", "/")
        content = str(step.get("content") or "")
        return "direct_patch", f"TARGET: {rel}\n{content}\n"
    if t == "agent":
        return "agent", str(step.get("goal") or "")
    if t == "agent_auto":
        return "agent", str(step.get("agent_blob") or "")
    if t == "log":
        return "agent", str(step.get("message") or "")
    return "agent", ""


def run_lumos_gate_substep(
    step: dict[str, Any],
    *,
    repo_root: Path,
    approval_granted: bool = False,
) -> dict[str, Any]:
    """
    Her plan adımı için Lumos kapısı (policy + risk). LLM yeni plan üretmez; adım olduğu gibi kalır.
    """
    mode, pl = _plan_step_to_mode_payload(step)
    ctx = GateContext()
    ctx.ingress_payload = {"is_substep": True, "step_type": step.get("type")}
    norm = normalize_request(mode, pl)
    norm = enrich_normalized_with_target_file(norm, repo_root)
    norm = enrich_output_language(norm)
    norm["is_substep"] = True
    ctx.normalized_task = norm.get("target_body") or norm.get("agent_blob") or ""
    ctx.policy_ok = policy_check(norm)
    if not ctx.policy_ok:
        return {
            "_substep_gate_ok": False,
            "policy_ok": False,
            "gate_complete": True,
            "http_status": 403,
            "error": "step blocked by lumos",
            "step": dict(step),
            "execution_mode": "rejected_policy",
        }

    sr = classify_step_risk(step)
    task_text = merge_text_for_risk_assessment(norm, pl)
    tr = classify_risk(task_text, norm.get("target_rel"))
    effective_risk = _merge_risk_class(sr, tr)

    if effective_risk == "high" and not approval_granted:
        return {
            "_substep_gate_ok": False,
            "policy_ok": True,
            "gate_complete": True,
            "error": "step requires approval",
            "step": dict(step),
            "execution_mode": "pending",
            "risk_level": "high",
        }

    if (
        not approval_granted
        and effective_risk in ("medium", "unknown")
        and _plan_step_mutating(step)
    ):
        return {
            "_substep_gate_ok": False,
            "policy_ok": True,
            "gate_complete": True,
            "error": "step blocked by lumos",
            "step": dict(step),
            "execution_mode": "restricted",
            "detail": f"RISK: {effective_risk} → otomatik uygulama kapalı",
        }

    return {
        "_substep_gate_ok": True,
        "policy_ok": True,
        "gate_complete": True,
        "execution_mode": "allow",
    }


def _audit_finalize_non_plan(
    audit: LumosAuditCollector,
    kind: str,
    ex: dict[str, Any] | None,
    job_id: str | None,
    plan: dict[str, Any],
) -> None:
    if kind == "direct_patch" and isinstance(ex, dict):
        er = str(ex.get("execution_result") or "")
        audit.set_step_results([{"type": "direct_patch", "execution_result": er}])
        audit.set_summary(
            blocked=er not in ("patch_applied", "no_change"),
            reason=str(ex.get("detail") or ""),
            execution_result=er,
            execution_kind=kind,
            job_id=job_id,
        )
    elif kind == "agent":
        audit.set_step_results([{"type": "agent", "job_id": job_id}])
        audit.set_summary(
            blocked=False,
            reason="",
            execution_result="agent_job_started",
            execution_kind=kind,
            job_id=job_id,
        )
    elif kind == "noop":
        audit.set_step_results([])
        audit.set_summary(
            blocked=False,
            reason=str(plan.get("detail") or ""),
            execution_result="gate_skipped",
            execution_kind=kind,
        )
    elif kind == "agent_auto" and isinstance(ex, dict):
        er = str(ex.get("execution_result") or "agent_auto_local")
        audit.set_step_results([{"type": "agent_auto", "execution_result": er}])
        audit.set_summary(
            blocked=False,
            reason=str(ex.get("detail") or ""),
            execution_result=er,
            execution_kind=kind,
        )


def _execute_plan_legacy(
    plan: dict[str, Any],
    *,
    run_direct: Callable[[str], dict[str, Any]],
    start_agent: Callable[[str, bool], str],
    run_agent_auto: Callable[[str], None] | None,
    audit: LumosAuditCollector | None = None,
) -> tuple[str, dict[str, Any] | None, str | None]:
    if audit is not None:
        audit.set_plan(plan)
    action = plan.get("action")
    if action == "noop" or not action:
        if audit is not None:
            audit.set_step_results([])
            audit.set_summary(
                blocked=False,
                reason="",
                execution_result="noop",
                execution_kind="noop",
            )
        return "noop", None, None
    if action == "direct_patch":
        instr = plan.get("instruction") or ""
        ex = run_direct(instr)
        if audit is not None:
            _audit_finalize_non_plan(audit, "direct_patch", ex, None, plan)
        return "direct_patch", ex, None
    if action == "agent":
        jid = start_agent(plan.get("goal") or "", True)
        if audit is not None:
            _audit_finalize_non_plan(audit, "agent", None, jid, plan)
        return "agent", None, jid
    if action == "agent_auto":
        if run_agent_auto:
            run_agent_auto(plan.get("agent_blob") or "")
        ex = {"execution_result": "agent_auto_local", "detail": plan.get("detail", "")}
        if audit is not None:
            _audit_finalize_non_plan(audit, "agent_auto", ex, None, plan)
        return "agent_auto", ex, None
    if audit is not None:
        audit.set_step_results([])
        audit.set_summary(
            blocked=False,
            reason="",
            execution_result="noop",
            execution_kind="noop",
        )
    return "noop", None, None


def _execute_plan_steps(
    plan: dict[str, Any],
    *,
    run_direct: Callable[[str], dict[str, Any]],
    start_agent: Callable[[str, bool], str],
    run_agent_auto: Callable[[str], None] | None,
    repo_root: Path | None = None,
    approval_granted: bool = False,
    parent_task: dict[str, Any] | None = None,
    audit: LumosAuditCollector | None = None,
) -> tuple[str, dict[str, Any] | None, str | None]:
    steps = plan.get("steps")
    if not isinstance(steps, list):
        return "noop", None, None
    if len(steps) == 0:
        if audit is not None:
            audit.set_step_results([])
            audit.set_summary(
                blocked=False,
                reason="",
                execution_result="noop",
                execution_kind="plan",
            )
        return "noop", None, None

    plan_llm_fallback = False
    # Tüm adımlar önce kapıdan geçer; biri bloklanırsa hiçbiri yürütülmez (kısmi uygulama yok).
    if repo_root is not None:
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                if audit is not None:
                    audit.set_step_results([])
                    audit.set_summary(
                        blocked=True,
                        reason="invalid step",
                        execution_result="substep_gate_blocked",
                        execution_kind="plan",
                    )
                return (
                    "plan",
                    {
                        "execution_result": "substep_gate_blocked",
                        "detail": {"error": "invalid step", "step": step},
                        "step_results": [],
                    },
                    None,
                )
            gate = run_lumos_gate_substep(
                step,
                repo_root=repo_root,
                approval_granted=approval_granted,
            )
            sr = classify_step_risk(step)
            pol_allowed = (
                gate.get("policy_ok", True)
                and gate.get("execution_mode") != "pending"
                and gate.get("_substep_gate_ok", False)
            )
            if audit is not None:
                audit.record_policy_phase(i, step, sr, pol_allowed, gate)
            if not gate.get("policy_ok", True):
                if audit is not None:
                    audit.set_step_results([])
                    audit.set_summary(
                        blocked=True,
                        reason="policy substep",
                        execution_result="substep_gate_blocked",
                        execution_kind="plan",
                    )
                return (
                    "plan",
                    {
                        "execution_result": "substep_gate_blocked",
                        "detail": {"gate": gate, "error": gate.get("error")},
                        "step_results": [],
                        "blocked_step": gate.get("step"),
                    },
                    None,
                )
            if gate.get("execution_mode") == "pending":
                if audit is not None:
                    audit.set_step_results([])
                    audit.set_summary(
                        blocked=True,
                        reason="step requires approval",
                        execution_result="substep_gate_blocked",
                        execution_kind="plan",
                    )
                return (
                    "plan",
                    {
                        "execution_result": "substep_gate_blocked",
                        "detail": {"gate": gate, "error": "step requires approval"},
                        "step_results": [],
                        "blocked_step": gate.get("step"),
                    },
                    None,
                )
            if not gate.get("_substep_gate_ok", False):
                if audit is not None:
                    audit.set_step_results([])
                    audit.set_summary(
                        blocked=True,
                        reason="substep gate",
                        execution_result="substep_gate_blocked",
                        execution_kind="plan",
                    )
                return (
                    "plan",
                    {
                        "execution_result": "substep_gate_blocked",
                        "detail": gate,
                        "step_results": [],
                        "blocked_step": gate.get("step"),
                    },
                    None,
                )

            if parent_task is not None:
                llm_check = validate_substep_with_llm(
                    step, parent_task, fallback_marker_key="llm_substep_validation"
                )
                if llm_check.get("llm_substep_validation") == "fallback":
                    plan_llm_fallback = True
                if audit is not None:
                    audit.record_plan_llm_phase(
                        i, step, sr, bool(llm_check.get("ok")), llm_check
                    )
                if not llm_check.get("ok"):
                    if audit is not None:
                        audit.set_step_results([])
                        audit.set_summary(
                            blocked=True,
                            reason="substep rejected by llm validation",
                            execution_result="substep_llm_blocked",
                            execution_kind="plan",
                        )
                    return (
                        "plan",
                        {
                            "execution_result": "substep_llm_blocked",
                            "detail": {
                                "error": "substep rejected by llm validation",
                                "step": step,
                                "llm_check": llm_check,
                            },
                            "step_results": [],
                            "blocked_step": step,
                        },
                        None,
                    )

    results: list[dict[str, Any]] = []
    last_patch_ex: dict[str, Any] | None = None
    last_instr_preview = ""
    last_jid: str | None = None
    execution_llm_fallback = False

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            if audit is not None:
                audit.set_step_results(results)
                audit.set_summary(
                    blocked=True,
                    reason="invalid step",
                    execution_result="step_failed",
                    execution_kind="plan",
                    job_id=last_jid,
                )
            return (
                "plan",
                {
                    "execution_result": "step_failed",
                    "detail": "invalid step",
                    "step_results": results,
                },
                last_jid,
            )
        if repo_root is not None and parent_task is not None:
            pre_exec_check = validate_substep_with_llm(
                step, parent_task, fallback_marker_key="execution_llm_check"
            )
            if pre_exec_check.get("execution_llm_check") == "fallback":
                execution_llm_fallback = True
            if audit is not None:
                audit.record_exec_llm_phase(
                    i,
                    step,
                    classify_step_risk(step),
                    bool(pre_exec_check.get("ok")),
                    pre_exec_check,
                )
            if not pre_exec_check.get("ok"):
                if audit is not None:
                    audit.set_step_results(results)
                    audit.set_summary(
                        blocked=True,
                        reason="blocked at execution time",
                        execution_result="execution_time_blocked",
                        execution_kind="plan",
                        job_id=last_jid,
                    )
                return (
                    "plan",
                    {
                        "execution_result": "execution_time_blocked",
                        "detail": {
                            "error": "blocked at execution time",
                            "step": step,
                            "check": pre_exec_check,
                        },
                        "step_results": results,
                        "blocked_step": step,
                    },
                    last_jid,
                )
        t = step.get("type")
        if t == "patch":
            rel = str(step.get("file") or "").strip().replace("\\", "/")
            content = str(step.get("content") or "")
            instr = f"TARGET: {rel}\n{content}\n"
            ex = run_direct(instr)
            er = str(ex.get("execution_result") or "")
            ok = er in ("patch_applied", "no_change") or (
                er == "replay_skipped"
                and str(ex.get("detail") or "") == "replay_mode"
            )
            results.append(
                {"type": "patch", "file": rel, "execution_result": er, "ok": ok}
            )
            if not ok:
                if audit is not None:
                    audit.set_step_results(results)
                    audit.set_summary(
                        blocked=True,
                        reason="step_failed",
                        execution_result="step_failed",
                        execution_kind="plan",
                        job_id=last_jid,
                    )
                return (
                    "plan",
                    {
                        "execution_result": "step_failed",
                        "detail": step,
                        "step_results": results,
                        "last_patch": last_patch_ex,
                        "last_instruction_preview": last_instr_preview,
                    },
                    last_jid,
                )
            last_patch_ex = ex
            last_instr_preview = instr[:500]
        elif t == "agent":
            jid = start_agent(str(step.get("goal") or ""), True)
            last_jid = jid
            results.append({"type": "agent", "job_id": jid, "ok": True})
        elif t == "agent_auto":
            if run_agent_auto:
                run_agent_auto(str(step.get("agent_blob") or ""))
            results.append({"type": "agent_auto", "ok": True})
            last_patch_ex = {
                "execution_result": "agent_auto_local",
                "detail": str(step.get("detail") or ""),
            }
        elif t == "log":
            print("[LUMOS LOG]", step.get("message", ""), flush=True)
            results.append({"type": "log", "ok": True})
        else:
            if audit is not None:
                audit.set_step_results(results)
                audit.set_summary(
                    blocked=True,
                    reason="unknown_step",
                    execution_result="unknown_step",
                    execution_kind="plan",
                    job_id=last_jid,
                )
            return (
                "plan",
                {
                    "execution_result": "unknown_step",
                    "detail": str(t),
                    "step_results": results,
                },
                last_jid,
            )

    er = str((last_patch_ex or {}).get("execution_result") or "plan_completed")
    agg: dict[str, Any] = {
        "execution_result": er,
        "detail": plan.get("detail", ""),
        "step_results": results,
        "last_patch": last_patch_ex,
        "last_instruction_preview": last_instr_preview,
    }
    if plan_llm_fallback:
        agg["llm_substep_validation"] = "fallback"
    if execution_llm_fallback:
        agg["execution_llm_check"] = "fallback"
    if audit is not None:
        audit.set_step_results(results)
        audit.set_summary(
            blocked=plan_execution_failed(er),
            reason="",
            execution_result=er,
            execution_kind="plan",
            job_id=last_jid,
        )
    return "plan", agg, last_jid


def execute_plan(
    plan: dict[str, Any],
    *,
    run_direct: Callable[[str], dict[str, Any]],
    start_agent: Callable[[str, bool], str],
    run_agent_auto: Callable[[str], None] | None,
    repo_root: Path | None = None,
    approval_granted: bool = False,
    parent_task: dict[str, Any] | None = None,
    audit: LumosAuditCollector | None = None,
) -> tuple[str, dict[str, Any] | None, str | None]:
    if isinstance(plan.get("steps"), list):
        return _execute_plan_steps(
            plan,
            run_direct=run_direct,
            start_agent=start_agent,
            run_agent_auto=run_agent_auto,
            repo_root=repo_root,
            approval_granted=approval_granted,
            parent_task=parent_task,
            audit=audit,
        )
    return _execute_plan_legacy(
        plan,
        run_direct=run_direct,
        start_agent=start_agent,
        run_agent_auto=run_agent_auto,
        audit=audit,
    )


def verify_result(execution_kind: str, ex: dict[str, Any] | None) -> str:
    if execution_kind == "noop":
        return "skipped_no_execution"
    if execution_kind == "agent":
        return "agent_job_started"
    if execution_kind == "agent_auto":
        return "agent_auto_applied"
    if execution_kind == "plan":
        er = str((ex or {}).get("execution_result") or "")
        return f"executor:{er}"
    if ex is None:
        return "unknown"
    er = str(ex.get("execution_result") or "")
    return f"executor:{er}"


def build_result_payload(
    *,
    ctx: GateContext,
    execution_kind: str,
    ex: dict[str, Any] | None,
    job_id: str | None,
) -> dict[str, Any]:
    if execution_kind == "agent":
        return {
            "accepted": True,
            "mode": "agent",
            "job_id": job_id,
            "lumos_gate": {
                "policy_ok": ctx.policy_ok,
                "reasoning_summary": ctx.reasoning_summary,
                "execution_mode": ctx.execution_mode,
                "verification_summary": ctx.verification_summary,
            },
        }
    if execution_kind == "noop":
        return {
            "accepted": True,
            "mode": "lumos_gate",
            "applied": False,
            "execution": "gate_skipped",
            "lumos_gate": {
                "policy_ok": ctx.policy_ok,
                "reasoning_summary": ctx.reasoning_summary,
                "execution_mode": ctx.execution_mode,
                "generated_content": ctx.generated_content,
                "verification_summary": ctx.verification_summary,
            },
        }
    if execution_kind == "agent_auto":
        return {
            "accepted": True,
            "mode": "lumos_gate",
            "applied": True,
            "execution": "agent_auto",
            "lumos_gate": {
                "policy_ok": ctx.policy_ok,
                "reasoning_summary": ctx.reasoning_summary,
                "verification_summary": ctx.verification_summary,
            },
        }
    if execution_kind == "plan":
        step_results = (ex or {}).get("step_results") or []
        er = str((ex or {}).get("execution_result") or "")
        failed = er in (
            "step_failed",
            "unknown_step",
            "substep_gate_blocked",
            "substep_llm_blocked",
            "execution_time_blocked",
        )
        return {
            "accepted": not failed,
            "mode": "lumos_plan",
            "execution": er,
            "step_results": step_results,
            "job_id": job_id,
            "lumos_gate": {
                "policy_ok": ctx.policy_ok,
                "reasoning_summary": ctx.reasoning_summary,
                "execution_mode": ctx.execution_mode,
                "verification_summary": ctx.verification_summary,
            },
            "outcome": "failed" if failed else "applied",
        }
    outcome = (
        "applied"
        if str((ex or {}).get("execution_result") or "") in ("patch_applied", "no_change")
        else "failed"
    )
    return {
        "accepted": True,
        "mode": "direct_patch",
        "execution": str((ex or {}).get("execution_result") or ""),
        "result_path": "",
        "cursor_bridge_exit": 0,
        "lumos_gate": {
            "policy_ok": ctx.policy_ok,
            "reasoning_summary": ctx.reasoning_summary,
            "execution_mode": ctx.execution_mode,
            "verification_summary": ctx.verification_summary,
        },
        "outcome": outcome,
    }


def run_lumos_gate(
    mode: str | dict[str, Any],
    payload: str = "",
    *,
    repo_root: Path,
    maybe_agent_auto: Callable[[str], None] | None = None,
    parse_agent_file_action: Callable[[str], Any] | None = None,
    approval_granted: bool = False,
    audit: LumosAuditCollector | None = None,
    replay_mode: bool = False,
    chat_user_text: str | None = None,
    ingest_user_message: str | None = None,
    client_requires_clarification: bool = False,
) -> dict[str, Any]:
    """
    Planlama + risk; executor çağrılmaz. Bridge tek kapı: önce bu, sonra lumos_gate_execute.
    Dönüş: gate_complete=True (nihai out) veya _kind=run (çalıştırma paketi).

    Alt adım kapısı: mode sözlüğü ile is_substep=True ve task=<adım> (payload yok sayılır).

    chat_user_text: POST /chat için kullanıcı mesajı; agent modunda normalize sonrası
    file_content_for_reasoning olarak yazılır (dosya yolu mantığına düşmeden).

    ingest_user_message: onay kartı title/raw_text için ham kullanıcı cümlesi (köprü).

    client_requires_clarification: POST /task gövdesinde requires_clarification=True ise;
    görev metni lumos tarafında belirsiz sayılmıyorsa (eylem+nesne / görev yapısı var)
    bu bayrak yok sayılır; aksi halde yürütme yapılmaz, pending_approval + Onaylar akışına düşer.
    """
    if isinstance(mode, dict):
        spec = mode
        if spec.get("is_substep") is True and isinstance(spec.get("task"), dict):
            return run_lumos_gate_substep(
                spec["task"],
                repo_root=repo_root,
                approval_granted=approval_granted,
            )
        raise ValueError(
            "run_lumos_gate: dict girişi yalnızca is_substep=True ve task=<adım> ile kullanılır"
        )

    if audit is not None:
        audit.set_input(str(mode), str(payload or ""))
        audit.set_replay_mode(replay_mode)

    ctx = GateContext()
    ctx.ingress_payload = {"mode": mode, "payload_len": len(payload or "")}
    norm = normalize_request(mode, payload)
    ing = (ingest_user_message or "").strip()
    if ing:
        norm = dict(norm)
        norm["ingest_raw_text"] = ing
        norm["ingest_title"] = ing
    norm = enrich_normalized_with_target_file(norm, repo_root)
    cut = (chat_user_text or "").strip()
    if cut and norm.get("mode") == "agent":
        norm = dict(norm)
        norm["file_read_status"] = "chat_text"
        norm["file_content_for_reasoning"] = cut
    norm = enrich_output_language(norm)
    norm.pop("approval_granted", None)
    ctx.normalized_task = norm.get("target_body") or norm.get("agent_blob") or ""
    ctx.policy_ok = policy_check(norm)
    if not ctx.policy_ok:
        ctx.execution_mode = "rejected_policy"
        out = {
            "http_status": 403,
            "http_body": {
                "accepted": False,
                "error": "policy blocked",
                "decision_kind": "blocked",
            },
            "policy_ok": False,
            "gate_complete": True,
        }
        if audit is not None:
            audit.set_plan({})
            audit.set_step_results([])
            audit.set_summary(
                blocked=True,
                reason="policy blocked",
                execution_result="policy_blocked",
                execution_kind="rejected_policy",
            )
            out["lumos_audit_log"] = audit.to_log_entry()
        return out

    reasoning = reason_task(norm, repo_root, payload)
    ctx.reasoning_summary = str(reasoning.get("summary") or "")

    task_text_risk = merge_text_for_risk_assessment(norm, payload)
    risk = classify_risk(task_text_risk, norm.get("target_rel"))
    if risk == "unknown":
        return {"status": "approved"}

    plan = build_execution_plan(norm, reasoning, mode=mode)

    if (
        mode == "agent"
        and maybe_agent_auto is not None
        and parse_agent_file_action is not None
        and str(reasoning.get("llm_mode") or "") == "agent"
    ):
        hit = parse_agent_file_action(norm.get("agent_blob") or "")
        if hit is not None:
            plan = {
                "steps": [
                    {
                        "type": "agent_auto",
                        "agent_blob": norm.get("agent_blob") or "",
                        "detail": ctx.reasoning_summary,
                    }
                ],
                "detail": ctx.reasoning_summary,
            }

    if risk == "medium":
        if _plan_steps_mutating(plan):
            plan = {
                "steps": [],
                "detail": (
                    (plan.get("detail") or "")
                    + f" | RISK: {risk} → otomatik uygulama kapalı"
                ).strip(" |"),
            }
            rsx = ctx.reasoning_summary
            tag = "MEDIUM RISK → kısıtlı"
            if tag.split()[0] not in rsx:
                ctx.reasoning_summary = f"{rsx} | {tag}".strip(" |")

    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    ctx.execution_mode = "plan" if steps else "noop"
    if reasoning.get("source") == "llm" and reasoning.get("llm_mode") == "direct_patch":
        ctx.generated_content = (reasoning.get("generated_content") or "")[:2000]

    if (
        client_requires_clarification
        and not approval_granted
        and user_intent_text_is_too_vague_for_action(norm, payload)
    ):
        rsx = ctx.reasoning_summary
        tag = "NETLİK GEREKLİ (istemci) → onay / netleştirme"
        if tag not in (rsx or ""):
            ctx.reasoning_summary = f"{rsx} | {tag}".strip(" |")
        out = _return_high_risk_pending(
            ctx, reasoning, mode, payload, norm, plan=plan
        )
        out["policy_ok"] = True
        out["gate_complete"] = True
        par = out.get("pending_approval_record")
        if isinstance(par, dict):
            par["requires_clarification"] = True
            par["risk_level"] = "medium"
        hb = out.get("http_body")
        if isinstance(hb, dict):
            hb["requires_clarification"] = True
            clar_dk = (
                "blocked"
                if risk == "high" or plan_has_high_risk_step(plan)
                else "unclear"
            )
            hb["decision_kind"] = clar_dk
            hb["message"] = (
                "Lumos: görev net değil; kullanıcı onayı veya netleştirme bekleniyor"
            )
            lg = hb.get("lumos_gate")
            if isinstance(lg, dict):
                lg["requires_clarification"] = True
                lg["decision_kind"] = clar_dk
        if audit is not None:
            audit.set_plan(plan)
            audit.set_step_results([])
            audit.set_summary(
                blocked=True,
                reason="pending_approval_requires_clarification",
                execution_result="pending_approval",
                execution_kind="pending_approval",
            )
            out["lumos_audit_log"] = audit.to_log_entry()
        return out

    if (risk == "high" or plan_has_high_risk_step(plan)) and not approval_granted:
        out = _return_high_risk_pending(
            ctx, reasoning, mode, payload, norm, plan=plan
        )
        out["policy_ok"] = True
        out["gate_complete"] = True
        if audit is not None:
            audit.set_plan(plan)
            audit.set_step_results([])
            audit.set_summary(
                blocked=True,
                reason="pending_approval",
                execution_result="pending_approval",
                execution_kind="pending_approval",
            )
            out["lumos_audit_log"] = audit.to_log_entry()
        return out

    if audit is not None:
        audit.set_plan(plan)

    return {
        "_kind": "run",
        "policy_ok": True,
        "gate_complete": False,
        "plan": plan,
        "ctx": ctx,
        "norm": norm,
        "reasoning": reasoning,
        "risk": risk,
        "mode": mode,
        "payload": payload,
        "approval_granted": approval_granted,
        "repo_root": repo_root,
        "audit": audit,
        "replay_mode": replay_mode,
    }


def _build_result_after_execute(
    *,
    plan: dict[str, Any],
    ctx: GateContext,
    norm: dict[str, Any],
    reasoning: dict[str, Any],
    risk: str,
    mode: str,
    payload: str,
    approval_granted: bool,
    kind: str,
    ex: dict[str, Any] | None,
    job_id: str | None,
) -> dict[str, Any]:
    ctx.verification_summary = verify_result(kind, ex)
    http_body = build_result_payload(ctx=ctx, execution_kind=kind, ex=ex, job_id=job_id)
    _inject_risk_fields(
        http_body,
        risk,
        approved_high=bool(approval_granted and risk == "high"),
    )
    # Köprü task_dispatch / UI: kullanıcı görev metni (extract_text_for_dispatch için)
    http_body["normalized_task"] = _jsonable_normalized(norm)

    _dk = lumos_intent_decision_kind(reasoning)
    http_body["decision_kind"] = _dk
    _lg_attach = http_body.get("lumos_gate")
    if isinstance(_lg_attach, dict):
        _lg_attach["decision_kind"] = _dk

    last_ex: dict[str, Any] | None = None
    last_res: dict[str, Any] | None = None

    if kind == "direct_patch" and ex is not None:
        last_ex = ex
        preview = (plan.get("instruction") or "")[:500]
        last_res = {
            "schema_version": "kando.cursor.result.v1",
            "goal_preview": preview,
            "outcome": http_body.get("outcome", "failed"),
            "reason": str(ex.get("detail") or ""),
            "verification_summary": ctx.verification_summary,
            "task_id": 0,
            "task_status": "",
            "brain_success": True,
            "verified_count": 0,
            "unverified_count": 0,
            "simulation_count": 0,
            "execution": ex,
            "lumos_gate": {
                "reasoning_source": reasoning.get("source"),
                "reasoning_summary": ctx.reasoning_summary,
                "policy_ok": ctx.policy_ok,
            },
        }
    elif kind == "noop":
        last_ex = {
            "execution_result": "gate_skipped",
            "detail": plan.get("detail", ""),
            "lumos_gate": {
                "reasoning_source": reasoning.get("source"),
                "reasoning_summary": ctx.reasoning_summary,
                "policy_ok": ctx.policy_ok,
            },
        }
        last_res = {
            "schema_version": "kando.cursor.result.v1",
            "goal_preview": "",
            "outcome": "not_applied",
            "reason": str(plan.get("detail") or ""),
            "verification_summary": ctx.verification_summary,
            "task_id": 0,
            "task_status": "",
            "brain_success": True,
            "verified_count": 0,
            "unverified_count": 0,
            "simulation_count": 0,
            "execution": last_ex,
            "lumos_gate": {
                "reasoning_source": reasoning.get("source"),
                "reasoning_summary": ctx.reasoning_summary,
                "policy_ok": ctx.policy_ok,
            },
        }
    elif kind == "agent_auto" and ex is not None:
        last_ex = ex
        last_res = {
            "schema_version": "kando.cursor.result.v1",
            "goal_preview": (norm.get("agent_blob") or "")[:500],
            "outcome": "applied",
            "reason": ctx.reasoning_summary,
            "verification_summary": ctx.verification_summary,
            "task_id": 0,
            "task_status": "",
            "brain_success": True,
            "verified_count": 0,
            "unverified_count": 0,
            "simulation_count": 0,
            "execution": ex,
            "lumos_gate": {
                "reasoning_source": reasoning.get("source"),
                "reasoning_summary": ctx.reasoning_summary,
                "policy_ok": ctx.policy_ok,
            },
        }
    elif kind == "plan" and ex is not None:
        last_patch = ex.get("last_patch")
        preview = str(ex.get("last_instruction_preview") or "")[:500]
        if last_patch is not None:
            last_ex = last_patch
            last_res = {
                "schema_version": "kando.cursor.result.v1",
                "goal_preview": preview,
                "outcome": http_body.get("outcome", "failed"),
                "reason": str(last_patch.get("detail") or ""),
                "verification_summary": ctx.verification_summary,
                "task_id": 0,
                "task_status": "",
                "brain_success": True,
                "verified_count": 0,
                "unverified_count": 0,
                "simulation_count": 0,
                "execution": last_patch,
                "lumos_gate": {
                    "reasoning_source": reasoning.get("source"),
                    "reasoning_summary": ctx.reasoning_summary,
                    "policy_ok": ctx.policy_ok,
                },
            }
        else:
            last_ex = {
                "execution_result": str(ex.get("execution_result") or ""),
                "detail": ex.get("detail"),
                "step_results": ex.get("step_results") or [],
                "lumos_gate": {
                    "reasoning_source": reasoning.get("source"),
                    "reasoning_summary": ctx.reasoning_summary,
                    "policy_ok": ctx.policy_ok,
                },
            }
            last_res = {
                "schema_version": "kando.cursor.result.v1",
                "goal_preview": preview,
                "outcome": http_body.get("outcome", "failed"),
                "reason": str(ex.get("detail") or ""),
                "verification_summary": ctx.verification_summary,
                "task_id": 0,
                "task_status": "",
                "brain_success": True,
                "verified_count": 0,
                "unverified_count": 0,
                "simulation_count": 0,
                "execution": last_ex,
                "lumos_gate": {
                    "reasoning_source": reasoning.get("source"),
                    "reasoning_summary": ctx.reasoning_summary,
                    "policy_ok": ctx.policy_ok,
                },
            }

    gate_m = _risk_gate_execution_mode(risk)
    if approval_granted and risk == "high":
        gate_m = f"approved:{ctx.execution_mode or 'execution'}"
    if isinstance(last_ex, dict) and isinstance(last_ex.get("lumos_gate"), dict):
        last_ex["lumos_gate"]["risk_level"] = risk
        last_ex["lumos_gate"]["risk_execution_mode"] = gate_m
    if isinstance(last_res, dict) and isinstance(last_res.get("lumos_gate"), dict):
        last_res["lumos_gate"]["risk_level"] = risk
        last_res["lumos_gate"]["risk_execution_mode"] = gate_m

    if (
        not approval_granted
        and isinstance(http_body, dict)
        and http_body.get("risk_level") == "high"
    ):
        return _return_high_risk_pending(
            ctx, reasoning, mode, payload, norm, plan=plan
        )

    return _handle_task_return(
        http_body=http_body,
        last_ex=last_ex,
        last_res=last_res,
        risk=risk,
        approval_granted=approval_granted,
    )


def validate_pending_for_approval(loaded: dict[str, Any]) -> None:
    """Onay öncesi: policy_ok + pending + kayıtlı plan (gate tekrar yok)."""
    if loaded.get("schema_version") != "lumos.pending_approval.v1":
        raise ValueError("geçersiz pending şeması")
    if loaded.get("final_decision") != "await_user_approval":
        raise ValueError("onay bekleyen kayıt değil")
    if loaded.get("policy_ok") is not True:
        raise ValueError("policy_ok gerekli")
    if loaded.get("risk_level") != "high":
        raise ValueError("yalnızca high-risk pending onayı")
    if loaded.get("execution_mode") != "pending_approval":
        raise ValueError("beklenen pending_approval kaydı değil")
    plan = loaded.get("execution_plan")
    if not isinstance(plan, dict):
        raise ValueError("execution_plan eksik veya geçersiz")
    steps = plan.get("steps")
    if isinstance(steps, list) and len(steps) > 0:
        pass
    elif str(plan.get("action") or "").strip():
        pass
    else:
        raise ValueError("execution_plan.steps gerekli (veya eski action)")
    if not isinstance(loaded.get("reasoning_snapshot"), dict):
        raise ValueError("reasoning_snapshot eksik")
    if not isinstance(loaded.get("normalized_task"), dict):
        raise ValueError("normalized_task eksik")


def execute_approved_pending_record(
    loaded: dict[str, Any],
    *,
    run_direct: Callable[[str], dict[str, Any]],
    start_agent: Callable[[str, bool], str],
    run_agent_auto: Callable[[str], None] | None = None,
    repo_root: Path | None = None,
    audit: LumosAuditCollector | None = None,
) -> dict[str, Any]:
    """
    Gate tekrar çalışmaz: yalnızca kayıtlı execution_plan + snapshot ile execute_plan.
    """
    validate_pending_for_approval(loaded)
    rr = repo_root if repo_root is not None else Path.cwd()
    plan = loaded["execution_plan"]
    reasoning = loaded["reasoning_snapshot"]
    norm = loaded["normalized_task"]
    mode = str(loaded.get("mode") or "")
    payload = str(loaded.get("original_payload") or "")

    ctx = GateContext()
    ctx.policy_ok = True
    ctx.reasoning_summary = str(loaded.get("reasoning_summary") or "")
    _steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    ctx.execution_mode = "plan" if _steps else str(plan.get("action") or "noop")
    ctx.generated_content = None
    if reasoning.get("source") == "llm" and reasoning.get("llm_mode") == "direct_patch":
        ctx.generated_content = (str(reasoning.get("generated_content") or ""))[:2000]

    parent_task = build_parent_task_context(
        mode=mode,
        payload=payload,
        norm=norm,
        reasoning=reasoning,
        reasoning_summary=ctx.reasoning_summary,
    )
    kind, ex, job_id = execute_plan(
        plan,
        run_direct=run_direct,
        start_agent=start_agent,
        run_agent_auto=run_agent_auto,
        repo_root=rr,
        approval_granted=True,
        parent_task=parent_task,
        audit=audit,
    )
    result = _build_result_after_execute(
        plan=plan,
        ctx=ctx,
        norm=norm,
        reasoning=reasoning,
        risk="high",
        mode=mode,
        payload=payload,
        approval_granted=True,
        kind=kind,
        ex=ex,
        job_id=job_id,
    )
    if audit is not None:
        if kind != "plan":
            _audit_finalize_non_plan(audit, kind, ex, job_id, plan)
        result["lumos_audit_log"] = audit.to_log_entry()
    return result


def lumos_gate_execute(
    bundle: dict[str, Any],
    *,
    run_direct: Callable[[str], dict[str, Any]],
    start_agent: Callable[[str, bool], str],
    run_agent_auto: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Yalnızca run_lumos_gate _kind=run paketi ile çağrılır; executor burada tetiklenir."""
    if bundle.get("_kind") != "run":
        raise ValueError("lumos_gate_execute: beklenen _kind=run paketi değil")
    plan = bundle["plan"]
    ctx = bundle["ctx"]
    norm = bundle["norm"]
    reasoning = bundle["reasoning"]
    risk = bundle["risk"]
    mode = bundle["mode"]
    payload = bundle["payload"]
    approval_granted = bool(bundle.get("approval_granted"))
    rr = bundle.get("repo_root")
    if rr is None:
        rr = Path.cwd()
    elif not isinstance(rr, Path):
        rr = Path(str(rr))
    audit = bundle.get("audit")
    replay_mode = bool(bundle.get("replay_mode"))

    if risk == "high" and not approval_granted:
        out = _return_high_risk_pending(
            ctx, reasoning, mode, payload, norm, plan=plan
        )
        if audit is not None:
            audit.set_plan(plan)
            audit.set_step_results([])
            audit.set_summary(
                blocked=True,
                reason="pending_approval",
                execution_result="pending_approval",
                execution_kind="pending_approval",
            )
            out["lumos_audit_log"] = audit.to_log_entry()
        return out

    parent_task = build_parent_task_context(
        mode=mode,
        payload=payload,
        norm=norm,
        reasoning=reasoning,
        reasoning_summary=ctx.reasoning_summary,
    )
    rd = run_direct
    sa = start_agent
    raa = run_agent_auto
    if replay_mode:
        def rd(instr: str) -> dict[str, Any]:
            return {"execution_result": "replay_skipped", "detail": "replay_mode"}

        def sa(goal: str, auto: bool) -> str:
            return "replay_skipped_job"

        raa = None

    kind, ex, job_id = execute_plan(
        plan,
        run_direct=rd,
        start_agent=sa,
        run_agent_auto=raa,
        repo_root=rr,
        approval_granted=approval_granted,
        parent_task=parent_task,
        audit=audit if isinstance(audit, LumosAuditCollector) else None,
    )
    if risk == "high" and not approval_granted:
        return _return_high_risk_pending(
            ctx, reasoning, mode, payload, norm, plan=plan
        )

    result = _build_result_after_execute(
        plan=plan,
        ctx=ctx,
        norm=norm,
        reasoning=reasoning,
        risk=risk,
        mode=mode,
        payload=payload,
        approval_granted=approval_granted,
        kind=kind,
        ex=ex,
        job_id=job_id,
    )
    if audit is not None:
        if kind != "plan":
            _audit_finalize_non_plan(audit, kind, ex, job_id, plan)
        result["lumos_audit_log"] = audit.to_log_entry()
    return result


def replay_lumos_task(
    log_entry: dict[str, Any],
    *,
    repo_root: Path,
    maybe_agent_auto: Callable[[str], None] | None = None,
    parse_agent_file_action: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Kayıtlı input ile gate+doğrulamayı tekrar çalıştırır; executor replay_mode ile devre dışı."""
    inp = log_entry.get("input") or {}
    mode = str(inp.get("mode") or "direct_patch")
    payload = str(inp.get("payload") or "")
    base_id = str(log_entry.get("log_id") or "unknown")
    audit = LumosAuditCollector(log_id=f"{base_id}_replay")
    audit.set_replay_mode(True)
    gate_result = run_lumos_gate(
        mode,
        payload,
        repo_root=repo_root,
        maybe_agent_auto=maybe_agent_auto,
        parse_agent_file_action=parse_agent_file_action,
        approval_granted=False,
        audit=audit,
        replay_mode=True,
    )
    if gate_result.get("_kind") != "run":
        new_entry = gate_result.get("lumos_audit_log") or audit.to_log_entry()
        match, diffs = compare_audit_entries(log_entry, new_entry, dry_run=True)
        return {
            "replay": True,
            "match": match,
            "differences": diffs,
            "new_log": new_entry,
        }

    def _noop_rd(instr: str) -> dict[str, Any]:
        return {"execution_result": "replay_skipped", "detail": "replay_mode"}

    def _noop_sa(goal: str, auto: bool) -> str:
        return "replay_skipped_job"

    out = lumos_gate_execute(
        gate_result,
        run_direct=_noop_rd,
        start_agent=_noop_sa,
        run_agent_auto=None,
    )
    new_entry = out.get("lumos_audit_log") or audit.to_log_entry()
    match, diffs = compare_audit_entries(log_entry, new_entry, dry_run=True)
    return {
        "replay": True,
        "match": match,
        "differences": diffs,
        "new_log": new_entry,
    }


def handle_task(
    mode: str,
    payload: str,
    *,
    repo_root: Path,
    run_direct: Callable[[str], dict[str, Any]],
    start_agent: Callable[[str, bool], str],
    maybe_agent_auto: Callable[[str], None] | None = None,
    parse_agent_file_action: Callable[[str], Any] | None = None,
    approval_granted: bool = False,
) -> dict[str, Any]:
    audit = LumosAuditCollector()
    gate_result = run_lumos_gate(
        mode,
        payload,
        repo_root=repo_root,
        maybe_agent_auto=maybe_agent_auto,
        parse_agent_file_action=parse_agent_file_action,
        approval_granted=approval_granted,
        audit=audit,
        replay_mode=False,
    )
    if gate_result.get("_kind") != "run":
        return gate_result
    return lumos_gate_execute(
        gate_result,
        run_direct=run_direct,
        start_agent=start_agent,
        run_agent_auto=maybe_agent_auto,
    )
