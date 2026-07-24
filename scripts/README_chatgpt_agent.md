# ChatGPT ↔ Core local agent

Terminalden kullanıcı metni alır, OpenAI **Responses API** ile görev metnine çevirir, `kando_bridge_server` üzerinden `request.txt` yazar, `kando_watch` / Core işini bitince `.lumos/outbox/last_result.json` ve `last_execution.json` dosyalarını okuyup kısa özet basar.

## Önkoşullar

- Depo kökünde çalışın (`.lumos` yolları buna göre).
- `openai` paketi yüklü bir Python kullanın (ör. `pip install -e .` ile proje ortamı veya `.venv`).
- `OPENAI_API_KEY` ortam değişkeninde tanımlı olsun; koda girmeyin.
- Arka plan: `kando_watch.py`, `kando_bridge_server.py`, `relay_agent.py`. ChatGPT uygulaması yerel porta komut göndermez; **terminalde yazmadan** sadece ChatGPT kullanmak için pano köprüsü: `scripts/local_chat_relay.py` ve `scripts/README_local_chat_relay.md`.

## Ortam değişkenleri

| Değişken | Zorunlu | Açıklama |
|----------|---------|----------|
| `OPENAI_API_KEY` | Evet | OpenAI API anahtarı |
| `OPENAI_MODEL` | Hayır | Varsayılan: `gpt-4.1-mini` |
| `BRIDGE_URL` | Hayır | Varsayılan: `http://localhost:8765` |
| `KANDO_WAIT_TIMEOUT_SEC` | Hayır | Outbox bekleme (saniye), varsayılan: `600` |
| `LUMOS_AGENT_STREAM` | Hayır | `1` (varsayılan) = Responses API **streaming**; `0` = senkron `responses.create` yedek |
| `LUMOS_AGENT_STREAM_STYLE` | Hayır | `execution` (varsayılan): olay bazlı kısa durum + görev metni canlı; `verbose`: reasoning özeti stderr’de, metin stdout’ta canlı (analiz/öneri/uzun reasoning için) |
| `LUMOS_AGENT_SKIP_BRIDGE` | Hayır | `1` ise yalnızca LLM akışı; bridge/Core çalışmaz |

Örnek: `export OPENAI_API_KEY=sk-...` veya `set -a; source scripts/chatgpt_agent.env.example; set +a` (dosyayı `.env` olarak kopyalayıp düzenleyin; repoya anahtar commit etmeyin).

## Çalıştırma

Terminal 1 (depo kökü):

```bash
python scripts/kando_watch.py
```

Terminal 2 (depo kökü):

```bash
python scripts/kando_bridge_server.py
```

Terminal 3 (depo kökü):

```bash
export OPENAI_API_KEY=sk-...
# Örnek: sanal ortamdan
.venv/bin/python scripts/chatgpt_agent.py
```

Agent isteminde `>` satırına isteğinizi yazın; Enter ile gönderilir.

### Streaming (varsayılan açık)

- **Aktif:** `LUMOS_AGENT_STREAM` tanımlı değil veya `1` iken `client.responses.stream(...)` kullanılır; görev metni token/token terminale akar.
- **Kapatma (fallback):** `LUMOS_AGENT_STREAM=0` → eski davranış: tek seferde `responses.create`, akış yok.
- **Stil:** `LUMOS_AGENT_STREAM_STYLE=execution` (varsayılan) → `response.created` / `in_progress` / ilk metin / `output_text.done` ile kısa `[durum] …` satırları; `verbose` → durum satırları yok, model reasoning delta olayları varsa stderr’e, görev metni stdout’a.

Örnek canlı akış (özet):

```text
… OpenAI Responses (streaming)
[durum] analiz ediliyor …
[durum] plan çıkarılıyor …
[durum] patch / görev metni üretiliyor …
Depodaki README dosyasını özetle.
[durum] doğrulanıyor …
```

Akış bitince aynı metin bridge’e POST edilir; ardından Core özeti okunur.

## Notlar

- Bridge sunucusu `localhost:8765` üzerinde POST gövdesini `.lumos/inbox/request.txt` olarak yazar; çalışma dizini depo kökü olmalı.
- `kando_watch` aynı içeriği tekrar görmezden gelir (`.last_request` ile). Aynı görevi tekrarlamak için metni biraz değiştirin veya ilgili durum dosyasını operatör olarak yönetin.
- Bu script mevcut Core / watcher / bridge kodunu değiştirmez; sadece üstte ince bir istemci katmanı ekler.
