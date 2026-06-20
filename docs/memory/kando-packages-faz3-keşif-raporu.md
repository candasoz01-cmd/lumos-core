# OD-027 Faz 3 — Keşif raporu (uygulama öncesi)

**Durum:** Slice **3a** **`implementation-complete`** (PR #313, `c0b8ea0`); Slice **3b** **`approved-for-implementation`** — [`od-027-slice-3b-archive-decision.md`](./od-027-slice-3b-archive-decision.md).  
**Kaynak karar:** [`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md) (Seçenek C — Hibrit).  
**Faz 1 envanter:** [`kando-packages-faz1-inventory.md`](./kando-packages-faz1-inventory.md).  
**Doğrulama tarihi:** 2026-06-20 (repo salt-okuma + grep).

---

## 1. Amaç

Faz 2 mimari kararı (C — Hibrit) sonrası **ilk uygulanabilir dilim** (Slice 3a) için güncel kanıt, §8 kesme kapıları durumu ve uygulama sınırını netleştirmek. Tam arşiv/cutover (Faz 4–5) bu dilimin dışındadır.

---

## 2. Keşif özeti (2026-06-20)

| Alan | Faz 1 (2026-06-18) | Faz 3 doğrulama | Değişim |
|------|--------------------|-----------------|---------|
| Canlı entry | `src/lumos_core/__main__.py` → `src/main.py` | Aynı | — |
| Canlı paketler | `kando_bridge`, `kando_runtime` | Aynı; CI PYTHONPATH değişmedi | — |
| Ayna paketler | `kando_core`, `kando_memory`, `kando_policy`, `kando_context` | Dış import hâlâ **sıfır** (`src/`, `tests/` grep) | — |
| `kando_core/__main__.py` web kalıntısı | OD-028 B1 ile kök temiz; paket stale | **Kaldırıldı** (PR #313) — yalnızca `cli` / `decision` alt komutları | 3a-2 **tamam** |
| `kando_runtime/lumos_runtime.py` | Ölü ayna | **Silindi** (PR #313); canonical `src/core/lumos_runtime.py` korundu | 3a-3 **tamam** |
| OD-043 / OD-046 | needs-review (çapraz) | **closed** — birincil `ui/`; kök E2E `ui/dist` | Geçişten bağımsız |

**Sabit:** Root `lumos` hâlâ `packages/kando_*` üzerinden başlamaz. Bridge/runtime → `src/` tek yönlü bağımlılık devam ediyor.

---

## 3. Slice 3a — uygulama paketi (S effort) `[implementation-complete — PR #313]`

Aşağıdaki dilim **merge edildi** (`c0b8ea0`); tek PR, dar kapsam, rollback kolay.

| # | Hedef | Dosya / alan | Risk | Rollback |
|---|--------|--------------|------|----------|
| **3a-1** | Import sözleşmesi yorumu | `packages/kando_bridge/README.md` veya mevcut karar belgesi referansı | Düşük | Docs revert |
| **3a-2** | `kando_core` web kalıntısı kaldır | `packages/kando_core/src/kando_core/__main__.py` — `web` parser, `_run_web()` (OD-028 B1 hizası) | Düşük | Git revert; paket zaten canlı entry değil |
| **3a-3** | Ölü `lumos_runtime` aynası kaldır | `packages/kando_runtime/src/kando_runtime/lumos_runtime.py` | Düşük | Git revert; dış import yok |

**Kapsam dışı (Slice 3a):**

- `kando_core` / `kando_memory` / `kando_policy` / `kando_context` tam arşiv taşıması (Faz 4)
- Bridge/runtime → `src/` birleştirme (Seçenek A alt kümesi)
- PYTHONPATH / CI / `pyproject.toml` entry değişikliği

---

## 4. §8 kesme kapıları — Slice 3a durumu

| # | Kriter | Slice 3a |
|---|--------|----------|
| K1 | Entrypoint | **Geçer** — kök `lumos` değişmez |
| K2 | Test | **Gerekli** — `pytest` + bridge testleri yeşil |
| K3 | CI | **Gerekli** — mevcut workflow yeşil |
| K4 | Import yolu | **Geçer** — kaldırılan modüllere dış import yok |
| K5 | Güvenlik sınırı | **Geçer** — gate/bridge dokunulmaz |
| K6 | Rollback | **Tanımlı** — git revert |
| K7 | Workspace / state | **Geçer** — `.lumos/` etkilenmez |
| K8 | Public sınır | **Geçer** — production secret yok |

**Karar:** Slice 3a, §8 kapılarını bozmaz; **PR #313 merge ile doğrulandı** (pytest + CI yeşil).

---

## 5. Sonraki dilimler (henüz onaylanmadı)

| Dilim | İçerik | Durum |
|-------|--------|--------|
| **3b** | Ayna paket arşivi (`kando_core`, `kando_memory`, `kando_policy`, `kando_context`) → `archive/packages/` | **`approved-for-implementation`** — [`od-027-slice-3b-archive-decision.md`](./od-027-slice-3b-archive-decision.md) |
| **4** | Cutover onayı | Kullanıcı açık komutu + §8 tam checklist |
| **5** | İndeks `migrated` / `superseded` | Faz 4 sonrası |

---

## 6. OD-027 durum güncellemesi

| İfade | Durum |
|-------|--------|
| Hedef mimari (Seçenek C) | **Onaylı** |
| Faz 1 envanter | **Tamamlandı** |
| Faz 2 karar | **Onaylı** |
| Faz 3 keşif (bu belge) | **Tamamlandı** |
| İlk uygulama dilimi (Slice 3a) | **`implementation-complete`** |
| Tam geçiş / arşiv | **`approved-for-implementation`** (Slice 3b karar; uygulama PR bekler) |

---

Son güncelleme: 2026-06-20 (Slice 3b **`approved-for-implementation`** — DL-C07)
