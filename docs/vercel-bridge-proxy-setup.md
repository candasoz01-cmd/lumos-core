# Vercel bridge proxy — kurulum ve 503 davranışı

| Alan | Değer |
|------|-------|
| **Belge türü** | Operasyon / dev runbook (docs only) |
| **Kod** | `api/bridge/[...path].js` |
| **Durum** | Prod: env tanımsız → beklenen 503 |

---

## Ne yapar?

Panel same-origin **`/api/bridge/*`** isteklerini yerel veya tünel üzerindeki **yerel köprü** (local bridge) upstream'e iletir. Proxy önce caller auth + path allowlist uygular; sonra bridge token'ı (`KANDO_BRIDGE_SECRET`) yalnızca sunucu tarafında eklenir. Token tarayıcıya sızmaz.

Desteklenen yollar: `task`, `chat`, `last-result`, `controlled`, `transcribe`.

---

## Gerekli ortam değişkenleri (Vercel)

Vercel proje ayarları → **Environment Variables** (Production / Preview / Development):

| Değişken | Zorunlu | Örnek | Not |
|----------|---------|-------|-----|
| `BRIDGE_UPSTREAM_URL` | Evet (köprü için) | `https://<tunnel-host>` | Sondaki `/` yok; `http://127.0.0.1:8765` yalnızca `vercel dev` + yerel köprü |
| `KANDO_BRIDGE_SECRET` | Evet (köprü için) | *(gizli — repoya yazmayın)* | Köprü ile aynı değer |
| `LUMOS_BRIDGE_PROXY_AUTH_TOKEN` | Evet (proxy auth) | *(gizli — repoya yazmayın)* | Public `/api/bridge/*` caller auth; `KANDO_BRIDGE_SECRET` ile aynı olmak zorunda değil |

**Asla** `PUBLIC_*` veya client bundle'a koymayın. Şablon: [`.env.example`](../.env.example).

Caller auth iki yoldan kabul edilir:
- `X-Lumos-Bridge-Auth: <LUMOS_BRIDGE_PROXY_AUTH_TOKEN>` header
- `lumos_bridge_proxy_auth=<LUMOS_BRIDGE_PROXY_AUTH_TOKEN>` cookie

Prod panel için tercih edilen yol, auth katmanının HTTP-only cookie set etmesidir. Header yolu smoke / operatör testi içindir.

---

## Neden prod'da 503?

`BRIDGE_UPSTREAM_URL` boş veya tanımsızsa proxy şunu döner:

```json
{
  "ok": false,
  "error": "bridge_proxy_unconfigured",
  "message": "Panel bağlantısı yapılandırılmamış..."
}
```

HTTP **503** — **beklenen davranış**; panel «bağlantı yapılandırılmamış» UX'ini gösterir. Bu bir deploy hatası değil, bilinçli «köprü yok» durumudur.

---

## Ortam karşılaştırması

| Ortam | Köprü | Panel görev akışı |
|-------|-------|-------------------|
| **Yerel dev** | Yerel köprü @ `127.0.0.1:8765` + `vercel dev` | `BRIDGE_UPSTREAM_URL` + `KANDO_BRIDGE_SECRET` + `LUMOS_BRIDGE_PROXY_AUTH_TOKEN` |
| **Prod (welockai.com)** | Upstream internetten erişilebilir olmalı | Vercel'de `BRIDGE_UPSTREAM_URL` = **HTTPS tünel veya barındırılmış köprü URL'si** |
| **Prod (env yok)** | Yok | `/api/bridge/*` → **503** (Sınırlı mod; yerel görevler çalışır) |

**Not:** `127.0.0.1` Vercel serverless'tan erişilemez. Prod için ngrok/Cloudflare Tunnel vb. veya kalıcı barındırılmış köprü gerekir — **tünel URL'si ve secret repoda commit edilmez**.

---

## Quick start for owner (prod köprü — 5 adım)

Secret veya tünel URL'si **repoya yazılmaz**. Owner Vercel dashboard + yerel makinede yapar.

