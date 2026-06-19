# Evidence Continuity EC2-04 — Guard/policy journal mirror (onaylı karar)

> **Durum:** `[decision-approved]` — implementasyon PR bekliyor.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 4 (EC2-04); v1 bilinçli boşluk (guard/policy); `record_guard_event` + `log_policy_blocked` read-only keşif (2026-06-19; subagent ae801e02).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md), [`audit-hook-term-decision.md`](./audit-hook-term-decision.md).

**Karar:** **Seçenek A** — guard ve policy **iki ayrı `source`** (`guard_audit` / `action_policy`); merkezi choke-point'lerde (`record_guard_event` H4a, `log_policy_blocked` H4b) journal'a **append-only tek `after` satırı**; guard mirror **yalnızca `deny`**; mevcut Python logging ve `log.txt` **korunur**; `lumos.evidence_continuity.v1` **enum genişlemesi**; `payload_summary` demo-safe alanlar (`action`, `reason_code`, `route`, `title_preview` basename).

**Bağımlılık:** **EC2-03** merge edildi (`b1c48aa`, PR #265) — pattern referansı; EC2-04 için **sert önkoşul değil**. EC2-14 şema CI frozenset güncellemesi implementasyon sırasında regresyonsuz kalmalı.

---

## Karar özeti

**Onaylı karar (firm):** Guard deny ve policy block olayları, mevcut audit kanallarından (Python `lumos.guard` logging; `.lumos/logs/log.txt`) hemen sonra `.lumos/logs/evidence_continuity.jsonl` dosyasına **tek append-only journal satırı** bırakır. Mevcut logging ve `log.txt` semantiği v1'de **değişmez**. Journal satırı `phase: after` only; `result` fazı **EC2-13** kapsamındadır.

**NOT — git audit hook değil:** EC2-04 runtime guard/policy journal mirror'dır. Informal «audit hook» takip maddesi [`audit-hook-term-decision.md`](./audit-hook-term-decision.md) ile **kapatıldı** (OD-059, DL-C01). Yeni pre-commit/post-commit git hook **açılmaz**.

| # | Kural | Durum |
|---|--------|--------|
| GP1 | Mevcut kanallar korunur — Python logging + `log.txt` append kaldırılmaz | `decision-approved` |
| GP2 | Journal append — guard deny / policy block başına tek `after` satırı (H4a/H4b) | `decision-approved` |
| GP3 | Enum **Seçenek A** — `source: guard_audit` + `source: action_policy` (iki kaynak) | `decision-approved` |
| GP4 | Store/operation: `guard` / `guard.decision` ve `policy_log` / `policy.blocked` | `decision-approved` |
| GP5 | Şema sürümü `lumos.evidence_continuity.v1` kalır — **v2 şema yok**; frozenset güncellemesi yeterli | `decision-approved` |
| GP6 | `payload_summary`: `action`, `reason_code`, `route`; guard için ek `title_preview` (path basename) | `decision-approved` |
| GP7 | Tam dosya yolu, token, credential, ham kullanıcı mesajı journal'a **girmez** | `decision-approved` |
| GP8 | Guard mirror **deny-only** — `allow` journal'a yazılmaz (gürültü + re-entrancy) | `decision-approved` |
| GP9 | `phase: result` v1'de **yok** — EC2-13 ayrı madde | `decision-approved` |
| GP10 | Journal hatası guard/policy ana akışını **kırmaz** (best-effort, H0 ilkesi) | `decision-approved` |
| GP11 | Re-entrancy koruması zorunlu — mirror bayrağı + deny-only filtre | `decision-approved` |

---

## Problem / mevcut boşluk

Evidence Continuity v1 yalnızca **panel sunucu (H1)**, **TaskEngine (H2)** ve (EC2-03 sonrası) **köprü outbox (H3)** yazım kapılarında journal bırakır. Guard ve policy hatları farklı, dağınık kanallara yazar; journal semantiği **yoktur**.

### Bugün guard olayları nereye gidiyor?

Merkezi fonksiyon: `src/core/guard_audit.py` → `record_guard_event()`.

| Özellik | Değer |
|---------|--------|
| Depolama | **Disk yok** — yalnızca Python `logging` |
| Logger | `lumos.guard` |
| Seviye | `allow` → INFO, `deny` → WARNING |
| Tasarım niyeti | *«core state'e ek yazma yapmaz»* |

**Çağrı noktaları (yüksek hacim):**

| Modül | Dosya | Senaryo |
|-------|-------|---------|
| Sandbox write guard | `src/core/workspace_contract.py` (`allow_write_to_core`) | Core yazım kontrolünde allow/deny |
| Write interceptor | `src/core/write_interceptor.py` | Direct write allow/deny, protected apply deny |
| Patch lifecycle | `patch_registry.py`, `patch_pipeline.py`, `patch_transaction.py`, `plan_registry.py` | Patch allow/deny kararları |

**Kritik zincir:** `append_evidence_event()` → `allow_write_to_core()` → `record_guard_event(allow)` — her journal append'te bir guard allow logu üretilir (`src/core/evidence_continuity.py`).

**Journal:** `.lumos/logs/evidence_continuity.jsonl` guard satırı **üretmiyor**.

### Bugün policy blocked nereye gidiyor?

Merkezi fonksiyon: `src/policy/action_policy.py` → `log_policy_blocked()`.

| Özellik | Değer |
|---------|--------|
| Depolama | `{base_dir}/logs/log.txt` |
| Format | logfmt: `policy_blocked action=… reason=… ts=…` |
| Tek runtime çağrı yolu | `src/cli/cli_tasks_mutation.py` → `_enforce_task_policy()` |

**Panel:** `panel/scripts/` altında `check_policy` / `log_policy_blocked` **yok**. Legacy panel bellek içi `policy_blocked` tutar; kalıcı depoya yazmaz.

**Köprü:** `packages/kando_bridge/src/kando_bridge/server.py` içinde `record_guard_event` / `log_policy_blocked` **kullanılmıyor**. Gate redleri `lumos_audit` → `.lumos/logs/YYYY-MM-DD.log` — farklı şema.

### Yan kanallar (journal değil — bilinçli ayrım)

| Kanal | Konum | Depolama |
|-------|-------|----------|
| Guard audit | `src/core/guard_audit.py` | Python logging |
| Policy blocked | `src/policy/action_policy.py` | `.lumos/logs/log.txt` |
| Lumos execution audit | `packages/kando_runtime/.../lumos_audit.py` | `.lumos/logs/YYYY-MM-DD.log` |
| Evolution log | `src/core/evolution_log.py` | `logs/lumos_evolution.jsonl` |
| EC journal | `src/core/evidence_continuity.py` | `.lumos/logs/evidence_continuity.jsonl` |

**Kullanıcıya görünür semptom:** CLI'da policy block veya sandbox guard deny yaşandığında `log.txt` veya stderr'de iz bırakılır; evidence continuity journal'da guard/policy hattına ait kayıt **yoktur**. Kopma/devam veya «son kanıt» (EC2-08) guard/policy ekseninde boş kalır.

**v1 bilinçli boşluk (kaynak):** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) — guard/policy v2 normalize; EC2-04 bu boşluğu kapatır.

