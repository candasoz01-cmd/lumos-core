# Son durum raporu + GitHub notu

## 1. Modül konumu raporu (“taşan” ve yanlış yerde olanlar)

**Şu an paket dışına taşan modül yok.**  
`security`, `core`, `context`, `memory`, `device`, `engine`, `policy`, `tools`, `ui`, `scripts` hepsi **`src/lumos_core/`** altında; top-level’da ayrı `src/security` veya `src/core` yok. Tüm import’lar `lumos_core.*` kullanıyor.

**Yanlış yerde / temizlenmesi iyi olanlar:**

| Konum | Durum | Neden |
|-------|--------|--------|
| **src/scripts/** | Sadece README kaldı; kod `lumos_core.scripts`’e taşındı | Eski adres; yeni kullanım: `python -m lumos_core.scripts.init_keystore` |
| **src/main.py.bak\*** | Birçok backup dosyası (main.py.bak, main.py.bak_lock, …) | src kökünü kirletiyor; paket değil, arşiv |

**Minimum hamle ile toplama:**

1. **src/scripts:** Olduğu gibi bırakılabilir (README yönlendiriyor). İstenirse klasör silinir; dokümanda tek adres `lumos_core.scripts` olur.
2. **main.py.bak\***: `.gitignore`’a `main.py.bak*` eklenir; gerekiyorsa bu dosyalar repo dışına (veya `docs/archive/`) taşınır / silinir. Tek hamle: `git rm src/main.py.bak*` (veya ignore + commit).

---

## 2. GitHub: default branch ve koruma (tek paragraf)

**Default branch:** Repo **Settings → General** sayfasında, en üstte **Default branch** alanı var (Branches sayfası değil). Oradan ana branch (örn. `kando/main` veya `main`) seçilir. **Branch protection:** Branches → Add rule (veya mevcut kural) → “Allow deletions” kapatılırsa silme engellenir. Private repo’da bazı kurallar “Not enforced” uyarısı verebilir (plan/org kısıtı); bu durumda silmeyi yerel disiplin ve PR akışıyla yönetmek yeterli.

---

## 3. SON ÇIKTI (istenen net sonuç)

1. **~/WORK_2026** artık repo değil; sadece **workspace**. Git işlemleri `lumos-core` içinde.
2. **~/WORK_2026/lumos-core** tek ana repo (çekirdek + monorepo içinde lumos-social).
3. **lumos-social** yolu net: monorepo içinde `lumos-core/lumos-social/`; dışarıdaki `~/WORK_2026/lumos-social` sandbox/legacy, repo’ya bağlanmıyor. Karışıklık yok.
4. **python -m pytest** çalışıyor; CI’da da aynı çağrı (Makefile: `PYTEST := $(PYTHON) -m pytest`).
5. **Yanlış yerdeki klasör/dosyalar:** Sadece `src/scripts` (artık sadece README) ve `src/main.py.bak*`; minimal fix: scripts’i isteğe bağlı kaldır, `main.py.bak*` için ignore veya `git rm` + dokümanda tek paket ağacı (`lumos_core`) vurgulanır.

---

**Cursor popup:** “Submit from a previous message?” gelirse **Continue without reverting** seç; revert istemiyoruz.
