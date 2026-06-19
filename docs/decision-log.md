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

### Geçici ertelendi

Bilinçli erteleme; yeniden açılma koşulu veya bağlı OD not edilir.

| ID | Tarih | Konu | Özet | Bağlantı |
|----|-------|------|------|----------|
| DL-E01 | 2026-06-17 | Ödeme / PSP | Şirket yapısı netleşene kadar ödeme sistemi dışarıda | OD-011, `docs/memory/payment-scope-decision.md` |
| DL-E02 | 2026-06-17 | Mail entegrasyonu | İzinli mail okuma/özet — kapsam sonra | OD-031 |
| DL-E03 | 2026-06-17 | Vault uygulama spec | Katman modeli ilke; API/amaç kodu bekliyor | OD-001–005 |

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

| ID | Tarih | Konu | Karar | Uygulama paketi | Bağlantı |
|----|-------|------|-------|-----------------|----------|
| DL-A01 | 2026-06-17 | OD-028 `lumos web` / `web/app.py` | **B1** — alt komutu kaldır; **restore değil** | `__main__.py` web dalı + `_run_web()`; `pyproject.toml` açıklama; `test_web_health.py`; `ARCHITECTURE_MAP.md` senkronu; `kando_core` ayrı (OD-027) | `docs/memory/lumos-web-command-decision.md` §12.2 |

### Karar kapandı — uygulama merge edildi

Karar uygulandı; kod `main`'de. DL-A02, DL-A03, DL-A04, DL-A05, DL-A06, DL-A07 ve DL-A08 takip satırları kapandı.

| ID | Tarih | Konu | Karar | Merge | Bağlantı |
|----|-------|------|-------|-------|----------|
| DL-A02 | 2026-06-19 | EC2-02 Client Evidence Queue | **Seçenek 1** — pending-op kuyruğu `panel.astro`; flush mevcut REST; journal şeması ve sunucu endpoint v1'de değişmez | PR #258 (`bc6e4e0`) — `panel.astro` + `test_panel_evidence_queue_ec2_02.py` | [`docs/memory/evidence-continuity-ec2-02-decision.md`](memory/evidence-continuity-ec2-02-decision.md) § Uygulama |
| DL-A03 | 2026-06-19 | EC2-12 Disconnect/resume test harness | **Seçenek 1** — test-only pytest integration harness (DR1–DR7); runtime, şema ve sunucu yüzeyi v1'de değişmez; Playwright E2E v1 reddedildi | PR #261 (`aa2a6ff`) — `test_panel_evidence_disconnect_resume_ec2_12.py` | [`docs/memory/evidence-continuity-ec2-12-decision.md`](memory/evidence-continuity-ec2-12-decision.md) § Uygulama |
| DL-A04 | 2026-06-19 | EC2-03 Köprü POST /task journal mirror | **Seçenek 1** — outbox overwrite değişmez; outbox persist sonrası append-only tek `after` satırı; enum `kando_bridge` / `bridge_outbox` / `bridge.task.post`; `payload_summary` yalnızca `title_preview` + `route`; `result` fazı EC2-13 dışı | PR #265 (`b1c48aa`) — `evidence_continuity.py` + `kando_bridge/server.py` H3 + `test_bridge_post_task_evidence_ec2_03.py` | [`docs/memory/evidence-continuity-ec2-03-decision.md`](memory/evidence-continuity-ec2-03-decision.md) § Uygulama |
| DL-A05 | 2026-06-19 | EC2-04 Guard/policy journal mirror | **Seçenek A** — iki source (`guard_audit` / `action_policy`); H4a/H4b choke-point; deny-only guard; parallel logging+log.txt korunur; `payload_summary` action/reason_code/route/title_preview(basename); `result` fazı EC2-13 dışı; git audit hook değil (OD-059) | PR #268 (`9475a0f`) — `evidence_continuity.py` + `guard_audit.py` H4a + `action_policy.py` H4b + `test_guard_policy_evidence_ec2_04.py` T1–T10 | [`docs/memory/evidence-continuity-ec2-04-decision.md`](memory/evidence-continuity-ec2-04-decision.md) § Uygulama |
| DL-A06 | 2026-06-19 | EC2-13 Köprü async agent `result` fazı | **Seçenek 1** — H5 `agent_runner` worker hook; `phase: result`; aynı enum; `payload_summary` + `job_id`; guard/policy result v1 dışı | PR #271 (`41a48fb`) — `evidence_continuity.py` H5 + `agent_runner.py` + `test_bridge_agent_result_evidence_ec2_13.py` R1–R10 | [`docs/memory/evidence-continuity-ec2-13-decision.md`](memory/evidence-continuity-ec2-13-decision.md) § Uygulama |
| DL-A07 | 2026-06-20 | EC2-08 Correlation UI | **Seçenek 1** — read-only `GET /evidence/recent` + `panel.astro` «Son işlem kanıtı» / «Buradan devam»; journal yazım hook'ları ve şema v1'de değişmez; köprü zinciri `job_id` + heuristic | PR #274 (`fb2af14`) — `evidence_continuity.py` read + `panel_tasks_server.py` route + `panel.astro` UI + U1–U12 pytest | [`docs/memory/evidence-continuity-ec2-08-decision.md`](memory/evidence-continuity-ec2-08-decision.md) § Uygulama |
| DL-A08 | 2026-06-20 | EC2-05 Store merge / ADR-008 drift | **Seçenek 1 (minimum v1)** — tam store merge reddedildi; `TASK_STORE_REGISTRY` + dual-store read-only health; chat localStorage dışı | PR #277 (`6521222`) — `evidence_continuity.py` + `panel_bridge_state.py` + `test_evidence_store_registry_ec2_05.py` R1–R8 | [`docs/memory/evidence-continuity-ec2-05-decision.md`](memory/evidence-continuity-ec2-05-decision.md) § Uygulama |

