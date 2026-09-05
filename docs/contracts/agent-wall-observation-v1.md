<!-- markdownlint-disable MD013 -->

# Lumos Agent Wall Observation v1

Durum: sözleşme taslağı — Faz-1 kapsamı kilitli, uygulama ayrı dilim.

Agent Wall bugün çakışma önleyicidir: [`task-claim-v1`](task-claim-v1.md) yazma başlamadan sahipliği ayırır, [`agent-status-v2`](agent-status-v2.md) kim ne yapıyor sorusunu gösterir. İkisi de **beyana** dayanır. Bu sözleşme üçüncü bir soruyu tanımlar: *beyan ile fiilen olan aynı mı?*

Gözlem katmanı **salt-okunurdur**. Hiçbir claim'i değiştirmez, hiçbir ajanı durdurmaz, hiçbir yazmayı engellemez.

**Yürütme bağlamı (2026-09-05):** Git tabanlı gözlem için birincil sınır sandbox’tır — [agent-wall-observer-sandbox-v0](agent-wall-observer-sandbox-v0.md), [ADR-033](../decisions/ADR-033-agent-wall-observer-sandbox.md). #832 head `d5248e26` sandbox MVP uygulanana kadar merge adayı değildir; yeni Git yönlendirme yaması yok.

## 1. Güven modeli — neden türetilmiş sinyal

Bu sözleşmenin tek belirleyici kararı budur.

[`TD-10`](../TECHNICAL_DEBT.md) kayıtlı: claim kimlikleri self-asserted, *"kötü niyetli ajan sahte kimlik beyan edebilir"*. Aynı sınır `agent_status_*.json` için de geçerlidir — sapan bir ajan kendi durum dosyasında da yanlış yazabilir.

Bu yüzden sinyaller ikiye ayrılır:

| Sınıf | Kaynak | Gözlemde kullanımı |
| --- | --- | --- |
| **Beyan** | `agent_status_*.json`, claim'in kendi `status` alanı | Yalnız bağlam. Tespit dayanağı **değildir**. |
| **Türetilmiş** | git geçmişi, çalışma ağacı durumu, `claim_events.jsonl` (append-only + fsync), dosya mtime | Tespit **yalnız** buna dayanır. |

Beyana dayanan bir gözlem katmanı yalnız dürüst ajanları izler; onlar zaten sorun değildir.

**Bu katman ajan kimliğini doğrulamaz.** TD-10 açık kalır. Gözlem, kimliğin doğru olduğunu varsaymaz — yalnız *bir claim ile bir etkinin uyuşup uyuşmadığını* söyler.

## 2. Faz-1 kapsamı: üç sinyal

Üçü de bugün main'de var olan veriden türetilir. Yeni emisyon, yeni ajan enstrümantasyonu, koşum yoluna müdahale **yoktur**.

### S1 — Kapsam dışı dokunuş

`claim.scopes` (beyan edilen repo-relative kapsamlar) ile dalın/çalışma ağacının fiilen dokunduğu dosyalar karşılaştırılır.

İki ayrı bulgu üretir; ağırlıkları farklıdır:

- `OUT_OF_SCOPE` — dokunulan yol hiçbir aktif claim kapsamında değil.
- `FOREIGN_SCOPE` — dokunulan yol **başka** bir `ACTIVE` claim'in kapsamında. Anayasa §3 ihlali adayıdır ve daha ağırdır.

Bu, §3'ün (*"bir dosyanın aynı anda yalnızca bir sahibi vardır"*) bugün yazılı norm olan hâlini ölçülebilir yapar.

### S2 — Sessiz sapma

Claim'in `task_id`'si bir işi söylerken dokunulan dosya kümesi başka bir işi anlatıyorsa bulgu üretilir. S1'in üstünde çalışır: kapsam dışı dokunuşların tek bir tutarlı başka işe kümelenmesi sapma göstergesidir.

Bunun gerçek bir örneği kayıtlıdır: `claude/console-lock-ast` dalında, claim'in söylediğinden farklı bir iş (retention süpürücüsü) yazıldı ve **10 gün commit edilmeden durdu**; ancak elle tarama ile bulundu ([`TD-29`](../TECHNICAL_DEBT.md), PR #827). Bu sinyal onu ilk gün görünür kılardı.

