# Yerel Kando köprü — hızlı dev runbook

Kısa smoke rehberi. Ayrıntılı API ve güvenlik: [scripts/README_kando_bridge_server.md](../scripts/README_kando_bridge_server.md).

## Önkoşul: token eşleşmesi

Yerel geliştirmede köprü secret'ı ile panel token'ı **aynı** olmalı:

```bash
export KANDO_BRIDGE_SECRET='test123'
# ui/.env veya shell:
# PUBLIC_KANDO_TOKEN=test123
```

`KANDO_BRIDGE_SECRET` sunucu tarafı; `PUBLIC_KANDO_TOKEN` tarayıcı bundle'ında görünür — yalnızca düşük riskli yerel placeholder kullanın.

## Port kontrolü (drift)

Smoke öncesi hangi sürecin hangi portta dinlediğini doğrulayın:

| Süreç | Varsayılan port | Not |
|--------|-----------------|-----|
| Köprü (`bridge_start.sh`) | **8765** | `KANDO_BRIDGE_PORT` ile değişir |
| Panel görev sunucusu | **8766** | `panel/scripts/panel_tasks_server.py` |
| `.env.example` örnekleri | **8787** | Eski/alternatif backend örneği; yerel köprü akışında 8765 kullanın |

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
lsof -nP -iTCP:8766 -sTCP:LISTEN
```

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

3. **UI** — Astro panel (isteğe bağlı; tam panel deneyimi için):

```bash
cd ui
# Örnek ui/.env:
# PUBLIC_LUMOS_CHAT_URL=http://127.0.0.1:8765/chat
# PUBLIC_KANDO_TOKEN=test123
# PUBLIC_LUMOS_PANEL_TASKS_URL=http://127.0.0.1:8766
npm run dev
# veya build sonrası: npm run preview
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

- [scripts/README_kando_bridge_server.md](../scripts/README_kando_bridge_server.md) — tam API, watcher akışı, `kando_send.py`, güvenlik notları
