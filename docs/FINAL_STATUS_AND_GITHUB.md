# Son durum özeti + GitHub notu

## 1. Modül konumu raporu (paket dışına taşan / yanlış yerde)

**Şu an hangi modüller paket dışına taşmış?**  
- **Yok.** `security`, `core`, `context`, `memory`, `device`, `engine`, `policy`, `tools`, `ui` hepsi **`src/lumos_core/`** altında; hiçbiri `src/` kökünde top-level paket değil.

**Hangisi yanlış yerde ve neden?**  
- **src/main.py:** Tek bilinçli “dışarıda” dosya; **stub** (sadece `lumos_core.interactive_cli.main` çağırıyor). Tercih edilen giriş `python -m lumos_core` olduğu için konumu tartışılabilir ama kırılmama için bilerek bırakıldı.  
- **src/scripts/:** İçinde sadece README var (init_keystore/init_identity `lumos_core.scripts`’e taşındı). “Yanlış” değil; legacy yönlendirme.  
- **src/main.py.bak\*** vb.: Yedek dosyalar; paket değil, isteğe bağlı temizlenebilir.

**Minimum hamle ile nasıl toplanacak?**  
- Ek taşıma gerekmiyor: çekirdek zaten tek paket (`lumos_core`). İstersen: (1) `main.py` stub’ı kalsın, (2) `src/scripts/` README kalsın, (3) `main.py.bak*` dosyalarını `.gitignore`’a ekle veya sil (minimal temizlik).

---

## 2. GitHub: default branch ve koruma (AMAÇ 5)

**Default branch:** Repo **Settings → General** sayfasında, en üstte **Default branch** alanı var (Branches sayfası değil). Oradan varsayılan dalı (örn. `kando/main` veya `main`) seçip **Update** ile kaydedin.

**Silme engelleme:** **Settings → Rules → Rulesets** (veya **Branches → Branch protection rules**) içinde ilgili kuralda **“Allow deletions”** kapalı olursa, o branch silinmez. Kuralı o branch’e uygulayın.

**“Not enforced” uyarısı:** Private repo’da organizasyon/plan ayarına göre bazı korumalar “Not enforced” görünebilir. Bu durumda silme/force push’u **yerel disiplin + PR akışı** ile yönetin; merge öncesi inceleme ve doğrudan push’u sınırlayan bir akış yeterli olur.

---

## 3. Son çıktı (net sonuç)

1. **~/WORK_2026** artık repo değil; sadece **workspace**. (`.git` yok; `.git_BACKUP_DO_NOT_TOUCH` varsa yedek.)
2. **~/WORK_2026/lumos-core** tek ana repo; çekirdek + monorepo içinde lumos-social.
3. **lumos-social** yolu net: **monorepo** (lumos-core içinde `lumos-social/`). Dışarıdaki ~/WORK_2026/lumos-social sandbox/arşiv; repo’ya bağlanmıyor.
4. **python -m pytest** çalışıyor; Makefile ve CI’da test **python -m pytest** ile çalışıyor.
5. **“Yanlış yerdeki klasör”** için kısa rapor ve minimal fix planı yukarıda (modül konumu raporu + minimum hamle).

---

## 4. Cursor “Submit from a previous message?” penceresi

Bu popup çıkarsa: **“Continue without reverting”** seçin (revert istemiyoruz); sonra normal şekilde ilerleyin.
