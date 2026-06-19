# Evidence Continuity EC2-09 — Retention / rotation policy (onaylı karar)

> **Durum:** `[implemented]` — merge PR #280 (`121216d`); retention policy metadata uygulandı.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 5 (EC2-09); v1 `append_jsonl_with_rotation` (1 MB × 3); EC2-08 rotation bilinçli sınır; read-only keşif (2026-06-20).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md).
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md), `src/core/log_rotation.py`.

**Karar:** **Seçenek 1 (minimum v1)** — mevcut `log_rotation` default'ları evidence journal için **adlandırılmış sabitler** olarak sabitlenir (`1 MB × 3` rotated + current); `evidence_retention_policy()` + `evidence_journal_storage_summary()` read-only; `GET /evidence/recent` yanıtına `retention` + `storage` metadata; **config override yok**; rotated dosyalardan UI tail-read **v1 dışı**.

**Bağımlılık:** EC2-08 read API mevcut (PR #274); EC2-14 şema CI — yanıt metadata journal şemasını değiştirmez.

---

## Karar özeti

| # | Kural | Durum |
|---|--------|--------|
| RT1 | v1 retention: **1 MB** per file, **3** rotated copies (+ current slot) | `decision-approved` |
| RT2 | Sabitler `evidence_continuity.py` içinde adlandırılır; `append_evidence_event` bunları kullanır | `decision-approved` |
| RT3 | Read-only `evidence_retention_policy()` — policy DTO (config yok) | `decision-approved` |
| RT4 | Read-only `evidence_journal_storage_summary(base_dir)` — mevcut dosya sayısı / byte | `decision-approved` |
| RT5 | `GET /evidence/recent` → `retention` + `storage` metadata (UI projection şeması aynı) | `decision-approved` |
| RT6 | Rotated `.jsonl.N` dosyalarından UI read **v1 dışı** — `read_recent` yalnızca current | `decision-approved` |
| RT7 | `.lumos/config` override, arşiv, TTL gün bazlı silme **v1 dışı** | `decision-approved` |
| RT8 | Evolution / decision log rotation ayrı domain — evidence sabitleri paylaşılmaz | `decision-approved` |

---

## Problem / mevcut boşluk

v1 journal `append_evidence_event` → `append_jsonl_with_rotation(..., DEFAULT_MAX_BYTES, DEFAULT_KEEP)` kullanır. Sabitler `log_rotation.py`'de genel JSONL default'larıdır; evidence-specific **adlandırılmış politika** ve **operasyonel görünürlük** yoktur.

| Özellik | Bugün | Boşluk |
|---------|-------|--------|
| Max file size | 1_000_000 B (implicit) | Evidence-specific isim yok |
| Rotated keep | 3 (implicit) | Policy DTO yok |
| API metadata | `events` + `truncated` only | Retention bilgisi UI/operatörde yok |
| Rotated read | `read_recent` yalnızca current file | Rotation sonrası eski kanıt UI'da kaybolur (EC2-08 bilinçli) |
| Config | Yok | v1 bilinçli; v2+ |

**Journal büyümesi:** Her mutasyon ~1 JSONL satırı; rotation tetiklenince current → `.1`, en eski `.3` silinir. Toplam üst sınır ≈ **4 × 1 MB** (current + 3 rotated) — hard cap değil, rotation anına bağlı.

---

## Seçenekler

### Seçenek 1 — Named constants + read-only policy metadata (SEÇİLDİ)

Davranış değişmez (hâlâ 1 MB × 3); politika görünür ve test edilebilir.

### Seçenek 2 — Config-driven retention (`.lumos/config`)

Operasyonel esneklik; migration, validation, EC2-14 etkisi — **v1 reddedildi**.

### Seçenek 3 — Multi-file tail read (rotated + current)

EC2-08 `read_recent` genişler; EC2-08 regression riski — **v2+ adayı; v1 reddedildi**.

### Seçenek 4 — Docs-only

Politika zaten çalışıyor; metadata yok — **reddedildi** (operasyonel görünürlük düşük).

---

## Minimum v1 uygulama sınırı

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | `EVIDENCE_CONTINUITY_MAX_BYTES`, `EVIDENCE_CONTINUITY_KEEP`; `evidence_retention_policy()`; `evidence_journal_storage_summary()`; append named constants |
| `panel/scripts/panel_tasks_server.py` | `build_evidence_recent_response` → `retention` + `storage` |
| `tests/test_evidence_retention_ec2_09.py` | **Yeni** — T1–T8 |

**Bilerek dokunulmayacak:** `log_rotation.py` default değişikliği, config schema, EC2-08 UI, multi-file read, EC2-06/07/10/11.

---

## Policy DTO (v1)

```json
{
  "policy_id": "lumos.evidence_continuity.retention.v1",
  "max_bytes_per_file": 1000000,
  "rotated_files_kept": 3,
  "max_file_slots": 4,
  "read_scope": "current_file_only"
}
```

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| T1 | `evidence_retention_policy()` | 1 MB, keep 3, policy_id |
| T2 | Append + rotation (küçük max_bytes test) | Named constants kullanılır |
| T3 | Boş journal storage summary | 0 bytes, 0 files |
| T4 | Current + `.1` rotated mevcut | file_count ≥ 2 |
| T5 | `build_evidence_recent_response` | `retention` + `storage` anahtarları |
| T6 | EC2-08 U1–U12 | Regresyonsuz |
| T7 | EC2-14 validate | Journal record şeması değişmez |
| T8 | `read_recent` rotation sonrası | Yalnızca current tail (bilinçli RT6) |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| Config override | RT7 |
| Multi-file UI read | RT6; EC2-08 scope |
| Arşiv / cold storage | P2+ |
| Per-source retention | Karmaşıklık |
| Kalıcı silme otomasyonu | SECURITY_NEVER_AUTO |

---

## Bağımlılıklar

| Belge | İlişki |
|-------|--------|
| [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md) | Read API; rotation UI sınırı |
| [`evidence-continuity-ec2-05-decision.md`](./evidence-continuity-ec2-05-decision.md) | Store merge ayrı |
| EC2-14 | Journal şema — metadata API yanıtında |

---

## Uygulama

**Merge:** PR #280 (`121216d` — `feat/ec2-09-retention-policy`).

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | Named constants; `evidence_retention_policy()`; `evidence_journal_storage_summary()` |
| `panel/scripts/panel_tasks_server.py` | `build_evidence_recent_response` → `retention` + `storage` |
| `tests/test_evidence_retention_ec2_09.py` | T1–T8 |

Config override ve multi-file UI read **v1 uygulanmadı** — RT6/RT7.
