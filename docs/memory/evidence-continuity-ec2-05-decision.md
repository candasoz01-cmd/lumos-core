# Evidence Continuity EC2-05 — Store merge / ADR-008 drift (onaylı karar)

> **Durum:** `[decision-approved]` — minimum v1 slice tanımlandı; tam ADR-008 store merge **reddedildi** (v1).
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 5 (EC2-05); ADR-008 çift görev deposu drift; v1 bilinçli boşluk (store merge); read-only keşif (2026-06-20).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [ADR-008](../decisions/ADR-008-agent-network-boundary.md), [`docs/PANEL_READONLY_AUDIT.md`](../PANEL_READONLY_AUDIT.md).

**Karar:** **Seçenek 1 (minimum v1)** — tam store merge **yapılmaz**; dual store parallel truth kalır; journal `source` + `store` ayrımı yeterli; read-only **store registry** + **dual-store health sinyali** (panel bridge) dar uygulama; `POST /task` ≠ `POST /tasks` birleştirilmez; chat `localStorage` store merge kapsamı **dışı**.

**Bağımlılık:** v2 Phase 1–4 tamamlandı (EC2-01..04, 08, 12, 13, 14); EC2-05 v2 fazlarına **hard blocker değil** (backlog).

---

## Karar özeti

**Onaylı karar (firm):** ADR-008'de kayıtlı çift görev deposu drift (`.lumos/tasks.json` panel CRUD vs `.lumos/tasks/tasks.json` TaskEngine) v1'de **birleştirilmez**. Evidence continuity journal zaten `source` + `store` ile hatları ayırır (`panel_tasks` / `task_engine`). Minimum v1: kodda **store path registry** sabitleri ve panel read-only bridge'de **her iki deponun ayrı sağlık sinyali** — merge, migration veya tek yazıcı yok.

| # | Kural | Durum |
|---|--------|--------|
| SM1 | Tam store merge v1 **reddedildi** — parallel truth korunur | `decision-approved` |
| SM2 | Journal `source` + `store` birincil ayrım; cross-store reconcile yok | `decision-approved` |
| SM3 | `POST /task` (köprü yürütme) ≠ `POST /tasks` (panel CRUD) — endpoint birleştirme yok | `decision-approved` |
| SM4 | Minimum v1 kod: `TASK_STORE_REGISTRY` + dual-store read-only health | `decision-approved` |
| SM5 | Chat geçmişi (`localStorage`) filesystem store merge kapsamı **dışı** | `decision-approved` |
| SM6 | `events[]` panel projection parallel kalır; journal ile otomatik reconcile yok | `decision-approved` |
| SM7 | Otomatik migration / tek canonical TaskStore yok — ayrı OD + onay gerekir | `decision-approved` |
| SM8 | Read-only bridge panel görev listesini **panel store**'dan okumaya devam eder | `decision-approved` |

---

## Problem / mevcut boşluk

Evidence Continuity v1 journal, panel sunucu (H1) ve TaskEngine (H2) mutasyonlarında `source` + `store` ile hatları ayırır; **depolar birleştirilmez**. ADR-008 ve v1 karar belgesi çift depo drift'i bilinçli kayıt altına alır.

### Bugün iki görev deposu nerede?

| Depo | Path | Yazıcı | JSON şema | Journal |
|------|------|--------|-----------|---------|
| **Panel tasks** | `.lumos/tasks.json` | `panel_tasks_server._write_doc()` | `tasks[]`, `events[]`, panel UX alanları | `source: panel_tasks_server`, `store: panel_tasks` |
| **TaskEngine** | `.lumos/tasks/tasks.json` | `TaskStore._save()` → `save_task_store_json()` | Engine `tasks` + `next_id` | `source: task_engine`, `store: task_engine` |

**Kritik drift (ADR-008):** Farklı path, farklı şema, farklı yazıcı; tek kaynak yok. CLI ile oluşturulan görevler TaskEngine path'te; panel CRUD panel path'te — kullanıcı «boş görev listesi» görebilir (`PANEL_READONLY_AUDIT`).

### Chat store (ayrı — merge değil)

| Depo | Konum | Yazıcı | EC2-05 kapsamı |
|------|-------|--------|----------------|
| Chat geçmişi | Tarayıcı `localStorage` (panel.astro / legacy app.js) | İstemci | **Dışı** — EC2-01/02 client queue; filesystem merge değil |
| Köprü outbox | `.lumos/outbox/last_*.json` | Köprü overwrite | **Dışı** — EC2-03 journal mirror yeterli v1 |

### Read-only bridge bugün ne okuyor?

`src/core/panel_bridge_state.py`:

- `_read_tasks_payload()` → `base/tasks.json` (panel store) — **doğru** panel UX için
- `_task_engine_health()` → aynı `base/tasks.json` — **yanlış etiket**; TaskEngine path (`base/tasks/tasks.json`) kontrol edilmiyor
- `system_paths["tasks"]` → panel path only

**Semptom:** System ekranı «Görev Motoru» kartı panel dosyasını okur; CLI görevleri varken engine store «yok» görünür veya tersi karışıklık.

### Journal zaten ayırıyor (merge gerekmez continuity için)

```python
# evidence_continuity.py — mevcut
STORE_PANEL_TASKS = "panel_tasks"      # → .lumos/tasks.json
STORE_TASK_ENGINE = "task_engine"      # → .lumos/tasks/tasks.json
```

