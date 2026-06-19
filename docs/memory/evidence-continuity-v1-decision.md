# Evidence Continuity v1 — onaylı karar (Karar A — daraltılmış kapsam)

> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge **yalnızca karar dokümanıdır**; kod, runtime, test veya deploy değişikliği içermez.
>
> **Uygulama yok:** `append_evidence_event`, hook entegrasyonları, journal dosyası oluşturma ve doğrulama senaryoları **henüz yapılmadı**. Onaylı ilkeler kayıt altındadır; teknik uygulama ayrı iş paketidir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`docs/decisions/ADR-008-agent-network-boundary.md`](../decisions/ADR-008-agent-network-boundary.md), [`docs/PERSISTENT_WRITE_PATH_AUDIT.md`](../PERSISTENT_WRITE_PATH_AUDIT.md), [`docs/lumos-guard-sandbox-kopya-siniri.md`](../lumos-guard-sandbox-kopya-siniri.md), [`docs/memory/primary-user-surface-decision.md`](./primary-user-surface-decision.md).

**Karar:** **A** — Sunucu tarafı **panel + engine** akışları only (daraltılmış v1).

**Keşif / audit çapraz referansları:** Evidence Continuity repo keşif raporu (Haziran 2026) — üç bağımsız görev persistence hattı, ADR-008 çift depo drift, panel `_write_doc` choke-point, TaskEngine `save_task_store_json` sink; eleştirel inceleme: hook minimum müdahale, chat gap, `events[]` çift kayıt riski.

---

## Karar özeti

**Onaylı karar (firm):** Panel görev sunucusu ve TaskEngine mutasyonları için **tek append-only journal** (`.lumos/logs/evidence_continuity.jsonl`) ile işlem kanıtı bırakılır. Kapsam **yalnızca sunucu yazım kapıları**dır; chat, client, köprü outbox, guard/policy mirror ve depo birleştirme v1 **dışındadır**.

| # | Kural | Durum |
|---|--------|--------|
| EC1 | Journal = **audit/continuity birincil kaynak** (sunucu mutasyonları). | `decision-approved` |
| EC2 | `tasks.json` içindeki `events[]` = **UI/legacy projection**; v1’de kaldırılmaz, journal ile reconcile edilmez. | `decision-approved` |
| EC3 | Tek journal dosyası: `.lumos/logs/evidence_continuity.jsonl`. | `decision-approved` |
| EC4 | Kesin şema: `lumos.evidence_continuity.v1`. | `decision-approved` |
| EC5 | Minimum hook: `append_evidence_event` helper + `panel_tasks_server._write_doc()` + `save_task_store_json()`. | `decision-approved` (ilke) / `implementation-pending` (kod) |
| EC6 | Chat görevleri, görev silme UX, çift depo merge, client/bridge/guard hook’ları **v1 kapsam dışı**. | `decision-approved` |
| EC7 | Demo-safe payload — secret, ham kullanıcı metni, production URL journal’a yazılmaz. | `decision-approved` |
| EC8 | **İlke:** Kanıt kopunca aranmaz; sunucu yazım kapılarında otomatik bırakılır. | `decision-approved` |

---

## Amaç

Bağlantı kopması, tarayıcı kesintisi veya süreç yarıda kalması durumunda **sunucu tarafı görev mutasyonlarının** kaybolmaması ve hangi işlemin, hangi depoda, hangi fazda gerçekleştiğinin **append-only kanıt** ile izlenebilmesi.

Bu belge:

- Panel CRUD (`.lumos/tasks.json`) ve TaskEngine mutasyonları (`.lumos/tasks/tasks.json`) için **minimum müdahale** ile continuity journal ilkelerini tanımlar.
- ADR-008’de kayıtlı **çift görev deposu drift**’ini v1’de **birleştirmez**; journal `source` + `store` ile ayrımı korur.
- Public repo sınırına uygun **demo-safe** event şemasını sabitler.

**Uygulama notu:** İlke kararları onaylandı; helper modülü, hook entegrasyonları, şema doğrulayıcı ve doğrulama senaryoları **henüz başlamadı**.

---

## Kapsam

