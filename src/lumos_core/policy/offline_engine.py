import re
from datetime import datetime
from getpass import getpass
from lumos_core.device.contacts import Contacts
from typing import Optional

class OfflineEngineV1:
    FEATURE_ORDER = False
    FEATURE_SMS = False

    def __init__(self, perm=None, unlock_cb=None, lock_cb=None, lock_status_cb=None):
        self.contacts = Contacts()
        self.perm = perm
        self.unlock_cb = unlock_cb
        self.lock_cb = lock_cb
        self.lock_status_cb = lock_status_cb

    def _normalize_contact_name(self, name: str) -> str:
        if not name:
            return name
        n = name.strip()

        # tırnak/noktalama temizle
        n = n.strip(" \"'“”‘’.,:;!?()[]{}")

        # Eftelya'ya / Eftelyaya / Eftelya ya -> Eftelya
        # önce apostrofla ayrılmış ekleri at
        n = re.sub(r"[’'](ya|ye|yı|yi|yu|yü)\b", "", n, flags=re.IGNORECASE)

        # sonra bitişik ekleri at (çok agresif olmasın diye sadece bu 6 ek)
        n_low = n.lower()
        for suf in ["ya","ye","yı","yi","yu","yü"]:
            if n_low.endswith(suf) and len(n) > len(suf) + 1:
                n = n[:-len(suf)]
                break

        return n.strip()



    def process(self, message: str) -> dict:
        msg = (message or "").strip()
        lower_msg = msg.lower()

        intent = self._classify(lower_msg)

        # Kilit komutları (offline)
        if lower_msg in ["kilit", "kilit durumu", "kilit?","lock","lock status"]:
            if self.lock_status_cb:
                st = self.lock_status_cb()  # dict
                return {"response": st.get("response","UNKNOWN"), "reason": "", "follow_up": ""}
            return {"response": "Kilit durumu bağlı değil.", "reason": "", "follow_up": ""}

        if lower_msg in ["kilidi aç", "kilit aç", "unlock", "kilitac", "kilit açar mısın"]:
            if not self.unlock_cb:
                return {"response": "Kilit sistemi bağlı değil.", "reason": "", "follow_up": ""}
            try:
                pw = getpass("Lumos passphrase: ")
            except Exception:
                pw = ""
            ok, msg = self.unlock_cb(pw)
            return {"response": "OK" if ok else "FAIL", "reason": "", "follow_up": ""}

        if lower_msg in ["kilidi kapat", "kilit kapat", "lock", "kilitkapat"]:
            if self.lock_cb:
                self.lock_cb()
                return {"response": "OK", "reason": "", "follow_up": ""}
            return {"response": "Kilit sistemi bağlı değil.", "reason": "", "follow_up": ""}



        if any(w in lower_msg for w in ["dün", "dun", "yarın", "yarin"]):
            return {
                "response": "Bunu offline modda hesaplamıyorum.",
                "reason": "Şu an sadece bugünün tarih/saat bilgisini veriyorum.",
                "follow_up": "Bugün için: saat / tarih / günlerden"
            }

        if "online" in lower_msg and ("geç" in lower_msg or "gec" in lower_msg or "aç" in lower_msg or "ac" in lower_msg):
            return {
                "response": "Bu oturum offline. Buradan online moda geçemem.",
                "reason": "Mod başlangıçta seçiliyor.",
                "follow_up": "Online için: LUMOS_MODE=online python3 main.py"
            }

        if intent == "DEVICE_TIME":
            return self._handle_time()

        if intent == "PERM_STATUS":
            return self._handle_perm_status()


        if intent == "NETWORK_REQUIRED_WEATHER":
            return {
                "response": "Offline moddayım. Canlı hava durumu veremem.",
                "reason": "Hava durumu güncel veri ister.",
                "follow_up": "İstersen online moda geçelim mi?"
            }

        if intent == "NETWORK_REQUIRED_FX":
            return {
                "response": "Offline moddayım. Canlı kur veremem.",
                "reason": "Kur bilgisi güncel veri ister.",
                "follow_up": "İstersen online moda geçip bakayım mı?"
            }

        # SMS (offline) V1: kapalı (sesli kullanım yokken kalabalık yapmasın)
        if intent == "ACTION_SEND_SMS":
            return {
                "response": "Offline moddayım. SMS özelliği bu sürümde kapalı.",
                "reason": "Offline sesli kullanım gelmeden SMS akışını açmıyoruz.",
                "follow_up": "İstersen mesaj taslağı hazırlayayım (göndermez) veya online moda geçelim."
            }


        if intent == "ACTION_DRAFT_ORDER":
            return self._handle_order_draft(msg)

        if not msg or len(msg) <= 2:
            return {
            "response": "Anlayamadım.",
            "reason": "Offline modda sınırlı komutlar var.",
            "follow_up": "İstersen şunları deneyelim: saat / izinler"

            }

        return {
            "response": "Anlayamadım.",
            "reason": "Offline modda sınırlı komutlar var.",
            "follow_up": "İstersen şunları deneyelim: saat / izinler"
        }

    def _lease(self, name: str, purpose: str, ttl: int) -> None:
        if self.perm:
            self.perm.acquire(name, purpose=purpose, ttl_seconds=ttl)

    def _handle_time(self) -> dict:
        self._lease("system_time", "time_query", 5)
        now = datetime.now()
        hhmm = now.strftime("%H:%M")
        date = now.strftime("%d.%m.%Y")
        weekday_en = now.strftime("%A")
        weekday_tr = {
            "Monday":"Pazartesi","Tuesday":"Salı","Wednesday":"Çarşamba","Thursday":"Perşembe",
            "Friday":"Cuma","Saturday":"Cumartesi","Sunday":"Pazar"
        }.get(weekday_en, weekday_en)
        return {
            "response": f"Saat {hhmm}. Bugün {date} ({weekday_tr}).",
            "reason": "Bu bilgi cihazın yerel saatinden alındı (offline).",
            "follow_up": ""
        }

    def _handle_message_draft(self, msg: str) -> dict:
        self._lease("draft_message", "message_draft", 15)

        target = self._extract_contact_name(msg)
        target = self._normalize_contact_name(target) if target else target
        self._lease("contacts_read", "contacts_lookup", 15)

        number = self.contacts.find_number(target) if target else None
        if target and not number:
            return {
                "response": f"Rehberde '{target}' diye kayıtlı biri yok.",
                "reason": "Alıcıyı bulamadım.",
                "follow_up": "Numarayı yaz veya farklı isim söyle.",
                "debug": locals().get("dbg","")
            }

        body = self._extract_message_body(msg)

        if not target:
            return {
                "response": "Mesaj taslağı hazırlayabilirim ama kime yazacağız?",
                "reason": "Alıcı adı net değil.",
                "follow_up": "Kime mesaj atıyoruz? (örnek: 'Eftelya')"
            }

        if not body:
            return {
                "response": f"{target} için mesaj taslağı hazırlayabilirim ama mesaj içeriği ne olsun?",
                "reason": "Mesaj metni net değil.",
                "follow_up": "Ne yazayım? (örnek: 'Yoldayım, 10 dk’ya oradayım.')"
            }

        draft = f"{target}, {body}"
        return {
            "response": f"Mesaj taslağı: {draft}",
            "reason": "Offline mod: sadece taslak üretir, göndermez.",
            "follow_up": "Bunu kopyalayıp göndermek ister misin?"
        }


    def _handle_sms_flow(self, msg: str) -> dict:
        # Offline modda tek mesaj kanalı: SMS varsay
        self._lease("sms_send", "sms_send", 20)

        target = self._extract_contact_name(msg)
        self._lease("contacts_read", "contacts_lookup", 15)

        number = self.contacts.find_number(target) if target else None
        if target and not number:
            return {
                "response": f"Rehberde '{target}' diye kayıtlı biri yok.",
                "reason": "Alıcıyı bulamadım.",
                "follow_up": "Numarayı yaz veya farklı isim söyle.",
                "debug": locals().get("dbg","")
            }

        body = self._extract_message_body(msg)

        if not target:
            return {
                "response": "SMS gönderebilirim. Kime göndereceğiz?",
                "reason": "Alıcı net değil.",
                "follow_up": "İsim ya da numara yaz (ör: 'Eftelya' veya '+90...')."
            }

        if not body:
            return {
                "response": f"{target} için SMS gönderebilirim. Ne yazayım?",
                "reason": "Mesaj metni net değil.",
                "follow_up": "Metni yaz (ör: 'Yoldayım, 10 dk’ya oradayım.')."
            }

        draft = f"{target} ({number}): {body}"

        dbg = f"TARGET={target!r} | NUMBER={number!r}"
        return {
            "response": f"SMS taslağı hazır: {draft}",
            "reason": "Offline mod: SMS gönderebiliriz ama önce onay lazım.",
            "follow_up": "Göndereyim mi? (EVET/HAYIR)",
            "debug": locals().get("dbg","")
        }

    def _handle_order_draft(self, msg: str) -> dict:
        self._lease("draft_order", "order_draft", 15)

        item, qty = self._extract_order(msg)

        if not item:
            return {
                "response": "Sipariş taslağı hazırlayabilirim ama ne sipariş edeceğiz?",
                "reason": "Ürün net değil.",
                "follow_up": "Ne istiyoruz? (örnek: 'döner')"
            }

        if qty is None:
            qty = 1

        draft = f"Merhaba, {qty} adet {item} sipariş etmek istiyorum."
        return {
            "response": f"Sipariş taslağı: {draft}",
            "reason": "Offline mod: sadece taslak üretir, göndermez.",
            "follow_up": "Hangi dönerciye? İsim yaz, taslağı ona göre düzenleyeyim."
        }

    def _classify(self, lower_msg: str) -> str:
        if self._is_time_query(lower_msg):
            return "DEVICE_TIME"

        if self._looks_like_perm_status(lower_msg):
            return "PERM_STATUS"

        if self._looks_like_weather(lower_msg):
            return "NETWORK_REQUIRED_WEATHER"

        if self._looks_like_fx(lower_msg):
            return "NETWORK_REQUIRED_FX"


        if self.FEATURE_SMS and self._looks_like_message(lower_msg):
            return "ACTION_SEND_SMS"

        if self.FEATURE_ORDER and self._looks_like_order(lower_msg):
            return "ACTION_DRAFT_ORDER"

        return "GENERAL"

    def _is_time_query(self, lower_msg: str) -> bool:
        keys = [
            "saat kaç", "saat kac", "saat", "time", "zaman",
            "tarih", "bugün kaç", "bugun kac", "bugün günlerden ne", "bugun gunlerden ne",
            "hangi gün", "hangi gun", "günlerden", "gunlerden"
            "ayın kaçı", "ayin kaci", "ayın kaç", "ayin kac",
            "ay kaç", "ay kac", "bugün ayın kaçı", "bugun ayin kaci",
            "günlerden ney", "gunlerden ney",
        ]
        return any(k in lower_msg for k in keys)

    def _looks_like_weather(self, lower_msg: str) -> bool:
        keys = ["hava", "hava nasıl", "hava nasil", "yağmur", "yagmur", "kaç derece", "kac derece"]
        return any(k in lower_msg for k in keys)

    def _looks_like_fx(self, lower_msg: str) -> bool:
        keys = ["kur", "dolar", "euro", "sterlin", "usd", "eur"]
        return any(k in lower_msg for k in keys)

    def _looks_like_message(self, lower_msg: str) -> bool:
        # 'yaz' kelimesi tek başına mesaj değildir (örn: 'ben kendim yazarım')
        # Mesaj niyeti için daha net işaretler arayalım.
        keys = ["mesaj", "sms", "whatsapp", "dm"]
        if any(k in lower_msg for k in keys):
            return True

        # açık kalıplar
        patterns = [
            "mesaj yaz", "sms at", "whatsapp yaz",
            "x'e mesaj", "mesaj at", "dm at"
        ]
        return any(p in lower_msg for p in patterns)

    def _looks_like_order(self, lower_msg: str) -> bool:
        keys = ["sipariş", "siparis", "döner", "doner", "pizza", "burger", "iki", "1", "2", "3", "adet"]
        return ("sipariş" in lower_msg) or ("siparis" in lower_msg) or ("döner" in lower_msg) or ("doner" in lower_msg) or any(k in lower_msg for k in keys)

    def _extract_contact_name(self, msg: str) -> Optional[str]:
        lower = msg.lower()
        if "eftelya" in lower:
            return "Eftelya"
        tokens = msg.split()
        if len(tokens) >= 2 and tokens[0].lower() in ["mesaj", "yaz", "mesajı", "mesaji"]:
            return tokens[1].strip(" ,.")
        return None

    def _extract_message_body(self, msg: str) -> Optional[str]:
        lower = msg.lower()
        if "yoldayım" in lower:
            return "yoldayım."
        if "yoldayim" in lower:
            return "yoldayım."
        if "diye" in lower:
            parts = msg.split("diye", 1)
            tail = parts[1].strip(" :,-.")
            if tail:
                return tail
        return None

    def _extract_order(self, msg: str):
        lower = msg.lower()
        qty = None
        if "iki" in lower or "2" in lower:
            qty = 2
        elif "üç" in lower or "uc" in lower or "3" in lower:
            qty = 3
        elif "bir" in lower or "1" in lower:
            qty = 1

        item = None
        if "döner" in lower or "doner" in lower:
            item = "döner"
        elif "pizza" in lower:
            item = "pizza"
        elif "burger" in lower:
            item = "burger"

        return item, qty

    def _looks_like_perm_status(self, lower_msg: str) -> bool:
        keys = ["güvenlik", "guvenlik", "izin", "yetki", "permission", "perm", "haklar", "erişim", "erisim"]
        return any(k in lower_msg for k in keys)

    def _handle_perm_status(self) -> dict:

        if not self.perm:
            return {
                "response": "Şu an izin sistemine bağlı değilim.",
                "reason": "PermissionManager engine’e bağlanmamış.",
                "follow_up": "Bu normal değil; main.py tarafını kontrol etmek lazım."
            }

        snap = self.perm.snapshot()
        active = snap.get("active", {}) or {}

        if not active:
            return {
                "response": "Şu an aktif erişim yok.",
                "reason": "Kısa süreli erişimler (lease) iş bitince otomatik kapanır.",
                "follow_up": ""
            }

        parts = []
        for name, meta in active.items():
            rem = meta.get("remaining_seconds")
            rem_txt = f"{rem}s" if rem is not None else "süresiz"
            purpose = meta.get("purpose") or ""
            if purpose:
                parts.append(f"- {name} ({purpose}) · {rem_txt}")
            else:
                parts.append(f"- {name} · {rem_txt}")

        return {
            "response": "Aktif erişimler:\n" + "\n".join(parts),
            "reason": "Bu, çekirdek içi kısa süreli erişim kaydıdır (OS izni değil).",
            "follow_up": ""
        }
    def _looks_like_small_talk(self, lower_msg: str) -> bool:
        keys = [
            "tamam", "ok", "oke", "eyvallah", "sağ ol", "sag ol", "teşekkür", "tesekkur",
            "güzel", "guzel", "kanki", ":)", "😀", "😄",
            "çok sade", "cok sade", "fazla sade", "çok kısa", "cok kisa"
        ]
        return any(k in lower_msg for k in keys)

    def _handle_small_talk(self, msg: str) -> dict:
        low = (msg or "").lower()

        if "çok sade" in low or "cok sade" in low or "fazla sade" in low or "çok kısa" in low or "cok kisa" in low:
            return {
                "response": "Anladım. Çok uzatmadan biraz daha açıklayıcı konuşabilirim.",
                "reason": "",
                "follow_up": "Ne yapmak istiyorsun? (saat / izinler / sipariş)"
            }

        # kısa, sıcak onay
        return {
            "response": "Tamam 🙂",
            "reason": "",
            "follow_up": ""
        }
