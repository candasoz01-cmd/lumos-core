# OD-029 — Ghidra kapsamı (public OSS sınırı)

**Durum:** **`decision-approved`** — public `lumos-core` içinde Ghidra entegrasyonu yok; operatör/yerel veya private katman.  
**Kaynak:** [`tools-technology-watchlist.md`](./tools-technology-watchlist.md); [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) OD-029.  
**Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md); public GitHub boundary.

---

## 1. Karar özeti

| Soru | Onaylı cevap |
|------|----------------|
| Ghidra RE/firmware entegrasyonu public OSS'te kalır mı? | **Hayır** — `lumos-core` public repoda Ghidra bağlantısı, headless pipeline, firmware blob analizi veya cihaz yazılımı otomasyonu **yok** |
| Ghidra kullanımı tamamen yasak mı? | **Hayır** — operatör **yerel** Ghidra (veya eşdeğer RE aracı) tamir/RE bağlamında **Lumos dışı** kullanılabilir; sonuç public repoya commit edilmez |
| Watchlist durumu | **Takip** — ihtiyaç doğrunca private katmanda veya operatör runbook'ta değerlendirilir |

**Seçilen yön:** **B — Public sınır dışı, watchlist devam** (A: public entegrasyon reddedildi; C: otomatik entegrasyon reddedildi).

---

## 2. Kapsam dışı (public repo)

- Ghidra headless script, plugin veya CI job
- Firmware binary, dump veya RE artifact commit
- Cihaz kontrolü / flash / JTAG otomasyonu
- Production RE pipeline veya credential

---

## 3. İzinli (public repo)

- Bu karar belgesi ve watchlist satırı
- Genel «RE araçları operatör yerelinde» runbook referansı (secret/artifact yok)
- Tamir asistanı **metin-only** kapsamı ile uyum (OD-020 çapraz — firmware otomasyonu public değil)

---

## 4. Rollback

Karar belgesi revert; OD-029 indeks `needs-review` geri alınır. Kod yolu yok.

---

Son güncelleme: 2026-06-20 (OD-029 B2)