1. **Yerel köprüyü doğrula** — `make bridge` (veya runbook); `127.0.0.1:8765` yanıt veriyor mu kontrol et.
2. **HTTPS tünel aç** — ngrok, Cloudflare Tunnel vb. ile köprüyü internete aç; **tünel base URL**'ini not et (sonda `/` yok).
3. **Vercel env ekle** — Proje → Settings → Environment Variables → Production (+ Preview isteğe bağlı):
   - `BRIDGE_UPSTREAM_URL` = tünel base URL (ör. `https://xxxx.ngrok-free.app`)
   - `KANDO_BRIDGE_SECRET` = köprü ile **aynı** gizli değer (yalnızca Vercel + yerel köprüde; repoda yok)
   - `LUMOS_BRIDGE_PROXY_AUTH_TOKEN` = public proxy caller auth değeri
4. **Redeploy** — Env değişikliğinden sonra Production redeploy (Vercel otomatik veya manual).
5. **Smoke** — `curl -sS -H "X-Lumos-Bridge-Auth: $LUMOS_BRIDGE_PROXY_AUTH_TOKEN" -o /dev/null -w "%{http_code}" https://welockai.com/api/bridge/task` → **503 değil** (köprü yanıt kodu); panelden görev gönder → 200.

Env yokken **503 = beklenen**; adım 3 atlanırsa panel Sınırlı modda kalır — deploy hatası sayılmaz.

---

## Yerel doğrulama

```bash
# Terminal 1 — köprü
make bridge   # veya proje runbook'undaki eşdeğeri

# Terminal 2 — UI + proxy
export BRIDGE_UPSTREAM_URL='http://127.0.0.1:8765'
export KANDO_BRIDGE_SECRET='<your-local-secret>'
export LUMOS_BRIDGE_PROXY_AUTH_TOKEN='<your-proxy-auth-token>'
vercel dev
```

Smoke header ile yapılır; panel akışı için aynı token cookie olarak set edilmiş olmalıdır.

---

## Prod smoke (env olmadan)

```bash
curl -sS -o /dev/null -w "%{http_code}" https://welockai.com/api/bridge/task
# Beklenen: 503 (GET/POST method fark etmez — upstream yok)
```

Köprü yapılandırıldıktan sonra aynı uç nokta köprü yanıt kodunu yansıtır.

---

## Owner verification checklist (copy-paste)

Secret veya tünel URL'si **repoda yok**. Owner Vercel dashboard + yerel makinede tamamlar. Durum: **OWNER_ACTION**.

| # | Adım | Doğrulama |
|---|------|-----------|
| 1 | Yerel köprü: `make bridge` (veya `./scripts/bridge_start.sh`) | `curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/health` veya runbook eşdeğeri → **200** veya köprü yanıt kodu |
| 2 | HTTPS tünel aç (ngrok / Cloudflare Tunnel) | Tünel base URL not edildi (sonda `/` yok) |
| 3 | Vercel → Settings → Environment Variables → **Production** | `BRIDGE_UPSTREAM_URL` = tünel URL; `KANDO_BRIDGE_SECRET` = köprü secret; `LUMOS_BRIDGE_PROXY_AUTH_TOKEN` = caller auth |
| 4 | Production **redeploy** | Deploy log success |
| 5 | Env **yokken** smoke (beklenen 503) | `curl -sS https://welockai.com/api/bridge/task \| jq -r '.error'` → `bridge_proxy_unconfigured` (veya HTTP 503) |
| 6 | Env **varken** smoke | `curl -sS -H "X-Lumos-Bridge-Auth: $LUMOS_BRIDGE_PROXY_AUTH_TOKEN" -o /dev/null -w "%{http_code}" https://welockai.com/api/bridge/task` → **503 değil** (köprü yanıtı; genelde 4xx/2xx köprüye bağlı) |
| 7 | Panel görev akışı | Auth katmanı `lumos_bridge_proxy_auth` cookie set eder; welockai.com `/panel` → görev gönder → 200 (köprü ayaktaysa) |

**Not:** Adım 5 env yokken **başarı** sayılır (bilinçli Sınırlı mod). Adım 6–7 yalnızca owner env set ettikten sonra.

---

## Çapraz referanslar

| Belge | Konu |
|-------|------|
| [Yerel köprü runbook](local-kando-dev-runbook.md) | Yerel tam akış |
| [mac-app-link-layer.md](mac-app-link-layer.md) | Prod URL listesi |
| [INTERNAL_ALPHA_OPERATIONS.md](INTERNAL_ALPHA_OPERATIONS.md) | Alpha operasyon |

---

*Son güncelleme: 2026-06-26 — owner verification checklist (OWNER_ACTION); 503 beklenen davranış.*
