"""CLI help text, argument parsing, and command dispatch for Lumos core.

Extracted from main.py for stabilization: no behavior change, no new dependencies.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from core.startup_health import get_durum_parts
from security.aliases import apply_alias


def norm_cmd(s: str) -> str:
    s = (s or "").strip().casefold()
    aliases = {
        "quit": "cik",
        "exit": "cik",
        "çık": "cik",
        "cık": "cik",
        "kilitle": "kapat",
        "lock": "kapat",
        "unlock": "ac",
        "aç": "ac",
    }
    return aliases.get(s, s)


# Canonical CLI: exit synonyms (q, çık, cik, quit -> exit)
EXIT_SYNONYMS = frozenset({"exit", "quit", "çık", "cik", "çik", "q"})

# Yardım: gruplu, kısa; help / yardım / yardım et hepsi aynı çıktıyı kullanır
HELP_TEXT = """Temel
  durum, hazır, ne yapıyorsun, son yaptığın ne, bugün ne yaptın, bana ne önerirsin, bir sonraki adım ne, en önemli eksik ne, neden böyle diyorsun, bunu kısaca anlat, kilit, kamera, alias, self test, hangi moddayım, şu an güvenli miyim, exit, yardım kısa, yardım temel, yardım etiketler, yardım notlar, yardım not işlemleri, yardım görüntüleme, yardım güvenlik, yardım arama

Görev motoru
  görev oluştur <metin>, görevler, görev kuyruk, görev durumu <id>, görev özeti <id>, görev adımları <id>, görev iptal <id>, yetki profili, yetki profili <rapor|guvenli_yurut|kisitli_otonom>, genel onay aç, genel onay kapat

Notlar
  bunu hatırla, son not ne, notları göster, kaç not var, notu sil, notları temizle, notu düzenle, notu kopyala, notu dışa aktar, notu paylaş, not özetle, not birleştir, notu geri al, not geçmişi, not ara <kelime>

