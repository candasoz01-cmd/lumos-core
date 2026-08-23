"""Canlı iki dilli transkriptin okunabilir terminal biçimi (kurucu, 2026-08-23).

Kurucu tespiti: ses çevirisi çalışıyordu ama canlı çıktı "duyulan" ile
"çeviri"yi telemetriyle aynı satıra sıkıştırıyordu; kimin konuştuğu hiç
görünmüyordu. Bu modül yalnız GÖSTERİM üretir — çeviri, ses ve kapanma
davranışına dokunmaz.

DÜRÜSTLÜK SINIRI (kod düzeyinde sabit): Recall'dan tek KARIŞIK ses akışı
geliyor (`audio_mixed_raw`), katılımcı kimliği taşıyan alan yok. Bu yüzden
satır başlıkları KİMSEYİ adlandırmaz; yalnız duyulan dili söyler ("Duyulan
(TR)"). "Sen / Karşı taraf" gibi atıf dilden türetilemez — kurucu İngilizce
konuşunca yanlış kişiye yazar (kurucu kararı, 2026-08-23). Gerçek konuşmacı
atfı katılımcı-başına ses akışı ister; ayrı dilim, bu modülün işi değil.

Bu bir ÜRÜN EKRANI DEĞİLDİR; kontrollü prova için geliştirici konsolu biçimidir.
Kullanıcıya görünen transkript ChatLumos içinde ayrı dilim olarak gelecek.
"""

from __future__ import annotations

from representative.pipeline import UtteranceRecord, flag_label

HEARD_PREFIX = "Duyulan"
INDENT = "   "

ATTRIBUTION_NOTE = (
    "Not: satırlar yalnız DUYULAN DİLİ gösterir; kimin konuştuğu bu sürümde "
    "bilinmiyor (karışık ses akışında konuşmacı kimliği yok)."
)


def attribution_note() -> str:
    """Oturum başında bir kez basılır — kimlik iddiası olmadığını söyler."""
    return ATTRIBUTION_NOTE


def format_heard(source_lang: str, text: str) -> str:
    """Duyulan söz — çeviri beklenmeden hemen basılır (akış korunur)."""
    return f"{HEARD_PREFIX} ({source_lang.upper()}): {text}"


def format_translation(record: UtteranceRecord) -> str:
    """Lumos çevirisi — özgün sözden ayrı satırda, girintili."""
    line = f"{INDENT}Lumos → {record.target_lang.upper()}: {record.translated_text}"
    marks = [m for m in (flag_label(record),) if m]
    if not record.delivered:
        marks.append("✕ seslendirilmedi")
    if marks:
        line += f"  [{' · '.join(marks)}]"
    return line


def format_telemetry(record: UtteranceRecord, routing_reason: str) -> str:
    """Ölçüm satırı — çeviri metninden ayrı tutulur ki transkript okunabilsin."""
    return (
        f"{INDENT}· e2e {record.latency_ms:.0f} ms"
        f" | stt {record.stt_ms:.0f} tr {record.translate_ms:.0f}"
        f" tts0 {record.tts_to_first_audio_ms:.0f}"
        f" | yön: {routing_reason}"
    )
