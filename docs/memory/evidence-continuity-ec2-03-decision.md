# Evidence Continuity EC2-03 — Köprü POST /task journal mirror (onaylı karar)

> **Durum:** `[implemented]` — merge PR #265 (`b1c48aa`); H3 köprü outbox journal mirror uygulandı.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 4 (EC2-03); v1 bilinçli boşluk (köprü outbox); `kando_bridge.server` `POST /task` + `persist_post_task_outbox_snapshots` read-only keşif (2026-06-19; subagent 4893ffcc).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md), [`evidence-continuity-ec2-12-decision.md`](./evidence-continuity-ec2-12-decision.md).

**Karar:** **Seçenek 1** — köprü `POST /task` outbox overwrite modeli **değişmez**; outbox persist sonrası journal'a **append-only tek `after` satırı**; `lumos.evidence_continuity.v1` **enum genişlemesi** (`kando_bridge` / `bridge_outbox` / `bridge.task.post`); `payload_summary` yalnızca demo-safe alanlar (`title_preview`, `route`).

**Bağımlılık:** **EC2-01** merge edildi (`5073780`, PR #256); **EC2-02** merge edildi (`bc6e4e0`, PR #258); **EC2-12** merge edildi (`aa2a6ff`, PR #261). EC2-03 için sert önkoşul **EC2-01/02 karşılandı**; EC2-12 hard blocker değil.

---

## Karar özeti

**Onaylı karar (firm):** Her köprü `POST /task` isteği, mevcut outbox snapshot yazımından (`last_execution.json`, `last_result.json` — overwrite) hemen sonra `.lumos/logs/evidence_continuity.jsonl` dosyasına **tek append-only journal satırı** bırakır. Outbox dosyaları, şemaları ve `GET /last-result` semantiği v1'de **değişmez**. Journal satırı `phase: after` only; `result` fazı **EC2-13** kapsamındadır.

| # | Kural | Durum |
|---|--------|--------|
| BM1 | Outbox overwrite modeli korunur — `persist_post_task_outbox_snapshots` davranışı değişmez | `decision-approved` |
| BM2 | Journal append — istek başına tek `after` satırı (H3 hook, outbox persist sonrası) | `decision-approved` |
| BM3 | Enum genişlemesi: `source: kando_bridge`, `store: bridge_outbox`, `operation: bridge.task.post` | `decision-approved` |
| BM4 | Şema sürümü `lumos.evidence_continuity.v1` kalır — **v2 şema yok**; frozenset validator güncellemesi yeterli | `decision-approved` |
| BM5 | `payload_summary` yalnızca `title_preview` + `route` (mevcut izinli anahtarlar) | `decision-approved` |
| BM6 | `lumos_http_response`, gate gövdesi, token, ham chat journal'a **girmez** | `decision-approved` |
| BM7 | `phase: result` v1'de **yok** — EC2-13 ayrı madde | `decision-approved` |
| BM8 | `POST /chat` task routing v1'de **kapsam dışı** | `decision-approved` |
| BM9 | Journal hatası `POST /task` HTTP yanıtını **kırmaz** (best-effort, H0 ilkesi) | `decision-approved` |
| BM10 | EC2-01/02 merge **önkoşul** karşılandı | `verified` — PR #256, #258 |

---

## Problem / mevcut boşluk

Evidence Continuity v1 yalnızca **panel sunucu (H1)** ve **TaskEngine (H2)** yazım kapılarında journal bırakır. Köprü `POST /task` hattı (`packages/kando_bridge/src/kando_bridge/server.py`) farklı bir yürütme girişidir (ADR-008: `POST /task` ≠ `POST /tasks`).

### Bugün `POST /task` nereye yazıyor?

```
do_POST(/task)
  → _post_task_envelope_meta + _post_task_outbox_snapshot
  → gate (_complete_through_gate → _send_lumos_pipeline_out)
  → _send_json (yanıt + snapshot)
  → finally: persist_post_task_outbox_snapshots
```

| Hedef | İçerik | Mekanizma |
|-------|--------|-----------|
| `.lumos/outbox/last_execution.json` | `lumos.bridge.post_task.last_execution.v1` | `persist_post_task_outbox_snapshots` |
| `.lumos/outbox/last_result.json` | `lumos.bridge.post_task.last_result.v1` | aynı fonksiyon |

**Overwrite modeli:** Her `POST /task` önceki outbox dosyalarını **üzerine yazar** — append-only değil. Panel/CLI `GET /last-result` yalnızca **son** isteği görür.

**Journal:** Köprü paketinde `evidence_continuity` / `append_evidence_event` **kullanılmıyor**. `.lumos/logs/evidence_continuity.jsonl` köprü isteklerinden **satır üretmez**.

**Yan kanallar (journal değil):**

| Kanal | Semantik |
|-------|----------|
| `logs/bridge.log` + stderr | `post_task_routed` operasyonel log |
| `append_audit_log` (gate) | Gate audit — farklı kanal, farklı semantik |
| Panel `bridgeLast` meta overlay | İstemci-only; EC2-02 bilinçli ayrım |

**Kullanıcıya görünür semptom:** Panel chat veya Görevler'den köprüye gönderilen görev yürütmesi outbox'ta sonuç bırakır; evidence continuity journal'da köprü hattına ait kayıt **yoktur**. Kopma/devam veya «son kanıt» (EC2-08) köprü ekseninde boş kalır.

**v1 bilinçli boşluk (kaynak):** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) — köprü outbox v1 kapsam dışı; EC2-03 bu boşluğu kapatır.

