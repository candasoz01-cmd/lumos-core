# Yerel köprü — hızlı dev runbook

Kısa smoke rehberi. Ayrıntılı API ve güvenlik: [Bridge server README](../scripts/README_kando_bridge_server.md).

## Phase 1: görev köprüsü proxy (`/api/bridge/task`)

Panel görev çağrıları (`POST /task`) artık tarayıcıdan doğrudan köprüye gitmez; same-origin **`/api/bridge/task`** üzerinden Vercel serverless proxy'ye gider. Proxy önce caller auth kontrolü yapar, sonra sunucu tarafında `KANDO_BRIDGE_SECRET` ekler ve `BRIDGE_UPSTREAM_URL/task` adresine iletir.

| Değişken | Konum | Açıklama |
|----------|--------|----------|
| `BRIDGE_UPSTREAM_URL` | Vercel / `vercel dev` (sunucu) | Örn. `http://127.0.0.1:8765` |
| `KANDO_BRIDGE_SECRET` | Vercel / `vercel dev` (sunucu) | Köprü token'ı; tarayıcıya gömülmez |
| `LUMOS_BRIDGE_PROXY_AUTH_TOKEN` | Vercel / `vercel dev` (sunucu) | `/api/bridge/*` caller auth; smoke / operatör header'ı |
| `LUMOS_BRIDGE_ALLOWED_LUMOS_IDS` | Vercel / `vercel dev` (sunucu) | Prod panel oturumu için virgülle ayrılmış Lumos ID allowlist'i |
| `PUBLIC_KANDO_TOKEN` | ui `.env.local` (isteğe bağlı) | **Yalnızca** sohbet / upload / health |

`BRIDGE_UPSTREAM_URL` veya proxy auth tanımsızsa proxy **503** döner; proxy auth hatalıysa **401** döner.

## Phase 2: medya outbox (`/api/bridge/last-result`)

Medya sekmesindeki “son sonuç” yenileme artık **`GET /api/bridge/last-result`** üzerinden gider; tarayıcı `X-Kando-Token` taşımaz. Proxy `BRIDGE_UPSTREAM_URL/last-result` adresine iletir. `BRIDGE_UPSTREAM_URL` yoksa **503** — görev akışıyla aynı “bağlantı yapılandırılmamış” mesajı.

## Phase 2 (adım 2): kontrollü dosya (`/api/bridge/controlled`)

Dosyalar sekmesi ve `file_rw` çağrıları artık **`POST /api/bridge/controlled`** üzerinden gider; tarayıcı `X-Kando-Token` taşımaz. Proxy `BRIDGE_UPSTREAM_URL/controlled` adresine iletir. `BRIDGE_UPSTREAM_URL` yoksa **503** — görev / last-result ile aynı “bağlantı yapılandırılmamış” mesajı.

Yerel smoke (proxy ile):

```bash
curl -sS -X POST http://localhost:3000/api/bridge/controlled \
  -H 'Content-Type: application/json' \
  -H "X-Lumos-Bridge-Auth: $LUMOS_BRIDGE_PROXY_AUTH_TOKEN" \
  -d '{"permission":"file_rw","tool":"read_file","action":"read_file","command":"read","path":"capability/_probe.txt"}'
```

Yerel smoke (proxy ile):

```bash
export KANDO_BRIDGE_SECRET='test123'
export BRIDGE_UPSTREAM_URL='http://127.0.0.1:8765'
export LUMOS_BRIDGE_PROXY_AUTH_TOKEN='local-proxy-auth'
./scripts/bridge_start.sh
# başka terminal:
vercel dev   # veya Vercel preview; Astro npm run dev tek başına /api/bridge sunmaz
```

## Önkoşul: token eşleşmesi (sohbet — görev / last-result / controlled dışı)

Sohbet, upload ve health probe hâlâ istemci `PUBLIC_KANDO_TOKEN` kullanır. Yerel geliştirmede köprü secret'ı ile bu token **aynı** olmalı:

