# Lumos Core — Release Blockers Analizi

| Alan | Değer |
|------|-------|
| **Belge türü** | Salt-okunur release engel analizi |
| **Tarih** | 2026-06-21 |
| **Kapsam** | 30 günlük paket/release penceresi (2026-06-21 → 2026-07-21) |
| **Durum** | Analiz only — kod/PR yok; yeni karar taahhüdü yok |
| **Referans** | [ADR-012 prep](ADR-012-enforcement-prep-assessment.md), [karar matrisi (tavsiyesiz)](ADR-012-enforcement-decision-matrix.md), [teknik borç envanteri](technical-debt-architecture-concentration-2026-06.md) (DL-T01), [uygulanabilirlik haritası](technical-debt-execution-map.md), [bağımlılık grafiği](technical-debt-dependency-graph.md) |
| **İlgili belgeler** | `docs/memory/open-decisions-needs-review.md`, ADR-001/012/013, `docs/analysis/lumos-quantum-readiness-checklist.md`, `README.md`, `ROADMAP.md`, `docs/memory/public-repo-boundary.md`, `pyproject.toml`, `.github/workflows/ci.yml` |

Bu belge **release engellerini** (RB-XX) listeler. Teknik borç uygulama sırası ve dalga topolojisi için bkz. [execution-map](technical-debt-execution-map.md) ve [dependency-graph](technical-debt-dependency-graph.md); 20 maddelik envanter için bkz. [mimari yoğunlaşma analizi](technical-debt-architecture-concentration-2026-06.md).

---

## 1. Özet

