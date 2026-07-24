# ADR-018 — İç katman adları: Core / Local / Sentinel

- **Durum:** Accepted (2026-07-23)
- **OD:** OD-061
- **Üst sınır:** `docs/lumos-karar-sozlesmesi.md`, `docs/memory/internal-agent-layers.md`

## Bağlam

İç katmanlar tarihsel olarak **Kando**, **Cando**, **Bando** adlarıyla anıldı. Bu adlar ürün yüzeyine sızma riski taşıyor, yeni belgelerde tutarsızlık üretiyor ve “üç marka” izlenimi veriyordu. Rol ayrımı (koordinasyon / yürütme / gözlem) korunmalı; yalnızca **adlandırma** sadeleşmeli.

## Karar

1. Güncel iç katman adları sabittir:
   - **Core** — iç çalışma / koordinasyon (eski: Kando)
   - **Local** — iç uygulama / yürütme (eski: Cando)
   - **Sentinel** — güvenlik / gözlem / anomali; executor değil (eski: Bando)
2. Dış yüzey **Lumos** kalır; iç katman adları kullanıcıya gösterilmez.
3. Legacy adlar yalnızca [`docs/memory/legacy-naming.md`](../memory/legacy-naming.md) **Legacy Naming** tarihçesinde geçer.
4. Yeni doküman, ADR, UI kopyası, commit mesajı şablonu veya mimari diyagramda legacy katman adları **yasaktır**.
5. Teknik tanımlayıcılar (`KANDO_BRIDGE_SECRET`, `X-Kando-Token`, `packages/kando_*`, `cando_local.py` vb.) bu ADR ile yeniden adlandırılmaz; ayrı cutover işidir. Bunlar katman adı sayılmaz.
6. `KandoLumos` marka dizgisi bu ADR kapsamı dışındadır.

## Sonuçlar

- Mimari belgeler Core / Local / Sentinel kullanır.
- OD-006 / OD-007 rol kararları geçerli kalır; ad güncellenir (Bando→Sentinel).
- Guard testi yeni legacy katman adı kullanımını reddeder (allowlist: `legacy-naming.md` + bu ADR’nin Legacy Naming bölümü).

## Legacy Naming

| Eski | Yeni |
|------|------|
| Kando | Core |
| Cando | Local |
| Bando | Sentinel |

Tarihçe ayrıntısı: [`docs/memory/legacy-naming.md`](../memory/legacy-naming.md).

## Bilinçli yapılmaz

- Wire protokol / env / paket yolu toplu rename (kırıcı)
- `src/security/`, vault, bridge davranış değişikliği
- Marka `KandoLumos` değişikliği

## İlişkili

- [`internal-agent-layers.md`](../memory/internal-agent-layers.md)
- [`internal-communication-sentinel-decision.md`](../memory/internal-communication-sentinel-decision.md) (eski dosya adı: `internal-communication-bando-decision.md`)
- [`product-rules.md`](../product-rules.md) PR-002 / PR-010
