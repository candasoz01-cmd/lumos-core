# ADR-010 — Guard / Policy / Trust Usage Map

| Alan | Değer |
|------|-------|
| Durum | **Checkpoint tamamlandı** (2026-06-21) — salt okuma analizi |
| İlgili | [ADR-010](../decisions/ADR-010-guard-policy-trust-terminology.md), ADR-003, ADR-006, ADR-007, ADR-008 |
| Kapsam | Docs-only; kod, import, test veya davranış değişikliği **yok** |
| Tarama | `src/`, `packages/`, `panel/` — `archive/` hariç |

## Amaç

ADR-010 terminoloji sözlüğünü repo gerçeğiyle doğrulamak: **guard, policy, trust, lock, consent, permission, confirmation, sandbox** terimlerinin hangi modüllerde geçtiğini, hangi drift risklerinin **doğrulandığını** ve ADR-006/007 finalize öncesi hangi ayrımın korunması gerektiğini kaydetmek.

---

## Özet bulgular

1. **Birleşik guard, policy veya trust motoru yok.** Davranış `lumos_gate`, `profiles.py`, `action_policy.py`, `change_sensitivity.py`, `write_interceptor`, `controlled_bridge`, `task_dispatch`, `src/security/*` ve panel read-only adapter'da **parçalıdır**.
2. **`trust` kod tabanında neredeyse yok** (aktif kodda 1 eşleşme: `src/context/__init__.py` yorum); trust kavramı **dokümantasyon ve ADR hedefi** düzeyindedir — ADR-007 ile uyumlu.
3. **`guard` en yoğun terim** (~123 `guard` + ~71 `Guard` eşleşmesi, 28+ dosya); çoğu `workspace_contract` guard sink'leri, `guard_audit`, `write_interceptor`, patch pipeline ve device guard.
4. **Lock semantik drift doğrulandı:** `_lock_ok(keystore_initialized)` ≠ runtime `LockState.unlocked` — farklı anlam, aynı kelime.
5. **Consent çift kaynak:** `effective_consent` (dosya + oturum) runtime; panel `panel_bridge_state` consent_ok + guidance metinleri — enforcement zinciri tek değil.
6. **`SECURITY_NEVER_AUTO` sözleşme var, tam enforce gap devam ediyor** — yalnızca `profiles.py` + `inviolable.py` referansı; engine'de eksik branch (ADR-006 ile örtüşür).
7. **Panel policy-engine.js yalnızca `archive/panel/`** — canlı read path `panel_bridge_state.py`; legacy mock drift riski arşivde kalır.
8. **Mail drift (Step 5 opsiyonel tarama):** Aktif guard/policy/trust kodunda prod mail credential veya OAuth yok; `controlled_bridge` mail yüzeyi **regex blok** ile reddeder — OD-031 Phase 2 boundary ile uyumlu.

---

## Terim frekans özeti (aktif kod, archive hariç)

| Terim | Yaklaşık eşleşme | Dosya sayısı | ADR-010 kategorisi |
|-------|------------------|--------------|-------------------|
| `sandbox` | 247 | 27 | sandbox |
| `policy` / `Policy` | 192 / 25 | 31 / 7 | policy |
| `consent` | 136 | 15 | consent / trust sinyali |
| `guard` / `Guard` | 123 / 71 | 28 / 12 | guard |
| `pending_approval` | 104 | 9 | confirmation |
| `permission` | 91 | 23 | permission |
| `LockState` | 3 | 2 | lock |
| `get_durum_parts` | 9 | 4 | trust (durum) |
| `_lock_ok` | 3 | 1 | lock drift |
| `may_execute_step` | 6 | 3 | permission |
| `SECURITY_NEVER_AUTO` | 3 | 2 | irreversible action |
| `trust` / `Trust` | 1 / 0 | 1 / 0 | trust (hedef only) |

*Tarama: `rg` — `src/`, `packages/`, `panel/`, `*.py` + `*.js`, 2026-06-21.*

---

## Giriş noktası → terim haritası

