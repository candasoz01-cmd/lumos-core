# AnchorUSB — MVP Planı (1–2 Hafta)

| Alan | Değer |
|------|-------|
| Durum | **Uygulama planı** — henüz kod yok |
| Tarih | 2026-06-26 |
| Süre | 2 hafta (10 iş günü) |
| Üst belge | [`../secure-device-framework.md`](../secure-device-framework.md) |

**MVP yığını (tek satır):** Rust `anchorusb-core` (AES-256-XTS/GCM + Argon2id + event log) + Python CLI + yerel şüphe kuralları; taşınabilir uygulama + USB'de `.vault` dosyası.

---

## Hafta 1 — Çekirdek ve yaşam döngüsü (Gün 1–5)

### Teslimler

| Gün | Teslim | Kabul |
|-----|--------|-------|
| 1 | `anchorusb-core` crate iskeleti; container header spec | Unit: header serialize/parse |
| 2 | Argon2id KDF + AES-256-GCM chunk encrypt/decrypt | Round-trip test vector |
| 3 | `init` / `unlock` / `lock` Rust API | Memory zeroize test |
| 4 | Append-only event log + hash chain | Tamper detection test |
| 5 | Python FFI + CLI: `init`, `unlock`, `lock`, `status` | Manuel USB: S0→S1→S2→S5 |

### Hafta 1 çıkış kriteri

- Gerçek USB veya disk imajında `.vault` oluşturulup kilitlenebiliyor.
- Event log'da en az 4 kayıt türü: `INITIALIZED`, `UNLOCKED`, `LOCKED`, `IO_SUMMARY`.

---

## Hafta 2 — Tespit, rapor, eklenti iskeleti (Gün 6–10)

### Teslimler

| Gün | Teslim | Kabul |
|-----|--------|-------|
| 6 | Yerel detector: başarısız parola eşiği, hızlı okuma | S4 banner CLI çıktısı |
| 7 | `export-report` komutu (JSON paket) | Manuel: S6 dosya oluşturma |
| 8 | Plugin registry + `audit` builtin (salt okunur log özeti) | Plugin enable onay akışı |
| 9 | `backup_local` eklenti taslağı (kullanıcı onaylı kopya) | Onaysız kopya yok testi |
| 10 | Entegrasyon testleri + README hızlı başlangıç | Hafta 2 başarı kriterleri |

### Hafta 2 çıkış kriteri

- S4 şüphe senaryosu yerel bayrak üretiyor; **dış ağ çağrısı yok** (test ile doğrulanmış).
- Rapor export yalnızca kullanıcı komutu ile.

---

## MVP kapsam dışı

| Öğe | Neden ertelendi |
|-----|-----------------|
| USB boot / live OS | Maliyet; taşınabilir app yeterli |
| Native GUI / Tauri | CLI önce |
| Enterprise wipe / HSM | Politika + çift onay; ayrı faz |
| Lumos / WeLockAI panel entegrasyonu | Opsiyonel kanca; bağımsız ürün |
| iOS / Android host | Masaüstü MVP |
| Tam LUKS partition | v2 raw partition modu |
| Otomatik bulut yedek | NEVER_AUTO (A-04) |
| Polis / acil API | NEVER_AUTO (A-01) |

---

## Başarı kriterleri (MVP bitti sayılması)

1. **Güvenlik:** Anahtar materyali process dışı ve log dışı; `zeroize` doğrulandı.
2. **Yaşam döngüsü:** S0–S6 manuel senaryo checklist'i geçti ([`anchorusb-lifecycle.md`](./anchorusb-lifecycle.md)).
3. **Politika:** NEVER_AUTO tablosundaki A-01–A-07 için otomatik yol **kodda yok** (statik analiz / grep checklist).
4. **Test:** `cargo test` + `pytest` yeşil; en az 1 gerçek USB manuel koşu kaydı (docs veya test raporu).
5. **Docs:** Teknik mimari ile uygulama davranışı uyumlu; sapma varsa doc güncellemesi aynı PR.

**Not:** CI yeşil olmadan «tamamlandı» denmez ([`lumos-karar-ozet.mdc`](../../../.cursor/rules/lumos-karar-ozet.mdc)).

---

## Test planı

### Birim testleri

| Alan | Araç | Örnek |
|------|------|-------|
| KDF / crypto | `cargo test` | Bilinen vector, yanlış parola |
| Event log zinciri | `cargo test` | Hash kırılma tespiti |
| Container I/O | `cargo test` | Büyük dosya chunk |
| CLI | `pytest` | Mock FFI, exit code |
| Plugin onay | `pytest` | Enable olmadan çağrı reddi |

### Manuel USB senaryoları

| ID | Senaryo | Beklenen |
|----|---------|----------|
| M1 | Yeni USB → `init` | `.vault` oluşur |
| M2 | Yanlış parola ×5 | S4 bayrak, dış ağ yok |
| M3 | Unlock → dosya yaz → lock | İçerik şifreli kalır |
| M4 | USB çıkar (kilitli) | Veri okunamaz |
| M5 | `export-report` | JSON dosya; otomatik upload yok |
| M6 | Plugin disabled iken backup | Reddedilir |

### Negatif testler (güvenlik)

- Ağ mock: MVP binary'nin şüphe anında **sıfır** istek gönderdiği (`tcpdump` veya test hook).
- Strings taraması: `police`, `emergency`, `auto_notify` gibi yasak akış ipucu yok (ürün kararı; enterprise ayrı repo olabilir).

---

## Riskler ve azaltma

| Risk | Azaltma |
|------|---------|
| Host OS keylogger | Kısa oturum; kullanıcı eğitimi; MVP kapsamı açık |
| FFI bellek sızıntısı | Rust sınırında minimal surface |
| Scope creep (Lumos entegrasyonu) | Bağımsız paket; docs-only lumos-core bağlantısı |

---

## Sonraki faz (MVP sonrası, taahhüt değil)

- Tauri minimal tray UI
- Raw partition / LUKS modu
- WeLockAI onay relay ile «vault kilidi aç» görevi (insan onaylı)
- Enterprise modül ayrı repo / private katman

---

*Son güncelleme: 2026-06-26 — 2 haftalık MVP planı.*
