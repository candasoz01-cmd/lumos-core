# Internal Alpha — Operasyonel Takip

| Alan | Değer |
|------|-------|
| **Belge türü** | Operasyonel takip (docs only) |
| **Faz başlangıcı** | **2026-06-18** |
| **Repo snapshot** | `main` @ `bd4b83c`+; CI yeşil |
| **Üst sınır** | [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md), [`lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md) |
| **Durum** | **Aktif** — operasyonel faz devam ediyor |

Bu belge Internal Alpha **operasyonel faz** takibidir. Wave 2+ ADR-012 enforcement, confirmation default-on ve Launch packaging uygulaması **bu fazda authorize edilmez**.

---

## 1. Giriş kriterleri (Alpha entry)

Kaynak: [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md) §6.

| ID | Kriter | Durum | Kanıt |
|----|--------|-------|-------|
| A1 | Ekip release kapsamı yazılı | **Kapandı** | [INTERNAL_ALPHA_RELEASE_SCOPE.md](INTERNAL_ALPHA_RELEASE_SCOPE.md) #501 |
| A2 | CI yeşil (`test`, `ui-smoke`, `ui-e2e`) | **Kapandı** | `main` CI success; P0-01 |
| A3 | P0/P1 triage + sahip | **Kapandı** | [p0-p1-triage-list.md](analysis/p0-p1-triage-list.md) #504 |
| A4 | README / panel alpha etiketi (RB-09) | **Kapandı** | README + panel Sınırlı mod |
| A5 | ADR-012 Alpha defer tek kayıt (G-18) | **Kapandı** | [adr-012-internal-alpha-defer-record.md](memory/adr-012-internal-alpha-defer-record.md) #500 |

**Operasyonel faz başlangıcı:** 2026-06-18 — tüm giriş kriterleri karşılandı; çekirdek yolculuk doğrulaması (P1-02) **çıkış** kapısı olarak devam eder.

---

## 2. P0 durumu (giriş seti)

Kaynak: [p0-p1-triage-list.md](analysis/p0-p1-triage-list.md).

| ID | Konu | Sahip | Kabul kriteri | Durum | Kanıt |
|----|------|-------|---------------|-------|-------|
| P0-01 | CI ana dal yeşil | Platform | `test` + `ui-smoke` + `ui-e2e` success on `main` | **Kapalı** | #503+ |
| P0-02 | Yazılı Alpha kapsam (G-24) | Ürün / release | Onaylı scope belgesi merge | **Kapalı** | #501 |
| P0-03 | ADR-012 Alpha defer (G-18) | Güvenlik / docs | Tek defer kaydı; Wave 2 yok | **Kapalı** | #500 |
| P0-04 | Merkezi P0/P1 triage (G-23) | Platform | Sahiplik + tablo | **Kapalı** | #504 |
| P0-05 | SECURITY_NEVER_AUTO regresyon | Güvenlik | Yeni bypass yok; Wave 1 P2 korunur | **İzleme** | #496–#498; haftalık `make test` |

**P0 özeti:** Giriş seti tamamlandı. P0-05 operasyonel izleme — regresyon PR'ında Güvenlik sahibi günceller.

---

## 3. Aktif P1 işleri (Alpha çıkış)

| ID | Konu | Sahip | Durum | İlk hafta aksiyon |
|----|------|-------|-------|-------------------|
| P1-02 | Çekirdek yolculuk ≥2 hafta | Ürün / QA | **Devam ediyor** | §4 yolculuk planı; haftalık checkpoint |
| P1-05 | Panel read-only tasks path | Platform | **Kapalı** | [p1-05-tasks-path-audit.md](analysis/p1-05-tasks-path-audit.md) #527 |
| P1-03 | Pilot sözleşmesi + davet | Ticari / ops | **Şablon hazır** | [pilot-contract-template.md](analysis/pilot-contract-template.md) — Alpha exit gate; imza Closed Pilot |
| P1-04 | Destek kanalı + SLA | Destek / ops | **Şablon hazır** | [support-channel-alpha.md](analysis/support-channel-alpha.md) — kanal TBD; Closed Pilot kapısı |
| P1-06 | RB-06 packaging | Platform | **Spike (defer)** | Launch P1 — Alpha'da `make test` yeterli |

Kapalı P1: P1-01 (#503), P1-07 (#502).

---

## 4. Çekirdek yolculuk doğrulama (P1-02)

**Blocker for:** Closed Pilot · **Alpha çıkış** kriteri ([scope §7](INTERNAL_ALPHA_RELEASE_SCOPE.md#7-alpha-çıkış-hedefleri-referans))

### 4.1 «Başladı» tanımı

P1-02 **başladı** sayılır when **all** of:

1. Bu belgede faz başlangıç tarihi kayıtlı (2026-06-18) ✓
2. En az bir ekip üyesi **Hafta 1 checkpoint** şablonunu doldurdu (§4.3)
3. Panel yolculuğu en az bir kez uçtan uca doğrulandı:
   - **Panel:** `ui/` → `/panel` (yerel dev veya staging)
   - **Yerel görev [Yerel]:** görev ekle → listele → düzenle (`localStorage`)
   - **Opsiyonel:** köprü sohbet (yapılandırılmış dev/staging; prod Sınırlı mod ayrı)

### 4.2 Doğrulama komutları (repo)

| Adım | Komut / yol | Beklenen |
|------|-------------|----------|
| CI parity pytest | `make test` | exit 0 |
| UI build + smoke | `cd ui && npm ci && npm run build && npm run e2e:smoke` | exit 0 |
| Panel yerel | `cd ui && npm run dev` → `http://localhost:4321/panel` | Sınırlı mod + görev akışı |
| CLI smoke (opsiyonel) | `make cli` | exit 0 |

### 4.3 Haftalık checkpoint şablonu

Her **Pazartesi** (veya ekip sprint günü) bir satır `docs/INTERNAL_ALPHA_OPERATIONS.md` §6 günlüğüne veya ekip kanalına:

```markdown
### Checkpoint — YYYY-MM-DD (Hafta N)

- **Katılımcı(lar):** @owner
- **Panel yolculuk:** evet / hayır — not (hangi ortam)
- **Yerel görev [Yerel]:** evet / hayır
- **Köprü sohbet (opsiyonel):** evet / hayır / N/A
- **Regresyon:** `make test` — pass / fail
- **P0-05 izleme:** yeni SECURITY_NEVER_AUTO regresyonu yok / var (ref)
- **Bloker:** yok / açıklama
```

**Tamamlanma:** Ardışık **≥14 takvim günü** içinde en az **2 tam checkpoint** (Hafta 1 + Hafta 2+) ve sıfır P0 regresyon → P1-02 **Kapalı** ([triage](analysis/p0-p1-triage-list.md)).

---

## 5. İlk hafta operasyonel aksiyonlar (2026-06-18 → 2026-06-25)

| # | Aksiyon | Sahip | Hedef |
|---|---------|-------|-------|
| 1 | `make test` baseline — kayıt checkpoint Hafta 1 | Platform | P0-05 izleme |
| 2 | Panel `/panel` yerel görev akışı — 1 ekip üyesi | Ürün / QA | P1-02 «başladı» §4.1 |
| 3 | İlk haftalık checkpoint doldur (§4.3) | Ürün / QA | 2026-06-23 Pazartesi |
| 4 | P1-05 path envanteri — `.lumos/tasks.json` vs `.lumos/tasks/tasks.json` | Platform | **Kapandı** — [p1-05-tasks-path-audit.md](analysis/p1-05-tasks-path-audit.md) |
| 5 | Wave 2 / default-on / RB-06 impl **başlatma** | — | **Yasak** — defer kayıtlı |

---

## 6. Operasyon günlüğü

| Tarih | Olay | Ref |
|-------|------|-----|
| 2026-06-18 | Operasyonel faz başlangıcı — giriş kriterleri karşılandı | DL-C23 |
| 2026-06-21 | UX finding #1 — premium dark panel polish (in_progress) | [INTERNAL_ALPHA_UX_FINDINGS.md](INTERNAL_ALPHA_UX_FINDINGS.md) #510 |
| 2026-06-23 | P1-05 tasks path audit — çift depo doğrulandı, migration defer | [p1-05-tasks-path-audit.md](analysis/p1-05-tasks-path-audit.md) |
| 2026-06-26 | Umbrella site chrome live — nav/footer, landing tokens (#529) | #529 |
| 2026-06-26 | Integration hub + GitHub/Google/Slack static pages live (#530) | #530 — welockai.com/integrations* |
| 2026-06-26 | WeLockAI charter + trust model drafts merged (#531) | [welockai-charter-draft.md](analysis/welockai-charter-draft.md), [welockai-trust-model-draft.md](analysis/welockai-trust-model-draft.md) |
| 2026-06-26 | Production surface verify — `/`, `/integrations`, `/panel`, `/slack`, `/cyber`, `/connect/mac` → 200 | welockai.com smoke |
| 2026-06-26 | **P1-02 faz «başladı»** — welockai.com tam yüzey canlı; §4.1 (1)+(3) karşılandı; haftalık checkpoint §4.3 devam | #529–#532 |
| 2026-06-26 | P1-03/P1-04 şablonları hazır — planlama boşluğu kapandı | [pilot-contract-template.md](analysis/pilot-contract-template.md), [support-channel-alpha.md](analysis/support-channel-alpha.md) |
| 2026-06-26 | Bridge proxy 503 prod davranışı belgelendi (env yok = beklenen) | [vercel-bridge-proxy-setup.md](vercel-bridge-proxy-setup.md) |

*(Checkpoint satırları buraya veya ekip kanalına eklenir.)*

---

## 7. Çıkış kriterleri

Tam liste: [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md) §7.

- P1-02 kapalı (≥2 hafta tekrar)
- P0 regresyon = 0
- P1 kapatıldı veya Closed Pilot defer
- Release checklist mevcut — [`GITHUB_RELEASE_CHECKLIST.md`](GITHUB_RELEASE_CHECKLIST.md)
- ADR-012 CLOSED **şart değil** — [defer kaydı](memory/adr-012-internal-alpha-defer-record.md)

---

## 8. Çapraz referanslar

| Belge | Amaç |
|-------|------|
| [p0-p1-triage-list.md](analysis/p0-p1-triage-list.md) | Canonical P0/P1 durum |
| [GITHUB_RELEASE_CHECKLIST.md](GITHUB_RELEASE_CHECKLIST.md) | Merge / CI operatör checklist |
| [adr-012-internal-alpha-defer-record.md](memory/adr-012-internal-alpha-defer-record.md) | Wave 2 defer |
| [release-blockers.md](analysis/release-blockers.md) | P1-02–P1-06 RB bağlamı |
| [next-work-queue.md](analysis/next-work-queue.md) | Retrospektif kuyruk + post-queue ops |

---

*Son güncelleme: 2026-06-26 — session closure: welockai yüzey canlı; P1-03/04 şablon; bridge 503 doc; P1-02 checkpoint devam.*