| Dahil | Açıklama |
|-------|----------|
| **Panel CRUD (sunucu)** | `panel/scripts/panel_tasks_server.py` — create, complete, delete, restore, PUT → `.lumos/tasks.json` |
| **TaskEngine mutasyonları (sunucu)** | `TaskStore._save()` → `save_task_store_json()` → `.lumos/tasks/tasks.json` |
| **Tek journal** | `.lumos/logs/evidence_continuity.jsonl` — workspace `logs/` omurgası altında |
| **Lifecycle fazları** | `before`, `after`, `error` (v1 sadeleştirme; `result` v2’de köprü/guard için) |
| **Şema** | `lumos.evidence_continuity.v1` — zorunlu/opsiyonel alanlar bu belgede kesin |
| **Demo-safe özet** | `payload_summary` — izinli anahtarlar; secret/PII yok |

**Firm:** v1 yalnızca **panel + engine sunucu akışları**; istemci, chat ve köprü yürütme hatları journal kapsamına girmez.

---

## Kapsam dışı (v1 bilinçli)

| Madde | Gerekçe |
|-------|---------|
| **Chat görevleri** | `applyPanelGorevKomutu()` — çoğunlukla `localStorage`; sunucu mutasyonu yok |
| **Görev silme UX** | Client-only satırlar, `id` eksikliği, chat türevli silme — ayrı iş paketi |
| **Çift depo birleştirme (store merge)** | ADR-008 drift (`.lumos/tasks.json` ≠ `.lumos/tasks/tasks.json`) — v2+ |
| **Client hook’ları** | `tasksApiPost()`, `localStorage` evidence queue — sunucu-first v1 |
| **Köprü outbox** | `persist_post_task_outbox_snapshots()`, `POST /task` — engine/panel dışı yürütme hattı |
| **Guard/policy journal mirror** | `record_guard_event()`, `log_policy_blocked()` — farklı semantik; v2 normalize |
| **Legacy panel** | `panel/js/app.js` statik panel — Astro panel birincil; legacy v2 |
| Chat geçmişi replay, DOM/Network snapshot | v2+ |
| `events[]` kaldırma veya migration | Parallel kalır; journal ayrı truth |
| Outbox `last_*.json` overwrite modelinin değiştirilmesi | v2 append-only outbox |
| `ObservationEngine` disk spill | v2 |
| Production orchestration, operasyonel backend | Public repo sınırı |

---

## Mimari özet

```
Panel form/API ──► panel_tasks_server._write_doc()
                         │
                         ├──► .lumos/tasks.json (mevcut)
                         └──► evidence_continuity.jsonl (onaylı; henüz yok)

CLI / TaskEngine ──► TaskStore._save() ──► save_task_store_json()
                         │
                         ├──► .lumos/tasks/tasks.json (mevcut)
                         └──► evidence_continuity.jsonl (onaylı; henüz yok)
```

**Mevcut parçalı kanıt (v1’de korunur, kaldırılmaz):**

- `.lumos/tasks.json` gömülü `events[]` (panel UI projection)
- `.lumos/trash/{id}.json` (panel delete)
- `.lumos/logs/log.txt` (policy vb.)
- Köprü outbox `last_*.json` (overwrite)
- Repo kökü `logs/lumos_evolution.jsonl` (ayrı domain — evolution, continuity değil)

**Audit bulgusu (ADR-008 / keşif raporu):** Görev yaşam döngüsü en az üç bağımsız hatta ayrılmıştır; v1 journal yalnızca panel sunucu + TaskEngine sink’lerini kapsar, hatları birleştirmez.

---

## Truth kuralı

| Katman | Rol | v1 davranışı |
|--------|-----|--------------|
| **`.lumos/logs/evidence_continuity.jsonl`** | Audit / continuity **birincil kaynak** (sunucu mutasyonları) | Onaylı hedef; henüz oluşturulmadı |
| **`tasks.json` → `events[]`** | UI / legacy **projection** | Parallel kalır; journal ile reconcile **edilmez** |
| **Trash, outbox, log.txt** | Mevcut yan kanıt | Korunur; v1’de journal’a taşınmaz |

**Firm:** Çakışma durumunda continuity teşhisi için journal esas alınır; `events[]` yalnızca panel gösterimi içindir.

---

## Tek journal dosyası

| Özellik | Değer |
|---------|--------|
| **Path** | `.lumos/logs/evidence_continuity.jsonl` |
| **Yazım deseni** | `append_jsonl_with_rotation()` ile hizalı (evolution/decision logları gibi) — `implementation-pending` |
| **Rotation** | Mevcut default (1 MB × 3); v1 yeterli — evidence-specific politika v2 |
| **Encoding** | UTF-8; satır başına bir JSON object |
| **Sandbox** | `logs/` core state; sandbox write kuralları geçerli ([`lumos-guard-sandbox-kopya-siniri.md`](../lumos-guard-sandbox-kopya-siniri.md)) |

