# Birincil kullanıcı yüzeyi — karar (OD-043)

**Durum:** `[decision-approved]` — dokümantasyon kararıdır; kod değişikliği içermez.  
**Kaynak:** `docs/memory/project-map-runtime-entrypoints.md`, `docs/memory/open-decisions-needs-review.md` (OD-043, çapraz OD-044 / OD-046).  
**Doğrulama:** Repo dosya sistemi read-only tarama — 2026-06-17.

---

## 1. Amaç

`panel/`, `ui/` ve `frontend/` dizinlerinin **birbirine karıştırılmadan** rollerini netleştirmek ve **birincil kullanıcı yüzeyi** sorusuna (OD-043) kanıta dayalı **onaylı karar** sunmaktır.

Bu belge:

- **Uygulama belgesi değildir** — hiçbir kod, test, build scripti veya deploy değişikliği önermez veya yapmaz.
- Çekirdek sözleşme (`docs/lumos-karar-sozlesmesi.md`) ve ürün kuralları (`docs/memory/product-rules.md`) üst sınır olarak geçerlidir; Lumos tek dış yüzey ilkesi bu kararı gevşetmez.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| `panel/`, `ui/`, `frontend/` kod değişikliği | OD-043 kararı dokümantasyon düzeyindedir; uygulama ayrı paketlerde |
| `api/bridge/`, `backend/`, `src/` Python çekirdeği | Runtime giriş zinciri ayrı belgede (`project-map-runtime-entrypoints.md`) |
| Diğer `docs/memory/*.md` dosyalarının güncellenmesi | Bu oturumda yalnızca bu dosya güncellenir |
| E2E hizası uygulaması | OD-046 Seçenek A — ayrı uygulama paketi; bu belge kararı onaylar, E2E migrasyonunu yapmaz |
| `lumos web` / `web/app.py` | OD-028; bu belgenin konusu değil |

---

## 3. Repo yüzeyleri mevcut durum (evidence-based)

### 3.1 Dizin varlığı

| Dizin | Var mı? | Paket adı | Kanıt |
|-------|---------|-----------|-------|
| **`panel/`** | Evet | `lumos-panel` (`panel/package.json`) | `index.html`, `js/`, `css/`, `e2e/`, Playwright devDependency |
| **`ui/`** | Evet | `lumos-core-ui` (`ui/package.json`) | Astro `^6.2.1`; `src/pages/index.astro`, `src/pages/panel.astro` |
| **`frontend/`** | Evet (minimal) | Yok | Yalnızca `index.html` + `project_memory_v1.js` (2 dosya) |

### 3.2 Root `package.json` scriptleri

```json
"build": "cd ui && npm install && npm run build",
"e2e:package": "npm run e2e:package --prefix panel",
"e2e:package:api": "npm run e2e:package:api --prefix panel",
"e2e:tasks-offline-online": "npm run e2e:tasks-offline-online --prefix panel"
```

- **Build hedefi:** `ui/` (Astro).
- **Root E2E hedefi (mevcut):** `panel/` (Playwright; statik `panel/index.html` sunucusu) — **legacy/static E2E kalite kapısı**; üretim yüzeyi değildir.

### 3.3 Deploy ve yerel geliştirme

| Kanal | Hedef | Kanıt |
|-------|--------|-------|
| **Vercel üretim** | `ui/dist` | `vercel.json`: `installCommand` / `buildCommand` → `cd ui && …`; `outputDirectory`: `ui/dist` |
| **Yerel UI (Astro)** | `ui/` | `ui/package.json`: `dev` → `astro dev`; `build` → `astro build` |
| **Yerel statik panel** | `panel/` | `panel/README.md`: `cd panel && python3 -m http.server 8080` → `http://127.0.0.1:8080/#yanit` |
| **`frontend/`** | Root script / Vercel zincirinde **yok** | `package.json` ve `vercel.json` içinde referans yok |

### 3.4 Üretim panel rotası (dokümantasyon kanıtı)

`docs/LUMOS_V1_READINESS.md` (repo içi, 2026-06-12):

- Üretim panel: `https://welockai.com/panel` — Astro `ui/` build, rota `/panel`.
- Legacy `panel/` statik uygulama: üretim için **superseded** (`ui/src/pages/panel.astro`).