### İleride değerlendirilecek

| ID | Tarih | Konu | Özet | Bağlantı |
|----|-------|------|------|----------|
| DL-F01 | 2026-06-17 | Cursor Automations | Proaktif hatırlatma; düşük riskli read/report pilot | `docs/tool-watchlist.md` |
| DL-F02 | 2026-06-17 | `frontend/` yaşam döngüsü | Arşiv / koru / ui'ye taşı / kaldır | OD-044 |
| DL-F03 | 2026-06-17 | Platform veri kasası | İzinli, şeffaf, geri alınabilir taşıma | `docs/security-architecture.md` SEC-023 |
| DL-F04 | 2026-06-17 | OpenAI Agents / Realtime / Computer Use / Codex | Watchlist; rastgele eklenmez | `docs/tool-watchlist.md` |
| DL-F05 | 2026-06-18 | Çalışma araçları connector (GitHub, Slack, Drive, Linear, Notion, Asana) | İlke onaylı; değerlendirme listesi + katman sırası; uygulama bekliyor | OD-033 — [`work-tools-connectors-decision.md`](memory/work-tools-connectors-decision.md) |
| DL-F06 | 2026-06-17 | Birincil kullanıcı yüzeyi | Taslak `ui/`; kesin karar bekliyor | OD-043 |
| DL-F07 | 2026-06-17 | Root build vs panel E2E hizası | Üretim `ui/`, E2E `panel/` — hizasız | OD-046 |
| DL-F08 | 2026-06-19 | Evidence Continuity v2 backlog | 14 madde; P0/P1/P2 + 5 faz planı; kod yok — planlama belgesi | [`docs/memory/evidence-continuity-v2-backlog.md`](memory/evidence-continuity-v2-backlog.md); OD-058 v1 closed |

### Karar kapandı — docs/memory (uygulama kodu yok)

| ID | Tarih | Konu | Karar | Bağlantı |
|----|-------|------|-------|----------|
| DL-C01 | 2026-06-19 | OD-059 audit hook terminolojisi | Informal «audit hook» ayrı git hook **gerektirmez**; üç katman (commit guard / EC runtime v1 / EC v2 #4+#14); informal takip maddesi docs seviyesinde **CLOSED** | [`docs/memory/audit-hook-term-decision.md`](memory/audit-hook-term-decision.md); OD-058 çapraz |

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

Son güncelleme: 2026-06-20 (DL-A08 closed — EC2-05 PR #277 merge)