| Giriş noktası | Konum | Birincil terim(ler) | Rol (ADR-010) | Not |
|---------------|-------|---------------------|---------------|-----|
| CLI durum / hazır | `cli/cli_parse.py` | consent, lock, `get_durum_parts` | trust (görünürlük) | `_lock_ok` semantiği |
| Startup özeti | `core/startup_health.py` | consent, lock, presence | trust sinyali | `effective_consent`; `_lock_ok` ≠ `LockState` |
| Task mutasyon CLI | `cli/cli_tasks_mutation.py` | policy, consent, lock | policy + trust | `check_policy` çağrıları |
| TaskEngine | `task_engine/engine.py` | permission, consent, guard | permission + confirmation | `may_execute_step_at_runtime` |
| Profil matrisi | `task_engine/profiles.py` | permission, policy, `SECURITY_NEVER_AUTO` | policy + permission | Canonical yetki |
| Minimal politika | `policy/action_policy.py` | policy, consent | policy | Offline/koruma/consent kuralları |
| Permission stub | `security/permissions.py` | permission | permission | Lease modeli **uygulanmamış** |
| Runtime kilit | `security/lock.py` | lock (`LockState`) | lock / trust | Passphrase unlock |
| Presence | `security/presence_lock.py` | presence, trust sinyali | trust | Demo düzeyi |
| Lumos gate | `kando_runtime/lumos_gate.py` | guard, confirmation | guard | LLM reasoning; `no_op` / risk |
| Task dispatch | `kando_runtime/task_dispatch.py` | guard, confirmation | guard | `pending_approval`, risk sınıflandırma |
| Controlled bridge | `kando_runtime/controlled_bridge.py` | guard, sandbox, permission | guard + sandbox | Mail/shell/silme blok |
| Bridge intent | `kando_runtime/bridge_intent.py` | guard (dolaylı) | guard | task vs chat ayrımı |
| Köprü sunucu | `kando_bridge/server.py` | guard, confirmation | guard | POST `/task` zinciri |
| Path hassasiyeti | `core/change_sensitivity.py` | guard | guard | CRITICAL/HIGH — gate'ten kopuk |
| Write interceptor | `core/write_interceptor.py` | guard, sandbox | guard + sandbox | Sensitivity + sandbox_mode |
| Workspace contract | `core/workspace_contract.py` | guard, sandbox | guard + sandbox | `allow_write_to_core` sink'ler |
| Guard audit | `core/guard_audit.py` | guard | guard | EC v2 guard kanıtı |
| Device guard | `device/device_guard.py` | guard, policy | guard | Cihaz yüzeyi |
| Device policy | `device/device_action_policy.py` | policy | policy | Cihaz eylem kuralları |
| Cursor bridge | `kando/cursor_bridge.py` | permission, confirmation | permission | `may_execute_step_at_runtime` |
| Panel read state | `core/panel_bridge_state.py` | consent, lock, keystore (görünürlük) | panel görünürlüğü ≠ enforcement | Guidance metinleri |
| Legacy panel JS | `archive/panel/js/policy-engine.js` | policy, consent, mock | local demo | Arşiv; runtime ile senkron garantisi yok |
| Involable core | `core/inviolable.py` | `SECURITY_NEVER_AUTO` | irreversible action | Sözleşme referansı |

---

## Import / zincir haritası (guard → policy → trust)

```
CLI / köprü girişi
  ├─ bridge_intent (task | chat)
  ├─ lumos_gate (agent | direct_patch | no_op; risk; plan)
  ├─ task_dispatch (task_type; pending_approval)
  ├─ profiles.may_execute_step_at_runtime / is_allowed_for_profile
  ├─ action_policy.check_policy (offline, koruma, consent)
  ├─ controlled_bridge (yüzey blok; sandbox path)
  ├─ change_sensitivity + write_interceptor (path guard)
  └─ src/security (LockState, presence, permissions stub)
       └─ startup_health.get_durum_parts / effective_consent (durum etiketi)
```

