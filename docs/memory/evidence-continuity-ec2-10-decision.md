# Evidence Continuity EC2-10 — ObservationEngine disk spill (onaylı karar)

> **Durum:** `[implemented]` — merge PR #289 (`1a0f411`); observation lifecycle spill uygulandı.
>
> **Keşif kaynağı:** v1 bilinçli boşluk — `ObservationEngine` in-memory only; CLI step lifecycle kaybolur; read-only keşif (2026-06-20).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md).

**Karar:** **Seçenek 1 (minimum v1)** — opsiyonel JSONL disk spill (`.lumos/logs/observation_lifecycle.jsonl`); `ObservationLifecycleSpill` best-effort append; TaskEngine `base_dir` + `observation_engine` birlikteyken otomatik bağlanır; evidence journal şeması **değişmez**; read-only tail helper.

---

## Karar özeti

| # | Kural | Durum |
|---|--------|--------|
| OB1 | Spill dosyası: `.lumos/logs/observation_lifecycle.jsonl` | `decision-approved` |
| OB2 | Şema: `lumos.observation_lifecycle.v1` — task_id, event_type, step_id, payload | `decision-approved` |
| OB3 | Best-effort append; observation memory birincil runtime | `decision-approved` |
| OB4 | Evidence journal mirror v1 **dışı** — ayrı domain | `decision-approved` |
| OB5 | Rotation: evidence ile aynı default (1 MB × 3) | `decision-approved` |
| OB6 | Spill yoksa davranış değişmez (in-memory only) | `decision-approved` |

---

## Minimum v1 uygulama sınırı

| Dosya | Değişiklik |
|-------|------------|
| `src/task_engine/observation/lifecycle_spill.py` | **Yeni** — spill path, append, read_recent |
| `src/task_engine/observation/engine.py` | Opsiyonel spill hook |
| `src/task_engine/engine.py` | Auto-wire spill when base_dir set |
| `tests/test_observation_lifecycle_spill_ec2_10.py` | **Yeni** — O1–O6 |

---

## Uygulama

**Merge:** PR #289 (`1a0f411` — `feat/ec2-10-observation-spill`).

| Dosya | Değişiklik |
|-------|------------|
| `src/task_engine/observation/lifecycle_spill.py` | Spill append + read_recent |
| `src/task_engine/observation/engine.py` | lifecycle_spill hook |
| `src/task_engine/engine.py` | Auto-wire when base_dir + observation_engine |
| `tests/test_observation_lifecycle_spill_ec2_10.py` | O1–O6 |

Evidence journal mirror **v1 uygulanmadı** — OB4.