---

## Minimum hook listesi

| # | Hook | Konum | Kapsadığı işlemler | Durum |
|---|------|-------|-------------------|--------|
| **H0** | `append_evidence_event(base_dir, record)` | Yeni helper (onay sonrası dosya) | Tek yazım deseni, şema doğrulama, rotation | `implementation-pending` |
| **H1** | `_write_doc(doc)` | `panel/scripts/panel_tasks_server.py` | Panel create / complete / delete / restore / PUT | `implementation-pending` |
| **H2** | `save_task_store_json(...)` | `src/core/workspace_contract.py` (TaskStore._save üzerinden) | Engine create / update / archive / delete | `implementation-pending` |

**Bilerek çıkarılan (v1):**

- `persist_post_task_outbox_snapshots` — köprü hattı
- `record_guard_event` / `log_policy_blocked` — farklı semantik
- `tasksApiPost` — client
- `applyPanelGorevKomutu` — chat, kapsam dışı

**Hook davranışı (onaylı ilke, uygulama bekliyor):**

1. `correlation_id` = request / `_save` girişinde UUID v4
2. `before` → disk yazımı → `after`; exception → `error`
3. Journal append hatası ana mutasyonu **kırmamalı** (best-effort `error` satırı); ana işlem öncelikli

**Audit referansı:** Keşif raporu `_write_doc()` ve `save_task_store_json()`’ı panel ve engine için **tek choke-point** olarak doğrulamıştır; v1 minimum müdahale bu iki kapı + bir helper ile sınırlıdır.

---

## Kesin event şeması — `lumos.evidence_continuity.v1`

### Zorunlu alanlar

| Alan | Tip | Kurallar |
|------|-----|----------|
| `schema` | string | Sabit: `"lumos.evidence_continuity.v1"` |
| `ts` | string | ISO8601 UTC, ms precision |
| `correlation_id` | string | UUID v4; tek işlem zinciri |
| `source` | enum | `"panel_tasks_server"` \| `"task_engine"` |
| `store` | enum | `"panel_tasks"` \| `"task_engine"` |
| `operation` | enum | Aşağıdaki tablo |
| `phase` | enum | `"before"` \| `"after"` \| `"result"` \| `"error"` |
| `outcome` | enum | `"ok"` \| `"error"` |

### Opsiyonel alanlar

| Alan | Tip | Kurallar |
|------|-----|----------|
| `entity_ref` | object | `{"kind":"task","id":"<string>"}` — panel: `tsk_*`, engine: int string |
| `mutation` | string | `create` \| `complete` \| `delete` \| `restore` \| `update` \| `archive` |
| `payload_summary` | object | Demo-safe; toplam ~200 char; yalnızca izinli anahtarlar |
| `error` | object | `{"code":"<string>","message":"<string>"}` — secret yok |

### `operation` enum (v1)

| `operation` | `source` | `store` | `mutation` |
|-------------|----------|---------|------------|
| `panel.task.create` | `panel_tasks_server` | `panel_tasks` | `create` |
| `panel.task.complete` | `panel_tasks_server` | `panel_tasks` | `complete` |
| `panel.task.delete` | `panel_tasks_server` | `panel_tasks` | `delete` |
| `panel.task.restore` | `panel_tasks_server` | `panel_tasks` | `restore` |
| `panel.task.put` | `panel_tasks_server` | `panel_tasks` | `update` |
| `engine.task.mutation` | `task_engine` | `task_engine` | create / update / archive / delete |

### `payload_summary` izinli anahtarlar

| Anahtar | Kullanım |
|---------|----------|
| `title_preview` | İlk 40 char, newline strip |
| `route` | HTTP route: `POST /tasks`, `POST /tasks/delete`, vb. |
| `task_count` | Doküman görev sayısı (`after` faz) |
| `events_appended` | Panel: bu yazımda eklenen `events[]` sayısı (0–1) |
| `trash_written` | Panel delete: `true` / `false` |
| `step_count` | Engine: görev adım sayısı |

**Yasak:** ham `goal`, `message`, token, credential, production URL, email, tam task body.

### Faz kuralları

| Faz | Ne zaman |
|-----|----------|
| `before` | Disk yazımından hemen önce |
| `after` | Disk yazımı başarılı |
| `result` | İş mantığı tamamlandı — v1 panel/engine için `after` yeterli; ayrı `result` v2 (köprü/guard) |
| `error` | Exception veya yazım reddi |

