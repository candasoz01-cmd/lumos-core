# Durum raporu ve sonraki adımlar

## 1. Paket dışına taşmış modül var mı?

**Hayır.** Security, core, context, memory, device, engine, policy, tools, ui, scripts hepsi **`src/lumos_core/`** altında. Top-level’da ayrı `src/security`, `src/core` vb. yok; tek paket ağacı `lumos_core`.

---

## 2. Yanlış yerde olanlar ve neden

| Konum | Durum | Neden |
|-------|--------|--------|
| **src/main.py** | Stub (redirect) | Asıl CLI `lumos_core.interactive_cli`; main.py geriye dönük uyumluluk için bırakıldı. Tek paket açısından “dışarıda” sayılabilir ama tek dosya, zararsız. |
| **src/scripts/** | Legacy | İçinde sadece README + run.sh + .bak; asıl scriptler `lumos_core.scripts`’e taşındı. Dizin boşaltıldı ama klasör duruyor. |
| **src/main.py.bak\*** | Gereksiz | Birçok yedek dosya (main.py.bak, main.py.bak_lock, …) repo kökünü kirletiyor; paket dışı, version control’da olmamalı. |

Not: `security.bak_lock` artık yok (temizlenmiş veya hiç commit edilmemiş).

---

## 3. Minimum hamle ile nasıl toplanacak?

- **main.py:** İstersen kaldırıp tüm çağrıları `python -m lumos_core` / `lumos` yap; ya da olduğu gibi bırak (tek satırlık redirect, minimum risk).
- **src/scripts/:** Klasörü tamamen kaldır; “scriptler taşındı” bilgisini sadece `docs/REPO_LAYOUT.md` veya bu dosyada tut. Alternatif: Sadece README bırak, run.sh ve .bak’ları sil.
- **main.py.bak\*:** `.gitignore`’a `main.py.bak*` (ve gerekirse `*.bak`) ekle; mevcut .bak dosyalarını repo’dan kaldır (git rm --cached veya sil + commit). Böylece çekirdek tek paket altında kalır, taşan/yanlış yerde dosya kalmaz.

Özet: Tek yapısal “taşma” yok; temizlik için (1) main.py stub’ı isteğe bağlı kaldırma, (2) src/scripts’i kaldırma veya sadeleştirme, (3) .bak’ları ignore + repo’dan çıkarma yeterli.

---

## 4. GitHub: default branch ve koruma (AMAÇ 5)

**Default branch:** Repo **Settings** → **General** → sayfada **Default branch** bölümü (Branches sayfası değil). Oradan varsayılan branch’i (örn. `kando/main` veya `main`) seçip **Update** ile kaydedersin.  

**Silme koruması:** **Settings** → **Branches** → **Branch protection rules** → kuralı düzenle; **Allow deletions** kapalıysa branch silinmesi engellenir. Private repo’da bazı kurallar “Not enforced” uyarısı verebilir (plan/organizasyona bağlı); bu durumda silme korumasını yerel disiplin ve PR akışıyla (ör. “default branch’e force-push / silme yasak” kuralı) yönetebilirsin.

---

## 5. Son çıktı özeti (SON ÇIKTI)

1. **~/WORK_2026** artık repo değil; sadece workspace.
2. **~/WORK_2026/lumos-core** tek ana repo.
3. **lumos-social** yolu net: monorepo (lumos-core içinde `lumos-social/`); dışarıdaki `~/WORK_2026/lumos-social` sandbox/legacy, karışıklık yok.
4. **python -m pytest** çalışıyor; CI’da da aynı çağrı (Makefile: `PYTEST := $(PYTHON) -m pytest`).
5. **Yanlış yerdeki klasör/dosya:** Yukarıdaki kısa rapor + minimal fix planı bu dosyada (ve REPO_LAYOUT’ta) yazılı.

---

**Cursor “Submit from a previous message?” penceresi:** Açılırsa **“Continue without reverting”** seç; revert istemiyoruz, normal şekilde devam et.
