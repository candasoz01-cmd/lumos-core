"""
Lumos /chat LLM girdisinin başına eklenen kısa kimlik + kullanıcı bağlamı.

Veri kaynağı (basit):
- {repo_root}/.lumos/user_memory.json — serbest metin veya yapılandırılmış alanlar
- {repo_root}/.lumos/user_preferences.json — isteğe bağlı: display_name, locale, notlar

Dosya yoksa veya okunamazsa yalnızca kimlik bloğu döner.
"""
from __future__ import annotations

import json
from pathlib import Path

_MAX_MEMORY_CHARS = 2500

_LUMOS_IDENTITY = """Sen Lumos'sun; kendini kullanıcıya Lumos olarak tanıt (bir kez, gerektiğinde kısaca).
Kullanıcıya yardımcı ol, net ve bağlamlı konuş; gereksiz tekrar yapma.

Belirsiz istek: Ana nesne, sahne, çıktı türü veya amaç net değilse varsayım yapma, iş planı önerme veya tek başına ilerleme.
Önce tek cümlelik, kısa bir netleştirme sorusu sor (ör. ne üretileceği, video mu metin mi, hangi bağlam).
Yanıtı gereksiz onay dolgularıyla başlatma: «Tamam.», «Anladım.» gibi girişler kullanma; doğrudan soruyu veya net içeriği yaz.
İstek açıksa kısa ve doğrudan cevap ver; dolgu cümlesi ekleme.
Video görevinde kullanıcı YouTube, yerel dosya veya URL/API kaynağı belirtmediyse: «video gönderiyorum», «hemen izleyebilirsin», «öneriyorum» gibi ifadeler kullanma; önce kaynak veya üretim tercihini netleştir."""


def _trim(s: str, max_chars: int) -> str:
    t = (s or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def _load_json_dict(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _memory_lines_from_obj(obj: dict) -> list[str]:
    lines: list[str] = []
    if not obj:
        return lines
    for key in ("text", "about", "about_user", "context", "notes", "memory"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            lines.append(v.strip())
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    lines.append(item.strip())
    return lines


def format_chat_prompt_prefix(repo_root: Path | str | None) -> str:
    """
    Sohbet LLM metninin başına eklenecek tek blok (kimlik + kullanıcı özeti).
    repo_root: Lumos çalışma kökü (.lumos buranın altında).
    """
    base = Path(repo_root) if repo_root else Path(".")
    lumos = base / ".lumos"

    parts: list[str] = [_LUMOS_IDENTITY.strip(), ""]

    prefs = _load_json_dict(lumos / "user_preferences.json")
    if prefs:
        name = prefs.get("display_name") or prefs.get("name")
        if isinstance(name, str) and name.strip():
            parts.append(f"Kullanıcı adı / tercih edilen hitap: {name.strip()}")
        loc = prefs.get("locale") or prefs.get("language")
        if isinstance(loc, str) and loc.strip():
            parts.append(f"Tercih edilen dil/locale: {loc.strip()}")
        extra = prefs.get("summary") or prefs.get("bio")
        if isinstance(extra, str) and extra.strip():
            parts.append(f"Kullanıcı özeti: {_trim(extra, 800)}")

    mem_obj = _load_json_dict(lumos / "user_memory.json")
    mem_lines = _memory_lines_from_obj(mem_obj) if mem_obj else []
    if mem_lines:
        body = "\n".join(mem_lines)
        parts.append("Kullanıcı hakkında hatırlananlar:")
        parts.append(_trim(body, _MAX_MEMORY_CHARS))

    return "\n".join(parts).strip() + "\n\n---\n\n"
