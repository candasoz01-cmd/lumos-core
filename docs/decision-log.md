# Karar günlüğü — kalıcı repo kaydı

**Durum:** Takip belgesi (kod değildir).  
**Amaç:** Sohbet/bellek veya CI kapsamı dışına çıkan maddelerin **kaybolmaması**; karar, erteleme ve iptal geçmişinin repo içinde tutulması.

---

## Nasıl kullanılır

1. Yeni karar veya erteleme → bu dosyaya satır ekle.
2. Detaylı canonical kayıt gerekiyorsa → `docs/memory/*.md` veya ADR.
3. Her satırda **statü** zorunlu: `aktif`, `geçici ertelendi`, `silindi/iptal`, `public'ten çıkarıldı`, `duplicate kapatıldı`, `ileride değerlendirilecek`.
4. Secret, PII, production credential **yazılmaz**.

---

## Statü başlıkları (CI / kapsam dışı takibi)

### Karar onaylı, uygulama bekliyor

İlke kararı onaylandı; somut uygulama/teknik paket bekliyor. Eski «geçici ertelendi» kayıtları bu statüye taşındı (envanter ab791c14 §13).

| ID | Tarih | Konu | Özet | Bağlantı |
|----|-------|------|------|----------|
| DL-E01 | 2026-06-17 | Ödeme / PSP | Ödeme modeli + PSP/hukuk-mali paket gelene kadar aktif kapsam dışı; şirket/vergi kaydı mevcut | OD-011, [`payment-scope-decision.md`](memory/payment-scope-decision.md) |
| DL-E02 | 2026-06-17 | Mail entegrasyonu | İletişim kanalları ilke onaylı; mail ilk kanal — provider/connector bekliyor; **dar v1 scope:** tek provider, read+notify | OD-031, [`mail-integration-approval-decision.md`](memory/mail-integration-approval-decision.md), [`od-031-mail-dar-v1-scope.md`](memory/od-031-mail-dar-v1-scope.md) |
| DL-E03 | 2026-06-17 | Vault uygulama spec | Vault ilke onaylı (OD-001–005); somut ürün/API/amaç kodu private impl bekliyor; **dar v1 keşif/tasarım** docs-only | OD-001–005, [`vault-secret-token-decision.md`](memory/vault-secret-token-decision.md), [`od-vault-dar-v1-design.md`](memory/od-vault-dar-v1-design.md) |

### Geçici ertelendi

Bilinçli erteleme; yeniden açılma koşulu veya bağlı OD not edilir. *(DL-E01–E03 taşındı — yukarı «Karar onaylı, uygulama bekliyor».)*

| ID | Tarih | Konu | Özet | Bağlantı |
|----|-------|------|------|----------|
| — | — | — | *(boş — aktif geçici erteleme yok)* | — |

### Public'ten çıkarıldı — private/internal'a taşınacak

| ID | Tarih | Konu | Özet | Bağlantı |
|----|-------|------|------|----------|
| DL-I01 | 2026-06-17 | Üretim auth / cihaz presence | Public sınır dışı; private katmanda | ADR-007 |

### Silindi / iptal

| ID | Tarih | Konu | Özet | Gerekçe |
|----|-------|------|------|---------|
| DL-R01 | 2026-06-17 | `lumos_core.main:main` entry notu | Geçersiz entry ifadesi | Repo: `lumos_core.__main__:main` |

### Duplicate kapatıldı

| ID | Tarih | Konu | Özet | Tek kaynak |
|----|-------|------|------|------------|
| DL-D01 | 2026-06-17 | `panel/` = `ui/` | İki ayrı dizin | `docs/project-map.md` |
| DL-D02 | 2026-06-17 | Ürün kuralları çift kayıt | `docs/product-rules.md` özet; detay `docs/memory/product-rules.md` | Bu günlük + memory |

### Karar onaylandı — uygulama bekliyor

Karar verildi; kod/CI uygulaması henüz yapılmadı. OD **closed** sayılmaz.

