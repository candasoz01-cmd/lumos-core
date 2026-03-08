# Paket yeri raporu — “taşan” ve yanlış yerdeki modüller

## Şu an hangi modüller paket dışına taşmış?

**Yok.** Tüm çekirdek modüller `src/lumos_core/` altında: `security`, `core`, `context`, `memory`, `device`, `engine`, `policy`, `tools`, `ui`, `scripts`, `ai_providers`, `system` hepsi **lumos_core** içinde. Top-level paket tek: **lumos_core**. `src/security` veya `src/core` gibi paket dışı dallanma yok.

---

## Hangisi yanlış yerde ve neden?

| Konum | Durum | Neden |
|-------|--------|------|
| **src/main.py** | İnce stub (sadece yönlendirme) | Paket dışında tek `.py`; tek amacı `lumos_core.interactive_cli.main` çağırmak. Kalması “python src/main.py” ile çalıştırmayı sürdürür; kaldırılırsa tek giriş `python -m lumos_core` olur. |
| **src/scripts/** | Artık sadece README | Asıl scriptler `lumos_core.scripts`’e taşındı. Dizin “taşındı” notu için duruyor; silinirse tek kaynak net kalır. |
| **src/main.py.bak\*** | Yanlış yerde | Yedek dosyalar repo kökünde; versiyon kontrolü ve dağıtımı kirletir. Silinmeli veya .gitignore’a alınmalı. |

---

## Minimum hamle ile nasıl toplanacak?

1. **main.py.bak\***  
   - `.gitignore`’a ekle: `main.py.bak*` (veya `*.bak`, `*.bak_*`).  
   - Zaten commit’lendiyse: `git rm --cached src/main.py.bak*` sonra commit; dosyaları silmek isteğe bağlı.

2. **src/main.py**  
   - **Seçenek A (minimal):** Olduğu gibi bırak; “giriş stub’ı” olarak dokümante et.  
   - **Seçenek B (tek giriş):** Sil; tüm kullanımı `python -m lumos_core` / `lumos` yap. Makefile/README’de “run: python -m lumos_core” olduğundan tek satır doküman güncellemesi yeterli.

3. **src/scripts/**  
   - İçinde sadece README varsa: Dizini silip README’deki “scriptler lumos_core.scripts’te” notunu kök veya `docs/REPO_LAYOUT.md`’ye taşı. Böylece tek paket ağacı netleşir.

**Özet:** Taşan modül yok; tek “yanlış yerde” olan şey backup dosyaları. Minimum fix: backup’ları ignore/remove, isteğe bağlı olarak main stub ve boş scripts dizinini kaldır.
