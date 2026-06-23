# P1-05 — Tasks path audit (`.lumos/tasks.json` vs `.lumos/tasks/tasks.json`)

| Alan | Değer |
|------|-------|
| **ID** | P1-05 |
| **Tarih** | 2026-06-23 |
| **Durum** | **Kapalı (doc + küçük yorum düzeltmesi)** |
| **Sahip** | Platform |
| **Kaynak** | [p0-p1-triage-list.md](p0-p1-triage-list.md), [PANEL_READONLY_AUDIT.md](../PANEL_READONLY_AUDIT.md) §2.1 |

---

## Verdict (tek cümle)

**İki bilinçli, senkronize edilmeyen görev deposu vardır; tek kaynak yoktur.** Panel UX CRUD → `.lumos/tasks.json`; CLI/TaskEngine motor → `.lumos/tasks/tasks.json`. Birleştirme v1 kapsamı dışı (ADR-008, EC2-05).

---

## Path envanteri

| Yüzey | Relatif path | Tam path (`.lumos` base) | Yazıcı | Şema |
|-------|--------------|--------------------------|--------|------|
| **Panel CRUD** (`panel_tasks_server.py`) | `tasks.json` | `.lumos/tasks.json` | `GET/PUT /tasks.json`, `POST /tasks`, … | `v`, `tasks[]` (active/done), `events[]` |
| **TaskEngine / CLI** (`TaskStore`) | `tasks/tasks.json` | `.lumos/tasks/tasks.json` | `save_task_store_json()` → `TaskStore._save()` | `tasks[]`, `next_id`, adım zinciri |
| **Panel read-only bridge** | Her ikisi | `panel_bridge_state._read_tasks_payload` → panel path; `_task_engine_store_health` → engine path | Salt okuma | EC2-05 dual health |
| **Evidence continuity** | Registry | `PANEL_TASKS_STORE_REL_PATH` / `TASK_ENGINE_STORE_REL_PATH` | Journal `store` alanı | Paralel truth, merge yok |

### Workspace contract

- `CORE_STATE_PATH_NAMES` üst seviyede `"tasks.json"` içerir → panel deposu çekirdek state.
- `is_core_state_path()` özel durum: `tasks/tasks.json` → TaskEngine deposu da çekirdek state.
- `save_task_store_json(tasks_dir, …)` path: `tasks_dir / "tasks.json"` (tipik `tasks_dir = .lumos/tasks`).

**Sonuç:** Sözleşme her iki path'i de çekirdek kabul eder; tek canonical dosya tanımı yok — kasıtlı çift depo.

---

## Kod referansları (grep özeti)

| Dosya | Path kullanımı |
|-------|----------------|
| `panel/scripts/panel_tasks_server.py` | `_base_dir() / "tasks.json"` |
| `src/task_engine/engine.py` | `base_dir / "tasks.json"` (`base_dir` = `.lumos/tasks`) |
| `src/core/lumos_runtime.py` | `TaskStore(Path(base_dir) / "tasks", …)` |
| `src/core/panel_bridge_state.py` | Panel: `base/tasks.json`; engine: `base/tasks/tasks.json`; `system_paths` her ikisi |
| `src/core/evidence_continuity.py` | `TASK_STORE_REGISTRY` sabitleri |
| `src/core/workspace_contract.py` | `save_task_store_json`, `is_core_state_path` |
| `ui/src/pages/panel.astro` | Yorum: panel sunucu → `.lumos/tasks.json` |

Arşiv `archive/panel/js/app.js` aynı panel path'ini kullanır; aktif panel `ui/` + `panel_tasks_server.py` hattıdır.

---

## Sync var mı? Dual-reality riski

| Soru | Cevap |
|------|-------|
| Otomatik sync / merge | **Yok** |
| Panel POST → engine dosyası | **Hayır** |
| CLI görev → panel dosyası | **Hayır** |
| Evidence journal birleştirme | **Yok** (EC2-05: `source` + `store` ile ayrım) |

**Risk:** Kullanıcı panelden görev ekler → `.lumos/tasks.json` dolu; CLI `görev oluştur` → `.lumos/tasks/tasks.json` dolu. İki liste birbirini görmez. Pilot senaryosu S03 ([pilot-user-program-design.md](pilot-user-program-design.md)).

**Azaltma (mevcut):**

- `panel_bridge_state` dual-store health (`panel_tasks_store_ok`, `task_engine_store_ok`)
- `system_paths.panel_tasks` vs `system_paths.task_engine_tasks`
- ADR-008 drift tablosu ve migration defer

---

## Mevcut mimari karar (değiştirilmedi)

| Belge | Karar |
|-------|-------|
| [ADR-008](../decisions/ADR-008-agent-network-boundary.md) | Çift depo bilinçli; otomatik birleştirme yok |
| [evidence-continuity-ec2-05-decision.md](../memory/evidence-continuity-ec2-05-decision.md) | v1 store registry + dual health; merge defer |
| [evidence-continuity-v1-decision.md](../memory/evidence-continuity-v1-decision.md) | Store merge v2+ |

**Büyük refactor (tek path, migration) bu audit kapsamında yapılmadı** — ayrı onay + ADR gerekir.

---

## P1-05 kapanış aksiyonları

1. **Bu belge** — canonical P1-05 bulguları.
2. **Triage güncellemesi** — `p0-p1-triage-list.md` P1-05 → Kapalı.
3. **Küçük kod yorumu** — `TaskStore` sınıf docstring: gerçek tipik path `.lumos/tasks/tasks.json` (yanıltıcı `.lumos/tasks.json` ifadesi düzeltildi).
4. **INTERNAL_ALPHA_OPERATIONS** — §5 #4 ve operasyon günlüğü checkpoint.

### Yapılmayanlar (bilinçli)

- `tasks_dir_path()` contract helper (STABILIZATION_EXECUTION_PLAN #6 — opsiyonel, ayrı PR)
- Panel read-only `_read_tasks_payload` engine path'e geçiş (farklı şema; panel listesi panel store'dan gelmeli)
- Store birleştirme veya sync katmanı

---

## Operatör notu

Alpha/Pilot testinde görev tutarlılığı kontrol ederken **hangi yüzeyden** oluşturulduğunu not edin:

- Panel [Yerel] / `POST /tasks` → `.lumos/tasks.json`
- CLI / TaskEngine → `.lumos/tasks/tasks.json`

İkisi aynı listede görünmez; bu beklenen v1 davranışıdır.

---

## Çapraz referanslar

- [PANEL_READONLY_AUDIT.md](../PANEL_READONLY_AUDIT.md) §2.1 (read-only script panel path — bilinen; bridge EC2-05 ile genişletildi)
- [WORKSPACE_CONTRACT_STABILITY_AUDIT.md](../WORKSPACE_CONTRACT_STABILITY_AUDIT.md) §tasks path
- [INTERNAL_ALPHA_OPERATIONS.md](../INTERNAL_ALPHA_OPERATIONS.md) §5 #4

---

*Son güncelleme: 2026-06-23 — P1-05 kapatıldı (doc-only resolution; migration defer).*
