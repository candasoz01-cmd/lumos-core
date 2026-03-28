# ChatGPT → yerel Kando (pano dinleyici)

## Teknik sınır (dürüst)

**ChatGPT masaüstü veya web uygulaması**, kullanıcı mesajlarını bilgisayarınızdaki bir porta veya sürece **göndermez**. Resmi bir “localhost webhook” veya “mesaj dinleyici API” yoktur. Bu yüzden **tam otomatik doğrudan entegrasyon** (yalnızca ChatGPT’ye yazıp hiçbir yerel adım olmadan) **mümkün değildir**.

## Çalışan MVP

`scripts/local_chat_relay.py`:

1. ChatGPT’de görev metnini üretin ve **kopyalayın**.
2. Metnin başına tek satır ekleyin: **`KANDO>>`** (veya `LUMOS_CLIPBOARD_PREFIX` ile özelleştirin).
3. Yerelde **izleme** veya **tek atım** ile relay’e POST edilir; zincir: `relay_agent` (8766) → bridge → `kando_watch` → Kando → `.lumos/outbox/`.

Böylece **Mac Terminalinde görev yazma** kalkar; tek tekrarlayan adım ChatGPT yanıtını **KANDO>>** ile işaretleyip kopyalamaktır.

## Önkoşullar (arka plan süreçleri)

Depo kökünde, mevcut hattınız açık olmalı:

- `PYTHONPATH=src python scripts/kando_watch.py`
- `PYTHONPATH=src python scripts/kando_bridge_server.py` — ayrıntı: [README_kando_bridge_server.md](README_kando_bridge_server.md)
- `PYTHONPATH=src python scripts/relay_agent.py`

## Çalıştırma

Depo kökü:

```bash
# Sürekli: pano değişince KANDO>> ile başlayan metni gönder
PYTHONPATH=src python scripts/local_chat_relay.py --watch
```

Tek sefer (panodan):

```bash
PYTHONPATH=src python scripts/local_chat_relay.py --clipboard
```

stdin (ör. kısayol veya başka araçtan pipe):

```bash
printf 'KANDO>>patch: README.md\nhello\n' | PYTHONPATH=src python scripts/local_chat_relay.py --stdin
```

## Ortam

| Değişken | Açıklama |
|----------|----------|
| `RELAY_URL` / `RELAY_PORT` | Relay (varsayılan `http://127.0.0.1:8766`) |
| `KANDO_WAIT_TIMEOUT_SEC` | Outbox bekleme (saniye) |
| `LUMOS_CLIPBOARD_PREFIX` | Tetik öneki (varsayılan `KANDO>>`) |
| `KANDO_CLIPBOARD_POLL_SEC` | `--watch` örnekleme aralığı (varsayılan `1`) |
| `--no-notify` | macOS bildirimini kapatır |

## Ortak kod

`src/kando/relay_outbox_client.py` — relay POST + outbox bekleme + özet; `chatgpt_agent.py` ile paylaşılır.

## Hâlâ mümkün olmayan tek şey

ChatGPT uygulamasının kendisinin, siz yazarken **otomatik olarak** yerel bir sürece veri göndermesi — **API yok**; tek gerçekçi köprüler: kopyala-yapıştır (bu script), tarayıcı eklentisi, veya OpenAI **API** ile kendi istemciniz (`chatgpt_agent.py` gibi).
