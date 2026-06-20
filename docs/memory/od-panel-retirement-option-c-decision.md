# Panel statik uygulama emekliliği — Seçenek C (hibrit)

**Durum:** `approved-for-implementation` — kullanıcı açık komutu (2026-06-20: «sırayla hepsini bitir»).  
**Kaynak:** OD-046 tarihsel Seçenek C — [`build-e2e-surface-alignment-decision.md`](./build-e2e-surface-alignment-decision.md) §7.3; birincil E2E zaten Seçenek A ile `ui/dist` (#300–#305).  
**Çapraz:** OD-043 **closed** (birincil `ui/`); OD-046 **closed** (birincil kök E2E → `ui/`).

---

## 1. Karar özeti

**Seçenek C (hibrit — OD-027 deseni):** Statik legacy panel uygulaması **`archive/panel/`** altına taşınır (`git mv`; silme yok). **`panel/scripts/`** canlı kalır — `ui/` E2E, evidence continuity testleri ve yerel dev köprüsü bu sunucuya bağlıdır.

| Alan | Emeklilik sonrası |
|------|-------------------|
| Birincil üretim yüzeyi | `ui/` → `welockai.com/panel` |
| Birincil kök E2E | `npm run e2e:package*` → `--prefix ui` |
| Legacy statik panel | `archive/panel/` — **canlı değil** |
| Legacy kök E2E | `npm run e2e:legacy:*` → `--prefix archive/panel` |
| Canlı köprü sunucusu | `panel/scripts/panel_tasks_server.py` |
| Salt okuma köprü | `panel/scripts/read_backend_state.py` |

**Kapsam dışı:**

- `panel/scripts/` taşıma veya birleştirme (ui/e2e + pytest import yolları sabit)
- `frontend/` yaşam döngüsü (OD-044 **closed**)
- Prod deploy / Vercel değişikliği

---

## 2. Keşif kanıtı (2026-06-20)

### 2.1 panel/ envanter

| Alt alan | Dosya (git) | Canlı tüketim |
|----------|-------------|---------------|
| Statik UI (`index.html`, `js/`, `css/`) | ~550+ | **Yok** — birincil `ui/src/pages/panel.astro` |
| Legacy E2E (`panel/e2e/`) | 12 script | Yalnızca `e2e:legacy:*` |
| Köprü sunucu (`panel/scripts/`) | 2 Python | **Canlı** — ui E2E, EC2 pytest, dev runbook |
| Dokümantasyon (`panel/*.md`) | 11 | Referans; statik panel ile birlikte arşiv |

### 2.2 Canlı bağımlılıklar (scripts kalır)

```text
ui/e2e/lib/tasks-server.mjs     → panel/scripts/panel_tasks_server.py
tests/test_panel_*_ec2_*.py     → panel/scripts/panel_tasks_server.py
tests/test_evidence_*.py        → panel/scripts/panel_tasks_server.py
ui/src/pages/panel.astro        → yorum: panel_tasks_server :8766
docs/local-kando-dev-runbook.md → panel_tasks_server.py
```

### 2.3 Birincil E2E durumu (OD-046 tamam)

- Kök `e2e:package*` → `ui/dist` — CI `ui-e2e` job yeşil
- Legacy `e2e:legacy:*` → `panel/` — geçiş dönemi; arşiv sonrası `archive/panel/`

---

## 3. Onaylı uygulama paketi (M effort — ayrı PR)

| # | Adım | Detay |
|---|------|--------|
| **C-1** | Hedef dizin | `archive/panel/` (yoksa oluştur) |
| **C-2** | Taşı | `git mv` — statik panel ağacı (`index.html`, `js/`, `css/`, `e2e/`, `camera.html`, `package.json`, `package-lock.json`, `*.md`) → `archive/panel/` |
| **C-3** | Koru | `panel/scripts/` — dokunulmaz |
| **C-4** | Kök script | `package.json` `e2e:legacy:*` → `--prefix archive/panel` |
| **C-5** | README | `panel/README.md` (scripts-only stub); `archive/panel/README.md` (arşiv notu) |
| **C-6** | Docs senkron | `project-map-runtime-entrypoints.md`, `primary-user-surface-decision.md` notları |
| **C-7** | Doğrulama | pytest + CI yeşil; `e2e:legacy:package` opsiyonel smoke |

**Risk:** Düşük-Orta — büyük `git mv`; scripts yolu değişmez; birincil E2E etkilenmez.

---

## 4. Rollback planı

1. Ters `git mv`: `archive/panel/*` → `panel/` (scripts hariç).
2. Kök `package.json` `e2e:legacy:*` → `--prefix panel` geri al.
3. README revert.

---

## 5. §8 benzeri kapılar

| # | Kriter | Durum |
|---|--------|-------|
| K1 | Birincil entry değişmez | **Geçer** — `ui/` prod, `lumos` CLI |
| K2 | Test | **Gerekli** — pytest + ui-e2e |
| K3 | CI | **Gerekli** |
| K4 | Import/script yolu | **Geçer** — `panel/scripts/` sabit |
| K5 | Public sınır | **Geçer** |
| K6 | Rollback | **Tanımlı** — §4 |
| K7 | Kalıcı silme yok | **Geçer** — arşiv + trash kuralı |

---

## 6. İndeks senkronu

- Yeni OD yok — OD-043/046 kapsamında operasyonel emeklilik
- `decision-log.md` — DL-C09 (karar); DL-A20 (uygulama)
- `open-decisions-needs-review.md` — not güncellemesi (prod smoke A3 ayrı)

---

Son güncelleme: 2026-06-20 (Seçenek C karar — kullanıcı onayı)