*(Şu an boş — DL-A01 kapandı; bkz. «Karar kapandı — uygulama merge edildi».)*

### Karar kapandı — uygulama merge edildi

Karar uygulandı; kod `main`'de. DL-A01, DL-A02 … DL-A16 takip satırları kapandı.

| ID | Tarih | Konu | Karar | Merge | Bağlantı |
|----|-------|------|-------|-------|----------|
| DL-A01 | 2026-06-17 | OD-028 `lumos web` / `web/app.py` | **B1** — alt komutu kaldır; **restore değil** | PR #227 (`ff0ef4c`) — `__main__.py` web dalı kaldırıldı; `test_web_health.py` silindi; mimari belge senkronu | [`docs/memory/lumos-web-command-decision.md`](memory/lumos-web-command-decision.md) §12.2 |
| DL-A02 | 2026-06-19 | EC2-02 Client Evidence Queue | **Seçenek 1** — pending-op kuyruğu `panel.astro`; flush mevcut REST; journal şeması ve sunucu endpoint v1'de değişmez | PR #258 (`bc6e4e0`) — `panel.astro` + `test_panel_evidence_queue_ec2_02.py` | [`docs/memory/evidence-continuity-ec2-02-decision.md`](memory/evidence-continuity-ec2-02-decision.md) § Uygulama |
| DL-A03 | 2026-06-19 | EC2-12 Disconnect/resume test harness | **Seçenek 1** — test-only pytest integration harness (DR1–DR7); runtime, şema ve sunucu yüzeyi v1'de değişmez; Playwright E2E v1 reddedildi | PR #261 (`aa2a6ff`) — `test_panel_evidence_disconnect_resume_ec2_12.py` | [`docs/memory/evidence-continuity-ec2-12-decision.md`](memory/evidence-continuity-ec2-12-decision.md) § Uygulama |
| DL-A04 | 2026-06-19 | EC2-03 Köprü POST /task journal mirror | **Seçenek 1** — outbox overwrite değişmez; outbox persist sonrası append-only tek `after` satırı; enum `kando_bridge` / `bridge_outbox` / `bridge.task.post`; `payload_summary` yalnızca `title_preview` + `route`; `result` fazı EC2-13 dışı | PR #265 (`b1c48aa`) — `evidence_continuity.py` + `kando_bridge/server.py` H3 + `test_bridge_post_task_evidence_ec2_03.py` | [`docs/memory/evidence-continuity-ec2-03-decision.md`](memory/evidence-continuity-ec2-03-decision.md) § Uygulama |
| DL-A05 | 2026-06-19 | EC2-04 Guard/policy journal mirror | **Seçenek A** — iki source (`guard_audit` / `action_policy`); H4a/H4b choke-point; deny-only guard; parallel logging+log.txt korunur; `payload_summary` action/reason_code/route/title_preview(basename); `result` fazı EC2-13 dışı; git audit hook değil (OD-059) | PR #268 (`9475a0f`) — `evidence_continuity.py` + `guard_audit.py` H4a + `action_policy.py` H4b + `test_guard_policy_evidence_ec2_04.py` T1–T10 | [`docs/memory/evidence-continuity-ec2-04-decision.md`](memory/evidence-continuity-ec2-04-decision.md) § Uygulama |
| DL-A06 | 2026-06-19 | EC2-13 Köprü async agent `result` fazı | **Seçenek 1** — H5 `agent_runner` worker hook; `phase: result`; aynı enum; `payload_summary` + `job_id`; guard/policy result v1 dışı | PR #271 (`41a48fb`) — `evidence_continuity.py` H5 + `agent_runner.py` + `test_bridge_agent_result_evidence_ec2_13.py` R1–R10 | [`docs/memory/evidence-continuity-ec2-13-decision.md`](memory/evidence-continuity-ec2-13-decision.md) § Uygulama |
| DL-A07 | 2026-06-20 | EC2-08 Correlation UI | **Seçenek 1** — read-only `GET /evidence/recent` + `panel.astro` «Son işlem kanıtı» / «Buradan devam»; journal yazım hook'ları ve şema v1'de değişmez; köprü zinciri `job_id` + heuristic | PR #274 (`fb2af14`) — `evidence_continuity.py` read + `panel_tasks_server.py` route + `panel.astro` UI + U1–U12 pytest | [`docs/memory/evidence-continuity-ec2-08-decision.md`](memory/evidence-continuity-ec2-08-decision.md) § Uygulama |
| DL-A08 | 2026-06-20 | EC2-05 Store merge / ADR-008 drift | **Seçenek 1 (minimum v1)** — tam store merge reddedildi; `TASK_STORE_REGISTRY` + dual-store read-only health; chat localStorage dışı | PR #277 (`6521222`) — `evidence_continuity.py` + `panel_bridge_state.py` + `test_evidence_store_registry_ec2_05.py` R1–R8 | [`docs/memory/evidence-continuity-ec2-05-decision.md`](memory/evidence-continuity-ec2-05-decision.md) § Uygulama |
| DL-A09 | 2026-06-20 | EC2-09 Evidence retention policy | **Seçenek 1 (minimum v1)** — named constants 1 MB × 3; retention + storage API metadata; config/multi-file read v1 dışı | PR #280 (`121216d`) — `evidence_continuity.py` + `panel_tasks_server.py` + `test_evidence_retention_ec2_09.py` T1–T8 | [`docs/memory/evidence-continuity-ec2-09-decision.md`](memory/evidence-continuity-ec2-09-decision.md) § Uygulama |
| DL-A10 | 2026-06-20 | EC2-06 Legacy panel evidence hizalama | **Seçenek 1 (minimum v1)** — read-only evidence strip + shared JS module; EC2-02 queue Astro-only | PR #283 (`5ff9660`) — `evidence-correlation-strip.js` + legacy Görevler şeridi + L1–L6 pytest | [`docs/memory/evidence-continuity-ec2-06-decision.md`](memory/evidence-continuity-ec2-06-decision.md) § Uygulama |
| DL-A11 | 2026-06-20 | EC2-07 events[] projection metadata | **Seçenek 1 (minimum v1)** — soft deprecation metadata; disk yazım korunur | PR #286 (`424cf19`) — `tasks_json_events_projection_meta()` + GET enrich + E1–E6 pytest | [`docs/memory/evidence-continuity-ec2-07-decision.md`](memory/evidence-continuity-ec2-07-decision.md) § Uygulama |
| DL-A12 | 2026-06-20 | EC2-10 ObservationEngine disk spill | **Seçenek 1 (minimum v1)** — JSONL spill; TaskEngine auto-wire; evidence journal dışı | PR #289 (`1a0f411`) — `ObservationLifecycleSpill` + O1–O6 pytest | [`docs/memory/evidence-continuity-ec2-10-decision.md`](memory/evidence-continuity-ec2-10-decision.md) § Uygulama |
| DL-A13 | 2026-06-20 | EC2-11 Structured evidence query | **Seçenek 1 (minimum v1)** — filtered tail query; tam reconstruct v1 dışı | PR #291 (`980a50f`) — `query_evidence_events()` + GET `/evidence/query` + Q1–Q6 pytest | [`docs/memory/evidence-continuity-ec2-11-decision.md`](memory/evidence-continuity-ec2-11-decision.md) § Uygulama |
| DL-A14 | 2026-06-19 | EC2-01 Chat görev persist + `id` | **Minimum v1** — chat create `POST /tasks` + H1 journal; sunucu `tsk_*` id; silme UX → DL-A16 | PR #256 (`5073780`) — `panel.astro` + `test_panel_gorev_create_ec2_01.py` | [`docs/memory/evidence-continuity-v2-backlog.md`](memory/evidence-continuity-v2-backlog.md) § Phase 2 |
| DL-A15 | 2026-06-19 | EC2-14 Şema validator CI kapısı | **Minimum v1** — `validate_evidence_record` pytest CI kapısı; ayrı decision memo yok | PR #255 (`5b2ae6b`) — `test_evidence_continuity.py` journal şema doğrulama | [`docs/memory/evidence-continuity-v2-backlog.md`](memory/evidence-continuity-v2-backlog.md) § Phase 1 |
| DL-A17 | 2026-06-20 | OD-027 Slice 3a — web kalıntısı + ölü `lumos_runtime` aynası | **Slice 3a implementation-complete** — `kando_core.__main__` web parser/`_run_web()` kaldırıldı; `kando_runtime/lumos_runtime.py` silindi; canonical `src/core/lumos_runtime.py` korundu | PR #313 (`c0b8ea0`) | [`docs/memory/kando-packages-faz3-keşif-raporu.md`](memory/kando-packages-faz3-keşif-raporu.md) §3–6 |
| DL-A18 | 2026-06-20 | OD-027 Slice 3b — ayna paket arşivi | **Slice 3b implementation-complete** — dört ölü ayna paket (`kando_core`, `kando_memory`, `kando_policy`, `kando_context`) `archive/packages/` altına taşındı; bridge/runtime/CI PYTHONPATH dokunulmadı | PR #316 (`1cdb0f2`) | [`docs/memory/od-027-slice-3b-archive-decision.md`](memory/od-027-slice-3b-archive-decision.md) §3–7 |
| DL-A19 | 2026-06-20 | OD-027 Faz 4 cutover | **Faz 4 implementation-complete** — §8 kesme kapıları doğrulandı; OD-027 **closed**; `archive/packages/README.md`; indeks senkronu | PR #317 (`9f8c6b4`) | [`docs/memory/od-027-faz4-cutover-decision.md`](memory/od-027-faz4-cutover-decision.md) §4 |
| DL-A20 | 2026-06-20 | Panel statik emekliliği (Seçenek C) | Statik panel → `archive/panel/`; `panel/scripts/` korundu; kök `e2e:legacy:*` → `archive/panel` | PR #320 | [`docs/memory/od-panel-retirement-option-c-decision.md`](memory/od-panel-retirement-option-c-decision.md) §3 |
| DL-A21 | 2026-06-20 | Prod smoke (A3) | Read-only `smoke-prod.mjs` + `workflow_dispatch` prod-smoke.yml; push gate değil | PR #323 | [`docs/memory/od-prod-smoke-decision.md`](memory/od-prod-smoke-decision.md) §3 |

