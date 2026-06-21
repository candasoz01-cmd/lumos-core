# PR-W1-05 Readiness — Gate/Dispatch Consume Wiring (Risk Path)

| Alan | Değer |
|------|-------|
| **Belge türü** | Readiness discovery (analysis only) |
| **Tarih** | 2026-06-21 |
| **Durum** | Plan — kod/PR/enforcement uygulaması yok |
| **Kapsam PR** | PR-W1-05 (ADR-012 Wave 1, Madde 1 — PR-C6) |
| **Referans plan** | [adr-012-wave1-execution-plan.md](adr-012-wave1-execution-plan.md) § PR-W1-05 |
| **Referans sıra** | [adr-012-implementation-sequence.md](adr-012-implementation-sequence.md) § Madde 1, PR-1c (kısmi) |
| **Teknik borç** | [td-02](technical-debt-dependency-graph.md#td-02-bridge-cu4-gap), [td-08](technical-debt-dependency-graph.md#td-08-parallel-pending-stores) |
| **Merged bağlam** | #491 (W1-01 bridge characterization), #492 (W1-03 consume/validate characterization) |
| **Hariç** | `lumos_gate_execute` resume (~L2617+), köprü approve handler, `cursor_bridge` — PR-W1-06 |

---

## 1. Executive summary

### PR-W1-05 ne yapacak

PR-W1-05, Madde 1 (PR-C6) zincirinde **shadow CU4 grant yazımından approve-yürütme tarafında consume zincirine geçişin ilk dilimidir**. Hedef:

- **High-risk** pending yolunda (`lumos_gate`): onaylı yürütme executor'ında (`execute_approved_pending_record`, ~L2550+) PR-W1-03 yardımcı sınırı ile `check_confirmation` / `consume_confirmation` entegrasyonu.
- **Medium-risk dispatch** yolunda (`task_dispatch`): onaylı yürütme executor'ında (`execute_approved_dispatch_pending`, ~L507+) aynı yardımcı sınırının tüketilmesi.
- Pending **oluşturma** yolları (`attach_bridge_pending_confirmation` — `lumos_gate` ~L1161–1168, `task_dispatch` ~L695–706) shadow grant yazmaya devam eder; W1-05 bu bölgeleri consume wiring bağlamında dokunma hedefi olarak işaretler, asıl davranış değişikliği **approve executor** katmanındadır.
- `LUMOS_CONFIRMATION_ENABLED=true` iken env-on consume kanıtı; high vs medium şema ayrımının korunması.

Kaynak: wave plan PR-W1-05 amaç, dosyalar, testler; execution-map td-02 § "Consume/validate … ardından handler entegrasyonu".

### PR-W1-05 ne yapmayacak (açık sınır)

| Alan | W1-05 | W1-06 |
|------|-------|-------|
| `lumos_gate_execute` resume (~L2617+) | **Dokunulmaz** | Wiring hedefi |
| `kando_bridge/server.py` `_handle_approve` (~L2230–2290) | Doğrudan wiring hedefi değil* | Birincil wiring |
| `src/kando/cursor_bridge.py` (~L720+) | Dokunulmaz | Wiring hedefi |
| Legacy `approval_token` deprecate/migration kararı | Dokunulmaz | Geçiş süresi / ikili destek |
| `LUMOS_CONFIRMATION_ENABLED` default-on (Madde 5) | Dokunulmaz | Wave 2+ |
| P2 / `SECURITY_NEVER_AUTO` (Madde 2) | Dokunulmaz | PR-W1-04/07 |

\* Bridge handler bugün `execute_approved_*` çağırır; W1-05 executor içine consume eklerse handler dosyası değişmeden dolaylı etki oluşabilir — bu **kasıtlı ara dilim** olabilir; W1-06 handler'ı doğrudan CU4 zincirine hizalar.

### Madde 1 exit vs W1-05 done

Madde 1 tam exit (`PR-W1-06`): köprü approve/resume + `lumos_gate_execute` + panel/CLI ile aynı CU4 store. **W1-05 done** yalnızca gate/dispatch **risk path executor consume** dilimini kapatır; RB-02 ve codex PR-C6 checkpoint **henüz kapanmaz**.

---

## 2. Etkilenen dosyalar

| Yol | Satır / sembol (mevcut) | Planlanan değişiklik türü | Not |
|-----|-------------------------|---------------------------|-----|
| `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | ~L1161–1168 `_return_high_risk_pending` → `attach_bridge_pending_confirmation` | **Okuma / sınır** — shadow yazım bölgesi; W1-05 birincil edit hedefi değil | #491 karakterize |
| `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | ~L2522–2547 `validate_pending_for_approval` | **Genişlet (planlı)** — W1-03 helper delegasyonu veya consume öncesi validate hizası | Mevcut inline validate |
| `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | ~L2550–2614 `execute_approved_pending_record` | **Uygulama (planlı)** — consume wiring birincil hedef | Bridge high-risk approve executor |
| `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | ~L2617+ `lumos_gate_execute` | **Dokunma yok** | W1-06 |
| `packages/kando_runtime/src/kando_runtime/task_dispatch.py` | ~L695–706 `_persist_medium_dispatch_pending` → `attach_bridge_pending_confirmation` | **Okuma / sınır** — shadow yazım | #491/#492 |
| `packages/kando_runtime/src/kando_runtime/task_dispatch.py` | ~L477–505 `validate_dispatch_pending_for_approval` | **Genişlet (planlı)** | Medium şema validate |
| `packages/kando_runtime/src/kando_runtime/task_dispatch.py` | ~L507–608 `execute_approved_dispatch_pending` | **Uygulama (planlı)** — consume wiring birincil hedef | Bridge medium dispatch executor |
| `src/policy/confirmation_policy.py` | `attach_bridge_*`, `consume_confirmation`, `check_confirmation` | **Tüketim (planlı)** — W1-03 bridge yardımcıları buradan çağrılır | W1-03 merge ön koşul |
| `packages/kando_bridge/src/kando_bridge/server.py` | ~L2273–2360 `_handle_approve` | **Dokunma yok (W1-05)** | W1-06; #492 gap dokümante |
| `tests/test_bridge_confirmation_adapter.py` | shadow → consume geçiş senaryoları | **Genişlet** | #491 taban |
| `tests/test_task_dispatch.py` | dispatch pending + `execute_approved_dispatch_pending` | **Genişlet** | Mevcut ~L208–256 shadow korelasyon |
| `tests/test_lumos_plan_substep_gate.py` | `approval_granted`, substep gate | **Regresyon genişlet** | Gate plan yolu |
| `tests/test_persona_security_simdi_checkpoint.py` | `run_lumos_gate` policy/gate | **Regresyon** | Persona checkpoint |
| `tests/test_bridge_approve_contract.py` | #491 legacy matris | **Okuma** — W1-05 sonrası güncelleme W1-06 ile overlap | Shadow grant unconsumed bugün |
| `tests/test_bridge_consume_validate_characterization.py` | #492 td-02 gap | **Okuma / kısıt kaynağı** | Approve handler consume yok |
| `tests/test_confirmation_policy.py` | consume/check env davranışı | **Okuma** — side-effect sırası kısıtı | W1-03 karakterizasyon |

---

## 3. Bağımlılıklar

### Zorunlu ön koşullar (merge)

| Ön koşul | Durum (repo okuma) | W1-05 için anlam |
|----------|-------------------|------------------|
| **#491 / PR-W1-01** | `tests/test_bridge_approve_contract.py` — legacy token matrisi, cross-store id/hash, high vs dispatch şema | Approve sözleşmesi sabit; W1-05 executor consume bu kısıtlara uymalı |
| **#492 / PR-W1-03 (karakterizasyon)** | `tests/test_bridge_consume_validate_characterization.py` — handler consume yok, validate-before-consume, execute hatasında grant korunur | Gap ve side-effect sırası kanıtı |
| **PR-W1-03 (uygulama — wave plan)** | `confirmation_policy.py` içinde **ayrı bridge consume/validate yardımcıları planlanmış**; grep ile **henüz yok** — yalnızca `attach_bridge_*` + genel `consume_confirmation` | **Blocker:** wave plan ön koşulu "W1-03 merge"; #492 tek başına yeterli değil |

### Blokladığı maddeler

- **PR-W1-06** — approve handler + `lumos_gate_execute` resume + cursor_bridge (Madde 1 exit PR).
- Dolaylı: **PR-W1-04**, **PR-W1-07** — kullanıcı sırası 1→2; W1-06 tamamlanmadan P2 uygulama merge edilmemeli.

### W1-03 karakterizasyon vs tam wiring PR

| Boyut | #492 (W1-03 karakterizasyon) | PR-W1-03 (plan — uygulama) | PR-W1-05 |
|-------|------------------------------|----------------------------|----------|
| Runtime değişiklik | Yok | `confirmation_policy` + `server.py` delegasyon | `lumos_gate` + `task_dispatch` executor consume |
| Test | `test_bridge_consume_validate_characterization.py` | `test_confirmation_policy`, adapter, approve contract genişletme | Gate/dispatch executor + regresyon |
| td-02 gap kapanışı | Gap **belgelenir** | Yardımcı sınır **sağlanır** | Risk path **ilk consume wiring** |
| Bridge handler | consume yok (grep sözleşmesi) | Handler henüz tam wiring değil (plan) | Dolaylı etki mümkün; doğrudan handler W1-06 |

---

## 4. #491 ve #492 ilişkisi

### #491 (W1-01) — W1-05'i kısıtlayan davranışlar

| Test / davranış | Dosya | W1-05 kısıtı |
|-----------------|-------|--------------|
| Legacy `approval_token` red matrisi (eksik/yanlış/used) | `test_bridge_approve_contract.py` | Token yolu W1-06'ya kadar korunmalı; consume wiring token doğrulamasını kırmamalı |
| `test_dispatch_approve_valid_token_executes_without_cu4_consume` | aynı | **Mevcut karakterizasyon:** approve sonrası shadow grant `consumed: false`; W1-05 bu testi **consume=true** yönünde güncellemeyi planlar |
| High vs medium şema + `confirmation_action_key` ayrımı | aynı | Executor'da doğru action_key/scope ile consume |
| Cross-store `confirmation_id` / `confirmation_scope_hash` | aynı | Grant path `.lumos/pending_confirmations/{cid}.json` |
| Shadow adapter testleri | `test_bridge_confirmation_adapter.py` | `run_lumos_gate` high risk → shadow kayıt; W1-05 pending oluşturmayı bozmamalı |

### #492 (W1-03) — td-02 gap ve side-effect sırası

| Test | Belgelenen gap / sıra | W1-05 uygulama notu |
|------|----------------------|---------------------|
| `test_bridge_server_has_no_consume_confirmation_import` | Handler CU4 consume kullanmaz | W1-05 handler'a dokunmaz; executor consume eklenirse W1-06 ile handler import hizası gerekir |
| `test_high_risk_approve_token_path_leaves_shadow_grant_unconsumed` | Legacy approve grant tüketmez | W1-05 sonrası executor consume ile **davranış değişir** — test W1-05 veya W1-06'da güncellenmeli |
| `test_high_risk_validate_failure_preserves_pending_and_grant` | Validate fail → pending + grant korunur | W1-05 consume yalnızca validate sonrası |
| `test_dispatch_execute_exception_preserves_shadow_grant` | Execute fail → pending silinmiş, grant **tüketilmemiş** | **Kritik:** W1-05 consume zamanlaması execute başarısına bağlanmalı (#492 kısıt) |
| `test_shadow_grant_check_validate_before_consume_when_enabled` | `check_confirmation` validate; consume ayrı adım | W1-03/W1-05 sırası: validate → (execute?) → consume — plan td-02 ile hizalanmalı |
| `test_consume_confirmation_unaffected_by_env_gate` | `confirmation_policy.py` | Consume env'den bağımsız mutasyon; `check` env'e duyarlı |

### td-02 gap özeti (#492)

**Gap:** `attach_bridge_pending_confirmation` shadow grant yazar; approve zinciri (`approval_token` → validate → unlink → `execute_approved_*`) **`consume_confirmation` çağırmaz**. Grant manuel `consume_confirmation` ile tüketilebilir durumda kalır — duplicate onay / CU4–legacy kopukluğu (RB-02).

**W1-05 kapsamı:** Gap'in **lumos_gate + task_dispatch executor** dilimini kapatır; köprü handler ve resume yolu W1-06'da kalır.

---

## 5. Gerekli testler

### Wave plan PR-W1-05 test gereksinimleri → dosya eşlemesi

| Wave plan gereksinimi | Mevcut test | W1-05 aksiyon |
|----------------------|-------------|---------------|
| Shadow → consume geçişi; env on iken grant tüketimi | `test_bridge_confirmation_adapter.py` (shadow only); `test_task_dispatch.py` (~L208–256 shadow korelasyon) | **Genişlet:** `execute_approved_*` + `LUMOS_CONFIRMATION_ENABLED=true` → grant `consumed: true` |
| High-risk ve medium-risk pending şema ayrımı | #491 `test_high_risk_pending_schema_distinct_from_dispatch`; adapter `test_high_vs_medium_risk_shadow_action_keys_differ` | **Korut + genişlet:** her executor doğru `BRIDGE_HIGH_RISK_ACTION` vs `BRIDGE_MEDIUM_DISPATCH_ACTION` |
| Gate/dispatch regresyon: plan substep | `test_lumos_plan_substep_gate.py` (`approval_granted`, substep block) | **Regresyon** — consume wiring plan/substep davranışını bozmamalı |
| Gate/dispatch regresyon: persona checkpoint | `test_persona_security_simdi_checkpoint.py` (`run_lumos_gate` policy 403) | **Regresyon** — policy block yolları etkilenmemeli |

### Genişletilecek mevcut testler

| Dosya | Mevcut kapsam | W1-05 yeni/ güncellenecek senaryolar |
|-------|---------------|--------------------------------------|
| `tests/test_bridge_confirmation_adapter.py` | Shadow attach, env off check no-op | High-risk `execute_approved_pending_record` consume (unit, mock executor) |
| `tests/test_task_dispatch.py` | `execute_approved_dispatch_pending` dosya yürütme; shadow attach | Consume after successful dispatch execute; wrong scope_hash fail |
| `tests/test_lumos_plan_substep_gate.py` | Plan gate, `approval_granted=True` | Pending/consume yok — saf regresyon |
| `tests/test_persona_security_simdi_checkpoint.py` | Bridge policy block | Saf regresyon |

### Yeni senaryolar (wave plan + #492 kısıtları)

| Senaryo | Önerilen konum | Kaynak kısıt |
|---------|----------------|--------------|
| Validate fail → grant tüketilmez | `test_task_dispatch.py` / adapter | #492 |
| Execute exception → grant tüketilmez | `test_task_dispatch.py` | #492 `test_dispatch_execute_exception_*` |
| İkinci consume → False | `test_confirmation_policy.py` (mevcut) + dispatch/gate integration | td-02 single-use |
| Env off: check no-op; consume davranışı net | adapter + dispatch | #491 adapter env testleri |
| Expired grant → consume fail | `test_confirmation_policy.py` (mevcut) + bridge scope | W1-03 |

### Bilerek W1-06'ya bırakılan testler

- `test_bridge_approve_contract.py` — end-to-end handler approve + CU4 consume
- `test_bridge_consume_validate_characterization.py` — handler import grep; W1-06 sonrası güncelleme
- `test_pending_approvals_list.py`, panel/cursor E2E

---

## 6. Uygulama öncesi riskler

| ID | Sınıf | Risk | Kanıt / bağlam | Mitigation notu (factual) |
|----|-------|------|----------------|---------------------------|
| R1 | **Blocker** | W1-03 uygulama PR merge edilmeden W1-05 başlanamaz | Wave plan ön koşul; `confirmation_policy` bridge yardımcıları yok; #492 test-only | W1-03 uygulama merge'i gate |
| R2 | **Blocker** | td-02 side-effect sırası — grant erken tüketim veya onaysız yürütme | execution-map td-02 **kritik**; #492 execute-exception senaryosu | Validate → execute sonucu → consume sırası #492 ile uyumlu olmalı |
| R3 | **High** | #491 testleri "shadow unconsumed" karakterize eder; W1-05 test drift | `test_dispatch_approve_valid_token_executes_without_cu4_consume` | W1-05 PR test güncellemesi planlanmalı |
| R4 | **High** | Bridge handler dolaylı consume — handler hâlâ legacy token + unlink önce | `server.py` L2286–2295 unlink before execute | Execute içi consume unlink sonrası grant hâlâ diskte mi — sıra analizi gerekir |
| R5 | **Medium** | td-08 üç fiziksel store korelasyonu | `pending_approvals/`, `pending_confirmations/`, `cursor_bridge/pending_approvals.json` | High/medium farklı şema; yanlış cid/hash regresyonu |
| R6 | **Medium** | `LUMOS_CONFIRMATION_ENABLED=false` opt-in — wiring kısmi etkisiz | `is_confirmation_enabled()` default false (#461 docs) | Env off iken consume/check no-op beklentisi testlerle sabitlenmeli |
| R7 | **Medium** | Rollback orta–yüksek | Wave plan PR-W1-05 rollback | `lumos_gate` + `task_dispatch` risk path geri sarım shadow-only |
| R8 | **Low** | `lumos_gate_execute` (~L2617+) dokunulmazlık ihlali | Wave plan açık hariç | Code review scope guard |
| R9 | **Low** | Plan substep / persona regresyon | `test_lumos_plan_substep_gate`, persona checkpoint | CI regresyon suite |

---

## 7. Exit criteria preview — "W1-05 done"

W1-05 **tamamlandı** sayılır ancak şu kanıtlar sağlandığında (W1-06 öncesi):

| # | Checkpoint | Kanıt |
|---|------------|-------|
| 1 | `execute_approved_pending_record` (high-risk) env-on iken pending kaydındaki `confirmation_id` + `confirmation_scope_hash` ile grant tüketir | Unit/integration test yeşil |
| 2 | `execute_approved_dispatch_pending` (medium-risk) aynı consume davranışı | `test_task_dispatch.py` yeşil |
| 3 | Validate failure ve execute failure senaryolarında grant **tüketilmez** (#492 kısıt) | Test yeşil |
| 4 | High vs medium `confirmation_action_key` ayrımı korunur | #491 + W1-05 testleri |
| 5 | `lumos_gate_execute` (~L2617+), `server.py` approve handler, `cursor_bridge` **değişmedi** (veya yalnızca import/delegasyon değil — executor odaklı diff) | PR diff scope |
| 6 | Shadow pending oluşturma (`attach_bridge_pending_confirmation` ~L1161, ~L695) regresyon yok | Adapter + dispatch attach testleri |
| 7 | `test_lumos_plan_substep_gate.py`, `test_persona_security_simdi_checkpoint.py` yeşil | CI |
| 8 | ruff + pytest (commit guard) yeşil | CI |

**W1-05 done ≠ Madde 1 done.** RB-02 / codex PR-C6 "Kapandı" **W1-06** sonrası.

---

## 8. Cross-refs

| Belge | İlgili bölüm |
|-------|--------------|
| [adr-012-wave1-execution-plan.md](adr-012-wave1-execution-plan.md) | PR-W1-05 amaç, dosyalar, testler, rollback, dependency order |
| [adr-012-implementation-sequence.md](adr-012-implementation-sequence.md) | Madde 1 PR-1c; td-02 kritik risk; Madde 1 test matrisi |
| [technical-debt-dependency-graph.md](technical-debt-dependency-graph.md) | [td-02](technical-debt-dependency-graph.md#td-02-bridge-cu4-gap), [td-08](technical-debt-dependency-graph.md#td-08-parallel-pending-stores) |
| [technical-debt-execution-map.md](technical-debt-execution-map.md) | td-02 § consume/validate sınırı → handler entegrasyon sırası |
| [release-blockers.md](release-blockers.md) | RB-02 — köprü CU4 consume wiring |
| Merged #491 | `tests/test_bridge_approve_contract.py`, genişletilmiş adapter/policy/dispatch |
| Merged #492 | `tests/test_bridge_consume_validate_characterization.py` — td-02 gap belgesi |

### Dependency graph (td-02 / td-08 ↔ W1-05)

```
td-08 (store envanteri #491)
    └── td-02 karakterizasyon (#491, #492)
            └── PR-W1-03 uygulama (bridge helpers)  ← plan ön koşul
                    └── PR-W1-05 (gate/dispatch executor consume)
                            └── PR-W1-06 (handler + resume + cursor)
                                    └── Madde 1 exit → PR-W1-04/07
```

---

## Yasaklar (bu belge)

- Kod, runtime, enforcement değişikliği **yapılmaz**
- PR **açılmaz**
- W1-06 / Wave 2 kapsamı **planlanmaz**
- Uygulama sırası **değiştirilmez**
