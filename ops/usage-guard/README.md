# lumos-usage-guard (TASLAK — deploy edilmedi)

Barındırılan yapay zekâ çağrıları (web sohbet, mobil sohbet, sesli görüşme anahtarı)
için kalıcı kullanım sayacı. Cloudflare Worker + tek SQLite Durable Object.

## Sınırlar (başlangıç)

| Sayaç | Sınır | Değişken |
|---|---|---|
| Kullanıcı / dakika | 10 | `LUMOS_USAGE_USER_PER_MINUTE` |
| Kullanıcı / gün (UTC) | 100 | `LUMOS_USAGE_USER_PER_DAY` |
| Tüm kullanıcılar / gün (UTC) | 2.000 | `LUMOS_USAGE_GLOBAL_PER_DAY` |

## Cloudflare ücretsiz plan hesabı

İzin verilen her istek: 1 Worker isteği + 1 Durable Object isteği + 3 satır yazma.
Reddedilen istek satır yazmaz. Tablo büyümez (sayaç başına tek satır).

| Ücretsiz sınır (günlük, 00:00 UTC) | Varsayılan tavanda (2.000 istek) | Oran |
|---|---|---|
| DO satır yazma 100.000 | 6.000 | %6 |
| DO isteği 100.000 | ≤ 2.000 izinli + reddedilenler | — |
| Worker isteği 100.000 (hesaptaki tüm Worker'larla ortak) | ≤ 2.000 izinli + reddedilenler | — |

Ücretsiz sınır aşılırsa Durable Object hata döner; Worker `503` verir ve Vercel
tarafı sağlayıcıya gitmez (kapalı varsayılan). Ücretli plana geçiş gerekmez.

## Bilinen sınırlar

- Tek nesne tek konumda çalışır: tüm istekler sırayla işlenir. Varsayılan
  tavan (günde 2.000) için yeterli; ölçek büyürse kullanıcı başına nesne
  + ayrı global nesne gerekir.
- Nesne erişilemezse sohbet ve ses kapanır (bilinçli, maliyet güvenliği için).
- İmzalı istek 60 sn içinde yeniden gönderilirse yalnız sayacı artırır;
  model erişimi vermez.

## Üretime geçiş (kurucu işleri — ajan yapmaz)

1. En az 32 karakterlik ortak gizli anahtar üret.
2. `wrangler secret put LUMOS_USAGE_GUARD_SECRET` (bu klasörde).
3. `wrangler deploy` → `*.workers.dev` adresi.
4. Vercel: `LUMOS_USAGE_GUARD_URL` (https adres) ve `LUMOS_USAGE_GUARD_SECRET`.
5. Vercel: `LUMOS_HOSTED_AI_ALLOWED_IDS` (PR-1).
6. Ancak bunlardan sonra PR-1 ve PR-2 merge/deploy; aksi halde sohbet kapanır.
