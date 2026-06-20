# Proje haritası — runtime giriş noktaları

**Durum:** `[migrated]` — ChatGPT Saved Memories / oturum bağlamından taşındı; dosya sistemi ile doğrulandı (2026-06-17).

---

## 1. Amaç

Bu belge, Lumos Core deposunda **aktif runtime giriş zincirini**, **canlı vs aday klasör ayrımını** ve geliştirme sırasında sık karıştırılan yolları tek canonical kaynak olarak tutar. Kod değişikliği veya yeni özellik öncesi buraya bakılır; `packages/kando_*` veya eski komutlar otomatik olarak canlı kabul edilmez.

---

## 2. Proje kökü

| Alan | Değer |
|------|--------|
| **Aktif proje kökü** | `lumos-core` |
| **Yerel tam yol (dev referansı)** | `/Users/candasoz/work_2026/lumos-core` veya `~/work_2026/lumos-core` |
| **Üst klasör** | `work_2026` — tüm klasör proje kökü **değildir** |
| **Ana referans** | Bu repo (`lumos-core`) |

**Notlar:**

- `work_2026` altında `lumos-core` dışında başka dizinler de vardır (`archive`, `backend` kopyası, `lumos-quantum` vb.); bunlar ayrı çalışma alanları olabilir.
- `lumos-demo` — `work_2026` altında **yok**; aktif lumos-core parçası **değildir** (giriş noktası, build hedefi, app bağımlılığı yok). `[superseded / not-found]` OD-045 kapandı — sonradan bulunursa ayrı repo/yan klasör olarak yeniden değerlendirilir.
- Kullanıcıya özel mutlak yol bu belgede yerel dev referansı olarak tutulabilir; paylaşılan canonical ifade `~/work_2026/lumos-core` tercih edilir.

---

## 3. Aktif runtime giriş zinciri

**Kök entry point (`pyproject.toml`):**

```toml
[project.scripts]
lumos = "lumos_core.__main__:main"
```

> **Düzeltme (doğrulandı):** Eski notlarda geçen `lumos_core.main:main` **geçersiz**; repoda `src/lumos_core/main.py` yok, giriş `__main__.py` üzerinden.

**CLI (varsayılan) zinciri:**

```
lumos  (veya python -m lumos_core)
  → src/lumos_core/__main__.py : main()
    → _run_cli()
      → src/main.py : main()
        → core.lumos_runtime.create_runtime()
        → cli.cli_router.run_cli_loop(router_ctx)
```

**Diğer `lumos` alt komutları (`__main__.py`):**

| Alt komut | Hedef |
|-----------|--------|
| `cli` (varsayılan) | `src/main.py` → CLI döngüsü |
| `decision` | `core.decision_pipeline` / `core.decision_runner` |

> **OD-028 B1 (2026-06-17):** `web` alt komutu kaldırıldı; `web/app.py` restore edilmedi.

**Özet:** Aktif ana giriş hâlâ **`src/`** tarafındadır. Root `pyproject.toml` → `lumos_core.__main__` → `main` modülü (`src/main.py`).

---

## 4. Canlı / aday klasör ayrımı

| Alan | Rol | Durum |
|------|-----|--------|
| **`src/`** | Canlı Lumos Core Python kodu (CLI, core, cli, task_engine, security, …) | **Aktif** |
| **`packages/kando_bridge`, `kando_runtime`** | Canlı köprü + gate/dispatch (OD-027 C) | **Aktif paket** — kök entry değil; `src/` tüketir (PYTHONPATH) |
| **`kando-ai/`** (repo kökü) | Ayrı `main.py` içeren alt proje | **Aday / yan** — root `lumos` CLI zincirine dahil değil |
| **`archive/packages/kando_*`** | OD-027 Slice 3b ayna paketler | Canlı değil — canonical `src/` |
| **`archive/`** (diğer) | Arşiv (ör. `archive/panel/`) | Canlı değil |
| **`frontend/`** | Köprü/prototip HTML | `[migrated]` — OD-044 Seçenek B; birincil/canlı değil (`frontend-role-decision.md`) |

**`packages/` altı canlı paketler (doğrulandı):**

- `kando_bridge`
- `kando_runtime`

Her birinin kendi `pyproject.toml` ve `src/kando_*/` yapısı vardır.

**Arşiv (OD-027 Slice 3b — `archive/packages/`, canlı değil):**

