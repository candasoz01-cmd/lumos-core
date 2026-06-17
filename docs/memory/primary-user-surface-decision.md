# Birincil kullanıcı yüzeyi — karar taslağı (OD-043)

**Durum:** `[decision-draft]` — uygulama değildir; kod değişikliği içermez.  
**Kaynak:** `docs/memory/project-map-runtime-entrypoints.md`, `docs/memory/open-decisions-needs-review.md` (OD-043, çapraz OD-044 / OD-046).  
**Doğrulama:** Repo dosya sistemi read-only tarama — 2026-06-17.

---

## 1. Amaç

`panel/`, `ui/` ve `frontend/` dizinlerinin **birbirine karıştırılmadan** rollerini netleştirmek ve **birincil kullanıcı yüzeyi** sorusuna (OD-043) kanıta dayalı bir **karar taslağı** sunmaktır.

Bu belge:

- **Uygulama belgesi değildir** — hiçbir kod, test, build scripti veya deploy değişikliği önermez veya yapmaz.
- Çekirdek sözleşme (`docs/lumos-karar-sozlesmesi.md`) ve ürün kuralları (`docs/memory/product-rules.md`) üst sınır olarak geçerlidir; Lumos tek dış yüzey ilkesi bu taslağı gevşetmez.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| `panel/`, `ui/`, `frontend/` kod değişikliği | OD-043 yalnızca karar taslağıdır |
| `api/bridge/`, `backend/`, `src/` Python çekirdeği | Runtime giriş zinciri ayrı belgede (`project-map-runtime-entrypoints.md`) |
| Diğer `docs/memory/*.md` dosyalarının güncellenmesi | Bu oturumda yalnızca bu dosya oluşturulur |
| Birincil yüzeyin **kesin** ilanı | Root build ↔ panel E2E çelişkisi (OD-046) kapanmadan «canlı» varsayımı yapılmaz |
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
- **Root E2E hedefi:** `panel/` (Playwright; statik `panel/index.html` sunucusu).

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

Bu ifade **ürün hazırlık belgesi** düzeyindedir; root E2E hâlâ `panel/` statik uygulamayı hedeflediği için «tek canlı yüzey» iddiası **henüz kapanmış sayılmaz** (OD-046).

### 3.5 `frontend/` ek kanıt

- `panel/e2e/run-frontend-task-loading.mjs` doğrudan `frontend/index.html` açar; köprü E2E senaryosu.
- Bu script **root `package.json` içinde expose edilmez** — ayrı çalıştırma gerekir.
- `docs/lumos-persona-security-implementation-gaps.md`: `frontend/index.html` «çalışma anı kullanıcı girdisi» deseni olarak anılır; üretim paneli `ui/src/pages/panel.astro` olarak ayrı tutulur.

---

## 4. Panel / UI / frontend ayrımı

**Sabit kural:** Üç dizin **aynı yüzey değildir**; görev tanımında hedef yüzey açık yazılmadan dosya değişikliği yapılmaz.

| Yüzey | Teknik kimlik | Rol (kanıta dayalı) | Karıştırma riski |
|-------|---------------|---------------------|------------------|
| **`ui/`** | Astro statik site (`lumos-core-ui`) | Landing (`/`) + üretim panel rotası (`/panel`); Vercel deploy çıktısı | `panel/` ile «panel» adı çakışması |
| **`panel/`** | Vanilla HTML/JS statik uygulama (`lumos-panel`) | Mock/fixture ağırlıklı geliştirme yüzeyi; root E2E paket kapısı; yerel `http.server` | `ui/src/pages/panel.astro` ile isim benzerliği |
| **`frontend/`** | Tek dosyalık HTML prototip + yardımcı JS | Köprü/görev E2E (`run-frontend-task-loading.mjs`); build/deploy zincirinde değil | «Frontend» genel terimiyle `ui/` sanılması |

**Ürün dili notu:** `docs/memory/ui-chat-experience.md` ve `docs/memory/product-rules.md` «panel / chat» derken **ürün yüzeyini** (Lumos tek dış yüzey) kasteder; bu, otomatik olarak `panel/` dizinine işaret etmez.

