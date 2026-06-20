# OD-027 Slice 3b — Ayna paket arşiv kararı

**Durum:** **`implementation-complete`** (PR #316, `1cdb0f2`).  
**Kaynak:** OD-027 Seçenek C — [`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md).  
**Önceki dilim:** Slice 3a **`implementation-complete`** (PR #313, DL-A17).  
**Keşif:** [`kando-packages-faz1-inventory.md`](./kando-packages-faz1-inventory.md), [`kando-packages-faz3-keşif-raporu.md`](./kando-packages-faz3-keşif-raporu.md).

---

## 1. Karar özeti

Dört **ölü ayna** paketi `packages/` altından **`archive/packages/`** altına taşınır (git `mv`; silme yok). Canlı paketler (`kando_bridge`, `kando_runtime`) ve canonical `src/` **dokunulmaz**.

| Paket | Canonical karşılık | Dış import (2026-06-20 grep) |
|-------|-------------------|------------------------------|
| `packages/kando_core` | `src/core/` (+ `src/lumos_core/`) | **sıfır** (`src/`, `tests/`) |
| `packages/kando_memory` | `src/memory/` | **sıfır** |
| `packages/kando_policy` | `src/security/`, `src/policy/` | **sıfır** |
| `packages/kando_context` | `src/context/` | **sıfır** (yalnızca `kando_memory` içi) |

**Kapsam dışı (Slice 3b):**

- `kando_bridge`, `kando_runtime` taşıma veya birleştirme
- PYTHONPATH / CI / `pyproject.toml` entry değişikliği (zaten yalnızca bridge+runtime)
- Faz 4 cutover veya OD-027 `migrated`/`superseded` indeks kapanışı

---

## 2. Keşif kanıtı (2026-06-20)

### 2.1 Import grep

```text
rg 'from kando_(core|memory|policy|context)|import kando_(core|memory|policy|context)' src/ tests/
→ 0 eşleşme
```

Paket içi tek çapraz import: `kando_memory` → `kando_context` (her ikisi de arşiv adayı).

### 2.2 CI / PYTHONPATH

`.github/workflows/ci.yml` — yalnızca:

```text
PYTHONPATH=.../src:.../packages/kando_runtime/src:.../packages/kando_bridge/src
```

Ayna paketler CI PYTHONPATH'te **yok**; arşiv taşıması CI davranışını değiştirmez.

### 2.3 Mevcut `archive/` deseni

Repo kökünde `archive/refactor_history/` mevcut (yedek `.py` dosyaları). Slice 3b hedefi **`archive/packages/`** — ayna paketlerin tam dizin ağacı; refactor_history ile karıştırılmaz.

---

## 3. Onaylı uygulama paketi (M effort — ayrı PR)

| # | Adım | Detay |
|---|------|--------|
| **3b-1** | Hedef dizin oluştur | `archive/packages/` (yoksa) |
| **3b-2** | Taşı | `git mv packages/kando_core archive/packages/kando_core` (ve memory, policy, context) |
| **3b-3** | Referans taraması | Docs/README'de `packages/kando_*` yollarını güncelle (canlı bridge/runtime hariç) |
| **3b-4** | Doğrulama | `pytest` + CI yeşil; kök `lumos` / bridge / runtime akışı değişmez |

**Risk:** Düşük — dış tüketim yok; taşıma geri alınabilir.

---

## 4. Rollback planı

1. **Tek commit revert** veya ters `git mv`:
   ```bash
   git mv archive/packages/kando_core packages/kando_core
   # (memory, policy, context için tekrarla)
   ```
2. Docs referans revert (3b PR ile birlikte gelen doc güncellemeleri).
3. **Veri migrasyonu yok** — `.lumos/` ve çekirdek state etkilenmez (OD-027 §11 madde 6).

---

## 5. §8 kesme kapıları — Slice 3b

| # | Kriter | Slice 3b |
|---|--------|----------|
| K1 | Entrypoint | **Geçer** — kök `lumos` → `src/`; ayna paketler entry değil |
| K2 | Test | **Gerekli** — pytest yeşil |
| K3 | CI | **Gerekli** — mevcut workflow yeşil |
| K4 | Import yolu | **Geçer** — dış import yok; PYTHONPATH değişmez |
| K5 | Güvenlik sınırı | **Geçer** — bridge/runtime/gate dokunulmaz |
| K6 | Rollback | **Tanımlı** — §4 |
| K7 | Workspace / state | **Geçer** |
| K8 | Public sınır | **Geçer** |

---

## 6. Sonraki dilimler

| Dilim | İçerik | Durum |
|-------|--------|--------|
| **3b uygulama** | Bu belge §3 | **`implementation-complete`** (PR #316) |
| **4** | Cutover onayı | **`implementation-complete`** — [`od-027-faz4-cutover-decision.md`](./od-027-faz4-cutover-decision.md) |
| **5** | İndeks `migrated` / `superseded` | **Tamamlandı** (Faz 4) |

---

## 7. İndeks / DL senkronu

- `open-decisions-needs-review.md` OD-027 — Slice 3b **complete** (PR #316)
- `decision-log.md` — DL-C07 (karar); **DL-A18** (uygulama — PR #316)
- `kando-packages-faz3-keşif-raporu.md` §5 — 3b **`approved-for-implementation`**

---

Son güncelleme: 2026-06-20 (Slice 3b **implementation-complete** — PR #316)
