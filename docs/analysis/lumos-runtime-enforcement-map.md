# Lumos Runtime Enforcement Map

| Alan | Değer |
|------|-------|
| Durum | **Güncellendi** — salt okuma analizi (2026-06-21); panel gate #443–#446; consent ayrımı #450 + session_consent CLI #451 |
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
| Panel gap | ~~`_task_actions_gate()` her zaman açık~~ → **Kapandı** #443–#446 (`task_action_gate` + `check_policy`); profil matrisi panelde hâlâ yok |
| Trust motor | Hedef (ADR-007); aktif kodda minimal |
| `SECURITY_NEVER_AUTO` | Matris + `inviolable.py`; tüm silme yollarında tam branch **gap** |
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
| **Enforce edilen** | Her adım öncesi `_is_step_allowed_runtime` → durdurma + `EVENT_POLICY_BLOCKED`; `may_perform_permanent_delete` silme dalında; `result_kind` / `simulasyon` ayrımı |
| **Gap** | `SECURITY_NEVER_AUTO` kümesinin adım executor'larına **otomatik map'i yok**; external adımlar matriste durur ama executor kayıtları ayrı |
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
| **Sorumluluk** | Salt okuma panel payload: tasks, trash, logs, guidance, consent/keystore **görünürlük** |
| **Enforce edilen** | Read-only; trash listesi diskten; task status map (`simulasyon` etiketi) |
| **Gap** | **Enforcement değil** — mock/guidance alanları CLI runtime ile birebir değil (ADR-011) |
| **Codex** | C4 (görünürlük), C1 read path

### `panel/scripts/panel_tasks_server.py`

| Alan | Değer |
|------|-------|
| **Sorumluluk** | Panel HTTP: tasks CRUD, trash, evidence, `/lumos-read-state`, `/lumos-consent` |
| **Enforce edilen** | Trash'e yazma; evidence journal; consent.json; görev mutasyonları `task_action_gate` → `check_policy` (#443–#446) |
| **Gap** | Profil matrisi: `task_action_gate` → `may_execute_step_at_runtime` (kısmi; delete-permanent hariç) |
| **Codex** | C1 yüzey ✓, C5 trash write ✓, C3/C6 **kısmi** (policy ✓; profil drift riski)

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
| **C1** Tek kapı | CLI router, panel server yüzeyi | Çoklu giriş (CLI vs panel vs bridge); panel profil matrisi yok |
| **C2** İç bypass yok | write_interceptor, workspace_contract | ~~Panel doğrudan tasks.json policy dışı~~ → PUT #444 gated |
| **C3** Onay/kanıt | profiles + TaskEngine + action_policy CLI/panel + evidence | ~~consent≠general_approval drift~~ → **Kapandı** #450+#451; panel profil matrisi yok; confirmation (CU4) → **PR-C0: reason codes defined, implementation pending** |
| **C4** Mock ayrımı | Task status `simulasyon`; panel status map | Panel mock alanları |
| **C5** Trash | workspace_contract, panel trash write | Kalıcı silme tüm path'lerde `user_initiated` (#445 gated) |
| **C6** Stop-on-risk | Profil never layer; policy offline/koruma; lumos_gate prompt; panel `task_action_gate` | sensitivity kopuk; P2 SECURITY_NEVER_AUTO engine branch |

---

## 6. Tarama kanıtı (dosya listesi)

Aktif kodda `may_execute_step_at_runtime` çağrıları:

- `src/task_engine/engine.py`
- `src/kando/cursor_bridge.py`

`check_policy` çağrıları:

- `src/cli/cli_tasks_mutation.py`

`may_perform_permanent_delete` çağrıları:

- `src/task_engine/engine.py` (delete/archive dalı)

Panel gate (2026-06-21 — #443+):

```python
# src/core/panel_bridge_state.py — task_action_gate()
pr = check_policy(action, _panel_policy_context())
# enabled=False when offline, koruma+delete, etc.
```

PR referansları: #443 policy enforcement, #444 PUT /tasks.json, #445 delete-permanent, #446 restore, #450 consent≠general_approval ayrımı, #451 session_consent CLI/lock flow.

---

## 7. CU4 / CU6 / CU7 / CU10 uyum özeti (#450 + #451)

| CU | Madde | Bu PR zinciri | Durum |
|----|-------|---------------|-------|
| **CU4** | Dış etkili aksiyon açık onay | `general_approval` ≠ `consent`; GA yazma önkoşulu, consent identity/keystore | **PR-C0: reason codes defined, implementation pending** — bkz. [CU4 skeleton draft](lumos-cu4-confirmation-skeleton-draft.md) |
| **CU6** | Geri dönüşsüz otomatik yok | `SECURITY_NEVER_AUTO`; consent/GA bağımsız | **Kısmi** — engine branch tam değil (#445 gated delete ayrı) |
| **CU7** | Ne/nerede/etki görünürlüğü | `consent oturum durum`; panel gate `reason`; ayrı GA mesajları | **Kısmi** — CU preview/confirmation yüzeyi yok |
| **CU10** | Online kimlik/kilit koşulu | `consent oturum aç` kilit açık gerektirir; `kilit ac` → session_consent; lock → sıfırlama | **Kısmi** — panel `LockState` env vekili; presence ayrı |

**Hedef zincir (ADR-010):** policy → consent (`effective_consent`) → profil+GA → confirmation (PR-C0 reason codes; PR-C1+ runtime) → NEVER_AUTO.

---

## İlgili belgeler

- [ADR-012 Security Codex](../decisions/ADR-012-lumos-security-codex.md)
- [Action permission matrix](lumos-action-permission-matrix.md)
- [Next minimal PR plan](lumos-security-codex-next-pr-plan.md)