```bash
export KANDO_BRIDGE_SECRET='test123'
# ui/.env veya shell:
# PUBLIC_KANDO_TOKEN=test123
```

`KANDO_BRIDGE_SECRET` sunucu tarafı; `PUBLIC_KANDO_TOKEN` tarayıcı bundle'ında görünür — yalnızca düşük riskli yerel placeholder kullanın. **Görev (`/task`) çağrıları** Phase 1'de proxy üzerinden gider; tarayıcı token taşımaz.

### Ortam dosyası adları

| Konum | Dosya | Not |
|--------|-------|-----|
| Astro UI | `ui/.env.local` | `npm run dev` buradan okur (`.env` değil); şablon: `ui/.env.example` → kopyala |
| Depo kökü | `.env` (şablon: `.env.example`) | `KANDO_BRIDGE_SECRET`, `OPENAI_API_KEY`, `BRIDGE_UPSTREAM_URL` — sunucu/köprü; `PUBLIC_*` yok |

Yerel smoke: `ui/.env.local` içinde `PUBLIC_KANDO_TOKEN`, shell'de `KANDO_BRIDGE_SECRET` — ikisi aynı değer.

### `PUBLIC_*` URL'ler (yerel smoke)

`PUBLIC_LUMOS_CHAT_URL` **tanımsızsa** panel varsayılan olarak Render'a gider (`https://lumos-core-1.onrender.com/chat`). Yerel köprü smoke için açıkça ayarlayın:

```bash
# ui/.env.local
PUBLIC_LUMOS_CHAT_URL=http://127.0.0.1:8765/chat
```

Aynı köprü portu (8765) için kontrol uçları:

```bash
PUBLIC_LUMOS_PANEL_UPLOAD_URL=http://127.0.0.1:8765/upload
PUBLIC_LUMOS_PANEL_HEALTH_URL=http://127.0.0.1:8765/health
```

## Port kontrolü (drift)

Smoke öncesi hangi sürecin hangi portta dinlediğini doğrulayın:

| Süreç | Varsayılan port | Not |
|--------|-----------------|-----|
| Köprü (`bridge_start.sh`) | **8765** | `KANDO_BRIDGE_PORT` ile değişir |
| Panel görev sunucusu | **8766** | `panel/scripts/panel_tasks_server.py` |
| Depo kökü / `ui/.env.example` | **8765** / **8766** | Köprü 8765; panel görev API 8766 (`PUBLIC_*` → `ui/.env.local`) |

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
lsof -nP -iTCP:8766 -sTCP:LISTEN
```

**8765 meşgulse:** `KANDO_BRIDGE_PORT=8766` köprüyü panel görev sunucusunun varsayılan portuyla çakıştırır (`panel_tasks_server` → 8766). Köprü için **8767+** kullanın veya görev sunucusunu farklı porta kaydırın; `ui/.env.local` içindeki `PUBLIC_*` URL'leri yeni köprü portuna göre güncelleyin.

**`127.0.0.1` tercih edin:** macOS'ta `localhost` bazen IPv6 (`::1`) çözülür; köprü `127.0.0.1`'de dinlerken panel `localhost` ile bağlanırsa bağlantı drift'i görülebilir. Smoke ve `curl` örneklerinde `127.0.0.1` kullanın.

## Başlatma sırası

Depo kökünden (`lumos-core`):

1. **Köprü** — secret zorunlu:

```bash
export KANDO_BRIDGE_SECRET='test123'
./scripts/bridge_start.sh
```

2. **Panel görev sunucusu** (statik panel + `/tasks` API):

```bash
python3 panel/scripts/panel_tasks_server.py
```

3. **UI** — proxy ile tam görev smoke için `vercel dev` (depo kökü); yalnızca Astro için `cd ui && npm run dev`:

```bash
# Depo kökü — görev proxy dahil:
export BRIDGE_UPSTREAM_URL='http://127.0.0.1:8765'
export KANDO_BRIDGE_SECRET='test123'
export LUMOS_BRIDGE_PROXY_AUTH_TOKEN='local-proxy-auth'
vercel dev
# Panel: http://127.0.0.1:3000/panel (vercel dev varsayılan portu)