---

## EC2-01 / EC2-02 / EC2-12 bağımlılık doğrulaması

| Kontrol | Kanıt |
|---------|--------|
| **EC2-01** merge | `5073780` — PR #256; chat create → `POST /tasks` + H1 journal |
| **EC2-02** merge | `bc6e4e0` — PR #258; pending-op kuyruğu + flush; panel REST journal |
| **EC2-12** merge | `aa2a6ff` — PR #261; DR1–DR7 disconnect/resume harness |
| Sert sıra | Backlog: EC2-03 Phase 4; EC2-01/02 tamamlanmış olmalı — [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) § bağımlılık grafi |
| EC2-12 ilişkisi | Harness köprü journal'ı **doğrulamaz** (henüz yok); EC2-03 sonrası EC2-12 genişletmesi opsiyonel |

**Sonuç:** EC2-01/02 önkoşulları **karşılandı**; EC2-03 implementasyon PR'ı açılabilir. EC2-12 merge edilmiş olması ek güvence sağlar; hard blocker değildir.

**EC2-03 sonrası açılanlar:**

```
EC2-03 (köprü mirror) ──► EC2-13 (result faz — köprü)
EC2-03 + EC2-04 ──► EC2-08 (correlation UI)
EC2-01..04 ──► EC2-12 tam kapsam değeri (köprü journal senaryoları)
```

---

## Seçilen yol ve neden bu yol

### Seçilen: outbox değişmeden + append journal (enum genişlemesi, demo-safe payload_summary)

```
[POST /task — her durum: 2xx/4xx/5xx, accepted/pending/hata]
       │
       ▼
  persist_post_task_outbox_snapshots  ──► last_execution.json / last_result.json (overwrite — değişmez)
       │
       ▼
  H3: mirror_post_task_outbox_to_evidence_journal(...)
       │
       ▼
  append_evidence_event (H0) ──► evidence_continuity.jsonl (append-only, tek after satırı)
```

**Neden bu yol:**

1. **Minimum köprü yüzeyi** — outbox overwrite ve `GET /last-result` semantiği bozulmaz; mevcut panel/CLI tüketicileri etkilenmez.
2. **Truth kuralı** — journal yalnızca sunucu/köprü sürecinden üretilir; istemci journal'a yazmaz (EC2-02 ile hizalı).
3. **Şema sürümü değil, enum genişlemesi** — `lumos.evidence_continuity.v1` korunur; EC2-14 CI kapısı frozenset güncellemesi ile yeşil kalır.
4. **Demo-safe sınır** — yalnızca `title_preview` (≤40 char) ve `route`; `lumos_http_response` / gate gövdesi journal dışı.
5. **Tek choke-point** — `persist_post_task_outbox_snapshots` sonrası; snapshot normalize edilmiş; tüm exit path'leri (`finally`, ~2520–2529) kapsanır.
6. **Public repo güvenli** — yeni HTTP endpoint yok; hassas payload mirror yok.
7. **EC2-13 ayrımı** — `after` = HTTP yanıt + outbox snapshot anı; async agent `result` ayrı lifecycle.

