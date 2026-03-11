"""Lumos core CLI: lock, presence, alias, durum."""
import json
import os
import re
from datetime import date
from getpass import getpass
from pathlib import Path
from typing import Any

from core.engine import CoreEngine
from core.logfmt import logfmt
from core.lumos import Lumos
from core.state import CoreState, format_durum
from core.startup_health import get_durum_parts, get_startup_summary
from engine.online_engine import OnlineEngineV1
from memory.secure_store import SecureNotesStore
from policy.offline_engine import OfflineEngineV1
from security import presence_lock as pl
from security.aliases import load_aliases, save_aliases, apply_alias
from security.keystore import FileKeyStore
from security.permissions import PermissionManager


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

HELP_TEXT = """Komutlar: kilit | kamera | alias | durum | hazır mıyım | hangi moddayım | şu an güvenli miyim | bana ne önerirsin | bir sonraki adım ne | en önemli eksik ne | neden böyle diyorsun | bunu kısaca anlat | bunu hatırla | son not ne | not özetle | notu kopyala | notu dışa aktar | notu paylaş | notları göster | etiketli notları göster | etikete göre notları göster <etiket> | etiketleri göster | not geçmişi | not ara <kelime> | etiketli not ara <kelime> | etiket ara <kelime> | notları temizle | notu sil | notu düzenle | notu adlandır <etiket> | etiket kaldır <etiket> | etiket değiştir <eski> <yeni> | not birleştir | notu geri al | ne yapıyorsun | son yaptığın ne | bugün ne yaptın | exit
  kilit    Cihaz kilidi / şifre
  kamera   Yüz tanıma (presence) kilit
  alias    Komut kısaltmaları (alias liste | alias ekle <ad> <hedef> | alias sil <ad>)
  durum    Kısa durum özeti (lock, presence, consent, mod, kritik not)
  hazır mıyım / hazir   Tek satır hazır olma özeti
  hangi moddayım   Mevcut çalışma modu (offline / online / güvenli offline)
  şu an güvenli miyim   Doğrudan güvenlik cevabı (kısa, dürüst)
  bana ne önerirsin   Şu an için en mantıklı sonraki adım (1–3 öneri)
  bir sonraki adım ne   Tek ve net bir sonraki adım
  en önemli eksik ne   Tek kritik eksik (consent > lock > güvenlik; yoksa yok)
  neden böyle diyorsun   Bir önceki cevabın kısa gerekçesi
  bunu kısaca anlat   Bir önceki cevabı kısa ve sade özetle
  bunu hatırla   Son anlamlı cevabı veya durum özetini kısa not olarak kaydeder
  son not ne   En son "bunu hatırla" ile kaydettiğin notu gösterir
  not özetle   En son kaydedilmiş notu kısa özet halinde verir
  notu kopyala   En son notu düz metin olarak verir (kopyalamak için)
  notu dışa aktar   En son notu tek satır düz metin olarak verir (dışa aktarmak için)
  notu paylaş   En son notu paylaşılabilir tek satır olarak verir
  notları göster   Kayıtlı notları listeler (en fazla son 5)
  etiketli notları göster   Sadece etiketli notları listeler (en fazla son 5)
  etikete göre notları göster <etiket>   Verilen etikete sahip notları listeler (en fazla 5)
  etiketleri göster   Kayıtlı notlardaki etiketleri listeler
  not geçmişi   Son not işlemlerini listeler (en fazla 5)
  notları temizle   Kayıtlı notları siler
  notu sil   En son notu siler
  notu düzenle   Son notu yeni kısa metinle değiştirir
  notu adlandır <etiket>   En son nota kısa etiket ekler
  etiket kaldır <etiket>   En son nottan etiketi kaldırır
  etiket değiştir <eski> <yeni>   Son nottaki etiketi yeni adla değiştirir
  not birleştir   Son iki notu tek kısa notta birleştirir
  notu geri al   Son not işlemini geri alır (silme, temizleme, düzenleme, birleştirme)
  not ara <kelime>   Kayıtlı notlarda kelime arar (en fazla 5 eşleşme)
  etiketli not ara <kelime>   Sadece etiketli notlarda kelime arar
  etiket ara <kelime>   Kayıtlı etiketlerde kelime arar
  ne yapıyorsun   Şu an ne yaptığını söyler
  son yaptığın ne   En son tamamladığın işi söyler
  bugün ne yaptın   Bugünkü işlerin kısa özeti
  exit     Çıkış (q, çık, quit)
Örnek: kilit, kamera aç, durum, hazir, hangi moddayım, şu an güvenli miyim, bana ne önerirsin, bir sonraki adım ne, en önemli eksik ne, neden böyle diyorsun, bunu kısaca anlat, bunu hatırla, son not ne, not özetle, notu kopyala, notu dışa aktar, notu paylaş, notları göster, etiketli notları göster, etikete göre notları göster güvenlik, etiketleri göster, not geçmişi, not ara lock, etiketli not ara lock, etiket ara güven, notları temizle, notu sil, notu düzenle, notu adlandır güvenlik, etiket kaldır güvenlik, etiket değiştir güvenlik koruma, not birleştir, notu geri al, ne yapıyorsun, son yaptığın ne, bugün ne yaptın, çık"""

REHBER_TEXT = """Şunları kullanabilirsin:
  kilit: cihaz kilidi işlemleri
  kamera: yüz algılama ve otomatik kilit
  durum: mevcut durum özeti (detaylı)
  hazir: hızlı hazır olma özeti
  hangi moddayım: mevcut çalışma modu (tek cümle)
  şu an güvenli miyim: doğrudan güvenlik cevabı
  bana ne önerirsin: şu an için 1–3 sonraki adım önerisi
  bir sonraki adım ne: tek ve net bir sonraki adım
  en önemli eksik ne: tek kritik eksik
  neden böyle diyorsun: bir önceki cevabın kısa gerekçesi
  bunu kısaca anlat: bir önceki cevabı kısa ve sade özetle
  bunu hatırla: son cevabı veya durum özetini kısa not olarak kaydeder
  son not ne: en son kaydettiğin notu gösterir
  not özetle: en son kaydedilmiş notu kısa özet halinde verir
  notu kopyala: en son notu düz metin olarak verir
  notu dışa aktar: en son notu tek satır düz metin olarak verir (dışa aktarmak için)
  notu paylaş: en son notu paylaşılabilir tek satır olarak verir
  notları göster: kayıtlı notları listeler (en fazla son 5)
  etiketli notları göster: sadece etiketli notları listeler (en fazla son 5)
  etikete göre notları göster <etiket>: verilen etikete sahip notları listeler (en fazla 5)
  etiketleri göster: kayıtlı notlardaki etiketleri listeler
  not geçmişi: son not işlemlerini listeler (en fazla 5)
  notları temizle: kayıtlı notları siler
  notu sil: en son notu siler
  notu düzenle: son notu yeni kısa metinle değiştirir
  notu adlandır <etiket>: en son nota kısa etiket ekler
  etiket kaldır <etiket>: en son nottan etiketi kaldırır
  etiket değiştir <eski> <yeni>: son nottaki etiketi yeni adla değiştirir
  not birleştir: son iki notu tek kısa notta birleştirir
  notu geri al: son not işlemini geri alır (silme, temizleme, düzenleme, birleştirme)
  not ara <kelime>: kayıtlı notlarda kelime arar (en fazla 5)
  etiketli not ara <kelime>: sadece etiketli notlarda kelime arar
  etiket ara <kelime>: kayıtlı etiketlerde kelime arar
  ne yapıyorsun: o an üstünde olduğun işi söyler
  son yaptığın ne: en son tamamladığın işi söyler
  bugün ne yaptın: bugünkü işlerin kısa özeti
  çık: çıkış yapar"""

