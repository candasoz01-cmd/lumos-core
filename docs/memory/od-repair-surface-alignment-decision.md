# OD-020/047/038 — Tamir asistanı yüzey ve demo-safe hizası

**Durum:** **`needs-review`** → **`decision-approved`** (yüzey/sınır ilkesi) / **`implementation-pending`** (detay UX).  
**Kaynak:** [`repair-assistant-requirements.md`](./repair-assistant-requirements.md)

---

## 1. Onaylı yüzey ilkesi

| Konu | Karar |
|------|--------|
| **Yüzey (OD-020)** | Tamir asistanı **ayrı mod/yüzey** — genel chat ses/görsel akışından izole; metin-first (OD-021 istisnası bilinçli) |
| **Vizyon hizası (OD-047)** | Teknik servis asistanı Lumos **uzman modu**; birincil yüzey `ui/` içinde veya bağlantılı rota — birincil prod yüzeyi panel değil |
| **Public demo sınırı (OD-038)** | Public repoda: **metin-only tanı**, genel akış açıklaması, mock PCB **yok**; gerçek firmware/RE/Ghidra otomasyon **private** |

---

## 2. Demo-safe vs private

| Akış | Public foundation | Private katman |
|------|-------------------|----------------|
| Metin soru-cevap tamir rehberi | Demo-safe taslak | — |
| PCB fotoğrafı yükleme/işleme | Politika notu only | Impl + depolama |
| Dış arama / şema taraması (OD-037) | İlke: offline varsayılan | Online entegrasyon |
| Ghidra / firmware RE | **Yok** (OD-029) | Operatör yerel |

---

## 3. Implementation-pending

- Yetki profili (`rapor` vs `guvenli_yurut`) tamir modu eşlemesi
- Foto hattı (OD-022) depolama/görünürlük
- Ses istisnası (OD-021) UX metni

---

Son güncelleme: 2026-06-20 (envanter ab791c14 §12 #9 — Phase 3)
