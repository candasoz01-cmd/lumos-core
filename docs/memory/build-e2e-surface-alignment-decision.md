# Root build vs panel E2E — yüzey hizası karar taslağı (OD-046)

**Durum:** `[decision-draft]` — uygulama değildir; kod, build, test veya deploy değişikliği içermez.  
**Kaynak:** `docs/memory/open-decisions-needs-review.md` (OD-046; çapraz OD-043, OD-044).  
**Doğrulama:** Repo dosya sistemi read-only tarama — 2026-06-17.

---

## 1. Amaç

Root `package.json` içindeki **build** hedefi (`ui/`) ile **E2E** hedefi (`panel/`) farklı dizinlere işaret ettiği için «hangi yüzey canlıdır?» sorusunu (OD-046) kanıta dayalı bir **karar taslağı** olarak netleştirmek.

Bu belge:

- **Uygulama belgesi değildir** — hiçbir kod, build scripti, E2E migrasyonu veya deploy değişikliği önermez veya yapmaz.
- Çekirdek sözleşme (`docs/lumos-karar-sozlesmesi.md`) üst sınır olarak geçerlidir.
- OD-043 (birincil kullanıcı yüzeyi) kapanmadan «tek canlı yüzey» kesin kararı verilmez; bu belge OD-046 özelinde build/E2E «canlı» tanımını ayırır.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| `ui/`, `panel/`, `frontend/` kod değişikliği | OD-046 yalnızca karar taslağıdır |
| Root `package.json` script değişikliği | Bilinçli hizalama kararı sonrası ayrı görev |
| E2E migrasyonu (`panel/` → `ui/dist`) | Uygulama kararı bekliyor |
| `api/bridge/`, `backend/`, `src/` Python çekirdeği | Runtime giriş zinciri ayrı belgede |
| OD-043 kesin kapanışı | Bu belge önkoşul sağlar; tek başına kapatmaz |
| OD-044 (`frontend/` yaşam döngüsü) | Yalnızca çapraz not; ayrı karar |
| `lumos web` / `web/app.py` | OD-028; bu belgenin konusu değil |

---

## 3. Mevcut build ve E2E gerçekliği (evidence from repo)

### 3.1 Root `package.json` scriptleri

```json
"build": "cd ui && npm install && npm run build",
"e2e:package": "npm run e2e:package --prefix panel",
"e2e:package:api": "npm run e2e:package:api --prefix panel",
"e2e:tasks-offline-online": "npm run e2e:tasks-offline-online --prefix panel"
```

| Script | Hedef dizin | Çıktı / davranış |
|--------|-------------|------------------|
| `npm run build` (kök) | `ui/` | Astro build → `ui/dist` |
| `npm run e2e:*` (kök) | `panel/` | Playwright; `panel/index.html` statik sunucu |

**Kanıt:** Kök `package.json` — build yalnızca `ui/`; tüm expose edilen E2E scriptleri `--prefix panel`.

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

**Taslak pozisyon (sabit kural):** Root build + Vercel `ui/`'ye işaret ediyorsa → **üretim yüzeyi adayı `ui/`** (`/panel` rotası dahil). Bu, deploy kanıtı düzeyinde güçlü sinyaldir; ancak tek başına E2E hizasını garanti etmez.

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

**Taslak pozisyon (sabit kural):** Root E2E `panel/` statik uygulamayı hedefliyorsa → bu bir **kalite kapısı**dır; tek başına «üretim yüzeyi = panel/» kanıtı **değildir**.

**Ürün dili notu:** `docs/memory/ui-chat-experience.md` «panel / chat» derken ürün yüzeyini (Lumos tek dış yüzey) kasteder; bu otomatik olarak `panel/` dizinine işaret etmez.

---

## 6. Canlı yüzey ve kalite kapısı ayrımı

OD-046'nın çözmesi gereken kavram ayrımı:

| Kavram | Tanım (taslak) | Mevcut repo kanıtı | «Canlı» sayılır mı? |
|--------|----------------|--------------------|---------------------|
| **Üretim / dış kullanıcı yüzeyi** | Deploy edilen, son kullanıcının gördüğü web UI | `vercel.json` → `ui/dist`; `LUMOS_V1_READINESS.md` → `welockai.com/panel` | **Taslak: evet** (`ui/`) |
| **Root build çıktısı** | `npm run build` (kök) artifact | `ui/dist` | Üretim adayı ile **hizalı** (taslak) |
| **Root E2E kalite kapısı** | Kökten çalıştırılan paket/regresyon testleri | `panel/` statik — Playwright | **Kalite kapısı**; üretim kanıtı değil |
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

`docs/memory/primary-user-surface-decision.md` üretim için taslağı `ui/`, E2E için `panel/` olarak ayırmıştır. OD-046 bu ayrımı **build/E2E «canlı» tanımı** özelinde daraltır; OD-043'ün kesin kapanışı için **bilinçli hizalama kararı** önkoşuldur.

---

## 7. Karar taslağı

### 7.1 Belge statüsü

| İfade | Durum |
|-------|--------|
| Bu belge uygulama değildir | **Sabit** |
| Repo kesin «tek canlı yüzey» kararı vermiyor | **Sabit** — `needs-review` |
| Build + Vercel → `ui/` = üretim yüzeyi **adayı** | **Taslak** (kanıt güçlü) |
| Root E2E → `panel/` = kalite kapısı, üretim kanıtı değil | **Taslak** (kanıt güçlü) |
| İki yüzey bilinçli hizalanmadan OD-043 kapanmaz | **Sabit** |

