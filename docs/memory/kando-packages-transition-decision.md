# OD-027 — `packages/kando_*` → `src/` geçiş kararı

**Durum:** `decision-approved / approved-for-implementation` — Faz 2 hedef mimari onaylandı (Seçenek **C — Hibrit**); Slice **3a** uygulama onaylı ([`kando-packages-faz3-keşif-raporu.md`](./kando-packages-faz3-keşif-raporu.md)); tam arşiv/cutover bekliyor.  
**Kaynak indeks:** [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) OD-027.  
**Faz 1 envanter:** [`kando-packages-faz1-inventory.md`](./kando-packages-faz1-inventory.md) (2026-06-18).  
**Doğrulama tarihi:** 2026-06-18 (Faz 2 karar taslağı; repo salt-okuma kanıtı).

---

## 1. Amaç

`packages/kando_*` altındaki ayrık paket mimarisi ile canlı Lumos Core (`src/`) arasındaki ilişkiyi netleştirmek; olası birleştirme veya kesme (cutover) için **faz taslağı** ve **kesme kriterleri** tanımlamak.

Bu belge **kod değişikliği veya taşıma işlemi değildir**. Amaç: geliştirme görevleri açılmadan önce hangi alanın canlı, hangisinin aday olduğunun ve geçişin hangi kapılardan geçeceğinin tek referans olarak kayıtlı kalmasıdır.

**Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu taslağı gevşetemez.

---

## 2. Kapsam dışı olanlar

| Madde | Neden kapsam dışı |
|-------|-------------------|
| Kod taşıma, import yeniden yönlendirme, entrypoint değişikliği | Bu belge yalnızca karar taslağıdır; uygulama ayrı görev ve açık hedef gerektirir |
| `panel/`, `ui/`, `frontend/` birincil yüzey seçimi | OD-043, OD-046 — ayrı karar; geçiş zamanlamasını doğrudan kilitlemez |
| `lumos web` / `web/app.py` restore veya kaldırma | OD-028 — **kapalı (B1):** kök `lumos` web dalı kaldırıldı; `packages/kando_core/__main__.py` web kalıntısı bu geçişte hizalanır |
| İç katman (Kando/Cando/Bando) protokol detayı | OD-006, OD-007 — [`internal-agent-layers.md`](./internal-agent-layers.md) |
| Vault / token uygulama modeli | OD-001, OD-002 — [`security-architecture.md`](./security-architecture.md) |
| `kando-ai/` içeriğinin ürünleştirilmesi | Yan/aday alan; canlı Lumos CLI kapsamı dışı |

---

## 3. Mevcut runtime giriş zinciri (repo-verified)

**Kök entry point** — `pyproject.toml`:

```toml
[project.scripts]
lumos = "lumos_core.__main__:main"

[tool.setuptools]
package-dir = { "" = "src" }
```

**Canlı CLI zinciri:**

```
lumos  (veya python -m lumos_core)
  → src/lumos_core/__main__.py : main()
    → _run_cli()  [varsayılan; alt komut yok veya "cli"]
      → src/main.py : main()
        → core.lumos_runtime.create_runtime()
        → cli.cli_router.run_cli_loop(router_ctx)
```

**Diğer `lumos` alt komutları** (`src/lumos_core/__main__.py`):

| Alt komut | Hedef | Repo durumu |
|-----------|--------|-------------|
| `cli` (varsayılan) | `src/main.py` → CLI döngüsü | **Canlı** |
| `decision` | `core.decision_pipeline` / `core.decision_runner` | **Canlı** (`src/` içi) |

**OD-028 (kapalı — B1):** Kök `lumos` artık `web` alt komutu **içermez** ([`lumos-web-command-decision.md`](./lumos-web-command-decision.md)). `packages/kando_core/__main__.py` hâlâ `_run_web()` ve `web` parser taşır — stale kalıntı; Faz 5 temizlik adayı.

**Doğrulanan düzeltmeler:**

- Eski notlardaki `lumos_core.main:main` **geçersiz**; güncel: `lumos_core.__main__:main`.
- `src/lumos_core/main.py` **yok**; giriş `__main__.py` üzerinden.

**Özet:** Root `pyproject.toml` → `lumos_core.__main__` → `src/main.py` → `core/` + `cli/`. Bu zincir **canlı Lumos Core** girişidir.

