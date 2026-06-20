# frontend/ rolü ve yaşam döngüsü — karar (OD-044)

**Durum:** `[closed]` — Seçenek **B** onaylandı; kod/taşıma/arşiv/silme yok.  
**Kaynak:** `docs/memory/open-decisions-needs-review.md` (OD-044; çapraz OD-043 **closed**, OD-046 **closed**).  
**Doğrulama:** Repo dosya sistemi read-only tarama — 2026-06-17; formal kapanış — 2026-06-20.

---

## Amaç

`frontend/` dizininin `panel/` ve `ui/` ile **karıştırılmadan** rolünü, build/deploy/E2E zincirindeki konumunu ve **yaşam döngüsü** seçeneklerini (OD-044) kanıta dayalı bir **karar taslağı** olarak netleştirmek.

Bu belge:

- **Uygulama belgesi değildir** — hiçbir kod, test, build scripti, deploy veya dizin taşıma işlemi önermez veya yapmaz.
- Çekirdek sözleşme (`docs/lumos-karar-sozlesmesi.md`) ve iş akışı ilkeleri (`docs/memory/project-workflow.md`) üst sınır olarak geçerlidir.
- Birincil kullanıcı yüzeyi (OD-043) ve root build ↔ panel E2E hizası (OD-046) bu belgede **kapatılmaz**; yalnızca çapraz referans verilir.

---

## Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| `frontend/`, `panel/`, `ui/` kod değişikliği | OD-044 yalnızca karar taslağıdır |
| Root `package.json`, `vercel.json`, build/E2E script değişikliği | Bilinçli yaşam döngüsü kararı sonrası ayrı görev |
| `api/bridge/`, `backend/`, `src/` Python çekirdeği | Runtime giriş zinciri ayrı belgede (`project-map-runtime-entrypoints.md`) |
| Diğer `docs/memory/*.md` dosyalarının güncellenmesi | Bu oturumda yalnızca bu dosya oluşturulur |
| OD-043 kesin kapanışı | Birincil yüzey kararı ayrı belgede (`primary-user-surface-decision.md`) |
| OD-046 hizalama kararı | Build/E2E «canlı» tanımı ayrı belgede (`build-e2e-surface-alignment-decision.md`) |
| `lumos web` / `web/app.py` | OD-028; bu belgenin konusu değil |

---

## Mevcut frontend/ gerçekliği

### Dizin içeriği (repo doğrulaması)

| Dosya | Boyut / yapı | Rol (kanıta dayalı) |
|-------|--------------|---------------------|
| **`frontend/index.html`** | Tek dosyalık monolitik HTML (~8.800+ satır); gömülü CSS ve JS | Panel benzeri arayüz prototipi; `POST /task` köprü entegrasyonu; başlık: «Lumos panel» |
| **`frontend/project_memory_v1.js`** | ES modül (~100 satır); yaratıcı proje hafızası yardımcıları | Repoda **`index.html` tarafından import edilmiyor** — yalnızca dizinde duran ayrı dosya |

### Paket ve kök script kanıtı

| Alan | Değer |
|------|--------|
| **`frontend/package.json`** | **Yok** — bağımsız npm paketi değil |
| Root `package.json` → `build` | `cd ui && npm install && npm run build` — **`frontend/` referansı yok** |
| Root `package.json` → `e2e:*` | `--prefix panel` — **`frontend/` referansı yok** |
| `vercel.json` | `installCommand` / `buildCommand` → `ui/`; `outputDirectory`: `ui/dist` — **`frontend/` referansı yok** |

### `project-map-runtime-entrypoints.md` kaydı

`frontend/` tabloda **«Eski/alternatif frontend»** ve **`[needs-review]`** olarak işaretli; panel/ui ile ilişkisi netleştirilmemiş.

### E2E kanıtı