---

## EC2-03 bağımlılık doğrulaması

| Kontrol | Kanıt |
|---------|--------|
| **EC2-03** merge | `b1c48aa` — PR #265; H3 köprü outbox journal mirror |
| H0 `append_evidence_event` | Hazır — `src/core/evidence_continuity.py` |
| H3 köprü mirror kalıbı | Referans — `mirror_post_task_outbox_to_evidence_journal`; EC2-04 aynı choke-point pattern'i izler |
| Sert sıra | Backlog: EC2-04 EC2-03'ten **bağımsız** başlayabilir; EC2-03 tamamlanmış olması pattern ve Phase 4 sırası açısından avantaj |
| EC2-14 şema CI | Enum + `payload_summary` anahtar genişlemesi frozenset güncellemesi gerekir |

**Sonuç:** EC2-03 **hard blocker değil**; EC2-04 implementasyon PR'ı açılabilir. EC2-03 merge edilmiş olması H3 mirror pattern referansı sağlar.

**EC2-04 sonrası açılanlar:**

```
EC2-04 (guard/policy mirror) ──► EC2-13 (result faz — guard)
EC2-03 + EC2-04 ──► EC2-08 (correlation UI)
EC2-01..04 ──► EC2-12 tam kapsam değeri (guard/policy journal senaryoları)
```

