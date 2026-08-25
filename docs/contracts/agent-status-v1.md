# Agent Status sözleşmesi — v1 (KA-001)

| Alan | Değer |
|------|-------|
| Durum | KOD adayı — bu PR ile |
| Kapsam kaydı | Scope accounting KA-001 (ortak ajan görünürlüğü) |
| Karar dayanağı | [ADR-008](../decisions/ADR-008-agent-network-boundary.md) — Lumos Board taksonomisindeki `Agent Status` bileşeni |
| Kod karşılığı | `src/core/agent_status_contract.py` |
| Şema sürümü | 1 |

Tek şema hem bu belgede hem kodda tanımlıdır; ayrışma olursa doküman
güncellenene kadar kod esas alınır.

## Amaç

Hangi ajanın hangi işle meşgul olduğunun **ortak, tipli ve salt okunur**
görünürlüğü. Bu sözleşme veri modelini sabitler; üzerine kurulacak paylaşım,
ekran veya koordinasyon işleri ayrı kapsamdır.

## Kapsam dışı (bilinçli, KA-001 v1)

- Yeni API endpoint, UI/panel değişikliği, WebSocket/SSE yok.
- `agent_runner` yazma davranışı değişmez; bu dilim yalnız okur.
- Event bus, dağıtık kilit, çok ajanlı orkestrasyon yok (ADR-008 gating'i geçerli).

## Şema v1

| Alan | Tip | Zorunlu | Anlam |
|------|-----|---------|-------|
| `version` | int | Evet | Şema sürümü; v1'de her zaman `1` |
| `agent_id` | str | Evet | Kaydı üreten ajanın kimliği (örn. `kando.agent_runner`) |
| `job_id` | str | Evet | İşin benzersiz kimliği |
| `status` | str | Evet | `running` / `completed` / `failed` / `unknown` |
| `owner` | str | Evet | İşi sahiplenen kimlik; çakışma tespitinin anahtarı |
| `started_at` | str \| null | Hayır | ISO 8601; bilinmiyorsa `null`, uydurulmaz |
| `updated_at` | str \| null | Hayır | ISO 8601; kaydın son güncellenme anı |
| `evidence_ref` | str | Evet | Kanıt referansı (durum dosyası yolu, evidence journal kaydı vb.) |
| `progress` | int \| null | Hayır | 0–100 arası ilerleme |
| `message` | str \| null | Hayır | Kısa, insan okunabilir durum |

## Eski dosyaların normalize edilmesi

Mevcut `agent_status_{job_id}.json` dosyaları (`src/kando/agent_runner.py`
üretir) yalnız `job_id`, `phase`, `status`, `final_report`, `errors` taşır.
Salt okunur okuyucu (`load_agent_status_records`) bunları şu kurallarla v1'e
çevirir:

| v1 alanı | Kaynak |
|----------|--------|
| `agent_id`, `owner` | Sabit `kando.agent_runner` (eski dosyada üretici kimliği yok) |
| `job_id` | Dosya içeriği; boşsa dosya adındaki `agent_status_{job_id}` deseni |
| `status` | Aynen; sözlük dışıysa `unknown` |
| `updated_at` | Dosya mtime (UTC) |
| `started_at` | `null` — eski dosyada yok, uydurulmaz |
| `evidence_ref` | Durum dosyasının yolu |
| `message` | `phase` alanı |
| `progress` | `null` |

Bozuk JSON, dict olmayan içerik veya doğrulanamayan kayıtlar okuma sonucunu
durdurmaz; dosya adıyla `issues` listesine düşer ve diğer kayıtlar okunmaya
devam eder.

## Sahiplik çakışması

`detect_ownership_conflicts`: aynı `job_id` için birden fazla farklı `owner`
görülüyorsa çakışmadır. v1'de çakışma yalnız **raporlanır**; çözümleme
(kilitleme, öncelik) bilinçli olarak kapsam dışıdır.

## Sürüm kuralı

Alan ekleme/çıkarma veya anlam değişikliği `version` artışı ve bu belgeye yeni
bölüm gerektirir. ~~`version` alanı v1 olmayan kayıtlar v1 okuyucusunda eski
format sayılır ve normalize edilir.~~ **Güncelleme (reader-v2):** sürüm
dağıtımı artık [`agent-status-v2.md`](agent-status-v2.md) § v1 geriye
uyumluluk / Sürüm kuralı'na tabidir — versionsuz kayıtlar v1'e normalize
edilmeye devam eder, açık `version: 2` v2 kurallarına gider, bilinmeyen açık
sürümler eski format sayılmaz, fail closed reddedilir.