OD-043 bu kanıtı **onaylı karar** olarak kilitler: birincil üretim/dış kullanıcı yüzeyi `ui/` (Astro). Root E2E hâlâ `panel/` statik uygulamayı hedeflediği için **E2E hizası** OD-046 Seçenek A uygulamasına kadar **beklemede** kalır.

### 3.5 `frontend/` ek kanıt

- `panel/e2e/run-frontend-task-loading.mjs` doğrudan `frontend/index.html` açar; köprü E2E senaryosu.
- Bu script **root `package.json` içinde expose edilmez** — ayrı çalıştırma gerekir.
- `docs/lumos-persona-security-implementation-gaps.md`: `frontend/index.html` «çalışma anı kullanıcı girdisi» deseni olarak anılır; üretim paneli `ui/src/pages/panel.astro` olarak ayrı tutulur.

---

## 4. Panel / UI / frontend ayrımı

**Sabit kural:** Üç dizin **aynı yüzey değildir**; görev tanımında hedef yüzey açık yazılmadan dosya değişikliği yapılmaz.

| Yüzey | Teknik kimlik | Rol (onaylı) | Karıştırma riski |
|-------|---------------|--------------|------------------|
| **`ui/`** | Astro statik site (`lumos-core-ui`) | **Birincil üretim / dış kullanıcı yüzeyi** — landing (`/`) + üretim panel rotası (`/panel`); Vercel deploy çıktısı | `panel/` ile «panel» adı çakışması |
| **`panel/`** | Vanilla HTML/JS statik uygulama (`lumos-panel`) | **Legacy / statik E2E kalite kapısı** — üretim yüzeyi **değil**; mock/fixture ağırlıklı geliştirme; root E2E paket kapısı (mevcut) | `ui/src/pages/panel.astro` ile isim benzerliği |
| **`frontend/`** | Tek dosyalık HTML prototip + yardımcı JS | Köprü/görev E2E (`run-frontend-task-loading.mjs`); birincil veya canlı yüzey **değil**; build/deploy zincirinde değil | «Frontend» genel terimiyle `ui/` sanılması |

**Ürün dili notu:** `docs/memory/ui-chat-experience.md` ve `docs/memory/product-rules.md` «panel / chat» derken **ürün yüzeyini** (Lumos tek dış yüzey) kasteder; bu, otomatik olarak `panel/` dizinine işaret etmez.

---

## 5. Birincil kullanıcı yüzeyi — onaylı karar (OD-043)

### 5.1 Bu belgenin statüsü

| İfade | Durum |
|-------|--------|
| Bu belge uygulama değildir | **Sabit** |
| `panel/`, `ui/`, `frontend/` karıştırılamaz | **Sabit** |
| `panel/` ve `ui/` ayrı yüzeylerdir | **Sabit** (repo doğrulandı) |
| `frontend/` canlı / birincil yüzey olarak kabul edilmez | **Onaylı** |
| Birincil üretim / dış kullanıcı yüzeyi = `ui/` (Astro) | **Onaylı** (OD-043) |
| `panel/` birincil üretim yüzeyi değildir | **Onaylı** (OD-043) |
| Root E2E → `ui/dist` veya Astro preview hizası | **Beklemede** — OD-046 Seçenek A uygulaması |

### 5.2 Onaylı pozisyon

| Bağlam | Yüzey | Gerekçe (kısa) | Durum |
|--------|--------|----------------|--------|
| **Üretim / dış kullanıcı (deploy)** | `ui/` (`/panel` rotası) | `vercel.json` + `LUMOS_V1_READINESS.md` + OD-043 | **Onaylı** |
| **Root `npm run build`** | `ui/` | Root `package.json` | **Onaylı** |
| **Root E2E paket kapısı (mevcut)** | `panel/` statik | `e2e:* --prefix panel` → `panel/index.html` sunucusu | **Legacy E2E kapısı** — üretim yüzeyi değil; OD-046 A ile hizalanacak |
| **Yerel statik panel geliştirme** | `panel/` | `panel/README.md` | Operasyonel gerçek (legacy / mock) |
| **Köprü odaklı HTML prototip** | `frontend/` | Yalnızca izole E2E; deploy yok | Canlı / birincil **değil** |

### 5.3 Reddedilen varsayımlar

