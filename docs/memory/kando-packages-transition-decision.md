# OD-027 — `packages/kando_*` → `src/` geçiş kararı (taslak)

**Durum:** `[needs-review]` — uygulama değil; karar taslağı.  
**Kaynak indeks:** [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) OD-027.  
**Doğrulama tarihi:** 2026-06-17 (repo read-only tarama).

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
| `lumos web` / `web/app.py` restore veya kaldırma | OD-028 — CLI alt komutu; `src/` zincirinden bağımsız needs-review |
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

**Diğer `lumos` alt komutları** (`__main__.py`):

| Alt komut | Hedef | Repo durumu |
|-----------|--------|-------------|
| `cli` (varsayılan) | `src/main.py` → CLI döngüsü | **Canlı** |
| `web` | `web/app.py` | **`web/` dizini yok** — OD-028 needs-review |
| `decision` | `core.decision_pipeline` / `core.decision_runner` | `src/` içi |

**Doğrulanan düzeltmeler:**

- Eski notlardaki `lumos_core.main:main` **geçersiz**; güncel: `lumos_core.__main__:main`.
- `src/lumos_core/main.py` **yok**; giriş `__main__.py` üzerinden.

**Özet:** Root `pyproject.toml` → `lumos_core.__main__` → `src/main.py` → `core/` + `cli/`. Bu zincir **canlı Lumos Core** girişidir.

---

## 4. `src/` canlı kod alanı

| Özellik | Değer |
|---------|--------|
| **Rol** | Canlı Lumos Core Python kodu |
| **Paket kökü** | `src/` (`package-dir` root `pyproject.toml` içinde) |
| **Ana modüller** | `lumos_core`, `core`, `cli`, `task_engine`, `security`, … |
| **Yerel state** | CWD altında `.lumos/` (`tasks.json`, `config`, `logs`, `trash`, …) — workspace sözleşmesi |
| **Durum** | **Aktif / canlı** |

**Sabit karar (taslak):** `src/` = live Lumos Core. Geçiş tamamlanana kadar tüm üretim benzeri CLI, görev motoru ve güvenlik sınırları buradan yürür.

---

## 5. `packages/kando_*` aday paket alanı

**Doğrulanan dizinler** (2026-06-17):

| Paket dizini | PyPI adı (`pyproject.toml`) | Bağımlılık notu |
|--------------|----------------------------|-----------------|
| `packages/kando_bridge` | `kando-bridge` | `kando-runtime>=0.1.0`; opsiyonel `stt` |
| `packages/kando_context` | `kando-context` | — |
| `packages/kando_core` | `kando-core` | — |
| `packages/kando_memory` | `kando-memory` | — |
| `packages/kando_policy` | `kando-policy` | — |
| `packages/kando_runtime` | `kando-runtime` | `openai`, `requests` |

**Yapı:** Her paketin kendi `pyproject.toml` ve `src/kando_*/` ağacı vardır. Örnek: `packages/kando_core/src/kando_core/__main__.py` benzer bir CLI yüzeyi sunar; ancak **kök `lumos` komutu bunu çağırmaz**.

**Sabit karar (taslak):**