# Bilinmeyen komut: kısa, yönlendirici; teknik hata yok
UNKNOWN_CMD_TEXT = 'Bunu anlamadım. "durum", "hazir" veya "yardım et" deneyebilirsin.'


def _get_oneri(base_dir: str | Path, keystore_initialized: bool, presence_module: Any) -> list[str]:
    """Mevcut duruma göre 1–3 kısa sonraki adım önerisi. Boş genel tavsiye yok."""
    from core.startup_health import get_durum_parts
    parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module)
    consent_ok = parts["consent_ok"]
    lock_ok = parts["lock_ok"]
    durum_label = parts.get("durum_label", "")
    out: list[str] = []
    if not consent_ok:
        out.append("Önce consent akışını tamamla.")
        if len(out) >= 3:
            return out
    if not lock_ok:
        out.append("Önce kilit kurulumunu kontrol et: kilit")
        if len(out) >= 3:
            return out
    if consent_ok and lock_ok and durum_label == "güvenli":
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
    if consent_ok and lock_ok:
        out.append("İstersen kamera aç: kamera")
    return out if out else ["durum yazıp mevcut durumu kontrol edebilirsin."]


def _get_tek_sonraki_adim(base_dir: str | Path, keystore_initialized: bool, presence_module: Any) -> str:
    """Mevcut duruma göre tek ve net bir sonraki adım. Tek cümle, 'Bir sonraki adım: ...'."""
    oneriler = _get_oneri(base_dir, keystore_initialized, presence_module)
    first = (oneriler or [""])[0]
    if first.startswith("Önce consent"):
        return "Bir sonraki adım: önce consent akışını tamamla."
    if first.startswith("Önce kilit"):
        return "Bir sonraki adım: lock durumunu kontrol et."
    if "kamera" in first and "aç" in first:
        return "Bir sonraki adım: istersen kamera/presence aç."
    if "Hazırsın" in first or "devam edebilirsin" in first:
        return "Bir sonraki adım: durum veya hazir ile devam et."
    if "durum" in first:
        return "Bir sonraki adım: durum veya hazir ile devam et."
    return "Bir sonraki adım: durum veya hazir ile devam et."


def _get_guvenli_cevap(base_dir: str | Path, keystore_initialized: bool, presence_module: Any) -> str:
    """Mevcut state'e göre kısa ve dürüst güvenlik cevabı. Tek cümle veya en fazla 2 kısa satır."""
    from core.startup_health import get_durum_parts
    parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module)
    consent_ok = parts["consent_ok"]
    lock_ok = parts["lock_ok"]
    durum_label = parts.get("durum_label", "")
    if not consent_ok:
        return "Şu an tam güvenli değilsin. Consent eksik."
    if not lock_ok:
        return "Şu an tam güvenli değilsin. Lock aktif değil."
    try:
        cfg = presence_module.load_presence_cfg(Path(base_dir))
        pres_enabled = bool(getattr(cfg, "enabled", False))
    except Exception:
        pres_enabled = False
    if consent_ok and lock_ok and not pres_enabled:
        return "Şu an kısmen güvenlisin. Lock aktif ama presence kapalı."
    if durum_label == "güvenli":
        return "Şu an güvenlisin. Temel korumalar aktif."
    return "Şu an kısmen güvenlisin. " + (parts.get("not_line") or "Durum ile detay görebilirsin.")


def _get_en_onemli_eksik(base_dir: str | Path, keystore_initialized: bool, presence_module: Any) -> str:
    """Mevcut duruma göre tek kritik eksik. Öncelik: consent > lock > temel güvenlik; yoksa kritik eksik yok."""
    parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module)
    if not parts["consent_ok"]:
        return "En önemli eksik: consent alınmamış."
    if not parts["lock_ok"]:
        return "En önemli eksik: lock aktif değil."
    if parts.get("not_line") != "kritik eksik yok":
        return "En önemli eksik: temel güvenlik durumu tam değil."
    return "Şu an kritik bir eksik görünmüyor."


def _get_mod_cevabi(
    mode: str,
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
) -> str:
    """Mevcut çalışma modunu tek cümle söyle. durum/hazır ile karışmaz; sadece mod cevabı."""
    if (mode or "").strip().lower() == "offline":
        parts = get_durum_parts(Path(base_dir), keystore_initialized, presence_module)
        if parts.get("durum_label") == "güvenli":
            return "Şu an güvenli offline moddasın."
        return "Şu an offline moddasın."
    return "Şu an online moddasın."


def _format_neden_cevap(reason: str | None) -> str:
    """Son cevabın kısa gerekçesi. 1 cümle, en fazla 2 kısa cümle."""
    if not (reason or "").strip():
        return "Bu cevap için kayda değer bir gerekçem yok."
    r = reason.strip().rstrip(".")
    return "Bunu " + r + " olduğu için söyledim."


# Önceki cevabı kısaltmak için: bu uzunluktan kısaysa "zaten kısa" denir
KISACA_ANLAT_SHORT_THRESHOLD = 90

# "Bunu hatırla" ile kaydedilen notun azami uzunluğu
HATIRLA_NOTE_MAX_LEN = 150

# "Not özetle": bu uzunluktan kısaysa "zaten yeterince kısa" denir
NOT_OZETLE_SHORT_THRESHOLD = 100
NOT_ADLANDIR_MAX_TAG_LEN = 24


