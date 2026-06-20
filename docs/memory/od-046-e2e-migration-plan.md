# OD-046 — E2E migrasyon planı (ui/dist hizası)

> **Durum:** `[implemented]` — Faz 0–5 tamamlandı (#300–#305 + Faz 5 doc sync); OD-046 **implementation-complete**.
>
> **Üst karar:** [`build-e2e-surface-alignment-decision.md`](./build-e2e-surface-alignment-decision.md) — Seçenek A onaylı; üretim yüzeyi `ui/`; kök E2E nihai hedef `ui/dist` veya Astro preview.
>
> **Keşif özeti (2026-06-20):** Legacy `panel/e2e/` altındaki 12 dosya (`package-flow-shared.mjs` dahil) `ui/dist` yüzeyine **mekanik port edilemez** — farklı uygulama (routing, DOM, storage anahtarları, hash navigasyon). OD-046 «tamamlandı» = kök `e2e:package*` karşılıklarının `ui/dist` üzerinde çalışması + CI `ui-e2e` job; 12 scriptin 1:1 taşınması **değil**.

**Karar (firm):** Kök E2E kalite kapısı, üretim paneli (`ui/dist` `/panel`) ile hizalanır. «Görev tamamla» adımı E2E'de **UI/API tamamlama yolu** (`#gorevler-detail-complete` → `POST /tasks/complete`) ile doğrulanır; chat `görev tamamla` komutu **OD-046 kapsamı dışındadır** — `panel.astro` ürün değişikliği gerekmez.

---

## 1. Tamamlanma tanımı (implementation-complete)

| # | Kriter | Kanıt |
|---|--------|--------|
| IC1 | Kök `npm run e2e:package` → `ui/dist` statik sunucu + Playwright | Root `package.json` hedefi `ui/` |
| IC2 | Kök `npm run e2e:package:api` → `ui/dist` + `panel_tasks_server` REST | API modu legacy ile eşdeğer davranış |
| IC3 | Kök `npm run e2e:tasks-offline-online` → `ui/dist` + offline/online geçişi | Görev API dayanıklılık kapısı |
| IC4 | CI `ui-smoke` job **korunur** (v1/v2 — PR #294–296) | `.github/workflows/ci.yml` |
| IC5 | CI **`ui-e2e` job** kök package scriptlerini çalıştırır | Yeni job; smoke'tan ayrı |
| IC6 | «Tamamla» adımı chat değil UI/API | `POST /tasks/complete`; chat komutu assert edilmez |
| IC7 | Legacy `panel/` E2E kök expose'dan **kaldırılmaz** (Faz 5'e kadar) veya açık deprecate notu | Geçiş dönemi; tek PR'da sert kesim yok |

**Tamamlandı (v1–v5):** IC1–IC7 karşılandı — smoke (#294–#296), ui/e2e package trio (#303–#305), kök redirect + `ui-e2e` CI (#305), legacy `e2e:legacy:*` (#305).

---

## 2. Legacy envanter özeti (keşif tablosu)

| # | Dosya | Kök expose | Hedef (bugün) | Mekanik port | OD-046 kararı |
|---|--------|------------|---------------|--------------|---------------|
| 1 | `run-package.mjs` | `e2e:package` | `panel/index.html` statik | **Hayır** — farklı DOM/LS | **Faz 2** — ui/dist package kapısı |
| 2 | `run-package-api.mjs` | `e2e:package:api` (birleşik) | panel + `panel_tasks_server` | **Hayır** | **Faz 3** — API package kapısı |
| 3 | `run-tasks-offline-online.mjs` | `e2e:tasks-offline-online` | panel + API offline döngüsü | **Hayır** | **Faz 3** — offline/online kapısı |
| 4 | `package-flow-shared.mjs` | (ortak modül) | panel LS anahtarları + chat assert | **Hayır** | **Faz 2** — `ui/e2e/` ortak assert (yeniden yazım) |
| 5 | `run-cross.mjs` | `panel` only (`e2e:cross`) | chat + trash + logs + dashboard zinciri | **Hayır** | **Kapsam dışı** — legacy zincir |
| 6 | `run-soft-delete.mjs` | `panel` only | silme happy path | **Hayır** | **Kapsam dışı** — package alt kümesi değil |
| 7 | `run-policy-gate.mjs` | `panel` only | politika kapısı | **Hayır** | **Kapsam dışı** — ayrı karar backlog |
| 8 | `run-verify-api-field.mjs` | `panel` only | saha API alan doğrulama | **Hayır** | **Kapsam dışı** — diagnose/saha |
| 9 | `run-chat-intent-browser.mjs` | `panel` only | chat intent/dispatch | **Hayır** | **Kapsam dışı** — chat görev tamamla dışı |
| 10 | `run-frontend-task-loading.mjs` | expose yok | `frontend/index.html` + köprü | **Hayır** | **Kapsam dışı** — OD-044 frontend |
| 11 | `diagnose-lumos-host-init.mjs` | expose yok | host-init teşhis | **Hayır** | **Kapsam dışı** — diagnose |
| 12 | `capture-kayitlar-oge-proof.mjs` | expose yok | PNG kanıt artifact | **Hayır** | **Kapsam dışı** — capture |

**Özet:** Kökten expose edilen **3 script** (package, package:api, tasks-offline-online) + ortak modül → **ui/dist karşılıkları** (Faz 2–4). Diğer 8 runner **bilinçli kapsam dışı**.

---

## 3. Kapsam dışı (non-goals)

| Non-goal | Gerekçe |
|----------|---------|
| **`frontend/` E2E** | OD-044 izole prototip; root build/E2E zincirinde değil |
| **Diagnose / capture scriptleri** | CI kapısı değil; yerel teşhis ve kanıt üretimi |
| **Legacy trash / logs / dashboard zinciri** | `run-cross.mjs` ve `package-flow-shared` logs/dashboard assert'leri; Astro panel farklı UX — ayrı ürün kararı |
| **Chat `görev tamamla`** | Ürün blocker kapandı: E2E «tamamla» = görevler UI tamamla butonu + `POST /tasks/complete`; chat komut dispatch **OD-046 dışı** |
| **12 script 1:1 port** | Mekanik taşıma mümkün değil; eşdeğer kök kapılar yeterli |
| **`panel/` dizin silme / emeklilik** | OD-046 C değil; geçiş dönemi legacy kapısı kalabilir |
| **Prod smoke (`welockai.com/panel`)** | Ayrı iş paketi; OD-046 implementation-complete tanımına dahil değil |

---

## 4. «Görev tamamla» kararı (ürün blocker — kapalı)

| Yön | Karar |
|-----|--------|
| **Legacy panel E2E** | `#lumos-chat-input` → `"görev tamamla …"` + chat storage assert |
| **OD-046 ui/dist E2E** | Görevler detayında **Tamamla** UI (`#gorevler-detail-complete` veya eşdeğer) → `tasksApiPost("/tasks/complete", { ref })` |
| **Chat komutu** | OD-046 migrasyonunda **assert edilmez** ve **zorunlu değil**; `panel.astro` chat dispatch değişikliği **istenmez** |
| **Doğrulama** | `task_completed` olayı + tamamlandı filtresi / status; chat mesajında `görev tamamla` metni **aranmaz** |

Bu karar Faz 0'da kayıt altına alındı; Faz 2–3 implementasyonunda bağlayıcıdır.

---

## 5. Fazlar ve PR sınırları

| Faz | Kapsam | PR sınırı (tek sorumluluk) | Çıktı |
|-----|--------|----------------------------|--------|
| **Faz 0** | Karar + migrasyon planı (bu belge) | `docs/memory/od-046-e2e-migration-plan.md` + indeks/karar belgesi güncellemesi | `approved-for-implementation` |
| **Faz 1** | `ui/e2e/` altyapı: `ui/dist` statik sunucu helper, Playwright ortak util, politika yama (online/kilit/consent) | Yalnızca `ui/e2e/*` + `ui/package.json` script taslağı; **davranış assert yok** | Infra hazır |
| **Faz 2** | `e2e:package` karşılığı — local/demo (`LUMOS_PANEL_TASKS_API_BASE=false` eşdeğeri); create → **UI tamamla** → sil; storage/API assert | `ui/e2e/run-package.mjs` (+ shared); kök script **henüz değiştirilmez** | IC1 kısmi (ui prefix) |
| **Faz 3** | `e2e:package:api` + `e2e:tasks-offline-online` karşılıkları; `panel_tasks_server` entegrasyonu | `ui/e2e/run-package-api.mjs`, `ui/e2e/run-tasks-offline-online.mjs` | IC2–IC3 kısmi (ui prefix) |
| **Faz 4** | Kök `package.json` `e2e:package*` → `--prefix ui`; CI **`ui-e2e` job**; legacy → `e2e:legacy:*` | `.github/workflows/ci.yml` + root `package.json` + `ui/package.json` expose | IC1–IC5 |
| **Faz 5** | OD-046 kapanış: doc sync, legacy kök expose deprecate notu (opsiyonel kaldırma ayrı onay) | `open-decisions-needs-review.md`, `build-e2e-surface-alignment-decision.md`, `decision-log.md` | **implementation-complete** |

**PR kuralı:** Faz atlama yok; her faz ayrı PR; Faz 4 öncesi kök scriptler legacy `panel/`'e işaret etmeye devam edebilir.

---

## 6. CI stratejisi

```
┌─────────────────────────────────────────────────────────┐
│  CI (mevcut + hedef)                                     │
├─────────────────────────────────────────────────────────┤
│  ui-smoke (v2, KORUNUR)                                  │
│    ui build → ui/e2e/smoke-panel.mjs                     │
│    IC4 — hızlı prod yüzeyi varlık kapısı                 │
├─────────────────────────────────────────────────────────┤
│  ui-e2e (Faz 4, YENİ)                                    │
│    ui build → e2e:package | e2e:package:api |            │
│               e2e:tasks-offline-online (ui prefix)       │
│    IC5 — kök package eşdeğer regresyon kapısı          │
├─────────────────────────────────────────────────────────┤
│  test (pytest) — değişmez                                │
└─────────────────────────────────────────────────────────┘
```

| Job | Ne zaman | Komut | OD-046 faz |
|-----|----------|-------|------------|
| `ui-smoke` | **Şimdi (v2)** | `npm run build` + `npm run e2e:smoke` (`ui/`) | v1/v2 tamam |
| `ui-e2e` | **Tamamlandı (Faz 4)** | `npm run build` + kök package E2E trio (`--prefix ui`) | PR #305 |

Smoke ve E2E **ayrı job** — smoke hızlı kırılma alarmı; E2E tam package kapısı.

---

## 7. OD-046 kapanış checklist

OD-046 **implementation-complete** — indeks **closed** (Faz 5):

- [x] IC1 — Kök `e2e:package` `ui/dist` hedefli ve yeşil — PR #303, #305
- [x] IC2 — Kök `e2e:package:api` `ui/dist` + API yeşil — PR #304, #305
- [x] IC3 — Kök `e2e:tasks-offline-online` yeşil — PR #304, #305
- [x] IC4 — CI `ui-smoke` yeşil (regresyonsuz) — PR #294–#296
- [x] IC5 — CI `ui-e2e` yeşil — PR #305
- [x] IC6 — Package akışında tamamla UI/API ile doğrulanıyor; chat `görev tamamla` yok — PR #303–#304
- [x] IC7 — Legacy kök expose → `e2e:legacy:*`; deprecate notu — PR #305, `panel/README.md` (Faz 5)
- [x] `build-e2e-surface-alignment-decision.md` §12 güncel — Faz 5
- [x] `open-decisions-needs-review.md` OD-046 **closed** — Faz 5
- [x] `decision-log.md` DL-F07 senkron — Faz 5

---

## 8. Çapraz referanslar

| ID / belge | İlişki |
|------------|--------|
| OD-043 | Birincil yüzey `ui/` — E2E hizası bu planla tamamlanır |
| OD-044 | `frontend/` E2E bu planda yok |
| PR #294–296 | v1 smoke + v2 CI smoke |
| PR #300–#305 | Faz 0–4 migrasyon zinciri (Faz 5 doc sync ayrı PR) |
| `panel_tasks_server.py` | Faz 3 API sunucusu — değişiklik yalnızca gerekirse dar PR |

---

Son güncelleme: 2026-06-20 (Faz 5 — implementation-complete; doc sync + indeks closed)
