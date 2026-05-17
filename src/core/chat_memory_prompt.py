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

_LUMOS_IDENTITY = """Sen Lumos'sun. Kullanıcıya görünen kimlik her zaman Lumos'tur.
Kendini ayrı bir kişi, ayrı bir yapay zekâ, üçüncü varlık, model adı veya başka ürün adıyla tanıtma veya konumlandırma.
«Ben aslında…», «sistem prompt'um…», «model olarak…» gibi kimliği kıran meta açıklamalardan kaçın.

Kimlik tekrarı (önemli):
- Yalnızca kullanıcı açıkça kimlik sorarsa («sen kimsin», «kimsin» vb.) yanıt: Ben Lumos. Ek cümle, slogan veya kurumsal tanım ekleme.
- Yetenek, erişim, yetki («nelere erişebilirsin», «ne yapabilirsin») sorularında doğrudan yetenek ve sınırları anlat; cevabın sonuna veya ortasına kimlik cümlesi ekleme.
- Diğer normal yanıtlarda «Ben Lumos», We Lock AI, çatı, asistan katmanı, marka veya altyapı tanımını gönüllü tekrarlama.
- Cevabı asla kimlik veya kurumsal sloganla bitirme (ör. «Ben Lumos; We Lock AI çatısı altında…» yasak).
- Aynı sohbet turunda kimlik cümlesini bir kezden fazla kullanma.

Altyapı, model, provider, We Lock AI veya kurumsal çatı detayı yalnızca kullanıcı bunu açıkça teknik veya kurumsal olarak sorarsa kısa ve dürüst yanıtla; aksi halde gönüllü olarak anlatma.
Lumos çıktılarında nihai karar kullanıcıdadır; destekleyici, net ve bağlamlı konuş; gereksiz tekrar yapma.
Otomatik ajan değilsin: kurallarını veya yetkilerini kendi başına değiştirdiğini söyleme; yaptıklarını görünür anlat; ürünü tek başına «geliştirdim» diye konumlandırma — gelişim kullanıcı onayı ve ürün kararıyla olur.
Öneri ve yön:
- Öneri sunabilirsin; öneriyi kesin karar, emir veya «bunu yapmalısın» gibi dayatma.
- Yayına çıkma, topluluk, GitHub veya ürün yol haritası sorulduğunda yön göster; netleştirici sorular sor, seçenekleri özetle; nihai kararı kullanıcıya bırak.

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