| Öğe | Kanıt |
|-----|--------|
| Script | `panel/e2e/run-frontend-task-loading.mjs` |
| Hedef | `join(REPO_ROOT, "frontend", "index.html")` — doğrudan `frontend/index.html` açar |
| Senaryo | Gönder → loading → `POST /task` (gerçek köprü: `kando_bridge_server.py`) → analiz kartı |
| Kök expose | **Hayır** — root `package.json` içinde bu script yok; ayrı çalıştırma gerekir |
| Statik sunucu | Script içinde minimal HTTP sunucu yalnızca `index.html` servis eder; `/task` köprü tarafında |

### Özet gerçeklik tablosu

| Soru | Kanıta dayalı yanıt |
|------|---------------------|
| `frontend/` var mı? | Evet — 2 dosya |
| Canlı üretim yüzeyi mi? | **Hayır** — build/deploy zincirinde yok |
| Birincil kullanıcı yüzeyi adayı mı? | **Hayır** — OD-043 taslak üretim `ui/` |
| Kök E2E paket kapısında mı? | **Hayır** — kök `e2e:*` yalnızca `panel/` |
| İzole köprü E2E hedefi mi? | **Evet** — `run-frontend-task-loading.mjs` |
| `ui/` veya `panel/` ile aynı kod tabanı mı? | **Hayır** — ayrı dizin, ayrı dosyalar |

---

## frontend/ ile ui/ ayrımı

**Sabit kural:** `frontend/` ile `ui/` **aynı şey değildir**.

| Boyut | **`frontend/`** | **`ui/`** (`lumos-core-ui`) |
|-------|-----------------|------------------------------|
| Teknoloji | Tek HTML dosyası + gömülü JS | Astro statik site |
| Paket | Yok | `ui/package.json` |
| Root build | Dahil değil | `npm run build` hedefi |
| Vercel deploy | Dahil değil | `ui/dist` çıktısı |
| Üretim rotası | Yok | `/` landing + `/panel` (`ui/src/pages/panel.astro`) |
| Dosya sayısı | 2 (monolit) | Astro proje yapısı (`src/pages/`, …) |

**Karıştırma riski:** Dizin adı «frontend» genel web terimiyle `ui/` (gerçek deploy yüzeyi) sanılabilir. Ürün dili «panel» dediğinde bu otomatik olarak `frontend/` dizinine işaret etmez.

**Taslak pozisyon:** Dış kullanıcıya sunulan web yüzeyi adayı **`ui/`**'dir (`primary-user-surface-decision.md`, `vercel.json`). `frontend/` bu kanala **dahil değildir**.

---

## frontend/ ile panel/ ayrımı

**Sabit kural:** `frontend/` ile `panel/` **aynı şey değildir**.

| Boyut | **`frontend/`** | **`panel/`** (`lumos-panel`) |
|-------|-----------------|------------------------------|
| Yapı | Tek `index.html` monolit | `index.html` + `js/` + `css/` + `e2e/` |
| Paket | Yok | `panel/package.json` |
| Kök E2E expose | Hayır | `e2e:package`, `e2e:package:api`, `e2e:tasks-offline-online` |
| Yerel çalıştırma | Belgesiz; E2E script statik sunucu kurar | `panel/README.md`: `python3 -m http.server 8080` |
| Başlık / isim | HTML `<title>`: «Lumos panel» | Panel statik uygulama; hash routing (`#yanit`, …) |
| Mock/fixture | Köprü E2E gerçek `POST /task` kullanır | Mock/fixture ağırlıklı geliştirme yüzeyi |

**Karıştırma riski:**

1. `frontend/index.html` başlığı «Lumos panel» — `panel/` dizini ve `ui/.../panel.astro` ile isim çakışması.
2. Her iki yüzey de görev gönderme / analiz kartı desenine sahip olabilir; kod tabanları **ayrıdır**.
3. Kök E2E `panel/` statik uygulamayı test eder; `frontend/` yalnızca **ayrı** `run-frontend-task-loading.mjs` ile test edilir.

