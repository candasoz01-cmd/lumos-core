"""Provider-independent meeting ingress + Recall.ai implementation (Faz 0).

Sözleşme (karar tablosu, 2026-08-12 kurucu şartları):
- Mimari sağlayıcıdan bağımsız `MeetingIngress` arayüzünün arkasında kalır;
  Recall.ai ilk gerçekleme, Attendee yedek aday.
- FAIL-CLOSED RETENTION: retention açıkça verilmeden bot İSTEĞİ OLUŞMAZ.
  Kapalı prova = timed/24h (teşhis penceresi, iş bitince erken explicit
  delete); gerçek dış toplantı = zero (null). Varsayılana düşme yolu YOK.
- Recall transkripsiyonu ASLA etkinleştirilmez (transcript bizde üretilir);
  custom metadata'ya yalnız opak iç ID yazılır (Recall'da kalıcı kalır);
  meeting URL'nin Recall'da kalıcı iz bıraktığı kabul edilmiş kalıntıdır.
- İfşa ilkesi (ADR-023): bot toplantıya kendini tanıtarak girer.

Dürüstlük notu: HTTP uçlarının/alan adlarının kesin şekli ilk CANLI çağrıda
doğrulanır (docs.recall.ai); birim testler yük (payload) kurallarını ve
fail-closed davranışı sabitler, ağı değil.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

# TR metni V1'de SESLENDİRİLMEZ; yazılı kanal geldiğinde oraya gider.
# Sesli beyan tek akış ve yalnız İngilizce (kurucu kararı 2026-08-20).
DISCLOSURE_LINE_TR = (
    "Merhaba, ben Lumos — kurucu Candaş Öz'ün yetkili yapay zekâ temsilcisiyim. "
    "Bu görüşmede çeviri yapacağım, bir tutanak tutulacak ve gördüğünüz görüntü "
    "kamera değil, üretilmiş bir göstergedir."
)
DISCLOSURE_LINE_EN = (
    "Hello, I am Lumos, the authorized AI representative of founder Candaş Öz. "
    "I will interpret in this meeting, a transcript is being kept, and my video "
    "is a generated indicator, not a camera."
)


@dataclass(frozen=True)
class RetentionPolicy:
    """Explicit retention — no default exists anywhere on purpose."""

    kind: str  # "zero" | "timed"
    hours: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("zero", "timed"):
            raise ValueError("retention kind must be 'zero' or 'timed'")
        if self.kind == "timed" and (self.hours is None or self.hours <= 0):
            raise ValueError("timed retention requires positive hours")
        if self.kind == "zero" and self.hours is not None:
            raise ValueError("zero retention takes no hours")

    def to_recall(self) -> dict[str, Any] | None:
        if self.kind == "zero":
            return None
        return {"type": "timed", "hours": self.hours}


REHEARSAL_RETENTION = RetentionPolicy(kind="timed", hours=24)
REAL_MEETING_RETENTION = RetentionPolicy(kind="zero")


class MeetingIngress(Protocol):
    """Provider-independent surface the interpreter core plugs into."""

    def join(self, meeting_url: str) -> str: ...  # returns session/bot id
    def speak(self, session_id: str, mp3_b64: str) -> None: ...
    def show_avatar(self, session_id: str, jpeg_b64: str) -> None: ...
    def kill(self, session_id: str) -> None: ...
    def delete_media(self, session_id: str) -> None: ...


def build_recall_bot_payload(
    meeting_url: str,
    retention: RetentionPolicy,
    internal_ref: str,
    bot_name: str = "Lumos · AI Representative",
    disclosure_mp3_b64: str | None = None,
    avatar_idle_jpeg_b64: str | None = None,
) -> dict[str, Any]:
    """Pure payload builder — unit tests pin the founder's rules here.

    - retention zorunlu parametre (imza düzeyinde fail-closed)
    - yalnız Google Meet URL kabul (Faz 0 tek platform)
    - transcription anahtarı payload'da HİÇ yer almaz
    - metadata yalnız opak iç referans taşır
    """
    if not isinstance(retention, RetentionPolicy):
        raise ValueError("retention must be an explicit RetentionPolicy")
    if "meet.google.com/" not in meeting_url:
        raise ValueError("Faz 0 covers Google Meet URLs only")
    if not internal_ref or "/" in internal_ref or " " in internal_ref:
        raise ValueError("internal_ref must be a single opaque token")
    payload: dict[str, Any] = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
        "recording_config": {"retention": retention.to_recall()},
        "metadata": {"lumos_ref": internal_ref},
    }
    if disclosure_mp3_b64:
        # Output Audio ucunun ön koşulu + girişte otomatik ifşa klibi
        # (prova 2 canlı doğrulaması: boş b64 400 döner — alan ancak gerçek
        # klip varsa gönderilir)
        payload["automatic_audio_output"] = {
            "in_call_recording": {"data": {"kind": "mp3", "b64_data": disclosure_mp3_b64}}
        }
    if avatar_idle_jpeg_b64:
        idle = {"kind": "jpeg", "b64_data": avatar_idle_jpeg_b64}
        payload["automatic_video_output"] = {
            "in_call_not_recording": dict(idle),
            "in_call_recording": dict(idle),
        }
    assert "transcription" not in json.dumps(payload).lower()
    return payload


class RecallMeetingIngress:
    """Recall.ai implementation. Ağ şekilleri ilk canlı çağrıda doğrulanır."""

    def __init__(
        self,
        retention: RetentionPolicy,
        region_base_url: str,
        api_key: str | None = None,
    ) -> None:
        self._retention = retention
        self._base = region_base_url.rstrip("/")
        key = api_key if api_key is not None else os.environ.get("RECALL_API_KEY", "")
        if not key:
            raise ValueError("RECALL_API_KEY missing — anahtar env'e yerleştirilmeli")
        self._key = key

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        req = urllib.request.Request(
            f"{self._base}{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Token {self._key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode() or "{}"
        return json.loads(raw)

    def join(self, meeting_url: str, internal_ref: str = "faz0-prova") -> str:
        payload = build_recall_bot_payload(meeting_url, self._retention, internal_ref)
        result = self._request("POST", "/api/v1/bot/", payload)
        return str(result["id"])

    def speak(self, session_id: str, mp3_b64: str) -> None:
        self._request(
            "POST", f"/api/v1/bot/{session_id}/output_audio/", {"kind": "mp3", "b64_data": mp3_b64}
        )

    def show_avatar(self, session_id: str, jpeg_b64: str) -> None:
        self._request(
            "POST",
            f"/api/v1/bot/{session_id}/output_video/",
            {"kind": "jpeg", "b64_data": jpeg_b64},
        )

    def kill(self, session_id: str) -> None:
        """Kill-switch: bot toplantıdan çıkarılır (ADR-023: yetkinin üstünde)."""
        self._request("POST", f"/api/v1/bot/{session_id}/leave_call/", {})

    def delete_media(self, session_id: str) -> None:
        """Prova sonrası erken explicit silme (kurucu şartı 1, 2026-08-12)."""
        self._request("POST", f"/api/v1/bot/{session_id}/delete_media/", {})
