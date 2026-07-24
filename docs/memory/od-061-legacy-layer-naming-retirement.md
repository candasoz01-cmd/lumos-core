# OD-061 — Legacy iç katman adlarının emekliliği (Kando/Cando/Bando → Core/Local/Sentinel)

| Alan | Değer |
|------|--------|
| ID | OD-061 |
| Durum | **decision-approved** |
| Tarih | 2026-07-23 |
| ADR | [`ADR-018`](../decisions/ADR-018-internal-layers-core-local-sentinel.md) |
| Canonical katman kaydı | [`internal-agent-layers.md`](./internal-agent-layers.md) |
| Tarihçe | [`legacy-naming.md`](./legacy-naming.md) |

## Karar

Legacy katman adları (**Kando**, **Cando**, **Bando**) emeklidir. Güncel adlar: **Core**, **Local**, **Sentinel**. Eski adlar yalnızca Legacy Naming tarihçesinde kalır. Yeni geliştirmede tekrar kullanım yasaktır.

Rol sınırları (OD-006 / OD-007) değişmez; yalnızca adlandırma güncellenir.

## Uygulama

- Dokümanlar Core / Local / Sentinel ile hizalandı.
- `internal-communication-bando-decision.md` → `internal-communication-sentinel-decision.md`
- Guard: legacy katman adı (allowlist dışı) red

## Bekleyen (ayrı iş)

- Teknik tanımlayıcı cutover (`KANDO_*`, `X-Kando-Token`, paket yolları)
- `KandoLumos` marka kararı (kapsam dışı)
