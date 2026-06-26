# Python Packaging Spike — RB-06 / G-17

| Alan | Değer |
|------|-------|
| **Belge türü** | Teknik spike (plan only) |
| **Tarih** | 2026-06-21 |
| **Durum** | **Spike tamamlandı** — uygulama defer (Commercial Launch P1) |
| **Kaynak** | [release-blockers.md](release-blockers.md#rb-06-python-paketleme-kando-bağımlılıkları-wheel-dışında), [pre-commercial-release-plan.md](pre-commercial-release-plan.md) |

---

## Problem

Bugün `pip install -e .` yalnızca `lumos-core` (`src/`) kurar. `kando_runtime` ve `kando_bridge` ayrı paketlerdir; CI ve `make test` **PYTHONPATH** ile birleştirilir:

```
src:packages/kando_runtime/src:packages/kando_bridge/src
```

**Kapanış koşulu (RB-06):** Tek `pip install` sonrası gate/bridge import edilebilir; CI aynı test setini PYTHONPATH olmadan geçer.

**Alpha defer:** Internal Alpha self-host geliştirici kitlesi küçük; Pro müşteri barındırılan hizmet bekler ([pre-commercial-release-plan.md](pre-commercial-release-plan.md)). Spike yeterli; tam uygulama Commercial Launch dilimine bırakılır.

---

## Mevcut kanıt

| Dosya | Gerçek |
|-------|--------|
| `pyproject.toml` | `lumos-core` 0.1.0; `package-dir = { "" = "src" }` |
| `packages/kando_runtime/pyproject.toml` | Ayrı paket |
| `packages/kando_bridge/pyproject.toml` | Ayrı paket |
| `.github/workflows/ci.yml` L31–33 | PYTHONPATH export zorunlu |
| `Makefile` L3, L40–41 | `TEST_PYTHONPATH` aynı üçlü |
| `requirements.txt` L1 | PYTHONPATH yorumu |

---

## Seçenekler

### A — Meta-package `lumos-core-all` (önerilen dar dilim)

Yeni kök `packages/lumos_core_all/pyproject.toml`:

- `dependencies = ["lumos-core", "kando-runtime", "kando-bridge"]` (path veya PyPI)
- Yerel geliştirme: `[tool.setuptools.packages.find]` yerine PEP 508 path deps veya `pip install -e ./packages/...` zinciri tek komutta

**Artı:** Mevcut üç paket yapısı korunur; RB-15 semver ayrımı sürer.  
**Eksi:** Dört `pyproject.toml` bakımı; path dep sürüm kilidi gerekir.

**Dar PR kapsamı (Launch):** meta-package + `pip install -e packages/lumos_core_all` + CI adımı PYTHONPATH kaldırma.

### B — Monorepo tek wheel (namespace birleşik)

Tek `pyproject.toml` altında `src/`, `kando_runtime/src`, `kando_bridge/src` find.

**Artı:** Tek `pip install -e .` gerçekten yeterli.  
**Eksi:** RB-15 versiyon parçalanması çözülür ama paket sınırları bulanıklaşır; OD-027 hibrit geçiş ile çelişme riski.

### C — Dokümante edilmiş dev kurulum (Alpha minimum)

README + `docs/dev-commit-guard.md`: zorunlu PYTHONPATH / `make test` — packaging değişikliği yok.

**Artı:** Sıfır kod riski.  
**Eksi:** RB-06 **kapanmaz**; Commercial Launch hard blocker kalır.

---

## Öneri

| Aşama | Karar |
|-------|-------|
| **Internal Alpha** | **Seçenek C** — mevcut `make test` + PYTHONPATH yeterli |
| **Commercial Launch (dar dilim)** | **Seçenek A** — meta-package; CI PYTHONPATH kaldırma ayrı PR |
| **Reddedilen (şimdilik)** | Seçenek B — mimari merge maliyeti yüksek |

---

## Uygulama sırası (Launch — uygulama bekliyor)

1. **PR-PKG-01 (docs):** README «Developer install» — PYTHONPATH veya `make test` (Alpha).
2. **PR-PKG-02 (spike impl):** `lumos-core-all` meta-package taslağı; yerel `pip install` smoke test.
3. **PR-PKG-03 (CI):** CI job PYTHONPATH kaldır; meta-package `-e` install.
4. **PR-PKG-04 (verify):** `pytest` + panel bridge import testleri PYTHONPATH'siz.

**Tahmini:** 3–5 gün (Launch P1); Alpha'da uygulanmaz.

---

## Çapraz referanslar

| ID | Bağlantı |
|----|----------|
| RB-06 | Bu spike |
| G-17 | Launch P1 |
| RB-08 | Publish CI — packaging sonrası |
| OD-027 | Hibrit `src/` + packages — meta-package ile uyumlu |

---

*Son güncelleme: 2026-06-21 — spike only; kod/CI değişikliği yok.*