- «Birincil üretim yüzeyi = `panel/`» — **reddedildi**. `panel/` yalnızca legacy/statik E2E kalite kapısıdır.
- «Birincil yüzey = `frontend/`» — **reddedildi**. Build/deploy zincirinde yok; iki dosyalık prototip.
- «`ui/` ve `panel/` birleşik tek kod tabanı» — **reddedildi**. Ayrı dizinler, ayrı `package.json`, farklı çalıştırma komutları.

**Özet onaylı cümle (OD-043):** Dış kullanıcıya sunulan birincil üretim web yüzeyi **`ui/` (Astro)** kabul edilir. **`panel/`** birincil üretim yüzeyi değildir; mevcut rolü **legacy/statik E2E kalite kapısı**dır. **`frontend/`** canlı veya birincil yüzey sayılmaz. Root E2E’nin üretim yüzeyiyle hizalanması **OD-046 Seçenek A uygulamasına kadar beklemededir**.

---

## 6. Build ve E2E ilişkisi

```
                    ┌─────────────────────────────────────┐
                    │  Root package.json                  │
                    └─────────────────────────────────────┘
                           │                    │
              npm run build│                    │npm run e2e:*
                           ▼                    ▼
                    ┌──────────┐         ┌──────────┐
                    │   ui/    │         │  panel/  │
                    │  Astro   │         │ Playwright│
                    │  → dist  │         │ → index  │
                    └──────────┘         │   .html  │
                           │             └──────────┘
                           ▼                    │
                    ┌──────────┐                │ (legacy E2E;
                    │ vercel   │                │  OD-046 A → ui)
                    │ ui/dist  │         ┌──────────┐
                    └──────────┘         │frontend/ │
                                         │ index.html│
                                         └──────────┘
```

| Komut / kanal | Hedef | Rol |
|---------------|--------|-----|
| `npm run build` (kök) | `ui/dist` | Üretim deploy — **birincil yüzey** |
| Vercel deploy | `ui/dist` | Dış kullanıcı — **birincil yüzey** |
| `npm run e2e:package` (kök) | `panel/` statik | **Legacy E2E kalite kapısı** (mevcut); OD-046 A ile `ui/dist` veya Astro preview’a hizalanacak |
| `cd ui && npm run dev` | Astro dev sunucusu | Yerel birincil yüzey geliştirme |
| `cd panel && python3 -m http.server` | Statik panel | Yerel legacy/mock geliştirme |
| `panel/e2e/run-frontend-task-loading.mjs` | `frontend/index.html` | Köprü E2E; birincil yüzey **değil** |

**OD-046 özeti (bağlantılı):** Seçenek A seçildi — E2E kalite kapısı `ui/dist` veya Astro preview ile hizalanacak. Uygulama **ayrı paket**; OD-043 kararı E2E migrasyonunun tamamlanmasını beklemez.

---

## 7. Kod değişikliği öncesi yönlendirme

Görev veya PR açılmadan önce:

1. **Hedef yüzeyi yaz:** `ui/`, `panel/` veya `frontend/` — üçü birden veya «panel» kelimesiyle belirsiz hedef **yasak**.
2. **Deploy mu, E2E mi, yerel mock mu?** Üçü farklı komut zincirleri kullanır (§6).
3. **Üretim / dış kullanıcı panel değişikliği** → hedef **`ui/src/pages/panel.astro`** (onaylı birincil yüzey); `panel/` statik değişikliği üretimi **otomatik** güncellemez.
4. **`panel/` görevleri** → yalnızca legacy/statik E2E kalite kapısı, mock/fixture veya OD-046 A migrasyon kapsamında; birincil üretim görevi olarak atanmaz.
5. **`frontend/`** → yalnızca açık prototip/köprü E2E görevlerinde; birincil veya canlı yüzey görevi olarak atanmaz.
6. **Bridge / token** → `ui/` prod bundle (`PUBLIC_KANDO_TOKEN`) ile `frontend/` runtime-input deseni karıştırılmaz; güvenlik sınırı `docs/lumos-karar-sozlesmesi.md`.
7. **Chat/panel UX kuralları** → `docs/memory/ui-chat-experience.md` ürün davranışı; uygulama yeri görevdeki hedef yüzeyle eşleştirilir (`ui/` birincil).

---

## 8. Riskler

