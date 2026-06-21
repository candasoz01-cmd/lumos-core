# SECURITY_NEVER_AUTO — P2 task engine analizi, helper önerisi, action_risk akışı

| Alan | Değer |
|------|-------|
| Durum | **Analiz-only** — uygulama yok |
| Tarih | 2026-06-21 |
| Referans | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [branch scan](lumos-security-never-auto-branch-scan.md), `src/task_engine/profiles.py`, `src/task_engine/engine.py` |
| Kapsam | Öneri ve gap haritası; **kod enforcement yok** |

## Özet

`SECURITY_NEVER_AUTO` dört üyeli sözleşme kümesi (`permanent_delete`, `external_write`, `irreversible_user_op`, `critical_system_config`) `profiles.py` ve `inviolable.py` içinde sabit. P0/P1 panel yolları #444–#446 ile kapandı. **P2:** TaskEngine `run_task` içinde küme üyelerine özel branch yok; `external`/`critical` step türleri matris üzerinden duruyor; üç üye (`external_write`, `irreversible_user_op`, `critical_system_config`) step `kind` veya action policy ile **doğrudan bağlı değil**. Bu belge yalnızca hook noktalarını, mevcut davranışı, helper taslağını ve ADR-012 karar katmanı akışını kaydeder.

---

## Bölüm 1 — P2: TaskEngine `run_task` branch analizi

### 1.1 Küme tanımı (kaynak)

```47:52:src/task_engine/profiles.py
SECURITY_NEVER_AUTO = frozenset({
    "permanent_delete",      # kalıcı silme
    "external_write",        # dış servislere kontrolsüz yazma
    "irreversible_user_op",  # kullanıcı adına geri dönüşsüz işlem
    "critical_system_config", # kritik sistem ayarı değişikliği
})
```

Bu stringler **step `kind` değildir**; sözleşme / inviolable sabitleridir. `STEP_PERMISSION_MATRIX` yalnızca `analyze`, `read`, `plan`, `safe_local`, `write_local`, `external`, `critical` türlerini bilir.

### 1.2 Bugün ne enforce ediliyor?

| Üye | Mevcut koruma | Yeterlilik |
|-----|---------------|------------|
| `permanent_delete` | `TaskStore.delete()` → `may_perform_permanent_delete(user_initiated)`; panel `delete-permanent` #445 | Store/CLI/panel yolu; engine adım executor'ına map yok |
| `external_write` | Dolaylı: `STEP_TYPE_EXTERNAL` → `DECISION_LAYER_NEVER`; `ActionRegistry` external/critical red; offline_engine | Step `kind=external` ile sınırlı; ayrı `external_write` action/kind yok |
| `irreversible_user_op` | Dolaylı: `STEP_TYPE_CRITICAL` never layer; bridge/cursor yüksek risk gate (ayrı modül) | Sözleşme terimi engine'de lookup yok |
| `critical_system_config` | Dolaylı: `critical` step + `change_sensitivity` CRITICAL etiket (gate kopuk) | Config intent sınıflandırması yok |

**`run_task` guard zinciri:**

```479:486:src/task_engine/engine.py
    def _is_step_allowed_runtime(self, step: TaskStep) -> bool:
        return may_execute_step_at_runtime(
            self.permission_profile, step.kind, self.general_approval
        )
```

`may_execute_step_at_runtime` → `get_decision_layer(step_type) == DECISION_LAYER_NEVER` ise red; aksi halde `is_allowed_for_profile`. **`SECURITY_NEVER_AUTO` kümesine doğrudan bakmaz.**

**ActionRegistry savunması** (executor seviyesi):

```60:62:src/task_engine/action_registry.py
        if kind in (STEP_TYPE_EXTERNAL, STEP_TYPE_CRITICAL):
            return False, "", "Bu adım türü yürütülmez (güvenlik).", False
```

### 1.3 Olası hook noktaları (öneri — uygulanmadı)

| Konum | Ne yapılabilir (gelecek) | Risk |
|-------|---------------------------|------|
| `engine.py` `_is_step_allowed_runtime` | Step metadata / action tag → `is_security_never_auto(tag)` red | Yanlış tag → false positive; profil matrisi ile çift guard |
| `engine.py` `run_task` döngüsü (L512 öncesi) | Ayrı `SECURITY_NEVER_AUTO` branch + `EVENT_POLICY_BLOCKED` + `block_reason=security_never_auto` | Kapsam genişlemesi; ADR-006 bilinçli erteleme |
| `engine.py` `_execute_step` / `ActionRegistry.execute` | Executor kaydı öncesi action alanı kontrolü | Eylem alanı × step kind drift |
| `profiles.py` yeni step türleri | `external_write` vb. için ayrı `STEP_TYPE_*` | Matris + inviolable + test genişlemesi; breaking change |
| `action_policy.py` | Yeni action sabitleri (`EXTERNAL_WRITE`, …) panel/CLI gate | Policy katmanı genişler; profil matrisinden bağımsız ikinci kaynak |