---

## Reddedilen alternatifler

| Alternatif | Red gerekçesi |
|------------|---------------|
| **`source: panel_tasks_server` / `panel.task.*` ile yazmak** | Truth kuralı ihlali; köprü yürütme ≠ panel CRUD |
| **`before` + `after` iki satır** | Köprüde disk mutasyon choke-point yok; yapay `before` |
| **`phase: result` EC2-03'te** | EC2-13 scope; async agent tamamlanması ayrı lifecycle |
| **`lumos_http_response` journal'a kopyalamak** | Demo-safe / public boundary ihlali; PII/gate gövdesi riski |
| **Outbox'ı append-only yapmak** | v1 bilinçli dışı; `GET /last-result` semantiği değişir |
| **`POST /chat` task routing aynı PR'da mirror** | Farklı persist (`persist_last_result_from_out`); kapsam genişlemesi |
| **İstemciden doğrudan journal append** | EC2-02 reddi; truth kuralı |
| **`POST /evidence/bridge` yeni endpoint** | EC2-02 pattern reddi; public yüzey genişler |
| **Şema sürümü `lumos.evidence_continuity.v2`** | Backlog «v1 şema» hedefi; enum genişlemesi yeterli |
| **İstek `source` (`panel_chat` vb.) journal alanı** | `payload_summary` izinli anahtarlarda yok; EC2-08/13 ayrı karar |

---

## Minimum v1 tasarım

### Hook katmanı

| Katman | Rol |
|--------|-----|
| **H0** | `append_evidence_event` — mevcut (`src/core/evidence_continuity.py`) |
| **H3 (yeni)** | `mirror_post_task_outbox_to_evidence_journal(...)` — köprü choke-point |

**Hook noktası:** `persist_post_task_outbox_snapshots` **başarılı outbox yazımından hemen sonra** — tercihen fonksiyon sonunda veya `do_POST` `finally` bloğunda outbox çağrısının ardından (`server.py`, ~2520–2529).

**Neden outbox sonrası / `finally`?**

- Yanıt gönderildikten sonra snapshot kesin (`_send_json`, ~1497–1500)
- Hata/400/500/pending dahil **her** `POST /task` outbox alır (`snapshot_incomplete` dahil)
- Panel H1'deki `before→disk→after` lifecycle köprüde yok; outbox zaten **post-response** semantiği

### Enum sabitleri (`evidence_continuity.py`)

| Sabit | Değer |
|-------|-------|
| `SOURCE_KANDO_BRIDGE` | `"kando_bridge"` |
| `STORE_BRIDGE_OUTBOX` | `"bridge_outbox"` |
| `OPERATION_BRIDGE_TASK_POST` | `"bridge.task.post"` |

`SOURCES`, `STORES`, `OPERATIONS` frozenset'lerine eklenir. `PHASE_RESULT` tanımlı kalır; EC2-03 v1'de **kullanılmaz**.

### Journal kaydı — alan kuralları

| Alan | v1 değeri | Not |
|------|-----------|-----|
| `schema` | `lumos.evidence_continuity.v1` | Değişmez |
| `phase` | **`after` only** | Tek satır / istek |
| `outcome` | `ok` if `200 ≤ http_status < 400` ve `accepted !== false`; aksi `error` | Outbox `last_res` alanlarından türet |
| `correlation_id` | Yeni UUID v4 / istek | `generate_correlation_id()` |
| `mutation` | **omit** | Bridge task store mutasyonu değil |
| `entity_ref` | **omit** v1 | `tsk_*` / engine id yok |
| `error` | `outcome: error` iken kısa `code`/`message` (secret yok) | Opsiyonel |
| `payload_summary` | `title_preview` ← `goal_preview`; `route` ← `POST /task/{mode}` veya `POST /task` | ≤80 char route; `sanitize_payload_summary` |