### 7.2 Kanıta dayalı taslak pozisyon

**Üretim «canlı» yüzey (dış kullanıcı):** Taslak olarak **`ui/`** — Astro build, Vercel `ui/dist`, `/panel` rotası (`ui/src/pages/panel.astro`). Kaynak: `vercel.json`, `LUMOS_V1_READINESS.md`, root `npm run build`.

**Kalite kapısı «canlı» yüzey (kök E2E):** Taslak olarak **`panel/`** statik uygulama — `panel/index.html` üzerinde Playwright. Kaynak: root `e2e:*` scriptleri, `panel/e2e/run-package.mjs`.

**Legacy / operatör geliştirme:** `panel/` statik uygulama üretim için dokümante olarak **superseded** (`LUMOS_V1_READINESS.md` §2); ancak kök E2E hâlâ bu yüzeyi test eder → **hizasızlık devam ediyor**.

### 7.3 Henüz kabul edilmeyen varsayımlar

- «E2E yeşil = prod panel doğrulandı»
- «Build yeşil = panel E2E senaryoları geçer»
- «`panel/` ve `ui/.../panel.astro` aynı test kapsamı»
- «Kök scriptler zaten hizalı» — kanıt bunun tersini gösteriyor

### 7.4 Özet taslak cümlesi (OD-046)

**Dış kullanıcıya sunulan üretim yüzeyi** taslak olarak **`ui/` (`/panel`)** kabul edilir; **root E2E kalite kapısı** ise **`panel/`** statik uygulamayı hedefler. Bu iki hedef **bilinçli olarak ayrılmıştır** ve repo bugün **hizalı değildir**. Kesin karar ve uygulama (E2E migrasyonu, `panel/` emekliliği veya parity politikası) **beklemededir**.

---

## 8. Kod değişikliği öncesi kural

Build/E2E hizası veya yüzey değişikliği görevi açılmadan önce:

1. **Hedef yüzeyi yaz:** `ui/src/pages/panel.astro` **veya** `panel/` — «panel» tek başına yeterli değil.
2. **Kanal belirt:** deploy mu (`ui/dist`), E2E mi (`panel/` statik), yerel mock mu (`panel/README.md` akışı).
3. **Kanıt türünü ayır:** Build pass, E2E pass ve prod smoke **farklı yüzeyleri** doğrular; birini diğerinin yerine kullanma.
4. **OD-046 kapanmadan** «build ve E2E zaten aynı yüzeyi test ediyor» varsayımı yapılmaz.
5. **OD-043 kapanmadan** birincil yüzey için kesin implementasyon kararı verilmez.
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
| **OD-046** | Root build (ui) ile panel E2E hangi yüzeyi «canlı» sayar? | **Taslak ayrım:** üretim → `ui/`; kök E2E → `panel/`. **Hizalama kararı:** `needs-review` |
| **OD-043** | Birincil yüzey `panel/`, `ui/` veya `frontend/` mi? | OD-046 hizalanmadan **kapanmaz**; taslak üretim `ui/` |
| **OD-044** | `frontend/` rolü? | Root build/E2E'de yok; canlı değil — kısa çapraz not |

### OD-046 için bekleyen uygulama seçenekleri (karar değil — yalnızca çerçeve)

Bu maddeler **henüz seçilmedi**; bilinçli oturumda değerlendirilir:

| Seçenek | Özet | Etki |
|---------|------|------|
| A | Kök E2E'yi `ui/dist` veya Astro preview'a taşı | E2E = üretim yüzeyi hizası |
| B | `panel/` statik E2E'yi koru; üretim smoke ayrı kanal | İki kapı; roller açık yazılır |
| C | `panel/` statik uygulamayı emekli et; yalnızca `ui/` | E2E migrasyonu zorunlu |
| D | Parity politikası: kritik akışlar her iki yüzeyde test | Bakım maliyeti artar |

**Not:** Seçenek işaretlenmeden kod/build/test değişikliği yapılmaz.

---

## 11. OD eşleme tablosu

| ID | Kaynak | Konu | Bu belgede netleşen | Durum | Çapraz not |
|----|--------|------|---------------------|--------|------------|
| **OD-046** | project-map-runtime-entrypoints.md | Root build vs panel E2E | Üretim adayı `ui/`; kök E2E `panel/`; «canlı» = bağlama göre; hizasız | **needs-review** | Uygulama seçeneği bekliyor |
| **OD-043** | project-map-runtime-entrypoints.md | Birincil kullanıcı yüzeyi | OD-046 hizalaması önkoşul; taslak üretim `ui/` | **needs-review** | primary-user-surface-decision.md |
| **OD-044** | project-map-runtime-entrypoints.md | `frontend/` rolü | Build/E2E zincirinde değil | **needs-review** | Birincil yüzey değil |

---

## 12. Sonraki adım

**Tek önerilen adım:** OD-046 için kısa karar oturumu — §10'daki seçeneklerden (A/B/C/D veya hibrit) birinin seçilmesi: root E2E'nin üretim yüzeyi (`ui/dist` / `welockai.com/panel`) ile bilinçli hizalanıp hizalanmayacağı ve `panel/` statik uygulamanın rolünün (legacy-only / parity test / kademeli emeklilik) netleştirilmesi.

Bu adım tamamlanmadan:

- OD-046 **closed** sayılmaz.
- OD-043 **closed** sayılmaz.
- Build/E2E script değişikliği görevi açılmaz.

---

Son güncelleme: 2026-06-17