**Önerilen sıra (onay sonrası, dar PR):**

1. Önce **sözleşme → step kind / action tag** eşleme tablosu docs + test (davranış değişmez).
2. Sonra yalnızca **tanımlı tag taşıyan adımlar** için engine red branch (feature flag veya env ile).
3. `permanent_delete` engine adımı eklenmeyecek — kalıcı silme yalnızca `TaskStore.delete(user_initiated=True)` ve panel onaylı endpoint (#445).

### 1.4 Gap özeti (P2)

- Küme üyelerinin dördü de `run_task` içinde **tek bir SECURITY_NEVER_AUTO branch'inde toplanmıyor**.
- `external_write`, `irreversible_user_op`, `critical_system_config` için **runtime lookup yok**; yalnızca `external`/`critical` step türleri ve dağınık modül guard'ları.
- CLI `general_approval` ↔ policy `consent` semantik karışımı (scan P2) codex C3 drift riski taşıyor — ayrı dar PR adayı, bu belgede uygulanmaz.

---

## Bölüm 2 — `is_security_never_auto()` helper önerisi (tasarım only)

### 2.1 Tek lookup API taslağı

```python
# ÖNERİ — profiles.py içinde veya security/policy modülünde; ŞU AN UYGULANMAZ

def is_security_never_auto(
    *,
    step_kind: str | None = None,
    action_tag: str | None = None,
    policy_action: str | None = None,
) -> bool:
    """
    Sözleşme kümesi üyeliği — profil/genel onaydan bağımsız.
    En az bir tanımlı girdi eşleşmeli; bilinmeyen girdi False (fail-open değil: explicit tag gerekir).
    """
    candidates: set[str] = set()
    if step_kind:
        candidates.add(_normalize(step_kind))
    if action_tag:
        candidates.add(_normalize(action_tag))
    if policy_action:
        candidates.add(_normalize(policy_action))
    return bool(candidates & SECURITY_NEVER_AUTO)
```

**Eşleme tablosu (docs-only, kod yok):**

| Girdi türü | Örnek değer | Küme üyesi |
|------------|-------------|------------|
| `step_kind` | `critical` | dolaylı (never layer; küme üyesi değil) |
| `action_tag` | `permanent_delete` | doğrudan |
| `policy_action` | (henüz yok) | gelecek: `permanent_delete_task` vb. |

### 2.2 Kullanıcı olabilecek call site'lar (gelecek)

| Call site | Amaç | Bugün alternatif |
|-----------|------|------------------|
| `TaskEngine._is_step_allowed_runtime` | Step metadata tag red | `may_execute_step_at_runtime` |
| `TaskStore.delete` | Tek satır sözleşme assert | `may_perform_permanent_delete` |
| `panel_tasks_server` kalıcı silme | Policy + küme birleşik mesaj | #445 `check_policy` + confirm |
| `action_policy.check_policy` | Yeni action → küme | Hardcoded action list |
| `write_interceptor` / bridge | Dış yazma tag | Regex + risk gate (cursor_bridge) |
| Test / `inviolable.verify_core_constants` | Küme bütünlüğü | Mevcut `EXPECTED_SECURITY_NEVER_AUTO` |

### 2.3 Neden şimdi uygulanmamalı

1. **Çift guard riski:** `may_execute_step_at_runtime` + helper aynı adımda tutarsız sonuç üretebilir.
2. **Eşleme eksik:** Küme üyelerinin step kind karşılığı resmi değil; helper erken eklenirse **sahte güven** (helper True dönmeyen ama riskli yollar).
3. **ADR-006 bilinçli gap:** Engine tam branch bilinçli ertelendi; helper tek başına gap'i kapatmaz.
4. **Public OSS sınırı:** Geniş enforcement davranış değişikliği ayrı onay + test + CI gerektirir.
5. **Fail-open / fail-close:** API tasarımı (bilinmeyen tag → False) yanlış uygulanırsa sessiz izin verebilir.

### 2.4 Uygulama öncesi koşullar (onay checklist)

- [ ] Eylem alanı × küme üyesi eşleme tablosu ADR-012 companion'da kilitlendi
- [ ] Her call site için mevcut guard ile **equivalence test** tanımlandı
- [ ] Panel + CLI + engine için ayrı dar PR'lar planlandı
- [ ] Kullanıcı açık onayı: "core enforcement uygula" (bu backlog turunda **yok**)

---

## Bölüm 3 — action_risk akışı: rapor → onay → kod yolu (ADR-012)

ADR-012 C3 ve `lumos-karar-sozlesmesi.md` karar katmanları ile runtime yolların karşılaştırması.

### 3.1 Hedef zincir (codex)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Rapor/      │ ──► │ Öneri/plan   │ ──► │ Kullanıcı onayı │ ──► │ Kod yürütme  │
│ analiz      │     │ (taslak)     │     │ (açık/genel)    │     │ (profil içi) │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
     rapor              plan/suggest      genel onay /            safe_local /
     analyze/read       öner ama bekle    passphrase /            write_local
                                           açık komut              (kisitli_otonom)
                                                                    ───────────► ASLA: external,
                                                                                 critical,
                                                                                 SECURITY_NEVER_AUTO
```

### 3.2 Mevcut kod yolu (bugün)

| Aşama | Codex katmanı | Kod girişi | Enforcement |
|-------|---------------|------------|-------------|
| **Rapor** | Sadece cevap / analiz | CLI `durum`, `gorevler`; profil `rapor`; step `analyze`/`read` | ✓ `may_execute_step_at_runtime` izinli |
| **Öneri** | Öner ama bekle | step `plan`; Brain pending intent | ✓ Uygulama adımı yok; write_local genel onay kapalıyken durur |
| **Onay** | Açık onayla uygula | `general_approval`; live_brain consent phrase; panel `/lumos-consent` | Kısmi — CLI policy `consent` = `general_approval[0]` (drift); panel policy #443–#446 |
| **Kod yolu** | Uygulama | `TaskEngine.run_task` → `_execute_step` → `ActionRegistry` | ✓ Profil matrisi + registry external/critical red |
| **Asla** | SECURITY_NEVER_AUTO | `TaskStore.delete(user_initiated)`; panel delete-permanent #445 | Kısmi — küme üyelerinin 3'ü engine'de ayrı branch yok |

**Policy katmanı (eylem düzeyi, step kind'dan bağımsız):**

| Action | Gate | Dosya |
|--------|------|-------|
| `create_task` … `cancel_task` | offline red | `action_policy.check_policy` |
| `delete_task` | koruma+delete red | aynı |
| Panel mutasyonları | `task_action_gate` → `check_policy` | `panel_bridge_state.py` (#443+) |

### 3.3 Desired vs current (ADR-012)

| Beklenti (ADR-012) | Bugün | Gap |
|--------------------|-------|-----|
| Rapor profili hiç uygulama yapmaz | ✓ Matris | — |
| Genel onay olmadan write_local yok | ✓ Engine guard | CLI consent eşlemesi net değil |
| Panel = CLI policy zinciri | ✓ #443–#446 | Profil matrisi panelde yok (yalnızca policy) |
| Riskli işlemde dur + kanıt | ✓ `EVENT_POLICY_BLOCKED`, evidence | Trust motor (ADR-007) eksik |
| SECURITY_NEVER_AUTO tüm yollar | Parçalı | P2 engine branch; helper yok |
| action_risk sınıflandırması birleşik | Dağınık | cursor_bridge risk_level; action_policy risk yok; tek `action_risk` modülü **yok** |

**Not:** Repoda `action_risk` adlı sembol yok. Codex anlamında **action_risk flow** = karar katmanları + policy + profil matrisi + (gelecek) birleşik risk etiketi. Hedef: ADR-007 trust sinyalleri + ADR-006 firewall tablosu ile birleşik `action_risk` sınıfı — **Faz 4**, bu turda uygulanmaz.

### 3.4 Önerilen docs-only sonraki adım (onay gerekir)

1. `lumos-action-permission-matrix.md` panel satırını #443–#446 ile güncelle (bu PR'da yapıldı).
2. Ayrı onay: `action_risk` terimini ADR-010 glossary'ye ekle (terminoloji PR).
3. Core enforcement: P2 engine branch veya `is_security_never_auto()` — **ayrı açık onay**.

---

## İlgili belgeler

- [lumos-security-never-auto-branch-scan.md](lumos-security-never-auto-branch-scan.md) — P0/P1 kapandı (#444–#446)
- [lumos-runtime-enforcement-map.md](lumos-runtime-enforcement-map.md) — panel gate güncellendi
- [ADR-012](../decisions/ADR-012-lumos-security-codex.md) — checkpoint tablosu

## Disiplin

Bu belge **analyze-only**. `profiles.py`, `engine.py`, LockState, trust motor ve panel davranışına **dokunulmadı**.