---

## Seçilen yol ve neden bu yol

### Seçilen: merkezi choke-point + append journal (enum Seçenek A, deny-only guard, parallel kanallar korunur)

```
[Guard deny veya policy block]
       │
       ▼
  H4a: record_guard_event (deny only)     H4b: log_policy_blocked
       │                                        │
       ▼                                        ▼
  mirror_guard_event_to_evidence_journal   mirror_policy_blocked_to_evidence_journal
       │                                        │
       └────────────────┬───────────────────────┘
                        ▼
  append_evidence_event (H0) ──► evidence_continuity.jsonl (append-only, tek after satırı)
       │
       ├──► (mevcut) Python logging / log.txt — korunur
       └──► best-effort: journal hatası ana akışı kırmaz
```

**Neden H4 choke-point:**

1. **Tek sorumluluk** — `record_guard_event` ve `log_policy_blocked` zaten merkezi; 30+ dağınık çağrı noktasına hook eklemek bakım yükü üretir.
2. **EC2-03 kalıbı** — H3 köprü mirror ile aynı «choke-point → builder → H0» akışı; Phase 4 tutarlılığı.
3. **Truth kuralı** — journal yalnızca sunucu/runtime sürecinden üretilir; istemci journal'a yazmaz (EC2-02 ile hizalı).

**Neden deny-only guard:**

1. **Re-entrancy** — `append_evidence_event` → `allow_write_to_core` → `record_guard_event(allow)` zinciri; allow mirror journal patlaması riski.
2. **Gürültü** — Her core yazımda allow guard logu üretilir; continuity değeri deny olaylarında yoğunlaşır.
3. **v1 kapsam** — Policy block zaten düşük hacimli ve tamamı mirror edilir; guard tarafında simetri gerekmez.

**Neden parallel kanallar korunur:**

1. Mevcut `test_guard_audit.py`, `test_action_policy.py` ve e2e beklentileri kırılmaz.
2. Operasyonel teşhis (stderr, `log.txt`) journal'dan bağımsız kalır.
3. EC2-03 outbox overwrite + journal append pattern'i ile uyumlu — outbox/logging silinmez.

**Neden Seçenek A (iki source):**

| Sabit | Değer |
|-------|-------|
| `SOURCE_GUARD_AUDIT` | `"guard_audit"` |
| `STORE_GUARD` | `"guard"` |
| `OPERATION_GUARD_DECISION` | `"guard.decision"` |
| `SOURCE_ACTION_POLICY` | `"action_policy"` |
| `STORE_POLICY_LOG` | `"policy_log"` |
| `OPERATION_POLICY_BLOCKED` | `"policy.blocked"` |

Teşhis netliği: `source` alanından guard vs policy ayrımı tek bakışta görülür; EC2-08 correlation UI ve EC2-13 `result` faz ayrımı için avantaj.

---

## Re-entrancy stratejisi

**Problem:** `append_evidence_event` içinde `allow_write_to_core` çağrılır; bu `record_guard_event(allow)` üretir. Mirror doğrudan `record_guard_event` içinde filtresiz yapılırsa sonsuz veya birikimli journal üretimi riski vardır.

**v1 çözüm (üç katman):**