**Taslak pozisyon:** `panel/` kök E2E kalite kapısı ve operatör geliştirme yüzeyidir (`build-e2e-surface-alignment-decision.md`). `frontend/` bu kapının **parçası değildir**; izole köprü prototipidir.

---

## Build / deploy / E2E ilişkisi

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
                    ┌──────────┐                │
                    │ vercel   │         ┌──────────────┐
                    │ ui/dist  │         │  frontend/   │  ← kök script yok
                    └──────────┘         │  index.html  │
                                         │  (izole E2E) │
                                         └──────────────┘
                                                ▲
                                                │
                              panel/e2e/run-frontend-task-loading.mjs
                              (manuel / panel içi çalıştırma)
```

| Kanal | `frontend/` dahil mi? | «Üretim kanıtı» sayılır mı? |
|-------|----------------------|-----------------------------|
| Root `npm run build` | **Hayır** | Hayır |
| Vercel deploy (`vercel.json`) | **Hayır** | Hayır |
| Root `npm run e2e:*` | **Hayır** | Hayır |
| `panel/e2e/run-frontend-task-loading.mjs` | **Evet** (tek tüketici) | Köprü E2E kanıtı; üretim/deploy kanıtı **değil** |

**Sabit kural:** Root build ve Vercel hattı `frontend/` hedeflemiyorsa, bu üretim/deploy kanıtı **değildir**.

**OD-046 çapraz not:** Üretim adayı `ui/`, kök E2E `panel/` — `frontend/` bu ikisinin dışında üçüncü bir HTML yüzeyidir. Hizalama kararı `frontend/` yaşam döngüsünü doğrudan çözmez.

---

## Yaşam döngüsü seçenekleri

Aşağıdaki seçenekler **karar değildir** — bilinçli değerlendirme adaylarıdır. Kod, taşıma veya silme işlemi seçim yapılmadan yapılmaz.

| Seçenek | Özet | Artı | Eksi / risk |
|---------|------|------|-------------|
| **A — Arşivle** | `frontend/` → `archive/` veya eşdeğer; dizin adı repo kökünden kaldırılır | Canlı/aday karışıklığı azalır; isim çakışması biter | `run-frontend-task-loading.mjs` yolu güncellenmeli; köprü E2E kaybı |
| **B — E2E/prototip olarak koru** | Dizin kalır; rol açıkça «köprü E2E + prototip» yazılır; üretim yüzeyi sayılmaz | Mevcut köprü E2E korunur; düşük taşıma maliyeti | «Lumos panel» başlığı ve `frontend/` adı karışıklığı sürer; bakım yükü |
| **C — `ui/` içine taşı** | Monolit veya parçalanmış içerik Astro projesine migrasyon | Tek deploy yüzeyi; üretim/E2E hizasına katkı (OD-046 ile koordineli) | Büyük diff; `index.html` ~8.800 satır; Astro mimarisine uyum kararı gerekir |
| **D — Tamamen kaldır** | Dizin ve bağlı E2E silinir | En az karmaşıklık; hayalet yüzey kalmaz | Köprü görev yükleme E2E kaybı; alternatif test yüzeyi gerekir |

**Not:** `project_memory_v1.js` şu an `index.html` tarafından kullanılmıyor; C veya D seçeneğinde ayrı değerlendirme gerekir (taşınmamış legacy parça).

---

## Karar taslağı

### Belge statüsü

| İfade | Durum |
|-------|--------|
| Bu belge uygulama değildir; kod değiştirmez | **Sabit** |
| `frontend/` mevcut durumda canlı üretim yüzeyi kabul edilmez | **Sabit** |
| Root build + Vercel `frontend/` hedeflemiyorsa → üretim/deploy kanıtı değildir | **Sabit** |
| Rol netleşene kadar (prototip / köprü E2E / legacy / arşiv adayı) canlı yüzey sayılmaz | **Sabit** |
| `frontend/` ≠ `ui/` | **Sabit** |
| `frontend/` ≠ `panel/` | **Sabit** |
| Yaşam döngüsü seçeneği (A/B/C/D) | **Seçenek B onaylandı** — izole köprü E2E + prototip referans; üretim/deploy/root build/root E2E yüzeyi değil |

### Kanıta dayalı taslak pozisyon

| Bağlam | `frontend/` rolü (taslak) | Kesinlik |
|--------|---------------------------|----------|
| Üretim / dış kullanıcı | **Dahil değil** | Sabit |
| Root build çıktısı | **Dahil değil** | Sabit |
| Vercel deploy | **Dahil değil** | Sabit |
| Kök E2E paket kapısı | **Dahil değil** | Sabit |
| İzole köprü E2E hedefi | **Evet** — `run-frontend-task-loading.mjs` | Repo kanıtı |
| Teknik kimlik | Monolit HTML prototip + kullanılmayan yardımcı JS | Repo kanıtı |
| `project-map` etiketi | «Eski/alternatif frontend» `[needs-review]` | Kayıt hizalı |

### Henüz kabul edilmeyen varsayımlar

- «`frontend/` = birincil web yüzeyi»
- «`frontend/` = `ui/` kaynağı veya Astro build girdisi»
- «`frontend/` = `panel/` statik uygulaması»
- «Kök build/E2E zaten `frontend/`'i kapsıyor»
- «Dizin adı genel terim olduğu için otomatik canlı sayılır»

### Özet taslak cümlesi (OD-044)

**`frontend/`** bugün repo kökünde duran, **üretim ve kök build/deploy zincirine dahil olmayan**, yalnızca **izole köprü E2E** (`run-frontend-task-loading.mjs`) ile ilişkilendirilmiş bir **HTML prototip adayıdır**. `ui/` ve `panel/` ile **aynı yüzey değildir**. Yaşam döngüsü (arşiv / koru / taşı / kaldır) **açık karar bekliyor**.

---

## Kod değişikliği öncesi kural

Görev veya PR açılmadan önce:

1. **Hedef yüzeyi açık yaz:** `ui/`, `panel/` veya `frontend/` — üçü birden veya belirsiz «frontend/panel» **yasak**.
2. **`frontend/` dosyalarına dokunma:** Açık hedef ve yaşam döngüsü kararı (veya OD-044 kapanışı) olmadan `frontend/` altında değişiklik yapılmaz.
3. **Kanal belirt:** deploy (`ui/dist`), kök E2E (`panel/`), izole köprü E2E (`frontend/` + `run-frontend-task-loading.mjs`) — üçü farklı komut zincirleri.
4. **Üretim değişikliği** → varsayılan aday `ui/`; `frontend/` değişikliği üretimi **otomatik** güncellemez.
5. **Bridge / token:** `ui/` prod bundle (`PUBLIC_KANDO_TOKEN`) ile `frontend/` runtime-input deseni karıştırılmaz; güvenlik sınırı `docs/lumos-karar-sozlesmesi.md`.
6. **İş akışı:** Tek hedef, dar kapsam (`docs/memory/project-workflow.md` §2) — `frontend/` «yan düzeltme» hedefi olarak kullanılmaz.

---

## Riskler

| Risk | Açıklama | Öncelik |
|------|----------|---------|
| **İsim çakışması** | `frontend/` dizin adı vs genel «frontend» terimi vs `frontend/index.html` başlığı «Lumos panel» | Yüksek |
| **Üçlü panel karışıklığı** | `panel/` dizini + `ui/.../panel.astro` + `frontend/` «Lumos panel» başlığı | Yüksek |
| **Hayalet üretim sanısı** | Dizin var diye canlı yüzey varsayımı | Yüksek |
| **E2E kopukluğu** | Kök E2E `panel/`; köprü E2E `frontend/` — ikisi farklı kod | Orta |
| **Monolit bakım** | Tek `index.html` ~8.800 satır; migrasyon maliyeti belirsiz | Orta |
| **Kullanılmayan dosya** | `project_memory_v1.js` import edilmiyor; amaç belirsiz | Düşük |
| **Stale memory** | Eski notlarda `frontend/` = canlı veya `ui/` ile özdeş iddiası | Orta |

---

## Açık kararlar

| ID | Soru | Bu belgedeki durum |
|----|------|-------------------|
| **OD-044** | `frontend/` rolü ve yaşam döngüsü? | **Kapandı (closed):** Seçenek B — izole köprü E2E + prototip; üretim/canlı değil |
| **OD-043** | Birincil yüzey `panel/`, `ui/` veya `frontend/` mi? | **Kapandı (closed):** birincil `ui/`; `frontend/` birincil değil |
| **OD-046** | Root build (ui) ile kök E2E hangi yüzeyi «canlı» sayar? | **Kapandı (closed):** kök E2E `ui/dist`; `frontend/` dışında |

Seçenek B kapsamında kod/taşıma/arşiv/silme **yapılmaz**. A/C/D veya hibrit değişiklik ayrı görev gerektirir.

---

## OD eşleme tablosu

| ID | Kaynak | Konu | Bu belgede netleşen | Durum | Çapraz not |
|----|--------|------|---------------------|--------|------------|
| **OD-044** | project-map-runtime-entrypoints.md | `frontend/` rolü ve yaşam döngüsü | Seçenek B: izole köprü E2E + prototip; canlı değil | **closed** | Bu belgenin ana konusu |
| **OD-043** | project-map-runtime-entrypoints.md | Birincil kullanıcı yüzeyi | Birincil `ui/`; `frontend/` birincil değil | **closed** | primary-user-surface-decision.md |
| **OD-046** | project-map-runtime-entrypoints.md | Root build vs kök E2E | Kök E2E `ui/dist`; `frontend/` zincirde yok | **closed** | build-e2e-surface-alignment-decision.md |

---

## Onaylı karar (Seçenek B)

| Karar | İfade |
|-------|--------|
| Yaşam döngüsü | **B — E2E/prototip olarak koru** — dizin kalır; rol «izole köprü E2E + prototip referans» |
| Üretim / deploy | **Dahil değil** — root build, Vercel, kök E2E kapısında yok |
| Birincil yüzey | **Değil** — OD-043 **closed** ile birincil `ui/` |
| Kod değişikliği | **Yok** — taşıma, arşiv, silme veya `ui/` migrasyonu (Seçenek C) ayrı görev |
| `run-frontend-task-loading.mjs` | **Korunur** — izole köprü E2E hedefi olarak kalır |
| `project_memory_v1.js` | **Korunur** — `index.html` import etmiyor; ayrı legacy parça; B kapsamında dokunulmaz |

**Özet onaylı cümle (OD-044):** `frontend/` izole köprü E2E + HTML prototip referansı olarak **korunur**; üretim, deploy, root build ve kök E2E yüzeyi **değildir**. Birincil yüzey `ui/` (OD-043). Kök E2E hizası `ui/dist` (OD-046).

---

## OD-044 kapanış checklist

- [x] Seçenek B onaylandı (A/C/D seçilmedi)
- [x] Canlı / birincil / üretim yüzeyi reddi sabit
- [x] `frontend/` ≠ `ui/` ≠ `panel/` ayrımı belgelendi
- [x] OD-043 / OD-046 çapraz referanslar **closed**
- [x] `open-decisions-needs-review.md` OD-044 **closed**
- [x] Kod/taşıma/arşiv/silme kapsam dışı

**Sonraki adım (opsiyonel, ayrı görev):** Seçenek A/C/D veya `project_memory_v1.js` temizliği yalnızca açık kullanıcı komutu ile.

---

Son güncelleme: 2026-06-20 (OD-044 closed — Seçenek B)