---

## 4. `src/` canlı kod alanı

| Özellik | Değer |
|---------|--------|
| **Rol** | Canlı Lumos Core Python kodu — **tek canonical çekirdek** |
| **Paket kökü** | `src/` (`package-dir` root `pyproject.toml` içinde) |
| **Ana modüller** | `lumos_core` (1), `core` (53), `cli` (7), `task_engine` (26), `security` (16), `policy` (4), `memory` (5), `context` (2), `engine` (4), `kando` (22), `device` (7) |
| **Yerel state** | CWD altında `.lumos/` (`tasks.json`, `config`, `logs`, `trash`, …) — workspace sözleşmesi |
| **Durum** | **Aktif / canlı** — sınıf: `canlı aday` (envanter) |
| **Import yönü** | `src/` → `packages/kando_*` import **yok** (`rg` sıfır eşleşme) |

**Sabit karar (onaylı):** `src/` = live Lumos Core. Tüm üretim benzeri CLI, görev motoru, güvenlik ve bellek katmanları buradan yürür. `src/kando/kando_core.py` yerel modül adıdır; `packages/kando_core` ile karıştırılmaz.

**Belirsiz alt alanlar (envanter):** `integrations/` (sınırlı canlı kullanım), `cando/` (geliştirme yardımcı), boş `logs/` dizini.

---

## 5. `packages/kando_*` paket alanı — envanter ve sınıflandırma

**Doğrulama:** Faz 1 envanter (2026-06-18). Detay: [`kando-packages-faz1-inventory.md`](./kando-packages-faz1-inventory.md).

### 5.1 Paket özet tablosu

| Paket dizini | PyPI adı | Sınıf (envanter) | Karar sınıfı | Gerekçe (kısa) |
|--------------|----------|------------------|--------------|----------------|
| `packages/kando_bridge` | `kando-bridge` | canlı aday | **keep** | `python -m kando_bridge`; 16 test; Makefile/CI PYTHONPATH; `src/` tüketir |
| `packages/kando_runtime` | `kando-runtime` | canlı aday (gate/dispatch) | **keep** | Bridge + test importları; gate/executor zinciri; `src/` PYTHONPATH zorunlu |
| `packages/kando_core` | `kando-core` | ölü kod / stale ayna | **archive candidate** | `from kando_core` dış import sıfır; 43 ortak basename `src/core/`; `__main__` web kalıntısı |
| `packages/kando_memory` | `kando-memory` | ölü kod (drift riskli ayna) | **archive candidate** | Dış import sıfır; `memory.py`/`session_memory.py` `src/memory/` ile farklı |
| `packages/kando_policy` | `kando-policy` | ölü kod (ayna + coupling) | **archive candidate** | Dış import sıfır; seçili dosyalar `src/security`/`src/policy` ile özdeş |
| `packages/kando_context` | `kando-context` | ölü kod (paket içi ayna) | **archive candidate** | Yalnızca `kando_memory` içinden; dış tüketim yok |

### 5.2 `kando_bridge` ve `kando_runtime` — canlı paket durumu

| Alan | `kando_bridge` | `kando_runtime` |
|------|----------------|-----------------|
| **Rol** | HTTP köprü, STT, `run.py` launcher | Gate, audit, dispatch, executor'lar |
| **Entry** | `python -m kando_bridge` → `server.run` | Kütüphane; root script yok |
| **Test** | 16 test dosyası | Aynı test setinde |
| **`src/` bağımlılığı** | `from core.*`, `from kando.file_patch_executor` | `lumos_runtime.py` tam bootstrap (`cli`, `core`, `security`, …) |
| **Karar** | **keep** (hibrit C) | **keep** (hibrit C); `lumos_runtime.py` aynası **archive candidate** |

**PYTHONPATH (canlı kanıt):** `src:packages/kando_runtime/src:packages/kando_bridge/src` (`Makefile`, `ci.yml`).

**Import grafiği:** Tek yönlü `packages → src`; tersi yok. Paketler `src/` olmadan import kırılır — ince kabuk değil, **ters bağımlılık** (Seçenek B riski).

### 5.3 Ayna paketler — `kando_core`, `kando_memory`, `kando_policy`, `kando_context`