| Katman | Mekanizma |
|--------|-----------|
| 1 | **Deny-only filtre** — yalnızca `event.decision == "deny"` mirror tetikler |
| 2 | **Mirror bayrağı** — thread-local `_EVIDENCE_MIRROR_ACTIVE` (veya eşdeğeri); mirror sırasında guard journal çağrısı atlanır |
| 3 | **Best-effort** — mirror hatası `record_guard_event` / `log_policy_blocked` dış davranışını değiştirmez |

**Doğrulama:** T4 — panel/engine journal append simülasyonunda guard allow log var; journal'da guard allow satırı **yok**; re-entrancy patlaması yok.

---

## Reddedilen alternatifler

| Alternatif | Red gerekçesi |
|------------|---------------|
| **Git pre-commit/post-commit audit hook** | [`audit-hook-term-decision.md`](./audit-hook-term-decision.md) AH1 — OD-059 reddi |
| **Her `record_guard_event` çağrı noktasında ayrı hook** | 30+ çağrı; bakım yükü; H4 choke-point daha dar |
| **Tüm guard allow mirror** | Gürültü + `append_evidence_event` re-entrancy |
| **`log.txt` / Python logging kaldırma** | Parallel truth; mevcut test/e2e kırılır |
| **`lumos_audit` / köprü gate journal'a merge** | Farklı şema; EC2-03 köprü `after` yeterli v1; kapsam genişlemesi |
| **`phase: result` EC2-04'te** | EC2-13 scope; guard/policy anlık deny/block |
| **Şema sürümü `lumos.evidence_continuity.v2`** | Backlog «v1 şema» hedefi; enum genişlemesi yeterli |
| **Seçenek B — tek source `guard_runtime`** | Teşhiste bir adım daha az net; Seçenek A firm |
| **Panel `policy_blocked` bellek → journal** | Client truth kuralı ihlali; EC2-02 reddi pattern |
| **Tam dosya yolu journal'da** | Demo-safe / public boundary ihlali |
| **İstemciden doğrudan journal append** | EC2-02 reddi; truth kuralı |
| **`POST /evidence/guard` yeni endpoint** | EC2-02 pattern reddi; public yüzey genişler |

---

## Minimum v1 tasarım

### Hook katmanı

| Katman | Rol |
|--------|-----|
| **H0** | `append_evidence_event` — mevcut (`src/core/evidence_continuity.py`) |
| **H4a** | `record_guard_event` sonunda — `decision == "deny"` only |
| **H4b** | `log_policy_blocked` sonunda — her policy block |

**Builder fonksiyonlar** (`src/core/evidence_continuity.py`):

- `mirror_guard_event_to_evidence_journal(event, *, base_dir=…)`
- `mirror_policy_blocked_to_evidence_journal(base_dir, action, reason)`

### Enum sabitleri (`evidence_continuity.py`)

`SOURCES`, `STORES`, `OPERATIONS` frozenset'lerine eklenir. `PAYLOAD_SUMMARY_ALLOWED_KEYS` genişlemesi: `action`, `reason_code`. `PHASE_RESULT` tanımlı kalır; EC2-04 v1'de **kullanılmaz**.

### Journal kaydı — alan kuralları

| Alan | Guard deny | Policy block |
|------|------------|--------------|
| `schema` | `lumos.evidence_continuity.v1` | aynı |
| `phase` | **`after` only** | **`after` only** |
| `outcome` | `error` | `error` |
| `source` | `guard_audit` | `action_policy` |
| `store` | `guard` | `policy_log` |
| `operation` | `guard.decision` | `policy.blocked` |
| `correlation_id` | Yeni UUID v4 / olay | Yeni UUID / olay |
| `mutation` | **omit** | **omit** |
| `entity_ref` | **omit** v1 | **omit** v1 |
| `error.code` | `reason_code` veya kısa kod | `reason` (offline_mode vb.) |
| `error.message` | Kısa, secret yok | Kısa, secret yok |
| `payload_summary` | `action`, `reason_code`, `route`, `title_preview`(basename) | `action`, `reason_code`, `route` |

**`payload_summary` demo-safe kuralları:**

