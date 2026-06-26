# AnchorUSB — Güvenli Cihaz / Vault Dokümantasyon Paketi

| Alan | Değer |
|------|-------|
| Durum | **Week 1 uygulandı** — `crates/anchorusb-core` + `crates/anchorusb-cli` |
| Tarih | 2026-06-26 |
| Çalışma adı | **AnchorUSB** (kilitli) |

Bağımsız taşınabilir vault ürün hattı. Lumos OSS çekirdeğinden ayrı iz; WeLockAI entegrasyonu opsiyonel.

---

## Belgeler

| Belge | İçerik |
|-------|--------|
| [`../secure-device-framework.md`](../secure-device-framework.md) | Birincil mimari: 6 katman, alarm vs otomatik-polis karşılaştırması, NEVER_AUTO, isimlendirme |
| [`anchorusb-technical-architecture.md`](./anchorusb-technical-architecture.md) | Rust/Python yığını, modül diyagramı, klasör ağacı, kripto, eklenti sözleşmesi |
| [`anchorusb-lifecycle.md`](./anchorusb-lifecycle.md) | USB takma yaşam döngüsü (Aşama 0–7) |
| [`anchorusb-mvp-plan.md`](./anchorusb-mvp-plan.md) | 1–2 haftalık MVP teslimleri ve test planı |

---

## Hızlı ilkeler

1. **Sistem bilgilendirir, karar vermez** — dış etki insan onaylı.
2. **Anahtarlar cihaz dışına çıkmaz** (varsayılan).
3. **Public repo güvenli** — polis API, gizli telemetri, otomatik dış bildirim yok.
4. **MVP:** taşınabilir uygulama + USB'de şifreli `.vault` dosyası.

## Uygulama (Week 1)

| Bileşen | Yol |
|---------|-----|
| Rust çekirdek | [`crates/anchorusb-core/README.md`](../../../crates/anchorusb-core/README.md) |
| CLI (`anchorusb`) | `crates/anchorusb-cli` |
| Test | `cargo test -p anchorusb-core` |

---

## İlgili Lumos belgeleri

| Belge | Bağlantı |
|-------|----------|
| Karar sözleşmesi | [`../../lumos-karar-sozlesmesi.md`](../../lumos-karar-sozlesmesi.md) |
| Public boundary | [`../../memory/public-repo-boundary.md`](../../memory/public-repo-boundary.md) |
| Grounded roadmap | [`../grounded-phase-roadmap.md`](../grounded-phase-roadmap.md) § Ayrı iz |
| Cihaz eşleştirme (Lumos Mobile) | [`../device-pairing-strategy.md`](../device-pairing-strategy.md) — farklı ürün alanı |

---

*Son güncelleme: 2026-06-26*