**Analiz bulgusu:** Zincir **doğrusal değil**; gate allow + profil deny veya policy allow + lock kapalı kombinasyonları mümkün (ADR-010 drift tablosu ile uyumlu).

---

## Terim → modül eşlemesi (ADR-010 sözlük doğrulaması)

| ADR-010 terimi | Birincil modül(ler) | Birleşik modül var mı? | Drift / not |
|----------------|---------------------|------------------------|-------------|
| **guard** | `lumos_gate`, `task_dispatch`, `write_interceptor`, `workspace_contract`, `device_guard`, `guard_audit` | Hayır | En dağınık terim |
| **policy** | `action_policy.py`, `device_action_policy.py`, `profiles.py` (matris) | Kısmen (matris) | Policy ≠ permission ayrımı korunmalı |
| **trust** | *(kod yok)* → `startup_health`, `LockState`, `presence_lock`, panel adapter | Hayır (ADR-007 hedef) | Terim çoğunlukla ADR/docs |
| **lock** | `LockState`, `_lock_ok`, panel `keystore_state` | Var (`LockState`) | **Semantik kayma doğrulandı** |
| **presence** | `presence_lock.py`, `presence_fsm.py` | Demo | Trust sinyali |
| **permission** | `profiles.py`, `permissions.py` (stub), `controlled_bridge` | Profil matrisi var | Stub lease gerçek değil |
| **consent** | `effective_consent`, `action_policy`, `panel_bridge_state` | Parçalı | consent ≠ confirmation |
| **confirmation** | `pending_approval`, `lumos_gate`, `task_dispatch`, `patch_pending` | Parçalı | İşlem bazlı onay |
| **sandbox** | `workspace_contract`, `write_interceptor`, `controlled_bridge` | Kısmen | Demo-safe sınır |
| **local demo** | `archive/panel` mockState, panel guidance | Panel adapter | Production iddiası yok |
| **private_layer_required** | `profiles` EXTERNAL/CRITICAL, `controlled_bridge` mail blok | Sözleşme | Public'te prod yok |

---

## Doğrulanan drift riskleri (ADR-010 § Repo drift)

| Risk | Doğrulama | Etkilenen terimler | Önerilen sonraki adım |
|------|-----------|-------------------|----------------------|
| **`LockState` vs `_lock_ok`** | `_lock_ok` = keystore init; `LockState.unlocked` = passphrase yüklü — **farklı** | lock, trust | Ayrı checkpoint; bu map düzeltmez |
| **Panel consent vekili** | Canlı path `panel_bridge_state`; `policy-engine.js` yalnızca arşiv | consent, panel görünürlüğü | Arşiv mock ≠ runtime; UI birincil kaynak read adapter |
| **CLI LOCKED vs runtime** | `get_durum_parts` lock_ok = `_lock_ok`; CLI metin ayrı öncelik | lock, locked | Terminoloji disiplini; kod birleştirme değil |
| **Panel mock** | `archive/panel/js/fixtures.js`, `mockState` — arşiv | local demo | Public demo etiketi korunmalı |
| **`packages/kando_policy` ayna** | `archive/packages/kando_policy/action_policy.py` — canonical `src/policy` | policy | ADR-003; import map ayrı checkpoint |
| **Gate allow + profil deny** | `lumos_gate` + `profiles` ayrı katman — her ikisi canlı | guard, policy, permission | Firewall birleştirme öncesi sözleşme |
| **`SECURITY_NEVER_AUTO` gap** | Tanım `profiles.py`; enforce `inviolable` referans — tam engine branch yok | irreversible action | ADR-006 risk tablosu ile birlikte |
| **Gate–sensitivity kopukluğu** | `change_sensitivity` gate'ten bağımsız import | guard | CRITICAL path + düşük gate riski mümkün |

---

## Guard ≠ trust ayrımı (kod kanıtı)