- `packages/kando_*` = **aday / ayrılmış mimari** alanı.
- Root entrypoint buradan **başlamaz**.
- Canlı kabul edilmeden önce: entrypoint, test, CI, import yolu, güvenlik sınırı ve geri alma (rollback) kriterleri **yazılı ve onaylı** olmalıdır ([§8](#8-kesme-kriterleri)).

**İç katman ilişkisi:** [`internal-agent-layers.md`](./internal-agent-layers.md) — dış dünya yalnızca Lumos geçidini görür; iç katmanlar doğrudan dış komut/veri kabul etmez. `packages/kando_*` canlıya alınsa bile bu sınır gevşetilmez.

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

### Faz 1 — Envanter ve sınır haritası `[needs-review]`

- `src/` modülleri ile `packages/kando_*` modülleri arasında işlev eşlemesi (çift kod, boşluk, çakışma).
- Güvenlik sınırı: hangi paket hangi dış etkiye dokunabilir ([`security-architecture.md`](./security-architecture.md)).
- Test ve CI: hangi paketlerin bağımsız test zinciri olacağı.

### Faz 2 — Hedef mimari kararı `[needs-review]`

Seçenekler (birbirini dışlar; çoklu seçim onay gerektirir):

| Seçenek | Özet |
|---------|------|
| **A — Birleştir** | Seçilen `kando_*` modülleri `src/` altına taşınır; root entry aynı kalır veya kontrollü genişler |
| **B — Ayrı kal** | `packages/` bağımsız kalır; `src/` yalnızca Lumos geçidi / ince kabuk |
| **C — Hibrit** | Çekirdek `src/`; belirli alt sistemler paket olarak yayınlanır; import sözleşmesi sabitlenir |
| **D — Dondur / arşiv** | `packages/kando_*` deneysel kalır; canlı yol `src/` ile sınırlı |

**Çıkış:** Yazılı hedef mimari + OD-027 durumu güncellemesi.

### Faz 3 — Kesme öncesi kapılar `[needs-review]`

- Entrypoint, test, CI, import path, güvenlik sınırı, rollback — hepsi [§8](#8-kesme-kriterleri) checklist’inde yeşil (veya bilinçli istisna kayıtlı).

### Faz 4 — Kesme (cutover) `[needs-review — kullanıcı onayı zorunlu]`

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
| 1 | Hedef mimari: A birleştir / B ayrı / C hibrit / D dondur? | **needs-review** |
| 2 | Hangi `kando_*` paketleri (varsa) canlı yola dahil edilecek? | **needs-review** |
| 3 | Kesme tek seferde mi, paket paket mi? | **needs-review** |
| 4 | Root `pyproject.toml` tek paket mi kalır, workspace/monorepo mu olur? | **needs-review** |
| 5 | `kando_core.__main__` ile root `lumos` ilişkisi (birleşme / kaldırma / alias) | **needs-review** |
| 6 | Geçiş sırasında `.lumos/` state migrasyonu gerekir mi? | **needs-review** |

**İlişkili ama bu belgede çözülmeyen:**

- **OD-028:** `lumos web` / `web/app.py` — restore veya kaldırma.
- **OD-043:** Birincil kullanıcı yüzeyi (`panel/` / `ui/` / `frontend/`).
- **OD-046:** Root `npm run build` (ui) ile panel E2E hangi yüzeyi «canlı» sayar.

---

## 12. OD eşleme tablosu

| OD | Konu | Bu belgedeki karşılık | Durum |
|----|------|------------------------|--------|
| **OD-027** | `packages/kando_*` → `src/` geçiş takvimi ve kesme kriterleri | Bu dosyanın tamamı | **needs-review** (taslak) |
| OD-028 | `lumos web` / `web/app.py` | §3 alt komut tablosu; kapsam dışı çözüm | needs-review (çapraz) |
| OD-043 | Birincil kullanıcı yüzeyi | §2 kapsam dışı; geçişten bağımsız | needs-review (çapraz) |
| OD-046 | Root build vs panel E2E | §2 kapsam dışı; geçişten bağımsız | needs-review (çapraz) |

**İndeks senkronu:** OD-027 kapanınca önce bu dosya ve [`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) §11 madde 4 güncellenir; ardından [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

---

## 13. Sonraki adım

**Tek adım:** Faz 1 envanter görevi aç — `src/` ile `packages/kando_*` modül eşlemesi ve çift-kod listesi (kod değişikliği yok; salt okuma raporu). Çıktı onaylandıktan sonra Faz 2 hedef mimari seçeneği (A/B/C/D) için kullanıcı kararı istenir.

---

## Netleşen sabit kararlar (taslak — uygulama bekliyor)

| Karar | İfade |
|-------|--------|
| Canlı runtime | `pyproject.toml` → `lumos_core.__main__` → `src/main.py` → `core/cli` |
| `src/` | Live Lumos Core |
| `packages/kando_*` | Aday / ayrılmış mimari; root entry buradan başlamaz |
| `kando-ai/` | Yan/aday; canlı Lumos CLI değil |
| Geçiş öncesi zorunluluk | Entrypoint, test, CI, import, güvenlik sınırı, rollback net olmalı |
| Taşıma kuralı | Açık hedef olmadan `src`↔`packages` move/import/entrypoint değişikliği yok |
| Takvim | Faz taslağı; sabit tarihli zorunlu plan değil |

---

*Son güncelleme: 2026-06-17*
