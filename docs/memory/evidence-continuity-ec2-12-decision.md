# Evidence Continuity EC2-12 — Disconnect/resume integration test harness (onaylı karar)

> **Durum:** `[implemented]` — PR #261 (`aa2a6ff`); test-only harness v1 merge edildi.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 4 (EC2-12); EC2-02 runtime merge sonrası disconnect/resume doğrulama boşluğu (2026-06-19 read-only keşif).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`primary-user-surface-decision.md`](./primary-user-surface-decision.md).

**Karar:** **Seçenek 1** — **test-only integration harness** (pytest + izole `LUMOS_BASE_DIR` + `panel_tasks_server` simülasyonu); disconnect/resume senaryoları DR1–DR7 otomatik doğrulanır; **runtime, şema ve sunucu yüzeyi v1'de değişmez**.

**Bağımlılık:** **EC2-02** merge edildi (PR #258, `bc6e4e0`) — pending-op kuyruğu + flush runtime mevcut; harness bu davranışı doğrular, yeniden uygulamaz.

---

## Karar özeti

**Onaylı karar (firm):** EC2-12, EC2-02 runtime'ının disconnect → enqueue → resume → journal reconcile zincirini **pytest integration harness** ile otomatikleştirir. «Disconnect» = enqueue without flush simülasyonu; «resume» = flush helper çağrısı. Gerçek ağ kopması veya tarayıcı E2E v1'de **gerekmez**. Yeni dosya: yalnızca `tests/test_panel_evidence_disconnect_resume_ec2_12.py`.

| # | Kural | Durum |
|---|--------|--------|
| DRH1 | v1 **test-only** — `panel.astro`, `panel_tasks_server.py`, `evidence_continuity.py` değişmez | `decision-approved` |
| DRH2 | Senaryo seti DR1–DR7 (complete/delete/restore flush, partial flush, idempotent, meta overlay) | `decision-approved` |
| DRH3 | Journal şeması `lumos.evidence_continuity.v1` v1'de **genişletilmez** | `decision-approved` |
| DRH4 | Yeni sunucu endpoint v1'de **yok** | `decision-approved` |
| DRH5 | Playwright / browser E2E v1'de **kapsam dışı** | `decision-approved` |
| DRH6 | EC2-02 merge **önkoşul** — harness mevcut flush sembollerine bağlı | `verified` — PR #258 |
| DRH7 | EC2-14 şema CI kapısı regresyonsuz kalmalı | `decision-approved` |

---

## Problem / mevcut boşluk

EC2-02 runtime (PR #258) disconnect/resume **davranışını uygular**; fakat otomatik doğrulama **eksiktir**. EC2-02 karar belgesi T1–T10 test planını tanımlar; mevcut `tests/test_panel_evidence_queue_ec2_02.py` yalnızca sembol kontrolü, enqueue ve **create** flush'u kapsar — complete/delete/restore disconnect/resume yolları test edilmemiştir.

**Keşif boşlukları (G1–G10 özeti):**

| # | Boşluk | Etki |
|---|--------|------|
| G1 | Prod loopback skip — `shouldSkipGorevlerTasksApi()` true iken flush **asla** çalışmaz | Kuyruk birikir; journal yok (bilinen sınırlama) |
| G2 | pytest disconnect/resume senaryosu **yok** | EC2-02 T2–T10 otomasyonu eksik |
| G3 | Complete/delete/restore flush testi **yok** | Yalnızca `create` flush testli |
| G4 | Partial flush — ağ hatasında FIFO yarıda kalır | Doğru davranış; test yok |
| G5 | Max attempt (5) sonrası sessiz stuck | Öğe kuyrukta kalır; stuck test yok |
| G6 | `window offline` event dinlenmiyor | Yalnızca `online` + visibility + interval |
| G7 | Concurrent tabs — `panelEvidenceFlushInFlight` sekme-local | Paralel flush; server idempotency'ye güven |
| G8 | Legacy E2E Astro'yu kapsamıyor | `panel/e2e/run-tasks-offline-online.mjs` legacy panel |
| G9 | `limited` → `full` geçişi flush tetiklemez | Edge case; API erişilebilirse sorun yok |
| G10 | Backoff/interval (45s) senaryoları test edilmemiş | CI'da pratik değil |

**EC2-12 hedefi:** G2, G3, G4 (kısmen), G5 (kısmen) — **doğrulama katmanı** ile kapatılır. G1, G6–G10 runtime iyileştirmeleri EC2-12 **dışı** (bilinçli kapsam dışı veya ayrı backlog).

---

## EC2-02 bağımlılığı (PR #258 merged)

| Kontrol | Kanıt |
|---------|--------|
| Merge commit | `bc6e4e0` — `Merge pull request #258` (`feat/ec2-02-client-evidence-queue`) |
| Runtime dosya | `ui/src/pages/panel.astro` — kuyruk CRUD, enqueue, `flushPendingEvidenceOps`, `wireEvidenceQueueFlushTriggers` |
| Mevcut test | `tests/test_panel_evidence_queue_ec2_02.py` — sembol, enqueue, create flush, dedup |
| Journal | Flush başarılı REST → H1 `panel.task.*` before/after (v1 şema) |
| Sert sıra | Backlog: EC2-12 tam değer için EC2-01..04; **minimum v1 için EC2-02 yeterli** |

**Sonuç:** EC2-02 önkoşulu **karşılandı**; harness PR'ı açılabilir. Harness, EC2-02'nin **mevcut flush davranışını** doğrular; runtime değiştirmez.

---

## Seçilen yol ve neden test-only harness

### Seçilen: pytest integration harness (runtime değişikliği yok)

```
[Simüle disconnect]
  offline complete / delete / restore
       │
       ▼
  enqueue pending-op (Python mirror — EC2-02 pattern)
       │
       │  (simüle resume — flush helper)
       ▼
  replayEvidencePendingOp / flush_* helpers
       │
       ├──► panel_tasks_server._write_doc() ──► evidence_continuity.jsonl (H1)
       │
       ▼
  pytest assert: journal before+after, kuyruk boş, idempotent
```

**Neden test-only harness (runtime değişikliği değil):**

1. **Backlog tanımı** — madde adı «integration **test harness**»; boşluk **doğrulama**, implementasyon değil.
2. **EC2-02 runtime zaten merge** — kuyruk + flush `panel.astro`'da mevcut; yeniden yazmaya gerek yok.
3. **Journal/şema/sunucu değişikliği istenmiyor** — CEQ3/CEQ4 (EC2-02) korunur; harness mevcut H1 journal'ı okur/doğrular.
4. **CI-dostu ve dar kapsam** — pytest + izole `LUMOS_BASE_DIR`; Playwright infra yok (OD-046).
5. **Public repo güvenli** — yeni endpoint, tarayıcı journal append veya şema genişlemesi yok.
6. **EC2-02 T1–T10 planını otomatikleştirir** — T2–T7 hedefi; mevcut EC2-02 testi T1/T9 kısmen karşılar.

**Neden E2E v1 değil:** `ui/` altında Playwright altyapısı yok; legacy E2E (`panel/e2e/`) Astro birincil paneli kapsamaz (OD-043, OD-046). Maliyet/yavaşlık; pytest integration v1 için yeterli.

**Neden runtime iyileştirme v1 değil:** G1 (prod loopback), G6 (`offline` event), G7 (concurrent tab lock) ayrı karar/bug; EC2-12 kapsam genişletmesi olur.

---

## Reddedilen alternatifler

| Alternatif | Red gerekçesi |
|------------|---------------|
| **Runtime flush iyileştirmesi EC2-12 içinde** | Kapsam genişler; backlog «harness» diyor; prod loopback (G1) ayrı karar |
| **`POST /evidence/client` veya şema genişlemesi** | EC2-02 reddi; journal truth kuralı; EC2-14 CI kapısı |
| **Tam browser E2E v1 zorunluluğu** | Infra yok; yavaş/flaky; pytest integration v1 yeterli |
| **Legacy panel E2E genişletme** | Astro birincil (OD-043); EC2-02 `panel.astro`'da |
| **Chat/köprü disconnect senaryoları** | EC2-03/04 bağımlılığı; Phase 4 tam değer sonrası |
| **HTTP subprocess integration v1 zorunluluğu** | v1.1 opsiyonel; saf Python simülasyonu CI için yeterli |

---

## Minimum v1 tasarım

### Senaryo seti (DR1–DR7)

| ID | Senaryo | Beklenen |
|----|---------|----------|
| DR1 | Create sunucuda → offline complete enqueue → flush | Journal'da `panel.task.complete` before+after; kuyruk boş |
| DR2 | Offline delete enqueue → flush | `panel.task.delete` journal; trash yazımı |
| DR3 | Offline restore enqueue → flush | `panel.task.restore` journal |
| DR4 | Multi-op FIFO: create+complete; 2. op ağ fail sim → partial | 1. flushed; 2. kuyrukta `attempts=1` |
| DR5 | Duplicate flush (idempotent) | Tek mutasyon; `not_found`/`already_done` → kuyruk temiz |
| DR6 | EC2-01 `tsk_*` + offline complete + flush | `ref_kind: id` hedefleme |
| DR7 | Meta overlay korunumu | Flush sonrası `taskPlan`/`bridgeLast` merge (`mergePanelGorevlerMetaFromPrevious` mantığı) |

**Simülasyon modeli:** «Disconnect» = enqueue without flush; «resume» = flush helper çağrısı. Gerçek HTTP/ağ kopması pytest'te gerekmez.

### Değişecek dosyalar (gelecek implementasyon — şimdi yapılmaz)

| Dosya | Değişiklik |
|-------|------------|
| `tests/test_panel_evidence_disconnect_resume_ec2_12.py` | **Yeni** — DR1–DR7 senaryoları |

**Opsiyonel (v1.1, aynı PR değil):**

| Dosya | Değişiklik |
|-------|------------|
| `tests/panel_evidence_harness.py` | Ortak helper'ların EC2-02 testinden paylaşımlı modüle taşınması |
| HTTP subprocess testleri | Gerçek POST/GET zinciri (flaky risk) |

**Bilerek dokunulmayacak (v1):**

- `ui/src/pages/panel.astro` — runtime stabil; harness önce mevcut davranışı doğrular
- `panel/scripts/panel_tasks_server.py` — endpoint/yüzey değişikliği yok
- `src/core/evidence_continuity.py` — şema/validator değişikliği yok
- Journal şeması — EC2-14 CI kapısı korunur

---

## Runtime değişikliği gerekmez — doğrulama

Harness, aşağıdaki **mevcut** `panel.astro` flush tetikleyicilerini ve algoritmasını doğrular; kod değişikliği **gerekmez**:

| Tetikleyici | Konum | Davranış |
|-------------|-------|----------|
| Sayfa init | `wireGorevlerPrototype` → `refreshPanelGorevlerFromTasksApi().then(... scheduleEvidenceQueueFlush())` (~11169–11181) | API skip değilse flush |
| Refresh başarı | `refreshPanelGorevlerFromTasksApi()` (~6834) | `scheduleEvidenceQueueFlush()` |
| `window` `online` | `wireEvidenceQueueFlushTriggers` (~6800) | flush |
| `visibilitychange` → visible | `wireEvidenceQueueFlushTriggers` (~6801–6802) | flush |
| 45s interval | `PANEL_EVIDENCE_FLUSH_INTERVAL_MS` (~6805–6807) | periyodik flush |
| Mod: `offline` → `limited`/`full` | `applyPanelUserMode` (~11818–11822) | flush |
| Flush algoritması | `flushPendingEvidenceOps` (~6738–6790) | FIFO, backoff, max 5 attempt, in-flight guard |
| Skip guard | `shouldSkipGorevlerTasksApi` (~6487–6491) | prod loopback — harness dışı (G1) |

**Enqueue noktaları (doğrulanacak yollar):** `completeGorevlerTaskLocal`, `finishDeleteGorevlerTaskLocal`, `restoreLastGorevlerTask`, `finishLocal` create yolu — EC2-02 karar belgesi ile hizalı.

**Sembol regresyonu:** Mevcut `test_panel_astro_evidence_queue_symbols()` (`_panel_astro_has_evidence_queue`) EC2-02 sembollerini korur; EC2-12 harness ayrı dosyada genişletir.

---

## Test stratejisi

### Katmanlar

| Katman | Araç | v1 durumu |
|--------|------|-----------|
| **Unit mirror** | pytest — enqueue/dedup/backoff/idempotent helpers | EC2-02 mevcut + EC2-12 genişletme |
| **Integration** | pytest + `panel_tasks_server` + izole `LUMOS_BASE_DIR` | **Birincil v1** — DR1–DR7 |
| **HTTP subprocess** | pytest + spawn server | v1.1 opsiyonel |
| **Browser E2E** | Playwright + `ui/dist/panel` | **Kapsam dışı v1** |

### EC2-02 T1–T10 eşlemesi

| T# | EC2-02 plan | EC2-12 v1 |
|----|-------------|-----------|
| T1 | Offline complete → kuyruk | DR1 (complete yolu) |
| T2 | Online flush → journal | DR1 flush sonrası journal assert |
| T3 | Offline delete → flush | DR2 |
| T4 | Duplicate flush idempotent | DR5 |
| T5 | `not_found` complete | DR5 |
| T6 | EC2-01 id + offline complete | DR6 |
| T7 | Meta overlay | DR7 |
| T8 | Kuyruk limit 64+1 | EC2-02 test'te yok; v1.1 |
| T9 | Demo-safe spot check | Mevcut EC2-02 test |
| T10 | CI yeşil | Tüm paket + EC2-14 regresyonsuz |

**Doğrulama kanalları:** `pytest tests/test_panel_evidence_disconnect_resume_ec2_12.py`; journal `evidence_continuity_path()` + `validate_evidence_record`; EC2-14 şema kapısı.

**Python mirror drift riski:** Sembol test + dar senaryo seti; kritik path'ler EC2-02 karar doc ile hizalı.

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| **Python mirror ↔ JS drift** | Harness yanlış geçer | Sembol test; EC2-02 doc hizası; dar senaryo |
| **HTTP subprocess flaky** | CI kırmızı | v1'de saf Python simülasyonu; HTTP v1.1 |
| **Prod loopback (G1) harness dışı** | Prod'da flush yok | Bilinçli; harness izole loopback ortamında |
| **E2E scope creep** | Maliyet patlaması | Playwright v1 reddedildi |
| **Partial flush / stuck queue (G4/G5)** | Yanlış assert | DR4/DR5 senaryoları; max attempt bilinçli sınır |
| **Concurrent tabs (G7)** | Çift mutasyon | Harness dışı; server idempotency mevcut |
| **EC2-14 regresyon** | Şema ihlali | Journal assert her senaryoda |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **Playwright / browser E2E** | Infra yok (OD-046); maliyet; pytest yeterli |
| **Prod loopback skip düzeltmesi (G1)** | Runtime değişikliği; ayrı karar |
| **`window offline` event (G6)** | Runtime iyileştirme; EC2-12 dışı |
| **Concurrent tab lock (G7)** | Runtime iyileştirme; EC2-12 dışı |
| **Köprü/guard disconnect (EC2-03/04)** | Phase 4 tam değer; journal kaynağı yok |
| **Chat geçmişi replay** | PII; EC2-02 kapsam dışı |
| **Şema genişlemesi / `POST /evidence/client`** | EC2-02 reddi; EC2-14 CI |
| **Legacy panel E2E** | Astro birincil (OD-043) |
| **T8 kuyruk limit 64+1** | v1.1; EC2-02 test'e eklenebilir |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md) | Runtime + T1–T10 plan; EC2-12 doğrular |
| [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) | EC2-12 Phase 4; P1 |
| EC2-02 merge `bc6e4e0` / PR #258 | Önkoşul — kuyruk + flush |
| EC2-14 / PR #255 | Şema CI — v1 genişleme yok |
| [`primary-user-surface-decision.md`](./primary-user-surface-decision.md) | `ui/src/pages/panel.astro` birincil |
| [`build-e2e-surface-alignment-decision.md`](./build-e2e-surface-alignment-decision.md) | E2E v1 erteleme (OD-046) |

---

## Uygulama

**Merge:** PR #261 (`aa2a6ff` — `test/ec2-12-disconnect-resume-harness`).

| Dosya | Değişiklik |
|-------|------------|
| `tests/test_panel_evidence_disconnect_resume_ec2_12.py` | DR1–DR7 disconnect/resume senaryoları — pytest + izole `LUMOS_BASE_DIR` + `panel_tasks_server` simülasyonu |

| Senaryo | Test |
|---------|------|
| DR1 | `test_dr1_server_create_offline_complete_enqueue_flush_journal` |
| DR2 | `test_dr2_offline_delete_enqueue_flush_journal_and_trash` |
| DR3 | `test_dr3_offline_restore_enqueue_flush_journal` |
| DR4 | `test_dr4_multi_op_fifo_partial_flush_on_network_fail` |
| DR5 | `test_dr5_duplicate_idempotent_flush_already_done_and_not_found` |
| DR6 | `test_dr6_ec2_01_tsk_id_offline_complete_flush` |
| DR7 | `test_dr7_meta_overlay_preserved_after_flush_refresh` |

Runtime, sunucu yüzeyi ve journal şeması v1'de değişmedi (DRH1, DRH3, DRH4).

---

## Sonraki adım

1. **Backlog senkron:** v2 backlog EC2-12 → `[implemented]` ✓.
2. **Phase 4 kalan:** EC2-03 (köprü mirror), EC2-04 (guard/policy normalize), EC2-08 (correlation UI), EC2-13 (`result` faz).
3. **Opsiyonel v1.1:** Ortak helper modülü; HTTP subprocess; T8 kuyruk limit testi.

---

**İndeks notu:** EC2-12 ayrı OD kaydı açmaz; v2 backlog + bu belge canonical. `docs/decision-log.md` DL-A03 satırı ile senkron.

---

Son güncelleme: 2026-06-19 (PR #261 merge — `[implemented]`)
