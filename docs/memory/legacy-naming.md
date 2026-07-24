# Legacy Naming — iç katman adları (tarihçe)

> **Durum:** Salt tarihçe. Yeni geliştirme, doküman veya UI metninde legacy adlar **kullanılmaz**.  
> **Canonical karar:** [`../decisions/ADR-018-internal-layers-core-local-sentinel.md`](../decisions/ADR-018-internal-layers-core-local-sentinel.md) · OD-061

Bu dosya, emekliye ayrılmış iç katman adlarını **yalnızca tarihçe** için tutar. Mimari rol anlatımı güncel adlarla [`internal-agent-layers.md`](./internal-agent-layers.md) içindedir.

## Eşleme (kilitli)

| Legacy ad | Güncel ad | Rol (özet) |
|-----------|-----------|------------|
| **Kando** | **Core** | İç çalışma / koordinasyon |
| **Cando** | **Local** | İç uygulama / iş yürütme |
| **Bando** | **Sentinel** | Güvenlik / gözlem / anomali (executor değil) |

Dış yüzey adı değişmedi: **Lumos**.

## Legacy Naming

Aşağıdaki adlar **emeklidir**. Yeni metin, ADR, kod yorumu veya ürün kopyasında kullanılmaz.

- Kando → yerine **Core**
- Cando → yerine **Local**
- Bando → yerine **Sentinel**

### Teknik tanımlayıcılar (henüz yeniden adlandırılmadı)

Bunlar katman adı değil; dosya yolu / env / HTTP başlığıdır. Yeniden adlandırma ayrı kesme işidir; bu ADR onları “güncel katman adı” yapmaz.

| Tanımlayıcı | Not |
|-------------|-----|
| `packages/kando_*`, `archive/packages/kando_*`, `src/kando/` | Paket / modül yolları (OD-027) |
| `kando_bridge`, `kando_runtime` | Canlı köprü paket adları |
| `KANDO_BRIDGE_SECRET`, `KANDO_MOCK` | Ortam değişkenleri |
| `X-Kando-Token` | HTTP başlığı (geri uyumluluk) |
| `cando_local.py`, `tests/cando/` | Yerel recipe CLI yolları |
| `local-kando-dev-runbook.md`, `kando-urun-onay-otomasyon-ayrimi.md` | Eski dosya adları (içerik güncel adlarla) |

### Marka bileşimi (ayrı karar)

`KandoLumos` dış iletişim marka dizgisidir; iç katman adı değildir. Marka yeniden adlandırma bu OD kapsamı dışındadır (ayrı kurucu kararı gerekir).

## Ne zaman bu dosyaya bakılır?

- Eski sohbet / PR / commit’te legacy ad görünürse eşlemeyi doğrulamak için.
- Guard testi allowlist’i için.

Son güncelleme: 2026-07-23