| Risk | Açıklama | Öncelik |
|------|----------|---------|
| **İsim çakışması** | `panel/` dizini vs `ui/.../panel.astro` vs «panel» ürün terimi | Yüksek |
| **Build / E2E ayrışması** | Yeşil E2E `panel/` statikte geçer; üretim `ui/dist` farklı kod — OD-046 A beklemede | Yüksek (OD-046) |
| **Stale memory** | Eski notlarda tek yüzey (`ui` *veya* `panel`) iddiası | Orta |
| **`frontend/` hayalet yüzey** | Dizin adı genel; deploy yok ama E2E var | Orta (OD-044) |
| **Yanlış klasörde dev** | `panel/` sunucusu ile `ui/` Astro dev karışması | Orta |
| **Ürün ilkesi ihlali** | İç katman adlarının hangi yüzeyde olursa olsun UI'ya sızması | Yüksek (sözleşme) |

---

## 9. Açık kararlar

| ID | Soru | Bu belgedeki durum |
|----|------|-------------------|
| **OD-043** | Birincil yüzey `panel/`, `ui/` veya `frontend/` mi? | **Kapandı — onaylı:** birincil üretim/dış kullanıcı yüzeyi `ui/`; `panel/` legacy/statik E2E kapısı (üretim değil); `frontend/` birincil/canlı değil |
| **OD-044** | `frontend/` rolü ve yaşam döngüsü? | Canlı / birincil kabul **edilmedi**; arşiv / birleştirme / E2E-only — **kapanmadı** |
| **OD-046** | Root build (ui) ile panel E2E hangi yüzeyi test eder? | **Seçenek A seçildi** — E2E `ui/dist` veya Astro preview’a hizalanacak; **uygulama beklemede** (ayrı paket) |

Diğer OD maddeleri bu belgenin kapsamı dışındadır.

---

## 10. OD eşleme tablosu

| ID | Kaynak | Konu | Bu belgede netleşen | Durum | Çapraz not |
|----|--------|------|---------------------|--------|------------|
| **OD-043** | project-map-runtime-entrypoints.md | Birincil kullanıcı yüzeyi | Üç yüzey ayrıldı; birincil üretim = `ui/`; `panel/` = legacy E2E kapısı; `frontend/` = birincil değil | **decision-approved** | OD-046 uygulaması E2E hizasını tamamlar |
| **OD-044** | project-map-runtime-entrypoints.md | `frontend/` rolü | Canlı / birincil yüzey **değil**; 2 dosya; izole E2E | **needs-review** | OD-043 ile bağlı |
| **OD-046** | project-map-runtime-entrypoints.md | Root build vs panel E2E | Seçenek A: E2E → `ui/dist` veya Astro preview; uygulama ayrı paket | **pending-implementation** | OD-043 kararını bloklamaz |

---

## 11. Sonraki adım

**Tek önerilen adım:** OD-046 Seçenek A **uygulama paketini** başlat — root E2E komutlarını `ui/dist` veya Astro preview hedefine taşı; `panel/` statik uygulamayı yalnızca legacy/E2E geçiş döneminde tut. OD-043 **kapandı**; E2E hizası tamamlanana kadar mevcut `panel/` E2E köprüsü geçerli kalır.

---

## 12. Ayrı uygulama paketi (OD-046 A)

OD-043 bu belgede kapanır; aşağıdaki işler **bu belge kapsamı dışında**, ayrı uygulama paketinde yürütülür:

| Paket parçası | Kapsam | Not |
|---------------|--------|-----|
| **E2E migrasyonu** | Root `e2e:*` hedefini `panel/` statikten `ui/dist` veya Astro preview’a taşıma | OD-046 Seçenek A |
| **Test komutları** | Root `package.json` ve `panel/package.json` E2E script güncellemesi | Kod değişikliği; bu belgeye dahil değil |
| **Doc sync** | `project-map-runtime-entrypoints.md`, `open-decisions-needs-review.md`, ilgili README’ler | OD-046 kapanışıyla eşzamanlı |

**Bekleme durumu:** E2E hizası **PENDING** — OD-046 Seçenek A uygulaması tamamlanana kadar root E2E mevcut `panel/` statik kapısını kullanmaya devam eder; bu, birincil üretim yüzeyinin `ui/` olduğu kararını değiştirmez.

---

Son güncelleme: 2026-06-17
