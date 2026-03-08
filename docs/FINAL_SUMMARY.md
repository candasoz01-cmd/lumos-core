# Son çıktı — özet

## 1. ~/WORK_2026 artık repo değil; sadece workspace

- WORK_2026 içinde `.git` yok (sadece `.git_BACKUP_DO_NOT_TOUCH`).
- Git işlemleri için `cd lumos-core` kullanılır.

## 2. ~/WORK_2026/lumos-core tek ana repo

- Tüm çekirdek kodu bu repoda; tek top-level paket: `src/lumos_core/`.

## 3. lumos-social için seçilen yol net; karışıklık yok

- **Monorepo:** lumos-social, lumos-core içinde `lumos-core/lumos-social/` olarak duruyor.
- Dışarıdaki `~/WORK_2026/lumos-social` sandbox/legacy; repo’ya bağlanmıyor (bkz. `docs/EXTERNAL_LUMOS_SOCIAL.md`).

## 4. python -m pytest çalışıyor; CI’da da aynı çağrı

- Makefile: `PYTEST := $(PYTHON) -m pytest`; `make test` = `python -m pytest -q`.
- CI (`.github/workflows/ci.yml`) pytest kurup `make check` çalıştırıyor; aynı mantık.

## 5. “Yanlış yerdeki klasör” — kısa rapor + minimal fix

- **Rapor:** Bkz. `docs/PACKAGE_LAYOUT_REPORT.md`.
- **Özet:** Modüller paket dışına taşmıyor; tek “artık” yerler `src/scripts/` (içerik taşındı) ve `src/main.py.bak*` (yedekler).
- **Minimal fix:** scripts artıklarını sil/arşivle; isteğe bağlı olarak main.py.bak* dosyalarını .gitignore veya archive’a al.

---

**GitHub (AMAÇ 5):** Default branch ayarı **Repo → Settings → General** sayfasında, **Default branch** alanından yapılır (Branches sayfası değil). Branch koruma kurallarında “Allow force pushes” / “Allow deletions” kapatılırsa silme engellenir. Private repo’da bazı kurallar “Not enforced” gösterebilir (plan/organizasyona bağlı); bu durumda yerel disiplin ve PR akışıyla yönetmek yeterli. Cursor’da “Submit from a previous message?” penceresi çıkarsa **“Continue without reverting”** seç (revert istemiyoruz).