# Alternatif: yalnız Astro (görev proxy yok; /api/bridge 404 veya 503 benzeri)
cd ui
# ui/.env.local örneği:
# PUBLIC_LUMOS_CHAT_URL=http://127.0.0.1:8765/chat
# PUBLIC_LUMOS_PANEL_UPLOAD_URL=http://127.0.0.1:8765/upload
# PUBLIC_LUMOS_PANEL_HEALTH_URL=http://127.0.0.1:8765/health
# PUBLIC_KANDO_TOKEN=test123
# PUBLIC_LUMOS_PANEL_TASKS_URL=http://127.0.0.1:8766
npm run dev
# Panel: http://127.0.0.1:4321/panel
```

Alternatif: `http://127.0.0.1:8766/index.html#chat` (panel_tasks_server statik paneli).

## Yerel `/chat` gereksinimleri

Köprü `POST /chat` OpenAI kullanır. Eksikse 5xx veya model hatası görülür.

- `openai` paketi kurulu (`.venv` veya proje bağımlılıkları)
- `OPENAI_API_KEY` export edilmiş
- Süreç `.venv` Python'u ile çalışıyor (`which python3` / `PATH`)

```bash
source .venv/bin/activate   # veya eşdeğeri
export OPENAI_API_KEY='sk-...'
```

## POST `/task` 401 — hızlı teşhis

| Neden | Kontrol |
|--------|---------|
| Secret tanımsız | Bridge terminalinde `KANDO_BRIDGE_SECRET` export edildi mi? |
| Token uyuşmazlığı | İstek `X-Kando-Token` veya `Authorization: Bearer` ile secret'ın aynısı mı? |
| Proxy auth eksik | `/api/bridge/*` isteğinde `X-Lumos-Bridge-Auth` header'ı veya `lumos_bridge_proxy_auth` cookie var mı? |
| Ortam uyumsuzluğu | `kando_send.py` / panel `PUBLIC_KANDO_TOKEN` farklı shell'de mi kaldı? |

`GET /health` token istemez; 401 yalnızca korumalı uç noktalarda (ör. `POST /task`).

## Sağlık kontrolleri

```bash
# Köprü ayakta mı (token gerekmez)
curl -sS http://127.0.0.1:8765/health

# Görev kuyruğu (token zorunlu)
export KANDO_BRIDGE_SECRET='test123'
curl -sS -X POST http://127.0.0.1:8765/task \
  -H "Content-Type: application/json" \
  -H "X-Kando-Token: test123" \
  -d '{"text":"smoke: köprü testi"}'
```

Beklenen: `/health` → 200 JSON; `/task` → 200 ve `accepted: true` (secret/token eşleşiyorsa).

## Smoke adımları

### 1. Pano iki tık

Panel sohbetinde **Panodaki metni ilet** butonu:

1. Panoya kısa bir metin kopyalayın.
2. İlk tık: onay / önizleme.
3. İkinci tık: gönder.

Beklenen geri bildirim: **Metin iletildi.**

### 2. Kimlik sorusu (sızıntı yok)

Panel sohbetinde veya doğrudan köprüye:

```bash
curl -sS -X POST http://127.0.0.1:8765/chat \
  -H "Content-Type: application/json" \
  -H "X-Kando-Token: test123" \
  -d '{"message":"ChatGPT misin, API mi kullanıyorsun?"}'
```

Soru: *"ChatGPT misin, API mi kullanıyorsun?"*

Beklenen: Lumos persona cevabı; **OpenAI / ChatGPT / API sağlayıcı adı veya teknik detay sızmamalı.**

## İlgili doküman

- [Bridge server README](../scripts/README_kando_bridge_server.md) — tam API, watcher akışı, `kando_send.py`, güvenlik notları
