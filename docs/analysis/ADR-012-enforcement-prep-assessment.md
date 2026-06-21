# ADR-012 Enforcement Prep Assessment

| Alan | Değer |
|------|-------|
| Durum | Salt okuma keşif (2026-06-21) — uygulama yok |
| Referans | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [runtime enforcement map](lumos-runtime-enforcement-map.md), [open decisions § enforcement](../memory/open-decisions-needs-review.md), [karar matrisi (tavsiyesiz)](ADR-012-enforcement-decision-matrix.md) |
| PR bağlamı | #459–#464 Faz-2 enforcement dalgası |

## Executive summary

- ADR-012 **CLOSED değil**; Faz-2 dalgası (#459–#464) panel/CLI policy→profil→confirmation zincirini merge etti; confirmation **opt-in** (#461) korunuyor.
- **Wired:** `task_action_gate`, CLI/panel `ensure_*_confirmation` + `consume_confirmation`, P2 engine branch (#463) + `is_security_never_auto()` helper.
- **Shadow:** PR-C6 `attach_bridge_pending_confirmation` — CU4 grant yazar, legacy `pending_approvals` + `approval_token` akışı devam eder; köprü yürütmede `consume_confirmation` **yok**.
- **Documented-only / gap:** Trust Faz 4 (ADR-007), `change_sensitivity` ↔ `lumos_gate` birleşik zincir, P2 tam küme eşlemesi, panel `LockState` vs `LUMOS_SESSION_UNLOCKED`.
- **Runtime değişikliği:** Bu keşif turunda **sıfır** — yalnızca analiz.

---

## 1. Kısa teknik değerlendirme

### ADR-012 checkpoint vs repo bugün

| Checkpoint | ADR-012 durumu | Repo gerçeği |
|------------|----------------|----------------|
| Panel policy (#443–#446) | Kapandı | `task_action_gate` → `check_policy` — wired |
| Profil guard (#449) | Kapandı | `may_execute_step_at_runtime` 2. kapı — wired |
| CU4 confirmation (#452–#458) | Kapandı (opt-in) | `confirmation_policy` + panel/CLI consume — wired when env on |
| E2E (#459+#460) | Kapandı | Test kanıtı; varsayılan kapalı |
| Varsayılan-on (#461) | Kapandı (docs) | Opt-in korunur; kod değişmedi |
| PR-C6 (#462) | **Kısmi** | Shadow adapter only |
| P2 engine (#463) | **Kısmi (dar)** | Engine branch + helper; `permanent_delete` hariç |
| Trust Faz 4 | Açık | Kod yok |
| Panel LockState | Açık | Env vekili; runtime `LockState` doğrulanmaz |

**Sonuç:** Codex C1–C6 sözleşmesi dokümante; enforcement **parçalı ama güçlü** (CLI/panel görev mutasyonları). Kapanışı engelleyen dört alan: köprü confirmation consume, P2 tam eşleme, trust motor, sensitivity↔gate zinciri.

### Shadow vs wired vs documented-only

| Katman | Durum | Kanıt |
|--------|-------|-------|
| Policy 1. kapı | **Wired** | `action_policy.check_policy` — CLI + panel |
| Profil 2. kapı | **Wired** | `may_execute_step_at_runtime` — engine, panel, cursor_bridge packet |
| Confirmation 3. kapı | **Wired (opt-in)** | `LUMOS_CONFIRMATION_ENABLED`; default no-op |
| `consume_confirmation` panel/CLI | **Wired** | `ensure_panel/cli/delete_permanent_confirmation` |
| PR-C6 bridge adapter | **Shadow** | `attach_bridge_pending_confirmation` yazar; yürütme legacy token |
| P2 `SECURITY_NEVER_AUTO` engine | **Wired (dar)** | `_step_security_never_auto_member` — `permanent_delete` excluded |
| `change_sensitivity` → gate | **Documented-only / kopuk** | `write_interceptor`, `decision_explorer`; `lumos_gate` import yok |
| Trust Faz 4 | **Documented-only** | ADR-007; `src/security/*` trust motoru yok |

---

## 2. Kullanım noktaları haritası

### Confirmation (`confirmation_enabled`, `check_confirmation`, `consume_confirmation`)

| Yüzey | Dosya | Satır / sembol | Davranış |
|-------|-------|----------------|----------|
| Env gate | `src/policy/confirmation_policy.py` | L101–104 `is_confirmation_enabled` | Opt-in |
| Panel 3. kapı (check) | `src/core/panel_bridge_state.py` | L157–187 `task_action_gate` | Check only in gate |
| Panel consume | `panel/scripts/panel_tasks_server.py` | `ensure_panel_mutation_confirmation`, `ensure_delete_permanent_confirmation` | Check+consume |
| CLI consume | `src/cli/cli_tasks_mutation.py` | L26–30, ~L232 `ensure_cli_mutation_confirmation` | Check+consume |
| Grant store | `confirmation_policy.py` | L516+ `consume_confirmation` | `.lumos/pending_confirmations/` |
| PR-C6 shadow | `lumos_gate.py` L1161–1168; `task_dispatch.py` L695–702 | `attach_bridge_pending_confirmation` | Parallel grant; **no consume on approve** |
| Bridge approve | `kando_bridge/server.py` L2230–2288 | `approval_token` + `approval_granted` | Legacy; CU4 consume **yok** |
| Cursor APPROVE | `src/kando/cursor_bridge.py` L720+ | `_handle_approve_goal` | `pending_approvals.json`; CU4 **yok** |

### Trust / keystore / session

| Sinyal | Kaynak | Kullanım | Gap |
|--------|--------|----------|-----|
| `keystore_ready` | `startup_health.py` L26; panel bridge L671+ | CLI `durum`/`hazir`; panel read payload | Dosya-init; consent'ten ayrıldı (#441) |
| `session_unlocked` | CLI: `LockState.is_locked()`; panel: **None** + note | CLI doğru; panel doğrulamaz | ADR-011 Faz 4 |
| `koruma_active` | Panel: `LUMOS_SESSION_UNLOCKED` env L61–65 | Policy delete gate | Runtime kilit değil |
| Consent | `effective_consent`, `consent_ok` | Policy identity/keystore; mutation context | Kalıcı consent panel POST ayrı |

### P2 `SECURITY_NEVER_AUTO`

| Üye | Enforce yolu |
|-----|--------------|
| Küme tanımı | `profiles.py` L47–52, `inviolable.py` |
| Helper | `is_security_never_auto` / `get_security_never_auto_member` L69–113 |
| Engine branch | `engine.py` L531–537, L572–594 — `include_permanent_delete=False` |
| `permanent_delete` | `workspace_contract.may_perform_permanent_delete`; panel #445 |
| Matris never | `external`/`critical` step kinds → `DECISION_LAYER_NEVER` |
| ActionRegistry | `external`/`critical` executor red |

### PR-C6 bridge

```
lumos_gate / task_dispatch (risk)
  → pending_approval_record (.lumos/pending_approvals/)
  → attach_bridge_pending_confirmation (shadow → pending_confirmations/)
Bridge POST approve
  → approval_token validate → approval_granted=True
  → execute (NO consume_confirmation)
```

### `change_sensitivity` gates

| Tüketici | Bağlantı |
|----------|----------|
| `write_interceptor.py` L77+ | CRITICAL/HIGH → patch pipeline |
| `decision_explorer.py` L110+ | HIGH/CRITICAL özet |
| `change_plan.py` | Patch plan etiketi |
| `lumos_gate.py` | **Import/use yok** — ADR-006 gap |

---

## 3. Etkilenecek bileşenler (gelecek enforcement adayları)

| Öncelik | Modül | Rol | Satır ref |
|---------|-------|-----|-----------|
| P0 | `packages/kando_bridge/src/kando_bridge/server.py` | Approve handler → CU4 consume | ~L2230–2290 |
| P0 | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | High-risk resume | L2617+ `lumos_gate_execute` |
| P0 | `packages/kando_runtime/src/kando_runtime/task_dispatch.py` | Dispatch approve path | L695–706, approve executor |
| P1 | `src/kando/cursor_bridge.py` | APPROVE goal vs CU4 | L720+, L2728 profil guard |
| P1 | `src/task_engine/engine.py` | P2 genişletme hook | L531–594 |
| P1 | `src/task_engine/profiles.py` | Helper + matris | L47–113, L285–295 |
| P2 | `src/core/panel_bridge_state.py` | LockState doğrulama | L48–66, L900–925 |
| P2 | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | Sensitivity entegrasyonu | risk path ~L1440+ |
| P2 | `src/core/change_sensitivity.py` | CRITICAL heuristic | L26–89 |
| P3 | `src/security/lock.py` | Trust Faz 4 tüketim | L6–15 |
| Docs | `docs/analysis/lumos-runtime-enforcement-map.md` | §8 sync | Mevcut |

**Call graph (CLI → enforcement):**

```
main.py → cli_router → cli_tasks_mutation
  → check_policy (action_policy)
  → [opt-in] ensure_cli_mutation_confirmation → consume_confirmation
  → TaskEngine.run_task
      → _step_security_never_auto_member (P2)
      → may_execute_step_at_runtime
```

---

## 4. Risk listesi (sıralı)

| Seviye | Risk | Etki |
|--------|------|------|
| **Blocker** | Köprü onayı CU4'tan bağımsız (`approval_token`); duplicate/onaysız yürütme yolu | PR-C6 gap; codex C3/C6 |
| **Blocker** | Panel `koruma_active` = env vekili; runtime kilit yansımaz | Yanlış delete/mutation izni algısı |
| **High** | P2 dar scope — tag eşleşmeyen `external_write` vb. engine'i bypass edebilir | CU6 tam kapanış yok |
| **High** | Trust Faz 4 yok — consent/keystore/session merkezi değil | ADR-007 + codex C3 kanıt |
| **Medium** | `change_sensitivity` ↔ `lumos_gate` kopuk | CRITICAL path + düşük gate riski |
| **Medium** | Confirmation opt-in — prod'da 3. kapı kapalı kalabilir | Bilinçli (#461); UX drift |
| **Low** | `PermissionManager` stub | Lease enforcement yok |
| **Low** | Panel mock/guidance alanları | C4 görünürlük; enforcement değil |

---

## 5. Karar verilmesi gereken maddeler (ajan cevaplamaz)

Detaylı fayda/risk, etkilenen bileşenler ve geri dönüş maliyeti: [ADR-012 enforcement decision matrix](ADR-012-enforcement-decision-matrix.md).

| # | Madde | Durum |
|---|-------|-------|
| 1 | **PR-C6 wiring kapsamı:** Shadow adapter yeterli mi, yoksa köprü approve/resume tek yol olarak `consume_confirmation` + opt-in env mi olacak? Legacy `pending_approvals` ne kadar süre korunacak? | **karar bekliyor** |
| 2 | **P2 genişletme sınırı:** Engine branch dar mı kalacak (`step.kind`/`action_key` eşlemesi), yoksa `action_policy` + panel/CLI action sabitleri için resmi eşleme tablosu mu eklenecek? | **karar bekliyor** |
| 3 | **Trust Faz 4 zamanlaması:** Codex kapanış öncesi mi zorunlu, yoksa köprü+P2 sonrası mı? Panel'de `session_unlocked` runtime'dan mı okunacak? | **karar bekliyor** |
| 4 | **Sensitivity ↔ gate:** `lumos_gate` risk skoru ile `classify_sensitivity` tek zincirde birleşecek mi; eşik politikası ne? | **karar bekliyor** |
| 5 | **Confirmation varsayılanı:** Opt-in kalıcı mı (#461); tam varsayılan-on için hangi ürün kapıları (E2E, false positive, köprü duplicate) kapanmalı? | **karar bekliyor** |
| 6 | **Panel LockState:** `LUMOS_SESSION_UNLOCKED` env vekili kaldırılacak mı; panel sunucusu runtime `LockState`'e nasıl bağlanacak (process model)? | **karar bekliyor** |

### Top 3 karar maddeleri (insan onayı önceliği)

1. **PR-C6:** Köprü onay sonrası yürütme `approval_token` mı kalacak, yoksa `consume_confirmation` + `LUMOS_CONFIRMATION_ENABLED` ile mi birleşecek? — **karar bekliyor**
2. **P2 genişletme:** `external_write` / `irreversible_user_op` / `critical_system_config` için action_key/policy eşleme tablosu genişletilsin mi, yoksa dar engine branch yeterli mi? — **karar bekliyor**
3. **Trust Faz 4:** Merkezi trust tüketimi codex C3 kanıt zincirine ne zaman ve hangi sinyallerle (`keystore_ready`, `session_unlocked`, consent) bağlanacak? — **karar bekliyor**

---

## İlgili PR'lar (#459–#464)

| PR | Konu | Enforcement etkisi |
|----|------|-------------------|
| #459 | CLI E2E confirmation | Wired (test) |
| #460 | Panel+API E2E | Wired (test) |
| #461 | Varsayılan-on docs → opt-in | Docs only |
| #462 | PR-C6 shadow adapter | Shadow |
| #463 | P2 engine branch + helper | Wired (dar) |
| #464 | Milestone docs sync | Docs only |

---

## Yasaklar (bu hazırlık turu)

- `consume_confirmation` köprü wiring uygulanmadı
- Trust Faz 4 davranışı değiştirilmedi
- P2 matching genişletilmedi
- `LUMOS_CONFIRMATION_ENABLED` default flip yok
- Mimari karar verilmedi — yalnızca seçenekler listelendi

---

## Sonraki adım

Enforcement uygulaması öncesi yukarıdaki karar maddelerinin insan onayı; ardından dar kapsamlı PR'lar (PR-C6 wiring, P2 genişletme, Trust Faz 4) ayrı onay hatlarında.
