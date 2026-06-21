# Lumos Core — Teknik Borç ve Mimari Yoğunlaşma Analizi

| Alan | Değer |
|------|-------|
| Durum | Salt okuma keşif (2026-06-21) — uygulama yok |
| Tarih | 2026-06-21 |
| Kapsam | Aktif kod + test yüzeyi; `archive/` referans olarak; kod değişikliği yok |
| Referans | [ADR-012 enforcement prep](ADR-012-enforcement-prep-assessment.md), [runtime enforcement map](lumos-runtime-enforcement-map.md), [proje haritası](../memory/project-map-runtime-entrypoints.md), [ADR zinciri özeti](ADR-006-010-011-chain-summary.md) |
| Yöntem | `wc -l`, `rg`, dosya okuma — kanıta dayalı; hipotezler açıkça etiketlenir |

## Executive summary

Bu rapor, önümüzdeki 3 ayda geliştirme hızını yavaşlatabilecek **20 teknik borç** noktasını kanıta dayalı listeler. Enforcement kararı veya uygulama önerisi **içermez**; borç perspektifine odaklanır. ADR-012 prep assessment ile uyumludur; çakışan maddeler çapraz referansla işaretlenir.

**Stratejik yatırım (yüksek mutlak etki, yüksek maliyet):** [#1 panel.astro](#td-01-panel-astro), [#2 köprü CU4 gap](#td-02-bridge-cu4-gap).

**Etki/maliyet önceliği (ilk 10):** [§ İlk 10 — Etki / Maliyet Oranı](#ilk-10--etki--maliyet-oranı).

---

## 20 Teknik Borç Maddesi — indeks

| # | Anchor | Kısa başlık | Risk |
|---|--------|-------------|------|
| 1 | [#td-01-panel-astro](#td-01-panel-astro) | `panel.astro` monolitik UI | kritik |
| 2 | [#td-02-bridge-cu4-gap](#td-02-bridge-cu4-gap) | Köprü onay yolu CU4 birleşmemiş | kritik |
| 3 | [#td-03-panel-lockstate-env](#td-03-panel-lockstate-env) | Panel koruma env vekili | kritik |
| 4 | [#td-04-lumos-gate-monolith](#td-04-lumos-gate-monolith) | `lumos_gate.py` yoğun sorumluluk | yüksek |
| 5 | [#td-05-cursor-bridge-hub](#td-05-cursor-bridge-hub) | `cursor_bridge.py` orchestration hub | yüksek |
| 6 | [#td-06-bridge-server-monolith](#td-06-bridge-server-monolith) | `kando_bridge/server.py` birleşimi | yüksek |
| 7 | [#td-07-panel-bridge-state](#td-07-panel-bridge-state) | `panel_bridge_state.py` birleşimi | yüksek |
| 8 | [#td-08-parallel-pending-stores](#td-08-parallel-pending-stores) | Paralel onay state mağazaları | yüksek |
| 9 | [#td-09-p2-never-auto-narrow](#td-09-p2-never-auto-narrow) | P2 `SECURITY_NEVER_AUTO` dar kapsam | yüksek |
| 10 | [#td-10-sensitivity-gate-gap](#td-10-sensitivity-gate-gap) | `change_sensitivity` ↔ gate kopuk | orta |
| 11 | [#td-11-trust-faz4-missing](#td-11-trust-faz4-missing) | Trust Faz 4 kod yok | yüksek |
| 12 | [#td-12-duplicate-runtime-state](#td-12-duplicate-runtime-state) | Duplicate `runtime_state` | orta |
| 13 | [#td-13-archive-parallel-code](#td-13-archive-parallel-code) | `archive/` paralel kod | orta |
| 14 | [#td-14-triple-panel-entry](#td-14-triple-panel-entry) | Üç katmanlı panel girişi | orta |
| 15 | [#td-15-lumos-runtime-bootstrap](#td-15-lumos-runtime-bootstrap) | `lumos_runtime.py` bootstrap | orta |
| 16 | [#td-16-cli-parse-monolith](#td-16-cli-parse-monolith) | `cli_parse.py` monolith | orta |
| 17 | [#td-17-quantum-dual-cli](#td-17-quantum-dual-cli) | Quantum çift CLI yüzeyi | düşük |
| 18 | [#td-18-confirmation-opt-in](#td-18-confirmation-opt-in) | Confirmation varsayılan kapalı | orta |
| 19 | [#td-19-task-dispatch-orchestrator](#td-19-task-dispatch-orchestrator) | `task_dispatch.py` orchestrator | orta |
| 20 | [#td-20-mega-panel-test](#td-20-mega-panel-test) | Mega panel test dosyası | orta |

---

## 20 Teknik Borç Maddesi

### 1. panel.astro monolitik UI yüzeyi {#td-01-panel-astro}

- **Kategori:** Oversized files / Single-file responsibility accumulation
- **Etkilenen dosyalar:** [`ui/src/pages/panel.astro`](../../ui/src/pages/panel.astro)
- **Risk seviyesi:** kritik
- **Tahmini bakım maliyeti:** yüksek (5–10 person-day)
- **Çözüm zorluğu:** yüksek
- **Çözülmezse oluşacak etki:** Panel UX, i18n, görev API, chat, bridge ve evidence akışları tek dosyada birleştiği için küçük değişiklikler geniş regresyon ve merge çatışması riski taşır.
- **Kanıt:** 15.497 satır; inline `<style>` ~4.238 satır (L52–L4290); inline `<script>` ~9.540 satır (L5954–L15494); `fetch(` / `addEventListener` / `function` eşleşmeleri 100+.

### 2. Köprü onay yolu CU4 confirmation ile birleşmemiş (shadow adapter) {#td-02-bridge-cu4-gap}

- **Kategori:** Duplicate implementations / Non-canonical surfaces
- **Etkilenen dosyalar:** [`packages/kando_bridge/src/kando_bridge/server.py`](../../packages/kando_bridge/src/kando_bridge/server.py), [`packages/kando_runtime/src/kando_runtime/lumos_gate.py`](../../packages/kando_runtime/src/kando_runtime/lumos_gate.py), [`packages/kando_runtime/src/kando_runtime/task_dispatch.py`](../../packages/kando_runtime/src/kando_runtime/task_dispatch.py), [`src/policy/confirmation_policy.py`](../../src/policy/confirmation_policy.py)
- **Risk seviyesi:** kritik
- **Tahmini bakım maliyeti:** yüksek (3–7 person-day)
- **Çözüm zorluğu:** yüksek
- **Çözülmezse oluşacak etki:** Panel/CLI confirmation zinciri ile köprü `approval_token` akışı paralel kalır; PR-C6 kapanmaz, enforcement drift devam eder.
- **Kanıt:** `kando_bridge/server.py` içinde `consume_confirmation` / `pending_confirmations` grep sonucu **0**; `_handle_approve` ~L2195+ `approval_token` doğrulaması; `attach_bridge_pending_confirmation` test edilir ([`tests/test_bridge_confirmation_adapter.py`](../../tests/test_bridge_confirmation_adapter.py)) ama approve sonrası consume testi yok; [ADR-012 prep](ADR-012-enforcement-prep-assessment.md) L43–45, L88–95.

### 3. Panel koruma sinyali env vekili — runtime LockState kopuk {#td-03-panel-lockstate-env}

- **Kategori:** Untested critical paths / Non-canonical surfaces
- **Etkilenen dosyalar:** [`src/core/panel_bridge_state.py`](../../src/core/panel_bridge_state.py), [`panel/scripts/panel_tasks_server.py`](../../panel/scripts/panel_tasks_server.py), [`src/security/lock.py`](../../src/security/lock.py)
- **Risk seviyesi:** kritik
- **Tahmini bakım maliyeti:** orta (2–4 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** Panel mutasyon gate'i `LUMOS_SESSION_UNLOCKED` env'ine dayanır; CLI `LockState.is_locked()` kullanır — aynı oturumda farklı güvenlik algısı oluşabilir.
- **Kanıt:** `panel_bridge_state.py` L61–65 env okuma; [ADR-012 prep](ADR-012-enforcement-prep-assessment.md) L14, L73–74; trust/LockState testleri yalnızca [`tests/test_panel_bridge_adr011_faz3.py`](../../tests/test_panel_bridge_adr011_faz3.py), [`tests/test_keystore_ready_rename.py`](../../tests/test_keystore_ready_rename.py) — `LockState` panel enforcement için doğrudan test yok.

### 4. lumos_gate.py yoğun sorumluluk kümesi {#td-04-lumos-gate-monolith}

- **Kategori:** Oversized files / God files / High dependency density
- **Etkilenen dosyalar:** [`packages/kando_runtime/src/kando_runtime/lumos_gate.py`](../../packages/kando_runtime/src/kando_runtime/lumos_gate.py)
- **Risk seviyesi:** yüksek
- **Tahmini bakım maliyeti:** yüksek (4–8 person-day parçalı ayrıştırma)
- **Çözüm zorluğu:** yüksek
- **Çözülmezse oluşacak etki:** Gate, dispatch, risk, evidence ve bridge intent mantığı tek modülde; enforcement genişlemesi her seferinde yüksek regresyon maliyeti doğurur.
- **Kanıt:** 2.799 satır; repo içi `lumos_gate` referansı 39 eşleşme (dosya içi + testler); `tests/test_*lumos_gate*` dosyası **yok** — doğrudan birim test dosyası bulunamadı.

### 5. cursor_bridge.py ikinci büyük orchestration hub'ı {#td-05-cursor-bridge-hub}

- **Kategori:** God files / High dependency density
- **Etkilenen dosyalar:** [`src/kando/cursor_bridge.py`](../../src/kando/cursor_bridge.py)
- **Risk seviyesi:** yüksek
- **Tahmini bakım maliyeti:** yüksek (4–8 person-day)
- **Çözüm zorluğu:** yüksek
- **Çözülmezse oluşacak etki:** Cursor APPROVE, pending_approvals, profil guard ve patch yürütme aynı dosyada; köprü/panel/CLI enforcement hizalaması zorlaşır.
- **Kanıt:** 3.253 satır (en büyük aktif Python dosyası); `pending_approvals` 15 eşleşme; `consume_confirmation` **0**; [`tests/kando/test_cursor_bridge_contract.py`](../../tests/kando/test_cursor_bridge_contract.py) 1.539 satır (sözleşme testi, CU4 consume kapsamı yok).

### 6. kando_bridge/server.py HTTP yüzeyi + onay yürütme birleşimi {#td-06-bridge-server-monolith}

- **Kategori:** Oversized files / Single-file responsibility accumulation
- **Etkilenen dosyalar:** [`packages/kando_bridge/src/kando_bridge/server.py`](../../packages/kando_bridge/src/kando_bridge/server.py)
- **Risk seviyesi:** yüksek
- **Tahmini bakım maliyeti:** orta–yüksek (3–6 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** Bridge API, transcribe, task post, approve ve evidence uçları tek handler dosyasında; güvenlik kapısı değişiklikleri geniş yüzeyi etkiler.
- **Kanıt:** 2.586 satır; `approval_token` 20+ eşleşme; `pending_approvals` 17 eşleşme.

### 7. panel_bridge_state.py read-state + policy gate + UX payload birleşimi {#td-07-panel-bridge-state}

- **Kategori:** Single-file responsibility accumulation / High dependency density
- **Etkilenen dosyalar:** [`src/core/panel_bridge_state.py`](../../src/core/panel_bridge_state.py), [`panel/scripts/panel_tasks_server.py`](../../panel/scripts/panel_tasks_server.py)
- **Risk seviyesi:** yüksek
- **Tahmini bakım maliyeti:** orta (2–5 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** `task_action_gate`, read payload, consent/profil metinleri ve evidence projeksiyonu aynı modülde; enforcement değişiklikleri tek dosyada yoğunlaşır.
- **Kanıt:** 970 satır; `task_action_gate` panel + testlerde 50+ referans; `panel_tasks_server.py` 11 `_task_actions_gate` / gate referansı, 1.482 satır.

### 8. Paralel onay state mağazaları (pending_approvals vs pending_confirmations) {#td-08-parallel-pending-stores}

- **Kategori:** Duplicate implementations
- **Etkilenen dosyalar:** [`src/policy/confirmation_policy.py`](../../src/policy/confirmation_policy.py), [`packages/kando_bridge/src/kando_bridge/server.py`](../../packages/kando_bridge/src/kando_bridge/server.py), [`src/kando/cursor_bridge.py`](../../src/kando/cursor_bridge.py), [`packages/kando_runtime/src/kando_runtime/task_dispatch.py`](../../packages/kando_runtime/src/kando_runtime/task_dispatch.py)
- **Risk seviyesi:** yüksek
- **Tahmini bakım maliyeti:** orta (2–4 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** İki grant namespace'i senkron tutulmak zorunda kalınır; shadow adapter yazsa da tüketmeyen yürütme yolu drift üretir.
- **Kanıt:** `pending_approvals` grep — 6 Python dosyası, çoklu eşleşme; `pending_confirmations` — 7 dosya; bridge approve handler CU4 consume kullanmıyor ([Madde 2](#td-02-bridge-cu4-gap) kanıtı).

### 9. P2 SECURITY_NEVER_AUTO engine kapsamı dar {#td-09-p2-never-auto-narrow}

- **Kategori:** Untested critical paths (kısmi) / Dead feature flags (policy gap)
- **Etkilenen dosyalar:** [`src/task_engine/engine.py`](../../src/task_engine/engine.py), [`src/task_engine/profiles.py`](../../src/task_engine/profiles.py), [`src/policy/action_policy.py`](../../src/policy/action_policy.py)
- **Risk seviyesi:** yüksek
- **Tahmini bakım maliyeti:** orta (2–3 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** `external_write`, `irreversible_user_op`, `critical_system_config` gibi üyeler action_key eşleşmesi olmadan engine dalını bypass edebilir ([ADR-012 prep](ADR-012-enforcement-prep-assessment.md) L44, L76–85).
- **Kanıt:** [`tests/test_security_never_auto_engine.py`](../../tests/test_security_never_auto_engine.py) mevcut; ADR-012 prep `include_permanent_delete=False` ve dar branch notu; `action_policy.py` yalnızca 101 satır — merkezi eşleme tablosu sınırlı.

### 10. change_sensitivity ↔ lumos_gate zinciri kopuk {#td-10-sensitivity-gate-gap}

- **Kategori:** Unused code paths / Duplicate implementations (paralel risk modelleri)
- **Etkilenen dosyalar:** [`src/core/change_sensitivity.py`](../../src/core/change_sensitivity.py), [`src/core/write_interceptor.py`](../../src/core/write_interceptor.py), [`packages/kando_runtime/src/kando_runtime/lumos_gate.py`](../../packages/kando_runtime/src/kando_runtime/lumos_gate.py)
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** orta (2–4 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** Patch pipeline CRITICAL/HIGH sınıflandırması ile gate risk skoru bağımsız kalır; aynı değişiklik farklı kapılardan farklı sonuç alabilir.
- **Kanıt:** [ADR-012 prep](ADR-012-enforcement-prep-assessment.md) L47, L98–105: `lumos_gate` içinde `change_sensitivity` import/use yok; [`tests/test_change_sensitivity.py`](../../tests/test_change_sensitivity.py), [`tests/test_write_interceptor_sensitivity.py`](../../tests/test_write_interceptor_sensitivity.py) mevcut — gate entegrasyon testi yok.

### 11. Trust Faz 4 (ADR-007) kod tabanında yok {#td-11-trust-faz4-missing}

- **Kategori:** Dead feature flags / Documented-only capability
- **Etkilenen dosyalar:** [`docs/decisions/ADR-007-trust-engine-layer.md`](../decisions/ADR-007-trust-engine-layer.md), [`src/security/`](../../src/security/), [`src/core/startup_health.py`](../../src/core/startup_health.py)
- **Risk seviyesi:** yüksek
- **Tahmini bakım maliyeti:** yüksek (5+ person-day — ürün kararına bağlı)
- **Çözüm zorluğu:** yüksek
- **Çözülmezse oluşacak etki:** Consent, keystore, session sinyalleri dağınık kalır; codex C3 kanıt zinciri tam kapanmaz.
- **Kanıt:** [ADR-012 prep](ADR-012-enforcement-prep-assessment.md) L32, L48: "Trust Faz 4 — Kod yok"; tests içinde `trust` / `TrustEngine` / `ADR-007` grep **0 dosya**.

### 12. Duplicate runtime_state modülleri {#td-12-duplicate-runtime-state}

- **Kategori:** Duplicate implementations
- **Etkilenen dosyalar:** [`src/core/runtime_state.py`](../../src/core/runtime_state.py), [`packages/kando_runtime/src/kando_runtime/runtime_state.py`](../../packages/kando_runtime/src/kando_runtime/runtime_state.py)
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** düşük–orta (1–2 person-day)
- **Çözüm zorluğu:** düşük–orta
- **Çözülmezse oluşacak etki:** Event/signal dosya yolları ve bellek içi state iki kopyada ayrışabilir; package vs src import karmaşası artar.
- **Kanıt:** `diff -q` çıktısı "Files differ"; 166 vs 142 satır; aynı modül docstring ve `_events_file()` / `LUMOS_BASE_DIR` yapısı.

### 13. archive/ paralel kod ve panel JS kalıntısı {#td-13-archive-parallel-code}

- **Kategori:** Non-canonical surfaces / Unused code paths
- **Etkilenen dosyalar:** [`archive/`](../../archive/) (16M), [`archive/panel/js/*.js`](../../archive/panel/js/) (11 dosya, ~10.258 satır), [`archive/packages/kando_core/src/kando_core/panel_bridge_state.py`](../../archive/packages/kando_core/src/kando_core/panel_bridge_state.py) (669 satır)
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** düşük–orta (1–3 person-day temizlik/plan)
- **Çözüm zorluğu:** düşük (silme kararı ayrı)
- **Çözülmezse oluşacak etki:** Grep ve yeni geliştiriciler aktif `src/` yerine arşiv kopyasını referans alabilir; canonical yüzey karışır.
- **Kanıt:** `du -sh archive` → 16M; arşiv `panel_bridge_state.py` 669 satır vs aktif 970 satır.

### 14. Üç katmanlı panel runtime girişi {#td-14-triple-panel-entry}

- **Kategori:** Non-canonical surfaces
- **Etkilenen dosyalar:** [`ui/src/pages/panel.astro`](../../ui/src/pages/panel.astro), [`panel/scripts/panel_tasks_server.py`](../../panel/scripts/panel_tasks_server.py), [`backend/index.js`](../../backend/index.js), [`archive/panel/js/`](../../archive/panel/js/)
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** orta (2–4 person-day dokümantasyon + yüzey birleştirme planı)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** Görev mutasyonları Python panel server'da, sosyal/feed/chat Node backend'de, UI tek astro dosyasında — uçtan uca davranış eşlemesi manuel kalır.
- **Kanıt:** `panel_tasks_server.py` REST + `/tasks.json` (L3–7, L693–699); `backend/index.js` 1.511 satır, `/posts/feed`, `/chat` vb.; [`docs/memory/project-map-runtime-entrypoints.md`](../memory/project-map-runtime-entrypoints.md) canonical zincir uyarısı.

### 15. lumos_runtime.py bootstrap yoğunlaşması {#td-15-lumos-runtime-bootstrap}

- **Kategori:** God files / High dependency density
- **Etkilenen dosyalar:** [`src/core/lumos_runtime.py`](../../src/core/lumos_runtime.py), [`src/main.py`](../../src/main.py), [`src/cli/cli_router.py`](../../src/cli/cli_router.py)
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** orta (2–4 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** CLI başlatma, observation, live brain, sandbox ve router context kurulumu tek dosyada; yeni CLI modları geniş import ağını büyütür.
- **Kanıt:** 943 satır; `create_runtime` birincil giriş (`src/main.py` L13–17); `policy` import yoğunluğu panel/CLI ile paylaşımlı.

### 16. cli_parse.py komut normalizasyon monolith'i {#td-16-cli-parse-monolith}

- **Kategori:** Oversized files / Single-file responsibility accumulation
- **Etkilenen dosyalar:** [`src/cli/cli_parse.py`](../../src/cli/cli_parse.py), [`src/cli/cli_router.py`](../../src/cli/cli_router.py)
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** orta (2–3 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** Yeni CLI komutları ve alias eşlemesi tek parser dosyasına eklenir; `cli_router.py` (247 satır) ile sorumluluk sınırı bulanıklaşır.
- **Kanıt:** `cli_parse.py` 629 satır; `cli_router.py` docstring "Extracted from main.py for stabilization" — parser hâlâ ayrı büyük modül.

### 17. Quantum readiness çift CLI yüzeyi (düşük drift) {#td-17-quantum-dual-cli}

- **Kategori:** Non-canonical surfaces (hafif)
- **Etkilenen dosyalar:** [`src/lumos_core/__main__.py`](../../src/lumos_core/__main__.py), [`src/lumos_core/quantum_readiness_cli.py`](../../src/lumos_core/quantum_readiness_cli.py), [`src/scripts/quantum_readiness_scan.py`](../../src/scripts/quantum_readiness_scan.py)
- **Risk seviyesi:** düşük
- **Tahmini bakım maliyeti:** düşük (0.5–1 person-day)
- **Çözüm zorluğu:** düşük
- **Çözülmezse oluşacak etki:** Scanner mantığı tek (`security.readiness.scanner`); script yalnızca stdout JSON — bakım maliyeti düşük ama iki entry point dokümantasyonu gerektirir.
- **Kanıt:** `quantum_readiness_cli.py` L17–18 "no duplicate scanner logic"; `quantum_readiness_scan.py` 18 satır thin wrapper; [`tests/test_lumos_quantum_readiness_cli.py`](../../tests/test_lumos_quantum_readiness_cli.py) + [`tests/test_quantum_readiness_scan.py`](../../tests/test_quantum_readiness_scan.py) mevcut.

### 18. LUMOS_CONFIRMATION_ENABLED varsayılan kapalı — prod drift riski {#td-18-confirmation-opt-in}

- **Kategori:** Dead feature flags / env vars
- **Etkilenen dosyalar:** [`src/policy/confirmation_policy.py`](../../src/policy/confirmation_policy.py), panel/CLI mutation modülleri
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** düşük (test/dokümantasyon) — davranış değişikliği ayrı karar
- **Çözüm zorluğu:** orta (ürün kararı #461)
- **Çözülmezse oluşacak etki:** 3. confirmation kapısı çoğu ortamda no-op; panel/CLI/köprü arasında farklı varsayılan algısı oluşabilir.
- **Kanıt:** `confirmation_policy.py` L103 env okuma; [ADR-012 prep](ADR-012-enforcement-prep-assessment.md) L29, L43, L147; testler env açıkken kapsamlı ([`tests/test_confirmation_policy.py`](../../tests/test_confirmation_policy.py) 74 eşleşme).

### 19. task_dispatch.py ikinci runtime orchestrator {#td-19-task-dispatch-orchestrator}

- **Kategori:** Oversized files / Duplicate implementations (gate + dispatch)
- **Etkilenen dosyalar:** [`packages/kando_runtime/src/kando_runtime/task_dispatch.py`](../../packages/kando_runtime/src/kando_runtime/task_dispatch.py), [`packages/kando_runtime/src/kando_runtime/lumos_gate.py`](../../packages/kando_runtime/src/kando_runtime/lumos_gate.py)
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** orta (2–4 person-day)
- **Çözüm zorluğu:** orta
- **Çözülmezse oluşacak etki:** Dispatch onay ve gate onay yolları ayrı pending şemaları kullanır; bridge adapter her iki kaynağa da yazılır.
- **Kanıt:** 1.873 satır; `attach_bridge_pending_confirmation` referansı `task_dispatch.py` + test; [`tests/test_task_dispatch.py`](../../tests/test_task_dispatch.py) 21 `lumos_gate` eşleşmesi — birleşik approve/consume testi yok.

### 20. Mega panel test dosyası bakım yükü {#td-20-mega-panel-test}

- **Kategori:** High dependency density (test tarafı) / Untested critical paths (dolaylı)
- **Etkilenen dosyalar:** [`tests/test_panel_i18n_v1.py`](../../tests/test_panel_i18n_v1.py) (1.782 satır), diğer panel gate testleri dağınık
- **Risk seviyesi:** orta
- **Tahmini bakım maliyeti:** orta (2–3 person-day parçalama)
- **Çözüm zorluğu:** düşük–orta
- **Çözülmezse oluşacak etki:** Panel i18n + UI sözleşmesi tek dev testte; enforcement testleri (`test_panel_*_policy_gate.py` vb.) ayrı dosyalarda — coverage haritası okuması zorlaşır.
- **Kanıt:** `test_panel_i18n_v1.py` 1.782 satır (test klasöründe 2. en büyük dosya); bridge approve E2E yalnızca adapter seviyesinde ([`test_bridge_confirmation_adapter.py`](../../tests/test_bridge_confirmation_adapter.py) 120 satır civarı).

---

## İlk 10 — Etki / Maliyet Oranı {#ilk-10--etki--maliyet-oranı}

Yüksek etki + düşük/orta maliyet önce sıralanmıştır. Etki skoru enforcement güvenliği ve geliştirme sürtünmesine göre; maliyet person-day T-shirt tahminidir.

| Sıra | Madde | Etki gerekçesi | Maliyet gerekçesi |
|------|-------|----------------|-------------------|
| 1 | **[#12](#td-12-duplicate-runtime-state) Duplicate runtime_state** | Package/src drift event kaybına yol açabilir | ~1–2 gün, dar diff, düşük davranış riski |
| 2 | **[#17](#td-17-quantum-dual-cli) Quantum readiness çift yüzey** | Düşük güvenlik etkisi; doc/entry karışıklığı | Thin wrapper; birleştirme veya deprecate kolay |
| 3 | **[#13](#td-13-archive-parallel-code) archive/ paralel kod** | Yanlış referans ve grep gürültüsü | Temizlik planı; runtime'a dokunmadan |
| 4 | **[#10](#td-10-sensitivity-gate-gap) change_sensitivity ↔ gate kopuk** | CRITICAL patch vs gate tutarsızlığı | Orta; karar matrisi ADR-012'de mevcut |
| 5 | **[#9](#td-09-p2-never-auto-narrow) P2 SECURITY_NEVER_AUTO dar kapsam** | Engine bypass yüksek güvenlik etkisi | Orta; mevcut helper genişletilebilir |
| 6 | **[#3](#td-03-panel-lockstate-env) Panel LockState env vekili** | Yanlış mutasyon izni algısı | Orta; process model kararı gerekir |
| 7 | **[#8](#td-08-parallel-pending-stores) Paralel pending mağazaları** | Duplicate grant state | Orta; [Madde 2](#td-02-bridge-cu4-gap) ile birlikte ele alınır |
| 8 | **[#18](#td-18-confirmation-opt-in) Confirmation opt-in drift** | 3. kapı çoğu ortamda kapalı | Düşük teknik maliyet; ürün kararı ayrı |
| 9 | **[#16](#td-16-cli-parse-monolith) cli_parse monolith** | CLI genişleme sürtünmesi | Orta parser ayrıştırma |
| 10 | **[#14](#td-14-triple-panel-entry) Üç katmanlı panel girişi** | Uçtan uca test/dokümantasyon yükü | Orta; mimari karar gerekir |

**Not:** Madde **[#1](#td-01-panel-astro) panel.astro** ve **[#2](#td-02-bridge-cu4-gap) köprü CU4 gap** en yüksek mutlak etkiye sahip; maliyetleri yüksek olduğu için etki/maliyet tablosunda ilk 10'a girmezler — stratejik yatırım kalemi olarak ayrı planlanmalıdır.

---

## Metodoloji Notları

- Satır sayıları: `wc -l` (2026-06-21), venv/node_modules hariç proje kaynakları.
- Env taraması: `LUMOS_*` grep; kullanılmayan env için kesin "dead" iddiasi yalnızca dokümante edilip kodda 0 okuma varsa işaretlendi.
- [ADR-012 enforcement prep assessment](ADR-012-enforcement-prep-assessment.md) mevcut keşif ile uyumlu; bu rapor borç perspektifine odaklanır.
- Hipotez: `panel.astro` iç sorumluluk sınırları statik analizle çıkarıldı; runtime modül grafiği dinamik profilleme yapılmadı.

---

## İlgili belgeler

- [ADR-012 enforcement prep assessment](ADR-012-enforcement-prep-assessment.md)
- [Runtime enforcement map](lumos-runtime-enforcement-map.md)
- [ADR zinciri özeti (006–012)](ADR-006-010-011-chain-summary.md)
- [Uygulanabilirlik haritası — PR dilimleri](technical-debt-execution-map.md)
- [Bağımlılık grafiği — Wave 1–3 topolojisi](technical-debt-dependency-graph.md)
- [Release blockers — RB-XX](release-blockers.md)
- [Proje haritası — runtime girişleri](../memory/project-map-runtime-entrypoints.md)
- [Karar günlüğü — DL-T01](../decision-log.md) (envanter yayını)
