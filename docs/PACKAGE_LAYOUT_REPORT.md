# Paket düzeni raporu

## Şu an hangi modüller paket dışına taşmış?

- **Hiçbiri.** `security`, `core`, `context`, `memory`, `device`, `ui`, `tools` hepsi **`src/lumos_core/`** altında; top-level paket sadece `lumos_core`.
- **Paket dışında kalanlar (kod değil):**
  - **src/main.py** — Tek dosya; sadece `lumos_core.interactive_cli.main` yönlendirmesi (bilinçli stub).
  - **src/scripts/** — İçinde sadece README + legacy/backup; asıl scriptler `lumos_core.scripts` altında.

## Hangisi yanlış yerde ve neden?

| Öğe | Durum | Neden |
|-----|--------|------|
| **src/main.py** | Kabul edilebilir | Tek giriş stub; istenirse kaldırılıp sadece `python -m lumos_core` kullanılabilir. |
| **src/scripts/** | Legacy | Eski init_keystore/init_identity buradaydı; artık `lumos_core.scripts`. Dizinde sadece README + .bak/run.sh kaldı. |
| **src/main.py.bak\*** | Gereksiz | Yedek dosyalar; repoda olmamalı, `.gitignore` veya temizlik konusu. |

**Yanlış yerde** sayılabilecek tek şey: **src/scripts/** ve **src/main.py.bak\*** (paket dışı kalıntı/backup).

## Minimum hamle ile nasıl toplanacak?

1. **main.py:** Olduğu gibi bırak (stub) **veya** silip dokümantasyonda “Çalıştırma: `python -m lumos_core`” de.
2. **src/scripts/:** README yeterli; dizini silmek yerine `.gitignore` ile `src/scripts/*.bak*`, `src/scripts/run.sh` ignore edilebilir; ya da tüm `src/scripts/` silinip README `docs/` altına taşınır.
3. **main.py.bak\***: `.gitignore`’a `main.py.bak*` ekle; mevcut .bak dosyalarını repodan kaldır (`git rm --cached` + commit).

Özet: Paket ağacı doğru (tek paket `lumos_core`). Minimum müdahale: backup’ları ignore et / temizle; scripts için sadece README yeterli veya scripts dizinini kaldır.

---

## GitHub: default branch ve koruma

**Default branch:** Repo **Settings → General** sayfasında, **Default branch** alanı (Branches sayfası değil). Oradan varsayılan dalı seçip **Update** ile kaydedin. **Branch protection:** Branches → Add rule (veya mevcut kural) → "Allow deletions" kapalı olursa silme engellenir. Private repo'da bazı kurallar "Not enforced" uyarısı verebilir (plan/organizasyona bağlı); bu durumda korumayı yerel disiplin ve PR akışıyla yönetin (ör. default'u silmeyin, PR ile merge).

---

## Son çıktı özeti

1. **~/WORK_2026** artık repo değil; sadece workspace.
2. **~/WORK_2026/lumos-core** tek ana repo.
3. **lumos-social** için seçilen yol net: monorepo (lumos-core içinde `lumos-social/`); dışarıdaki `~/WORK_2026/lumos-social` sandbox/legacy; karışıklık kalmıyor.
4. **python -m pytest** çalışıyor; CI'da da aynı çağrı (Makefile: `PYTEST := $(PYTHON) -m pytest`).
5. **Yanlış yerdeki klasör/dosya:** Sadece `src/main.py` (stub, kabul edilebilir), `src/scripts/` (legacy) ve `src/main.py.bak*` (temizlenmeli). Minimal fix: `.gitignore` ile backup'ları hariç tut; istenirse `main.py` stub kaldırılıp yalnızca `python -m lumos_core` kullanılır.