### S3 — Ritim ve asılı claim

`claim_events.jsonl` zaman damgalarından türetilir:

- `heartbeat_at` ile `expires_at` arasındaki sapma
- TTL aşımı (`EXPIRED` olması gerekirken `ACTIVE` görünen)
- uzun süre `ACTIVE` olup hiç olay üretmeyen claim

"Ajan çalışıyor mu, asılı mı" sorusunu ajanın kendi beyanına sormadan cevaplar.

## 3. Kapsam dışı — Faz-1'de yok

| Konu | Neden Faz-1'de değil |
| --- | --- |
| Anormal çağrı oranı | Ajan başına araç/çağrı sayacı **bugün yok**. `claim_events` claim yaşam döngüsünü sayar, iş hacmini değil. Yeni emisyon kararı gerekir. |
| Ajan başına bütçe / limit | `owner` bazlı bütçe kaydı yok; hacim ölçülmeden anlamsızdır. |
| Beklenmeyen hedefe erişim (egress) | Kısmi bir mekanizma **zaten çalışıyor**: pytest `test provenance` bloğu gerçek egress host'larını raporluyor. Sıfırdan yazılmaz, genişletilir — ayrı dilim. |
| Kontrol / engelleme | Bilinçli. Ölçülmemiş bir sinyalle kapı koymak, yanlış pozitifte çalışan ajanı durdurur. |
| Ajan kimliğinin doğrulanması | TD-10'un konusu. |
| `wall.py` (#807) entegrasyonu | Bağımlılık ters yönde kurulmaz; #807 merge olursa bu okuyucu onun altına girer. |

## 4. Çıktı: ayrı gözlem güncesi

Gözlem çıktısı **`.lumos/logs/wall_observations.jsonl`** dosyasına yazılır.

`evidence_continuity` hattına **bağlanmaz**. Gerekçe: o hattın payload'ı bilinçli olarak dar bir allowlist ile sınırlıdır (`src/core/evidence_continuity.py`), sapma bulgusu için gereken alanları taşıyamaz; ayrıca gözlem kaydının kendi yaşam döngüsü ve saklama kararı ayrı olmalıdır.

Şema: `lumos.agent_wall_observation.v1`

Zorunlu alanlar:

- `schema`, `at` (UTC, ISO-8601)
- `signal` — `OUT_OF_SCOPE` | `FOREIGN_SCOPE` | `SILENT_DRIFT` | `STALE_CLAIM`
- `claim_id`, `task_id`, `repo`, `owner` — gözlenen claim'den
- `evidence` — bulgunun **türetildiği** kanıt: dalda dokunulan yollar, olay zaman damgaları, karşılaştırılan kapsam
- `derived_from` — hangi kaynaklardan türetildiği (`git`, `claim_events`, `claim_store`); beyan kaynağı kullanıldıysa açıkça `agent_status` yazılır

Kurallar:

1. Kayıt **append-only**; gözlemci hiçbir satırı geri dönüp değiştirmez.
2. Dosya yolları repo-relative yazılır; mutlak yol ve makine yolu kaydedilmez.
3. Serbest metin `mask_secretlike` (`src/lumos_board/agent_status.py:150`) ile maskelenir; sapma raporu sır sızdıramaz.
4. Gözlemci claim store'a, `agent_status_*.json`'a veya çalışma ağaçlarına **yazmaz**.
5. Bir bulgu, üretildiği kanıt olmadan kaydedilmez — `evidence` boş olamaz.

## 5. Bu sözleşmenin vermediği garantiler

- **Tam kapsama değildir.** Commit edilmemiş ve hiç `git status`'a düşmemiş etki (ör. repo dışına yazma) görülmez.
- **Gerçek zamanlı değildir.** Gözlem periyodik okumadır; sapma anında değil, sonraki okumada görünür.
- **Yanlış pozitif üretir.** Meşru ama claim'de beyan edilmemiş dokunuşlar `OUT_OF_SCOPE` sayılır. Faz-1'in amacı bu oranı **ölçmektir**; kapı koymak değil.
- **Kötü niyetli ajana karşı tam değildir.** Git geçmişini ve claim güncesini üretebilen bir aktör sinyali de şekillendirebilir. Bu katman gizli düşmana karşı değil, **sessiz sapmaya** karşıdır.