**Örnek journal satırı (başarılı agent):**

```json
{
  "schema": "lumos.evidence_continuity.v1",
  "ts": "2026-06-19T18:00:00.000Z",
  "correlation_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "source": "kando_bridge",
  "store": "bridge_outbox",
  "operation": "bridge.task.post",
  "phase": "after",
  "outcome": "ok",
  "payload_summary": {
    "title_preview": "README düzelt",
    "route": "POST /task/agent"
  }
}
```

### Outcome kuralları (özet)

| Koşul | `outcome` |
|-------|-----------|
| `http_status` 200–399 ve `accepted !== false` | `ok` |
| `http_status` ≥400 veya `accepted === false` | `error` |
| `snapshot is None` (`snapshot_incomplete`) | `error` |
| Gate pending / onay bekliyor (`accepted: false`, 200) | `error` (v1 — EC2-13'te `result` ile netleşir) |

### `base_dir`

Journal: `lumos_base_dir()` — panel H1 ile hizalı. Outbox: `ROOT / ".lumos" / "outbox"`. **`LUMOS_BASE_DIR` env farklıysa** outbox ile journal farklı köke gidebilir — bilinen risk (§ Riskler).

### Best-effort

Panel H1 ile aynı ilke: journal hatası `POST /task` yanıtını **kırmamalı** (`append_evidence_event` raise etmez).

---

## Değişecek dosyalar (gelecek implementasyon — şimdi yapılmaz)

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | `SOURCE_KANDO_BRIDGE`, `STORE_BRIDGE_OUTBOX`, `OPERATION_BRIDGE_TASK_POST` + frozenset; isteğe bağlı `mirror_post_task_outbox_record(...)` builder |
| `packages/kando_bridge/src/kando_bridge/server.py` | Outbox persist sonrası H3 çağrısı; `lumos_base_dir` import |
| `tests/test_bridge_post_task_evidence_ec2_03.py` | **Yeni** — outbox + journal entegrasyon (T1–T9) |
| `tests/test_evidence_continuity.py` | Yeni enum değerleri için validator testleri |

**Bilerek dokunulmayacak (v1):**

- `panel/scripts/panel_tasks_server.py` — H1 değişmez
- `ui/src/pages/panel.astro` — client queue (EC2-02) değişmez
- Outbox dosya adları / şema (`POST_TASK_LAST_*`) — overwrite modeli
- Guard/policy (`EC2-04`)
- `POST /chat` handler

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| T1 | İzole `tmp_path`: `LUMOS_BASE_DIR=tmp_path`, mock outbox paths | `persist_post_task_outbox_snapshots` + mirror → 1 journal satırı |
| T2 | Başarılı agent `POST /task` (`accepted: true`, 200) | `phase: after`, `outcome: ok`, `source: kando_bridge`, `store: bridge_outbox`, `operation: bridge.task.post` |
| T3 | `accepted: false` / 4xx | `outcome: error`; kısa `error.code` (secret yok) |
| T4 | `snapshot is None` (no JSON response) | Journal satırı yine var; `outcome: error` |
| T5 | İki ardışık `POST /task` | Outbox 1 dosya (overwrite); journal **2 satır** (append) |
| T6 | `goal` içinde uzun metin | `title_preview` ≤40 char; ham metin journal'da yok |
| T7 | `lumos_gate` büyük gövde outbox'ta | Journal'da `lumos_http_response` **yok** |
| T8 | Her journal satırı | `validate_evidence_record(rec) == []` |
| T9 | EC2-14 / mevcut evidence testleri | Regresyonsuz; frozenset genişlemesi CI yeşil |

**Doğrulama kanalları:** pytest + `evidence_continuity_path(tmp_path)` okuma; mevcut `tests/test_bridge_post_task_source.py` outbox testleri korunur.

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| **Outbox overwrite bozulması** | `GET /last-result` / panel bridge kartı kırılır | Outbox koduna dokunmadan yalnızca journal append |
| **`LUMOS_BASE_DIR` ≠ `ROOT/.lumos`** | Outbox bir yerde, journal başka yerde | Mirror'da `lumos_base_dir()`; test + doc env hizası |
| **`correlation_id` kopukluğu** | Panel `tsk_*` ↔ köprü ↔ gate zinciri UI'da görünmez | Bilinçli v1; EC2-08 correlation UI |
| **Duplicate `POST /task`** | Journal'da çok satır | Append-only audit için kabul; outbox son istek |
| **Enum genişlemesi vs EC2-14** | CI validator reddi | frozenset + `test_evidence_continuity` güncelle |
| **Public repo sınırı** | Hassas payload journal'da | Yalnızca `title_preview` + `route` |
| **ThreadingHTTPServer** | Paralel POST → journal sırası | Append JSONL; correlation istek başına ayrı UUID |
| **`POST /chat` task yolu journal dışı** | Continuity boşluğu devam | EC2-03 kapsamı yalnız `POST /task`; ayrı backlog |
| **Pending/onay `accepted: false`** | v1'de `outcome: error` | EC2-13 `result` fazında netleşir |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **`phase: result` / async agent tamamlanması** | EC2-13 — köprü/guard ayrı lifecycle |
| **`POST /chat` task routing mirror** | Farklı persist yolu; kapsam genişlemesi |
| **`lumos_http_response` journal mirror** | Demo-safe ihlali; public boundary |
| **Outbox append-only** | v1 bilinçli dışı; overwrite semantiği korunur |
| **İstek `source` (`panel_chat` vb.) journal alanı** | `payload_summary` anahtarı yok; EC2-08/13 |
| **`entity_ref` / `tsk_*` köprü journal'da** | Köprü yürütme store mutasyonu değil; EC2-13/08 |
| **Guard/policy normalize** | EC2-04 ayrı madde |
| **Correlation UI** | EC2-08 — yeterli journal kaynağı gerekir |
| **Legacy panel `app.js`** | Astro birincil (OD-043) |
| **Şema sürümü v2** | Enum genişlemesi yeterli |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) | Köprü v1 dışı idi; H0/H1/H2 |
| [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) | EC2-03 Phase 4; P1 |
| [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md) | Client queue; truth kuralı pattern |
| [`evidence-continuity-ec2-12-decision.md`](./evidence-continuity-ec2-12-decision.md) | Disconnect harness; köprü journal sonrası genişletme |
| EC2-01 merge `5073780` / PR #256 | Chat create persist |
| EC2-02 merge `bc6e4e0` / PR #258 | Client queue |
| EC2-14 / PR #255 | Şema CI — enum genişlemesi regresyonsuz kalmalı |
| [ADR-008](../decisions/ADR-008-agent-network-boundary.md) | `POST /task` ≠ `POST /tasks` |


