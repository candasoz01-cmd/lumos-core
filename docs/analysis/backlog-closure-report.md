# Backlog Closure Report

| Alan | Değer |
|------|-------|
| Tarih | 2026-06-26 |
| Kapsam | NA-01..NA-08, naming §C.2, bridge prod, P1-02..P1-04, konsolide kapanış |
| Dal / PR | #544, #545, #546 |

---

## Özet

| Metrik | Sayı |
|--------|------|
| **Done (docs / safe label)** | **12** |
| **Deferred (onay / faz)** | **1** (NA-01 davranış) |
| **Owner-only (human input)** | **7** |
| Açık PR | 3 (sıralı merge) |

---

## Kapanış tablosu

| ID | Konu | Durum | PR |
|----|------|-------|-----|
| NA-01 | `decision_runner` base_dir zorunlu | **deferred** — NEEDS_APPROVAL | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| NA-02 | Arşiv decision_runner mirror | **done** — RESOLVED-DOC | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| NA-03 | Mac AASA placeholder | **done** — RESOLVED-DOC | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| NA-04 | Secrets / bridge / OAuth stub | **owner** — NEEDS_OWNER | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| NA-05 | TBD fiyat / KYC / destek | **owner** — NEEDS_OWNER | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| NA-06 | `known_files` observation stub | **done** — RESOLVED-DOC | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| NA-07 | UI/CSS placeholder grep | **done** — RESOLVED-DOC | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| NA-08 | `DIRECT_WRITE_ATTEMPT` audit terimi | **done** — RESOLVED-DOC | [#544](https://github.com/candasoz01-cmd/lumos-core/pull/544) |
| C.2-pilot | Pilot kuruluş adları kalıbı | **done** — placeholder locked | [#545](https://github.com/candasoz01-cmd/lumos-core/pull/545) |
| C.2-support | `support@<DOMAIN_TBD>` kalıbı | **done** — placeholder locked | [#545](https://github.com/candasoz01-cmd/lumos-core/pull/545) |
| C.2-apple | Apple Team ID + bundle ID kalıbı | **done** — placeholder locked | [#545](https://github.com/candasoz01-cmd/lumos-core/pull/545) |
| BRIDGE-prod | Vercel bridge owner checklist + curl | **done** — OWNER_ACTION documented | [#546](https://github.com/candasoz01-cmd/lumos-core/pull/546) |
| P1-02 | Internal Alpha Hafta 2 checkpoint | **deferred** — pending pilot week (≥14 gün) | [#546](https://github.com/candasoz01-cmd/lumos-core/pull/546) |
| P1-03 | Pilot sözleşme şablonu link | **done** — getting-started + INTERNAL_ALPHA | [#546](https://github.com/candasoz01-cmd/lumos-core/pull/546) |
| P1-04 | Destek kanalı şablonu link | **done** — getting-started + INTERNAL_ALPHA | [#546](https://github.com/candasoz01-cmd/lumos-core/pull/546) |

---

## Owner action list (copy-paste)

1. **Vercel bridge env** — Vercel Production → `BRIDGE_UPSTREAM_URL` + `KANDO_BRIDGE_SECRET`; redeploy; doğrula: `curl -sS -o /dev/null -w "%{http_code}" https://welockai.com/api/bridge/task` (env yokken 503 beklenir). Detay: [`vercel-bridge-proxy-setup.md`](../vercel-bridge-proxy-setup.md) §Owner verification checklist.

2. **Yerel köprü secret** — `export KANDO_BRIDGE_SECRET='<secret>'` yalnızca shell / `.env` (gitignore); repoya commit etme.

3. **Apple Team ID** — Developer hesabından Team ID al; AASA `appID` ship deploy'da güncelle; repoda `XXXXXXXXXX` kalır. Detay: [`mac-app-link-layer.md`](../mac-app-link-layer.md), naming registry §C.2.

4. **Bundle ID doğrulama** — Mac app target `com.welockai.lumos` ship öncesi doğrula veya güncelle (private build).

5. **Destek e-postası** — `support@<DOMAIN_TBD>` formatında domain + posta kutusu oluştur; [`support-channel-alpha.md`](./support-channel-alpha.md) doldur; naming registry §C.2 satırını onayla.

6. **Pilot müşteri adları** — [`pilot-contract-template.md`](./pilot-contract-template.md) doldur; gerçek kuruluş adları yalnızca private sözleşme / davet listesi; public repoda `ÖrnekKuruluş-A/B/C` kullan.

7. **Ticari TBD** — Fiyat, KYC, SLA: [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) + ticari/hukuk onayı; sahte değer commit etme.

---

## Yalnızca insan girdisine bloklu

| Blokaj | Neden | Sonraki tetik |
|--------|-------|---------------|
| NA-01 `base_dir` zorunlu | Otonom apply davranışı — güvenlik onayı | Ayrı PR + güvenlik sahibi |
| Gerçek Apple Team ID / bundle | Dış hesap + ship | Mac client ship öncesi |
| `support@` gerçek adres | Domain / posta kutusu | Closed Pilot öncesi |
| Pilot kuruluş gerçek adları | Ticari sözleşme | Closed Pilot kickoff |
| Fiyat / KYC / SLA TBD | Hukuk / banka | Pre-commercial release |
| Vercel prod köprü | Secret + tünel URL | Owner checklist adım 1–7 |
| P1-02 Hafta 2 checkpoint | ≥14 gün + 2. checkpoint kanıtı | 2026-07-02 veya sonrası |

---

## Çapraz referanslar

| Belge | Rol |
|-------|-----|
| [`todo-fixme-sweep-report.md`](./todo-fixme-sweep-report.md) | NA-01..NA-08 detay |
| [`lumos-approved-naming-registry.md`](./lumos-approved-naming-registry.md) | §C.2 owner kalıpları |
| [`INTERNAL_ALPHA_OPERATIONS.md`](../INTERNAL_ALPHA_OPERATIONS.md) | P1-02 checkpoints |
| [`getting-started.md`](../getting-started.md) | P1-03 / P1-04 linkleri |

---

*Konsolide kapanış — backlog işleme 2026-06-26.*