---

## 5. Birincil kullanıcı yüzeyi karar taslağı

### 5.1 Bu belgenin statüsü

| İfade | Durum |
|-------|--------|
| Bu belge uygulama değildir | **Sabit** |
| `panel/`, `ui/`, `frontend/` karıştırılamaz | **Sabit** |
| `panel/` ve `ui/` ayrı yüzeylerdir | **Sabit** (repo doğrulandı) |
| `frontend/` canlı yüzey olarak kabul edilmez | **Sabit** — OD-044 kapanana kadar |
| «Birincil yüzey» kesin kararı | **`needs-review`** — OD-043 açık |

### 5.2 Kanıta dayalı taslak pozisyon (henüz kesin karar değil)

| Bağlam | Taslak yüzey | Gerekçe (kısa) | Kesinlik |
|--------|--------------|----------------|----------|
| **Üretim / dış kullanıcı (deploy)** | `ui/` (`/panel` rotası) | `vercel.json` + `LUMOS_V1_READINESS.md` | Taslak — E2E hizası eksik (OD-046) |
| **Root `npm run build`** | `ui/` | Root `package.json` | Taslak |
| **Root E2E paket kapısı** | `panel/` statik | `e2e:* --prefix panel` → `panel/index.html` sunucusu | Taslak — üretim yüzeyiyle çelişki |
| **Yerel statik panel geliştirme** | `panel/` | `panel/README.md` | Operasyonel gerçek |
| **Köprü odaklı HTML prototip** | `frontend/` | Yalnızca izole E2E; deploy yok | Canlı **değil** |

### 5.3 Henüz kabul edilmeyen varsayımlar

- «Birincil yüzey = `panel/`» — root E2E bunu test eder ama üretim deploy `ui/` kullanır.
- «Birincil yüzey = `frontend/`» — build/deploy zincirinde yok; iki dosyalık prototip.
- «`ui/` ve `panel/` birleşik tek kod tabanı» — ayrı dizinler, ayrı `package.json`, farklı çalıştırma komutları.

