# Yerel HTTP köprüsü (`kando_bridge_server.py`)

**Kaynak kod:** `packages/kando_bridge/src/kando_bridge/server.py` (`python -m kando_bridge`).
`scripts/kando_bridge_server.py` aynı `main()` girişine ince bir sarmalayıcıdır.

ChatGPT, tarayıcı eklentisi veya başka bir istemci **bu makinede** çalışan küçük bir HTTP sunucusuna istek atar; sunucu metni `.lumos/inbox/request.txt` dosyasına yazar. **`kando_watch.py`** bu dosyayı tetikleyici olarak kullanıp yerel görev zincirini (köprü / patch / apply) çalıştırır.

## Önkoşullar

- Depo kökünde `.lumos/inbox/` kullanılabilir olmalı (ilk yazımda oluşturulur).
- Arka planda **watcher** açık olmalı:

```bash
cd /path/to/lumos-core
PYTHONPATH=src python scripts/kando_watch.py
```

## Sunucuyu başlatma

Depo kökünden (önce yerel secret **zorunlu**):

```bash
cd /path/to/lumos-core
export KANDO_BRIDGE_SECRET='your-local-dev-secret'
./scripts/bridge_start.sh
```

`GET /health` token istemez (**200**); korumalı uç noktalar secret veya token olmadan **401** döner.

**Elle başlatma** (isteğe bağlı; `PYTHONPATH` üçlemesi `bridge_start.sh` ile aynı):

```bash
cd /path/to/lumos-core
export KANDO_BRIDGE_SECRET='your-local-dev-secret'
export PYTHONPATH="$PWD/src:$PWD/packages/kando_bridge/src:$PWD/packages/kando_runtime/src"
python3 -m kando_bridge
# veya eşdeğer sarmalayıcı:
python3 scripts/kando_bridge_server.py
```

Varsayılan: **`127.0.0.1:8765`**. Bind adresi **yalnızca** `127.0.0.1`, `::1` veya `localhost` olabilir (`0.0.0.0` reddedilir). İstemci adresi de loopback değilse **403**.

## Sunucuyu durdurma

Ön planda çalışıyorsa terminalde **Ctrl+C**. Arka planda PID ile başlattıysanız `kill <pid>` veya `pkill -f "kando_bridge"` (dikkat: aynı ada sahip başka süreçleri de kapatabilir).

## Port doluysa (`EADDRINUSE` / Address already in use)

Başka bir süreç aynı portu kullanıyorsa sunucu açılmaz. Kontrol örnekleri (macOS / Linux):

```bash
export KANDO_BRIDGE_PORT=8766
./scripts/bridge_start.sh
# veya mevcut dinleyeni görmek için:
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

`./scripts/bridge_start.sh` varsayılan port meşgulse açık bir mesajla çıkar; `KANDO_BRIDGE_PORT` ile boş port verip yeniden deneyin.

| Ortam değişkeni | Anlamı |
|-----------------|--------|
| `KANDO_BRIDGE_PORT` | Dinlenecek port (CLI `--port` ile geçersiz kılınır) |
| `KANDO_BRIDGE_SECRET` | **Zorunlu** — korumalı uç noktalar için paylaşımlı token (gap #5) |

### İsteğe bağlı STT (`POST /transcribe`)

Yerel faster-whisper yalnızca `[stt]` ekstra bağımlılığı ve env ile açılır; varsayılan kurulumda motor kapalıdır (**503**).

| Ortam değişkeni | Anlamı |
|-----------------|--------|
| `KANDO_STT_ENABLED` | `1` ise faster-whisper kuruluysa motor etkin |
| `KANDO_STT_MODEL` | Whisper modeli (varsayılan `tiny`) |
| `KANDO_STT_DEVICE` | `cpu` / `cuda` (varsayılan `cpu`) |
| `KANDO_STT_COMPUTE_TYPE` | Örn. `int8` (varsayılan `int8`) |
| `KANDO_STT_LANGUAGE` | Dil kodu; boş = otomatik (varsayılan `tr`) |
| `KANDO_STT_INTEGRATION` | `1` ise yerel entegrasyon testi çalışır (CI'da yok) |

Kurulum: `pip install -e 'packages/kando_bridge[stt]'` (depo kökünden uygun `PYTHONPATH` ile).

## Güvenlik

1. **Ağ**: Sunucu varsayılan olarak `127.0.0.1` üzerinde dinler; uzak makinadan doğrudan bağlanılmaz.
2. **Token (zorunlu)**: `KANDO_BRIDGE_SECRET` ayarlanmalıdır. Boş veya tanımsızsa korumalı uç noktalar **401** döner. İstekte şunlardan biri gerekir:
   - `X-Kando-Token: <secret>`
   - veya `Authorization: Bearer <secret>`
3. **Korumalı uç noktalar**: Tüm `POST` istekleri ve korumalı `GET` yolları (`/last-result`, `/outbox`, `/agent-status`, vb.) token ister. `GET /health` kimlik doğrulaması **gerektirmez** (durum kontrolü).
4. **Yerel geliştirme**: Gerçek üretim sırrı kullanmayın; yalnızca yerel placeholder:

```bash
export KANDO_BRIDGE_SECRET='your-local-dev-secret'
```

Persona güvenlik checkpoint’inde gap #5 anti-taklit köprü auth testleri bu davranışla geçer (`tests/test_persona_security_simdi_checkpoint.py`).

5. **Panel / tarayıcı:** `PUBLIC_KANDO_TOKEN` istemci bundle'ında görünür; gerçek köprü sırrını `PUBLIC_*` ile gömme — bkz. [gap #4](../docs/lumos-persona-security-implementation-gaps.md).

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

Secret ve token olmadan korumalı uç noktalar **401** döner. Yerel örnek:

```bash
export KANDO_BRIDGE_SECRET='your-local-dev-secret'
./scripts/bridge_start.sh &
curl -sS -X POST http://127.0.0.1:8765/task \
  -H "Content-Type: application/json" \
  -H "X-Kando-Token: your-local-dev-secret" \
  -d '{"text":"görev: src/core/foo.py küçük düzeltme"}'