| Paket | Modül sayısı | Dış tüketim | `src/` örtüşmesi | Karar |
|-------|--------------|-------------|------------------|-------|
| `kando_core` | 47 | **sıfır** | 43 ortak basename `src/core/` | **archive candidate** |
| `kando_memory` | 5 | **sıfır** | 5/5 basename; 2 dosya drift | **archive candidate** |
| `kando_policy` | 19 | **sıfır** | 17+ ortak basename | **archive candidate** |
| `kando_context` | 2 | yalnızca `kando_memory` | 2/2 basename `src/context/` | **archive candidate** |

**Ölü ayna modülleri (`kando_runtime` içi):**

| Modül | Canonical | Karar |
|-------|-----------|-------|
| `lumos_runtime.py` | `src/core/lumos_runtime.py` | **archive candidate** (dış import sıfır) |
| `brain.py` | `src/core/brain.py` (`diff -q` özdeş) | **uncertain** — hangi zincir kullanıyor net değil; arşiv öncesi doğrulama |

**Sabit karar (onaylı):**

- Root entrypoint `packages/kando_*` üzerinden **başlamaz**.
- Canlı yol: `src/` canonical + `kando_bridge` + `kando_runtime` (gate/dispatch) paket olarak kalır.
- Ayna paketler (`kando_core`, `kando_memory`, `kando_policy`, `kando_context`) arşiv adayı; birleştirme gereksiz (canonical zaten `src/`).
- Kesme öncesi: entrypoint, test, CI, import, güvenlik sınırı, rollback — [§8](#8-kesme-kriterleri).

**İç katman ilişkisi:** [`internal-agent-layers.md`](./internal-agent-layers.md) — dış dünya yalnızca Lumos geçidini görür; bu sınır gevşetilmez.

---

## 6. `kando-ai/` yan/aday alanı

| Özellik | Değer |
|---------|--------|
| **Konum** | Repo kökü `kando-ai/` |
| **İçerik** | `main.py`, `requirements.txt` (OpenAI görsel/parça işleme betiği) |
| **Root `lumos` CLI** | **Dahil değil** |
| **Durum** | **Yan / aday** — ayrı çalıştırma alanı |

**Sabit karar (taslak):** `kando-ai/` canlı Lumos CLI başlangıcı değildir; geçiş planının kritik yolu üzerinde sayılmaz. Public sınır ve demo-safe içerik kuralları geçerlidir.

---

## 7. Geçiş takvimi taslağı (phase draft, NOT fixed dates — needs-review)

Aşağıdaki fazlar **zorunlu takvim değildir**; sıra ve içerik onay bekler. Tarih atanmamıştır.

### Faz 0 — Mevcut durum (şimdi)

- Canlı: `src/` + root `lumos` entry.
- Aday: `packages/kando_*`, `kando-ai/`.
- Karar: geçiş yapılmaz; yanlış entry sanılmaz.

### Faz 1 — Envanter ve sınır haritası `[tamamlandı — 2026-06-18]`

Salt-okuma raporu: [`kando-packages-faz1-inventory.md`](./kando-packages-faz1-inventory.md).

- `src/` modülleri ile `packages/kando_*` modülleri arasında işlev eşlemesi (çift kod, boşluk, çakışma).
- Güvenlik sınırı: hangi paket hangi dış etkiye dokunabilir ([`security-architecture.md`](./security-architecture.md)).
- Test ve CI: hangi paketlerin bağımsız test zinciri olacağı.

### Faz 2 — Hedef mimari kararı `[onaylandı — 2026-06-18]`

**Önerilen ve onaylanan seçenek: C — Hibrit.**

#### Seçenek karşılaştırması (envanter kanıtı)

| Seçenek | Özet | Envanter desteği | Risk / red nedeni |
|---------|------|------------------|-------------------|
| **A — Birleştir** | `kando_bridge` + `kando_runtime` → `src/` altına taşı | 16 test + CI PYTHONPATH sadeleşir; modüller taşınabilir | Büyük diff; gate/bridge güvenlik sınırı yeniden doğrulanmalı; acil kazanç düşük (paketler zaten canlı) |
| **B — Ayrı kal** | `packages/` bağımsız; `src/` ince kabuk | Mevcut PYTHONPATH zinciri | **Reddedildi:** paketler `src/` olmadan çalışmaz; ters bağımlılık; `lumos_runtime`/`kando_core` drift devam eder |
| **C — Hibrit** ✓ | `src/` canonical çekirdek; yalnızca `kando_bridge` + `kando_runtime` paket kalır; ayna paketler arşiv | Ayna paketler zaten ölü (dış import sıfır); arşiv net kazanç; canlı test/CI kanıtı bridge+runtime için | Import sözleşmesi (`packages → src`) dokümante edilmeli; arşiv öncesi `brain.py` belirsizliği giderilmeli |
| **D — Dondur / arşiv** | Tüm `packages/kando_*` deneysel | `kando_core`/`memory`/`policy`/`context` fiilen ölü | **Kısmi:** `bridge`+`runtime` canlı kaldığı sürece tam D mümkün değil — C ile birleşir |

#### Seçenek C — gerekçe (envanter doğrulaması)

1. **Canonical zaten `src/`:** Kök `lumos` → `src/main.py` → `core/cli`; `src/` → `packages` import yok.
2. **Canlı paketler dar küme:** Yalnızca `kando_bridge` (16 test, panel E2E spawn) ve `kando_runtime` (gate/dispatch) fiilen kullanılıyor; Makefile/CI PYTHONPATH bunları içerir, `kando_core` dahil değil.
3. **Ayna paketler birleştirme gerektirmez:** `kando_core` (43 dosya örtüşme, sıfır dış import), `kando_memory`, `kando_policy`, `kando_context` — hepsi **archive candidate**; taşıma yerine arşiv/temizlik yeterli.
4. **A birleştirme ertelenebilir:** Bridge/runtime `src/` altına taşımak (ör. `src/kando_bridge`) opsiyonel Faz 4+ işi; şu an paket sınırı güvenlik/geçit ayrımına hizmet ediyor.
5. **B sürdürülemez:** “Bağımsız paket” iddiası envanterle çelişiyor — `lumos_runtime.py` pakette `src/` import eder.

#### Onaylanan hedef mimari (C)

```
Canlı yol:
  lumos (root) → src/ (canonical: core, cli, task_engine, security, memory, policy, context, kando)
              ↘ packages/kando_bridge (HTTP köprü, STT)
              ↘ packages/kando_runtime (gate, dispatch, executor'lar — lumos_runtime aynası hariç)

Arşiv (Slice 3b — archive/packages/):
  archive/packages/kando_core, kando_memory, kando_policy, kando_context

Kalan aday (Faz 5):
  packages/kando_runtime/lumos_runtime.py (+ muhtemelen brain.py) — Slice 3a ile lumos_runtime aynası kaldırıldı

Dokunulmaz (cutover öncesi):
  src/ canonical; .lumos/ workspace sözleşmesi; güvenlik geçidi
```

**Sonraki uygulama paketi sınırı (implementation-pending):**

1. Import sözleşmesi belgesi: `packages/kando_bridge` + `kando_runtime` → `src/` tek yönlü bağımlılık; PYTHONPATH sabit.
2. Ayna paket arşivi: `kando_core`, `kando_memory`, `kando_policy`, `kando_context` — açık hedef path + rollback ile.
3. `kando_core.__main__` web kalıntısı kaldırma (OD-028 hizası).
4. `kando_runtime/lumos_runtime.py` ölü ayna kaldırma veya `src/core` ile tek kaynak senkronu.
5. (Opsiyonel, ayrı görev) Bridge/runtime `src/` altına taşıma — Seçenek A alt kümesi; C onayı bunu zorunlu kılmaz.

**Çıkış:** Bu belge + OD-027 indeks güncellemesi (`decision-approved / implementation-pending`).

### Faz 3 — Kesme öncesi kapılar + Slice 3a `[implementation-complete — PR #313]`

Keşif raporu: [`kando-packages-faz3-keşif-raporu.md`](./kando-packages-faz3-keşif-raporu.md).

**Tamamlanan dilim (Slice 3a — S effort, PR #313 / `c0b8ea0`):**

1. `kando_core.__main__.py` web kalıntısı kaldırıldı (OD-028 hizası)
2. `kando_runtime/lumos_runtime.py` ölü ayna silindi
3. Import sözleşmesi referans notu (docs-only veya README)

§8 checklist Slice 3a için geçerli; ayna paket arşivi **3b** **`implementation-complete`** (PR #316 / `1cdb0f2`) — [`od-027-slice-3b-archive-decision.md`](./od-027-slice-3b-archive-decision.md).

**Slice 3b (M effort, PR #316):** dört ayna paket `archive/packages/` altına taşındı (`git mv`); canlı `packages/` yalnızca bridge + runtime.

### Faz 4 — Kesme (cutover) `[implementation-pending — kullanıcı onayı zorunlu]`

- Tek sorumluluklu görev(ler); açık hedef path ve geri alma planı.
- CI yeşil olmadan “tamamlandı” denmez ([`project-workflow.md`](./project-workflow.md) §5).

### Faz 5 — Temizlik ve dokümantasyon `[needs-review]`

- [`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) güncellemesi.
- `open-decisions-needs-review.md` OD-027 durumu (`migrated` / `superseded`).

---

## 8. Kesme kriterleri

`packages/kando_*` (veya seçilen alt kümesi) **canlı** kabul edilmeden önce aşağıdaki maddelerin tamamı netleşmiş ve doğrulanmış olmalıdır.

| # | Kriter | Doğrulama sorusu |
|---|--------|------------------|
| K1 | **Entrypoint** | Kök `lumos` (veya onaylı yeni entry) hangi modüle gider? Çift entry yok mu? |
| K2 | **Test** | İlgili birim/entegrasyon testleri geçiyor mu? Regresyon seti tanımlı mı? |
| K3 | **CI** | GitHub Actions (veya eşdeğer) yeşil mi? Yeni paket CI’ya eklendi mi? |
| K4 | **Import yolu** | `src/` ↔ `packages/` import grafiği döngüsüz ve belgelenmiş mi? |
| K5 | **Güvenlik sınırı** | Lumos geçidi bypass yok; token/vault/bridge kuralları korunuyor mu? |
| K6 | **Rollback** | Kesme geri alınırsa hangi commit/tag ve hangi entry geri gelir? Veri migrasyonu var mı? |
| K7 | **Workspace / state** | `.lumos/` ve çekirdek path’lere yazım workspace sözleşmesine uygun mu? |
| K8 | **Public sınır** | Public repo’ya production secret, private orchestration veya operasyonel detay sızmıyor mu? |

**Kesme onayı:** Mimari karar + kullanıcı açık komutu. Otomatik veya tek taraflı kesme yok.

---

## 9. Kod değişikliği öncesi kural

[`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) §8 ile hizalı; geçiş kararıyla sabitlenen ek kurallar:

1. Giriş noktası `src/` zinciri mi, yoksa `packages/kando_*` aday mı — **önce bu belgeye bak**.
2. **`src/` ↔ `packages/` taşıma, import değişikliği veya entrypoint değişikliği** yalnızca görevde **açık hedef** (dosya/modül/path) yazılıysa yapılır.
3. `.lumos/` veya çekirdek state path’ine yazım workspace sözleşmesine uygun olmalıdır.
4. Canlı zincir düşünülürken `packages/` veya `kando-ai/` **canlı entry sanılmaz**.
5. Minimum kod değişikliği; kapsam genişletme yok ([`project-workflow.md`](./project-workflow.md) §2, §4).

---

## 10. Riskler

| Risk | Açıklama | Azaltma (özet) |
|------|----------|----------------|
| **Yanlış entry sanma** | `packages/kando_*` veya `kando-ai/` üzerinden canlı CLI varsayımı | Bu belge + `project-map-runtime-entrypoints.md` |
| **Çift kod / drift** | Aynı işlev hem `src/` hem `packages/` içinde farklı evrilir | Faz 1 envanter; tek canonical modül kararı |
| **Import döngüsü** | Kesme sırasında `src` ↔ `kando_*` karşılıklı import | K4; mimari inceleme önce |
| **Güvenlik bypass** | İç katmana doğrudan dış akış | `internal-agent-layers.md`, `security-architecture.md` |
| **Erken kesme** | CI/test/rollback olmadan canlıya alma | §8 checklist; CI yeşil kuralı |
| **Kapsamsız görev** | Belirsiz “geçiş yap” isteğiyle toplu taşıma | Açık hedef path zorunluluğu (§9) |
| **UI/runtime karışıklığı** | Panel/UI build ile Python geçişinin aynı sanılması | OD-043/046 ayrı tutulur |

---

## 11. Açık kararlar

| # | Soru | Durum |
|---|------|--------|
| 1 | Hedef mimari: A birleştir / B ayrı / C hibrit / D dondur? | **Onaylandı: C — Hibrit** |
| 2 | Hangi `kando_*` paketleri canlı yola dahil? | **Onaylandı: `kando_bridge` + `kando_runtime` (gate/dispatch); ayna paketler arşiv** |
| 3 | Kesme tek seferde mi, paket paket mi? | **needs-review** (uygulama paketi) — öneri: önce ayna arşiv, bridge/runtime sabit |
| 4 | Root `pyproject.toml` tek paket mi kalır, workspace/monorepo mu olur? | **needs-review** — C ile mevcut PYTHONPATH korunur; monorepo zorunlu değil |
| 5 | `kando_core.__main__` ile root `lumos` ilişkisi | **Onaylandı: kaldırma/arşiv** — hiç çağrılmıyor; web kalıntısı OD-028 hizası |
| 6 | Geçiş sırasında `.lumos/` state migrasyonu gerekir mi? | **Onaylandı: hayır** — kod taşıma/arşiv; state path değişmez |

**İlişkili ama bu belgede çözülmeyen:**

- **OD-028:** Kapalı (B1) — kök `lumos` web yok; `kando_core.__main__` web kalıntısı bu geçişte temizlenir.
- **OD-043:** Birincil kullanıcı yüzeyi — **closed** (`ui/`).
- **OD-046:** Root build vs kök E2E — **closed** (`ui/dist`).

---

## 12. OD eşleme tablosu

| OD | Konu | Bu belgedeki karşılık | Durum |
|----|------|------------------------|--------|
| **OD-027** | `packages/kando_*` → `src/` geçiş takvimi ve kesme kriterleri | Bu dosyanın tamamı + Faz 3 keşif | **approved-for-implementation** (Slice 3a **complete**; 3b karar onaylı) |
| OD-028 | `lumos web` / `web/app.py` | §3 — kök kapalı (B1); `kando_core.__main__` kalıntısı Slice 3a | **closed** (çapraz temizlik Slice 3a) |
| OD-043 | Birincil kullanıcı yüzeyi | §2 kapsam dışı; geçişten bağımsız | **closed** (çapraz) |
| OD-046 | Root build vs kök E2E | §2 kapsam dışı; geçişten bağımsız | **closed** (çapraz) |

**İndeks senkronu:** Kesme (Faz 4) tamamlanınca `project-map-runtime-entrypoints.md` §11 ve bu indeks `migrated`/`superseded` güncellenir.

---

## 13. Sonraki adım

**Tek adım (uygulama):** Slice **3b** PR — [`od-027-slice-3b-archive-decision.md`](./od-027-slice-3b-archive-decision.md) §3 (`git mv` → `archive/packages/`); pytest + CI yeşil. Faz 4 cutover ayrı kullanıcı onayı gerektirir.

---

## Netleşen sabit kararlar (onaylı — uygulama bekliyor)

| Karar | İfade |
|-------|--------|
| Hedef mimari | **C — Hibrit:** `src/` canonical; `kando_bridge` + `kando_runtime` paket kalır |
| Canlı runtime | `pyproject.toml` → `lumos_core.__main__` → `src/main.py` → `core/cli` |
| `src/` | Live Lumos Core — **keep** |
| `kando_bridge`, `kando_runtime` | Canlı paket — **keep** |
| `kando_core`, `kando_memory`, `kando_policy`, `kando_context` | Stale ayna — **archive candidate** |
| `kando_runtime/lumos_runtime.py` | Ölü ayna — **archive candidate** (canonical: `src/core/lumos_runtime.py`) |
| `kando-ai/` | Yan/aday; canlı Lumos CLI değil — **uncertain** (ürünleştirme kapsam dışı) |
| Import sözleşmesi | Tek yönlü `packages → src`; PYTHONPATH: `src:kando_runtime:kando_bridge` |
| Geçiş öncesi zorunluluk | Entrypoint, test, CI, import, güvenlik sınırı, rollback net olmalı (§8) |
| Taşıma kuralı | Açık hedef olmadan `src`↔`packages` move/import/entrypoint değişikliği yok |
| State migrasyonu | Gerekmez — `.lumos/` path değişmez |
| Takvim | Faz taslağı; sabit tarihli zorunlu plan değil |

---

*Son güncelleme: 2026-06-18*