def _shorten_previous_response(text: str) -> str:
    """Önceki (uzun) cevabın özünü bozmadan kısa, sade özeti. Yeni bilgi eklemez."""
    t = (text or "").strip().replace("\n", " ")
    while "  " in t:
        t = t.replace("  ", " ")
    if not t:
        return ""
    # İlk cümleyi al (nokta veya ? ! ile biten)
    first_sentence_end = -1
    for i, c in enumerate(t):
        if c in ".?!":
            first_sentence_end = i + 1
            break
    if first_sentence_end > 0:
        first = t[:first_sentence_end].strip()
    else:
        first = t
    # İlk cümle çok uzunsa kelime sınırında kırp (max 120 karakter)
    max_len = 120
    if len(first) <= max_len:
        return first
    truncated = first[:max_len].rsplit(maxsplit=1)
    if not truncated:
        return first[:max_len].rstrip()
    return truncated[0].rstrip(".,") + "."


def _note_for_hatirla(text: str | None) -> str | None:
    """Son cevaptan 'bunu hatırla' için kısa not üretir. Anlamsız/teknikse None döner."""
    if not (text or "").strip():
        return None
    short = _shorten_previous_response(text).strip()
    if not short or len(short) > HATIRLA_NOTE_MAX_LEN:
        short = short[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,") if len(short or "") > HATIRLA_NOTE_MAX_LEN else (short or "")
    if not short:
        return None
    # Teknik veri dökümü: tek satırda çok pipe (örn. LOCKED | Presence: ...)
    first_line = (short.split("\n")[0] or "").strip()
    if first_line.count("|") >= 2 and any(x in first_line.upper() for x in ("LOCKED", "UNLOCKED", "PRESENCE")):
        return None
    return short[:HATIRLA_NOTE_MAX_LEN].strip() or None


def _lumos_dir() -> str:
    if Path("src/.lumos").exists():
        return "src/.lumos"
    return ".lumos"

def _read_lumos_id(base_dir: str) -> str:
    try:
        p = Path(base_dir) / "identity.json"
        if not p.exists():
            return ""
        data = json.loads(p.read_text(encoding="utf-8"))
        return str(data.get("lumos_id", "")).strip()
    except Exception:
        return ""

def _input_or_eof(prompt: str, eof_value: str = "cik") -> str:
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return eof_value


def _parse_yes_no(x: str) -> bool | None:
    x = (x or "").strip().lower()
    x = x.replace("ı", "i").replace("İ", "i")
    yes = {"evet", "e", "y", "yes", "ok", "tamam", "ewet"}
    no = {"hayir", "hayır", "h", "n", "no"}
    if x in yes:
        return True
    if x in no:
        return False
    return None


def _fold_for_search(s: str) -> str:
    """Büyük/küçük harf ve Türkçe karakter farkını tolere etmek için metni katla."""
    s = (s or "").strip().casefold()
    return (
        s.replace("\u0131", "i").replace("İ", "i")
        .replace("ö", "o").replace("ü", "u")
        .replace("ş", "s").replace("ğ", "g").replace("ç", "c")
    )


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
    parts = s.split()
    head = parts[0]
    rest = parts[1:] if len(parts) > 1 else []
    if head in EXIT_SYNONYMS:
        return ("exit", [])
    if head in ("help", "?"):
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
    # "yardım et" / "ne yazabilirim" -> kısa rehber; Türkçe harfleri ASCII'ye çevir (ö→o, ü→u, ş→s, ğ→g, ç→c, ı→i)
    _q = (
        s.replace("\u0131", "i")
        .replace("İ", "i")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ç", "c")
    )
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
    if _q == "bunu hatirla":
        return ("hatirla", [])
    if _q == "son not ne":
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
    if _q == "hangi moddayim":
        return ("hangi_moddayim", [])
    return ("unknown", [])


def handle_command(raw: str, base_dir: Path, aliases: dict) -> tuple[str, list[str]]:
    """Alias for normalize_command for compatibility."""
    return normalize_command(raw, base_dir, aliases)


def _record_note_op(history: list[list[str]], op_label: str) -> None:
    """Son not işlemleri listesine ekle; en fazla 5, en yeni sonda."""
    h = history[0]
    h.append(op_label)
    if len(h) > 5:
        h.pop(0)


def _record_today_action(
    today_date: list[str],
    today_actions: list[list[str]],
    action: str,
) -> None:
    """Bugünkü iş listesine ekle; gün değiştiyse sıfırla. Aynı iş tekrar eklenmez."""
    today = date.today().isoformat()
    if today_date[0] != today:
        today_date[0] = today
        today_actions[0] = []
    if action and action not in today_actions[0]:
        today_actions[0].append(action)


def _format_today_bullet(action: str) -> str:
    """'En son X.' -> 'X' (madde metni)."""
    if action.startswith("En son "):
        s = action[7:].strip()
        if s.endswith("."):
            s = s[:-1]
        return s
    return action


def main() -> None:
    mode = os.getenv("LUMOS_MODE", "offline").strip().lower()

    base_dir = _lumos_dir()
    try:
        aliases = load_aliases(base_dir)
    except Exception:
        aliases = {}
    if not isinstance(aliases, dict):
        aliases = {}

    perm = PermissionManager(enabled=True)
    offline_engine = OfflineEngineV1(perm=perm)
    online_engine = OnlineEngineV1()
    engine = offline_engine if mode == "offline" else online_engine

    lumos = Lumos(mode=mode, engine=engine)
    lumos.boot()
    root_key = None
    ks = FileKeyStore(base_dir=base_dir)

    def _attach_notes(rk: bytes) -> bool:
        try:
            store = SecureNotesStore(base_dir=base_dir)
            lumos.note_memory.attach_store(store, rk)
            return True
        except Exception:
            return False

    def unlock_with_passphrase(passphrase: str) -> tuple[bool, str]:
        nonlocal root_key, online_engine, engine
        p = (passphrase or "").strip()

        if not p:

            return False, "FAIL"

        try:

            rk = ks.load_root_key(p)

            if not _attach_notes(rk):

                return False, "FAIL"
            root_key = rk
            lumos.lock_state.unlock(rk)

            try:

                lumos.note_memory.root_key = rk

            except Exception:

                pass

            os.environ["LUMOS_PASSPHRASE"] = p

            if mode == "online":
                online_engine = OnlineEngineV1()
                engine = online_engine
                lumos.engine = engine

            try:

                if mode == "online":

                    if hasattr(online_engine, "set_passphrase"):

                        online_engine.set_passphrase(p)

                    elif hasattr(online_engine, "passphrase"):

                        online_engine.passphrase = p

                    if hasattr(online_engine, "client") and hasattr(online_engine.client, "set_passphrase"):

                        online_engine.client.set_passphrase(p)

                    elif hasattr(online_engine, "client") and hasattr(online_engine.client, "passphrase"):

                        online_engine.client.passphrase = p

            except Exception:

                pass

            return True, "OK"

        except Exception:

            return False, "FAIL"

    


    def device_lock_cli(silent: bool = False):
        try:
            nm = getattr(lumos, "note_memory", None)
            if nm and hasattr(nm, "device_lock"):
                nm.device_lock()
            if not silent:
                print("Cihaz kilitlendi. (Lumos aktif)")
        except Exception:
            if not silent:
                print("Device lock hata verdi.")
    def do_lock() -> None:
        nonlocal root_key

        lumos.lock_state.lock()

        fn = globals().get('maybe_device_lock')

        if callable(fn):

            fn(lumos)

        try:

            os.environ.pop("LUMOS_PASSPHRASE", None)

        except Exception:

            pass
        root_key = None

        try:
            lumos.note_memory.root_key = None
        except Exception:
            pass

    def presence_menu(*, state: CoreState, engine: CoreEngine, base_dir: str, initial_cmd: str | None = None) -> str | None:
        from pathlib import Path as _P
        pl = engine.pl

        def _lock_cb():
            engine.do_lock()
            try:
                engine.device_lock_cli(silent=False)
            except Exception:
                pass

        def _run_cmd(cmd: str) -> bool | str:
            cmd = (cmd or "").strip().lower()
            if cmd.startswith("kamera "):
                cmd = cmd.split(None, 1)[1].strip()
            _qc = cmd.replace("\u0131", "i")
            if _qc in ("ne yapiyorsun", "napiyon", "neyapiyorsun", "ne yapiyon"):
                print("Şu an kamera menüsündeyim.")
                return False
            if cmd in ("cik", "çık"):
                print("OK")
                return True
            if cmd and cmd.split()[0] in _GLOBAL_CMDS:
                return cmd
            if cmd in ("durum", "status"):
                cfg = pl.load_presence_cfg(_P(base_dir))
                print(f"enabled={cfg.enabled} timeout={cfg.timeout_sec}s face={cfg.require_face} mode={cfg.lock_mode} status={pl.presence_status()}")
                return False
            if cmd in ("ac", "aç", "on"):
                ans = _input_or_eof("Kamera tabanlı otomatik kilit açılsın mı? (evet/hayır): ")
                if ans in ("cik", "çık", "exit", "quit"):
                    print("OK")
                    return True
                __yn = _parse_yes_no(ans)
                if __yn is None:
                    print("Lütfen evet/hayır yaz.")
                    return False
                ans = "evet" if __yn else "hayır"
                if ans not in ("evet", "e", "yes", "y"):
                    print("OK")
                    return False

                raw = _input_or_eof("Kaç saniye yüz görünmezse kilitlesin? (varsayılan 30): ")
                try:
                    timeout = int(raw) if raw else 30
                except Exception:
                    timeout = 30
                if timeout < 5:
                    timeout = 5

                cfg = pl.load_presence_cfg(_P(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                cfg.enabled = True
                cfg.timeout_sec = timeout
                cfg.poll_sec = 1.0
                cfg.camera_index = 0
                cfg.require_face = True
                cfg.lock_mode = "mac"
                if not was_enabled:
                    state.log_event(logfmt("presence_enabled", timeout=cfg.timeout_sec, poll=cfg.poll_sec, cam=cfg.camera_index, require_face=cfg.require_face))
                pl.save_presence_cfg(_P(base_dir), cfg)
                pl.start_presence_lock(base_dir=_P(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face)
                print("OK")
                return False

            if cmd in ("kapat", "off", "stop"):
                cfg = pl.load_presence_cfg(_P(base_dir))
                was_enabled = bool(getattr(cfg, "enabled", False))
                pl.stop_presence_lock(base_dir=_P(base_dir), reason=None, silent=True)
                if was_enabled:
                    state.log_event(logfmt("presence_disabled"))
                cfg.enabled = False
                pl.save_presence_cfg(_P(base_dir), cfg)
                print("OK")
                return False

            if cmd in ("sure", "süre", "timeout"):
                cfg = pl.load_presence_cfg(_P(base_dir))
                default = int(getattr(cfg, "timeout_sec", 30))
                while True:
                    raw = _input_or_eof(f"Süre (sn) [{default}]: ")
                    if raw in ("cik", "çık", "exit", "quit"):
                        break
                    if raw == "" or raw in ("ok", "tamam"):
                        val = default
                        cfg.timeout_sec = val
                        pl.save_presence_cfg(_P(base_dir), cfg)
                        if cfg.enabled:
                            pl.stop_presence_lock(base_dir=_P(base_dir), silent=True)
                            pl.start_presence_lock(base_dir=_P(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face, silent_stop=True, reason="internal")
                        print("OK")
                        break
                    if not raw.isdigit():
                        print("Lütfen sayı, ok veya çık yaz.")
                        continue
                    val = int(raw)
                    if val < 5 or val > 600:
                        print("Süre 5 ile 600 saniye arasında olmalı.")
                        continue
                    cfg.timeout_sec = val
                    pl.save_presence_cfg(_P(base_dir), cfg)
                    if cfg.enabled:
                        pl.stop_presence_lock(base_dir=_P(base_dir), silent=True)
                        pl.start_presence_lock(base_dir=_P(base_dir), lock_cb=_lock_cb, is_already_locked=state.is_locked, timeout_sec=cfg.timeout_sec, poll_sec=cfg.poll_sec, camera_index=cfg.camera_index, require_face=cfg.require_face, silent_stop=True, reason="internal")
                    print("OK")
                    break
                return False

            print('Bunu anlamadım. Burada durum, ac, kapat, sure veya cik yazabilirsin.')
            return False

        print("Kamera: durum | ac | kapat | sure | cik")
        if initial_cmd:
            r = _run_cmd(initial_cmd)
            if r is True:
                return None
            if isinstance(r, str):
                return r
        while True:
            cmd = _input_or_eof("Kamera> ")
            r = _run_cmd(cmd)
            if r is True:
                return None
            if isinstance(r, str):
                return r

        try:
            import inspect
            import atexit
            from pathlib import Path as _P
    
            _base = _P(base_dir)
            _pcfg = pl.load_presence_cfg(_base)
    
            def _presence_lock_action():
                try:
                    engine.do_lock()
                except Exception:
                    pass
                try:
                    engine.device_lock_cli(silent=True)
                except Exception:
                    pass
    
            if getattr(_pcfg, "enabled", False) and not pl.is_running():
                try:
                    _sig = inspect.signature(pl.start_presence_lock)
                    _candidates = {
                        "base_dir": _base,
                        "on_lock": _presence_lock_action,
                        "lock_cb": _presence_lock_action,
                        "lock_fn": _presence_lock_action,
                        "callback": _presence_lock_action,
                        "on_trigger": _presence_lock_action,
                        "on_timeout": _presence_lock_action,
                        "is_already_locked": state.is_locked,
                    }
                    _kwargs = {k: v for k, v in _candidates.items() if k in _sig.parameters}
                    pl.start_presence_lock(**_kwargs)
                except Exception:
                    try:
                        pl.start_presence_lock(base_dir=_base)
                    except Exception:
                        pass

            if getattr(_pcfg, "enabled", False):
                def _presence_stop():
                    try:
                        _sig2 = inspect.signature(pl.stop_presence_lock)
                        _kwargs2 = {"base_dir": _base} if "base_dir" in _sig2.parameters else {}
                        pl.stop_presence_lock(**_kwargs2)
                    except Exception:
                        pass
    
                atexit.register(_presence_stop)
        except Exception:
            pass

    state = CoreState(lumos, pl, mode)
    engine = CoreEngine(do_lock, device_lock_cli, unlock_with_passphrase, pl)

    def _recovery_lock_cb():
        try:
            engine.do_lock()
        except Exception:
            pass
        try:
            engine.device_lock_cli(silent=True)
        except Exception:
            pass

    engine.recover_presence(Path(base_dir), state.log_event, _recovery_lock_cb, state.is_locked)

    # Ürün iyileştirmesi: "hazir" / "hazır mıyım" ana promptta çalışıyor; Kilit> / Kamera> alt menülerinde global komut olarak eklenebilir.
    _GLOBAL_CMDS = {"kilit", "lock", "kamera", "presence", "alias", "exit", "quit"}

    def lock_menu(*, state: CoreState, engine: CoreEngine, initial_cmd: str | None = None) -> str | None:
        def _run_cmd(c: str) -> bool | str:
            _qc = (c or "").strip().replace("\u0131", "i")
            if _qc in ("ne yapiyorsun", "napiyon", "neyapiyorsun", "ne yapiyon"):
                print("Şu an kilit menüsündeyim.")
                return False
            if c in ("cik", "çık"):
                print("OK")
                return True
            if c and c.split()[0] in _GLOBAL_CMDS:
                return c
            if c in ("durum", "status"):
                print(state.lock_status())
                return False
            if c in ("kapat", "kilitle", "lock"):
                engine.do_lock()
                try:
                    engine.device_lock_cli(silent=True)
                except Exception:
                    pass
                return False
            if c in ("ac", "aç", "unlock", "open"):
                pw = getpass("Passphrase: ")
                ok, msg = engine.unlock_with_passphrase(pw)
                print(msg)
                return False
            print('Bunu anlamadım. Burada durum, ac, kapat veya cik yazabilirsin.')
            return False

        print("LOCK")
        print("Kilit: durum | ac | kapat | cik")
        if initial_cmd:
            c = initial_cmd.strip().lower()
            if c.startswith("kilit "):
                c = c.split(None, 1)[1].strip()
            r = _run_cmd(c)
            if r is True:
                return None
            if isinstance(r, str):
                return r
        while True:
            cmd = _input_or_eof("Kilit> ")
            if cmd.startswith("kilit "):
                cmd = cmd.split(None, 1)[1].strip()
            r = _run_cmd(cmd)
            if r is True:
                return None
            if isinstance(r, str):
                return r

    def alias_menu(*, args: list[str]) -> None:
        if not args:
            print("Alias: alias liste | alias ekle <ad> <hedef> | alias sil <ad>")
            return
        if args[0] == "liste":
            if not aliases:
                print("(alias yok)")
            else:
                for k, v in sorted(aliases.items()):
                    print(f"  {k} -> {v}")
            return
        if args[0] == "ekle":
            rest = " ".join(args[1:]).strip()
            tokens = rest.split(None, 1)
            name = tokens[0].lower() if tokens else ""
            target = tokens[1].strip() if len(tokens) > 1 else name
            if not name:
                print("Lütfen alias ekle <ad> <hedef> yaz. Örnek: alias ekle k kilit")
                return
            aliases[name] = target
            save_aliases(base_dir, aliases)
            print("OK")
            return
        if args[0] == "sil":
            name = (args[1] if len(args) > 1 else "").strip().lower()
            if not name:
                print("Lütfen alias sil <ad> yaz.")
                return
            if name in aliases:
                del aliases[name]
                save_aliases(base_dir, aliases)
            print("OK")
            return
        print("Alias: alias liste | alias ekle <ad> <hedef> | alias sil <ad>")

    def run_panel() -> None:
        from pathlib import Path as _P
        try:
            from ui.tui import run_tui, tui_available
        except ImportError:
            print("Bu terminal panel desteklemiyor (curses yok).")
            return
        if not tui_available():
            print("Bu terminal panel desteklemiyor.")
            return
        mode_label = state.mode_str()
        title_line2 = f"{mode_label} • güvenli"
        log_path = _P.cwd() / ".lumos" / "log.txt"

        def snapshot_getter():
            return state.snapshot(base_dir=base_dir, log_path=log_path)

        run_tui(
            title="Lumos Core",
            title_line2=title_line2,
            snapshot_getter=snapshot_getter,
            items=[
                ("Kilit", lambda: lock_menu(state=state, engine=engine, initial_cmd=None)),
                ("Kamera (Presence)", lambda: presence_menu(state=state, engine=engine, base_dir=base_dir, initial_cmd=None)),
                ("Alias", lambda: alias_menu(args=[])),
                ("Kayıtlar", lambda: None),  # handled by TUI log viewer
                ("Kapat", None),
            ],
            descriptions=[
                "Cihaz kilidi / şifre",
                "Yüz tanıma kilit",
                "Komut kısaltmaları",
                "Son 200 log satırı",
                "Panelden çık",
            ],
            hint="↑↓ seç, Enter onay, q çıkış",
            log_path=log_path,
            log_item_index=3,
        )

    ui_mode = (os.getenv("LUMOS_UI") or "").strip().lower()
    if ui_mode == "tui":
        try:
            run_panel()
        except Exception:
            print("Panel açılamadı, normal CLI'ye geçiliyor.")
        return

    # ---- CLI döngüsü ----
    pending: str | None = None
    current_task: list[str | None] = [None]  # aktif görev; "ne yapıyorsun" buna bakar
    last_action: list[str | None] = [None]   # en son tamamlanan iş; "son yaptığın ne" buna bakar
    today_date: list[str] = [""]             # YYYY-MM-DD; gün değişince today_actions sıfırlanır
    today_actions: list[list[str]] = [[]]     # bugünkü (tekilleştirilmiş) işler; "bugün ne yaptın" buna bakar
    last_response_reason: list[str | None] = [None]  # son cevabın gerekçesi; "neden böyle diyorsun" buna bakar
    last_response_text: list[str | None] = [None]     # son cevabın tam metni; "bunu kısaca anlat" buna bakar
    saved_notes: list[list[str]] = [[]]               # "bunu hatırla" ile kaydedilen kısa notlar
    pending_note_edit: list[bool] = [False]            # "notu düzenle" sonrası yeni metin bekleniyor
    last_note_undo: list[tuple[str, Any] | None] = [None]  # (op, data) tek adımlık geri al
    note_ops_history: list[list[str]] = [[]]          # son not işlemleri (en fazla 5); "not geçmişi"
    while True:
        try:
            pl.watchdog_tick(Path(base_dir), state.log_event, _recovery_lock_cb, state.is_locked)
        except Exception:
            pass
        if pending is not None:
            raw = pending
        else:
            try:
                raw = input("Sen: ").strip()
            except EOFError:
                raw = "çık"

        pending = None
        route, args = normalize_command(raw, Path(base_dir), aliases)

        if pending_note_edit[0]:
            if route != "unknown":
                pending_note_edit[0] = False
            else:
                if not raw.strip():
                    print("Boş metin kabul edilmiyor.")
                    continue
                old_content = saved_notes[0][-1]
                saved_notes[0][-1] = raw.strip()
                last_note_undo[0] = ("notu_duzenle", old_content)
                _record_note_op(note_ops_history, "notu düzenle")
                print("Son notu güncelledim.")
                pending_note_edit[0] = False
                continue

        if route == "":
            continue
        if route == "help":
            last_response_reason[0] = "komut listesini istedin"
            last_action[0] = "En son yardım listesini gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = HELP_TEXT
            print(HELP_TEXT)
            continue
        if route == "rehber":
            last_response_reason[0] = "rehberi istedin"
            last_action[0] = "En son yardım rehberini gösterdim."
            _record_today_action(today_date, today_actions, last_action[0])
            last_response_text[0] = REHBER_TEXT
            print(REHBER_TEXT)
            continue
        if route == "onerir":
            oneriler = _get_oneri(base_dir, ks.is_initialized(), pl)
            for o in oneriler:
                print(o)
            last_response_reason[0] = (oneriler[0].rstrip(".") if oneriler and oneriler[0] else None)
            last_action[0] = "En son sonraki adım önerisini verdim."
            last_response_text[0] = "\n".join(oneriler) if oneriler else None
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "sonraki_adim":
            step = _get_tek_sonraki_adim(base_dir, ks.is_initialized(), pl)
            print(step)
            last_response_reason[0] = step.replace("Bir sonraki adım: ", "").strip() if step.startswith("Bir sonraki adım:") else step
            last_action[0] = "En son tek sonraki adımı söyledim."
            last_response_text[0] = step
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "guvenli_miyim":
            resp = _get_guvenli_cevap(base_dir, ks.is_initialized(), pl)
            print(resp)
            last_response_reason[0] = resp.split(". ", 1)[1].strip().rstrip(".") if ". " in resp else resp
            last_action[0] = "En son güvenlik cevabını verdim."
            last_response_text[0] = resp
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "en_onemli_eksik":
            resp = _get_en_onemli_eksik(base_dir, ks.is_initialized(), pl)
            print(resp)
            last_response_reason[0] = resp
            last_action[0] = "En son tek kritik eksiği söyledim."
            last_response_text[0] = resp
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "hangi_moddayim":
            resp = _get_mod_cevabi(mode, base_dir, ks.is_initialized(), pl)
            print(resp)
            last_response_reason[0] = resp
            last_action[0] = "En son mod cevabını verdim."
            last_response_text[0] = resp
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "neden_boyle":
            ned_cevap = _format_neden_cevap(last_response_reason[0])
            print(ned_cevap)
            last_action[0] = "En son önceki cevabın gerekçesini söyledim."
            last_response_text[0] = ned_cevap
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "kisaca_anlat":
            prev = (last_response_text[0] or "").strip()
            if not prev or len(prev) < KISACA_ANLAT_SHORT_THRESHOLD:
                out_short = "Zaten kısa söyledim."
                print(out_short)
            else:
                out_short = _shorten_previous_response(prev)
                print(out_short)
            last_response_reason[0] = "kısaca anlat dedin"
            last_action[0] = "En son önceki cevabı kısaca özetledim."
            last_response_text[0] = out_short
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        if route == "hatirla":
            note = _note_for_hatirla(last_response_text[0])
            if not note:
                print("Hatırlanacak net bir şey bulamadım.")
            else:
                last_saved = (saved_notes[0][-1:] or [""])[0]
                if note.strip() == last_saved.strip():
                    print("Zaten not ettim.")
                else:
                    saved_notes[0].append(note.strip())
                    _record_note_op(note_ops_history, "bunu hatırla")
                    print("Bunu not ettim.")
            last_response_reason[0] = "bunu hatırla dedin"
            last_action[0] = "En son hatırla işlemini yaptım."
            last_response_text[0] = "Bunu not ettim." if note else "Hatırlanacak net bir şey bulamadım."
            continue
        if route == "son_not_ne":
            if saved_notes[0]:
                print("Son not: " + saved_notes[0][-1])
            else:
                print("Henüz kayıtlı bir not yok.")
            continue
        if route == "notu_kopyala":
            if saved_notes[0]:
                _record_note_op(note_ops_history, "notu kopyala")
                print(saved_notes[0][-1])
            else:
                print("Kopyalanacak kayıtlı not yok.")
            continue
        if route == "notu_disa_aktar":
            if saved_notes[0]:
                _record_note_op(note_ops_history, "notu dışa aktar")
                print(saved_notes[0][-1])
            else:
                print("Dışa aktarılacak kayıtlı not yok.")
            continue
        if route == "notu_paylas":
            if saved_notes[0]:
                _record_note_op(note_ops_history, "notu paylaş")
                print(saved_notes[0][-1])
            else:
                print("Paylaşılacak kayıtlı not yok.")
            continue
        if route == "not_ozetle":
            if not saved_notes[0]:
                print("Özetlenecek kayıtlı not yok.")
            else:
                _record_note_op(note_ops_history, "not özetle")
                last_note = saved_notes[0][-1].strip()
                if len(last_note) <= NOT_OZETLE_SHORT_THRESHOLD:
                    print("Son not zaten yeterince kısa.")
                else:
                    short = _shorten_previous_response(last_note).strip()
                    if not short:
                        short = (last_note[:120].rsplit(maxsplit=1)[0].rstrip(".,") + ".") if len(last_note) > 120 else last_note
                    print("Kısa özet: " + short)
            continue
        if route == "notlari_goster":
            if not saved_notes[0]:
                print("Henüz kayıtlı not yok.")
            else:
                recent = saved_notes[0][-5:]
                print("Kayıtlı notlar:")
                for n in recent:
                    print("- " + n)
            continue
        if route == "etiketli_notlari_goster":
            tagged = [n for n in saved_notes[0] if n.startswith("[") and "] " in n]
            if not tagged:
                print("Henüz etiketli not yok.")
            else:
                recent_tagged = tagged[-5:]
                print("Etiketli notlar:")
                for n in recent_tagged:
                    print("- " + n)
            continue
        if route == "etikete_gore_notlari_goster":
            tag_raw = (args[0] if args else "").strip()
            if not tag_raw:
                print("Göstermek için bir etiket yazman gerekiyor.")
                continue
            tagged = [n for n in saved_notes[0] if n.startswith("[") and "] " in n]
            folded = _fold_for_search(tag_raw)
            matches = [n for n in tagged if _fold_for_search(n[1 : n.index("] ")].strip()) == folded]
            if not matches:
                print("Bu etikete sahip not bulamadım.")
            else:
                recent = matches[-5:]
                print("Eşleşen notlar:")
                for n in recent:
                    print("- " + n)
            continue
        if route == "etiketleri_goster":
            seen: set[str] = set()
            tags_ordered: list[str] = []
            for n in reversed(saved_notes[0]):
                if n.startswith("[") and "] " in n:
                    tag = n[1 : n.index("] ")].strip()
                    if tag and tag not in seen:
                        seen.add(tag)
                        tags_ordered.append(tag)
            if not tags_ordered:
                print("Henüz kayıtlı etiket yok.")
            else:
                print("Kayıtlı etiketler:")
                for t in tags_ordered:
                    print("- " + t)
            continue
        if route == "etiket_ara":
            word = (args[0] if args else "").strip()
            if not word:
                print("Aramak için bir etiket yazman gerekiyor.")
                continue
            seen_tag: set[str] = set()
            tags_ordered_etiket_ara: list[str] = []
            for n in reversed(saved_notes[0]):
                if n.startswith("[") and "] " in n:
                    tag = n[1 : n.index("] ")].strip()
                    if tag and tag not in seen_tag:
                        seen_tag.add(tag)
                        tags_ordered_etiket_ara.append(tag)
            folded = _fold_for_search(word)
            matched = [t for t in tags_ordered_etiket_ara if folded in _fold_for_search(t)]
            if not matched:
                print("Bu aramayla eşleşen etiket bulamadım.")
            else:
                print("Eşleşen etiketler:")
                for t in matched:
                    print("- " + t)
            continue
        if route == "not_gecmisi":
            if not note_ops_history[0]:
                print("Henüz kayıtlı not işlemi yok.")
            else:
                print("Son not işlemleri:")
                for op in reversed(note_ops_history[0]):
                    print("- " + op)
            continue
        if route == "notlari_temizle":
            if not saved_notes[0]:
                print("Temizlenecek kayıtlı not yok.")
            else:
                last_note_undo[0] = ("notlari_temizle", saved_notes[0][:])
                saved_notes[0].clear()
                _record_note_op(note_ops_history, "notları temizle")
                print("Kayıtlı notları temizledim.")
            continue
        if route == "notu_sil":
            if not saved_notes[0]:
                print("Silinecek kayıtlı not yok.")
            else:
                last_note_undo[0] = ("notu_sil", saved_notes[0][-1])
                saved_notes[0].pop()
                _record_note_op(note_ops_history, "notu sil")
                print("Son notu sildim.")
            continue
        if route == "notu_duzenle":
            if not saved_notes[0]:
                print("Düzenlenecek kayıtlı not yok.")
            else:
                pending_note_edit[0] = True
                print("Son notu düzenlemek için yeni kısa metni yaz.")
            continue
        if route == "notu_adlandir":
            tag_raw = (args[0] if args else "").strip()
            if not tag_raw:
                print("Etiket için kısa bir ad yazman gerekiyor.")
                continue
            if not saved_notes[0]:
                print("Etiketlenecek kayıtlı not yok.")
                continue
            tag = tag_raw
            if len(tag) > NOT_ADLANDIR_MAX_TAG_LEN:
                tag = tag[:NOT_ADLANDIR_MAX_TAG_LEN].strip()
            old_content = saved_notes[0][-1]
            saved_notes[0][-1] = "[" + tag + "] " + old_content
            last_note_undo[0] = ("notu_duzenle", old_content)
            _record_note_op(note_ops_history, "notu adlandır")
            print("Son notu etiketledim.")
            continue
        if route == "etiket_kaldir":
            tag_raw = (args[0] if args else "").strip()
            if not tag_raw:
                print("Kaldırmak için bir etiket yazman gerekiyor.")
                continue
            if not saved_notes[0]:
                print("Etiketi kaldıracak kayıtlı not yok.")
                continue
            last = saved_notes[0][-1]
            if not last.startswith("[") or "] " not in last:
                print("Son notta bu etiket yok.")
                continue
            idx = last.index("] ")
            tag_in_note = last[1:idx].strip()
            if _fold_for_search(tag_in_note) != _fold_for_search(tag_raw):
                print("Son notta bu etiket yok.")
                continue
            rest = last[idx + 2 :].strip()
            saved_notes[0][-1] = rest
            last_note_undo[0] = ("notu_duzenle", last)
            _record_note_op(note_ops_history, "etiket kaldır")
            print("Etiketi kaldırdım.")
            continue
        if route == "etiket_degistir":
            eski_raw = (args[0] if len(args) > 0 else "").strip()
            yeni_raw = (args[1] if len(args) > 1 else "").strip()
            if not eski_raw or not yeni_raw:
                print("Eski ve yeni etiket yazman gerekiyor.")
                continue
            if not saved_notes[0]:
                print("Etiket değiştirilecek kayıtlı not yok.")
                continue
            last = saved_notes[0][-1]
            if not last.startswith("[") or "] " not in last:
                print("Son notta bu etiket yok.")
                continue
            idx = last.index("] ")
            tag_in_note = last[1:idx].strip()
            if _fold_for_search(tag_in_note) != _fold_for_search(eski_raw):
                print("Son notta bu etiket yok.")
                continue
            yeni = yeni_raw
            if len(yeni) > NOT_ADLANDIR_MAX_TAG_LEN:
                yeni = yeni[:NOT_ADLANDIR_MAX_TAG_LEN].strip()
            rest = last[idx + 2 :].strip()
            saved_notes[0][-1] = "[" + yeni + "] " + rest
            last_note_undo[0] = ("notu_duzenle", last)
            _record_note_op(note_ops_history, "etiket değiştir")
            print("Etiketi güncelledim.")
            continue
        if route == "not_birlestir":
            if len(saved_notes[0]) < 2:
                print("Birleştirmek için en az 2 kayıtlı not gerekiyor.")
            else:
                last_two = [saved_notes[0][-2].strip(), saved_notes[0][-1].strip()]
                merged = (last_two[0] + " " + last_two[1]).strip()
                if len(merged) > 240:
                    merged = (merged[:240].rsplit(maxsplit=1)[0].rstrip(".,") + ".").strip() or merged[:240]
                saved_notes[0].append(merged)
                last_note_undo[0] = ("not_birlestir", None)
                _record_note_op(note_ops_history, "not birleştir")
                print("Son iki notu birleştirdim.")
            continue
        if route == "notu_geri_al":
            u = last_note_undo[0]
            if not u:
                print("Geri alınacak uygun bir not işlemi yok.")
            else:
                op, data = u
                if op == "notu_sil":
                    saved_notes[0].append(data)
                elif op == "notlari_temizle":
                    saved_notes[0][:] = data
                elif op == "notu_duzenle":
                    saved_notes[0][-1] = data
                elif op == "not_birlestir":
                    saved_notes[0].pop()
                last_note_undo[0] = None
                _record_note_op(note_ops_history, "notu geri al")
                print("Son not işlemini geri aldım.")
            continue
        if route == "kac_not_var":
            n = len(saved_notes[0])
            if n == 0:
                print("Kayıtlı not yok.")
            else:
                print(f"{n} kayıtlı not var.")
            continue
        if route == "not_ara":
            word = (args[0] if args else "").strip()
            if not word:
                print("Aramak için bir kelime yazman gerekiyor.")
                continue
            _record_note_op(note_ops_history, "not ara")
            folded = _fold_for_search(word)
            matches = [n for n in saved_notes[0] if folded in _fold_for_search(n)]
            if not matches:
                print("Bu aramayla eşleşen not bulamadım.")
            else:
                recent = matches[-5:]
                print("Eşleşen notlar:")
                for n in recent:
                    print("- " + n)
            continue
        if route == "etiketli_not_ara":
            word = (args[0] if args else "").strip()
            if not word:
                print("Aramak için bir kelime yazman gerekiyor.")
                continue
            tagged = [n for n in saved_notes[0] if n.startswith("[") and "] " in n]
            folded = _fold_for_search(word)
            matches = [n for n in tagged if folded in _fold_for_search(n)]
            if not matches:
                print("Bu aramayla eşleşen etiketli not bulamadım.")
            else:
                print("Eşleşen etiketli notlar:")
                for n in matches:
                    print("- " + n)
            continue
        if route == "ne_yapiyorsun":
            if current_task[0]:
                txt = "Şu an " + current_task[0]
                print(txt)
                last_response_reason[0] = current_task[0]
            else:
                txt = "Şu an aktif bir görevim yok."
                print(txt)
                last_response_reason[0] = "aktif görev yoktu"
            last_response_text[0] = txt
            continue
        if route == "son_yaptigin_ne":
            if last_action[0]:
                print(last_action[0])
                last_response_reason[0] = last_action[0]
                last_response_text[0] = last_action[0]
            else:
                txt = "Henüz kayda değer bir işlem yapmadım."
                print(txt)
                last_response_reason[0] = "henüz işlem yoktu"
                last_response_text[0] = txt
            continue
        if route == "bugun_ne_yaptin":
            if today_date[0] != date.today().isoformat():
                today_date[0] = date.today().isoformat()
                today_actions[0] = []
            if not today_actions[0]:
                txt = "Bugün kayda değer bir işlem yapmadım."
                print(txt)
                last_response_reason[0] = "bugün işlem yoktu"
                last_response_text[0] = txt
            else:
                items = today_actions[0][-5:]  # en fazla 5 madde, en son yapılanlar
                lines = ["Bugün şunları yaptım:"] + ["- " + _format_today_bullet(a) for a in items]
                txt = "\n".join(lines)
                print(txt)
                last_response_reason[0] = "bugünkü işlere baktım"
                last_response_text[0] = txt
            continue
        if route == "unknown":
            last_response_reason[0] = None
            last_response_text[0] = None
            print(UNKNOWN_CMD_TEXT)
            continue
        if route == "exit":
            print("OK")
            break
        if route == "durum":
            current_task[0] = "durum çıktısını hazırlıyorum."
            try:
                snap = state.snapshot(base_dir=base_dir, log_path=Path.cwd() / ".lumos" / "log.txt")
                parts = get_durum_parts(Path(base_dir), ks.is_initialized(), engine.pl)
                durum_txt = format_durum(snap, parts["consent_ok"], parts["lock_ok"], parts["durum_label"], parts["not_line"])
                print(durum_txt)
                last_response_reason[0] = parts.get("not_line") or parts.get("durum_label", "")
                last_action[0] = "En son durum özetini gösterdim."
                last_response_text[0] = durum_txt
                _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "hazir":
            current_task[0] = "açılış sağlık özetini doğruluyorum."
            try:
                summary = get_startup_summary(Path(base_dir), not state.is_locked(), pl)
                print(summary)
                last_response_reason[0] = summary
                last_action[0] = "En son hazır olma özetini verdim."
                last_response_text[0] = summary
                _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "kilit":
            current_task[0] = "kilit menüsündeyim."
            try:
                result = lock_menu(state=state, engine=engine, initial_cmd=args[0] if args else None)
                if result is not None:
                    pending = result
                else:
                    last_action[0] = "En son kilit menüsünü açtım."
                    _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "kamera":
            current_task[0] = "kamera menüsündeyim."
            try:
                result = presence_menu(state=state, engine=engine, base_dir=base_dir, initial_cmd=args[0] if args else None)
                if result is not None:
                    pending = result
                else:
                    last_action[0] = "En son kamera menüsünü açtım."
                    _record_today_action(today_date, today_actions, last_action[0])
            finally:
                current_task[0] = None
            continue
        if route == "alias":
            alias_menu(args=args)
            last_action[0] = "En son alias işlemi yaptım."
            _record_today_action(today_date, today_actions, last_action[0])
            continue
        print(UNKNOWN_CMD_TEXT)

if __name__ == "__main__":
    main()