| Anahtar | Guard deny | Policy block |
|---------|------------|--------------|
| `action` | `write`, `patch`, `delete`… (`GuardEvent.action`) | `create_task`, `delete_task`… |
| `reason_code` | `core_state_under_live_base`, `DIRECT_WRITE_ATTEMPT_…` | `offline_mode`, `koruma_aktif_delete` |
| `route` | `GuardEvent.caller` (≤80 char) | `"cli:task_mutation"` (sabit) |
| `title_preview` | Path **basename** only (≤40 char) | omit |

**Örnek journal satırı (guard deny):**

```json
{
  "schema": "lumos.evidence_continuity.v1",
  "ts": "2026-06-19T20:00:00.000Z",
  "correlation_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "source": "guard_audit",
  "store": "guard",
  "operation": "guard.decision",
  "phase": "after",
  "outcome": "error",
  "error": {
    "code": "core_state_under_live_base",
    "message": "sandbox core write denied"
  },
  "payload_summary": {
    "action": "write",
    "reason_code": "core_state_under_live_base",
    "route": "workspace_contract.allow_write_to_core",
    "title_preview": "tasks.json"
  }
}
```

**Örnek journal satırı (policy block):**

```json
{
  "schema": "lumos.evidence_continuity.v1",
  "ts": "2026-06-19T20:01:00.000Z",
  "correlation_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  "source": "action_policy",
  "store": "policy_log",
  "operation": "policy.blocked",
  "phase": "after",
  "outcome": "error",
  "error": {
    "code": "offline_mode",
    "message": "policy blocked"
  },
  "payload_summary": {
    "action": "create_task",
    "reason_code": "offline_mode",
    "route": "cli:task_mutation"
  }
}
```

### `base_dir`

Journal: `lumos_base_dir()` veya çağrı bağlamındaki `base_dir` — policy mirror `log_policy_blocked` ile aynı kök. Guard mirror için `lumos_base_dir()` tercih edilir (panel H1 ile hizalı).

### Best-effort

Panel H1 / EC2-03 BM9 ile aynı ilke: journal hatası guard/policy ana akışını **kırmamalı** (`append_evidence_event` raise etmez).

---

## Değişecek dosyalar (gelecek implementasyon — şimdi yapılmaz)

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | Enum sabitleri; `PAYLOAD_SUMMARY` genişlemesi (`action`, `reason_code`); `mirror_guard_event_*`, `mirror_policy_blocked_*` builder'lar; re-entrancy bayrağı |
| `src/core/guard_audit.py` | H4a: deny sonrası journal mirror + re-entrancy guard |
| `src/policy/action_policy.py` | H4b: `log.txt` sonrası journal mirror |
| `tests/test_guard_policy_evidence_ec2_04.py` | **Yeni** — guard/policy + journal entegrasyon (T1–T10) |
| `tests/test_evidence_continuity.py` | Yeni enum + payload anahtar validator testleri |
| `tests/test_guard_audit.py` | Deny → journal satırı; allow → journal yok |
| `tests/test_action_policy.py` | Policy block → journal + `log.txt` korunur |

**Bilerek dokunulmayacak (v1):**

- `packages/kando_bridge/src/kando_bridge/server.py` — EC2-03 tamam; köprü gate audit ayrı kanal
- `panel/js/app.js`, `panel/scripts/panel_tasks_server.py` — panel memory policy kapsam dışı
- `packages/kando_runtime/.../lumos_audit.py` — execution audit farklı şema
- `packages/kando_policy/` — ölü ayna; runtime `src/policy/` kullanır
- Git hook / `.githooks/`
- Köprü gate `append_audit_log` normalize

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| T1 | İzole `tmp_path`: sandbox deny (`allow_write_to_core`, core path) | 1 journal satırı; `source: guard_audit`, `outcome: error` |
| T2 | Guard allow (`decision: allow`) | Journal satırı **yok** |
| T3 | CLI policy block (`log_policy_blocked`) | Journal + `log.txt` satırı; `source: action_policy` |
| T4 | `append_evidence_event` (panel/engine simülasyonu) | Guard allow log var; journal'da guard allow **yok**; re-entrancy patlaması yok |
| T5 | Guard deny payload | Tam path journal'da **yok**; basename `title_preview` |
| T6 | Her journal satırı | `validate_evidence_record(rec) == []` |
| T7 | İki ardışık policy block | `log.txt` 2 satır; journal **2 append** satırı |
| T8 | Enum frozenset + yeni payload anahtarları | EC2-14 / `test_evidence_continuity` regresyonsuz |
| T9 | Mevcut `test_guard_audit.py` / `test_action_policy.py` | Logging + `log.txt` davranışı korunur |
| T10 | `tests/test_bridge_post_task_evidence_ec2_03.py` | Köprü mirror (EC2-03) regresyonsuz |

