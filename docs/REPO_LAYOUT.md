# Repo ve workspace düzeni

## Karar kuralı

- **~/WORK_2026/lumos-core sağlamsa:** ~/WORK_2026 altındaki her şey "workspace klasörü" olarak kalır; WORK_2026 kendisi repo **değildir**.
- **lumos-social ileride ayrı repo olacaksa:** İleride bağlanır; şu an birleştirme/karıştırma yok.

## Monorepo (şu anki seçim)

- **Tek repo:** lumos-core. İçinde **lumos-social/** klasörü yer alır (sosyal katman: Telegram, ileride Facebook/TikTok/YouTube vb.).
- **~/WORK_2026/lumos-social** (dışarıdaki ayrı klasör): Sandbox / eskiden kalma. Repo'ya bağlı değil; yerel denemeler için durabilir. Kaynak gerçek: lumos-core içindeki `lumos-social/`.
- Submodule şu an kullanılmıyor (gereksiz karmaşa).

## Çekirdek paket ağacı (src layout)

- **Tek top-level paket:** `src/lumos_core/` (context, core, device, engine, memory, policy, security, tools, ui, scripts).
- **Giriş:** `python -m lumos_core` veya `lumos` (cli); interaktif CLI: `lumos_core.interactive_cli.main`.
- **src/main.py:** Sadece yönlendirme (lumos_core.interactive_cli’yi çağırır); tercih: `python -m lumos_core`.
- **Yardımcı scriptler:** `lumos_core.scripts.init_keystore`, `lumos_core.scripts.init_identity` (eskiden src/scripts/).

## Klasör yapısı (WORK_2026)

```
WORK_2026/                    # repo değil
├── lumos-core/               # tek kaynak repo (içinde lumos-social/)
│   ├── src/
│   │   ├── lumos_core/       # tek paket (çekirdek)
│   │   └── main.py           # redirect stub
│   ├── lumos-social/         # monorepo içinde
│   ├── ...
├── lumos-social/             # sandbox/legacy (bağlanmaz)
└── lumos-quantum/            # ayrı dizin (demo/entropy)
```