Etiketler
  notu adlandır <etiket>, etiketleri göster, etiket ara <kelime>, etiket kaldır <etiket>, etiket değiştir <eski> <yeni>, etiketli notları göster, etiketli not ara <kelime>, etikete göre notları göster <etiket>"""

HELP_ETIKETLER_TEXT = """Etiketler
  notu adlandır <etiket>, etiketleri göster, etiket ara <kelime>, etiket kaldır <etiket>, etiket değiştir <eski> <yeni>, etiketli notları göster, etiketli not ara <kelime>, etikete göre notları göster <etiket>"""

HELP_NOTLAR_TEXT = """Notlar
  bunu hatırla, son not ne, notları göster, kaç not var, notu sil, notları temizle, notu düzenle, notu kopyala, notu dışa aktar, notu paylaş, not özetle, not birleştir, notu geri al, not geçmişi, not ara <kelime>"""

HELP_NOT_ISLEMLERI_TEXT = """Not işlemleri:
  bunu hatırla, notu düzenle, notu sil, notları temizle, notu kopyala, notu dışa aktar, notu paylaş, not özetle, not birleştir, notu geri al"""

HELP_TEMEL_TEXT = """Temel
  durum, hazır, hazır mıyım, ne yapıyorsun, son yaptığın ne, bugün ne yaptın, bana ne önerirsin, bir sonraki adım ne, hangi moddayım, şu an güvenli miyim, neden böyle diyorsun, bunu kısaca anlat, bunu hatırla"""

HELP_GUVENLIK_TEXT = """Güvenlik
  durum, hazır, hazır mıyım, hangi moddayım, şu an güvenli miyim, neden böyle diyorsun"""

HELP_ARAMA_TEXT = """Arama:
  not ara <kelime>, etiket ara <kelime>, etiketli not ara <kelime>, etikete göre notları göster <etiket>"""

HELP_GORUNTULEME_TEXT = """Görüntüleme:
  durum, hazır, hazır mıyım, hangi moddayım, şu an güvenli miyim, son not ne, kaç not var, notları göster, etiketli notları göster, etiketleri göster, not geçmişi"""

HELP_KISA_TEXT = "Kısa yardım: yardım temel | yardım güvenlik | yardım notlar | yardım not işlemleri | yardım görüntüleme | yardım etiketler | yardım arama\nGenel liste için: help"

REHBER_TEXT = HELP_TEXT

UNKNOWN_CMD_TEXT = 'Bunu anlamadım. "durum", "hazir" veya "yardım et" deneyebilirsin.'

NEDEN_ANLAMADIN_TEXT = (
    "Yazdığın ifade kayıtlı komutlara yeterince yakın değildi, bu yüzden güvenli tarafta kalıp işlem yapmadım.\n"
    "Örnek: görev durumu 2 | görev özeti 1 | yetki profili rapor | yardım"
)

NEUTRAL_FALLBACK_TEXT = (
    "Bunu kayıtlı komutlara yeterince yakın bulmadım, bu yüzden işlem yapmadım.\n"
    "Örnek: durum | görevler | görev durumu <id> | görev özeti <id> | yetki profili | yardım"
)

COMMAND_ANCHOR_WORDS = frozenset({"gorev", "yetki", "not", "notlar", "durum", "hazir", "genel"})
CASUAL_FIRST_WORDS = frozenset({
    "saat", "tamam", "oldu", "neden", "napiyoruz", "napiyon", "ben", "cikti", "sanirim", "bakalim",
    "tarih", "zaman", "ne", "evet", "hayir", "oldumu",
})

FALLBACK_BY_FAMILY = {
    "gorev": 'Görev ailesine yakınsın. Örnek: görevler | görev durumu <id> | görev özeti <id>',
    "yetki": 'Yetki ailesine yakınsın. Örnek: yetki profili | yetki profili rapor',
    "not": 'Not ailesine yakınsın. Örnek: notları göster | not ara <kelime> | yardım notlar',
    "durum": 'Durum/temel ailesine yakınsın. Örnek: durum | hazır | yardım temel',
}

KISACA_ANLAT_SHORT_THRESHOLD = 90
HATIRLA_NOTE_MAX_LEN = 150
NOT_OZETLE_SHORT_THRESHOLD = 100
NOT_ADLANDIR_MAX_TAG_LEN = 24

GOREV_SECOND_TOKEN_TOLERANCE = {"durmu": "durumu", "ozti": "ozeti"}
YETKI_PROFIL_TOLERANCE = ("profili", "profil")


def _fold_for_search(s: str) -> str:
    """Büyük/küçük harf ve Türkçe karakter farkını tolere etmek için metni katla."""
    s = (s or "").strip().casefold()
    return (
        s.replace("\u0131", "i").replace("İ", "i")
        .replace("ö", "o").replace("ü", "u")
        .replace("ş", "s").replace("ğ", "g").replace("ç", "c")
    )


def _is_why_question(raw: str) -> bool:
    q = _fold_for_search((raw or "").strip())
    return q in ("neden anlamadin", "neyi anlamadin", "neye takildin")


def _first_token_folded(raw: str) -> str:
    q = _fold_for_search((raw or "").strip())
    parts = q.split()
    return parts[0] if parts else ""


def _has_anchor(raw: str) -> bool:
    return _first_token_folded(raw) in COMMAND_ANCHOR_WORDS


def _is_casual_or_indeterminate(raw: str) -> bool:
    first = _first_token_folded(raw)
    if first in CASUAL_FIRST_WORDS:
        return True
    q = _fold_for_search((raw or "").strip())
    if first == "sanirim" or first == "bakalim" or (len(q) > 25 and first in ("ne", "ben", "evet", "hayir")):
        return True
    return False


def _infer_family_from_raw(raw: str) -> str | None:
    first = _first_token_folded(raw)
    q = _fold_for_search((raw or "").strip())
    if first == "gorev":
        return "gorev"
    if first == "yetki":
        return "yetki"
    if first in ("not", "notlar") and ("goster" in q or "ara" in q or "hatirla" in q or "etiket" in q):
        return "not"
    if first in ("durum", "hazir"):
        return "durum"
    if first == "genel" and "onay" in q:
        return "durum"
    return None


def _route_to_family(route: str) -> str | None:
    if not route:
        return None
    if route.startswith("gorev") or route == "gorevler":
        return "gorev"
    if route.startswith("yetki"):
        return "yetki"
    if route.startswith("not") or "not" in route or route in ("hatirla", "son_not_ne", "etiketli_not", "etiket_ara"):
        return "not"
    if route in ("durum", "hazir", "rehber", "help"):
        return "durum"
    return None


def get_fallback_message(raw: str, last_route: str | None) -> str:
    if _is_why_question(raw):
        return NEDEN_ANLAMADIN_TEXT
    if _is_casual_or_indeterminate(raw):
        return NEUTRAL_FALLBACK_TEXT
    if not _has_anchor(raw):
        return NEUTRAL_FALLBACK_TEXT
    family = _infer_family_from_raw(raw) or _route_to_family(last_route or "")
    if family and family in FALLBACK_BY_FAMILY:
        return f"Bunu anlamadım. {FALLBACK_BY_FAMILY[family]}"
    return NEUTRAL_FALLBACK_TEXT


def _get_oneri(
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
    session_consent: bool = False,
) -> list[str]:
    parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module, session_consent=session_consent)
    consent_ok = parts["consent_ok"]
    ks_ready = parts["keystore_ready"]
    durum_label = parts.get("durum_label", "")
    out: list[str] = []
    if not consent_ok:
        out.append("Önce consent akışını tamamla.")
        if len(out) >= 3:
            return out
    if not ks_ready:
        out.append("Önce keystore kurulumunu kontrol et: kilit")
        if len(out) >= 3:
            return out
    if consent_ok and ks_ready and durum_label == "güvenli":
        try:
            cfg = presence_module.load_presence_cfg(Path(base_dir))
            pres_enabled = bool(getattr(cfg, "enabled", False))
        except Exception:
            pres_enabled = True
        if not pres_enabled:
            out.append("İstersen kamera aç: kamera")
        if not out:
            out.append("Hazırsın. durum, hazir veya yardım et ile devam edebilirsin.")
        return out
    if consent_ok and ks_ready:
        out.append("İstersen kamera aç: kamera")
    return out if out else ["durum yazıp mevcut durumu kontrol edebilirsin."]


def _get_tek_sonraki_adim(
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
    session_consent: bool = False,
) -> str:
    oneriler = _get_oneri(base_dir, keystore_initialized, presence_module, session_consent=session_consent)
    first = (oneriler or [""])[0]
    if first.startswith("Önce consent"):
        return "Bir sonraki adım: önce consent akışını tamamla."
    if first.startswith("Önce keystore"):
        return "Bir sonraki adım: keystore durumunu kontrol et."
    if "kamera" in first and "aç" in first:
        return "Bir sonraki adım: istersen kamera/presence aç."
    if "Hazırsın" in first or "devam edebilirsin" in first:
        return "Bir sonraki adım: durum veya hazir ile devam et."
    if "durum" in first:
        return "Bir sonraki adım: durum veya hazir ile devam et."
    return "Bir sonraki adım: durum veya hazir ile devam et."


def _get_guvenli_cevap(
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
    session_consent: bool = False,
) -> str:
    parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module, session_consent=session_consent)
    consent_ok = parts["consent_ok"]
    ks_ready = parts["keystore_ready"]
    durum_label = parts.get("durum_label", "")
    if not consent_ok:
        return "Şu an tam güvenli değilsin. Consent eksik."
    if not ks_ready:
        return "Şu an tam güvenli değilsin. Keystore hazır değil."
    try:
        cfg = presence_module.load_presence_cfg(Path(base_dir))
        pres_enabled = bool(getattr(cfg, "enabled", False))
    except Exception:
        pres_enabled = False
    if consent_ok and ks_ready and not pres_enabled:
        return "Şu an kısmen güvenlisin. Keystore hazır ama presence kapalı."
    if durum_label == "güvenli":
        return "Şu an güvenlisin. Temel korumalar aktif."
    return "Şu an kısmen güvenlisin. " + (parts.get("not_line") or "Durum ile detay görebilirsin.")


def _get_en_onemli_eksik(
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
    session_consent: bool = False,
) -> str:
    parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module, session_consent=session_consent)
    if not parts["consent_ok"]:
        return "En önemli eksik: consent alınmamış."
    if not parts["keystore_ready"]:
        return "En önemli eksik: keystore hazır değil."
    if parts.get("not_line") != "kritik eksik yok":
        return "En önemli eksik: temel güvenlik durumu tam değil."
    return "Şu an kritik bir eksik görünmüyor."


def _get_mod_cevabi(
    mode: str,
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
    session_consent: bool = False,
) -> str:
    if (mode or "").strip().lower() == "offline":
        parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module, session_consent=session_consent)
        if parts.get("durum_label") == "güvenli":
            return "Şu an güvenli offline moddasın."
        return "Şu an offline moddasın."
    return "Şu an online moddasın."


def _format_neden_cevap(reason: str | None) -> str:
    if not (reason or "").strip():
        return "Bu cevap için kayda değer bir gerekçem yok."
    r = reason.strip().rstrip(".")
    return "Bunu " + r + " olduğu için söyledim."


def _shorten_previous_response(text: str) -> str:
    t = (text or "").strip().replace("\n", " ")
    while "  " in t:
        t = t.replace("  ", " ")
    if not t:
        return ""
    first_sentence_end = -1
    for i, c in enumerate(t):
        if c in ".?!":
            first_sentence_end = i + 1
            break
    if first_sentence_end > 0:
        first = t[:first_sentence_end].strip()
    else:
        first = t
    max_len = 120
    if len(first) <= max_len:
        return first
    truncated = first[:max_len].rsplit(maxsplit=1)
    if not truncated:
        return first[:max_len].rstrip()
    return truncated[0].rstrip(".,") + "."


def _note_for_hatirla(text: str | None) -> str | None:
    if not (text or "").strip():
        return None
    short = _shorten_previous_response(text).strip()
    if not short or len(short) > HATIRLA_NOTE_MAX_LEN:
        short = short[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,") if len(short or "") > HATIRLA_NOTE_MAX_LEN else (short or "")
    if not short:
        return None
    first_line = (short.split("\n")[0] or "").strip()
    if first_line.count("|") >= 2 and any(x in first_line.upper() for x in ("LOCKED", "UNLOCKED", "PRESENCE")):
        return None
    return short[:HATIRLA_NOTE_MAX_LEN].strip() or None


def _record_note_op(history: list[list[str]], op_label: str) -> None:
    h = history[0]
    h.append(op_label)
    if len(h) > 5:
        h.pop(0)


def _record_today_action(
    today_date: list[str],
    today_actions: list[list[str]],
    action: str,
) -> None:
    today = date.today().isoformat()
    if today_date[0] != today:
        today_date[0] = today
        today_actions[0] = []
    if action and action not in today_actions[0]:
        today_actions[0].append(action)


def _format_today_bullet(action: str) -> str:
    if action.startswith("En son "):
        s = action[7:].strip()
        if s.endswith("."):
            s = s[:-1]
        return s
    return action


def normalize_command(raw: str, base_dir: Path, aliases: dict) -> tuple[str, list[str]]:
    """Strip, casefold, apply user aliases, normalize head to canonical command. Return (canonical, args)."""
    s = (raw or "").strip().casefold()
    if not s:
        return ("", [])
    s = apply_alias(s, aliases)
    s = re.sub(r"[.,]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().casefold()
    if not s:
        return ("", [])
    s = unicodedata.normalize("NFC", s)
    parts = s.split()
    if len(parts) == 2 and _fold_for_search(parts[0]) == "genel" and _fold_for_search(parts[1]) == "onaykapat":
        parts = [parts[0], "onay", "kapat"]
    head = parts[0]
    rest = parts[1:] if len(parts) > 1 else []
    if head in EXIT_SYNONYMS:
        return ("exit", [])
    if len(parts) >= 2 and head in ("help", "?", "yardim", "yardım") and parts[1].casefold() == "etiketler":
        return ("help_etiketler", [])
    if len(parts) >= 3 and head in ("help", "?", "yardim", "yardım") and parts[1].casefold() == "not" and parts[2].casefold() in ("işlemleri", "islemleri"):
        return ("help_not_islemleri", [])
    if len(parts) >= 2 and head in ("help", "?", "yardim", "yardım") and parts[1].casefold() == "notlar":
        return ("help_notlar", [])
    if len(parts) >= 2 and head in ("help", "?", "yardim", "yardım") and parts[1].casefold() == "temel":
        return ("help_temel", [])
    if len(parts) >= 2 and head in ("help", "?", "yardim", "yardım") and parts[1].casefold() in ("güvenlik", "guvenlik"):
        return ("help_guvenlik", [])
    if len(parts) >= 2 and head in ("help", "?", "yardim", "yardım") and _fold_for_search(parts[1]) == "kisa":
        return ("help_kisa", [])
    if len(parts) >= 2 and head in ("help", "?", "yardim", "yardım") and parts[1].casefold() == "arama":
        return ("help_arama", [])
    if len(parts) >= 2 and head in ("help", "?", "yardim", "yardım") and parts[1].casefold() in ("görüntüleme", "goruntuleme"):
        return ("help_goruntuleme", [])
    if head in ("help", "?", "yardim", "yardım"):
        return ("help", [])
    if head in ("kilit", "lock"):
        return ("kilit", rest)
    if head in ("kamera", "presence"):
        return ("kamera", rest)
    if head == "alias":
        return ("alias", rest)
    if head == "durum":
        return ("durum", rest)
    if head in ("hazir", "hazır"):
        return ("hazir", rest)
    if head == "self" and len(parts) >= 2 and parts[1].lower() == "test":
        return ("self_test", [])
    if head == "selftest":
        return ("self_test", [])
    if head == "not" and len(parts) >= 2 and _fold_for_search(parts[1]) == "ozetle":
        return ("not_ozetle", [])
    if len(parts) >= 2 and head == "notu":
        rest_folded = _fold_for_search(" ".join(parts[1:]))
        if rest_folded == "kopyala":
            return ("notu_kopyala", [])
        if rest_folded == "disa aktar":
            return ("notu_disa_aktar", [])
        if rest_folded == "paylas":
            return ("notu_paylas", [])
        if rest_folded == "duzenle":
            return ("notu_duzenle", [])
        if rest_folded.startswith("duzenle ") and len(parts) > 2:
            edit_text = " ".join(parts[2:]).strip()
            return ("notu_duzenle", [edit_text] if edit_text else [])
        if rest_folded == "sil":
            return ("notu_sil", [])
        if rest_folded == "geri al":
            return ("notu_geri_al", [])
    _q = (
        s.replace("\u0131", "i")
        .replace("İ", "i")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ç", "c")
    )
    if _q.strip() == "not ozetle" or (_q.strip().startswith("not ozetle") and (len(_q.strip()) == 10 or _q.strip()[10:11].isspace())):
        return ("not_ozetle", [])
    if _q in ("yardim et", "ne yazabilirim"):
        return ("rehber", [])
    if _q in ("ne yapiyorsun", "napiyon", "neyapiyorsun", "ne yapiyon"):
        return ("ne_yapiyorsun", [])
    if _q == "son yaptigin ne":
        return ("son_yaptigin_ne", [])
    if _q == "bugun ne yaptin":
        return ("bugun_ne_yaptin", [])
    if _q in ("bana ne onerirsin", "ne onerirsin", "onerir"):
        return ("onerir", [])
    if _q == "bir sonraki adim ne":
        return ("sonraki_adim", [])
    if _q == "su an guvenli miyim":
        return ("guvenli_miyim", [])
    if _q == "en onemli eksik ne":
        return ("en_onemli_eksik", [])
    if _q == "neden boyle diyorsun":
        return ("neden_boyle", [])
    if _q == "bunu kisaca anlat":
        return ("kisaca_anlat", [])
    if _q.startswith("bunu hatirla "):
        rest = s[13:].strip()
        return ("hatirla", [rest] if rest else [])
    if _q.startswith("bunlari hatirla "):
        rest = s[16:].strip()
        return ("hatirla", [rest] if rest else [])
    if _q == "not et" or _q == "not al":
        return ("hatirla", [])
    if _q.startswith("not et "):
        rest = s[7:].strip()
        return ("hatirla", [rest] if rest else [])
    if _q.startswith("not al "):
        rest = s[7:].strip()
        return ("hatirla", [rest] if rest else [])
    if _q == "bunu not et":
        return ("hatirla", [])
    if _q.startswith("bunu not et "):
        rest = s[12:].strip()
        return ("hatirla", [rest] if rest else [])
    if _q in ("bunu hatirla", "bunlari hatirla"):
        return ("hatirla", [])
    _q_flat = " ".join(_q.split())
    if _q_flat in ("son not ne", "son not ney", "son noy ne"):
        return ("son_not_ne", [])
    if _q == "etiketli notlari goster":
        return ("etiketli_notlari_goster", [])
    if _q == "etikete gore notlari goster":
        return ("etikete_gore_notlari_goster", [])
    if _q.startswith("etikete gore notlari goster "):
        tag = (_q[25:].strip().split() or [""])[0]
        return ("etikete_gore_notlari_goster", [tag] if tag else [])
    if _q == "notlari goster":
        return ("notlari_goster", [])
    if _q == "etiketleri goster":
        return ("etiketleri_goster", [])
    if _q == "notlari temizle":
        return ("notlari_temizle", [])
    if _q == "notu sil":
        return ("notu_sil", [])
    if _q == "notu kopyala":
        return ("notu_kopyala", [])
    if _q == "notu disa aktar":
        return ("notu_disa_aktar", [])
    if _q == "notu paylas":
        return ("notu_paylas", [])
    if _q == "not ozetle":
        return ("not_ozetle", [])
    if _q == "notu duzenle":
        return ("notu_duzenle", [])
    if _q == "not birlestir":
        return ("not_birlestir", [])
    if _q == "notu geri al":
        return ("notu_geri_al", [])
    if _q == "kac not var":
        return ("kac_not_var", [])
    if _q == "not gecmisi":
        return ("not_gecmisi", [])
    if _q == "not ara":
        return ("not_ara", [])
    if _q.startswith("not ara "):
        word = (_q[8:].strip().split() or [""])[0]
        return ("not_ara", [word])
    if _q == "etiketli not ara":
        return ("etiketli_not_ara", [])
    if _q.startswith("etiketli not ara "):
        word = (_q[17:].strip().split() or [""])[0]
        return ("etiketli_not_ara", [word] if word else [])
    if _q == "notu adlandir":
        return ("notu_adlandir", [])
    if _q.startswith("notu adlandir "):
        tag = _q[14:].strip()
        return ("notu_adlandir", [tag] if tag else [])
    if _q == "etiket ara":
        return ("etiket_ara", [])
    if _q.startswith("etiket ara "):
        word = (_q[11:].strip().split() or [""])[0]
        return ("etiket_ara", [word] if word else [])
    if _q == "etiket kaldir":
        return ("etiket_kaldir", [])
    if _q.startswith("etiket kaldir "):
        tag = _q[14:].strip()
        return ("etiket_kaldir", [tag] if tag else [])
    if _q == "etiket degistir":
        return ("etiket_degistir", [])
    if _q.startswith("etiket degistir "):
        rest = _q[16:].strip().split()
        eski = (rest[0] if rest else "").strip()
        yeni = (rest[1] if len(rest) >= 2 else "").strip()
        return ("etiket_degistir", [eski, yeni])
    if _q in ("durum ozet", "durum ozeti"):
        return ("durum", [])
    if _q == "hangi moddayim":
        return ("hangi_moddayim", [])
    _head_fold = _fold_for_search(head)
    if _head_fold == "gorevler":
        return ("gorevler", [])
    if _head_fold == "gorev" and len(parts) >= 2:
        second_fold = _fold_for_search(parts[1])
        second_fold = GOREV_SECOND_TOKEN_TOLERANCE.get(second_fold, second_fold)
        if second_fold == "olustur":
            rest = " ".join(parts[2:]).strip()
            return ("gorev_olustur", [rest] if rest else [])
        if second_fold in ("kuyruk", "kuyruğu", "kuyruk listesi"):
            return ("gorev_kuyruk", [])
        if second_fold == "temizle" and len(parts) >= 3:
            third_fold = _fold_for_search(parts[2])
            if third_fold in ("tamamlananlar", "tamamlanmislar", "tamamlanmis"):
                return ("gorev_temizle_tamamlananlar", [])
            if third_fold in ("simulasyonlar", "simulasyon", "simülasyonlar"):
                return ("gorev_temizle_simulasyonlar", [])
        if second_fold == "durumu":
            return ("gorev_durumu", [parts[2]] if len(parts) >= 3 else [])
        if second_fold == "ozeti":
            return ("gorev_ozeti", [parts[2]] if len(parts) >= 3 else [])
        if second_fold == "adimlari":
            return ("gorev_adimlari", [parts[2]] if len(parts) >= 3 else [])
        if second_fold in ("arsivle", "arsiv", "arşivle", "arşiv"):
            return ("gorev_arsivle", [parts[2]] if len(parts) >= 3 else [])
        if second_fold == "sil":
            return ("gorev_sil", [parts[2]] if len(parts) >= 3 else [])
        if second_fold in ("sayac", "sayaç", "istatistik", "istatistikler"):
            return ("gorev_sayac", [])
        if parts[1].lower() in ("iptal", "iptal"):
            return ("gorev_iptal", [parts[2]] if len(parts) >= 3 else [])
    if _head_fold == "gorev" and len(parts) == 1:
        return ("gorevler", [])
    if len(parts) >= 2 and _fold_for_search(parts[0]) == "yetki" and _fold_for_search(parts[1]) in YETKI_PROFIL_TOLERANCE:
        return ("yetki_profili", [parts[2]] if len(parts) >= 3 else [])
    if len(parts) >= 3 and _fold_for_search(parts[0]) == "genel" and _fold_for_search(parts[1]) == "onay":
        third = _fold_for_search(parts[2])
        if third in ("ac", "aç"):
            return ("genel_onay_ac", [])
        if third == "kapat":
            return ("genel_onay_kapat", [])
    return ("unknown", [])


def handle_command(raw: str, base_dir: Path, aliases: dict) -> tuple[str, list[str]]:
    """Alias for normalize_command for compatibility."""
    return normalize_command(raw, base_dir, aliases)
