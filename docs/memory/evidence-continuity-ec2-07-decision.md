# Evidence Continuity EC2-07 — `events[]` migration / deprecate (onaylı karar)

> **Durum:** `[decision-approved]` — minimum v1 uygulama bekliyor.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 5 (EC2-07); v1 truth kuralı (`events[]` = UI projection); EC2-05 SM6; read-only keşif (2026-06-20).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md).
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`evidence-continuity-ec2-05-decision.md`](./evidence-continuity-ec2-05-decision.md).

**Karar:** **Seçenek 1 (minimum v1)** — tam `events[]` migration **yapılmaz**; disk yazımı ve panel Kayıtlar/Dashboard tüketimi **korunur**; read-only **`events_meta`** API metadata (`GET /tasks`, `GET /tasks.json`) journal'ın audit truth olduğunu açıkça belirtir; `tasks_json_events_projection_meta()` sabit DTO.

**Bağımlılık:** EC2-08 read API mevcut; EC2-05 parallel truth kuralı korunur.

---

## Karar özeti

| # | Kural | Durum |
|---|--------|--------|
| EV1 | Tam `events[]` → journal migration v1 **reddedildi** | `decision-approved` |
| EV2 | `tasks.json` on-disk şeması değişmez (`v`, `tasks`, `events`) | `decision-approved` |
| EV3 | Panel sunucu yazım hattı `events[]` append'e devam eder | `decision-approved` |
| EV4 | Read-only `events_meta` yalnızca HTTP GET yanıtında; dosyaya yazılmaz | `decision-approved` |
| EV5 | Audit truth = `.lumos/logs/evidence_continuity.jsonl` | `decision-approved` |
| EV6 | Journal ile `events[]` otomatik reconcile **yok** | `decision-approved` |
| EV7 | `deprecation_status: soft_deprecated_v1` — UI projection rolü açık | `decision-approved` |

---

## Problem / mevcut boşluk

v1 karar: journal continuity birincil; `tasks.json` içindeki `events[]` panel UI projection (Kayıtlar, Dashboard, legacy ledger). İki kanal paralel kalır — teşhiste karışıklık riski.

| Kanal | Rol bugün | Boşluk |
|-------|-----------|--------|
| `evidence_continuity.jsonl` | Audit / continuity truth | API metadata var (EC2-08/09) |
| `tasks.json` → `events[]` | UI projection | Rol API yanıtında **belirtilmiyor** |

---

## Seçenekler

### Seçenek 1 — API metadata + soft deprecation (SEÇİLDİ)

Davranış değişmez; rol görünür ve test edilebilir.

### Seçenek 2 — Tam migration (events[] kaldır, journal-only UI)

Kayıtlar/Dashboard regresyonu; yüksek risk — **v1 reddedildi**.

### Seçenek 3 — Yazım durdur (events[] append kapat)

Panel UI kırılır — **v1 reddedildi**.

### Seçenek 4 — Docs-only

Metadata yok — **reddedildi** (EC2-05/09 slice ile uyumsuz).

---

## Minimum v1 uygulama sınırı

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | `tasks_json_events_projection_meta()`; `enrich_tasks_doc_api_response()` |
| `panel/scripts/panel_tasks_server.py` | GET `/tasks`, `/tasks.json` → enriched response |
| `tests/test_evidence_events_projection_ec2_07.py` | **Yeni** — E1–E6 |

**Bilerek dokunulmayacak:** on-disk `tasks.json` şeması, `events[]` yazım, journal şema, UI tüketim kodu.

---

## Policy DTO (v1)

```json
{
  "policy_id": "lumos.tasks_json.events_projection.v1",
  "role": "ui_projection",
  "audit_truth": "evidence_continuity_journal",
  "reconcile_with_journal": false,
  "deprecation_status": "soft_deprecated_v1",
  "events_count": 3
}
```

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| E1 | `tasks_json_events_projection_meta()` | policy_id, audit_truth |
| E2 | Boş doc enrich | events_count 0 |
| E3 | Doc with events enrich | events_count doğru |
| E4 | On-disk doc unchanged | `_read_doc()` events_meta yok |
| E5 | GET handler uses enrich | build helper çağrısı |
| E6 | EC2-08/09 regresyonsuz | Mevcut pytest yeşil |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| events[] kaldırma | EV1 |
| Journal → events[] backfill | EV6 |
| Kayıtlar UI journal'a geçiş | Ayrı UI paketi |
| TaskEngine events | Farklı store |

---

## Uygulama

*(Implementasyon PR merge sonrası doldurulur.)*
