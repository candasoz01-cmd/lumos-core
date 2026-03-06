# Paket dışı taşma ve “yanlış yerde” raporu

## Şu an hangi modüller paket dışına taşmış?

**Hiçbiri.** Tüm canlı modüller tek paket altında: `src/lumos_core/` (context, core, device, engine, memory, policy, security, tools, ui, scripts). Top-level `security`, `core`, `context` yok; hepsi `lumos_core` içinde.

## Hangisi yanlış yerde ve neden?

| Konum | Durum | Neden |
|-------|--------|--------|
| **src/main.py** | Stub (bilinçli) | Sadece `lumos_core.interactive_cli`’ye yönlendiriyor; tek giriş `python -m lumos_core`. Doğru yerde sayılır. |
| **src/scripts/** | Eski dizin | İçinde sadece README kaldı; `init_keystore` / `init_identity` → `lumos_core.scripts` taşındı. “Yanlış” değil, boşaltılmış. |
| **src/security.bak_lock/** | Yedek | Paket değil; eski kilit kodları. Taşma değil, arşiv. |
| **src/main.py.bak\*** | Yedek dosyalar | Repo köküne dağılmış backup’lar; .gitignore’a alınabilir. |
| **lumos.py** (repo kökü) | Düzeltildi | Eski: `from main import main` → Yeni: `from lumos_core.interactive_cli import main`. |

## Minimum hamle ile nasıl toplanacak?

1. **Yapıldı:** Giriş noktası tek paket üzerinden: `lumos_core` (+ stub main.py). Scriptler `lumos_core.scripts`. `lumos.py` import’u `lumos_core.interactive_cli` olacak şekilde güncellendi.
2. **İsteğe bağlı:** `src/main.py.bak*` ve `src/security.bak_lock/` için .gitignore kuralı ekle (örn. `*.bak*`, `security.bak_lock/`) veya arşivleyip sil; böylece `src/` altında sadece `lumos_core/` + `main.py` (stub) + isteğe bağlı `scripts/README` kalır.
3. **Sonuç:** Tek doğru ağaç `src/lumos_core/`; dışarı taşan modül yok. “Yanlış yerde” olanlar ya stub ya yedek; minimum müdahale ile toplanmış durumda.
