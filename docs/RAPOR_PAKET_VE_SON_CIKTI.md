# Paket dışı taşma raporu + minimal fix + son çıktı

## 1. Şu an hangi modüller paket dışına taşmış?

- **Yok.** Tüm canlı modüller `src/lumos_core/` altında: `lumos_core.security`, `lumos_core.core`, `lumos_core.context`, `lumos_core.memory`, vb. Hiçbiri artık `src/security`, `src/core` gibi top-level değil.
- **Paket dışında kalanlar (modül değil):**
  - **src/main.py** — Sadece yönlendirme stub’ı (lumos_core.interactive_cli’yi çağırıyor). Bilinçli; “taşma” sayılmaz.
  - **src/scripts/** — İçinde sadece README (init_keystore/init_identity → `lumos_core.scripts` taşındı).
  - **src/security.bak_lock/** — Eski yedek; paket değil, import edilmemeli (içinde hâlâ `from src.security...` var, kırık).
  - **src/main.py.bak\*** — Eski yedek dosyalar.

## 2. Hangisi yanlış yerde ve neden?

| Konum | Durum | Neden |
|-------|--------|-------|
| **src/security.bak_lock/** | Yanlış yerde | Eski lock yedeği; `src` altında paket gibi duruyor, import’lar (`src.security`) artık geçersiz. Çekirdek paket ağacına ait değil. |
| **src/main.py.bak\*** | Gereksiz | Repo kökünde onlarca yedek; karışıklık ve “hangi main gerçek?” hissi. |
| **src/main.py** | Bilinçli stub | Doğru yerde; tek satırlık redirect. İstersen kaldırıp sadece `python -m lumos_core` kullanılabilir. |
| **src/scripts/** | Boşaltıldı | Sadece README kaldı; mantıklı. İstersen dizini tamamen kaldırıp README’yi docs’a taşıyabilirsin. |

## 3. Minimum hamle ile nasıl toplanacak?

1. **security.bak_lock:** `.gitignore`’a ekle (`security.bak_lock/`) veya `docs/archive/` / repo dışı yedek klasörüne taşı; repoda “paket” gibi görünmesin.
2. **main.py.bak\***:** `.gitignore`’a `main.py.bak*` ekle; yeni yedekler takip edilmesin. Mevcut olanları silmek veya arşive taşımak ayrı PR (isteğe bağlı).
3. **src/scripts:** Opsiyonel — dizini kaldırıp “Scripts taşındı” notunu `docs/REPO_LAYOUT.md` veya `docs/EXTERNAL_LUMOS_SOCIAL.md` yanına kısa paragraf olarak ekle.

Bunlarla tek paket ağacı (`src/lumos_core/`) net kalır; taşma kalmaz.

---

## AMAÇ 5 — GitHub: default branch ve koruma (tek paragraf)

**Default branch:** Repo **Settings → General** sayfasında, en üstte **Default branch** alanı var (Branches sayfası değil). Oradan ana branch’i (örn. `kando/main` veya `main`) seçip **Update** ile kaydediyorsun. **Branch protection:** **Settings → Branches → Add branch protection rule** ile kural oluşturup “Allow deletions” kapalı tutarsan silme engellenir. Private repo’da bazı kurallar “Not enforced” uyarısı verebilir (plan/organizasyon kısıtı); o durumda silmeyi yerel disiplin ve PR akışıyla yönetebilirsin.

---

## SON ÇIKTI (net sonuç özeti)

1. **~/WORK_2026** artık repo değil; sadece **workspace**. Git işlemleri `lumos-core` içinde.
2. **~/WORK_2026/lumos-core** tek ana repo; kaynak gerçek burada.
3. **lumos-social** için seçilen yol net: **monorepo** (lumos-core içinde `lumos-social/`). Dışarıdaki ~/WORK_2026/lumos-social sandbox/legacy; karışıklık yok.
4. **python -m pytest** çalışıyor; Makefile ve CI’da da `python -m pytest` kullanılıyor.
5. **“Yanlış yerdeki klasör”** için kısa rapor ve **minimal fix planı** yukarıda: `security.bak_lock` ve `main.py.bak*` .gitignore veya arşiv; isteğe bağlı `src/scripts` kaldırma.

---

**Ek (Cursor):** “Submit from a previous message?” penceresi çıkarsa **“Continue without reverting”** seç; revert istemiyoruz, normal şekilde devam et.