- `kando_core`, `kando_memory`, `kando_policy`, `kando_context` — canonical karşılıkları `src/`; kök `lumos` bunları çağırmaz.

**Kural:** Canlı zinciri düşünürken önce `src/`; `packages/` veya `kando-ai/` canlı entry sanılmaz.

---

## 5. Panel / backend / runtime kayıtları

### Panel ve UI

| Dizin | Var mı? | Rol |
|-------|---------|-----|
| **`panel/`** | Evet | **Canlı köprü:** `panel/scripts/` only; statik UI → `archive/panel/` |
| **`archive/panel/`** | Evet | Legacy statik panel + `e2e:legacy:*` Playwright; birincil üretim değil |
| **`ui/`** | Evet | Astro tabanlı statik UI (`lumos-core-ui`); root `npm run build` burayı hedefler |

> **Düzeltme (doğrulandı):** Birincil üretim/dış kullanıcı = **`ui/`** (`ui/dist`, OD-043 **closed**). Kök E2E birincil = **`ui/dist`** (OD-046). Legacy statik panel = **`archive/panel/`** (`e2e:legacy:*`); canlı köprü = **`panel/scripts/`**.

### Backend

| Dizin | Var mı? | Rol |
|-------|---------|-----|
| **`backend/`** | Evet | Express + Prisma SQLite API; `npm run dev` → `node --watch index.js` |

### Yerel runtime kayıtları (`.lumos/`)

Çalışma kökü (CWD) altında `.lumos/` omurgası kullanılır. `src/core/workspace_contract.py` içindeki `CORE_STATE_PATH_NAMES`:

- `tasks.json`, `config`, `config.json`, `logs`, `trash`, `aliases.json`, `notes.enc.json`, `presence.json`, `identity.json`, `keystore.json`

Repoda `.lumos/` mevcut; örnek alt içerik: `config/`, `logs/`, `cursor_bridge/`, `inbox/`, `outbox/`, `patch_memory.sqlite`, `context.json` vb.

**Kural:** `trash/` aktif state kaynağı değildir; çekirdek sözleşme `docs/lumos-karar-sozlesmesi.md` ve `workspace_contract` ile uyumludur.

---

## 6. API bridge

| Dosya | Rol |
|-------|-----|
| **`api/bridge/[...path].js`** | Vercel serverless proxy: `/api/bridge/*` → `BRIDGE_UPSTREAM_URL/*` |

Desteklenen fazlar (dosya başlığı): `task`, `last-result`, `controlled`, `transcribe`. Token sunucu tarafında enjekte edilir; `BRIDGE_UPSTREAM_URL` yoksa `bridge_proxy_unconfigured` döner.

Panel ↔ köprü entegrasyonu bu katmandan geçer; Python CLI zincirinden ayrıdır.

---

## 7. Şüpheli / eski komut notları

| Komut / ifade | Durum |
|---------------|--------|
| Root `package.json` → `"build": "cd ui && npm install && npm run build"` | **`ui/` birincil build** — OD-043 **closed**; kök E2E → `ui/dist` (OD-046) |
| `lumos_core.main:main` entry | **Eski / hatalı** — güncel: `lumos_core.__main__:main` |
| `src/lumos_core/main.py` | **Yok** — zincir `__main__.py` üzerinden |
| `lumos web` → `web/app.py` | **Kaldırıldı** (OD-028 B1) — alt komut yok; `web/` restore edilmedi |
| Kök `e2e:package*` | `ui/dist` hedefler; legacy için `e2e:legacy:*` → `archive/panel/` |

---

## 8. Kod değişikliği öncesi kontrol

1. Giriş noktası `src/` zinciri mi, yoksa `packages/kando_*` aday mı?
2. `.lumos/` veya çekirdek state path’ine yazım workspace sözleşmesine uygun mu?
3. Panel mi (`panel/`) UI mı (`ui/`) hedefleniyor?
4. Bridge değişikliği `api/bridge/[...path].js` + upstream env ile mi?
5. Root `npm run build` Astro UI içindir; panel E2E ayrı scriptlerdedir.

---

## 9. Riskler