v1 truth kuralı ([`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md)): journal continuity birincil; `events[]` projection; cross-store reconcile yok.

---

## Seçenekler

### Seçenek 1 — Minimum v1: registry + dual-store read-only health (SEÇİLDİ)

- Tam merge yok; registry sabitleri + bridge'de ayrı health/path sinyalleri
- Düşük regresyon; public-safe; ADR-008 «migration ayrı onay» ile uyumlu

### Seçenek 2 — Tam store merge (TaskEngine canonical, panel migrate)

- Yüksek regresyon; şema migration; trash/events[]; panel + köprü etkisi
- ADR-008 «bu turda yapılmaz»; backlog P2 ayrı OD — **v1 reddedildi**

### Seçenek 3 — Docs-only (registry/health yok)

- Karar kaydı yeterli; drift teşhisi bridge'de kalır
- Minimum operasyonel değer düşük — **reddedildi** (dar kod slice tercih)

---

## Seçilen yol ve neden

**Seçenek 1:** Continuity journal merge olmadan çalışır; asıl kullanıcı/teşhis boşluğu read-only tarafın engine path'i görmemesidir. Registry + dual health, merge riski olmadan «hangi depo nerede» sorusunu kodda sabitler. Tam merge gelecekte ayrı OD + migration planı gerektirir (SM7).

---

## Minimum v1 uygulama sınırı

### Yapılacak (dar)

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | `TASK_STORE_REGISTRY`, `task_store_rel_path()`, `resolve_task_store_path()` |
| `src/core/panel_bridge_state.py` | `_store_file_health()`; `_panel_tasks_store_health()` + `_task_engine_store_health()`; `system_paths` dual path; `task_engine` kart notu drift-aware |
| `tests/test_evidence_store_registry_ec2_05.py` | **Yeni** — R1–R8 registry + dual health |

### Bilerek dokunulmayacak (v1)

| Alan | Gerekçe |
|------|---------|
| `panel_tasks_server.py` yazım path | Panel store ayrı boru hattı |
| `task_engine/engine.py` TaskStore | Engine store ayrı |
| `save_task_store_json` / migration | SM7 — ayrı OD |
| `POST /task` ↔ `POST /tasks` birleştirme | ADR-008 |
| `read_backend_state.py` / `packages/kando_core` ayna | Canonical `src/core/`; ayna sync EC2-05 dışı |
| Journal şema / hook'lar | EC2-05 store path metadata journal'a eklenmez v1 |
| EC2-06 legacy panel, EC2-07 events[] | Kapsam dışı |

---

## Store registry (v1 sözleşme)

| `store` (journal enum) | Relative path (base = `.lumos/`) | Yazıcı |
|------------------------|----------------------------------|--------|
| `panel_tasks` | `tasks.json` | `panel_tasks_server` |
| `task_engine` | `tasks/tasks.json` | `TaskStore` / `save_task_store_json` |

Chat / outbox / trash bu registry'de **yok** — farklı domain.

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| R1 | `task_store_rel_path("panel_tasks")` | `"tasks.json"` |
| R2 | `task_store_rel_path("task_engine")` | `"tasks/tasks.json"` |
| R3 | Bilinmeyen store | `None` |
| R4 | `resolve_task_store_path(tmp_path, "task_engine")` | `tmp_path/tasks/tasks.json` |
| R5 | Yalnız panel store dosyası | Panel health ok; engine health «yok» |
| R6 | Yalnız engine store dosyası | Engine health ok; panel tasks payload count 0 |
| R7 | Her iki store mevcut | Her iki health ok; paths farklı |
| R8 | EC2-14 / mevcut evidence testleri | Regresyonsuz |

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| **Erken tam merge** | Yüksek regresyon, trash/events[] | SM1 reddi; ayrı OD |
| **Dual store kullanıcı kafa karışıklığı** | «Görev nerede?» | Dual health + path labels; journal source/store |
| **Bridge hâlâ panel listesi gösterir** | Engine görevleri listede yok | Bilinçli SM8; tam liste merge sonrası |
| **packages/kando_core ayna drift** | İki kopya farklı kalabilir | Canonical `src/core/`; OD-027 |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **Tek canonical TaskStore** | Seçenek 2 — ayrı OD |
| **Otomatik iki-yönlü sync** | Reconcile yok; journal truth ayrı |
| **Chat localStorage → tasks.json merge** | EC2-01/02; farklı domain |
| **Köprü outbox → tasks merge** | EC2-03 |
| **Legacy panel path fix (EC2-06)** | Astro birincil |
| **`events[]` migration (EC2-07)** | Parallel truth |
| **Journal'a filesystem path yazma** | Demo-safe; registry kod sabiti yeterli |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [ADR-008](../decisions/ADR-008-agent-network-boundary.md) | Çift depo drift kaynağı; migration «yapılmaz» |
| [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) | v1 merge dışı; journal source+store |
| [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) | EC2-05 P2 Phase 5 |
| [`docs/PANEL_READONLY_AUDIT.md`](../PANEL_READONLY_AUDIT.md) | Path drift teşhisi |
| EC2-08 | Correlation UI engine olayları panel bağlamı dışı — bilinçli |
| EC2-09 | Retention ayrı madde |

---

## Uygulama

**Durum:** `[decision-approved]` — implementasyon PR bekliyor.

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | Store registry helpers |
| `src/core/panel_bridge_state.py` | Dual-store health + system_paths |
| `tests/test_evidence_store_registry_ec2_05.py` | R1–R8 |

Tam store merge **v1 uygulanmaz** — gerekçe: ADR-008 yüksek etki; regresyon; ayrı migration OD (SM7).

---

## Sonraki adım

1. Implementasyon PR merge + backlog/decision-log sync.
2. Gelecek (v2+ / ayrı OD): TaskEngine canonical migration, panel store deprecate, trash/events[] planı — **EC2-05 v1 dışı**.

---

Son güncelleme: 2026-06-20 (karar onay — minimum v1 slice)
