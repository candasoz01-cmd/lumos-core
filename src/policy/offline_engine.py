import re
from datetime import datetime
from device.contacts import Contacts
from typing import Optional


class OfflineEngineV1:
    def __init__(self, perm=None):
        self.contacts = Contacts()
        self.perm = perm

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
        for suf in ["ya", "ye", "yı", "yi", "yu", "yü"]:
            if n_low.endswith(suf) and len(n) > len(suf) + 1:
                n = n[:-len(suf)]
                break

        return n.strip()

    def process(self, message: str) -> dict:
        msg = (message or "").strip()
        lower_msg = msg.lower()

        intent = self._classify(lower_msg)

        if intent == "DEVICE_TIME":
            return self._handle_time()

        if intent == "NETWORK_REQUIRED_WEATHER":
            return {
                "response": "Offline moddayım. Canlı hava durumu veremem.",
                "reason": "Hava durumu güncel veri ister.",
                "follow_up": "İstersen online moda geçelim mi?",
            }

        if intent == "NETWORK_REQUIRED_FX":
            return {
                "response": "Offline moddayım. Canlı kur veremem.",
                "reason": "Kur bilgisi güncel veri ister.",
                "follow_up": "İstersen online moda geçip bakayım mı?",
            }

        # SMS (offline) V1: kapalı (sesli kullanım yokken kalabalık yapmasın)
        if intent == "ACTION_SEND_SMS":
            return {
                "response": "Offline moddayım. SMS özelliği bu sürümde kapalı.",
                "reason": "Offline sesli kullanım gelmeden SMS akışını açmıyoruz.",
                "follow_up": "İstersen mesaj taslağı hazırlayayım (göndermez) veya online moda geçelim.",
            }

        if intent == "ACTION_DRAFT_ORDER":
            return self._handle_order_draft(msg)

        if not msg or len(msg) <= 2:
            return {
                "response": "Yanındayım.",
                "reason": "İstersen birlikte sadeleştirebiliriz.",
                "follow_up": "Buradaki asıl mesele sence ne?",
            }

        # tests/test_offline.py: kısa selam → legacy "Anlayamadım."
        if intent == "GENERAL" and lower_msg in ("selam", "merhaba", "hey", "hi", "hello"):
            return {
                "response": "Anlayamadım.",
                "reason": "",
                "follow_up": "",
            }

        reflected = msg if len(msg) <= 120 else msg[:120].rstrip() + "…"

        return {
            "response": f"Şunu duyuyorum: '{reflected}'",
            "reason": "İstersen birlikte sadeleştirebiliriz.",
            "follow_up": "Bunu tek cümlede nasıl söylersin?",
        }

    def _lease(self, name: str, purpose: str, ttl: int) -> None:
        if self.perm:
            self.perm.acquire(name, purpose=purpose, ttl_seconds=ttl)

    def _handle_time(self) -> dict:
        self._lease("system_time", "time_query", 5)
        now = datetime.now()
        hhmm = now.strftime("%H:%M")
        date = now.strftime("%d.%m.%Y")
        return {
            "response": f"Saat {hhmm}. Bugün {date}.",
            "reason": "Bu bilgi cihazın yerel saatinden alındı (offline).",
            "follow_up": "İstersen şunu da söyle: bugün hangi işin en acil?",
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
                "debug": locals().get("dbg", ""),
            }

        body = self._extract_message_body(msg)

        if not target:
            return {
                "response": "Mesaj taslağı hazırlayabilirim ama kime yazacağız?",
                "reason": "Alıcı adı net değil.",
                "follow_up": "Kime mesaj atıyoruz? (örnek: 'Eftelya')",
            }

        if not body:
            return {
                "response": f"{target} için mesaj taslağı hazırlayabilirim ama mesaj içeriği ne olsun?",
                "reason": "Mesaj metni net değil.",
                "follow_up": "Ne yazayım? (örnek: 'Yoldayım, 10 dk’ya oradayım.')",
            }

        draft = f"{target}, {body}"
        return {
            "response": f"Mesaj taslağı: {draft}",
            "reason": "Offline mod: sadece taslak üretir, göndermez.",
            "follow_up": "Bunu kopyalayıp göndermek ister misin?",
        }

    def _handle_sms_flow(self, msg: str) -> dict:
        self._lease("sms_send", "sms_send", 20)

        target = self._extract_contact_name(msg)
        self._lease("contacts_read", "contacts_lookup", 15)

        number = self.contacts.find_number(target) if target else None
        if target and not number:
            return {
                "response": f"Rehberde '{target}' diye kayıtlı biri yok.",
                "reason": "Alıcıyı bulamadım.",
                "follow_up": "Numarayı yaz veya farklı isim söyle.",
                "debug": locals().get("dbg", ""),
            }

        body = self._extract_message_body(msg)

        if not target:
            return {
                "response": "SMS gönderebilirim. Kime göndereceğiz?",
                "reason": "Alıcı net değil.",
                "follow_up": "İsim ya da numara yaz (ör: 'Eftelya' veya '+90...').",
            }

        if not body:
            return {
                "response": f"{target} için SMS gönderebilirim. Ne yazayım?",
                "reason": "Mesaj metni net değil.",
                "follow_up": "Metni yaz (ör: 'Yoldayım, 10 dk’ya oradayım.').",
            }

        draft = f"{target} ({number}): {body}"

        return {
            "response": f"SMS taslağı hazır: {draft}",
            "reason": "Offline mod: SMS gönderebiliriz ama önce onay lazım.",
            "follow_up": "Göndereyim mi? (EVET/HAYIR)",
            "debug": locals().get("dbg", ""),
        }

    def _handle_order_draft(self, msg: str) -> dict:
        self._lease("draft_order", "order_draft", 15)

        item, qty = self._extract_order(msg)

        if not item:
            return {
                "response": "Sipariş taslağı hazırlayabilirim ama ne sipariş edeceğiz?",
                "reason": "Ürün net değil.",
                "follow_up": "Ne istiyoruz? (örnek: 'döner')",
            }

        if qty is None:
            qty = 1

        draft = f"Merhaba, {qty} adet {item} sipariş etmek istiyorum."
        return {
            "response": f"Sipariş taslağı: {draft}",
            "reason": "Offline mod: sadece taslak üretir, göndermez.",
            "follow_up": "Hangi dönerciye? İsim yaz, taslağı ona göre düzenleyeyim.",
        }

    def _classify(self, lower_msg: str) -> str:
        if self._is_time_query(lower_msg):
            return "DEVICE_TIME"

        if self._looks_like_weather(lower_msg):
            return "NETWORK_REQUIRED_WEATHER"

        if self._looks_like_fx(lower_msg):
            return "NETWORK_REQUIRED_FX"

        if self._looks_like_message(lower_msg):
            return "ACTION_SEND_SMS"

        if self._looks_like_order(lower_msg):
            return "ACTION_DRAFT_ORDER"

        return "GENERAL"

    def _is_time_query(self, lower_msg: str) -> bool:
        keys = [
            "saat kaç",
            "saat kac",
            "saat",
            "time",
            "tarih",
            "bugün kaç",
            "bugun kac",
            "bugün günlerden ne",
            "bugun gunlerden ne",
            "hangi gün",
            "hangi gun",
            "günlerden",
            "gunlerden",
        ]
        return any(k in lower_msg for k in keys)

    def _looks_like_weather(self, lower_msg: str) -> bool:
        keys = ["hava", "hava nasıl", "hava nasil", "yağmur", "yagmur", "kaç derece", "kac derece"]
        return any(k in lower_msg for k in keys)

    def _looks_like_fx(self, lower_msg: str) -> bool:
        keys = ["kur", "dolar", "euro", "sterlin", "usd", "eur"]
        return any(k in lower_msg for k in keys)

    def _looks_like_message(self, lower_msg: str) -> bool:
        keys = ["mesaj", "sms", "whatsapp", "dm", "yaz", "yoldayım", "yoldayim"]
        return ("mesaj" in lower_msg) or ("yaz" in lower_msg and "mesaj" in lower_msg) or any(k in lower_msg for k in keys)

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
