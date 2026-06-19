# Evidence Continuity EC2-13 — Köprü async agent `result` fazı (onaylı karar)

> **Durum:** `[decision-approved]` — implementasyon PR bekliyor.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 4 (EC2-13); `PHASE_RESULT` read-only keşif; `kando_bridge` POST /task + `agent_runner` async completion; EC2-03/04 `after`-only mirror (2026-06-19).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md), [`evidence-continuity-ec2-04-decision.md`](./evidence-continuity-ec2-04-decision.md).

**Karar:** **Seçenek 1** — köprü **async agent** tamamlanması için `phase: result` journal satırı; H5 hook `agent_runner.start_agent_job` worker sonunda (outbox snapshot kopyası sonrası); aynı enum üçlüsü (`kando_bridge` / `bridge_outbox` / `bridge.task.post`); `payload_summary` demo-safe (`title_preview`, `route`, `job_id`); guard/policy **result fazı v1'de yok** (senkron terminal olaylar — EC2-04 `after` yeterli).

**Bağımlılık:** **EC2-03** merge edildi (`b1c48aa`, PR #265); **EC2-04** merge edildi (`9475a0f`, PR #268). EC2-13 için sert önkoşul **EC2-03 karşılandı**; EC2-04 pattern referansı; EC2-14 frozenset güncellemesi regresyonsuz kalmalı.

---

## Keşif özeti

### `result` fazı bugün ne durumda?

| Bulgu | Kanıt |
|-------|--------|
| `PHASE_RESULT = "result"` tanımlı | `src/core/evidence_continuity.py` — `PHASES` frozenset içinde |
| **Hiçbir runtime mirror kullanmıyor** | Tüm builder'lar (`mirror_post_task_outbox_*`, `mirror_guard_*`, `mirror_policy_*`) yalnızca `PHASE_AFTER` |
| v1 şema faz enum'unda yer alıyor | [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) § «Faz kuralları» — panel/engine için `after` yeterli; köprü/guard `result` v2 |
| EC2-03/04 bilinçli erteleme | BM7 / GP9 — `after` = HTTP yanıt anı; async tamamlanma EC2-13 |

### Köprü agent «complete» ne zaman olur?

```
POST /task (agent route)
  → lumos_gate_execute → start_agent_job (async thread)
  → EC2-03 H3: persist_post_task_outbox_snapshots + mirror (phase: after, outcome pending/ok)
  → HTTP yanıt döner (last_res.outcome: "pending", task_status: "agent_running")

[Arka plan — agent_runner worker]
  → run_agent_pipeline (repo_scan … final_report)
  → agent_status_{job_id}.json + agent_last.json
  → _copy_cursor_bridge_snapshots_to_outbox  ← H5 hook noktası
```

| Yol | Tamamlanma | EC2-13 `result` gerekir mi? |
|-----|------------|----------------------------|
| Async agent (`start_agent_job`) | Worker thread `done` / `error` | **Evet** — `after` pending; gerçek sonuç async |
| Sync gate (`persist_last_result_from_out`) | Aynı HTTP isteği | **Hayır** — EC2-03 `after` yeterli |
| `POST /chat` task routing | `persist_last_result_from_out` | **Hayır** — v1 kapsam dışı (EC2-03 BM8) |
| Pending approval → approve → agent | Onay sonrası async agent | **Evet** — approve sonrası agent job |

**Hook noktası (firm):** `src/kando/agent_runner.py` → `start_agent_job` worker, `_copy_cursor_bridge_snapshots_to_outbox(rr, outbox_dir)` **hemen sonrası** (başarı ve hata yollarında outbox/agent_last yazımından sonra).

### Guard «result» lifecycle var mı?

| Bulgu | Sonuç |
|-------|--------|
| Guard deny / policy block **senkron terminal** | EC2-04 H4a/H4b — olay anında `phase: after`, `outcome: error` |
| Async tamamlanma yok | `record_guard_event` / `log_policy_blocked` tek atımlık |
| Backlog «guard hatları» ifadesi | Ayrı lifecycle ihtiyacı **köprü async** ekseninde; guard için `result` fazı **anlamsız** |

**v1 karar:** Guard/policy tarafında **ayrı `result` journal satırı yazılmaz**; EC2-04 `after` terminal kayıt olarak kalır.

### EC2-03 / EC2-04 bağımlılık doğrulaması

| Kontrol | Kanıt |
|---------|--------|
| EC2-03 merge | `b1c48aa` — PR #265; H3 `mirror_post_task_outbox_to_evidence_journal` |
| EC2-04 merge | `9475a0f` — PR #268; H4 guard/policy `after` mirror |
| `PHASE_RESULT` validator'da | `PHASES` frozenset — EC2-14 testleri geçer; kullanım yok |
| Outbox overwrite | Değişmez — `result` journal append-only ek satır |

---

## Karar özeti

**Onaylı karar (firm):** Async köprü agent işi tamamlandığında (veya worker hata ile bittiğinde), outbox `last_result.json` / `last_execution.json` güncellendikten sonra `.lumos/logs/evidence_continuity.jsonl` dosyasına **tek append-only `phase: result` satırı** bırakılır. EC2-03 `after` satırı korunur (HTTP kabul anı). Guard/policy EC2-04 `after` satırları değişmez.

| # | Kural | Durum |
|---|--------|--------|
| BR1 | Yalnızca **async agent** tamamlanması — sync gate / direct_patch aynı istekte `result` yok | `decision-approved` |
| BR2 | H5 hook — `agent_runner` worker, outbox snapshot kopyası sonrası | `decision-approved` |
| BR3 | Enum değişmez — `source: kando_bridge`, `store: bridge_outbox`, `operation: bridge.task.post` | `decision-approved` |
| BR4 | `phase: result` — **ilk runtime kullanım**; şema sürümü `lumos.evidence_continuity.v1` | `decision-approved` |
| BR5 | `payload_summary`: `title_preview`, `route` (`agent/async`), `job_id` (yeni izinli anahtar) | `decision-approved` |
| BR6 | `outcome`: `final_report.status == "ok"` → `ok`; aksi `error` | `decision-approved` |
| BR7 | Ham `final_report`, commit hash, tam path journal'a **girmez** | `decision-approved` |
| BR8 | Guard/policy **result fazı v1'de yok** — EC2-04 `after` terminal | `decision-approved` |
| BR9 | Journal hatası agent worker'ı **kırmaz** (best-effort, H0 ilkesi) | `decision-approved` |
| BR10 | Yeni HTTP endpoint v1'de **yok** | `decision-approved` |
| BR11 | `correlation_id` v1'de `after` ile **bağımsız UUID**; `job_id` ile bağlantı — EC2-08 UI | `decision-approved` |

---

## Seçilen yol ve neden

### Seçilen: bridge-only async `result` + H5 agent_runner hook

```
[POST /task agent — EC2-03 after]
       │
       ▼
  start_agent_job (async)
       │
       ▼
  [worker: pipeline → outbox copy]
       │
       ▼
  H5: mirror_bridge_agent_result_to_evidence_journal(...)
       │
       ▼
  append_evidence_event (H0) ──► evidence_continuity.jsonl (phase: result)
```

**Neden bu yol:**

1. **Dar runtime kapsam** — tek choke-point (`agent_runner` worker); köprü `server.py` genişlemesi yok.
2. **EC2-03 ayrımı korunur** — `after` = HTTP + pending snapshot; `result` = gerçek yürütme sonucu.
3. **Enum genişlemesi yok** — aynı operation, farklı phase; EC2-14 frozenset minimal güncelleme (`job_id` payload anahtarı).
4. **Guard hariç tutma gerekçeli** — senkron deny/block zaten terminal; sahte `result` gürültü üretir.
5. **Public repo güvenli** — demo-safe payload; yeni endpoint yok.

---

## Reddedilen alternatifler

| Alternatif | Red gerekçesi |
|------------|---------------|
| **Guard/policy `result` mirror** | Senkron terminal; EC2-04 `after` yeterli; async lifecycle yok |
| **Yeni operation `bridge.task.result`** | Gereksiz enum; aynı operation + `phase: result` v1 şema niyeti |
| **H3 `server.py` finally'de result** | Async tamamlanma HTTP isteği dışında; yanlış hook |
| **`correlation_id` propagate zorunlu v1** | Outbox/agent_status'ta persist yok; scope genişler — EC2-08 |
| **`lumos_http_response` / final_report journal'da** | Demo-safe ihlali |
| **Sync POST /task için de `result`** | `after` zaten tam sonuç; duplicate satır |
| **`POST /chat` task routing result** | EC2-03 kapsam dışı; ayrı backlog |
| **Şema sürümü v2** | Enum/payload genişlemesi yeterli |
| **`POST /evidence/bridge-result` endpoint** | EC2-02/03 pattern reddi |

---

## Minimum v1 tasarım

### Hook katmanı

| Katman | Rol |
|--------|-----|
| **H0** | `append_evidence_event` — mevcut |
| **H3** | EC2-03 — `after` (değişmez) |
| **H5 (yeni)** | `mirror_bridge_agent_result_to_evidence_journal(...)` — agent worker sonu |

### Enum / payload

| Sabit / anahtar | Değer / kural |
|-----------------|---------------|
| `source` | `kando_bridge` (mevcut) |
| `store` | `bridge_outbox` (mevcut) |
| `operation` | `bridge.task.post` (mevcut) |
| `phase` | **`result`** |
| `PAYLOAD_SUMMARY_ALLOWED_KEYS` | + `job_id` (≤32 char, hex id) |

### Journal kaydı — alan kuralları

| Alan | v1 değeri |
|------|-----------|
| `schema` | `lumos.evidence_continuity.v1` |
| `phase` | **`result`** |
| `outcome` | `ok` if `final_report.status == "ok"`; else `error` |
| `correlation_id` | Yeni UUID v4 / tamamlanma olayı |
| `mutation` | **omit** |
| `entity_ref` | **omit** v1 |
| `error` | `outcome: error` iken kısa `code`/`message` (ör. `agent_failed`, `verify_failed`) |
| `payload_summary` | `title_preview` ← `final_report.task` veya goal; `route`: `"agent/async"`; `job_id` |

**Örnek journal satırı (başarılı agent):**

```json
{
  "schema": "lumos.evidence_continuity.v1",
  "ts": "2026-06-19T22:00:00.000Z",
  "correlation_id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
  "source": "kando_bridge",
  "store": "bridge_outbox",
  "operation": "bridge.task.post",
  "phase": "result",
  "outcome": "ok",
  "payload_summary": {
    "title_preview": "README düzelt",
    "route": "agent/async",
    "job_id": "a1b2c3d4e5f67890"
  }
}
```

**Örnek journal satırı (başarısız agent):**

```json
{
  "schema": "lumos.evidence_continuity.v1",
  "ts": "2026-06-19T22:05:00.000Z",
  "correlation_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
  "source": "kando_bridge",
  "store": "bridge_outbox",
  "operation": "bridge.task.post",
  "phase": "result",
  "outcome": "error",
  "error": {
    "code": "verify_failed",
    "message": "agent pipeline failed"
  },
  "payload_summary": {
    "title_preview": "risky change",
    "route": "agent/async",
    "job_id": "b2c3d4e5f6789012"
  }
}
```

### Outcome kuralları

| Koşul | `outcome` | `error.code` (örnek) |
|-------|-----------|----------------------|
| `final_report.status == "ok"` | `ok` | omit |
| `final_report.status == "partial"` | `error` | `agent_partial` |
| `final_report.status == "failed"` | `error` | ilk `errors[]` veya `agent_failed` |
| Worker exception | `error` | `agent_worker_error` |

### Best-effort

EC2-03 BM9 ile aynı: journal hatası agent worker / outbox yazımını **kırmamalı**.

---

## Değişecek dosyalar (gelecek implementasyon)

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | `job_id` payload anahtarı; `mirror_bridge_agent_result_record`, `mirror_bridge_agent_result_to_evidence_journal` |
| `src/kando/agent_runner.py` | H5: worker sonunda journal mirror (success + failure) |
| `tests/test_bridge_agent_result_evidence_ec2_13.py` | **Yeni** — R1–R10 |
| `tests/test_evidence_continuity.py` | `PHASE_RESULT` + `job_id` validator testleri |

**Bilerek dokunulmayacak (v1):**

- `packages/kando_bridge/src/kando_bridge/server.py` — H3 `after` değişmez
- `src/core/guard_audit.py`, `src/policy/action_policy.py` — guard result yok
- Outbox dosya adları / overwrite semantiği
- Correlation UI (EC2-08)
- `POST /chat` handler

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| R1 | Mock agent pipeline `status: ok` + mirror | 1 journal satırı; `phase: result`, `outcome: ok` |
| R2 | Mock pipeline `status: failed` | `phase: result`, `outcome: error` |
| R3 | Worker exception path | `phase: result`, `outcome: error` |
| R4 | `payload_summary.job_id` | Present; ≤32 char |
| R5 | Ham `final_report` / commit hash | Journal'da **yok** |
| R6 | EC2-03 `after` + EC2-13 `result` aynı agent akışı simülasyonu | Journal **2 satır**; farklı phase |
| R7 | Sync POST /task (no agent job) | Yalnızca `after`; `result` **yok** |
| R8 | Her journal satırı | `validate_evidence_record(rec) == []` |
| R9 | EC2-14 / mevcut EC2-03/04 testleri | Regresyonsuz |
| R10 | Guard deny sonrası | Yalnızca EC2-04 `after`; `result` **yok** |

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| **`after`/`result` correlation kopuk** | UI zinciri görünmez | `job_id` payload; EC2-08 |
| **Duplicate result** | Worker retry / double mirror | Tek worker exit; idempotent test |
| **`LUMOS_BASE_DIR` drift** | Journal outbox dışında | `lumos_base_dir()` H5'te |
| **Enum/payload EC2-14** | CI reddi | frozenset + validator test |
| **Guard backlog metni «guard hatları»** | Beklenti uyumsuzluğu | Bu belgede guard result **bilinçli dışı** |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **Guard/policy `result` faz** | Senkron terminal; EC2-04 yeterli |
| **`correlation_id` propagate `after`→`result`** | EC2-08 |
| **Sync POST /task `result`** | EC2-03 `after` yeterli |
| **`POST /chat` result mirror** | EC2-03 kapsam dışı |
| **Pending approval `result`** | Onay sonrası agent job H5 kapsar; ayrı approval result yok |
| **Correlation UI** | EC2-08 |
| **Şema sürümü v2** | Payload anahtar genişlemesi yeterli |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md) | H3 `after`; BM7 result erteleme |
| [`evidence-continuity-ec2-04-decision.md`](./evidence-continuity-ec2-04-decision.md) | Guard `after` terminal; GP9 |
| EC2-03 merge `b1c48aa` / PR #265 | Sert önkoşul ✓ |
| EC2-04 merge `9475a0f` / PR #268 | Pattern referansı ✓ |
| EC2-14 / PR #255 | Şema CI |
| EC2-08 | Correlation UI — `after`+`result` birleştirme |

---

## Sonraki adım

1. **Implementasyon PR:** `feat/ec2-13-bridge-agent-result-phase` — H5 + testler.
2. **Backlog senkron:** EC2-13 → `[implemented]` merge sonrası.
3. **Phase 4 kalan:** EC2-08 (correlation UI).

---

**İndeks notu:** EC2-13 ayrı OD kaydı açmaz; v2 backlog + bu belge canonical. `docs/decision-log.md` DL-A06 satırı ile senkron.

---

Son güncelleme: 2026-06-19 (keşif + karar onayı)
