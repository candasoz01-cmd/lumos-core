# Lumos Runtime Enforcement Map

| Alan | Değer |
|------|-------|
| Durum | **Güncellendi** — salt okuma analizi (2026-06-21); panel gate #443–#446; consent #450+#451; profil guard #449; CU4 confirmation #452–#458 (opt-in); E2E #459+#460; varsayılan-on kararı opt-in korunur (#461); PR-C6 adapter kısmi (#462); P2 engine branch (#463) |
| İlgili | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [ADR-010 usage map](ADR-010-guard-policy-trust-usage-map.md), [permission matrix](lumos-action-permission-matrix.md) |
| Kapsam | Docs-only; `archive/` hariç aktif kod taraması |
| Yöntem | `rg` + dosya okuma — kanıt tabanlı |

## Amaç

ADR-012 Security Codex maddelerinin (C1–C6) repo'da **nerede enforce edildiğini**, **gap** kaldığını ve **codex ile hizayı** kaydetmek.

**Codex referansı:** C1 tek kapı · C2 iç bypass yok · C3 onay/kanıt · C4 mock ayrımı · C5 trash · C6 stop-on-risk.

---

## Özet

| Bulgu | Detay |
|-------|-------|
| Enforcement **parçalı** | Tek security motoru yok; ADR-010 ile uyumlu |
| En güçlü zincir | `task_engine/profiles.py` → `may_execute_step_at_runtime` → `TaskEngine.run_task` |
| Panel gate | **Kapandı** #443–#446 (`check_policy`); profil matrisi **Kapandı** #449 (`may_execute_step_at_runtime` 2. kapı); confirmation **Kapandı** #453–#456 (3. kapı, opt-in) |
| Trust motor | Hedef (ADR-007); aktif kodda minimal |
| `SECURITY_NEVER_AUTO` | Matris + `inviolable.py`; engine branch **kısmi** #463 (`permanent_delete` store/panel; step tag eşlemesi sınırlı) |
| consent ≠ general_approval | **Kapandı** #450 (policy/read ayrımı) + #451 (`consent oturum` CLI + unlock path) |

---

## 1. Runtime başlatma zinciri

### `src/core/lumos_runtime.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Workspace bootstrap, engine/memory/policy, CoreState, lock/presence, CLI context, TaskStore/TaskEngine kurulumu |
| **Enforce edilen** | `ensure_trash_dir`, sandbox env (`LUMOS_SANDBOX`), startup self-check (tasks/logs/trash yazılabilirlik) |
| **Gap** | Tek kapı sözleşmesi burada **deklare edilmez**; dış giriş `main.py`/CLI'ye dağılır |
| **Codex** | C5 (trash dir), kısmi C1 |

### `src/main.py` + `src/cli/cli_router.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | CLI giriş, route dağıtımı, readonly vs mutation ayrımı |
| **Enforce edilen** | Route seviyesinde handler ayrımı; online/offline dallanma |
| **Gap** | Tüm route'lar için merkezi policy guard yok (mutation alt kümesi ayrı) |
| **Codex** | C1 kısmi |

### `src/core/live_brain.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Online serbest metin → LLM; pending intent/clarification; consent phrase ile genel onay |
| **Enforce edilen** | Consent ifadeleri (`onaylıyorum`); pending intent resume; tool unavailable → red |
| **Gap** | `_tool_available` şu an **her zaman False** — deterministik intent çoğunlukla red |
| **Codex** | C3 (onay), C6 (belirsizlikte dur), C2 (task creation Brain üzerinden)

---

## 2. Görev oluşturma ve yürütme (`task_engine`)

### `src/task_engine/profiles.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Canonical profil × adım türü matrisi; `SECURITY_NEVER_AUTO` sabitleri |
| **Enforce edilen** | `is_allowed_for_profile`, `may_execute_step_at_runtime`, `get_decision_layer` |
| **Gap** | Eylem alanı (mail, terminal, …) düzeyinde mapping **yok** — yalnızca `step.kind` |
| **Codex** | C3 ✓ (matris), C6 ✓ (`DECISION_LAYER_NEVER`)

