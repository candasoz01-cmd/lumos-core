# Lumos Core — Sonraki İş Kuyruğu (10 madde)

| Alan | Değer |
|------|-------|
| **Belge türü** | İş kuyruğu — **tamamlandı (retrospektif)** |
| **Tarih** | 2026-06-21 (kapanış); **2026-06-26** post-queue sync |
| **Repo durumu** | `main` @ `83834c9`+ — CI yeşil (#529–#532) |
| **Kaynaklar** | [adr-012-wave1-execution-plan.md](adr-012-wave1-execution-plan.md), [release-blockers.md](release-blockers.md), [p0-p1-triage-list.md](p0-p1-triage-list.md) |

---

## Durum özeti

10 maddelik kuyruk **2026-06-21 tamamlandı**. Post-Alpha web yüzeyi (#529–#532) ve session closure dokümanları **2026-06-26** merge edildi.

**G-23 (P0/P1 triage):** Aktif — [p0-p1-triage-list.md](p0-p1-triage-list.md).

---

## Tamamlanan 10 madde

| # | ID / Başlık | Durum | PR / kanıt |
|---|-------------|-------|------------|
| 1 | **PR-W1-02** — P2 TaskStep producer envanteri | **Kapandı** | #496 |
| 2 | **PR-W1-04** — `SECURITY_NEVER_AUTO` eşleme | **Kapandı** | #497 |
| 3 | **PR-W1-07** — P2 engine + panel senkron | **Kapandı** | #498 |
| 4 | **ADR-012 checkpoint sync** | **Kapandı** | #499 |
| 5 | **G-18 / RB-01** — ADR-012 Alpha defer | **Kapandı** | #500 |
| 6 | **G-24 / RB-09** — Internal Alpha scope | **Kapandı** | #501 |
| 7 | **RB-07** — Release checklist | **Kapandı** | #502 |
| 8 | **RB-17 / G-03** — Modül menüsü rozeti | **Kapandı** | #503 |
| 9 | **open-decisions sync** | **Kapandı** | #504 |
| 10 | **RB-06 / G-17** — Python packaging spike | **Kapandı (spike)** | [python-packaging-spike-rb06.md](python-packaging-spike-rb06.md) |

---

## Post-queue tamamlanan (2026-06-26)

| Konu | Durum | Kanıt |
|------|-------|-------|
| welockai.com umbrella + integrations | **Kapandı** | #529, #530 |
| Charter + trust model drafts | **Kapandı** | #531 |
| Alpha ops milestone log | **Kapandı** | #532 |
| P1-05 tasks path audit | **Kapandı** | #527 |
| P1-03 pilot şablon | **Şablon hazır** | [pilot-contract-template.md](pilot-contract-template.md) |
| P1-04 destek şablon | **Şablon hazır** | [support-channel-alpha.md](support-channel-alpha.md) |
| Bridge proxy 503 belgesi | **Kapandı** | [vercel-bridge-proxy-setup.md](../vercel-bridge-proxy-setup.md) |
| Session closure raporu | **Kapandı** | [session-closure-report.md](session-closure-report.md) |

---

## Kapsam dışı (bilinçli defer)

| Madde | Neden |
|-------|-------|
| **Wave 2 enforcement** | ADR-012 defer; ayrı onay |
| **Gerçek OAuth** (GitHub/Slack/Google) | Private / Launch; static sayfalar yeterli Alpha |
| **Gerçek OS executor** | Private katman; OSS stub |
| RB-06 uygulama | Launch P1 — spike hazır |
| ADR-012 CLOSED | Wave 2 + Launch gerekir |

---

## Aktif operasyonel (Alpha)

| Öncelik | Konu | Durum |
|---------|------|-------|
| 1 | P1-02 çekirdek yolculuk ≥2 hafta | **Devam** — haftalık checkpoint |
| 2 | P0-05 regresyon izleme | **İzleme** |
| — | P1-03/04 imza + kanal | **Closed Pilot kapısı** |

---

*Son güncelleme: 2026-06-26 — post #529–#532 sync; session closure.*
