# Kısa rapor + GitHub + son çıktı

---

## 1. “Paket dışına taşmış” modüller / yanlış yerde olanlar

**Şu an top-level (paket dışı) olanlar:**  
- **security, core, context** artık top-level değil; hepsi **`src/lumos_core/`** altında (lumos_core.security, lumos_core.core, lumos_core.context vb.).

**Paket dışında kalan tek şeyler:**  
- **`src/main.py`** — Sadece yönlendirme stub’ı (lumos_core.interactive_cli’yi çağırıyor). İstenirse kalabilir; “yanlış yerde” sayılmaz.  
- **`src/scripts/`** — Eski script dizini; içinde sadece README (init_keystore/init_identity `lumos_core.scripts`’e taşındı). Yani “boş” sayılır, yanlış yerde.

**Özet:** Gerçek kod taşması yok. Tek “yanlış yerde” olan: **`src/scripts/`** (artık kullanılmıyor, sadece README var).

**Minimum hamle:**  
- `src/scripts/` klasörünü tamamen kaldır (README’deki “taşındı” bilgisi zaten `docs/REPO_LAYOUT.md` ve `lumos_core.scripts` docstring’lerinde).  
- `src/main.py` stub’ı kalabilir (geriye dönük uyum); istersen “tercih: python -m lumos_core” notu README’de kalsın.

---

## 2. GitHub: default branch ve koruma (AMAÇ 5)

**Default branch:** Repo **Settings → General** sayfasında, **Default branch** alanından seçilir (Branches sayfası değil). Orada listeden ana branch’i (örn. `kando/main` veya `main`) seçip **Update** ile kaydedin.

**Silme engelleme:** Branch kurallarında (Branch protection rules) ilgili branch için **“Allow deletions”** kapalıysa, o branch silinemez. Kural yoksa ekleyin; “Allow force pushes” de genelde kapatılır.

**“Not enforced” uyarısı:** Private repo’da organizasyon/plan ayarına göre bazı korumalar “Not enforced” gösterebilir. Bu durumda default branch’i ve kuralları yine de ayarlayın; ek olarak yerel disiplin (force push / branch silme yapmama) ve PR akışıyla yönetin.

---

## 3. Son çıktı (net sonuç)

1. **~/WORK_2026** artık repo değil; sadece **workspace**. (İçinde `.git` yok; varsa yedeklendi.)
2. **~/WORK_2026/lumos-core** tek ana repo; çekirdek ve monorepo kaynağı burada.
3. **lumos-social** için seçilen yol net: **monorepo** (lumos-core içinde `lumos-social/`). Dışarıdaki `~/WORK_2026/lumos-social` sandbox/legacy; repo’ya bağlanmıyor. Karışıklık kalmıyor.
4. **`python -m pytest`** çalışıyor; Makefile ve CI’da da aynı çağrı kullanılıyor (pytest komutuna güvenilmiyor).
5. **“Yanlış yerdeki klasör”** için kısa rapor ve minimal fix: Yukarıdaki 1. bölüm (sadece `src/scripts/` kaldırılacak; `main.py` stub isteğe bağlı kalır).

---

## Ek: Cursor “Submit from a previous message?” penceresi

Bu pencere çıkarsa **“Continue without reverting”** seçin (revert istemiyoruz); sonra normal şekilde ilerleyin.
