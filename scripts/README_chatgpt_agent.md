# ChatGPT ↔ Core local agent

`scripts/chatgpt_agent.py` terminalden kullanıcı metni alır, OpenAI **Responses API** ile görev metnine çevirir ve mevcut relay'e JSON `goal` gönderir. Bridge yanıtındaki `job_id` ile mevcut yerel agent sonuç kaydını bekler; eski relay yalnız `ok` döndürürse ilişkili Cursor outbox çiftini kullanır. ChatGPT masaüstü/web uygulamasını dinlemez; elle kopyalanan metin için [yerel pano relay'i](README_local_chat_relay.md) vardır.

## Önkoşullar ve route sözleşmesi

- `openai` paketi bulunan proje Python ortamı ve `OPENAI_API_KEY` gerekir. Anahtarı koda veya Git'e koymayın.
- İstemci kendi depo kökünün `.lumos/outbox` dizinini okur; bridge/üretici aynı dizine yazmalıdır. İstemci `LUMOS_BASE_DIR` ile başka bir outbox seçmez.
- `scripts/kando_watch.py` devre dışıdır (exit 2); çalıştırmayın. İş yönlendirmesi bridge içindedir.
- `relay_agent.py` varsayılan olarak `http://localhost:8765/task` kullanır. Eski `BRIDGE_URL=http://localhost:8765` veya sonu `/` olan origin ayarına `/task` eklenir; açıkça verilmiş diğer yollar korunur.
- Relay mevcut bridge HTTP durumunu ve JSON yanıtını değiştirmeden iletir. `accepted` / `ok` / HTTP 200 tamamlanma değildir; onay bekleyen iş de `accepted=true` dönebilir. Yeni endpoint veya onay atlama yoktur.

## Ortam değişkenleri

| Değişken | Açıklama |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI API anahtarı; zorunlu |
| `OPENAI_MODEL` | Varsayılan `gpt-4.1-mini` |
| `RELAY_URL` / `RELAY_PORT` | İstemcinin relay adresi; varsayılan `http://127.0.0.1:8766` |
| `BRIDGE_URL` | **Relay sürecinin** bridge adresi; varsayılan `http://localhost:8765/task` |
| `KANDO_WAIT_TIMEOUT_SEC` | Outbox bekleme saniyesi; varsayılan `600` |
| `LUMOS_AGENT_STREAM` | `1` (varsayılan): Responses streaming; `0`: senkron `responses.create` |
| `LUMOS_AGENT_STREAM_STYLE` | `execution` (varsayılan): kısa durum + görev metni; `verbose`: mevcut reasoning delta olayları stderr'de, metin stdout'ta |
| `LUMOS_AGENT_SKIP_BRIDGE` | `1`: yalnız LLM akışı; relay'e gönderilmez |

## Çalıştırma

Aşağıdaki komutlar operatör içindir; offline testler canlı zincirin doğrulandığı anlamına gelmez. Depo kökünde, ayrı terminallerde:

```bash
HOST=127.0.0.1 PYTHONPATH=src python scripts/kando_bridge_server.py
```

```bash
BRIDGE_URL=http://127.0.0.1:8765/task PYTHONPATH=src python scripts/relay_agent.py
```

API anahtarını ortamda tanımladıktan sonra:

```bash
PYTHONPATH=src .venv/bin/python scripts/chatgpt_agent.py
```

`>` isteminde görevi yazıp Enter'a basın. Ctrl+D / Ctrl+C ile çıkılır. Streaming kapatmak için `LUMOS_AGENT_STREAM=0`, yalnız metin üretmek için `LUMOS_AGENT_SKIP_BRIDGE=1` kullanılır.

## Sonucu kabul sözleşmesi

Her açık gönderim, mevcut `goal` metninin sonuna benzersiz `[relay:<uuid>]` etiketi ekler. Aynı metnin aynı saniyede yeniden gönderimi farklı etikete sahiptir. Relay'in mevcut `görev: ` öneki korunur; yeni HTTP alanı veya sonuç endpoint'i yoktur.

Güncel bridge JSON yanıtı için:

