# Evidence Continuity EC2-11 — Structured query / reconstruct (onaylı karar)

> **Durum:** `[implemented]` — merge PR #291 (`980a50f`); structured query API uygulandı.
>
> **Keşif kaynağı:** v2 backlog EC2-11; EC2-08 tail read mevcut; full reconstruct v1 dışı (2026-06-20).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md).

**Karar:** **Seçenek 1 (minimum v1)** — read-only filtered query over journal tail (`entity_id`, `operation`, `source`); `GET /evidence/query`; demo-safe UI projection; **tam görev durumu reconstruct v1 dışı**.

---

## Karar özeti

| # | Kural | Durum |
|---|--------|--------|
| QY1 | `filter_evidence_events()` + `query_evidence_events()` read-only | `decision-approved` |
| QY2 | `GET /evidence/query?entity_id=&operation=&source=&limit=` | `decision-approved` |
| QY3 | Arama kapsamı: `read_recent` tail (MAX_READ_LIMIT) — bilinçli sınır | `decision-approved` |
| QY4 | Yanıt: UI projection şeması + `filters` metadata | `decision-approved` |
| QY5 | Tam reconstruct / cross-store merge v1 **dışı** | `decision-approved` |
| QY6 | Journal yazım hook'ları değişmez | `decision-approved` |

---

## Minimum v1 uygulama sınırı

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | filter + query helpers |
| `panel/scripts/panel_tasks_server.py` | GET `/evidence/query` |
| `tests/test_evidence_query_ec2_11.py` | Q1–Q6 |

---

## Uygulama

**Merge:** PR #291 (`980a50f` — `feat/ec2-11-evidence-query`).

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | filter + query helpers |
| `panel/scripts/panel_tasks_server.py` | GET `/evidence/query` |
| `tests/test_evidence_query_ec2_11.py` | Q1–Q6 |

Tam görev durumu reconstruct **v1 uygulanmadı** — QY5.