**Özet taslak cümlesi (OD-043):** Dış kullanıcıya sunulan birincil web yüzeyi **taslak olarak `ui/` (Astro)** kabul edilir; **`panel/`** ayrı statik + E2E yüzeyi olarak kalır; **`frontend/`** canlı yüzey sayılmaz. Bu cümle **kesin karar değildir** — OD-046 (build vs E2E «canlı» tanımı) ve bilinçli migrasyon kararı beklenir.

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
                    ┌──────────┐                │ (ayrı script,
                    │ vercel   │                │  root'ta yok)
                    │ ui/dist  │         ┌──────────┐
                    └──────────┘         │frontend/ │
                                         │ index.html│
                                         └──────────┘
```

| Komut / kanal | Hedef | «Canlı» sayılır mı? |
|---------------|--------|---------------------|
| `npm run build` (kök) | `ui/dist` | Üretim deploy için **evet** (taslak) |
| Vercel deploy | `ui/dist` | Dış kullanıcı için **evet** (taslak) |
| `npm run e2e:package` (kök) | `panel/` statik | Kalite kapısı; üretim yüzeyiyle **çelişkili** `[needs-review]` |
| `cd ui && npm run dev` | Astro dev sunucusu | Yerel üretim yolu geliştirme |
| `cd panel && python3 -m http.server` | Statik panel | Yerel mock/fixture geliştirme |
| `panel/e2e/run-frontend-task-loading.mjs` | `frontend/index.html` | Köprü E2E; birincil yüzey **değil** |

**OD-046 özeti:** Root build `ui/` derken root E2E `panel/` der — hangi yüzeyin «canlı» kabul edileceği **açık karar bekliyor**.

---

## 7. Kod değişikliği öncesi yönlendirme

Görev veya PR açılmadan önce:

1. **Hedef yüzeyi yaz:** `ui/`, `panel/` veya `frontend/` — üçü birden veya «panel» kelimesiyle belirsiz hedef **yasak**.
2. **Deploy mu, E2E mi, yerel mock mu?** Üçü farklı komut zincirleri kullanır (§6).
3. **Üretim panel değişikliği** → varsayılan aday `ui/src/pages/panel.astro` (deploy kanıtı); `panel/` statik değişikliği üretimi **otomatik** güncellemez.
4. **`frontend/`** → yalnızca açık prototip/köprü E2E görevlerinde; birincil yüzey görevi olarak atanmaz.
5. **Bridge / token** → `ui/` prod bundle (`PUBLIC_KANDO_TOKEN`) ile `frontend/` runtime-input deseni karıştırılmaz; güvenlik sınırı `docs/lumos-karar-sozlesmesi.md`.
6. **Chat/panel UX kuralları** → `docs/memory/ui-chat-experience.md` ürün davranışı; uygulama yeri görevdeki hedef yüzeyle eşleştirilir.

---

## 8. Riskler

| Risk | Açıklama | Öncelik |
|------|----------|---------|
| **İsim çakışması** | `panel/` dizini vs `ui/.../panel.astro` vs «panel» ürün terimi | Yüksek |
| **Build / E2E ayrışması** | Yeşil E2E `panel/` statikte geçer; üretim `ui/dist` farklı kod | Yüksek (OD-046) |
| **Stale memory** | Eski notlarda tek yüzey (`ui` *veya* `panel`) iddiası | Orta |
| **`frontend/` hayalet yüzey** | Dizin adı genel; deploy yok ama E2E var | Orta (OD-044) |
| **Yanlış klasörde dev** | `panel/` sunucusu ile `ui/` Astro dev karışması | Orta |
| **Ürün ilkesi ihlali** | İç katman adlarının hangi yüzeyde olursa olsun UI'ya sızması | Yüksek (sözleşme) |

---

## 9. Açık kararlar

| ID | Soru | Bu belgedeki durum |
|----|------|-------------------|
| **OD-043** | Birincil yüzey `panel/`, `ui/` veya `frontend/` mi? | **Taslak:** üretim için `ui/`; E2E için `panel/`; `frontend/` değil. **Kesin karar:** `needs-review` |
| **OD-044** | `frontend/` rolü ve yaşam döngüsü? | Canlı kabul **edilmedi**; arşiv / birleştirme / E2E-only — **kapanmadı** |
| **OD-046** | Root build (ui) ile panel E2E hangi yüzeyi «canlı» sayar? | **Kapanmadı** — birincil yüzey kararının önkoşulu |

Diğer OD maddeleri bu belgenin kapsamı dışındadır.

---

## 10. OD eşleme tablosu

| ID | Kaynak | Konu | Bu belgede netleşen | Durum | Çapraz not |
|----|--------|------|---------------------|--------|------------|
| **OD-043** | project-map-runtime-entrypoints.md | Birincil kullanıcı yüzeyi | Üç yüzey ayrıldı; üretim taslağı `ui/`; kesin karar bekliyor | **needs-review** | OD-046 önkoşul |
| **OD-044** | project-map-runtime-entrypoints.md | `frontend/` rolü | Canlı yüzey **değil**; 2 dosya; izole E2E | **needs-review** | OD-043 ile bağlı |
| **OD-046** | project-map-runtime-entrypoints.md | Root build vs panel E2E | Build→`ui/`, E2E→`panel/` çelişkisi belgelendi | **needs-review** | OD-043 kapanışını bloklar |

---

## 11. Sonraki adım

**Tek önerilen adım:** OD-046 için kısa karar oturumu — root E2E’nin üretim yüzeyi (`ui/dist` veya `ui` dev) ile hizalanıp hizalanmayacağı ve `panel/` statik uygulamanın rolünün (legacy-only / parity test / kademeli emeklilik) netleştirilmesi. Bu adım tamamlanmadan OD-043 **closed** sayılmaz.

---

Son güncelleme: 2026-06-17
