# Root build vs panel E2E — yüzey hizası kararı (OD-046)

**Durum:** `[decision-approved]` / **`implementation-complete`** — Seçenek A uygulandı; v1–v2 smoke+CI (#294–#296); Faz 0–4 (#300–#305) → [`od-046-e2e-migration-plan.md`](od-046-e2e-migration-plan.md).  
**Kaynak:** `docs/memory/open-decisions-needs-review.md` (OD-046; çapraz OD-043, OD-044).  
**Doğrulama:** Repo dosya sistemi read-only tarama — 2026-06-17; karar onayı — 2026-06-17.

---

## 1. Amaç

Root `package.json` içindeki **build** hedefi (`ui/`) ile **E2E** hedefi (`panel/`) farklı dizinlere işaret ettiği için «hangi yüzey canlıdır?» sorusunu (OD-046) kanıta dayalı olarak netleştirmek ve **onaylanmış hizalama kararını** kaydetmek.

Bu belge:

- **Uygulama belgesi değildir** — hiçbir kod, build scripti, E2E migrasyonu veya deploy değişikliği önermez veya yapmaz.
- Çekirdek sözleşme (`docs/lumos-karar-sozlesmesi.md`) üst sınır olarak geçerlidir.
- **Onaylanan karar (Seçenek A):** Kök E2E kalite kapısı, üretim yüzeyi (`ui/dist` veya Astro preview) ile hizalanacak; bugünkü `panel/` E2E geçiş dönemi kalite kapısıdır.
- OD-043 (birincil kullanıcı yüzeyi) kapanışı, bu hizalama **uygulamasının** sonucuna bağlıdır.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| `ui/`, `panel/`, `frontend/` kod değişikliği | OD-046 yalnızca karar taslağıdır |
| Root `package.json` script değişikliği | Bilinçli hizalama kararı sonrası ayrı görev |
| E2E migrasyonu (`panel/` → `ui/dist`) | Karar onaylandı (Seçenek A); uygulama ayrı iş paketi |
| `api/bridge/`, `backend/`, `src/` Python çekirdeği | Runtime giriş zinciri ayrı belgede |
| OD-043 kesin kapanışı | Hizalama uygulaması sonucuna bağlı; tek başına kapatmaz |
| OD-044 (`frontend/` yaşam döngüsü) | Yalnızca çapraz not; ayrı karar |
| `lumos web` / `web/app.py` | OD-028; bu belgenin konusu değil |

---

## 3. Mevcut build ve E2E gerçekliği (evidence from repo)

### 3.1 Root `package.json` scriptleri

```json
"build": "cd ui && npm install && npm run build",
"e2e:smoke:ui": "npm run build && npm run e2e:smoke --prefix ui",
"e2e:package": "npm run e2e:package --prefix ui",
"e2e:package:api": "npm run e2e:package:api --prefix ui",
"e2e:tasks-offline-online": "npm run e2e:tasks-offline-online --prefix ui",
"e2e:legacy:package": "npm run e2e:package --prefix panel"
```

| Script | Hedef dizin | Çıktı / davranış |
|--------|-------------|------------------|
| `npm run build` (kök) | `ui/` | Astro build → `ui/dist` |
| `npm run e2e:smoke:ui` (kök) | `ui/dist` | Playwright smoke — `/panel` title + temel DOM (OD-046 v1) |
| `npm run e2e:legacy:*` (kök) | `panel/` | Playwright; `panel/index.html` — **deprecated** geçiş kapısı |
| `npm run e2e:package*` (kök, birincil) | `ui/dist` | Playwright package trio — **OD-046 birincil kapı** |

**Kanıt:** Kök `package.json` — build `ui/`; birincil `e2e:package*` → `--prefix ui`; legacy → `e2e:legacy:*` → `--prefix panel`.

### 3.2 `ui/` (Astro — `lumos-core-ui`)

| Alan | Değer |
|------|--------|
| Paket | `ui/package.json` → `lumos-core-ui` |
| Build | `astro build` |
| Dev | `astro dev` |
| Üretim panel rotası | `ui/src/pages/panel.astro` → deploy sonrası `/panel` |

### 3.3 `panel/` (statik — `lumos-panel`)

| Alan | Değer |
|------|--------|
| Paket | `panel/package.json` → `lumos-panel` |
| Yerel çalıştırma | `panel/README.md`: `cd panel && python3 -m http.server 8080` → `http://127.0.0.1:8080/#yanit` |
| E2E | `panel/e2e/run-package.mjs` — `PANEL_DIR = panel/`; `panel/index.html` üzerinde statik HTTP sunucu başlatır |
| Kök E2E expose | `e2e:package`, `e2e:package:api`, `e2e:tasks-offline-online` (panel içinde ek scriptler var; kökten expose edilenler yukarıdaki üçü) |

**Kanıt:** `panel/e2e/run-package.mjs` satır 12–13, 23–27 — `panel/` kökünde `index.html` zorunlu; statik sunucu bu dizinden servis eder.

### 3.4 Vercel deploy

`vercel.json`:

```json
"installCommand": "cd ui && npm install",
"buildCommand": "cd ui && npm run build",
"outputDirectory": "ui/dist"
```

Deploy zinciri **`ui/dist`** üretir; `panel/` referansı yok.

### 3.5 Ürün hazırlık belgesi (`docs/LUMOS_V1_READINESS.md`)

| İfade | Anlam |
|-------|--------|
| Production panel: `https://welockai.com/panel` | Astro `ui/` build, rota `/panel` |
| Legacy `panel/` static app | Üretim için **superseded** — `ui/src/pages/panel.astro` |
| `panel/camera.html` | Dev/smoke only; prod deploy'da yok |
| Astro `ui` build ships to `/panel` | `vercel.json` `outputDirectory: ui/dist` ile doğrulanmış (smoke notu) |

### 3.6 Özet gerçeklik tablosu

| Kanal | Hedef yüzey | Kod tabanı |
|-------|-------------|------------|
| Root `npm run build` | `ui/dist` | Astro (`ui/`) |
| Vercel deploy | `ui/dist` | Astro (`ui/`) |
| Root `npm run e2e:*` | `panel/index.html` (statik sunucu) | Vanilla HTML/JS (`panel/`) |
| Üretim URL (`welockai.com/panel`) | `/panel` rotası | `ui/src/pages/panel.astro` build çıktısı |
| `frontend/` | Root build/E2E zincirinde **yok** | İzole prototip (OD-044) |

**Çelişki (OD-046 çekirdeği):** Build ve deploy `ui/` derken; kök E2E kalite kapısı `panel/` statik uygulamayı test eder. İki farklı kod tabanı.

---

## 4. Root build / Vercel / UI ilişkisi

```
Kök package.json                    vercel.json
      │                                  │
      │ npm run build                    │ installCommand + buildCommand
      ▼                                  ▼
   ┌─────────┐                      ┌─────────┐
   │   ui/   │  astro build         │ ui/dist │  → welockai.com
   │  Astro  │ ──────────────────►  │ output  │     /panel rotası
   └─────────┘                      └─────────┘
```

| Soru | Kanıta dayalı yanıt |
|------|---------------------|
| Root build ne üretir? | `ui/dist` (Astro statik site) |
| Vercel ne deploy eder? | Aynı: `ui/dist` |
| Üretim panel hangi dosyadan gelir? | `ui/src/pages/panel.astro` build çıktısı |
| `panel/` dizini build'e dahil mi? | **Hayır** — root build ve Vercel zincirinde referans yok |

**Onaylanmış pozisyon:** Root build + Vercel `ui/`'ye işaret ediyorsa → **üretim yüzeyi `ui/`** (`/panel` rotası dahil). Bu, deploy kanıtı düzeyinde güçlü sinyaldir; E2E hizası Seçenek A uygulaması ile tamamlanacaktır.

---

## 5. Root E2E / panel ilişkisi

```
Kök package.json
      │
      │ npm run e2e:package | e2e:package:api | e2e:tasks-offline-online
      ▼
   ┌─────────┐
   │ panel/  │  Playwright + statik HTTP (panel/index.html)
   │  E2E    │
   └─────────┘
```

| Soru | Kanıta dayalı yanıt |
|------|---------------------|
| Kök E2E neyi açar? | `panel/index.html` — `panel/` dizininden statik sunucu |
| Hangi paket adı? | `lumos-panel` (`panel/package.json`) |
| `ui/dist` veya `ui` dev sunucusu test edilir mi? | **Hayır** — kök expose E2E scriptlerinde `ui/` hedefi yok |
| Panel README ne diyor? | Mock/fixture ağırlıklı geliştirme yüzeyi; hash routing (`#yanit`, `#dashboard`, …) |

**Onaylanmış pozisyon:** Root E2E bugün `panel/` statik uygulamayı hedefler → bu **geçiş dönemi kalite kapısı**dır; nihai hedef üretim yüzeyi (`ui/dist` veya Astro preview) ile hizadır (Seçenek A). `panel/` tek başına «üretim yüzeyi = panel/» kanıtı **değildir**.

**Ürün dili notu:** `docs/memory/ui-chat-experience.md` «panel / chat» derken ürün yüzeyini (Lumos tek dış yüzey) kasteder; bu otomatik olarak `panel/` dizinine işaret etmez.

---

## 6. Canlı yüzey ve kalite kapısı ayrımı

OD-046'nın çözmesi gereken kavram ayrımı:

| Kavram | Tanım | Mevcut repo kanıtı | «Canlı» sayılır mı? |
|--------|-------|--------------------|---------------------|
| **Üretim / dış kullanıcı yüzeyi** | Deploy edilen, son kullanıcının gördüğü web UI | `vercel.json` → `ui/dist`; `LUMOS_V1_READINESS.md` → `welockai.com/panel` | **Evet** (`ui/`) — onaylı |
| **Root build çıktısı** | `npm run build` (kök) artifact | `ui/dist` | Üretim yüzeyi ile **hizalı** — onaylı |
| **Root E2E kalite kapısı** | Kökten çalıştırılan paket/regresyon testleri | `panel/` statik — Playwright (bugün); hedef `ui/dist` / Astro preview | **Geçiş dönemi kalite kapısı**; nihai hedef üretim hizası |
| **Yerel statik panel geliştirme** | Mock/fixture operatör görünümü | `panel/README.md`, `python3 -m http.server` | Geliştirme yüzeyi; deploy değil |
| **`frontend/` prototip** | Köprü odaklı HTML | Root build/E2E'de yok | Canlı **değil** (OD-044) |

### Sabit ayrım kuralları (firm)

| Kural | Açıklama |
|-------|----------|
| **panel/ E2E pass ≠ ui/ production panel validated** | Yeşil `e2e:package` `panel/index.html` davranışını doğrular; `ui/src/pages/panel.astro` veya `welockai.com/panel` otomatik doğrulanmış sayılmaz. |
| **ui/ build pass ≠ panel/ static E2E behavior validated** | `ui/dist` build başarısı `panel/` Playwright senaryolarının geçtiği anlamına gelmez. |
| **Build hedefi ≠ E2E hedefi (bugün)** | İki ayrı kod tabanı; bilinçli hizalama olmadan «canlı» tek yüzey iddiası yapılamaz. |
| **Görevde «panel» kelimesi** | Hedef açık yazılmalı: `ui/src/pages/panel.astro` (üretim rotası) **veya** `panel/` (statik uygulama) — belirsiz «panel» yasak. |

### OD-043 ile ilişki

`docs/memory/primary-user-surface-decision.md` üretim için taslağı `ui/`, E2E için `panel/` olarak ayırmıştır. OD-046 **Seçenek A** ile kök E2E'nin üretim yüzeyine (`ui/`) hizalanmasını onaylamıştır. OD-043'ün kesin kapanışı, bu hizalamanın **uygulanması ve doğrulanması** sonucuna bağlıdır.

---

## 7. Onaylanmış karar

### 7.1 Belge statüsü

| İfade | Durum |
|-------|--------|
| Bu belge uygulama değildir | **Sabit** |
| OD-046 hizalama kararı | **Onaylandı** — Seçenek A |
| Build + Vercel → `ui/` = üretim yüzeyi | **Onaylı** (kanıt güçlü) |
| Root E2E birincil → `ui/dist` (OD-046 **closed**) | **Onaylı** |
| Root E2E legacy → `e2e:legacy:*` / `panel/` | **Onaylı** |
| OD-043 kapanışı | **closed** — E2E hizası tamam (#300–#307) |

### 7.2 Onaylanmış pozisyon

**Üretim «canlı» yüzey (dış kullanıcı):** **`ui/`** — Astro build, Vercel `ui/dist`, `/panel` rotası (`ui/src/pages/panel.astro`). Kaynak: `vercel.json`, `LUMOS_V1_READINESS.md`, root `npm run build`.

**Kalite kapısı (kök E2E — birincil, Seçenek A uygulandı):** **`ui/dist`** — kök `e2e:package*` → `--prefix ui`. Kaynak: root `package.json`, `ui/e2e/run-package.mjs`, CI `ui-e2e` job (#300–#305).

**Legacy kalite kapısı:** `e2e:legacy:*` → `panel/` statik uygulama — operatör/geriye dönük; birincil kapı değil (`panel/README.md` deprecated notu).

### 7.3 Seçilen seçenek: A

| Seçenek | Durum | Özet |
|---------|--------|------|
| **A** | **Seçildi** | Kök E2E'yi `ui/dist` veya Astro preview'a taşı — E2E = üretim yüzeyi hizası |
| B | Seçilmedi (tarihsel referans) | `panel/` statik E2E'yi koru; üretim smoke ayrı kanal |
| C | Seçilmedi (tarihsel referans) | `panel/` statik uygulamayı emekli et; yalnızca `ui/` |
| D | Seçilmedi (tarihsel referans) | Parity politikası: kritik akışlar her iki yüzeyde test |

### 7.4 Hâlâ geçerli olan yasak varsayımlar

- «E2E yeşil = prod panel doğrulandı» (bugünkü `panel/` E2E için geçerli)
- «Build yeşil = panel E2E senaryoları geçer»
- «`panel/` ve `ui/.../panel.astro` aynı test kapsamı»
- «Kök scriptler zaten hizalı» — kanıt bunun tersini gösteriyor; uygulama tamamlanana kadar geçerli

### 7.5 Özet onay cümlesi (OD-046)

**Dış kullanıcıya sunulan üretim yüzeyi** **`ui/` (`/panel`)** kabul edilir. **Root E2E kalite kapısı** bugün **`panel/`** statik uygulamayı hedefler; **onaylanan nihai hedef** üretim yüzeyi ile hizadır (**Seçenek A:** `ui/dist` veya Astro preview). Repo bugün **henüz hizalı değildir**; hizalama **ayrı uygulama iş paketidir**.

---

## 8. Kod değişikliği öncesi kural

Build/E2E hizası veya yüzey değişikliği görevi açılmadan önce:

1. **Hedef yüzeyi yaz:** `ui/src/pages/panel.astro` **veya** `panel/` — «panel» tek başına yeterli değil.
2. **Kanal belirt:** deploy mu (`ui/dist`), E2E mi (`panel/` statik), yerel mock mu (`panel/README.md` akışı).
3. **Kanıt türünü ayır:** Build pass, E2E pass ve prod smoke **farklı yüzeyleri** doğrular; birini diğerinin yerine kullanma.
4. **OD-046 uygulaması tamamlanmadan** «build ve E2E zaten aynı yüzeyi test ediyor» varsayımı yapılmaz.
5. **OD-043 kapanmadan** birincil yüzey için kesin implementasyon kapanışı verilmez — OD-043, Seçenek A uygulama sonucuna bağlıdır.
6. **Çekirdek sözleşme** (`docs/lumos-karar-sozlesmesi.md`) — token/bridge sınırları `ui/` prod bundle ile `panel/` mock ortamını karıştırmaz.

---

## 9. Riskler

| Risk | Açıklama | Öncelik |
|------|----------|---------|
| **Sahte güven (E2E)** | `e2e:package` geçer; prod `/panel` regresyonu fark edilmez | Yüksek |
| **Sahte güven (build)** | `ui` build geçer; `panel/` statik E2E kırık kalabilir | Yüksek |
| **İsim çakışması** | `panel/` dizini vs `ui/.../panel.astro` vs ürün terimi «panel» | Yüksek |
| **Stale dokümantasyon** | `LUMOS_V1_READINESS.md` legacy superseded der; E2E hâlâ legacy'yi test eder | Orta |
| **OD-043 blokajı** | Hizalama kararı ertelenirse birincil yüzey kesinleşmez | Yüksek |
| **Yanlış görev hedefi** | PR `panel/` değiştirir; üretim `ui/` güncellenmez (veya tersi) | Yüksek |

---

## 10. Açık kararlar

| ID | Soru | Bu belgedeki durum |
|----|------|-------------------|
| **OD-046** | Root build (ui) ile panel E2E hangi yüzeyi «canlı» sayar? | **Uygulandı (Seçenek A):** üretim → `ui/`; birincil kök E2E → `ui/dist`; legacy → `e2e:legacy:*` / `panel/` |
| **OD-043** | Birincil yüzey `panel/`, `ui/` veya `frontend/` mi? | **Kapandı (closed):** birincil üretim `ui/`; formal kapanış OD-046 tamamlandı (#300–#307) |
| **OD-044** | `frontend/` rolü? | Root build/E2E'de yok; canlı değil — kısa çapraz not |

### OD-046 seçenekleri (onay + tarihsel referans)

| Seçenek | Durum | Özet | Etki |
|---------|--------|------|------|
| **A** | **Seçildi** | Kök E2E'yi `ui/dist` veya Astro preview'a taşı | E2E = üretim yüzeyi hizası |
| B | Seçilmedi (tarihsel referans) | `panel/` statik E2E'yi koru; üretim smoke ayrı kanal | İki kapı; roller açık yazılır |
| C | Seçilmedi (tarihsel referans) | `panel/` statik uygulamayı emekli et; yalnızca `ui/` | E2E migrasyonu zorunlu |
| D | Seçilmedi (tarihsel referans) | Parity politikası: kritik akışlar her iki yüzeyde test | Bakım maliyeti artar |

**Not:** Karar onaylandı (Seçenek A); kod/build/test değişikliği **ayrı uygulama iş paketinde** yapılır.

---

## 11. OD eşleme tablosu

| ID | Kaynak | Konu | Bu belgede netleşen | Durum | Çapraz not |
|----|--------|------|---------------------|--------|------------|
| **OD-046** | project-map-runtime-entrypoints.md | Root build vs panel E2E | Seçenek A uygulandı: üretim `ui/`; birincil kök E2E → `ui/dist`; legacy → `e2e:legacy:*` | **implementation-complete** | PR #300–#305 |
| **OD-043** | project-map-runtime-entrypoints.md | Birincil kullanıcı yüzeyi | Birincil üretim `ui/`; E2E hizası tamam | **closed** | primary-user-surface-decision.md |
| **OD-044** | project-map-runtime-entrypoints.md | `frontend/` rolü | Seçenek B: izole köprü E2E; build/E2E zincirinde değil | **closed** | Birincil yüzey değil |

---

## 12. Tam E2E tanımı (implementation-complete)

**Canonical migrasyon planı:** [`od-046-e2e-migration-plan.md`](od-046-e2e-migration-plan.md) — Faz 0–5, envanter, non-goals, CI stratejisi, kapanış checklist.

### 12.1 Mevcut durum (v1–v2)

| Parça | Kapsam | Durum |
|-------|--------|--------|
| UI smoke (v1) | `ui/e2e/smoke-panel.mjs` — `ui/dist` statik `/panel` | **Tamamlandı** — PR #294 |
| Kök script | `npm run e2e:smoke:ui` | **Tamamlandı** |
| CI smoke (v2) | `.github/workflows/ci.yml` → `ui-smoke` job | **Tamamlandı** — PR #296 |
| Tam E2E migrasyonu | Kök `e2e:package*` → `ui/dist` | **Tamamlandı** — PR #303–#305 |
| CI package E2E | `ui-e2e` job | **Tamamlandı** — PR #305 |
| Legacy kök expose | `e2e:legacy:*` → `panel/` | **Deprecated notu** — PR #305 + `panel/README.md` |
| Prod smoke | `welockai.com/panel` veya eşdeğer | Bekliyor (OD-046 dışı) |

**Statü:** **`implementation-complete`** — OD-046 kapandı; prod smoke OD dışı backlog.

### 12.2 implementation-complete kriterleri

OD-046 **implementation-complete** yalnızca aşağıdakilerin tamamı sağlandığında:

| # | Kriter |
|---|--------|
| 1 | Kök `e2e:package`, `e2e:package:api`, `e2e:tasks-offline-online` **`ui/dist`** (veya Astro preview) hedefler |
| 2 | CI **`ui-smoke` korunur** + yeni **`ui-e2e` job** package trio'yu çalıştırır |
| 3 | Legacy 12 script **1:1 port değil** — kök expose üçlüsünün ui karşılığı yeterli (keşif: mekanik port mümkün değil) |
| 4 | «Görev tamamla» E2E adımı **UI/API** (`POST /tasks/complete`); chat `görev tamamla` **kapsam dışı** |

OD-046 **implementation-complete** (2026-06-20). OD-043 **closed** — birincil yüzey `ui/`; kök E2E hizası bu checklist ile tamamlandı (#300–#307).

---

Son güncelleme: 2026-06-20 (OD-043 closed; OD-046 implementation-complete)
