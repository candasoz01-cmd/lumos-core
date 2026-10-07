# ChatGPT → yerel Core (pano / stdin relay'i)

`scripts/local_chat_relay.py`, kullanıcının ChatGPT'den **elle kopyaladığı** metni yerel relay'e iletir. ChatGPT masaüstü/web uygulamasını dinlemez ve bu kodda otomatik uygulama entegrasyonu yoktur. `--watch` yalnız macOS panosunu örnekler.

## Metin sözleşmesi

1. Görev metnini ChatGPT'de üretip kopyalayın.
2. Başına **`CORE>>`** koyun; ardından en az 8 karakter görev metni olmalıdır.
3. `--clipboard`, `--stdin` veya `--watch` ile gönderin.

Varsayılan kod, yardım ve örneklerde `CORE>>`'dir. Eski `KANDO>>` önekini kullanmak için `LUMOS_CLIPBOARD_PREFIX='KANDO>>'` açıkça ayarlanabilir. Önek eşleşmesi büyük/küçük harfe duyarlıdır.

## Önkoşullar ve route sözleşmesi

İstemci mevcut `relay_agent` (8766) → bridge → Core → `.lumos/outbox` hattını kullanır. Bridge ile istemcinin outbox dizini aynı olmalıdır; istemci kendi depo kökünün `.lumos/outbox` dizinini okur.

`scripts/kando_watch.py` artık çalışmaz (exit 2); başlatmayın. Relay varsayılanı `http://localhost:8765/task` olup eski origin-only `BRIDGE_URL` ayarları da `/task` yoluna çevrilir. Bridge HTTP durumu ve JSON yanıtı korunur. `/task` alındı özeti (`accepted` / `ok`) tamamlanmış görev kanıtı değildir; onay bekleyen yanıt da kabul edilmiş olabilir.

Mevcut bridge hakkında [bridge README'sine](README_kando_bridge_server.md), paket kabul koşulları için [ortak sonuç sözleşmesine](README_chatgpt_agent.md#sonucu-kabul-sözleşmesi) bakın. Bu istemci düzeltmesi bridge/relay sunucularına yeni API eklemez; canlı hat doğrulanmış değildir.

## Çalıştırma

Uygun yerel hat operatör tarafından hazırlandıktan sonra depo kökünden:

```bash
# Pano değişince CORE>> ile başlayan metni gönder
PYTHONPATH=src python scripts/local_chat_relay.py --watch
```

Panodan tek gönderim:

```bash
PYTHONPATH=src python scripts/local_chat_relay.py --clipboard
```

stdin (macOS dışında da kullanılabilir):

```bash
printf 'CORE>> README dosyasını özetle\n' | PYTHONPATH=src python scripts/local_chat_relay.py --stdin
```

## Ortam

| Değişken / seçenek | Açıklama |
|--------------------|----------|
| `RELAY_URL` / `RELAY_PORT` | Relay; varsayılan `http://127.0.0.1:8766` |
| `KANDO_WAIT_TIMEOUT_SEC` | Outbox bekleme saniyesi; varsayılan `600` |
| `LUMOS_CLIPBOARD_PREFIX` | Tetik öneki (varsayılan `CORE>>`) |
| `KANDO_CLIPBOARD_POLL_SEC` | `--watch` örnekleme aralığı; varsayılan `1` |
| `--no-notify` | macOS bildirimini kapatır |

## Sonuç ve tekrar gönderim

Her açık gönderim benzersiz `[relay:<uuid>]` etiketi alır. Güncel `/task` tek-agent yanıtı `mode=lumos_plan` olur: tam bir agent adımı, `execution=plan_completed`, `outcome=applied` ve üst/adım/kayıt job ID eşleşmesi gerekir. `normalized_task.mode=agent`, `raw_payload` ve `agent_blob` özgün `görev: ` önekli UUID etiketli isteği tam taşımalıdır. Eksik bağlama `UNSUPPORTED/8`, farklı istek `CORRELATION_MISMATCH/6` olur.

Eski `mode=agent` için terminal `final_report.task` özgün önekli/etiketli istekle tam eşleşmelidir. Güncel planner task metnini yeniden yazdığı için onun istek bağı normalized alanlarla kurulur. Geçerli job ID için mevcut `get_job_status` okuyucusu yalnız `.lumos/outbox/agent_status_<job_id>.json` kaydını izler; ortak son sonuç dosyası bu işin yerine geçmez.

Eski relay düz `ok` döndürürse iki Cursor outbox dosyası yeni ve okuma boyunca değişmeden kalmalı; tam `execution.goal`, ortak pozitif tamsayı `task_id` ve `result.goal_preview` eşleşmelidir. Özet yalnız kabul edilmiş bellekteki kayıttan basılır.

“Görev tamamlandı” ve exit `0`, agent için `status=completed`, `phase=done`, `final_report.status=ok`, boolean `final_report.verify.ok=true` ve iki `errors=[]` koşulunu gerektirir. Terminal `final_report.task` boş olmamalıdır; legacy agent için tam istek eşleşmesi de zorunludur. Eski Cursor çifti için `outcome=applied` + `task_status=tamamlandi` + boolean `brain_success=true` gerekir.

Başarısız/kısmi/simülasyon veya eksik terminal sonuç exit `6`; HTTP/taşıma/yanıt okuma hatası `4`; eski Cursor eşleşmesi yokluğu `5` döndürür. Onay/netleştirme bekleme veya agent sonucu henüz yokluğu **PENDING / 7**; ID'siz veya desteklenmeyen receipt (**direct_patch**, **lumos_gate**, tek-agent biçimine uymayan **lumos_plan** dahil) **UNSUPPORTED / 8** olur. Birden fazla/nested adım, patch veya agent_auto içeren planın son işi bütün planın başarı kanıtı sayılmaz; `step_results[].ok=true` da yalnız başlatma bilgisidir. HTTP 200 ve `accepted=true` tek başına başarı değildir.

`--watch` değişmeyen pano içeriğini tekrar göndermez. Hata, belirsiz teslim, pending, unsupported veya başarısız sonuç sonrası izleme **durur**; pano değişip eski içerik geri gelse de otomatik yeniden gönderim olmaz. Yeniden başlatma ve gönderme yeni istek yaratır; önce mevcut sonucu/etkileri inceleyin. Bu etiket sunucuda idempotency garantisi değildir.

Ortak kod: `src/kando/relay_outbox_client.py`. Testler tamamen offline fixture kullanır; gerçek ChatGPT uygulaması veya canlı API entegrasyonu kanıtı değildir.
