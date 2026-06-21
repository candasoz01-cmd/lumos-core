# ADR-012 Enforcement — Karar Matrisi (tavsiyesiz)

| Alan | Değer |
|------|-------|
| Durum | Salt okuma analiz — karar bekliyor (2026-06-21) |
| Referans | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [enforcement prep assessment](ADR-012-enforcement-prep-assessment.md), [runtime enforcement map](lumos-runtime-enforcement-map.md) |
| Kapsam | Altı açık karar maddesi için açıklama, fayda/risk, etkilenen bileşenler, geri dönüş maliyeti |
| Yasak | Bu belgede **tavsiye, önerilen seçenek veya tercih sütunu yoktur** |

## Amaç

[ADR-012 enforcement prep assessment](ADR-012-enforcement-prep-assessment.md) §5'te listelenen altı karar maddesini, enforcement uygulaması öncesinde insan onayına sunulacak **nötr** bir karar matrisine dönüştürmek. Her madde için seçenekler tanımlanır; fayda ve riskler ayrı listelenir; etkilenen dosya/bileşenler ve geri dönüş maliyeti değerlendirilir.

**Not:** Bu belge karar **vermez**; yalnızca karar verilecek alanları yapılandırır.

---

## Madde 1 — PR-C6 wiring kapsamı (shadow vs consume_confirmation birleşimi)

### Açıklama

