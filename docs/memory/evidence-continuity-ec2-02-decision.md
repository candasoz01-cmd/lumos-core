# Evidence Continuity EC2-02 — Client Evidence Queue minimum v1 (onaylı karar)

> **Durum:** `decision-approved` / `implementation-pending` — tasarım kilitlendi; kod PR bekliyor.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 3 (EC2-02); v1 bilinçli boşluk (client hook'ları); `panel.astro` offline fallback ve meta overlay davranışı (2026-06-19 read-only tarama).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`primary-user-surface-decision.md`](./primary-user-surface-decision.md).

**Karar:** **Seçenek 1** — `panel.astro` içinde **pending-op kuyruğu** (`localStorage`); flush mevcut panel REST uçları üzerinden; journal şeması ve sunucu endpoint yüzeyi v1'de **değişmez**.

**Bağımlılık:** **EC2-01** merge edildi (`5073780`, PR #256) — chat görev oluşturma `POST /tasks` ile sunucuya persist eder; sunucu `id` (`tsk_*`) üretilir.

---

## Karar özeti

**Onaylı karar (firm):** Tarayıcıda yalnızca yerelde kalan görev mutasyonları (complete, delete, restore; gerekirse create-without-id) **append-only pending-op kuyruğuna** yazılır. Bağlantı veya API erişilebilir olduğunda kuyruk **mevcut** `tasksApiPost` REST çağrılarıyla boşaltılır; sunucu tarafı H1 hook'u journal'a `lumos.evidence_continuity.v1` satırı bırakır. İstemci journal'a **doğrudan yazmaz**; yeni sunucu endpoint v1'de **açılmaz**.

| # | Kural | Durum |
|---|--------|--------|
| CEQ1 | Pending-op kuyruğu tek anahtar: `lumos_panel_evidence_pending_ops_v1` | `decision-approved` |
| CEQ2 | Flush yalnızca mevcut REST: `POST /tasks`, `/tasks/complete`, `/tasks/delete`, `/tasks/restore` | `decision-approved` |
| CEQ3 | Journal şeması `lumos.evidence_continuity.v1` v1'de **genişletilmez** | `decision-approved` |
| CEQ4 | Yeni sunucu endpoint (`POST /evidence/client` vb.) v1'de **yok** | `decision-approved` |
| CEQ5 | Her kuyruk öğesi `op_id` (UUID v4) taşır — idempotency ve dedup | `decision-approved` |
| CEQ6 | Client-only meta (`taskPlan`, `bridgeLast`, `when`, `priority`) journal'a **girmez**; yalnızca mevcut `mergePanelGorevlerMetaFromPrevious` overlay korunur | `decision-approved` |
| CEQ7 | Demo-safe — kuyrukta secret, ham chat, token, production URL **yok** | `decision-approved` |
| CEQ8 | EC2-01 tamamlanmadan uygulama **başlamaz** (sunucu `id` olmadan sync anlamsız) | `verified` — merge `5073780` |

---

## Problem / mevcut boşluk

Evidence Continuity v1 yalnızca **sunucu yazım kapılarında** (H1 `_write_doc`, H2 `save_task_store_json`) journal bırakır. Astro panel (`ui/src/pages/panel.astro`) şu senaryolarda mutasyon yapar ama journal **oluşmaz**:

| Senaryo | Mevcut davranış | Continuity etkisi |
|---------|-----------------|-------------------|
| **Offline fallback** | `shouldSkipGorevlerTasksApi()` veya `shouldFallbackGorevlerTasksLocal(apiUnreachable)` → yerel tamamlama/silme/geri yükleme | Sunucu mutasyonu yok → H1 journal yok |
| **Local complete** | `completeGorevlerTaskLocal(t)` — `status: tamamlandi` + `persistPanelGorevlerTasks()` | Kanıt yalnızca `localStorage` (`lumos_panel_gorevler_list_v1`) |
| **Local delete / restore** | `finishDeleteGorevlerTaskLocal`, `lastGorevlerDeletedLocalRow` ile RAM/local restore | Trash + journal yok; tarayıcı temizlenince kanıt kaybolur |
| **Meta overlay** | `mergePanelGorevlerMetaFromPrevious` — `taskPlan`, `bridgeLast`, `priority`, `onay_bekliyor` sunucu refresh sonrası korunur | Meta istemci-only; journal veya görev deposu ile reconcile edilmez (bilinçli) |

**Kullanıcıya görünür semptom:** Prod panel + loopback API (`shouldSkipGorevlerTasksApi`), çevrimdışı mod veya geçici ağ kesintisinde görev «tamamlandı/silindi» görünür; `.lumos/logs/evidence_continuity.jsonl` içinde karşılık **yoktur**.

**EC2-01 sonrası kalan boşluk:** Chat/create artık mümkün olduğunda `POST /tasks` ile sunucuya gider ve journal alır; fakat **complete/delete/restore** offline yolları hâlâ journal dışıdır. EC2-02 bu boşluğu kapatır.

---

## EC2-01 bağımlılık doğrulaması

| Kontrol | Kanıt |
|---------|--------|
| Merge commit | `5073780` — `Merge pull request #256` (`feat/ec2-01-chat-task-persist`) |
| Dosyalar | `ui/src/pages/panel.astro`, `tests/test_panel_gorev_create_ec2_01.py` |
| Davranış | `persistPanelGorevCreateViaApi` / `applyPanelGorevKomutu` → `POST /tasks`; dönen `task.id` panel satırına yazılır |
| Journal | Sunucu create → H1 `panel.task.create` `before`/`after` (v1 şema) |
| Sert sıra | Backlog: EC2-02, EC2-01 **sonrasında** — [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) § bağımlılık grafi |

**Sonuç:** EC2-01 önkoşulu **karşılandı**; EC2-02 implementasyon PR'ı açılabilir.

---

## Seçilen yol ve neden bu yol

### Seçilen: pending-op kuyruğu + mevcut REST flush

```
[Offline / API unreachable]
  complete / delete / restore (local)
       │
       ▼
  enqueue pending-op ──► localStorage (lumos_panel_evidence_pending_ops_v1)
       │
       │  (online / API reachable / page load)
       ▼
  flushPendingEvidenceOps()
       │
       ├──► tasksApiPost("/tasks/complete" | "/tasks/delete" | "/tasks/restore" | "/tasks")
       │
       ▼
  panel_tasks_server._write_doc() ──► evidence_continuity.jsonl (H1 — mevcut)
```

**Neden bu yol:**

1. **Minimum sunucu yüzeyi** — v1 H0/H1/H2 ve `lumos.evidence_continuity.v1` şeması zaten doğrulandı (PR #248, EC2-14 CI); yeni endpoint veya şema genişlemesi regresyon riski taşır.
2. **Truth kuralı korunur** — journal yalnızca sunucu mutasyonlarından üretilir; istemci «kanıt yazmaz», «mutasyon talep eder».
3. **Mevcut REST semantiği yeterli** — complete/delete/restore/create zaten H1 journal bırakır; flush bu kapılardan geçer.
4. **Public repo güvenli** — tarayıcıdan disk journal append veya yeni evidence API yok; demo-safe sınır değişmez.
5. **EC2-01 ile uyum** — sunucu `id` ile kuyruk öğeleri hedeflenebilir; title-only fallback yalnızca legacy satırlar için sınırlı kalır.
6. **Meta overlay ayrımı** — `taskPlan` / `bridgeLast` istemci zenginleştirmesi; journal'a taşınmaz (v2+ ayrı karar).

---

## Reddedilen alternatifler

| Alternatif | Red gerekçesi |
|------------|---------------|
| **`POST /evidence/client`** (yeni sunucu endpoint) | Journal yazım kapısı çoğalır; auth/CORS/rate-limit; public yüzey genişler; v1 minimum hook ilkesine aykırı |
| **Tarayıcıdan doğrudan journal append** | `.lumos/logs/` istemciden yazılamaz/güvenilmez; truth kuralı ihlali; sandbox/guard bypass riski |
| **Şema genişlemesi v1** (`source: panel_client`, client `correlation_id` zorunlu alan vb.) | EC2-14 CI kapısı mevcut şemayı kilitler; client/server correlation birleştirme EC2-08 UI ile birlikte planlanmalı |
| **Kuyruk olmadan yalnızca «yeniden dene» banner'ı** | Kullanıcı sekmeyi kapatınca mutasyon kaybolur; continuity hedefi karşılanmaz |
| **Chat geçmişinden reconstruct** | PII/ham metin riski; kapsam dışı (§ kapsam dışı v1) |

---

## Minimum v1 tasarım

### Kuyruk anahtarı ve kayıt şekli

| Özellik | Değer |
|---------|--------|
| **localStorage key** | `lumos_panel_evidence_pending_ops_v1` |
| **Format** | JSON array; FIFO; en eski önce flush |
| **Maksimum boyut** | 64 öğe (aşımda en eski düşürülür + tek satır konsol uyarısı) |
| **Şema sürümü** | `v: 1` (kuyruk meta; journal şeması **değil**) |

**Örnek kuyruk öğesi:**

```json
{
  "v": 1,
  "op_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "op": "complete",
  "ref": "tsk_abc123",
  "ref_kind": "id",
  "enqueued_at": "2026-06-19T16:00:00.000Z",
  "attempts": 0
}
```

| `op` | REST hedefi | `ref` / `ref_kind` |
|-----|-------------|---------------------|
| `create` | `POST /tasks` | `title` (+ opsiyonel demo-safe `title_preview` hash değil düz title ≤200 char); `ref_kind: title` |
| `complete` | `POST /tasks/complete` | `ref`: `id` veya title; `ref_kind`: `id` \| `title` |
| `delete` | `POST /tasks/delete` | aynı |
| `restore` | `POST /tasks/restore` | `ref`: trash `id`; `ref_kind`: `id` |

**Yasak alanlar:** chat snippet, token, credential, bridge payload, ham plan metni, production URL.

### Enqueue noktaları (`panel.astro`)

| Fonksiyon / yol | Koşul | Kuyruklanan `op` |
|-----------------|-------|------------------|
| `completeGorevlerTaskLocal(t)` | offline fallback veya bilinçli local complete | `complete` |
| `finishDeleteGorevlerTaskLocal(t, ref)` | offline delete | `delete` |
| Offline restore (`lastGorevlerDeletedLocalRow` → liste) | sunucu restore yapılamadı | `restore` (sunucu trash'e yazılmış id varsa) veya `create` (yalnızca local row, sunucuda hiç yoksa — nadir) |
| `finishLocal()` create yolu | `shouldSkipGorevlerTasksApi()` ve satırda `id` yok | `create` |

**Not:** Sunucu reachability varken başarılı REST çağrısı sonrası **enqueue yapılmaz** — H1 zaten journal bırakır.

### Flush tetikleyicileri

| Tetikleyici | Davranış |
|-------------|----------|
| `wireGorevler` init — API erişilebilir | `flushPendingEvidenceOps()` (fire-and-forget, UI bloklamaz) |
| `refreshPanelGorevlerFromTasksApi()` başarılı | ardından flush |
| `document.visibilitychange` → `visible` | API erişilebilir ise flush |
| `window` `online` event | flush |
| Kullanıcı modu `offline` → `limited`/`full` | flush |

**Flush algoritması (özet):**

1. Kuyruk boş veya `shouldSkipGorevlerTasksApi()` → çık.
2. Kopya al; sırayla işle (FIFO).
3. Her öğe için ilgili `tasksApiPost`; başarı → öğeyi kuyruktan sil + persist.
4. `not_found` / zaten tamamlanmış benzeri → **idempotent success** say, öğeyi sil (journal zaten var veya görev yok).
5. Ağ hatası → `attempts++`; `< 5` ise öğe kuyrukta kalır; backoff (1s, 2s, 4s… max 30s) sonraki flush'ta.
6. Flush sonrası `refreshPanelGorevlerFromTasksApi()` + `mergePanelGorevlerMetaFromPrevious` (meta overlay korunur).

### Idempotency

| Katman | Mekanizma |
|--------|-----------|
| **Client** | `op_id` UUID v4; flush başarılı olunca öğe silinir; aynı `op_id` tekrar yazılmaz |
| **Server** | Mevcut REST + H1 journal; duplicate complete/delete için `not_found` / `ok` yanıtları idempotent kabul |
| **correlation_id** | Sunucu H1'de üretir (v1 şema); client göndermez — EC2-08'de UI birleştirme |
| **Dedup** | Enqueue öncesi aynı `(op, ref)` pending varsa yeni öğe eklenmez (son durum kazanır: complete/delete için) |

---

## Değişecek dosyalar (gelecek implementasyon — şimdi yapılmaz)

| Dosya | Değişiklik |
|-------|------------|
| `ui/src/pages/panel.astro` | Kuyruk CRUD, enqueue hook'ları, `flushPendingEvidenceOps`, tetikleyici wiring |
| `tests/test_panel_evidence_queue_ec2_02.py` | Kuyruk serileştirme, flush sırası, idempotent davranış (panel.astro mantığı ile hizalı saf Python veya js extract) |

**Bilerek dokunulmayacak (v1):**

- `panel/scripts/panel_tasks_server.py` — endpoint/yüzey değişikliği yok
- `src/core/evidence_continuity.py` — şema/validator değişikliği yok
- `panel/js/app.js` — legacy panel; Astro birincil (OD-043)
- Chat thread, köprü outbox, guard journal

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| T1 | Offline complete → kuyrukta 1 `complete` öğesi | `localStorage` key dolu; UI `tamamlandi` |
| T2 | Online flush → `POST /tasks/complete` | Journal'da `panel.task.complete` `before`+`after`; kuyruk boş |
| T3 | Offline delete → online flush | Journal'da `panel.task.delete`; trash yazımı H1 ile |
| T4 | Duplicate flush (aynı op iki kez) | Tek sunucu mutasyonu; ikinci flush idempotent |
| T5 | `not_found` complete | Kuyruk öğesi silinir; kullanıcıya bloklayıcı hata yok |
| T6 | EC2-01 create (`tsk_*`) + offline complete + flush | `ref_kind: id` ile hedefleme; journal zinciri |
| T7 | Meta overlay | Flush sonrası `taskPlan` / `bridgeLast` korunur (`mergePanelGorevlerMetaFromPrevious`) |
| T8 | Kuyruk limit 64+1 | En eski düşer; uyarı log |
| T9 | Demo-safe | Kuyruk JSON'unda token/chat/URL yok (spot check) |
| T10 | pytest paketi CI yeşil | EC2-14 şema kapısı regresyonsuz |

**Doğrulama kanalları:** pytest (T1–T10 otomasyonu mümkün olanlar); manuel izole `LUMOS_BASE_DIR` + panel sunucu curl journal okuma.

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| **Retry storm** | API flood | Backoff; max 5 attempt; flush tek uçuş (in-flight guard) |
| **Duplicate mutasyon** | Çift complete/delete | `op_id` + server idempotent yanıt; pending `(op,ref)` dedup |
| **correlation_id kopukluğu** | Client flush ↔ journal zinciri UI'da görünmez | Bilinçli v1; EC2-08'de birleştirme |
| **Offline uzun süre** | Kuyruk büyür | 64 cap; FIFO drop + uyarı |
| **Title-only ref çakışması** | Yanlış görev hedeflenir | EC2-01 sonrası `id` öncelikli; title fallback legacy |
| **Restore RAM limit** | `lastGorevlerDeletedLocalRow` kaybolur | Kuyruk `restore`/`create` ile persist; RAM yalnızca UX |
| **Meta/journal drift** | Plan köprü journal'da yok | Bilinçli kapsam dışı; overlay korunur |
| **Public repo sınırı** | Hassas payload kuyrukta | CEQ7 demo-safe alan seti |
| **Prod loopback skip** | `shouldSkipGorevlerTasksApi` true iken flush yok | Kuyruk birikir; kullanıcı local API veya mod değişince flush — bilinen sınırlama |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **Chat geçmişi replay / reconstruct** | PII; journal kaynağı değil |
| **`bridgeLast` / `taskPlan` journal mirror** | İstemci zenginleştirmesi; farklı semantik — EC2-03/04/13 |
| **EC2-08 correlation UI** | Yeterli journal + client correlation birleştirmesi gerekir |
| **Yeni journal şeması / `source: panel_client`** | Şema CI (EC2-14) — v2+ |
| **`POST /evidence/client`** | Reddedilen alternatif |
| **Legacy panel `app.js`** | Astro birincil; EC2-06 |
| **Köprü outbox, guard/policy** | EC2-03, EC2-04 |
| **Store merge (ADR-008)** | EC2-05 ayrı OD |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) | H1 journal; client v1 kapsam dışı idi |
| [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) | EC2-02 Phase 3; P0 |
| EC2-01 merge `5073780` / PR #256 | Önkoşul — chat create persist |
| EC2-14 / PR #255 | Şema CI — v1 genişleme yok |
| [`audit-hook-term-decision.md`](./audit-hook-term-decision.md) | «Audit hook» ≠ client queue |
| [`primary-user-surface-decision.md`](./primary-user-surface-decision.md) | `ui/src/pages/panel.astro` birincil |

---

## Sonraki adım

1. **Dar implementasyon PR:** `panel.astro` pending-op kuyruğu + flush + enqueue hook'ları; `tests/test_panel_evidence_queue_ec2_02.py`.
2. **Doğrulama:** T1–T10; journal spot check; CI yeşil (EC2-14 regresyonsuz).
3. **Backlog senkron:** Bu belge `decision-approved` → uygulama merge sonrası `implemented` / `verified` olarak güncellenir.

---

**İndeks notu:** EC2-02 ayrı OD kaydı açmaz; v2 backlog + bu belge canonical. `docs/decision-log.md` DL-A02 satırı ile senkron.

---

Son güncelleme: 2026-06-19
