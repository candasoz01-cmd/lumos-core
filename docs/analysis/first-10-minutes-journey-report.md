# İlk 10 Dakika Yolculuğu — Soğuk Başlangıç Analizi

**Tarih:** 2026-06-26  
**Kapsam:** Yeni geliştirici, repoyu ilk kez açıyor; kod değişikliği yok.  
**Yöntem:** README, Makefile, paket yapısı, `ui/` girişi, panel/köprü belgeleri, mevcut gap analizleri.

---

## Timeline (Dakika 0–10)

| Dakika | Ne olur | Başarı / sürtünme |
|--------|---------|-------------------|
| **0** | GitHub'dan klonlar. README **Quick Start** 3 adım: `cd ui` → `npm install` → `npm run dev`. CONTRIBUTING yok (README: "later"). | Klon OK. |
| **1** | `cd ui && npm install`. Node `<22.12` ise `engines` uyarısı/hata riski; Quick Start bunu söylemiyor (Developer Setup'ta var). | Sürtünme: önkoşul gizli. |
| **2–3** | `npm run dev` → Astro `http://localhost:4321`. | **İlk gerçek başarı:** landing yüklenir (TR, welockai.com canonical meta). |
| **4** | "Geliştirici Panelini Aç" → `/panel`. Sınırlı mod rozeti, bağlantı durumu. | Panel kabuğu açılır; sohbet/köprü yoksa "bağlantı yok" UX. |
| **5** | Sohbet veya görev dener. `.env.local` yok; köprü yok; görev sunucusu yok. Chat URL prod'da `/api/bridge/chat` veya uzak Render'a gidebilir. | **Beklenti kırılması:** README "çalıştırdım" hissi vs panel "çalışmıyor". |
| **6** | README'ye döner: backend "optional", bridge "optional", Deploy bölümü erken gelir. `Makefile` Python/test dünyası; Quick Start'ta yok. | İki paralel mental model: "sadece UI" vs "Lumos = panel + köprü + Python". |
| **7** | `panel/` klasörü görür; `archive/panel/` legacy. `docs/project-map.md` olmadan `ui/` vs `panel/` karışır. | İsimlendirme sürtünmesi. |
| **8** | Landing'de **#kurulum** 8 adımlı rehber (clone → env → bridge → tasks → `vercel dev` → `npm run dev`). README Quick Start ile **çelişir**. | "Doğru yol hangisi?" |
| **9** | `docs/local-kando-dev-runbook.md` bulunursa port tablosu (4321 / 3000 / 8765 / 8766), `vercel dev` vs `npm run dev` netleşir. | Derin belge iyi; keşif maliyeti yüksek. |
| **10** | `make install` / `lumos` CLI keşfedilmez veya Python venv kurulmamışsa atlanır. `docs/tr/`, `README.tr.md` 404. | TR giriş kırık; Python yolu görünmez. |

**10. dakikadaki tipik durum:** Landing + panel kabuğu açık; tam özellik yok; hangi belgenin otorite olduğu belirsiz.

---

## Blockers

### P0 (ilk 10 dakikada akışı kıran)

| ID | Sorun | Kanıt |
|----|-------|-------|
| **B-P0-1** | **README Quick Start ile gerçek "çalışan panel" yolu uyumsuz.** Quick Start 3 adım; landing #kurulum 8 adım + köprü + `vercel dev`. Yeni gelen README ile yetinir, panelde köprü/görev kırık görünür. | `README.md` L51–58 vs `ui/src/pages/index.astro` L2634–2758 |
| **B-P0-2** | **Kırık Türkçe giriş linkleri.** `README.tr.md` ve `docs/tr/` README'de referanslı; repoda yok. | `README.md` L3; glob 0 sonuç |
| **B-P0-3** | **Tek "altın yol" yok; doc giriş noktaları parçalı.** README, landing kurulum, `local-kando-dev-runbook`, `scripts/README_kando_bridge_server.md`, `panel/README.md`, `backend/README.md`, `Makefile`, `docs/project-map.md` — hepsi farklı derinlikte. | `docs/analysis/release-readiness-gap-analysis.md` GAP-02, GAP-29 |

### P1 (ilerleyebilir ama yanlış yönlendirir)

| ID | Sorun |
|----|-------|
| **B-P1-1** | **`ui/` vs `panel/` vs `archive/panel/`** — birincil panel `ui/src/pages/panel.astro`; `panel/` yalnızca Python scriptleri. |
| **B-P1-2** | **`npm run dev` (4321) vs `vercel dev` (3000)** — görev proxy `/api/bridge/*` için `vercel dev` gerekir; README Quick Start bunu söylemiyor. |
| **B-P1-3** | **Node >= 22.12 Quick Start'ta yok** — `ui/package.json` `engines`. |
| **B-P1-4** | **Python CLI/Makefile görünmez** — `make install`, `lumos`, `make test` README Quick Start zincirinde değil. |
| **B-P1-5** | **"Core" dev dilinde, "Lumos" ürün dilinde** — köprü belgeleri Core adını taşır; yeni gelen marka sınırını anlamak zorunda. |
| **B-P1-6** | **Stale doc riski** — `STABILIZASYON_LISTESI.md` vs güncel `panel/README.md`; backend `/posts/feed` 410 vs eski checklist (GAP-30). |

---

## Quick wins (yalnızca dokümantasyon)

| ID | Fix | Efor |
|----|-----|------|
| **QW-1** | README **Quick Start**'ı iki katmanlı yap: **(A) 5 dk — UI only** + **(B) Tam yerel dev → `docs/local-kando-dev-runbook.md` + landing #kurulum linki**. | Düşük |
| **QW-2** | Kırık linkleri düzelt: `README.tr.md` / `docs/tr/` ya oluştur ya README'den kaldır. | Düşük |
| **QW-3** | README başına **Prerequisites** kutusu: Node >= 22.12; opsiyonel Python 3.10+, `vercel` CLI. | Düşük |
| **QW-4** | **`docs/getting-started.md`** (tek canonical): port tablosu, "limited vs full", `ui/` = welockai.com yüzeyi, `panel/` = script-only. | Orta |
| **QW-5** | README **Developer Setup**'tan hemen sonra `docs/project-map.md` linki. | Düşük |
| **QW-6** | Landing #kurulum adım 0: "Yalnızca arayüz için README Quick Start yeterli; tam panel için adım 4–8". | Düşük |

---

## What's already good

- Landing (`ui/src/pages/index.astro`) **8 adımlı yerel kurulum** — kopyala-yapıştır, env, köprü, `vercel dev` ayrımı net.
- **`ui/.env.example`** ve **`.env.example`** yorumlu; runbook'a işaret ediyor.
- **`docs/local-kando-dev-runbook.md`** — port drift, `127.0.0.1` vs `localhost`, Phase 1 proxy, smoke adımları.
- **`docs/project-map.md`** — `ui/` birincil, `panel/` legacy ayrımı canonical.
- **`docs/integrations-overview.md`** — welockai.com yüzeyleri vs OSS sınırı açık.
- Panel **Sınırlı mod** rozeti ve limited UX mevcut.
- **`.env.example` → `.env.local`** landing'de adım 4 olarak var.

---

## Önerilen altın yol (yeni gelenler)

### Katman A — "İlk 5 dakika" (tek terminal, garantili başarı)

```bash
git clone https://github.com/candasoz01-cmd/lumos-core
cd lumos-core/ui
# Node >= 22.12 gerekli
npm install
npm run dev
```

1. `http://127.0.0.1:4321/` — landing (birincil başarı)
2. `http://127.0.0.1:4321/panel` — panel kabuğu, **Sınırlı mod** (köprü olmadan normal)

**Beklenti metni:** "Sohbet ve köprü görevleri Katman B gerektirir; Sınırlı mod yerel keşif içindir."

### Katman B — "Tam yerel dev" (10+ dk, 3–4 terminal)

Canonical kaynak: **`docs/local-kando-dev-runbook.md`**

1. `cp ui/.env.example ui/.env.local`
2. `export KANDO_BRIDGE_SECRET='test123'` → `./scripts/bridge_start.sh`
3. `python3 panel/scripts/panel_tasks_server.py`
4. Depo kökünde: `BRIDGE_UPSTREAM_URL` + `KANDO_BRIDGE_SECRET` → **`vercel dev`** → `http://127.0.0.1:3000/panel`
5. Sohbet için: Python venv + `OPENAI_API_KEY` (runbook)

**Mimari not:** Birincil web yüzeyi **`ui/`** (welockai.com deploy hedefi); **`panel/`** yalnızca görev sunucusu scriptleri.

---

## Özet tablo

| Metrik | Değer |
|--------|-------|
| İlk başarı anı | ~3 dk — landing @ :4321 |
| "Panel çalışıyor" algısı | ~5 dk — `/panel` shell |
| Tam connected mod | 10 dk **yetmez**; runbook + çoklu süreç |
| CONTRIBUTING | Yok |
| Getting-started doc | Yok (dağınık) |

---

## Top 3 blockers

1. **P0:** README Quick Start (3 adım) vs landing/runbook (8 adım + köprü) — panel "bozuk" görünür.
2. **P0:** Kırık `README.tr.md` / `docs/tr/` linkleri.
3. **P0:** Tek canonical onboarding yok; 6+ belge giriş noktası.

## Top 3 quick wins

1. README Quick Start'ı **Katman A / Katman B** olarak böl + runbook linki.
2. Kırık TR linklerini kaldır veya minimal stub ekle.
3. **`docs/getting-started.md`** — port tablosu, `ui/` vs `panel/`, `npm run dev` vs `vercel dev`.
