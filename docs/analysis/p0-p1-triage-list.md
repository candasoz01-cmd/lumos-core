# P0/P1 Triage List — Internal Alpha (G-23)

| Alan | Değer |
|------|-------|
| **Belge türü** | Operasyonel triage (docs only) |
| **Tarih** | 2026-06-26 |
| **Kaynak** | [launch-readiness-gap.md](launch-readiness-gap.md) A3, [INTERNAL_ALPHA_RELEASE_SCOPE.md](../INTERNAL_ALPHA_RELEASE_SCOPE.md) §6 |
| **Durum** | **Aktif** — Internal Alpha operasyonel faz (2026-06-18+) |

---

## Amaç

Internal Alpha girişinde **bilinen P0/P1 maddelerinin tek kaynak listesi** ve **sahip ataması**. Bu belge issue tracker yerine repo-içi canonical triage kaydıdır; kapanış kanıtı PR/issue ref ile güncellenir.

**Kural:** P0 = Alpha blokaj veya güvenlik/regresyon; P1 = Alpha çıkış veya Pilot giriş riski. Wave 2+ enforcement (Trust Faz 4, default-on, sensitivity↔gate, Panel LockState) bu listeye **alınmaz** — ayrı ADR/onay hattı.

---

## P0 — Alpha giriş / çalışma blokajı

| ID | Konu | Durum | Sahip | Kanıt / not |
|----|------|-------|-------|-------------|
| P0-01 | CI ana dal yeşil (`test`, `ui-smoke`, `ui-e2e`) | **Kapalı** | Platform | `main` CI success; son merge #503 |
| P0-02 | Yazılı Internal Alpha release kapsamı (G-24) | **Kapalı** | Ürün / release | [INTERNAL_ALPHA_RELEASE_SCOPE.md](../INTERNAL_ALPHA_RELEASE_SCOPE.md) #501 |
| P0-03 | ADR-012 Alpha defer tek kayıt (G-18) | **Kapalı** | Güvenlik / docs | [adr-012-internal-alpha-defer-record.md](../memory/adr-012-internal-alpha-defer-record.md) #500 |
| P0-04 | Merkezi P0/P1 triage + sahip (G-23) | **Kapalı** | Platform | Bu belge |
| P0-05 | Aktif güvenlik regresyonu (SECURITY_NEVER_AUTO bypass) | **İzleme — açık yok** | Güvenlik | Wave 1 P2 #496–#498 merge; yeni regresyon yok |

**Alpha P0 özeti:** P0-04 kapanışı ile Alpha giriş P0 seti tamamlandı sayılır (operasyonel doğrulama: çekirdek yolculuk tekrarı A3 çıkış kriteri).

---

## P1 — Alpha çıkış / Pilot giriş riski

| ID | Konu | Durum | Sahip | Blocker for | Not |
|----|------|-------|-------|-------------|-----|
| P1-01 | Modül menüsü iskelet rozet (RB-17 / G-03) | **Kapalı** | UX / panel | Closed Pilot | #503 — nav `inactiveBadge` |
| P1-02 | Çekirdek yolculuk ≥2 hafta ekip tekrarı (G-02) | **Devam ediyor** | Ürün / QA | Closed Pilot | Faz başlangıç 2026-06-18; [INTERNAL_ALPHA_OPERATIONS.md](../INTERNAL_ALPHA_OPERATIONS.md) §4 |
| P1-03 | Pilot sözleşmesi + davet ≤20 (G-04) | **Şablon hazır** | Ticari / ops | Closed Pilot | [pilot-contract-template.md](pilot-contract-template.md) — Alpha exit gate; imza pilot başında |
| P1-04 | Yazılı destek kanalı + best-effort SLA (G-05) | **Şablon hazır** | Destek / ops | Closed Pilot | [support-channel-alpha.md](support-channel-alpha.md) — `support@` TBD |
| P1-05 | Panel read-only tasks path uyumsuzluğu | **Kapalı** | Platform | Alpha çıkış | [p1-05-tasks-path-audit.md](p1-05-tasks-path-audit.md) — bilinçli çift depo; sync yok; migration defer (ADR-008, EC2-05) |
| P1-06 | Python packaging tek `pip install` (RB-06 / G-17) | **Spike** | Platform | Commercial Launch | [python-packaging-spike-rb06.md](python-packaging-spike-rb06.md) — Alpha defer |
| P1-07 | Release checklist (RB-07) | **Kapalı** | Release | Beta+ | [GITHUB_RELEASE_CHECKLIST.md](../GITHUB_RELEASE_CHECKLIST.md) #502 |

---

## Sahiplik sözlüğü

| Sahip | Kapsam |
|-------|--------|
| **Platform** | CI, packaging spike, repo altyapısı, panel teknik borç |
| **Ürün / release** | Alpha/Pilot kapsam, yolculuk doğrulama |
| **UX / panel** | Panel menü, müşteri yüzü kopya |
| **Güvenlik** | ADR-012, SECURITY_NEVER_AUTO, regresyon |
| **Ticari / ops** | Pilot davet, sözleşme |
| **Destek / ops** | Destek kanalı, SLA metni |
| **QA** | Ekip içi tekrarlanabilirlik testi |

---

## Güncelleme akışı

1. Yeni P0/P1: tabloya satır ekle; sahip zorunlu.
2. Kapanış: `Durum` → **Kapalı** + PR/issue ref.
3. Alpha çıkış: P1-02 **Kapalı** + P0 regresyon = 0 hedefi.
4. `INTERNAL_ALPHA_RELEASE_SCOPE.md` §6 A3 bu belgeye referans verir.

---

## Çapraz referanslar

| ID | Bağlantı |
|----|----------|
| G-23 | Bu belge |
| G-03 | P1-01 (#503) |
| G-17 | P1-06 (spike) |
| RB-17 | P1-01 |
| RB-06 | P1-06 |

---

*Son güncelleme: 2026-06-26 — session closure: P1-03/04 şablon; welockai yüzey (#529–#532); bridge 503 doc; P1-02 checkpoint devam; P1-06 Launch P1 defer ([python-packaging-spike-rb06.md](python-packaging-spike-rb06.md)).*
