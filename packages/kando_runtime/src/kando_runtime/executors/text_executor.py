from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LLM_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))

Intent = dict[str, str]

# Kanonik anahtar → eş anlamlı / yazım varyantları (base; kodla birlikte gelir).
SYNONYMS: dict[str, list[str]] = {
    "absurt": ["absürt", "absurd"],
    "kısa": ["kisa", "kısaca", "kisaca"],
    "fıkra": ["fikra"],
}

# Runtime / config / test ile genişletilir; SYNONYMS ile birleştirilir.
RUNTIME_SYNONYMS: dict[str, list[str]] = {}

_SYNONYMS_JSON_ENV = "LUMOS_TEXT_SYNONYMS_JSON"


def _normalize_synonym_token(s: object) -> str | None:
    """Strip + lower; boş kalırsa None (tabloya eklenmez)."""
    if s is None:
        return None
    t = str(s).strip().lower()
    return t if t else None


def _validate_synonym_entry(
    key: object,
    value: object,
    *,
    source: str = "",
) -> tuple[str, list[str]] | None:
    """Geçerli ve normalize edilmiş tek grup döndürür; değilse None + log."""
    prefix = f"{source}: " if source else ""
    canon = _normalize_synonym_token(key)
    if canon is None:
        logger.warning(
            "%ssynonyms ignored — empty key after normalize: %r",
            prefix,
            key,
        )
        return None
    if not isinstance(value, list):
        logger.warning(
            "%ssynonyms ignored — key %r: value must be list, got %s",
            prefix,
            key,
            type(value).__name__,
        )
        return None

    variants: list[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            logger.warning(
                "%ssynonyms ignored — key %r index %s: value must be str, got %s",
                prefix,
                key,
                i,
                type(item).__name__,
            )
            continue
        n = _normalize_synonym_token(item)
        if n is None:
            logger.warning(
                "%ssynonyms ignored — key %r index %s: empty after normalize",
                prefix,
                key,
                i,
            )
            continue
        if n == canon:
            continue
        variants.append(n)

    return canon, variants


def _coerce_synonym_map(
    raw: dict[str, Any],
    *,
    source: str = "",
) -> dict[str, list[str]]:
    """Yüklenen dict'i doğrula; sadece normalize edilmiş geçerli girdileri döndür."""
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        parsed = _validate_synonym_entry(k, v, source=source)
        if parsed is None:
            continue
        canon, variants = parsed
        if canon not in out:
            out[canon] = []
        seen = set(out[canon])
        for x in variants:
            if x not in seen:
                out[canon].append(x)
                seen.add(x)
    return out


def _merge_synonym_maps(
    *maps: dict[str, list[str]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in maps:
        for canon, variants in m.items():
            if canon not in out:
                out[canon] = []
            seen = set(out[canon])
            for v in variants:
                if v not in seen:
                    out[canon].append(v)
                    seen.add(v)
    return out


def _flatten_to_canon(merged: dict[str, list[str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canon, variants in merged.items():
        c = _normalize_synonym_token(canon)
        if c is None:
            continue
        lookup[c] = c
        for v in variants:
            t = _normalize_synonym_token(v)
            if t:
                lookup[t] = c
    return lookup


_synonym_lookup_cache: dict[str, str] | None = None


def _effective_synonym_maps() -> dict[str, list[str]]:
    return _merge_synonym_maps(
        _coerce_synonym_map(SYNONYMS, source="SYNONYMS"),
        RUNTIME_SYNONYMS,
    )


def _rebuild_synonym_lookup() -> dict[str, str]:
    global _synonym_lookup_cache
    _synonym_lookup_cache = _flatten_to_canon(_effective_synonym_maps())
    return _synonym_lookup_cache


def get_synonym_lookup() -> dict[str, str]:
    if _synonym_lookup_cache is None:
        _rebuild_synonym_lookup()
    return dict(_synonym_lookup_cache or {})


def register_runtime_synonyms(extra: dict[str, list[str]]) -> None:
    global RUNTIME_SYNONYMS
    coerced = _coerce_synonym_map(dict(extra), source="register_runtime_synonyms")
    RUNTIME_SYNONYMS = _merge_synonym_maps(RUNTIME_SYNONYMS, coerced)
    _rebuild_synonym_lookup()


def load_synonyms_from_json(path: str | Path) -> dict[str, list[str]]:
    """JSON'dan synonym haritası yükle; geçersiz girdiler atlanır ve loglanır."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        logger.warning(
            "synonyms ignored — %s: root must be object, got %s",
            p,
            type(raw).__name__,
        )
        return {}
    return _coerce_synonym_map(raw, source=str(p))


def load_synonyms_from_json_file(path: str | Path | None = None) -> None:
    env_path = (path or os.getenv(_SYNONYMS_JSON_ENV) or "").strip()
    if not env_path:
        return
    extra = load_synonyms_from_json(env_path)
    if extra:
        register_runtime_synonyms(extra)


def _normalize_word(w: str, lookup: dict[str, str]) -> str:
    t = w.strip(".,!?;:()[]\"'")
    if not t:
        return ""
    low = t.lower()
    return lookup.get(low, low)


def _parse_intent(prompt: str) -> Intent:
    lookup = _synonym_lookup_cache or _rebuild_synonym_lookup()
    pl = (prompt or "").strip().lower()
    raw_words = [w for w in pl.split() if w.strip(".,!?;:()[]\"'")]
    words = [_normalize_word(w, lookup) for w in raw_words]
    words = [w for w in words if w]

    length: str = "short" if "kısa" in words else "long"
    style: str = "absürt" if "absurt" in words else "normal"
    typ: str = "fıkra" if (len(words) == 1 and words[0] == "fıkra") else "text"

    return {
        "length": length,
        "style": style,
        "type": typ,
    }


def _format_rules(intent: Intent) -> list[str]:
    rules: list[str] = []
    if intent["length"] == "short":
        rules.append("Çıktıyı kısa tut: az cümle, gereksiz söz kalabalığı yok.")
    if intent["style"] == "absürt":
        rules.append(
            "Üslup absürt olsun: beklenmedik, abartılı mizah; düz kurumsal ton kullanma."
        )
    if intent["type"] == "fıkra":
        rules.append("Sadece bir fıkra üret; en fazla 2-3 satır; daha uzun yazma.")
    return rules


def _build_system_layer(intent: Intent) -> str:
    base = (
        "Sen Lumos metin asistanısın. Yanıtın Türkçe olsun ve kullanıcı isteğine uygun olsun."
    )
    lines = _format_rules(intent)
    if not lines:
        return base
    return base + "\n\nAşağıdaki biçim kurallarına uy:\n" + "\n".join(
        f"- {x}" for x in lines
    )


def _post_enforce(value: str, intent: Intent) -> str:
    out = (value or "").strip()
    if intent["type"] == "fıkra":
        nonempty = [ln for ln in out.splitlines() if ln.strip()]
        if len(nonempty) > 3:
            return "\n".join(nonempty[:3])
    if intent["length"] == "short" and len(out) > 800:
        return out[:800].rstrip() + "…"
    return out


def _call_openai_text(system: str, user: str) -> str | None:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return None
    model = (os.getenv("OPENAI_MODEL") or "").strip() or "gpt-4.1-mini"
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                timeout=_LLM_TIMEOUT,
            )
        except TypeError:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None


def _fallback_value(prompt: str, intent: Intent) -> str:
    tags: list[str] = []
    if intent["length"] == "short":
        tags.append("kısa")
    if intent["style"] == "absürt":
        tags.append("absürt")
    if intent["type"] == "fıkra":
        tags.append("fıkra≤3satır")
    prefix = f"[{'|'.join(tags)}] " if tags else ""
    return f"[Lumos cevap] {prefix}{prompt[:200]}"


def run(task_ctx: dict[str, Any]) -> dict[str, Any]:
    prompt = str(task_ctx.get("prompt", ""))
    intent = _parse_intent(prompt)
    if intent.get("type") == "fıkra" or intent.get("style") == "absürt":
        return {
            "status": "done",
            "output": {
                "type": "route",
                "target": "agent",
                "task": {
                    "type": "text.agent",
                    "prompt": prompt,
                },
            },
        }
    system = _build_system_layer(intent)
    text = _call_openai_text(system, prompt)
    if text is None:
        text = _fallback_value(prompt, intent)
    text = _post_enforce(text, intent)
    return {
        "status": "done",
        "output": {
            "type": "text",
            "value": text,
        },
    }


_rebuild_synonym_lookup()
load_synonyms_from_json_file()
