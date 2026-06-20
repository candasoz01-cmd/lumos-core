# OD-027 Faz 4 — Kesme (cutover) kararı

**Durum:** `approved-for-implementation` — kullanıcı açık komutu (2026-06-20: «sırayla hepsini bitir»).  
**Kaynak:** OD-027 Seçenek C — [`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md).  
**Önceki dilimler:** Slice 3a **`implementation-complete`** (PR #313); Slice 3b **`implementation-complete`** (PR #316).  
**Keşif:** [`kando-packages-faz3-keşif-raporu.md`](./kando-packages-faz3-keşif-raporu.md), [`od-027-slice-3b-archive-decision.md`](./od-027-slice-3b-archive-decision.md).

---

## 1. Karar özeti

**Faz 4 cutover = formal kapanış.** Kod taşıma/arşiv işi Slice 3a–3b ile tamamlandı; Faz 4 yalnızca §8 kesme kapılarının nihai doğrulaması, indeks senkronu ve «geçiş tamamlandı» ilanını kapsar.

| Alan | Cutover sonrası durum |
|------|------------------------|
| Canlı çekirdek | `src/` (canonical) |
| Canlı paketler | `packages/kando_bridge`, `packages/kando_runtime` |
| Arşiv ayna paketler | `archive/packages/kando_{core,memory,policy,context}` |
| Root entry | `pyproject.toml` → `lumos_core.__main__` → `src/main.py` |
| PYTHONPATH | `src:kando_runtime:kando_bridge` (değişmez) |

**Kapsam dışı (Faz 4):**

- Bridge/runtime → `src/` birleştirme (Seçenek A alt kümesi; opsiyonel Faz 5+)
- `kando-ai/` ürünleştirme
- `panel/` / `ui/` yüzey kararları (OD-043/046 ayrı)

---

## 2. Keşif kanıtı (2026-06-20)

### 2.1 Repo durumu (main `b4e6867`)

```text
packages/           → yalnızca kando_bridge, kando_runtime
archive/packages/   → kando_core, kando_memory, kando_policy, kando_context
```

### 2.2 Import grep

```text
rg 'from kando_(core|memory|policy|context)|import kando_(core|memory|policy|context)' src/ tests/
→ 0 eşleşme
```

### 2.3 Test / CI

| Kanıt | Sonuç |
|-------|--------|
| Yerel pytest (PYTHONPATH + KANDO_MOCK=1) | **751 passed**, 2 skipped |
| CI `.github/workflows/ci.yml` | PYTHONPATH yalnızca bridge+runtime; ayna paket yok |

---

## 3. §8 kesme kapıları — Faz 4 nihai

| # | Kriter | Faz 4 |
|---|--------|-------|
| K1 | Entrypoint | **Geçer** — kök `lumos` → `src/`; çift entry yok |
| K2 | Test | **Geçer** — pytest yeşil (751 passed) |
| K3 | CI | **Geçer** — mevcut workflow (test + ui-smoke + ui-e2e) |
| K4 | Import yolu | **Geçer** — tek yönlü `packages → src`; ayna dış import sıfır |
| K5 | Güvenlik sınırı | **Geçer** — gate/bridge dokunulmadı |
| K6 | Rollback | **Tanımlı** — Slice 3b §4 (`git mv` geri) |
| K7 | Workspace / state | **Geçer** — `.lumos/` etkilenmedi |
| K8 | Public sınır | **Geçer** — production secret yok |

**Karar:** Tüm §8 kapıları geçti; cutover onaylanır.

---

## 4. Onaylı uygulama paketi (S effort — docs + README)

| # | Adım | Detay |
|---|------|--------|
| **4-1** | Karar belgesi | Bu dosya |
| **4-2** | İndeks senkronu | `open-decisions-needs-review.md` OD-027 → **closed**; `decision-log.md` DL-C08/DL-A19 |
| **4-3** | Mimari belge | `kando-packages-transition-decision.md` Faz 4/5; `project-map-runtime-entrypoints.md` §11 |
| **4-4** | Arşiv README | `archive/packages/README.md` — ayna paketler canlı değil |
| **4-5** | Doğrulama | pytest + CI yeşil |

**Risk:** Düşük — kod davranışı değişmez; yalnızca durum ilanı ve dokümantasyon.

---

## 5. Rollback planı

1. **İndeks revert** — OD-027 durumunu `approved-for-implementation` geri al.
2. **Kod geri alma gerekmez** — Slice 3b zaten bağımsız revert edilebilir (§4).
3. **Veri migrasyonu yok** — `.lumos/` etkilenmez.

---

## 6. Sonraki dilimler

| Dilim | İçerik | Durum |
|-------|--------|--------|
| **Faz 4 uygulama** | Bu belge §4 | **`approved-for-implementation`** |
| **Faz 5 (opsiyonel)** | Bridge/runtime → `src/` birleştirme; stale doc path temizliği | `needs-review` |

---

## 7. İndeks / DL senkronu

- `open-decisions-needs-review.md` OD-027 — Faz 4 cutover **complete** sonrası **closed**
- `decision-log.md` — DL-C08 (karar); DL-A19 (uygulama)
- `kando-packages-faz3-keşif-raporu.md` §5 — Dilim 4 cutover

---

Son güncelleme: 2026-06-20 (Faz 4 karar — kullanıcı onayı)
