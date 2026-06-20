# Prod smoke — karar ve minimal uygulama (A3)

**Durum:** `approved-for-implementation` — kullanıcı açık komutu (2026-06-20: sequential backlog A3).  
**Kaynak:** OD-046 dışı backlog — [`build-e2e-surface-alignment-decision.md`](./build-e2e-surface-alignment-decision.md) §12.1; [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) §6.  
**Çapraz:** Birincil üretim yüzeyi `ui/` → `welockai.com/panel` (OD-043 **closed**); CI `ui-smoke` / `ui-e2e` yerel `ui/dist` hedefler — prod doğrulaması ayrı kanal.

---

## 1. Karar özeti

**Prod smoke = read-only HTTPS doğrulama** — canlı `/panel` yüzeyinin yüklendiğini, temel DOM'un var olduğunu ve kırıcı konsol hatası olmadığını kontrol eder. Yazım, auth secret veya köprü token **gerektirmez**.

| Kanal | Hedef | CI |
|-------|--------|-----|
| `ui-smoke` / `ui-e2e` | Yerel `ui/dist` | Her push/PR (`ci.yml`) |
| **Prod smoke (yeni)** | `https://welockai.com/panel` (override: `LUMOS_PROD_PANEL_URL`) | **`workflow_dispatch` only** — dış URL; push kapısı değil |

**Kapsam dışı:**

- Prod görev ekleme / chat gönderimi (yazım; v1 manuel sign-off LUMOS_V1_READINESS'te)
- Secret, token, bridge credential
- `archive/panel/` legacy statik yüzey
- Push/PR zorunlu CI job (flaky dış bağımlılık riski)

---

## 2. Keşif kanıtı (2026-06-20)

| Bulgu | Kanıt |
|-------|--------|
| Prod URL public | `LUMOS_V1_READINESS.md` — `https://welockai.com/panel` |
| v1 manuel smoke PASS | 2026-06-12 sign-off; otomatik tekrar yok |
| CI prod smoke yok | `.github/workflows/ci.yml` — yalnızca `ui-smoke` + `ui-e2e` |
| Secret gerekmez | Read-only GET; sınırlı mod rozeti metin assert |

---

## 3. Onaylı uygulama paketi (S effort)

| # | Adım | Dosya |
|---|------|--------|
| P-1 | Prod smoke script | `ui/e2e/smoke-prod.mjs` |
| P-2 | npm script | `ui/package.json` → `e2e:smoke:prod`; kök `e2e:smoke:prod` |
| P-3 | Manuel CI workflow | `.github/workflows/prod-smoke.yml` — `workflow_dispatch` |
| P-4 | Karar + günlük | Bu belge; `decision-log.md` DL-C10 |

**Doğrulama:** Yerel `npm run e2e:smoke:prod --prefix ui` (network); workflow manuel tetik.

**Console filtresi:** Sınırlı modda köprü/API `Failed to load resource` / `ERR_CONNECTION_REFUSED` beklenir — kırıcı `pageerror` ve filtre dışı `console.error` fail eder.

---

## 4. Rollback

1. Workflow dosyasını sil veya devre dışı bırak.
2. npm scriptleri kaldır.
3. Karar belgesi arşiv notu — davranış değişmez (CI push kapısı yok).

---

Son güncelleme: 2026-06-20 (A3 karar — minimal stub)