### İleride değerlendirilecek

| ID | Tarih | Konu | Özet | Bağlantı |
|----|-------|------|------|----------|
| DL-F01 | 2026-06-17 | Cursor Automations | Proaktif hatırlatma; düşük riskli read/report pilot | `docs/tool-watchlist.md` |
| DL-F02 | 2026-06-17 | `frontend/` yaşam döngüsü | **Seçenek B uygulandı** (OD-044 **closed**) — izole köprü E2E + prototip; üretim/deploy değil | OD-044 — [`frontend-role-decision.md`](memory/frontend-role-decision.md) |
| DL-F03 | 2026-06-17 | Platform veri kasası | İzinli, şeffaf, geri alınabilir taşıma | `docs/security-architecture.md` SEC-023 |
| DL-F04 | 2026-06-17 | OpenAI Agents / Realtime / Computer Use / Codex | Watchlist; rastgele eklenmez | `docs/tool-watchlist.md` |
| DL-F05 | 2026-06-18 | Çalışma araçları connector (GitHub, Slack, Drive, Linear, Notion, Asana) | İlke onaylı; değerlendirme listesi + katman sırası; uygulama bekliyor | OD-033 — [`work-tools-connectors-decision.md`](memory/work-tools-connectors-decision.md) |
| DL-F07 | 2026-06-17 | Root build vs panel E2E hizası | **Seçenek A uygulandı** (OD-046 **closed**) — üretim `ui/`; smoke (#294–#296); Faz 0–4 (#300–#305): kök `e2e:package*` → `ui/dist`, CI `ui-e2e`, legacy `e2e:legacy:*` | OD-046 — [`build-e2e-surface-alignment-decision.md`](memory/build-e2e-surface-alignment-decision.md), [`od-046-e2e-migration-plan.md`](memory/od-046-e2e-migration-plan.md) |
| DL-F08 | 2026-06-19 | Evidence Continuity v2 backlog | 14/14 madde minimum v1 uygulandı (PR #255–#291); takip belgesi `implementation-complete` | [`docs/memory/evidence-continuity-v2-backlog.md`](memory/evidence-continuity-v2-backlog.md); OD-058 v1 closed |

### Karar kapandı — docs/memory (uygulama kodu yok)

| ID | Tarih | Konu | Karar | Bağlantı |
|----|-------|------|-------|----------|
| DL-C01 | 2026-06-19 | OD-059 audit hook terminolojisi | Informal «audit hook» ayrı git hook **gerektirmez**; üç katman (commit guard / EC runtime v1 / EC v2 #4+#14); informal takip maddesi docs seviyesinde **CLOSED** | [`docs/memory/audit-hook-term-decision.md`](memory/audit-hook-term-decision.md); OD-058 çapraz |
| DL-C02 | 2026-06-20 | OD-043 Birincil kullanıcı yüzeyi | **Closed** — birincil üretim/dış kullanıcı yüzeyi **`ui/` Astro**; `panel/` legacy E2E; `frontend/` birincil değil; formal kapanış OD-046 (#300–#307) sonrası | [`docs/memory/primary-user-surface-decision.md`](memory/primary-user-surface-decision.md); [`build-e2e-surface-alignment-decision.md`](memory/build-e2e-surface-alignment-decision.md) |
| DL-C03 | 2026-06-20 | OD-046 E2E migrasyonu kapanışı | Kök E2E **`ui/dist`** hizası **implementation-complete**; PR #300–#305; indeks closed | [`docs/memory/od-046-e2e-migration-plan.md`](memory/od-046-e2e-migration-plan.md); [`build-e2e-surface-alignment-decision.md`](memory/build-e2e-surface-alignment-decision.md) |
| DL-C04 | 2026-06-20 | OD-044 frontend/ rolü | **Closed** — Seçenek **B**: izole köprü E2E + prototip referans; üretim/deploy/root build/root E2E değil; kod/taşıma/arşiv/silme yok | [`docs/memory/frontend-role-decision.md`](memory/frontend-role-decision.md) |
| DL-C05 | 2026-06-20 | OD-027 kando_* Faz 3 keşif | **Slice 3a** uygulama **DL-A17** (#313); **Slice 3b** uygulama **DL-A18** (#316) | [`docs/memory/kando-packages-faz3-keşif-raporu.md`](memory/kando-packages-faz3-keşif-raporu.md) |
| DL-C06 | 2026-06-20 | OD-059 Paket B CI ruff parity | Pre-commit ile CI hizalandı — `ruff check .` in `.github/workflows/ci.yml` | [`docs/memory/audit-hook-term-decision.md`](memory/audit-hook-term-decision.md) |
| DL-C07 | 2026-06-20 | OD-027 Slice 3b ayna paket arşivi | **`approved-for-implementation`** — dört ölü ayna paket (`kando_core`, `kando_memory`, `kando_policy`, `kando_context`) → `archive/packages/`; dış import sıfır; rollback `git mv` geri; bridge/runtime/CI PYTHONPATH dokunulmaz | [`docs/memory/od-027-slice-3b-archive-decision.md`](memory/od-027-slice-3b-archive-decision.md) |
| DL-C08 | 2026-06-20 | OD-027 Faz 4 cutover | **Cutover onaylandı** — §8 kapıları geçti; Slice 3a–3b tamam; OD-027 **closed**; canlı yol `src/` + bridge + runtime | [`docs/memory/od-027-faz4-cutover-decision.md`](memory/od-027-faz4-cutover-decision.md) |
| DL-C09 | 2026-06-20 | Panel statik emekliliği (Seçenek C) | **`decision-approved`** — **(a)** docs onaylı (docs-only v2); fiziksel **DL-A20** (#320); prod smoke **DL-C10** | [`docs/memory/od-panel-retirement-option-c-decision.md`](memory/od-panel-retirement-option-c-decision.md) |
| DL-C10 | 2026-06-20 | Prod smoke (A3) | Read-only HTTPS smoke; `workflow_dispatch` only | [`docs/memory/od-prod-smoke-decision.md`](memory/od-prod-smoke-decision.md) |
| DL-C11 | 2026-06-20 | OD-010 CI doc-only sınıflandırma | **Closed** — kod yolunda CI zorunlu | [`docs/memory/od-010-ci-classification-decision.md`](memory/od-010-ci-classification-decision.md) |
| DL-C12 | 2026-06-20 | OD-029 Ghidra public kapsamı | **Public entegrasyon reddedildi** — watchlist; operatör yerel/private RE | [`docs/memory/od-029-ghidra-scope-decision.md`](memory/od-029-ghidra-scope-decision.md) |
| DL-C13 | 2026-06-20 | OD-025 Vault migration senkronu | **Closed** (ilke düzeyi) — ChatGPT vault/token maddeleri `vault-secret-token-decision.md`'e taşındı; uygulama OD-001–005 | [`docs/memory/od-025-vault-migration-decision.md`](memory/od-025-vault-migration-decision.md) |
| DL-C14 | 2026-06-20 | OD-027 Faz 5 doc sync kapanışı | **Doc-only complete** — path/indeks senkronu (#317–331); bridge/runtime birleştirme **ertelendi** (ayrı oturum, onaylı impl) | [`docs/memory/kando-packages-transition-decision.md`](memory/kando-packages-transition-decision.md) Faz 5 |
| DL-C15 | 2026-06-20 | Vault/mail dar v1 design scope | **Doc-only complete** — vault dar v1 keşif/tasarım (UX outline, amaç kodu iskeleti, teknoloji çerçevesi); mail dar v1 hedef (tek provider, read+notify); **OD-B05 ertelendi** (kullanıcı 2026-06-20); impl ayrı onay | [`od-vault-dar-v1-design.md`](memory/od-vault-dar-v1-design.md), [`od-031-mail-dar-v1-scope.md`](memory/od-031-mail-dar-v1-scope.md) |
---

## 2026-06-17 — Dokümantasyon düzeni kurulumu

**Karar:** Repo içi kalıcı dokümantasyon/takip dosyaları oluşturuldu; kod değiştirilmedi.

| Dosya | Amaç | Statü |
|-------|------|--------|
| `docs/product-rules.md` | Ürün kuralları özeti | **aktif** |
| `docs/security-architecture.md` | Güvenlik kuralları özeti | **aktif** |
| `docs/workflow-rules.md` | İş akışı ve Cursor kuralları | **aktif** (güncellendi) |
| `docs/tool-watchlist.md` | Araç takip listesi | **aktif** |
| `docs/project-map.md` | Proje kökü ve dizin haritası | **aktif** |
| `docs/decision-log.md` | Bu günlük | **aktif** |

**İş akışı maddeleri (özet):**

| Madde | Statü |
|-------|--------|
| CI için çıkarılan kod/test/doküman kaybolmaz; statü yazılır | **aktif kural** |
| Uzun görev metinleri ayrı kopyalanabilir blokta; terminal blokları yalnızca komut için | **aktif kural** |
| Açıklamalar kod bloğunda değil; yalnızca çalıştırılabilir komutlar terminal kod bloğunda | **aktif kural** |

---

## Açık karar indeksi

Tam liste: `docs/memory/open-decisions-needs-review.md` (OD-001 … OD-060).

---

Son güncelleme: 2026-06-20 (DL-C15 — vault/mail dar v1 design scope)