PR-C6 (#462), köprü (bridge) yüksek riskli görevlerinde CU4 confirmation namespace'ine **shadow adapter** ekledi: `attach_bridge_pending_confirmation` paralel olarak `.lumos/pending_confirmations/` altına grant yazar; köprü onay/yürütme akışı ise legacy `.lumos/pending_approvals/` + `approval_token` üzerinden devam eder. Panel ve CLI mutasyon yollarında `consume_confirmation` **wired**; köprü approve/resume yolunda **yok**.

**Seçenek A — Shadow adapter yeterli (mevcut durum korunur):** Köprü risk kaydı oluşturulurken shadow grant yazılır; onay sonrası yürütme legacy `approval_token` doğrulaması ile kalır; iki namespace paralel yaşar.

**Seçenek B — Tek yol birleşimi:** Köprü approve/resume yürütmesi `consume_confirmation` + `LUMOS_CONFIRMATION_ENABLED` opt-in env ile panel/CLI ile aynı CU4 zincirine bağlanır; legacy `pending_approvals` / `approval_token` ya kaldırılır ya da geçiş süresince ikili desteklenir.

**Ek alt karar (her iki seçenekte de geçerli):** Legacy `pending_approvals` ne kadar süre korunacak — kalıcı paralel mi, deprecate + migration mi, anında kesme mi.

### Faydalar

**Seçenek A (shadow):**
- Mevcut köprü istemcileri ve `approval_token` sözleşmesi bozulmaz (#462 merge davranışı korunur).
- CU4 grant kaydı audit/izlenebilirlik için paralel oluşur; panel/CLI ile namespace hizası dokümante edilir.
- Opt-in confirmation env kapalıyken köprü akışı etkilenmez.

**Seçenek B (birleşim):**
- Tek onay tüketim yolu — duplicate onay veya onaysız yürütme riski azalır (codex C3/C6 hizası).
- Panel, CLI ve köprü aynı `confirmation_policy` grant store'unu paylaşır.
- E2E confirmation testleri (#459, #460) köprü yüzeyine genişletilebilir.

### Riskler

**Seçenek A (shadow):**
- İki bağımsız onay mekanizması — köprü yürütmesi CU4 grant tüketmeden devam edebilir.
- Shadow grant ile legacy onay arasında tutarsızlık (biri onaylı, diğeri değil) algılanabilir.
- PR-C6 "kısmi" durumu codex kapanışını engellemeye devam eder.

**Seçenek B (birleşim):**
- Mevcut köprü istemcileri `approval_token` → CU4 grant migration gerektirir.
- `LUMOS_CONFIRMATION_ENABLED` opt-in iken birleşim tam etkisiz kalabilir (env kapalı = no-op).
- Geçiş süresinde ikili path desteği karmaşıklık ve regresyon riski taşır.

### Etkilenecek dosyalar / bileşenler

| Bileşen | Yol | Rol |
|---------|-----|-----|
| Shadow adapter | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` (~L1161–1168) | Risk kaydında `attach_bridge_pending_confirmation` |
| Dispatch risk path | `packages/kando_runtime/src/kando_runtime/task_dispatch.py` (~L695–702) | Aynı shadow grant yazımı |
| CU4 modülü | `src/policy/confirmation_policy.py` | `attach_bridge_pending_confirmation`, `consume_confirmation`, `is_confirmation_enabled` |
| Köprü approve handler | `packages/kando_bridge/src/kando_bridge/server.py` (~L2230–2288) | `approval_token` doğrulama, yürütme tetikleme |
| Cursor bridge approve | `src/kando/cursor_bridge.py` (~L720+) | `_handle_approve_goal`, `pending_approvals.json` |
| Gate yürütme resume | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` (~L2617+ `lumos_gate_execute`) | Yüksek risk resume |
| Grant store | `.lumos/pending_confirmations/` | CU4 grant dosyaları |
| Legacy store | `.lumos/pending_approvals/` | Köprü onay kayıtları |
| Testler | `tests/test_confirmation_policy.py`, `tests/test_panel_bridge_codex_gate.py` | CU4 gate davranışı |
| Dokümantasyon | `docs/analysis/lumos-cu4-confirmation-skeleton-draft.md` §4.1 | PR-C6 durum kaydı |

### Geri dönüş maliyeti

| Seçenek | Maliyet | Gerekçe |
|---------|---------|---------|
| A — Shadow korunur | **Düşük** | #462 merge durumuna dönüş; ek kod değişikliği gerekmez |
| B — Birleşim uygulanır, geri alınır | **Orta–yüksek** | Approve handler, dispatch ve gate'de wiring geri sarılır; migration verisi (`pending_confirmations`) temizlenmesi gerekebilir; köprü istemci sözleşmesi değişmiş olur |

---

## Madde 2 — P2 genişletme sınırı (dar engine vs tam eşleme tablosu)

### Açıklama

P2 (#463), `SECURITY_NEVER_AUTO` kümesi için TaskEngine'de **dar** bir branch ekledi: `is_security_never_auto()` / `get_security_never_auto_member()` helper ile `step.kind` / `action_key` eşleşince `BLOCK_SECURITY_NEVER_AUTO`; `permanent_delete` engine scope **dışında** (TaskStore + panel #445/#454 yolu). Küme üyeleri (`external_write`, `irreversible_user_op`, `critical_system_config`) sözleşme terimleridir; `STEP_PERMISSION_MATRIX` yalnızca `analyze`…`critical` step türlerini bilir — tag eşleşmeyen yollar engine branch'i bypass edebilir.

**Seçenek A — Dar engine branch (mevcut #463 kapsamı):** Engine döngüsünde yalnızca helper ile doğrudan eşleşen `step.kind` / `action_key` / `action_tag` durdurulur; `permanent_delete` store/panel yolunda kalır; policy/action sabitleri genişletilmez.

**Seçenek B — Tam eşleme tablosu:** `action_policy`, panel/CLI action sabitleri, step metadata ve engine için resmi `SECURITY_NEVER_AUTO` × action/kind eşleme tablosu eklenir; helper tüm yüzeylerde aynı tabloyu kullanır.

### Faydalar

**Seçenek A (dar):**
- Minimal kod yüzeyi; #463 merge davranışı korunur.
- Mevcut profil matrisi (`external`/`critical` → `DECISION_LAYER_NEVER`) ve ActionRegistry savunması ile çakışma riski düşük.
- Test kapsamı sınırlı kalır (`tests/test_security_never_auto_engine.py`).

**Seçenek B (tam tablo):**
- Küme üyelerinin tüm silme/yazma/yürütme yollarında tutarlı red.
- Tek kaynak eşleme — profil matrisi, policy gate ve engine arasında drift azalır.
- Codex C6 (stop-on-risk) ve CU6 (geri dönüşsüz otomatik yok) kanıt zinciri güçlenir.

### Riskler

**Seçenek A (dar):**
- Tag eşleşmeyen `external_write` vb. engine branch'i atlayabilir.
- Policy, engine ve bridge risk gate arasında farklı koruma seviyeleri kalır.
- Codex "SECURITY_NEVER_AUTO tüm silme/yazma yolları" checkpoint'i tam kapanmaz.

**Seçenek B (tam tablo):**
- Matris genişlemesi breaking change ve false positive riski (meşru adımların durması).
- `profiles.py`, `action_policy.py`, panel action sabitleri ve testler senkron tutulmalı.
- Bakım yükü — yeni action eklenince tablo güncellemesi zorunlu.

### Etkilenecek dosyalar / bileşenler

| Bileşen | Yol | Rol |
|---------|-----|-----|
| Küme tanımı | `src/task_engine/profiles.py` (L47–113) | `SECURITY_NEVER_AUTO`, helper API |
| Engine branch | `src/task_engine/engine.py` (L531–594) | `_step_security_never_auto_member`, `run_task` döngüsü |
| Inviolable check | `src/core/inviolable.py` | Küme bütünlük doğrulama |
| ActionRegistry | `src/task_engine/action_registry.py` | `external`/`critical` executor red |
| Policy gate | `src/policy/action_policy.py` | Hardcoded action listesi |
| Kalıcı silme | `src/core/workspace_contract.py` | `may_perform_permanent_delete` |
| Panel delete | `panel/scripts/panel_tasks_server.py` | delete-permanent gate (#445) |
| CLI mutation | `src/cli/cli_tasks_mutation.py` | Policy + confirmation |
| Bridge risk | `src/kando/cursor_bridge.py`, `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | Yüksek risk gate (ayrı modül) |
| Testler | `tests/test_security_never_auto_engine.py` | Helper + engine branch |
| Analiz | `docs/analysis/security-never-auto-p2-and-helper-proposal.md` | Gap haritası |

### Geri dönüş maliyeti

| Seçenek | Maliyet | Gerekçe |
|---------|---------|---------|
| A — Dar branch korunur | **Düşük** | #463 merge durumu; tablo eklenmedi |
| B — Tam tablo uygulanır, geri alınır | **Orta–yüksek** | Çoklu modülde eşleme tablosu ve policy genişlemesi geri sarılır; false positive düzeltmeleri gerekmiş olabilir |

---

## Madde 3 — Trust Faz 4 zamanlaması ve sinyaller

### Açıklama

ADR-011 Faz 1–3 (#436–#438) tamamlandı; **Faz 4** (ADR-007 trust motor tüketimi) bekliyor. Repo'da merkezi trust motoru yok; sinyaller dağınık: `keystore_ready` (`startup_health`), `session_unlocked` (`LockState`), `consent` (`effective_consent`), panel'de `session_unlocked` runtime'dan okunmuyor. Codex C3 (onay + kanıt) kapanışı için trust kanıt zinciri genişletmesi açık.

**Seçenek A — Codex kapanış öncesi zorunlu:** PR-C6 wiring ve/veya P2 genişlemesinden önce veya eşzamanlı olarak Trust Faz 4 uygulanır; panel `session_unlocked` runtime `LockState`'ten okunur.

**Seçenek B — Köprü + P2 sonrası:** Mevcut dağınık sinyaller korunur; Trust Faz 4 ayrı checkpoint olarak PR-C6/P2 tamamlandıktan sonra planlanır.

**Ek alt karar:** Panel'de `session_unlocked` — runtime `LockState` doğrudan mı, trust motor snapshot'ı mı, yoksa mevcut env/consent vekili mi kalacak.

### Faydalar

**Seçenek A (önce trust):**
- `keystore_ready` ≠ `session_unlocked` drift tek motor altında çözülür (ADR-011, ADR-007 hizası).
- Policy `koruma_active` ve panel read payload tutarlı sinyal kullanır.
- Codex C3 kanıt zinciri merkezi trust tüketimi ile tamamlanabilir.

**Seçenek B (sonra trust):**
- Köprü confirmation ve P2 daraltması bağımsız ilerler; trust motoru büyük parça olarak ayrılır.
- Mevcut CLI `durum`/`hazir` ayrımı (#436–#438) bozulmaz.
- Public OSS sınırında minimal kod değişikliği ile Faz-2 dalgası kapatılabilir.

### Riskler

**Seçenek A (önce trust):**
- Trust motor tasarımı/uygulaması Faz-2 enforcement takvimini geciktirir.
- Panel process modeli (ayrı HTTP sunucu vs CLI runtime) LockState erişimini karmaşıklaştırabilir.
- ADR-007 kapsamı genişlerse public/private sınır ihlali riski.

**Seçenek B (sonra trust):**
- Panel `koruma_active` env vekili ile kalır — yanlış delete/mutation izni algısı devam eder.
- Dağınık sinyaller codex kapanış kanıtında zayıf nokta kalır.
- İki lock sinyali (`keystore_ready`, `session_unlocked`) birleştirilmeden enforcement katmanları farklı anlam taşır.

### Etkilenecek dosyalar / bileşenler

| Bileşen | Yol | Rol |
|---------|-----|-----|
| Lock state | `src/security/lock.py` | `LockState`, passphrase unlock |
| Startup health | `src/core/startup_health.py` | `keystore_ready`, `consent_ok`, `_lock_ok` |
| Panel policy context | `src/core/panel_bridge_state.py` (L48–66) | `koruma_active`, env vekili |
| Panel server | `panel/scripts/panel_tasks_server.py` | Read payload, policy gate |
| CLI durum/hazir | `src/cli/cli_router.py`, `src/core/lumos_runtime.py` | İki lock sinyali gösterimi |
| Presence | `src/security/presence_lock.py` | Presence sinyali |
| Permissions stub | `src/security/permissions.py` | `PermissionManager` lease |
| Lumos runtime | `src/core/lumos.py` | `lock_state` alanı |
| ADR | `docs/decisions/ADR-007-trust-engine-layer.md`, `docs/decisions/ADR-011-lock-semantics-decision.md` | Trust sözleşmesi |
| Usage map | `docs/analysis/ADR-010-guard-policy-trust-usage-map.md` | Sinyal haritası |

### Geri dönüş maliyeti

| Seçenek | Maliyet | Gerekçe |
|---------|---------|---------|
| A — Trust Faz 4 uygulanır, geri alınır | **Yüksek** | Yeni trust motor modülü, panel/CLI/policy entegrasyonu geri sarılır; sinyal sözleşmesi değişmiş olur |
| B — Trust ertelenir (mevcut) | **Düşük** | Dağınık sinyaller korunur; ek trust kodu yok |

---

## Madde 4 — Sensitivity ↔ gate entegrasyonu

### Açıklama

`change_sensitivity` (`classify_sensitivity`) CRITICAL/HIGH path etiketlemesi yapar; tüketiciler: `write_interceptor`, `decision_explorer`, `change_plan`. `lumos_gate` risk skoru ayrı prompt/runtime mantığı kullanır — `change_sensitivity` import veya kullanım **yok** (enforcement map gap). ADR-006 zincirinde sensitivity ↔ gate kopukluğu kayıtlı.

**Seçenek A — Ayrı katmanlar (mevcut):** `classify_sensitivity` patch pipeline'da kalır; `lumos_gate` kendi risk skorunu kullanır; iki sistem paralel.

**Seçenek B — Tek zincir birleşimi:** `lumos_gate` risk değerlendirmesinde `classify_sensitivity` çıktısı kullanılır veya birleşik eşik politikası tanımlanır; CRITICAL path + gate risk tek karar noktasında birleşir.

**Ek alt karar:** Eşik politikası — HIGH/CRITICAL hangi gate moduna (`no_op`, `agent`, pending approval) map edilecek.

### Faydalar

**Seçenek A (ayrı):**
- Mevcut `write_interceptor` ve gate davranışı değişmez.
- Patch pipeline ve köprü reasoning ayrı sorumluluk alanları kalır.
- Düşük regresyon riski.

**Seçenek B (birleşik):**
- CRITICAL path değişiklikleri köprü risk gate ile tutarlı değerlendirilir.
- Codex C6 (stop-on-risk) tek sinyal zincirinde kanıtlanabilir.
- `decision_explorer` ve gate aynı hassasiyet sınıflandırmasını paylaşır.

### Riskler

**Seçenek A (ayrı):**
- Düşük gate risk skoru + CRITICAL sensitivity kombinasyonunda tutarsız davranış.
- İki bağımsız "dur" mekanizması — hangisinin baskın olduğu belirsiz kalabilir.
- ADR-006 gap codex kapanışında açık madde olarak kalır.

**Seçenek B (birleşik):**
- Gate prompt sözleşmesi ve runtime assert değişir; köprü görev regresyonu.
- Path tabanlı sensitivity ile intent tabanlı gate risk farklı girdi türleri — yanlış eşleme false positive/negative.
- Eşik politikası tanımı ve test kapsamı genişler.

### Etkilenecek dosyalar / bileşenler

| Bileşen | Yol | Rol |
|---------|-----|-----|
| Sensitivity sınıflandırma | `src/core/change_sensitivity.py` (L26–89) | `classify_sensitivity`, CRITICAL heuristic |
| Write interceptor | `src/core/write_interceptor.py` (L77+) | CRITICAL/HIGH → patch pipeline |
| Decision explorer | `src/core/decision_explorer.py` (L110+) | HIGH/CRITICAL özet |
| Change plan | `src/core/change_plan.py` | Patch plan etiketi |
| Lumos gate | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` (~L1440+ risk path) | LLM reasoning, `no_op` / pending approval |
| Task dispatch | `packages/kando_runtime/src/kando_runtime/task_dispatch.py` | Dispatch risk dallanması |
| Guard audit | `src/core/guard_audit.py` | Audit trail |
| Dokümantasyon | `docs/analysis/lumos-runtime-enforcement-map.md` §4, `docs/analysis/ADR-006-010-011-chain-summary.md` | Gap kaydı |

### Geri dönüş maliyeti

| Seçenek | Maliyet | Gerekçe |
|---------|---------|---------|
| A — Ayrı katmanlar | **Düşük** | Mevcut durum; entegrasyon kodu yok |
| B — Birleşim uygulanır, geri alınır | **Orta** | Gate risk path ve olası dispatch dallanması geri sarılır; eşik politikası config kaldırılır |

---

## Madde 5 — Confirmation varsayılanı (opt-in vs default-on)

### Açıklama

CU4 confirmation (#452–#458) **opt-in**: `LUMOS_CONFIRMATION_ENABLED=true|1|yes` iken 3. kapı aktif; varsayılan (env yok/false) → no-op. #461 docs kararı: **opt-in korunur**; tam varsayılan-on ürün incelemesine ertelendi (DL-C18). Kod değişmedi.

**Seçenek A — Opt-in kalıcı:** `is_confirmation_enabled()` varsayılan False; confirmation yalnızca env açıkken panel/CLI/köprüde (eğer wired) devreye girer.

**Seçenek B — Default-on:** Env yok veya true iken confirmation aktif; explicit `LUMOS_CONFIRMATION_ENABLED=false` ile kapatılır.

**Ek alt karar (Seçenek B için):** Tam varsayılan-on öncesi hangi kapılar kapanmalı — E2E kanıt (#459, #460), false positive profili, köprü duplicate onay (PR-C6 gap).

### Faydalar

**Seçenek A (opt-in):**
- Mevcut panel/CLI davranışı (#443–#449) env olmadan aynı kalır.
- False positive ve UX sürtünmesi prod'da varsayılan olarak oluşmaz.
- #461 kararı ve DL-C18 ile uyumlu.

**Seçenek B (default-on):**
- Codex C3 üçüncü kapı prod'da varsayılan olarak devrede.
- Kullanıcı onayı olmadan `write_local` mutasyonları ek koruma alır.
- CU4 sözleşmesi tam anlamıyla "açık onay zorunlu" ilkesine yaklaşır.

### Riskler

**Seçenek A (opt-in):**
- Prod'da 3. kapı kapalı kalabilir — bilinçli (#461) ama codex C3 tam enforcement değil.
- Köprü duplicate onay gap'i opt-in kapalıyken daha az görünür.
- UX drift: dokümantasyon "confirmation var" der, varsayılan davranış farklı.

**Seçenek B (default-on):**
- Mevcut otomasyon/scriptler env ayarlamadan confirmation grant bekler — kırılma.
- False positive: meşru mutasyonlar modal/onay bekler; panel E2E dışı akışlar etkilenir.
- PR-C6 köprü wiring gap'i default-on ile birleşince duplicate veya çift blok riski artar.

### Etkilenecek dosyalar / bileşenler

| Bileşen | Yol | Rol |
|---------|-----|-----|
| Env gate | `src/policy/confirmation_policy.py` (L101–104) | `is_confirmation_enabled` |
| Panel gate | `src/core/panel_bridge_state.py` (L157–187) | `task_action_gate` 3. kapı |
| Panel server | `panel/scripts/panel_tasks_server.py` | `ensure_panel_mutation_confirmation`, `/lumos-confirm/*` |
| CLI mutation | `src/cli/cli_tasks_mutation.py` | `ensure_cli_mutation_confirmation` |
| CLI onayla | `src/cli/cli_router.py` (#458) | Grant tüketimi |
| Testler | `tests/test_panel_bridge_codex_gate.py`, E2E (#459, #460) | Opt-in env ile kanıt |
| ADR / decision log | `docs/decisions/ADR-012-lumos-security-codex.md` §7, `docs/decision-log.md` DL-C18 | Varsayılan-on kararı |
| CU4 draft | `docs/analysis/lumos-cu4-confirmation-skeleton-draft.md` | False positive tablosu |

### Geri dönüş maliyeti

| Seçenek | Maliyet | Gerekçe |
|---------|---------|---------|
| A — Opt-in (mevcut) | **Düşük** | Tek satır env gate; #461 durumu |
| B — Default-on uygulanır, geri alınır | **Orta** | `is_confirmation_enabled` default flip + dokümantasyon sync; kullanıcı/CI env beklentileri değişmiş olur; testler güncellenmeli |

---

## Madde 6 — Panel LockState (env vekili vs runtime LockState)

### Açıklama

Panel policy context (`_panel_policy_context`) `koruma_active` değerini runtime `LockState` yerine `LUMOS_SESSION_UNLOCKED` env vekilinden türetir: env `true|1|yes` değilse koruma aktif sayılır. CLI `hazir` komutu `LockState.is_locked()` kullanır; panel read payload'da `session_unlocked` runtime doğrulanmaz (ADR-011 Faz 4 gap). Policy delete gate (`koruma_active` + delete) panelde env'e bağlı.

**Seçenek A — Env vekili korunur:** Panel sunucusu ayrı process olarak `LUMOS_SESSION_UNLOCKED` (ve consent) env ile policy context oluşturur; runtime `LockState` doğrulanmaz.

**Seçenek B — Runtime LockState bağlantısı:** Panel sunucusu CLI runtime ile aynı process'te veya IPC/shared state ile `LockState` / `CoreState.lock_status()` okur; env vekili kaldırılır veya yalnızca fallback.

**Ek alt karar:** Process model — panel embedded mi, ayrı HTTP sunucu mu; LockState erişim mekanizması (shared memory, socket, startup sync).

### Faydalar

**Seçenek A (env vekili):**
- Panel bağımsız process olarak çalışmaya devam eder; CLI runtime'a bağlı değildir.
- Mevcut testler (`LUMOS_SESSION_UNLOCKED` monkeypatch) çalışır.
- Minimal altyapı değişikliği.

**Seçenek B (runtime LockState):**
- CLI ve panel aynı kilit gerçeğini yansıtır — ADR-011 session_unlocked enforcement hizası.
- Env unutulması veya yanlış set edilmesi ile policy bypass riski azalır.
- Codex C6 koruma+delete gate gerçek runtime sinyaline dayanır.

### Riskler

**Seçenek A (env vekili):**
- Env set edilmemiş panel her zaman koruma aktif veya tersi davranabilir — drift.
- Kullanıcı CLI'da kilidi açmış olsa panel farklı `koruma_active` gösterebilir.
- ADR-011 Faz 4 ve codex kapanışında açık madde kalır.

**Seçenek B (runtime LockState):**
- Panel process modeli değişikliği gerekebilir (embedded server, state paylaşımı).
- Ayrı process panel LockState'e erişemezse yeni IPC katmanı.
- Mevcut panel deployment/script akışları (`panel_tasks_server.py` standalone) etkilenir.

### Etkilenecek dosyalar / bileşenler

| Bileşen | Yol | Rol |
|---------|-----|-----|
| Panel policy context | `src/core/panel_bridge_state.py` (L48–66, L900–925) | `koruma_active`, gate reason |
| Panel server | `panel/scripts/panel_tasks_server.py` | HTTP API, read payload |
| Lock state | `src/security/lock.py` | `LockState`, `is_locked()` |
| Core state | `src/core/lumos.py`, `src/core/lumos_runtime.py` | Runtime bootstrap, lock_status |
| Policy | `src/policy/action_policy.py` | `koruma_active` + delete red |
| Startup health | `src/core/startup_health.py` | `keystore_ready` vs session |
| Testler | `tests/test_panel_bridge_codex_gate.py`, `tests/test_panel_restore_policy_gate.py` | Env monkeypatch |
| ADR | `docs/decisions/ADR-011-lock-semantics-decision.md` | İki lock sinyali, Faz 4 |

### Geri dönüş maliyeti

| Seçenek | Maliyet | Gerekçe |
|---------|---------|---------|
| A — Env vekili (mevcut) | **Düşük** | Mevcut panel deployment |
| B — Runtime LockState uygulanır, geri alınır | **Orta–yüksek** | Process model / IPC değişikliği geri sarılır; panel startup scriptleri etkilenmiş olur |

---

## Karar matrisi

| # | Karar konusu | Seçenek A | Seçenek B | Fayda özeti | Risk özeti | Etkilenen alan | Geri dönüş maliyeti | Karar durumu |
|---|--------------|-----------|-----------|-------------|------------|----------------|---------------------|--------------|
| 1 | PR-C6 wiring kapsamı | Shadow adapter; legacy `approval_token` yürütme | `consume_confirmation` + opt-in env ile köprü birleşimi | A: geriye uyum, düşük kırılma — B: tek onay yolu, CU4 hizası | A: duplicate onay, kısmi codex — B: migration, opt-in etkisizlik | `lumos_gate`, `task_dispatch`, `kando_bridge/server`, `confirmation_policy`, `cursor_bridge` | A: düşük — B geri alım: orta–yüksek | **bekliyor** |
| 2 | P2 genişletme sınırı | Dar engine branch (#463) | Tam action/kind eşleme tablosu | A: minimal diff — B: küme tam kapsama, drift azalması | A: tag bypass — B: false positive, matris bakımı | `profiles.py`, `engine.py`, `action_policy`, `action_registry`, panel/CLI | A: düşük — B geri alım: orta–yüksek | **bekliyor** |
| 3 | Trust Faz 4 zamanlaması | Codex kapanış öncesi zorunlu | Köprü + P2 sonrası erteleme | A: merkezi trust, sinyal birliği — B: bağımsız Faz-2 ilerleme | A: gecikme, process model — B: env drift, zayıf kanıt | `lock.py`, `startup_health`, `panel_bridge_state`, ADR-007/011 | A geri alım: yüksek — B: düşük | **bekliyor** |
| 4 | Sensitivity ↔ gate | Ayrı katmanlar (mevcut) | Birleşik zincir + eşik politikası | A: düşük regresyon — B: tutarlı stop-on-risk | A: kopuk gap — B: gate regresyon, eşik karmaşıklığı | `change_sensitivity`, `write_interceptor`, `lumos_gate`, `task_dispatch` | A: düşük — B geri alım: orta | **bekliyor** |
| 5 | Confirmation varsayılanı | Opt-in (#461, mevcut kod) | Default-on (`ENABLED` varsayılan true) | A: UX sürtünmesi yok — B: varsayılan 3. kapı | A: prod'da kapı kapalı — B: script kırılması, false positive | `confirmation_policy`, panel/CLI gate, E2E testler | A: düşük — B geri alım: orta | **bekliyor** (docs: opt-in #461) |
| 6 | Panel LockState | `LUMOS_SESSION_UNLOCKED` env vekili | Runtime `LockState` / trust snapshot | A: bağımsız panel process — B: CLI/panel kilit hizası | A: env drift, yanlış koruma algısı — B: process model değişimi | `panel_bridge_state`, `panel_tasks_server`, `lock.py`, `action_policy` | A: düşük — B geri alım: orta–yüksek | **bekliyor** |

---

## İlgili belgeler

| Belge | İçerik |
|-------|--------|
| [ADR-012 enforcement prep assessment](ADR-012-enforcement-prep-assessment.md) | Keşif özeti, risk listesi, karar maddeleri kaynağı |
| [ADR-012 Security Codex](../decisions/ADR-012-lumos-security-codex.md) | C1–C6 sözleşmesi, checkpoint tablosu |
| [Runtime enforcement map](lumos-runtime-enforcement-map.md) | Wired / shadow / gap haritası |
| [CU4 confirmation skeleton](lumos-cu4-confirmation-skeleton-draft.md) | PR-C6, false positive |
| [P2 SECURITY_NEVER_AUTO analiz](security-never-auto-p2-and-helper-proposal.md) | Engine branch, helper API |
| [ADR-011 lock semantics](../decisions/ADR-011-lock-semantics-decision.md) | İki lock sinyali, Faz 4 |

---

## Yasaklar (bu belge)

- Tavsiye veya önerilen seçenek sütunu **yoktur**
- Karar verilmez — tüm maddeler **bekliyor** (Madde 5 docs kaydı #461 ayrı; runtime kararı açık)
- Kod veya enforcement değişikliği **yapılmaz**