**v1 sadeleştirme:** Panel ve engine için yalnızca `before` + `after` (veya hata durumunda `error`).

### JSONL örnekleri

**Panel create — before/after:**

```json
{"schema":"lumos.evidence_continuity.v1","ts":"2026-06-19T12:00:00.000Z","correlation_id":"11111111-1111-4111-8111-111111111111","source":"panel_tasks_server","store":"panel_tasks","operation":"panel.task.create","phase":"before","outcome":"ok","entity_ref":{"kind":"task","id":"tsk_abc"},"mutation":"create","payload_summary":{"route":"POST /tasks","title_preview":"Fatura öde"}}
{"schema":"lumos.evidence_continuity.v1","ts":"2026-06-19T12:00:00.015Z","correlation_id":"11111111-1111-4111-8111-111111111111","source":"panel_tasks_server","store":"panel_tasks","operation":"panel.task.create","phase":"after","outcome":"ok","entity_ref":{"kind":"task","id":"tsk_abc"},"mutation":"create","payload_summary":{"task_count":3,"events_appended":1}}
```

**Panel delete — before/after + trash:**

```json
{"schema":"lumos.evidence_continuity.v1","ts":"2026-06-19T12:01:00.000Z","correlation_id":"22222222-2222-4222-8222-222222222222","source":"panel_tasks_server","store":"panel_tasks","operation":"panel.task.delete","phase":"before","outcome":"ok","entity_ref":{"kind":"task","id":"tsk_abc"},"mutation":"delete","payload_summary":{"route":"POST /tasks/delete"}}
{"schema":"lumos.evidence_continuity.v1","ts":"2026-06-19T12:01:00.020Z","correlation_id":"22222222-2222-4222-8222-222222222222","source":"panel_tasks_server","store":"panel_tasks","operation":"panel.task.delete","phase":"after","outcome":"ok","entity_ref":{"kind":"task","id":"tsk_abc"},"mutation":"delete","payload_summary":{"trash_written":true,"task_count":2,"events_appended":1}}
```

**Engine create — before/after:**

```json
{"schema":"lumos.evidence_continuity.v1","ts":"2026-06-19T12:02:00.000Z","correlation_id":"33333333-3333-4333-8333-333333333333","source":"task_engine","store":"task_engine","operation":"engine.task.mutation","phase":"before","outcome":"ok","entity_ref":{"kind":"task","id":"42"},"mutation":"create","payload_summary":{"step_count":3}}
{"schema":"lumos.evidence_continuity.v1","ts":"2026-06-19T12:02:00.008Z","correlation_id":"33333333-3333-4333-8333-333333333333","source":"task_engine","store":"task_engine","operation":"engine.task.mutation","phase":"after","outcome":"ok","entity_ref":{"kind":"task","id":"42"},"mutation":"create","payload_summary":{"step_count":3}}
```

**Panel write failure — error:**

```json
{"schema":"lumos.evidence_continuity.v1","ts":"2026-06-19T12:03:00.000Z","correlation_id":"44444444-4444-4444-8444-444444444444","source":"panel_tasks_server","store":"panel_tasks","operation":"panel.task.complete","phase":"error","outcome":"error","entity_ref":{"kind":"task","id":"tsk_xyz"},"mutation":"complete","error":{"code":"write_failed","message":"OSError: permission denied"}}
```

---

## Başarı kriterleri

| # | Kriter | Doğrulama |
|---|--------|-----------|
| 1 | Panel create → journal’da aynı `correlation_id` ile `before` + `after`, `store: panel_tasks` | Manuel / test script |
| 2 | Panel delete → `mutation: delete`, `payload_summary.trash_written: true` | Journal + `.lumos/trash/` varlığı |
| 3 | CLI görev oluştur → `source: task_engine`, `store: task_engine` | CLI + journal okuma |
| 4 | Journal yalnızca `.lumos/logs/evidence_continuity.jsonl` altında | Path kontrolü |
| 5 | Tüm satırlar `schema` + zorunlu alanları taşır | Spot check / şema validator (v1.1 adayı) |
| 6 | Kayıtlarda secret / ham kullanıcı mesajı yok | Payload review |
| 7 | Chat-local görevler journal’da **yok** — bilinen boşluk | Bilinçli kapsam dışı dokümantasyonu |
| 8 | `events[]` parallel kalır; journal ile reconcile edilmez | Truth kuralı doğrulaması |