- `requires_approval`, `requires_clarification` veya `video_prompt_clarification=true`: **PENDING**, exit `7`; istemci onay vermez.
- `accepted=false`, `ok=false`, hata veya başarısız/kısmi/simülasyon outcome: **FAILED**, exit `6`.
- Güncel `/task` tek-agent işi de `mode=lumos_plan` olarak döner. Yalnız `execution=plan_completed`, `outcome=applied` ve tam bir `step_results=[{type:agent, job_id:..., ok:true}]` adımı desteklenir. Üst `job_id`, adım ID'si ve yerel kayıt ID'si aynı olmalıdır. `step_results[].ok` yalnız başlatma bilgisidir, tamamlanma değildir.
- Bu planın `normalized_task.mode=agent` olması, `normalized_task.raw_payload` ve `agent_blob` alanlarının gönderilen UUID etiketli metnin `görev: ` önekli haliyle **tam eşleşmesi** gerekir. Bu alanları gerçek `_build_result_after_execute` katmanı HTTP yanıtına ekler. Eksik bağlama `UNSUPPORTED/8`, farklı istek `CORRELATION_MISMATCH/6` üretir.
- Eski `mode=agent` yanıtı için terminal `final_report.task`, gönderilen `görev: ` önekli etiketli metinle tam eşleşmelidir. Farklı/eksik task veya farklı UUID başarı değildir. Güncel planner ise görev metnini Intent/Reason biçimine dönüştürdüğünden özgün metin terminal task'a zorla eşitlenmez; onun istek bağı yukarıdaki normalized alanlardan kurulur.
- Geçerli 16 küçük hex karakterlik `job_id` için mevcut `kando.agent_runner.get_job_status` okuyucusu `.lumos/outbox/agent_status_<job_id>.json` kaydını izler. Ortak `agent_last.json` veya `last_*.json` bu işin yerine okunmaz.
- Bu kayıt bulunamazsa, bozuksa, başka ID taşıyorsa veya timeout sonunda hâlâ çalışıyorsa: **PENDING**, exit `7`; yeni POST yapılmaz.
- İşçi `completed` yazmış olsa bile başarı için `phase=done`, `final_report.status=ok`, boolean `final_report.verify.ok=true` ve hem işçi hem rapor `errors=[]` gerekir. Terminal `final_report.task` boş olmayan metin olmalıdır; legacy agent için yukarıdaki tam eşleşme de zorunludur. `failed`, eksik veya çelişkili terminal kayıt exit `6` döndürür.
- Diğer yanıtlar **UNSUPPORTED**, exit `8`. Özellikle ID'siz receipt, `direct_patch` / `lumos_gate`, birden fazla/nested adımlı veya patch/agent_auto içeren `lumos_plan` receipt'i tamamlanma sayılmaz. Bir planın son `job_id` değeri bütün adımların sonucu değildir. Bu türler için yeni terminal sonuç şeması uydurulmaz.

Eski relay yalnız düz `ok` döndürürse geriye uyum için Cursor outbox çifti beklenir. Yalnız şu koşullarda kabul edilir:

1. Her iki dosyanın mtime'ı gönderim öncesi değerinden yenidir.
2. İki dosya okunurken kimlik/boyut/zaman bilgileri değişmez; eksik, kısmi veya bozuk JSON kabul edilmez.
3. `execution.goal`, gönderilen etiketli metnin `görev: ` önekli haliyle **tam** eşleşir.
4. İki paketteki `task_id` aynı pozitif tamsayıdır; eksik ID, `0`, bool, metin ve float kabul edilmez.
5. `result.goal_preview`, `execution.goal` metninin ilk 500 karakteriyle eşleşir; bu mevcut Cursor paket üreticisinin kuralıdır.

Kabul edilmiş terminal kayıt veya Cursor çifti bellekte tutulur; özet ve başarı kararı için dosyalar yeniden okunmaz. Eski Cursor çifti için `outcome=applied`, `task_status=tamamlandi` ve JSON boolean `brain_success=true` birlikte olmadıkça başarı bildirilmez. `failed`, `blocked`, `partial`, `simulation` veya eksik/çelişkili durumlar başarı değildir; sonuç gösterilir ve exit `6` döner.

HTTP/taşıma veya okunamayan HTTP yanıtı exit `4`, eski Cursor çiftinin bulunamaması exit `5`, başarısız sonuç `6`, pending iş `7`, desteklenmeyen receipt `8` döndürür. Başarı exit `0` ile bildirilir. HTTP 200 tek başına tamamlanma değildir. Teslim belirsizse otomatik yeniden gönderim yapılmaz; program durur. Yeniden başlatıp göndermek **yeni bir istektir**; önce mevcut sonucu ve etkileri operatör olarak inceleyin. UUID etiketi sunucuda idempotency veya tam bir kez yürütme garantisi sağlamaz.

Bu sözleşme offline fixture testleriyle sınanır. Güncel başarı fixture'i gerçek route → normalize → plan → execute → result wrapper/payload → HTTP envelope zincirini kullanır; politika/model kararları ve agent başlatma fixture ile değiştirilir, gerçek iş çalıştırılmaz. Gerçek Responses API → relay → bridge → görev sonucu zinciri ve otomatik ChatGPT uygulama entegrasyonu bu testlerle doğrulanmış değildir.