| Risk | Açıklama |
|------|----------|
| **Yanlış entry sanma** | `packages/kando_*` veya `kando-ai/` üzerinden canlı CLI varsayımı |
| **panel vs ui karışıklığı** | Birincil üretim/E2E `ui/`; legacy E2E `panel/` — hedef yüzey görevde yazılmalı |
| **Stale memory** | ChatGPT’deki `lumos_core.main` veya tek klasör (`ui` *veya* `panel`) notları güncel değil |
| **Çoklu work_2026 dizini** | Yanlış klasörde komut çalıştırma |

---

## 10. Migration tablosu

| Kaynak (ChatGPT / eski not) | Repo gerçeği | Durum |
|-----------------------------|--------------|--------|
| `lumos = lumos_core.main:main` | `lumos = lumos_core.__main__:main` | `[migrated]` düzeltildi |
| Zincir: `lumos_core/main.py` → `main.py` | `lumos_core/__main__.py` → `main.py` | `[migrated]` düzeltildi |
| Panel = `ui/` | `panel/` **ve** `ui/` ayrı dizinler | `[migrated]` düzeltildi |
| `ui/` yok → build stale | `ui/` var (Astro) | `[migrated]` — birincil yüzey `ui/` (OD-043 **closed**) |
| `packages/kando_*` = canlı entry | Root entry `src/`; packages aday | `[migrated]` |
| `lumos-demo` ayrı proje | `work_2026/lumos-demo` yok; lumos-core parçası değil | `[superseded / not-found]` OD-045 |
| `web/app.py` web sunucusu | `web/` dizini yok; `lumos web` kaldırıldı (OD-028 B1) | `[migrated]` |
| `.lumos/` runtime kayıtları | Mevcut + `CORE_STATE_PATH_NAMES` | `[migrated]` |
| `api/bridge/[...path].js` | Mevcut | `[migrated]` |
| `backend/` Express API | Mevcut | `[migrated]` |

---

## 11. Manuel eklenecek maddeler

Aşağıdaki satırlar henüz repo dışı kaynaktan işlenmedi veya doğrulanmadı:

| # | Durum | Madde | Not |
|---|--------|--------|-----|
| 1 | `[superseded / not-found]` | `lumos-demo` konumu ve lumos-core ile ilişkisi | OD-045 kapandı; `work_2026` altında yok; lumos-core parçası değil; sonradan bulunursa ayrı değerlendirme |
| 2 | `[closed]` | Birincil kullanıcı yüzeyi (OD-043) | `ui/` birincil; `panel/` legacy E2E; `frontend/` birincil değil — [`primary-user-surface-decision.md`](primary-user-surface-decision.md) |
| 3 | `[migrated]` | `lumos web` / `web/app.py` — OD-028 B1 alt komut kaldırıldı | `web/` restore yok; `__main__.py` güncellendi |
| 4 | `[closed]` | `packages/kando_*` → `src/` geçiş (OD-027) | Seçenek C; Slice 3a (#313), 3b (#316), Faz 4 cutover — [`od-027-faz4-cutover-decision.md`](od-027-faz4-cutover-decision.md); canlı yalnızca bridge+runtime |
| 5 | `[queued]` | ChatGPT Saved Memories’ten ek proje yolu / deploy notları | `chatgpt-saved-memories-migration.md` tablosuna yapıştırılacak |
| 6 | `[doc-sync-complete]` | OD-027 Faz 5 (doc-only) | Path/indeks senkronu (#317–331); bridge/runtime → `src/` birleştirme **ertelendi — ayrı oturum** — [`kando-packages-transition-decision.md`](kando-packages-transition-decision.md) Faz 5 |

---

## Hızlı referans — üst seviye dizinler

```
lumos-core/
├── src/                 # CANLI Python core + CLI
├── packages/kando_bridge, kando_runtime/  # CANLI paketler
├── archive/packages/kando_*/  # Arşiv ayna paketler (OD-027)
├── panel/scripts/       # Canlı köprü sunucuları (tasks API)
├── archive/panel/       # Legacy statik panel + E2E
├── ui/                  # Astro statik UI
├── backend/             # Express + Prisma API
├── api/bridge/          # Vercel bridge proxy
├── .lumos/              # Yerel runtime state
├── pyproject.toml       # lumos CLI entry
└── package.json         # ui build + panel e2e scriptleri
```

---

*Son doğrulama: 2026-06-20 — OD-027 Faz 5 doc sync; fiziksel bridge/runtime merge ayrı oturuma ertelendi.*
