# Repo ve workspace düzeni

## Karar kuralı (workspace / repo)

- **~/WORK_2026/lumos-core sağlamsa:** ~/WORK_2026 altında kalan her şey **workspace klasörü** olarak kalır; WORK_2026 kendisi repo **olmayacak**.
- **lumos-social ayrı repo olacaksa:** İleride bağlanır; **şu an** birleştirme/karıştırma yok. Şimdilik monorepo.

## Monorepo (şu anki seçim) — AMAÇ 2

- **Tek repo:** lumos-core. İçinde **lumos-social/** klasörü yer alır (sosyal katman: Telegram, ileride Facebook/TikTok/YouTube vb.).
- **~/WORK_2026/lumos-social** (dışarıdaki ayrı klasör): Sandbox / eskiden kalma. Repo'ya bağlı değil; yerel denemeler için durabilir. Kaynak gerçek: lumos-core içindeki `lumos-social/`. Bu klasördeki README'de "sandbox/legacy" notu vardır.
- Submodule şu an kullanılmıyor (gereksiz karmaşa).

## Çekirdek paket ağacı (src layout) — tek paket, yanlış yerde dosya yok

- **Tek top-level paket:** `src/lumos_core/` (context, core, device, engine, memory, policy, security, tools, ui, scripts). **src/ altında tek paket klasörü lumos_core;** başka top-level paket yok. Tüm çekirdek kodu `lumos_core` altında; çekirdeği büyütürken yalnızca `src/lumos_core/...` altına eklenir. `src/` kökündeki `main.py.bak*` dosyaları arşivdir; istenirse ayrı PR ile taşınabilir veya silinebilir.
- **pyproject.toml:** `[tool.setuptools.packages.find]` ile `include = ["lumos_core*"]` tanımlı; sadece bu paket kurulur. src/ altına yeni top-level paket eklenmemeli.
- **Giriş:** `python -m lumos_core` veya `lumos` (cli); interaktif CLI: `lumos_core.interactive_cli.main`.
- **Yardımcı scriptler:** `lumos_core.scripts.init_keystore`, `lumos_core.scripts.init_identity`. (Eski `src/scripts/` kaldırıldı; tek yer lumos_core.scripts.)

## Test / CI (pytest, ruff)

- **Prensip:** `pytest` / `ruff` komutuna güvenilmez; her yerde `python -m pytest` ve `python -m ruff` kullanılır. Makefile: `PYTEST := $(PYTHON) -m pytest`, `RUFF := $(PYTHON) -m ruff`; `make test`, `make lint`; CI: `make check` sonra `python -m ruff check .`.
- **Dev bağımlılıklar:** Önce `python -m pip install -e ".[dev]"`; pytest yoksa `python -m pip install pytest`; ruff yoksa `python -m pip install ruff`. CI: `pip install -e ".[dev]"` sonra `make check` ve `python -m ruff check .`.

## Klasör yapısı (WORK_2026)

```
WORK_2026/                    # repo değil
├── lumos-core/               # tek kaynak repo (içinde lumos-social/)
│   ├── src/
│   │   └── lumos_core/       # tek paket (çekirdek)
│   ├── lumos-social/         # monorepo içinde
│   ├── ...
├── lumos-social/             # sandbox/legacy (bağlanmaz)
└── lumos-quantum/            # ayrı dizin (demo/entropy)
```