```

Sağlık kontrolü (token gerekmez):

```bash
curl -sS http://127.0.0.1:8765/health
```

## Watcher ile birlikte akış

1. Terminal A: `PYTHONPATH=src python scripts/kando_watch.py`
2. Terminal B: `export KANDO_BRIDGE_SECRET='your-local-dev-secret'` ardından `./scripts/bridge_start.sh`
3. İstemci `POST /task` ile metni yollar → `request.txt` güncellenir → watcher tetiklenir → yerel görev zinciri çalışır → sonuçlar `.lumos/outbox/` ve `cursor_bridge/` altında güncellenir (mevcut `kando_watch` davranışı).

## Hızlı gönderim (`kando_send.py`)

Bridge ayaktayken terminalden doğrudan `POST /task` (dosyaya elle yazmaz):

```bash
cd /path/to/lumos-core
export KANDO_BRIDGE_SECRET='your-local-dev-secret'
./scripts/bridge_start.sh &
python3 scripts/kando_send.py "görev: src/core/foo.py küçük düzeltme"
```

Stdin / pipe (panodan veya pipe ile yapıştırma):

```bash
export KANDO_BRIDGE_SECRET='your-local-dev-secret'
echo 'patch: README.md' | python3 scripts/kando_send.py
pbpaste | python3 scripts/kando_send.py
python3 scripts/kando_send.py   # argümansız: stdin'den okur
```

macOS pano kısayolu: `export KANDO_BRIDGE_SECRET='…'` sonrası `./scripts/kando_clip.sh` (`pbpaste | kando_send.py`).

Birden fazla argv kelimesi tek mesajda birleştirilir. `KANDO_BRIDGE_SECRET` zorunludur; 401 alırsanız bridge ile aynı secret'ı export edin.

## İlişkili araçlar

- `scripts/kando_send.py` — köprüye `POST /task` ile gönderir (bridge `request.txt`'ye yazar); doğrudan dosya yazmaz.
- `scripts/local_chat_relay.py` / `relay_agent.py` — pano veya başka relay ile entegrasyon; bridge HTTP’sine `curl` veya küçük bir istemci ile bağlanabilir.

## Sınır

ChatGPT **web/masaüstü uygulamasının** kendi başına bu porta istek atması mümkün değildir; pratik köprüler: tarayıcı eklentisi, kopyala-yapıştır relay, veya OpenAI API ile kendi istemciniz. Bu sunucu, **yerelde** çalışan istemcinin güvenli bir giriş noktasıdır.

Yanıtlarda `Access-Control-Allow-Origin: *` üretilir; yine de `GET`/`POST` için istemci adresi **loopback** olmalıdır. Panel (`npm --prefix ui run dev`) ile aynı makinede `127.0.0.1` köprüsüne istek atıldığında tarayıcı CORS açısından genelde sorunsuzdur; paneli **Vercel gibi uzak bir origin**den açıp yerel `127.0.0.1` köprüsüne bağlanmak tarayıcıda engellenebilir (karma içerik / özel ağ erişimi); bu durumda köprüyü erişilebilir bir hostta ayrı yayınlamanız veya tünel kullanmanız gerekir.
