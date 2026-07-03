# AnchorUSB — macOS deneysel POC (scripts)

**Bu dizin üretim güvenlik aracı veya Lumos Key değildir.** macOS üzerinde araştırma ve deneme amaçlı, **POC seviyesinde** betikler ve yardımcılardır.

## Konum ve statü

- **lumos-core** içinde izlenen **deneysel POC**; şimdilik ayrı repo açılmaz.
- Tasarım **bağımsız ve taşınabilir** tutulur («bağımsız tasarla, ayrı repo açma»): olgunlaştıkça `packages/secure-device` veya ayrı `lumos-secure-device` deposuna taşınabilir; ilk ev **bu dizin** ve ilgili crate’lerdir.
- Bileşen, **Secure Device Framework** altında yeniden kullanılabilir güvenlik modülüne evrilebilir.

## Yaşam döngüsü

- Aşama: **Research Memory** → deneysel **M2–M3 POC** (USB tak/çıkar, mount algılama, Touch ID denemeleri).
- Operasyonel USB/vault modeli için: [`docs/analysis/secure-device/anchorusb-lifecycle.md`](../../docs/analysis/secure-device/anchorusb-lifecycle.md).

## İlgili kod ve kararlar

| Bağlantı | Açıklama |
|----------|----------|
| [`crates/anchorusb-core`](../../crates/anchorusb-core) | `.vault` konteyner kütüphanesi (yerel, ağ yok) |
| [`docs/analysis/secure-device/anchorusb-lifecycle.md`](../../docs/analysis/secure-device/anchorusb-lifecycle.md) | USB yaşam döngüsü (dokümantasyon) |
| [`docs/drafts/BACKLOG.md` — LUMOS-0009](../../docs/drafts/BACKLOG.md) | Trust Layer / Lumos Key **kapsamı**; bu POC **üretim Lumos Key değildir** |

## Sınırlar

- **Yalnızca macOS** (shell, IOKit/USB, LocalAuthentication denemeleri).
- **Ağ yok**; bu dizinde **gizli anahtar, parola veya üretim sırları** tutulmaz.
- CI entegrasyonu ve üretim dağıtımı bu POC’nin parçası değildir.

## Dizin içeriği (özet)

- `anchorusb-usb-plug-poc.sh` — USB takılma POC
- `anchorusb-mount-lib.sh`, `test-mount-detect.sh` — mount algılama
- `anchorusb-touchid.swift`, `build-touchid.sh` — Touch ID derleme/deneme (`bin/` yerel derleme çıktısı, git dışı)

Yerel derleme: `./build-touchid.sh` (çıktı `bin/`, `.gitignore` ile hariç).
