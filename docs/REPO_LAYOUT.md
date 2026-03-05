# Repo ve workspace düzeni

## Karar kuralı

- **~/WORK_2026/lumos-core sağlamsa:** ~/WORK_2026 altındaki her şey "workspace klasörü" olarak kalır; WORK_2026 kendisi repo **değildir**.
- **lumos-social ileride ayrı repo olacaksa:** İleride bağlanır; şu an birleştirme/karıştırma yok.

## Monorepo (şu anki seçim)

- **Tek repo:** lumos-core. İçinde **lumos-social/** klasörü yer alır (sosyal katman: Telegram, ileride Facebook/TikTok/YouTube vb.).
- **~/WORK_2026/lumos-social** (dışarıdaki ayrı klasör): Sandbox / eskiden kalma. Repo'ya bağlı değil; yerel denemeler için durabilir. Kaynak gerçek: lumos-core içindeki `lumos-social/`.
- Submodule şu an kullanılmıyor (gereksiz karmaşa).

## Klasör yapısı (WORK_2026)

```
WORK_2026/                    # repo değil
├── lumos-core/               # tek kaynak repo (içinde lumos-social/)
│   ├── src/
│   ├── lumos-social/         # monorepo içinde
│   ├── ...
├── lumos-social/             # sandbox/legacy (bağlanmaz)
└── lumos-quantum/            # ayrı dizin (demo/entropy)
```
