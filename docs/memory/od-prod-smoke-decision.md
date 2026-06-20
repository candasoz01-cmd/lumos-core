# Prod panel smoke — A3 karar

**Durum:** `approved-for-implementation` — kullanıcı açık komutu (2026-06-20 backlog A3).  
**Kaynak:** OD-046 non-goals — [`build-e2e-surface-alignment-decision.md`](./build-e2e-surface-alignment-decision.md) § prod smoke ayrı backlog; [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) §6.  
**Hedef URL:** `https://welockai.com/panel` (public; override: `LUMOS_PROD_PANEL_URL`).

---

## 1. Karar özeti

**Minimal read-only prod smoke:** Playwright ile canlı `/panel` HTTPS 200, temel DOM (`#chat-thread` veya `#panel-conn-badge`), kırıcı `console.error` yok. **Yazma yok**, secret yok, API token yok.

| Kanal | Tetikleyici | Kapı mı? |
|-------|-------------|----------|
| **GitHub Actions `prod-smoke.yml`** | `workflow_dispatch` (manuel) | **Hayır** — push/PR gate değil |
| Yerel | `npm run e2e:smoke:prod` (kök veya `ui/`) | Opsiyonel operatör |

**Kapsam dışı:**

- Prod görev ekleme / POST /tasks
- Auth / vault / backend credential
- Push veya PR zorunlu CI job'ı (flaky dış bağımlılık riski)

---

## 2. Keşif (2026-06-20)

| Alan | Durum |
|------|--------|
| Birincil prod yüzey | `ui/` Astro → `welockai.com/panel` (OD-043 **closed**) |
| Birincil kök E2E | `ui/dist` — CI `ui-smoke` + `ui-e2e` (OD-046 **closed**) |
| Prod smoke geçmişi | `LUMOS_V1_READINESS.md` §6 — 2026-06-11/12 manuel PASS |
| Boşluk | Otomatik/tekrarlanabilir **public repo** workflow yok |

**Public sınır:** Yalnızca public HTTPS URL; repo secret gerekmez.

---

## 3. Onaylı uygulama paketi (S effort)

| # | Adım | Dosya |
|---|------|--------|
| **A3-1** | Prod smoke script | `ui/e2e/smoke-prod.mjs` |
| **A3-2** | npm expose | `ui/package.json`, kök `package.json` |
| **A3-3** | Manuel workflow | `.github/workflows/prod-smoke.yml` |
| **A3-4** | Doğrulama | CI yeşil (prod job push gate **değil**) |

---

## 4. Rollback

1. Workflow dosyasını sil veya `workflow_dispatch` devre dışı bırak.
2. npm script satırlarını kaldır.

---

## 5. İndeks

- `decision-log.md` — DL-C10 (karar); DL-A21 (uygulama)

---

Son güncelleme: 2026-06-20