### `src/task_engine/engine.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Görev kaydı, adım yürütme, doğrulama, observation events |
| **Enforce edilen** | Her adım öncesi `_is_step_allowed_runtime` → durdurma + `EVENT_POLICY_BLOCKED`; `SECURITY_NEVER_AUTO` engine branch (#463) → `BLOCK_SECURITY_NEVER_AUTO`; `may_perform_permanent_delete` silme dalında; `result_kind` / `simulasyon` ayrımı |
| **Gap** | Engine branch `permanent_delete` hariç; küme üyelerinin step kind/action_key eşlemesi sınırlı; external adımlar matriste durur ama executor kayıtları ayrı |
| **Codex** | C3 ✓, C4 ✓, C5 kısmi, C6 ✓ (adım durdurma)

### `src/cli/cli_tasks_mutation.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | CLI görev oluştur/tamamla/sil/iptal |
| **Enforce edilen** | `check_policy` — offline, koruma+delete, consent snapshot (`effective_consent(session_consent)`) |
| **Gap** | ~~`general_approval` policy context'te `consent` ile eşleniyor~~ → **Kapandı** #450 |
| **Codex** | C3, C6 ✓ (policy block + log)

### `src/cli/cli_router.py` + `src/core/lumos_runtime.py` (session consent)

| Alan | Değer |
|------|-------|
| **Sorumluluk** | `consent oturum aç/kapat/durum`; kilit menüsü unlock+consent / lock→consent sıfırlama |
| **Enforce edilen** | Oturum consent yalnız kilit açıkken (`state.is_locked()`); genel onaydan ayrı liste |
| **Gap** | Kalıcı `consent.json` yazımı CLI'de yok (panel `POST /lumos-consent` ayrı yüzey) |
| **Codex** | C3 ✓ (consent sinyali), C10 kısmi (unlock önkoşulu; presence ayrı) |

### `src/task_engine/diagnostics.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Adım blok nedeni kullanıcı mesajı |
| **Enforce edilen** | Profil/onay uyumsuzluğunda açıklayıcı `block_reason` |
| **Codex** | C3 kanıt (kullanıcıya görünür neden)

---

## 3. Panel / API köprüsü

### `src/core/panel_bridge_state.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Salt okuma panel payload; **`task_action_gate`** — panel mutasyon enforcement merkezi |
| **Enforce edilen** | Read-only payload; `task_action_gate`: `check_policy` → `may_execute_step_at_runtime` (#449) → `check_confirmation` (#453–#456, `LUMOS_CONFIRMATION_ENABLED` opt-in) |
| **Gap** | Mock/guidance alanları CLI runtime ile birebir değil (ADR-011); confirmation varsayılan no-op |
| **Codex** | C3 ✓ (üç kapı), C4 (görünürlük), C1 read path + mutasyon gate

### `panel/scripts/panel_tasks_server.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Panel HTTP: tasks CRUD, trash, evidence, `/lumos-read-state`, `/lumos-consent` |
| **Enforce edilen** | Trash'e yazma; evidence journal; consent.json; görev mutasyonları `task_action_gate` → `check_policy` (#443–#446) → `may_execute_step_at_runtime` (#449) → `check_confirmation` (#453–#456, opt-in) |
| **Gap** | `LUMOS_SESSION_UNLOCKED` env vekili; runtime `LockState` doğrulanmaz (ADR-011); confirmation varsayılan kapalı |
| **Codex** | C1 yüzey ✓, C5 trash write ✓, C3 **kısmi** (policy+profil+confirmation opt-in ✓; trust motor eksik)

---

## 4. Policy / guard / trust

### `src/policy/action_policy.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Minimal hardcoded task/identity kuralları |
| **Enforce edilen** | Offline mutasyon red; koruma+delete red; consent+identity/keystore red; `log_policy_blocked` |
| **Gap** | Sınırlı action seti; ~~`general_approval` vs `consent` semantik drift (CLI)~~ → **Kapandı** #450 (`PolicyContext.general_approval` ayrı alan) |
| **Codex** | C3, C6 ✓ (CLI mutation + panel #443–#446)

### `src/policy/offline_engine.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Offline modda dış/network yok ilkesi |
| **Enforce edilen** | Offline cevap üretimi |
| **Codex** | C6 (dış risk kapalı)

### `src/security/lock.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | `LockState` — passphrase sonrası kök anahtar bellekte |
| **Enforce edilen** | Oturum kilidi state |
| **Gap** | ADR-011: `keystore_ready` ≠ `session_unlocked` drift devam |
| **Codex** | C3 security settings (kısmi)

### `src/security/presence_lock.py`, `src/security/permissions.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Presence sinyali; permission lease modeli |
| **Enforce edilen** | Demo düzeyi presence |
| **Gap** | `PermissionManager` lease enforcement **uygulanmamış** (stub) |
| **Codex** | C3 gap

### `src/core/workspace_contract.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Trash tek hedef, core state path, sandbox yazım guard, kalıcı silme kapısı |
| **Enforce edilen** | `move_to_trash`, `is_allowed_trash_path`, `allow_write_to_core`, `may_perform_permanent_delete(user_initiated)` |
| **Gap** | Tüm silme çağrıları `user_initiated` ile gelmeyebilir |
| **Codex** | C5 ✓, C2 ✓ (core write guard)

### `src/core/write_interceptor.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Core/protected path direct write → patch pipeline |
| **Enforce edilen** | Sandbox+core red; guard audit `DIRECT_WRITE_ATTEMPT` |
| **Codex** | C2 ✓, C6 ✓

### `src/core/change_sensitivity.py`, `src/core/guard_audit.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Path hassasiyeti sınıflandırma; guard olay kaydı |
| **Enforce edilen** | CRITICAL/HIGH etiketleme; audit trail |
| **Gap** | Sensitivity → otomatik dur **zinciri kopuk** (gate ayrı) |
| **Codex** | C6 kısmi

### `packages/kando_runtime/src/kando_runtime/lumos_gate.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Köprü görevleri LLM reasoning; `no_op` / risk prompt |
| **Enforce edilen** | Prompt sözleşmesi: riskli işte direct_patch yok; onay varsayımı yok |
| **Gap** | Prompt enforcement; runtime assert **sınırlı** |
| **Codex** | C4, C6 (köprü yüzeyi)

### `src/core/inviolable.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Çekirdek sabitlerin (`SECURITY_NEVER_AUTO`, trash dirname) değişmediğini doğrulama |
| **Enforce edilen** | Test/startup integrity check |
| **Codex** | C5, C3 sözleşme referansı

### `src/core/evidence_continuity.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Panel/CLI olaylarını evidence journal'a yansıtma |
| **Enforce edilen** | Policy block mirror; panel operasyon kayıtları |
| **Codex** | C3 kanıt ✓

---

## 5. Codex madde × enforcement özeti

| Codex | Güçlü enforce | Gap |
|-------|---------------|-----|
| **C1** Tek kapı | CLI router, panel server yüzeyi | Çoklu giriş (CLI vs panel vs bridge); köprü ayrı yüzey |
| **C2** İç bypass yok | write_interceptor, workspace_contract | ~~Panel doğrudan tasks.json policy dışı~~ → PUT #444 gated |
| **C3** Onay/kanıt | profiles + TaskEngine + action_policy CLI/panel + evidence + confirmation (opt-in) | ~~consent≠GA drift~~ → **Kapandı** #450+#451; ~~panel profil~~ → **Kapandı** #449; confirmation **merge** #453–#458 — varsayılan kapalı (`LUMOS_CONFIRMATION_ENABLED`) |
| **C4** Mock ayrımı | Task status `simulasyon`; panel status map | Panel mock alanları |
| **C5** Trash | workspace_contract, panel trash write | Kalıcı silme tüm path'lerde `user_initiated` (#445 gated) |
| **C6** Stop-on-risk | Profil never layer; policy offline/koruma; lumos_gate prompt; panel `task_action_gate`; P2 SECURITY_NEVER_AUTO engine branch (#463) | sensitivity kopuk; tam küme eşlemesi açık |

---

## 6. Tarama kanıtı (dosya listesi)

Aktif kodda `may_execute_step_at_runtime` çağrıları:

- `src/task_engine/engine.py`
- `src/kando/cursor_bridge.py`
- `src/core/panel_bridge_state.py` (`task_action_gate` — #449)

`check_policy` çağrıları:

- `src/cli/cli_tasks_mutation.py`
- `src/core/panel_bridge_state.py` (`task_action_gate`)

`check_confirmation` / `is_confirmation_enabled` çağrıları (#453–#456):

- `src/core/panel_bridge_state.py` (`task_action_gate` 3. kapı)
- `src/policy/confirmation_policy.py` (modül)
- `src/cli/cli_tasks_mutation.py` (#458 CLI `onayla`)
- `panel/scripts/panel_tasks_server.py` (`POST /lumos-confirm/*` — #457)

`may_perform_permanent_delete` çağrıları:

- `src/task_engine/engine.py` (delete/archive dalı)

Panel gate (2026-06-21 — #443+):

```python
# src/core/panel_bridge_state.py — task_action_gate()
pr = check_policy(action, _panel_policy_context())
# enabled=False when offline, koruma+delete, etc.
```

PR referansları: #443 policy enforcement, #444 PUT /tasks.json, #445 delete-permanent, #446 restore, #449 panel profil guard, #450 consent≠general_approval, #451 session_consent CLI, #452 PR-C0 reason codes docs, #453 confirmation_policy modülü, #454 delete-permanent confirmation, #455 trash modal UI, #456 panel mutation confirmation gate, #457 CU7 preview endpoint+modal, #458 CLI `onayla`, #459 CLI E2E, #460 panel+API E2E.

**Confirmation opt-in:** `LUMOS_CONFIRMATION_ENABLED=true|1|yes` — varsayılan yok/false → 3. kapı no-op; mevcut davranış (#443–#449) korunur.

---

## 7. CU4 / CU6 / CU7 / CU10 uyum özeti (#449–#458)

| CU | Madde | Merge durumu | Not |
|----|-------|--------------|-----|
| **CU4** | Dış etkili aksiyon açık onay | **Merge** #453–#456, #458 | `confirmation_policy`; 3. kapı opt-in; bkz. [CU4 skeleton draft](lumos-cu4-confirmation-skeleton-draft.md) |
| **CU6** | Geri dönüşsüz otomatik yok | **Kısmi** | #445+#454 delete-permanent; P2 engine branch **merge** #463 (dar kapsam) |
| **CU7** | Ne/nerede/etki görünürlüğü | **Merge** #457 | `POST /lumos-confirm/request` + panel modal (#455 UI) |
| **CU10** | Online kimlik/kilit koşulu | **Kısmi** | #451 session_consent CLI; panel env vekili; presence ayrı |

**Hedef zincir (ADR-010):** policy → consent (`effective_consent`) → profil+GA (#449) → confirmation (#453–#458, opt-in) → NEVER_AUTO.

---

## 8. Açık kalan maddeler

Detaylı keşif değerlendirmesi: [ADR-012 enforcement prep assessment](ADR-012-enforcement-prep-assessment.md).

| Madde | Durum | Referans |
|-------|-------|----------|
| P2 `SECURITY_NEVER_AUTO` engine branch | **Kapandı (dar kapsam)** | #463 — `run_task` branch + helper; `permanent_delete` store/panel; [P2 analiz](security-never-auto-p2-and-helper-proposal.md) |
| PR-C6 köprü `pending_approval` → confirmation namespace | **Kısmi** | #462 shadow adapter; köprü yürütmede `consume_confirmation` wiring açık — [CU4 skeleton §4.1](lumos-cu4-confirmation-skeleton-draft.md) |
| Trust motor Faz 4 (ADR-007) | Açık | ADR-011 checkpoint |
| E2E confirmation akışı (opt-in env ile) | **Kapandı** | PR #459 CLI, #460 panel+API E2E |
| Confirmation varsayılan-on kararı | **Kapandı (docs)** | Opt-in korunur (#461, E2E #460); tam default-on ertelendi; kod değişikliği yok (DL-C18) |
| Panel `LockState` vs env vekili | Açık | ADR-011 |
| `is_security_never_auto()` helper | **Kapandı** | #463 — `profiles.py`; engine scope `permanent_delete` hariç |

---

## İlgili belgeler

- [ADR-012 Security Codex](../decisions/ADR-012-lumos-security-codex.md)
- [Action permission matrix](lumos-action-permission-matrix.md)
- [Next minimal PR plan](lumos-security-codex-next-pr-plan.md)