---

## Uygulama

**Merge:** PR #265 (`b1c48aa` — `feat/ec2-03-bridge-journal-mirror`).

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | `SOURCE_KANDO_BRIDGE`, `STORE_BRIDGE_OUTBOX`, `OPERATION_BRIDGE_TASK_POST`; `mirror_post_task_outbox_to_evidence_journal` |
| `packages/kando_bridge/src/kando_bridge/server.py` | Outbox persist sonrası H3 mirror çağrısı |
| `tests/test_bridge_post_task_evidence_ec2_03.py` | T1–T9 köprü outbox + journal entegrasyon |
| `tests/test_evidence_continuity.py` | Yeni enum değerleri validator testleri |

Outbox overwrite semantiği ve `POST /task` yanıt yüzeyi v1'de değişmedi; journal append-only (EC2-13 `result` fazı dışı).


---

## Sonraki adım

1. **Backlog senkron:** v2 backlog EC2-03 → `[implemented]` ✓.
2. **Phase 4 kalan:** EC2-04 (guard/policy), EC2-08 (correlation UI), EC2-13 (`result` faz).

---

**İndeks notu:** EC2-03 ayrı OD kaydı açmaz; v2 backlog + bu belge canonical. `docs/decision-log.md` DL-A04 satırı ile senkron.

---

Son güncelleme: 2026-06-19 (PR #265 merge — `[implemented]`)
