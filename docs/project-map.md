# Proje haritası — kalıcı repo kaydı

**Durum:** Proje haritası (kod değildir).  
**Genişletilmiş canonical:** `docs/memory/project-map-runtime-entrypoints.md`

Repo kökü, aktif giriş zinciri ve sık karıştırılan dizinlerin **kalıcı özeti**. Dosya sistemi ile doğrulandı: 2026-06-17.

---

## Proje kökü

| Alan | Değer | Statü |
|------|--------|--------|
| **Aktif proje kökü** | `lumos-core` | **proje haritası** |
| **Yerel tam yol** | `/Users/candasoz/work_2026/lumos-core` | **proje haritası** |
| **Üst klasör** | `work_2026` — tüm alt klasörler proje kökü **değildir** | **proje haritası** |

---

## Aktif runtime giriş zinciri (Python)

**Kök entry (`pyproject.toml`):**

```toml
lumos = "lumos_core.__main__:main"
```

> **Repo düzeltmesi:** Eski notlardaki `lumos_core.main:main` **geçersizdir**; repoda `src/lumos_core/main.py` yok.

**CLI zinciri:**

```
lumos  (veya python -m lumos_core)
  → src/lumos_core/__main__.py : main()
    → src/main.py : main()
      → core.lumos_runtime.create_runtime()
      → cli.cli_router.run_cli_loop(router_ctx)
```

| Öğe | Statü |
|-----|--------|
| `src/` canlı/aktif Lumos Core | **proje haritası** |
| `packages/kando_*` ayrıştırılmış mimari adayı; root entry buradan başlamaz | **proje haritası** |
| `lumos web` → `web/app.py` | **karar: B1 kaldır** — restore değil; uygulama bekliyor (OD-028). Bugün: alt komut hâlâ `__main__.py`'de, `web/` yok, komut kırık. |

---

## Web yüzeyleri ve Node paketleri

| Dizin | Paket | Rol | Statü |
|-------|--------|-----|--------|
| **`ui/`** | `lumos-core-ui` | Astro statik site; landing + `/panel` | **proje haritası** — Vercel deploy hedefi |
| **`panel/`** | `lumos-panel` | Statik panel; kök E2E (`e2e:* --prefix panel`) | **proje haritası** |
| **`frontend/`** | yok | İzole HTML prototip; köprü E2E | **ileride değerlendirilecek** (OD-044) |
| **`backend/`** | — | Express + Prisma SQLite API | **proje haritası** |
| **`api/bridge/[...path].js`** | — | Vercel serverless proxy | **proje haritası** |

---

## Root `package.json` ve build

```json
"build": "cd ui && npm install && npm run build"
```

| Soru | Repo gerçeği | Statü |
|------|--------------|--------|
| `ui/` var mı? | **Evet** — Astro projesi mevcut | **proje haritası** |
| Root build ne hedefler? | `ui/dist` | **proje haritası** |
| `vercel.json` | `outputDirectory`: `ui/dist` | **proje haritası** |
| Kök E2E | `--prefix panel` | **proje haritası** |

> Eski not: «`ui/` görünmüyorsa build şüpheli» — **güncel repo'da `ui/` mevcut**; build komutu teknik olarak çalışabilir. Birincil yüzey ve build/E2E hizası ayrı karar (OD-043, OD-046).

---

## Yerel runtime kayıtları

| Alan | Rol | Statü |
|------|-----|--------|
| **`.lumos/`** | Yerel runtime state (tasks, config, logs, trash, …) | **proje haritası** |
| **`trash/`** | Aktif state kaynağı **değil** | **proje haritası** |

---

## Ürün sınırı (harita notu)

| Madde | Statü |
|-------|--------|
| Son kullanıcıya görünen tek dış yüzey **Lumos** (`ui/` deploy yolu dahil) | **aktif kural** |
| Kando/Cando/Bando kullanıcıya gösterilmez | **aktif kural** |

---

## Şüpheli / eski notlar

| Not | Güncel durum | Statü |
|-----|--------------|--------|
| `lumos_core.main:main` entry | `lumos_core.__main__:main` | **duplicate kapatıldı** — eski not hatalı |
| `panel/` = `ui/` | Ayrı dizinler | **duplicate kapatıldı** |
| `lumos-demo` under `work_2026` | Bulunamadı | **ileride değerlendirilecek** (OD-045) |

---

## Kod değişikliği öncesi kontrol listesi

1. Hedef `src/` zinciri mi, `packages/kando_*` aday mı?
2. Panel mi (`panel/`), UI mı (`ui/`), frontend prototip mi (`frontend/`)?
3. Bridge değişikliği `api/bridge/` + upstream env ile mi?
4. Root `npm run build` → `ui/`; kök E2E → `panel/`.

---

## İlişkili belgeler

- `docs/memory/primary-user-surface-decision.md` — OD-043
- `docs/memory/build-e2e-surface-alignment-decision.md` — OD-046
- `docs/memory/frontend-role-decision.md` — OD-044

---

Son güncelleme: 2026-06-17
