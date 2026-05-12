# Kando lokal HTTP bridge (`kando_bridge_server.py`)

**Kaynak kod:** `packages/kando_bridge/src/kando_bridge/server.py` (`python -m kando_bridge`).
`scripts/kando_bridge_server.py` aynı `main()` girişine ince bir sarmalayıcıdır.

ChatGPT, tarayıcı eklentisi veya başka bir istemci **bu makinede** çalışan küçük bir HTTP sunucusuna istek atar; sunucu metni `.lumos/inbox/request.txt` dosyasına yazar. **`kando_watch.py`** bu dosyayı tetikleyici olarak kullanıp Kando zincirini (bridge / patch / apply) çalıştırır.

## Önkoşullar

- Depo kökünde `.lumos/inbox/` kullanılabilir olmalı (ilk yazımda oluşturulur).
- Arka planda **watcher** açık olmalı:

```bash
cd /path/to/lumos-core
PYTHONPATH=src python scripts/kando_watch.py
```

## Sunucuyu başlatma

Depo kökünden:

```bash
cd /path/to/lumos-core
PYTHONPATH=src python -m kando_bridge
# veya eşdeğer:
PYTHONPATH=src python3 scripts/kando_bridge_server.py
```

Varsayılan: **`127.0.0.1:8765`**. Bind adresi **yalnızca** `127.0.0.1`, `::1` veya `localhost` olabilir (`0.0.0.0` reddedilir). İstemci adresi de loopback değilse **403**.

| Ortam değişkeni | Anlamı |
|-----------------|--------|
| `KANDO_BRIDGE_PORT` | Dinlenecek port (CLI `--port` ile geçersiz kılınır) |
| `KANDO_BRIDGE_SECRET` | Dolu ise her POST için token zorunlu |

## Güvenlik

1. **Ağ**: Sunucu varsayılan olarak `127.0.0.1` üzerinde dinler; uzak makinadan doğrudan bağlanılmaz.
2. **Token** (isteğe bağlı): `KANDO_BRIDGE_SECRET` ayarlandığında istekte şunlardan biri gerekir:
   - `X-Kando-Token: <secret>`
   - veya `Authorization: Bearer <secret>`

## API

### `GET /` veya `GET /health`

Sunucu ayakta mı kontrolü (kısa JSON).

### `POST /task`

Gövde:

- **`application/json`**: `{"text": "görev metni ..."}`
- **`text/plain`**: gövde doğrudan görev metni
- **`application/x-www-form-urlencoded`**: `text=...` veya `task=...`

Yanıt (200):

```json
{
  "accepted": true,
  "request_path": "/abs/path/to/lumos-core/.lumos/inbox/request.txt",
  "queued_text": "görev metni ..."
}
```

Hata (4xx/5xx): `accepted: false`, `error` alanı.

## Örnek curl

Token yok:

```bash
curl -sS -X POST http://127.0.0.1:8765/task \
  -H "Content-Type: application/json" \
  -d '{"text":"görev: src/core/foo.py küçük düzeltme"}'
```

Token ile:

```bash
export KANDO_BRIDGE_SECRET='örnek-gizli-dize'
PYTHONPATH=src python scripts/kando_bridge_server.py &
curl -sS -X POST http://127.0.0.1:8765/task \
  -H "Content-Type: application/json" \
  -H "X-Kando-Token: örnek-gizli-dize" \
  -d '{"text":"görev: ..."}'
```

## Watcher ile birlikte akış

1. Terminal A: `PYTHONPATH=src python scripts/kando_watch.py`
2. Terminal B: `PYTHONPATH=src python scripts/kando_bridge_server.py`
3. İstemci `POST /task` ile metni yollar → `request.txt` güncellenir → watcher tetiklenir → Kando çalışır → sonuçlar `.lumos/outbox/` ve `cursor_bridge/` altında güncellenir (mevcut `kando_watch` davranışı).

## İlişkili araçlar

- `scripts/kando_send.py` — aynı `request.txt` dosyasına CLI’dan yazar; bridge ile aynı hedef.
- `scripts/local_chat_relay.py` / `relay_agent.py` — pano veya başka relay ile entegrasyon; bridge HTTP’sine `curl` veya küçük bir istemci ile bağlanabilir.

## Sınır

ChatGPT **web/masaüstü uygulamasının** kendi başına bu porta istek atması mümkün değildir; pratik köprüler: tarayıcı eklentisi, kopyala-yapıştır relay, veya OpenAI API ile kendi istemciniz. Bu sunucu, **yerelde** çalışan istemcinin güvenli bir giriş noktasıdır.
