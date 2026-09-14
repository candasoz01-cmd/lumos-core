"""Saklama politikasının METİN KATMANINA çevrildiği yer (kurucu kararları).

Karar zinciri:
- 2026-08-24 (kalem 1-2): sebep/durum alanları SÜREKLİ işletimsel kayıttır;
  kaynak/çeviri metni DIAGNOSTIC katmandır.
- 2026-08-25 (kapanış şartı 2): `zero` saklama YEREL metni de kapsar.

Sıfır saklamada GARANTİ EDİLEN:
- kaynak/çeviri düz metni kalıcı hâle GETİRİLMEZ (jsonl'e yazılmaz),
- düz metin konsol/log/markdown çıktısına BASILMAZ,
- jsonl satırında metin alanları boş kalır + `text_state="not_persisted"`,
- sebep, teslim durumu, yön ve zamanlama olduğu gibi kalır.

GARANTİNİN DIŞINDA: işlem sırasında bellekte GEÇİCİ olarak bulunan düz metin.
STT çıktısı, çeviri istemi ve çeviri sonucu süreç belleğinde düz metindir ve
sağlayıcıya düz metin olarak gider; bu katman kalıcılığı ve çıktıyı yönetir,
belleği değil.

Bu modül politikayı TEK yerde metin katmanına çevirir. Rig'ler hem kaydı hem
ekranı aynı `TextLayer` nesnesinden geçirir — birini redakte edip diğerini
unutma yolu kapalıdır.

Kapsam notu: kapalı provanın 24 saatlik metin penceresinin İŞLETİLMESİ
(süresi dolanı silme + zamanlayıcı) bu dilimde YOKTUR; ayrı bir iş olarak
duruyor. Yani `rehearsal` politikasında metin şu an süresiz yaşar.
"""

from __future__ import annotations

from representative.meeting_ingress import (
    REAL_MEETING_RETENTION,
    REHEARSAL_RETENTION,
    RetentionPolicy,
)
from representative.pipeline import TextLayer

POLICIES = {"rehearsal": REHEARSAL_RETENTION, "real-meeting": REAL_MEETING_RETENTION}


def text_layer_for(policy: RetentionPolicy) -> TextLayer:
    """Politikadan metin katmanı: `zero` → metin hiç yazılmaz (kayıt ve konsol).

    Sağlayıcı medyasını yöneten politika nesnesinin AYNISI yerel metni de
    yönetir; ikinci bir politika tanımlamak ikinci bir saklama yolu demek olurdu.
    """
    if not isinstance(policy, RetentionPolicy):
        raise ValueError("policy must be an explicit RetentionPolicy")
    return TextLayer(persists=policy.kind != "zero")
