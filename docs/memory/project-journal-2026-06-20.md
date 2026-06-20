# Proje Günlüğü — 20 Haziran 2026

## Özet

Panel UX **Tur 13** üç PR ile kapandı; Bugbot'un #409 incelemesi #410'daki photo fallback düzeltmesine yol açtı. Landing hero/roadmap/kuantum i18n tamamlandı; Gmail readonly smoke zinciri (#413–#416) kod + operatör runbook olarak `main`'e girdi. Gün sonunda `main` yeşil.

**Güncelleme (2026-06-21 — OD-031 Phase 2 Step 4):** Canonical [`public-repo-boundary.md`](./public-repo-boundary.md) oluşturuldu (mail + ops + public kod stub); eski boundary dosyaları redirect stub'a indirildi; ADR-002 revize edildi (demo-safe stub gerçeği); ADR-004–009 mail drift ifadeleri hizalandı; indeks/journal senkronu.

## Tamamlananlar

### Panel UX — Tur 13 kapanışı
- **#409** (17:22 UTC) — HTTP 200 `/chat` JSON hata yanıtları artık sınıflandırılmış hata balonu olarak gösteriliyor; ham `error` string'i asistan cevabı sayılmaz.
- **#410** (17:26 UTC) — Locale değişiminde balon gövdeleri yenileniyor; Bugbot sonrası **photo fallback** önceliği düzeltildi (HTTP 200'de hem `error` hem `reply` varken foto yanıtı korunur).
- **#411** (17:30 UTC) — Attach menüsü focus trap; kapanınca odak geri dönüyor.

### Bugbot doğrulaması (#409)
- Cursor Bugbot #409'da 1 potansiyel sorun işaretledi; bulgu #410 commit'inde giderildi (`test_panel_astro_i18n_v51_chat_200_photo_fallback_reply_priority_wiring`).

### Landing i18n (#412)
- **#412** (18:10 UTC) — Hero, roadmap ve kuantum bölümleri `landing/tr` + `landing/en` anahtarlarına taşındı; CSS token testi eklendi.

### Gmail readonly smoke hazırlığı (#413–#416)
- **#413** — Gmail OAuth callback sözleşmesi (PR1).
- **#414** — Vault secret read adapter (PR2).
- **#415** — Env-gated readonly Gmail API smoke (PR3); CI'da `LUMOS_GMAIL_SMOKE` yoksa otomatik skip.
- **#416** (19:03 UTC) — Operatör runbook stub: [`gmail-readonly-smoke-operator-runbook.md`](./gmail-readonly-smoke-operator-runbook.md) (tam metin ops vault'ta; OD-031 Phase 2 Step 1).

### OD-031 Phase 2 Step 4 — docs boundary + ADR sync (2026-06-21)
- Canonical boundary: [`public-repo-boundary.md`](./public-repo-boundary.md)
- Legacy redirects: [`public-mail-strategy-boundary.md`](./public-mail-strategy-boundary.md), [`public-ops-runbook-boundary.md`](./public-ops-runbook-boundary.md)
- ADR-002 § Public kod gerçeği; ADR-004–009 mail drift düzeltmesi
- İndeks senkronu: `decision-log.md`, `open-decisions-needs-review.md`, migration index'ler, private notice'lar

## Repo durumu

| Alan | Değer |
|------|-------|
| **main SHA (20 Haz)** | `f036d713a691d20e050c885594b56c67e38caad3` |
| **Son merge (20 Haz)** | #416 — docs: Gmail readonly smoke operator runbook |
| **CI (20 Haz)** | Yeşil — son push (#416) `success` (53s, 2026-06-20T19:28 UTC) |
| **Phase 2 Step 4** | Docs-only PR — boundary canonical + ADR sync (branch `docs/od-031-phase2-step4-boundary-adr-sync`) |

## Operatörde kalan

Canlı Gmail readonly smoke: vault + OAuth token hazır operatör makinesinde `LUMOS_GMAIL_SMOKE=1` ile manuel koşu (runbook §3 — ops vault).

**Ürün impl bekleyen:** Onaylı private mail/vault connector paketi; public stub ≠ prod.

## Sonraki odak

**ADR-010 usage map** — checkpoint tamamlandı (2026-06-21): [`docs/analysis/ADR-010-guard-policy-trust-usage-map.md`](../analysis/ADR-010-guard-policy-trust-usage-map.md).

**ADR-011 lock semantiği** — karar kaydı (2026-06-21): [`docs/decisions/ADR-011-lock-semantics-decision.md`](../decisions/ADR-011-lock-semantics-decision.md). İki sinyal (`keystore_ready` vs `session_unlocked`); birleştirme yok; rename PR ayrı.

**Sonraki:** Rename PR (`_lock_ok`, CLI argümanları); OD-031 private impl ops vault'ta. **Landing Tur 1** — kalan landing vitrin bölümlerinin i18n ve token kapsamını genişletmek.