| Soru | Guard cevabı (modül) | Trust cevabı (modül) |
|------|----------------------|----------------------|
| Bu adım yürütülebilir mi? | `lumos_gate`, `task_dispatch`, `profiles`, `action_policy` | — |
| Kök anahtar / consent / presence durumu? | — | `LockState`, `effective_consent`, `presence_lock`, `get_durum_parts` |
| Panelde ne görünüyor? | — (yalnızca gösterim) | `panel_bridge_state` guidance |

**Sonuç:** Guard katmanları trust sinyallerini **tüketmiyor** (merkezi trust engine yok); ADR-010 ayrımı repo gerçeğiyle **uyumlu**.

---

## Policy ≠ permission ayrımı (kod kanıtı)

| | policy | permission |
|---|--------|------------|
| **Kural tanımı** | `action_policy.check_policy`, `profiles.STEP_PERMISSION_MATRIX` | — |
| **Uygulama anı grant** | — | `may_execute_step_at_runtime`, `is_allowed_for_profile` |
| **Stub** | — | `PermissionManager.acquire` no-op |

---

## Consent ≠ confirmation ayrımı (kod kanıtı)

| | consent | confirmation |
|---|---------|--------------|
| **Kalıcı / oturum** | `consent.json`, `effective_consent`, session_consent | — |
| **Tek işlem** | — | `pending_approval`, gate risk→onay, `patch_pending_approval` |
| **Policy red** | `consent_required` (identity/keystore) | offline_mode, koruma_aktif_delete |

---

## Public / private sınır (guard-policy-trust taraması)

| Public repo'da (doğrulandı) | Public'te yok / private katman |
|-----------------------------|--------------------------------|
| Terminoloji + usage map (bu belge) | Prod auth, prod lock/presence enforcement |
| Demo-safe stub (`integrations/mail/`, vault adapter) | Mail OAuth prod, vault PoC runbook (ops vault) |
| `controlled_bridge` mail regex blok | Connector credential, provider impl |
| `local_demo` panel guidance | Operasyonel backend trust skoru |
| Parçalı guard/trust **kavram** ayrımı | Birleşik Trust Engine / AI Firewall |

OD-031 Phase 2 Step 4 boundary sync sonrası **mail drift guard/policy kodunda tespit edilmedi**.

---

## ADR-006 / ADR-007 ile çapraz referans

| ADR | Usage map bekleyen alan | Bu checkpoint |
|-----|-------------------------|---------------|
| ADR-006 (guard/firewall) | Guard dokunuş noktaları tablosu | **Tamamlandı** — § Giriş noktası haritası; ADR **kabul edildi** (2026-06-21) |
| ADR-007 (trust engine) | Trust state sinyalleri | **Tamamlandı** — trust kod yok; sinyaller haritalandı |
| ADR-010 (terminoloji) | Terim→kod eşlemesi | **Tamamlandı** — § Terim→modül |

**Sonraki (bu belge dışı):** ADR-007 karar metni revizyonu, lock semantiği birleştirme **ayrı checkpoint** (ADR-006 ve ADR-010 finalize tamamlandı).

---

## Ne yapılmadı (bilinçli)

- Kod, import, test veya davranış değişikliği
- Lock semantiği birleştirme (`_lock_ok` vs `LockState`)
- Yeni trust engine veya guard birleştirme
- Panel UI / mock kaldırma
- Infisical runbook rename (opsiyonel P1 — Kalem 3 dışı)

---

## Sonraki gözden geçirme

1. ADR-010 **kabul edildi** (2026-06-21) — bkz. [ADR-010](../decisions/ADR-010-guard-policy-trust-terminology.md)
2. ADR-006 **kabul edildi** (2026-06-21) — bkz. [ADR-006](../decisions/ADR-006-ai-firewall-guard-layer.md)
3. ADR-007 § İlk güvenli adım — trust sinyal tablosu revizyonu
4. Lock semantiği — **ayrı ADR/checkpoint** (usage map sonrası onay)
5. `packages/kando_policy` import drift — ADR-003 dar import map (ADR-008 disiplini)

---

Son güncelleme: 2026-06-21 (Kalem 3 sonrası — ADR-010 usage map checkpoint)
