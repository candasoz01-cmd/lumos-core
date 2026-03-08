# Son çıktı — özet rapor

## 1. Paket dışına taşan / yanlış yerdeki modüller

**Şu an hangi modüller paket dışına taşmış?**
- **Hiçbiri.** `security`, `core`, `context`, `memory`, `device`, `ui`, `tools` hepsi **`src/lumos_core/`** altında; top-level’da ayrı `src/security` veya `src/core` yok.
- Paket dışında kalan tek şeyler: **`src/main.py`** (bilinçli stub) ve **`src/scripts/`** (içi boşaltıldı, sadece README kaldı).

**Hangisi yanlış yerde ve neden?**
- **`src/main.py`** — Teknik olarak paket dışında; amaçlı stub (doğrudan `lumos_core.interactive_cli`’ye yönlendiriyor). İstersen kaldırıp tek girişi `python -m lumos_core` yapabilirsin.
- **`src/scripts/`** — Eski init script’leri `lumos_core.scripts`’e taşındı; bu klasörde sadece “taşındı” README’si var. Tamamen silinip yalnızca `lumos_core.scripts` kullanılabilir.
- **Repo kökündeki `scripts/legacy_runner.py`** — `import main` kullanıyor (sys.path’e src ekleyerek). `main` artık py-module değil; çalışması için `src`’in path’te olması ve `src/main.py` stub’ının kalması gerekiyor. Minimum hamle: `import main` → `from lumos_core.interactive_cli import main` yapıp stub’a bağımlılığı kaldırmak.

**Minimum hamle ile nasıl toplanacak?**
1. **`scripts/legacy_runner.py`:** `import main` yerine `from lumos_core.interactive_cli import main` kullan (veya `lumos_core`’u path’e ekleyip aynı import). Böylece `src/main.py` stub’ı opsiyonel olur.
2. **İsteğe bağlı:** `src/main.py` stub’ını sil; herkes `python -m lumos_core` / `lumos` kullansın.
3. **İsteğe bağlı:** `src/scripts/` klasörünü tamamen kaldır (içinde sadece README var).

---

## 2. GitHub: default branch ve koruma

**Default branch:** Repo **Settings → General** sayfasında, en üstte **Default branch** alanı var (Branches sayfası değil). Oradan ana branch’i (örn. `kando/main` veya `main`) seçip **Update** ile kaydedebilirsin.

**Silme engeli:** Branch koruma kurallarında (**Branch protection rules**) “Allow force pushes” / “Allow deletions” kapalıysa, o branch silinmez. Private repo’da bazı kurallar plan/organizasyona göre “Not enforced” uyarısı verebilir; bu durumda korumayı yerel disiplin ve PR akışıyla (force push / silme yapmama) yönetebilirsin.

---

## 3. Son çıktı (istenen 5 madde)

| # | İstenen | Durum |
|---|--------|--------|
| 1 | ~/WORK_2026 artık repo değil; sadece workspace | **Evet.** `.git` yok (sadece `.git_BACKUP_DO_NOT_TOUCH`). |
| 2 | ~/WORK_2026/lumos-core tek ana repo | **Evet.** Tek kaynak repo; monorepo (içinde lumos-social/). |
| 3 | lumos-social için seçilen yol net; karışıklık yok | **Evet.** Monorepo: lumos-social repo içinde; dış ~/WORK_2026/lumos-social sandbox/legacy (docs/EXTERNAL_LUMOS_SOCIAL.md). |
| 4 | python -m pytest çalışıyor; CI’da da aynı çağrı | **Evet.** Makefile: `PYTEST := $(PYTHON) -m pytest`; CI `make check` ile aynı. |
| 5 | “Yanlış yerdeki klasör” kısa rapor + minimal fix planı | **Var.** Yukarıdaki “Paket dışına taşan / yanlış yerde” + “Minimum hamle” bölümü. |

---

## 4. Cursor “Submit from a previous message?” penceresi

Bu popup çıkarsa: **“Continue without reverting”** seç (revert istemiyoruz); sonra normal şekilde devam et.
