# GitHub (default branch / koruma) ve son durum özeti

## Default branch ve branch koruma (tek paragraf)

**Default branch:** Repo **Settings → General** sayfasında, en üstte **Default branch** alanı var (Branches sayfası değil). Oradan varsayılan dalı seçip **Update** ile kaydedebilirsin. **Branch protection** kuralları **Settings → Branches → Branch protection rules** altında; bir kuralda **“Allow deletions”** kapalıysa o dal silinmez. Private repo’da bazı korumalar plan/organizasyona bağlı olarak **“Not enforced”** uyarısı verebilir; böyle durumda silmeyi yerel disiplin ve PR akışıyla (merge sonrası silme yapmama, doğru branch’te çalışma) yönetmek yeterli.

---

## SON ÇIKTI (net sonuç)

1. **~/WORK_2026 artık repo değil; sadece workspace.**  
   `.git` yok (sadece `.git_BACKUP_DO_NOT_TOUCH`); git komutları bu dizinde repo görmez.

2. **~/WORK_2026/lumos-core tek ana repo.**  
   Tüm çekirdek kodu bu repoda; default branch (örn. `kando/main` veya `chore/restructure-src`) burada yönetilir.

3. **lumos-social için seçilen yol net; karışıklık kalmıyor.**  
   **Monorepo:** Kaynak gerçek `lumos-core/lumos-social/`. Dışarıdaki `~/WORK_2026/lumos-social` sandbox/legacy; repo’ya bağlanmaz. (Ayrı repo seçilse ileride submodule/ayrı remote ile bağlanır; şu an monorepo.)

4. **`python -m pytest` çalışıyor; CI’da da aynı çağrı.**  
   Makefile’da `PYTEST := $(PYTHON) -m pytest`; `make test` ve CI `python -m pytest` kullanıyor. Dev deps: `pip install -e ".[dev]"` veya `pip install pytest`.

5. **“Yanlış yerdeki klasör” için kısa rapor + minimal fix planı var.**  
   Detay: **`docs/PACKAGE_LAYOUT_REPORT.md`**. Özet: Paket dışına taşan sadece `src/main.py` (stub) ve `src/scripts/` (legacy). Minimum hamle: main stub kalır veya silinir; `src/scripts/` temizlenir veya sadece README ile bırakılır.

---

**Cursor “Submit from a previous message?” popup:** **“Continue without reverting”** seç; revert istemiyoruz, normal şekilde devam et.