**Doğrulama kanalları:** pytest + `evidence_continuity_path(tmp_path)` okuma; mevcut caplog testleri.

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| **Re-entrancy döngüsü** | Journal patlaması | Deny-only + mirror bayrağı |
| **Allow guard gürültüsü** | Her core yazımda journal satırı | v1'de allow mirror yok |
| **Tam path sızıntısı** | Public boundary | Basename-only `title_preview` |
| **Enum vs EC2-14** | CI validator reddi | frozenset + `test_evidence_continuity` güncelle |
| **Panel policy boşluğu** | UI block journal'da görünmez | Bilinçli v1; EC2-08/01 |
| **Parallel kanal karmaşası** | log.txt + logging + journal | Mevcut kanallar korunur; journal continuity birincil |
| **`packages/kando_core/guard_audit.py` ayna** | Drift | Runtime `core.guard_audit` import eder; tek kaynak `src/core/` |
| **`correlation_id` kopukluğu** | Guard deny ↔ task ↔ köprü zinciri UI'da görünmez | Bilinçli v1; EC2-08 correlation UI |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **`phase: result` / async tamamlanma** | EC2-13 — guard/policy ayrı lifecycle |
| **Köprü gate / `lumos_audit` normalize** | Farklı şema; EC2-03 köprü `after` yeterli v1 |
| **Panel bellek içi `policy_blocked` → journal** | Client truth; EC2-02 reddi pattern |
| **Tüm guard allow mirror** | Gürültü + re-entrancy |
| **`log.txt` / Python logging kaldırma** | Parallel truth |
| **Tam dosya yolu journal'da** | Demo-safe ihlali |
| **Git audit hook** | OD-059 reddi |
| **`entity_ref` / `tsk_*` guard journal'da** | Guard deny task store mutasyonu değil |
| **Correlation UI** | EC2-08 — yeterli journal kaynağı gerekir |
| **Şema sürümü v2** | Enum genişlemesi yeterli |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) | Guard/policy v1 dışı idi; H0/H1/H2 |
| [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) | EC2-04 Phase 4; P1 |
| [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md) | H3 mirror pattern referansı |
| [`audit-hook-term-decision.md`](./audit-hook-term-decision.md) | EC2-04 ≠ git hook; OD-059 |
| EC2-03 merge `b1c48aa` / PR #265 | Köprü mirror — pattern, hard blocker değil |
| EC2-14 / PR #255 | Şema CI — enum genişlemesi regresyonsuz kalmalı |
| EC2-13 | `result` faz — guard tarafı EC2-04 sonrası |

---

## Sonraki adım

1. **Dar implementasyon PR** — yalnızca bu belgedeki dosya listesi ve T1–T10 test planı.
2. **Backlog senkron:** v2 backlog EC2-04 → `[decision-approved]` ✓.
3. **Phase 4 kalan:** EC2-13 (`result` faz), EC2-08 (correlation UI).

---

**İndeks notu:** EC2-04 ayrı OD kaydı açmaz; v2 backlog + bu belge canonical. `docs/decision-log.md` DL-A05 satırı ile senkron.

---

Son güncelleme: 2026-06-19 (`[decision-approved]`)