- ADR-012 Security Codex **kabul edildi** ancak **CLOSED değil** — Wave 1 Madde 1–2 (#491–#498) kapandı; kalan: Trust Faz 4, sensitivity↔gate, Panel LockState — ayrıntı [prep assessment §1](ADR-012-enforcement-prep-assessment.md#1-kısa-teknik-değerlendirme).
- ADR-012 enforcement Madde 3–6 **karar bekliyor** (insan onayı); Madde 1–2 **kapandı** (Seçenek B, Wave 1) — bkz. [RB-05](#rb-05--adr-012-enforcement-altı-karar-maddesi-karar-bekliyor).
- Packaging/docs: `pip install` sonrası tam CLI/gate/bridge yolu garanti değil (RB-06); ~~README release checklist kırık referans (RB-07)~~ RB-07 checklist mevcut; publish CI yok (RB-08); README kararlı OSS iddiası yok (RB-09).
- Vault (OD-001–005) ve mail/vault stub'ları **decision-approved / implementation-pending**; public boundary demo-safe stub (RB-10, RB-16).
- Quantum Readiness Faz-2 **docs-kapalı (kısmi)** — release blocker **değil** (§5).
- td-01..td-11 ile doğrudan örtüşen maddeler §6 çapraz tabloda RB-ID ile eşlenir.

---

## 2. Hard blockers (release için çözülmesi gerekir)

### RB-01 — ADR-012 Security Codex CLOSED değil

| Alan | Değer |
|------|-------|
| **Kategori** | güvenlik / docs |
| **Blokaj seviyesi** | hard blocker |
| **Açıklama** | Codex C1–C6 sözleşmesi merge edildi; Wave 1 Madde 1–2 (#491–#498) kapandı. Checkpoint tablosunda Trust Faz 4, sensitivity↔gate ve panel LockState **açık**. «Açık kalan maddeler (codex kapanış öncesi)» bölümü açıkça «Security Codex **CLOSED değildir**» der. |
| **Kanıt** | `docs/decisions/ADR-012-lumos-security-codex.md` checkpoint tablosu; Wave 1 #491–#498 merge |
| **30 gün içinde kapanış koşulu** | ADR-012 checkpoint tablosunda kalan maddeler (Trust Faz 4, sensitivity↔gate, LockState) «kapandı» veya bilinçli defer kaydı ile CLOSED durum geçişi tamamlanır. |
| **Alpha defer** | **Kayıtlı** — [`adr-012-internal-alpha-defer-record.md`](../memory/adr-012-internal-alpha-defer-record.md) (G-18); Internal Alpha CLOSED beklemez; Launch defer ayrı |
| **Bağımlılıklar** | RB-02, RB-03, RB-04, RB-05, RB-11 |

### RB-02 — Köprü CU4 `consume_confirmation` wiring eksik (PR-C6 kısmi)

| Alan | Değer |
|------|-------|
| **Kategori** | teknik / güvenlik |
| **Blokaj seviyesi** | ~~hard blocker~~ **kapandı (2026-06-21)** |
| **Açıklama** | ~~Shadow adapter grant yazar; köprü approve/resume legacy `approval_token` + `pending_approvals` ile devam eder.~~ Wave 1 Seçenek B: köprü approve/resume `consume_confirmation` + opt-in env (#494–#495); karakterizasyon #491–#493. |
| **Kanıt** | Wave 1 #491–#495; ADR-012 checkpoint «Kapandı»; open-decisions köprü wiring satırı **closed** |
| **30 gün içinde kapanış koşulu** | ~~ADR-012 Madde 1 (PR-C6 wiring) kararı verilir…~~ **Sağlandı** — Wave 1 Madde 1 merge. |
| **Bağımlılıklar** | RB-05 (Madde 1 kararı kapandı) |

### RB-03 — Panel LockState env vekili vs runtime kilit

| Alan | Değer |
|------|-------|
| **Kategori** | teknik / güvenlik |
| **Blokaj seviyesi** | hard blocker |
| **Açıklama** | Panel `koruma_active` / `session_unlocked` için `LUMOS_SESSION_UNLOCKED` env vekili kullanır; CLI `LockState.is_locked()` kullanır. Aynı oturumda farklı güvenlik algısı mümkün. |
| **Kanıt** | td-03; ADR-012 prep L14, L73–74, L143; [execution-map — td-03](technical-debt-execution-map.md#td-03-panel-lockstate-env) |
| **30 gün içinde kapanış koşulu** | ADR-012 Madde 6 (Panel LockState) kararı verilir; panel process modeli ile runtime kilit sinyali hizalanır veya codex maddesi resmi defer ile kapatılır. |
| **Bağımlılıklar** | RB-05, RB-11 |

### RB-04 — P2 `SECURITY_NEVER_AUTO` dar engine kapsamı

| Alan | Değer |
|------|-------|
| **Kategori** | güvenlik / teknik |
| **Blokaj seviyesi** | ~~hard blocker~~ **kapandı (2026-06-21)** |
| **Açıklama** | ~~Engine branch #463 dar…~~ Wave 1 Seçenek B: tam eşleme tablosu #497; engine + panel/CLI/store sync #498; karakterizasyon #496. |
| **Kanıt** | Wave 1 #496–#498; ADR-012 checkpoint «Kapandı»; open-decisions P2 satırı **closed** |
| **30 gün içinde kapanış koşulu** | ~~ADR-012 Madde 2 kararı + seçilen kapsamda merge kanıtı…~~ **Sağlandı** — Wave 1 Madde 2 merge. |
| **Bağımlılıklar** | RB-05 (Madde 2 kararı kapandı) |

### RB-05 — ADR-012 enforcement altı karar maddesi «karar bekliyor»

| Alan | Değer |
|------|-------|
| **Kategori** | operasyonel / docs |
| **Blokaj seviyesi** | hard blocker |
| **Açıklama** | ~~PR-C6 wiring, P2 genişletme,~~ Trust Faz 4 zamanlaması, sensitivity↔gate, confirmation varsayılanı (tam default-on kapıları), Panel LockState — matriste **karar bekliyor**; Madde 1–2 **kapandı** (Wave 1 Seçenek B). |
| **Kanıt** | `docs/analysis/ADR-012-enforcement-decision-matrix.md`; prep assessment §5; open-decisions Güvenlik/mimari bölümü |
| **30 gün içinde kapanış koşulu** | Kalan maddeler (3–6) için durum `closed`/`deferred`/`accepted-as-is` olarak ADR veya open-decisions'da kayıt altına alınır. |
| **Bağımlılıklar** | RB-01, RB-02, RB-03, RB-04, RB-11, RB-12 |

### RB-06 — Python paketleme: kando bağımlılıkları wheel dışında

| Alan | Değer |
|------|-------|
| **Kategori** | packaging |
| **Blokaj seviyesi** | hard blocker |
| **Açıklama** | `pyproject.toml` yalnızca `src/` → `lumos-core` 0.1.0. `kando-runtime` ve `kando-bridge` ayrı `packages/*/pyproject.toml`; CI `PYTHONPATH=src:kando_runtime:kando_bridge` zorunlu. `requirements.txt` yorumu bunu doğrular. |
| **Kanıt** | `pyproject.toml` L20–24; `requirements.txt` L1; `Makefile` L3, L40–41; `.github/workflows/ci.yml` L31–33 |
| **30 gün içinde kapanış koşulu** | Tek `pip install` ile gate/bridge import edilebilir hale gelir (monorepo wheel, workspace deps veya birleşik meta-package) ve CI'da PYTHONPATH olmadan aynı test seti geçer. |
| **Bağımlılıklar** | — |

### RB-07 — Release checklist dosyası eksik (README kırık referans)

| Alan | Değer |
|------|-------|
| **Kategori** | docs / packaging |
| **Blokaj seviyesi** | ~~hard blocker~~ **kapandı (2026-06-21)** |
| **Açıklama** | ~~README L60 `docs/GITHUB_RELEASE_CHECKLIST.md` linkler; repo'da dosya bulunamadı.~~ Canonical checklist oluşturuldu; README referansı geçerli. |
| **Kanıt** | [`GITHUB_RELEASE_CHECKLIST.md`](GITHUB_RELEASE_CHECKLIST.md); README L60 |
| **30 gün içinde kapanış koşulu** | ~~Checklist dosyası oluşturulur…~~ **Sağlandı** — docs PR. |
| **Bağımlılıklar** | RB-08 (publish CI hâlâ açık) |

### RB-08 — Publish/release CI pipeline yok

| Alan | Değer |
|------|-------|
| **Kategori** | operasyonel / packaging |
| **Blokaj seviyesi** | hard blocker |
| **Açıklama** | `.github/workflows/` altında yalnızca `ci.yml` (test/ruff/E2E) ve manuel `prod-smoke.yml`. PyPI, npm veya GitHub Release artifact workflow'u yok. |
| **Kanıt** | `.github/workflows/ci.yml`; `.github/workflows/prod-smoke.yml` (`workflow_dispatch` only) |
| **30 gün içinde kapanış koşulu** | Hedef dağıtım kanalı (PyPI tag, GitHub Release, npm) için otomatik build+publish veya resmi manuel release runbook'u tanımlanır. |
| **Bağımlılıklar** | RB-06, RB-07 |

### RB-09 — README: kararlı OSS ürün iddiası yok

| Alan | Değer |
|------|-------|
| **Kategori** | ürün / docs |
| **Blokaj seviyesi** | hard blocker |
| **Açıklama** | «Early active development»; «not yet a stable, fully contribution-ready open source product»; CONTRIBUTING «will be added later». Resmi/professional track «not published yet». |
| **Kanıt** | `README.md` L32–49, L68–72, L148 |
| **30 gün içinde kapanış koşulu** | Release track tanımı ile README durum metni hizalanır (dev build vs stable tag ayrımı net yazılır). |
| **Bağımlılıklar** | RB-18 |

### RB-10 — Vault kritik kararlar implementation-pending (OD-001–005)

| Alan | Değer |
|------|-------|
| **Kategori** | güvenlik / ürün |
| **Blokaj seviyesi** | hard blocker |
| **Açıklama** | Secret/token/vault segmentasyon/şifreleme kararları onaylı; V1a partial stub; tam PoC ve bridge **private** bekliyor. Public boundary: stub ≠ prod. |
| **Kanıt** | `docs/memory/open-decisions-needs-review.md` OD-001–005; `docs/memory/public-repo-boundary.md` §C |
| **30 gün içinde kapanış koşulu** | Release iddiası vault/secret yönetimi içermiyorsa README/ADR'da demo-stub sınırı açık kalır; içeriyorsa OD-001–005 implementation-complete veya bilinçli defer. |
| **Bağımlılıklar** | RB-16 |

---

## 3. Soft blockers (caveat ile release mümkün)

### RB-11 — Trust Faz 4 (ADR-007) kod yok

| Alan | Değer |
|------|-------|
| **Kategori** | güvenlik |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | Merkezi trust motoru yok; consent/keystore/session sinyalleri dağınık. |
| **Kanıt** | td-11; ADR-012 L198; prep L32, L145 |
| **30 gün içinde kapanış koşulu** | Trust Faz 4 uygulanır veya codex defer + release notunda «dağınık trust sinyalleri» caveat. |
| **Bağımlılıklar** | RB-05 |

### RB-12 — `change_sensitivity` ↔ `lumos_gate` kopuk

| Alan | Değer |
|------|-------|
| **Kategori** | teknik |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | CRITICAL path patch sınıflandırması ile gate risk skoru bağımsız. |
| **Kanıt** | td-10; prep L47, L98–105; ADR-012 matris Madde 4 |
| **30 gün içinde kapanış koşulu** | Madde 4 kararı + isteğe bağlı entegrasyon veya dokümante edilmiş çift risk modeli. |
| **Bağımlılıklar** | RB-05 |

### RB-13 — Confirmation 3. kapı varsayılan kapalı (opt-in)

| Alan | Değer |
|------|-------|
| **Kategori** | ürün / güvenlik |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | `LUMOS_CONFIRMATION_ENABLED` yok/false → confirmation no-op; bilinçli karar #461. |
| **Kanıt** | ADR-012 L132–134, L199; prep L147 |
| **30 gün içinde kapanış koşulu** | Release notunda opt-in zorunluluğu; veya default-on ürün kararı (DL-C18 defer). |
| **Bağımlılıklar** | — |

### RB-14 — CONTRIBUTING.md yok

| Alan | Değer |
|------|-------|
| **Kategori** | docs |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | Katkı süreci README'de «will be added later». |
| **Kanıt** | README L48 |
| **30 gün içinde kapanış koşulu** | Dosya eklenir veya «controlled review» süreci başka belgede tanımlanır. |

### RB-15 — Versiyon parçalanması

| Alan | Değer |
|------|-------|
| **Kategori** | packaging |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | `lumos-core` 0.1.0, `ui` 0.0.1, `kando-*` 0.1.0 — koordineli semver/release tag yok. |
| **Kanıt** | `pyproject.toml`; `ui/package.json`; `packages/*/pyproject.toml` |
| **30 gün içinde kapanış koşulu** | Release manifest / tag stratejisi tek kaynakta tanımlanır. |

### RB-16 — Mail/vault public stub vs prod iddiası

| Alan | Değer |
|------|-------|
| **Kategori** | ürün / güvenlik |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | Public boundary: integration stub ≠ production connector. |
| **Kanıt** | `public-repo-boundary.md` §C; OD-031 |
| **30 gün içinde kapanış koşulu** | Release metni demo-safe stub sınırını taşımaz. |

### RB-17 — ROADMAP: çoğu modül iskelet/placeholder

| Alan | Değer |
|------|-------|
| **Kategori** | ürün |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | ROADMAP «Yakında / Takipte»; README early active development. Panel nav: iskelet modüllerde «Henüz aktif değil» rozeti (#503). |
| **Kanıt** | `ROADMAP.md`; README L42; `ui/src/pages/panel.astro` `data-module-availability="inactive"` |
| **30 gün içinde kapanış koşulu** | Pilot giriş: menü rozet/gizleme ✓ (2026-06-21); release «dev foundation build» etiketi hizası devam |

### RB-18 — ADR-001 / ADR-013 hâlâ «Taslak»

| Alan | Değer |
|------|-------|
| **Kategori** | docs |
| **Blokaj seviyesi** | soft blocker |
| **Açıklama** | Quantum alanı taslak ADR; Faz-2 kısmi uygulama var ama ADR durumu Taslak. |
| **Kanıt** | ADR-001 L5–6; ADR-013 L7 |
| **30 gün içinde kapanış koşulu** | ADR durum geçişi veya release notunda «taslak ADR, kısmi impl» ayrımı. |

---

## 4. Watch list (blokaj değil; hız riski)

| ID | Konu | Kanıt |
|----|------|-------|
| RB-19 | `lumos_gate.py` (~2800 satır) dedicated unit test yok; testler dağınık | td-04; execution-map §#4 |
| RB-20 | Entropy birim testi yok | quantum checklist L122 |
| RB-21 | Prod smoke yalnızca manuel `workflow_dispatch` | `prod-smoke.yml` |
| RB-22 | Gmail live smoke CI'da skip (env gate) | `tests/test_gmail_api_smoke.py`; project-journal |
| RB-23 | `panel.astro` ~15.5K satır monolit | td-01 |
| RB-24 | OD-B05 bridge/runtime → `src/` merge ertelendi | open-decisions L106 |
| RB-25 | `archive/` paralel kod (16M) | td-13 |
| RB-26 | Duplicate `runtime_state` src vs kando_runtime | td-12 |
| RB-27 | Marka/vitrin OD-048–057 needs-review/queued | open-decisions |
| RB-28 | `PermissionManager` stub — lease enforcement yok | prep assessment L148 |

---

## 5. Explicitly NOT blockers (yanlış alarm önleme)

| Konu | Neden blocker değil |
|------|---------------------|
| **Quantum Readiness Faz-2** | open-decisions: **closed (kısmi — docs)** #468–#483; CLI, panel GET, live fields, badge uygulandı |
| **E2E confirmation #459+#460** | ADR-012 checkpoint: Tamamlandı (opt-in env) |
| **Varsayılan-on kararı** | Kapandı (docs): opt-in korunur #461 |
| **Evidence Continuity v1/v2** | OD-058 closed; v2 backlog 14/14 implementation-complete |
| **OD-027 kando packages geçişi** | Closed — Seçenek C; Faz 4 cutover tamam |
| **OD-043–046 yüzey hizası** | Closed — birincil `ui/`, E2E migration complete |
| **OD-010 CI tamamlanma** | Closed |
| **OD-029 Ghidra** | Closed — public entegrasyon yok |
| **Ödeme (OD-011)** | Bilinçli kapsam dışı; release için eksik sayılmaz |
| **PR-C6 köprü wiring (RB-02)** | Wave 1 #491–#495 merge; ADR-012 checkpoint Kapandı |
| **P2 tam eşleme (RB-04)** | Wave 1 #496–#498 merge; ADR-012 checkpoint Kapandı |
| **Faz-2 enforcement dalgası docs (#464)** | Closed (docs) — açık satırlar enforcement uygulaması, release tag değil |
| **Entropy sağlayıcı davranışı** | ADR-013: değiştirilmez — readiness tarayıcı ayrı |

---

## 6. Cross-reference tablosu

| RB ID | open-decisions | ADR-012 karar maddesi | td-XX |
|-------|----------------|----------------------|-------|
| RB-01 | — (codex genel) | Açık maddeler §204–214 | td-02,03,09,10,11 |
| RB-02 | CU4 wiring (**closed**) | Madde 1 PR-C6 ✓ | td-02, td-08 |
| RB-03 | Trust Faz 4 (needs-review) | Madde 6 LockState | td-03 |
| RB-04 | P2 tam eşleme (**closed**) | Madde 2 P2 ✓ | td-09 |
| RB-05 | 2× needs-review satırı (Madde 3–6) | Matris Madde 3–6 | — |
| RB-06 | OD-B05 (ertelendi) | — | td-15 |
| RB-07 | — | — | — |
| RB-08 | OD-010 (CI closed — test only) | — | — |
| RB-09 | OD-043 closed | — | td-14 |
| RB-10 | OD-001–005 | C3 onay+kanıt | — |
| RB-11 | Trust Faz 4 | Madde 3 | td-11 |
| RB-12 | sensitivity chain | Madde 4 | td-10 |
| RB-13 | — | Madde 5 (#461 closed) | td-18 |
| RB-16 | OD-031 | — | — |
| RB-19 | — | — | td-04 |
| RB-23 | — | — | td-01 |