**v1 “bitti” sayılması:** Kriter 1–6 geçer; 7–8 bilinen sınırlar olarak raporlanır. CI yeşil + uygulama commit’i olmadan tamamlanmış sayılmaz.

---

## Riskler

| Risk | Etki | v1 mitigasyon (onaylı ilke) |
|------|------|------------------------------|
| `events[]` + journal çift kayıt | Log şişmesi, tutarsızlık | Truth kuralı: journal = audit; `events[]` = UI projection |
| Chat gap devam eder | Continuity boşluğu | Bilinçli kapsam dışı; v2 prerequisite |
| Çift depo drift (ADR-008) | Parçalı kanıt | Journal `source` + `store` zorunlu; merge v2 |
| Panel `_write_doc` sandbox | Yanlış base_dir | Journal `base_dir` = `LUMOS_BASE_DIR`; sandbox test ayrı |
| Rotation ile eski kanıt kaybı | Geçmiş silinir | Default 1 MB × 3; v2 retention politikası |
| Hook log hatası ana işlemi kırar | Mutasyon fail | Best-effort append; ana mutasyon öncelikli |
| Public repo sınırı | Hassas veri sızıntısı | Demo-safe şema, `payload_summary` kısıtı |
| Görev silme UX (chat/client) | Silme kanıtı eksik | v1 kapsam dışı; journal bu boşluğu kapatmaz |

---

## v2’ye ertelenen maddeler

1. Chat görev persist + `id` + silme UX düzeltmesi  
2. Client evidence queue (`localStorage` → sunucu journal sync)  
3. Köprü `POST /task` outbox append + journal mirror  
4. Guard/policy tek semantik journal (`record_guard_event`, `log_policy_blocked`)  
5. Çift depo birleştirme — ADR-008 drift çözümü  
6. Legacy panel (`panel/js/app.js`) hizalama  
7. `events[]` migration veya deprecate  
8. Correlation UI — “son işlem kanıtı”, “buradan devam”  
9. Evidence-specific rotation / retention politikası  
10. `ObservationEngine` disk spill — CLI step lifecycle  
11. Structured query / görev durumu reconstruct  
12. Disconnect + resume integration test harness  
13. `result` fazı — köprü ve guard hatları için ayrı lifecycle  
14. Şema validator CI kapısı  

---

## Implementation-pending

Aşağıdakiler **henüz uygulanmadı**; bu belge uygulama izni vermez.

| Sıra | İş | Not |
|------|-----|-----|
| 1 | `append_evidence_event` helper modülü | Yeni dosya — kullanıcı onayı ile |
| 2 | Hook H1: `_write_doc()` | Panel tüm mutasyonlar |
| 3 | Hook H2: `save_task_store_json()` | Engine tüm mutasyonlar |
| 4 | Manuel / otomasyon doğrulama | Başarı kriterleri 1–6 |
| 5 | Şema spot-check / validator (opsiyonel v1.1) | Kriter 5 |

**Yasak (bu aşamada):** kod, test, runtime değişikliği, client/bridge/guard hook’ları, store merge, `open-decisions-needs-review.md` otomatik güncelleme (ayrı istek).

---

## Bağımlılıklar ve audit çapraz referansları

| Belge / bulgu | İlişki |
|---------------|--------|
| [ADR-008](../decisions/ADR-008-agent-network-boundary.md) | Çift görev deposu drift; v1 birleştirmez |
| [PERSISTENT_WRITE_PATH_AUDIT](../PERSISTENT_WRITE_PATH_AUDIT.md) | `save_task_store_json`, `append_log_line` sink haritası |
| [primary-user-surface-decision](./primary-user-surface-decision.md) | Astro panel birincil; legacy panel v2 |
| Evidence Continuity keşif raporu (2026-06) | Üç persistence hattı, hook choke-point doğrulaması |
| Evidence v1 eleştirel inceleme (2026-06) | Minimum hook, chat gap, çift kayıt riski |

---

## Sonraki adım

1. **Onay (tamamlandı — ilke):** Karar A ve EC1–EC8 `decision-approved`; teknik uygulama `implementation-pending`.
2. **Implementation-pending:** `append_evidence_event` + H1/H2 hook’ları — ayrı uygulama paketi, dar commit.
3. Chat silme, store merge ve köprü mirror **bu pakete dahil edilmez** — v2 backlog.

---

Son güncelleme: 2026-06-19
