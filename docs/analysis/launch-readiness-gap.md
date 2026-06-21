# Lumos Core — Launch Readiness Gap Analizi

| Alan | Değer |
|------|-------|
| **Belge ID** | `launch-readiness-gap` |
| **Durum** | `analiz` — giriş kriterleri vs repo gerçekliği |
| **Tarih** | 2026-06-21 |
| **Birincil kaynak** | [`pre-commercial-release-plan.md`](./pre-commercial-release-plan.md) |
| **Kapsam** | Internal Alpha → Closed Pilot → Open Beta → Commercial Launch **giriş kriterleri** |
| **Dil** | Türkçe (birincil) |
| **Repo snapshot** | `main` @ `3db02ff` (#493); CI son run: success |
| **Feragat** | Kod/PR yok; hipotezler `[HİPOTEZ]` ile işaretlidir |

---

## Yönetici özeti

Lumos bugün **Aşama 0 (Pre-Alpha)** konumundadır. Internal Alpha **girişine kısmen yakın** (CI yeşil, erken geliştirme etiketi hizalı) ancak **yazılı release kapsamı**, **P0/P1 triage listesi** ve **ADR-012 Alpha defer tek kaydı** eksik. Commercial Launch için **10 giriş gap'i** doğrudan blokaj oluşturur (ödeme, banka B1–B5, publish CI, ADR-012 bilinçli kapanış).

| Metrik | Değer |
|--------|-------|
| Toplam giriş kriteri | 30 |
| Tamamlandı | 3 |
| Kısmen tamamlandı | 8 |
| Başlanmadı | 19 |
| **Toplam gap (kısmi + başlanmadı)** | **27** |
| Internal Alpha hazır mı? | **Kısmi — hayır (tam değil)** |
| Commercial Launch giriş gap | **10** |

---

## Aşama 1 — Internal Alpha (giriş kriterleri)

Kaynak: [`pre-commercial-release-plan.md` §89–99](./pre-commercial-release-plan.md#aşama-1--internal-alpha)

| # | Kriter | Durum | Kanıt | İlgili gap / RB / OD |
|---|--------|-------|-------|----------------------|
| A1 | Ekip release kapsamı yazılı tanımlandı (panel + yerel görevler ± köprü; entegrasyon/posta dışı) | **Kısmen tamamlandı** | [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) v1/Faz A kapsamı var; [`release-readiness-gap-analysis.md`](./release-readiness-gap-analysis.md) GAP-01: README vs v1-readiness çelişkisi; **Internal Alpha release scope** adlı tek yazılı ekip belgesi yok | G-24, GAP-01, RB-09 |
| A2 | CI yeşil (son merge'den itibaren en az bir tam `ci.yml` run) | **Tamamlandı** | `gh run list`: `main` push #493 → **success** (~48s, 2026-06-21); [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) test + ruff + ui-smoke | — |
| A3 | Bilinen P0/P1 hata listesi oluşturuldu ve sahipleri atandı | **Başlanmadı** | Repo taraması: merkezi P0/P1 triage dosyası/issue etiketi **bulunamadı**; yalnızca [`PANEL_READONLY_AUDIT.md`](../PANEL_READONLY_AUDIT.md) P1 notu | G-23 |
| A4 | README / panel metni «erken geliştirme / alpha» ile hizalı | **Tamamlandı** | [`README.md`](../../README.md) L32–49 «early active development»; [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) limited mode; panel i18n «Sınırlı mod» | RB-09 (Alpha'da kapanması beklenen etiketleme **karşılandı**) |
| A5 | ADR-012 durumu dokümante: Alpha CLOSED beklemez; açık maddeler defer/yol haritası | **Kısmen tamamlandı** | [`ADR-012`](../decisions/ADR-012-lumos-security-codex.md) §204–214 açık maddeler; [`pre-commercial-release-plan.md`](./pre-commercial-release-plan.md) §422–441 Alpha defer; [`adr-012-wave1-execution-plan.md`](./adr-012-wave1-execution-plan.md) plan — **Alpha defer imza/onay kaydı** ayrı belge değil | G-18, RB-01, RB-05 |

**Alpha giriş özeti:** 2 / 5 tamam → **Internal Alpha girişine geçilemez (tam)**.

---

## Aşama 2 — Closed Pilot (giriş kriterleri)

Kaynak: [`pre-commercial-release-plan.md` §147–155](./pre-commercial-release-plan.md#aşama-2--closed-pilot)

| # | Kriter | Durum | Kanıt | İlgili gap / RB / OD |
|---|--------|-------|-------|----------------------|
| P1 | Internal Alpha **çıkış kriterleri** tamamlandı | **Başlanmadı** | Alpha çıkış (≥2 hafta yolculuk, P0=0, RB-07 vb.) **doğrulanmadı** | G-01, G-02 |
| P2 | Pilot kullanıcı sözleşmesi / erken erişim metni | **Başlanmadı** | [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) §4 hukuki sayfalar eksik; pilot sözleşmesi repoda yok | G-04 |
| P3 | Davet listesi ≤20; Pro persona segment | **Başlanmadı** | [`commercial-product-packaging.md`](./commercial-product-packaging.md) §2 persona tanımı var; **davet listesi operasyonel kayıt yok** | G-04 |
| P4 | Panelde Sınırlı mod + «ne çalışır / ne çalışmaz» onboarding | **Kısmen tamamlandı** | [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) §2–3; panel i18n `limitedSub`; PR #136–#139 merged | E2, E3, [`first-customer-reality-check.md`](./first-customer-reality-check.md) |
| P5 | Destek kanalı yazılı + best-effort SLA bildirimi | **Başlanmadı** | Packaging §7.1 `support@<TBD>`; müşteri yüzünde destek kanalı yok (E9) | G-05 |
| P6 | Modül menüsünde planlanmamış özellikler «henüz aktif değil» veya gizli | **Kısmen tamamlandı** | Capabilities legend (`GELİŞTİRME AŞAMASINDA`) [`ui/src/i18n/messages/panel/tr.ts`](../../ui/src/i18n/messages/panel/tr.ts); **menü genelinde RB-17 rozet/gizleme yok** — ROADMAP çoğu modül iskelet | RB-17, E3, E4, G-03 |
| P7 | Köprü: barındırılmış köprü **veya** self-host kurulum rehberi | **Kısmen tamamlandı** | [`scripts/README_kando_bridge_server.md`](../../scripts/README_kando_bridge_server.md), README Deploy; prod `welockai.com` Sınırlı mod (köprü yok); pilot kohort barındırma **operasyonel değil** | G-06, RB-02, E1 |

---

## Aşama 3 — Open Beta (giriş kriterleri)

Kaynak: [`pre-commercial-release-plan.md` §206–218](./pre-commercial-release-plan.md#aşama-3--open-beta)

| # | Kriter | Durum | Kanıt | İlgili gap / RB / OD |
|---|--------|-------|-------|----------------------|
| B1 | Closed Pilot **çıkış kriterleri** tamamlandı | **Başlanmadı** | Pilot metrikleri (≥5 kullanıcı 14 gün vb.) **kanıt yok** | G-02 |
| B2 | Beta katılım politikası (waitlist/açık kayıt, kapasite üst sınırı) | **Başlanmadı** | Repoda beta kayıt/waitlist politikası **yok** | G-10 |
| B3 | Yayınlanmış minimum hukuki yüzey (gizlilik, kullanım, iptal/iade çerçevesi) | **Başlanmadı** | [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) §4 — gizlilik, kullanım, çerez **Eksik** | G-07, Bank B3 |
| B4 | İletişim sayfası: şirket adı, e-posta, [KKTC] fiziksel/kayıtlı adres | **Başlanmadı** | Bank checklist §3 iletişim **Eksik**; Packaging §7.1 e-posta TBD | G-09, Bank B5 |
| B5 | Landing / vitrin (OD-048) beta iddia seviyesi; fiyat TBD açık | **Başlanmadı** | OD-048 `needs-review`; [`od-048-landing-vitrin-decision.md`](../memory/od-048-landing-vitrin-decision.md) taslak; müşteri yüzü landing **yok** | G-08, OD-048, Bank B5 |
| B6 | Destek süreci: ticket/e-posta, iç runbook, escalation | **Başlanmadı** | Ticket akışı / runbook repoda **yok** | G-11 |
| B7 | Onboarding: Sınırlı mod, Starter vs beta, modül durumu | **Kısmen tamamlandı** | Limited mode prod var; **Starter vs beta tek sayfa OSS/Pro farkı** müşteri yüzünde yok (E6) | E6, G-03 |
| B8 | Trial süresi tanımı; checkout'suz beta modeli seçimi | **Kısmen tamamlandı** | Packaging §5.2 14 gün **öneri**; checkout yok (OD-011); **seçilmiş beta modeli yazılı karar/onboarding metni yok** | E7, OD-011 |

---

## Aşama 4 — Commercial Launch (giriş kriterleri)

Kaynak: [`pre-commercial-release-plan.md` §269–285](./pre-commercial-release-plan.md#aşama-4--commercial-launch)

| # | Kriter | Durum | Kanıt | İlgili gap / RB / OD |
|---|--------|-------|-------|----------------------|
| L1 | Open Beta **çıkış kriterleri** tamamlandı | **Başlanmadı** | Beta metrik kanıtı **yok** | — |
| L2 | **OD-011 uygulama paketi** onaylandı ve uygulandı | **Başlanmadı** | [`payment-scope-decision.md`](../memory/payment-scope-decision.md) `decision-approved` / **`implementation-pending`**; PSP/checkout/webhook yok | G-12, OD-011, Bank B1–B2 |
| L3 | Bank checklist **kritik blockers** B1–B5 kapalı | **Başlanmadı** | [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) yönetici özeti: B1 PSP **Eksik**, B2 checkout **Eksik**, B3 hukuk **Eksik**, B4 fiyat/vergi **Eksik**, B5 landing **Eksik** | G-13–G-15, G-07–G-09 |
| L4 | Pro self-serve veya Business teklif yolu tanımlı | **Başlanmadı** | Packaging §3 planlama only; kayıt/ödeme yolu yok (first-customer #2) | G-21 |
| L5 | PCI ilkesi: kart verisi Lumos yüzeyinde tutulmaz | **Tamamlandı** | OD-011 + Packaging §7.3 + bank checklist §1 | — |
| L6 | İptal/iade self-servis veya destek yolu **canlı** | **Başlanmadı** | Packaging §6 çerçeve only; self-servis UI yok (E7, bank §4–§5) | G-20 |
| L7 | ADR-012: **CLOSED** veya resmi defer + müşteri iddiası hizası | **Başlanmadı** | ADR-012 §204 «CLOSED değildir»; Wave 1 #491–493 kısmi PR-C6; resmi launch defer kaydı yok | G-18, RB-01 |
| L8 | Vault/entegrasyon: prod değilse demo-stub sınırı README/panelde | **Kısmen tamamlandı** | [`public-repo-boundary.md`](../memory/public-repo-boundary.md); README NOTICE; **panel modül iddiaları vs stub** tutarlılığı tam denetlenmedi `[HİPOTEZ]` | RB-10, RB-16 |
| L9 | Publish/release CI veya resmi manuel release runbook | **Başlanmadı** | RB-08: yalnızca `ci.yml` + manuel `prod-smoke.yml`; PyPI/npm publish yok; RB-07 checklist dosyası yok | G-16, G-19, RB-07, RB-08 |
| L10 | Hukuk + mali onay: fiyat, vergi, mesafeli satış [KKTC], e-fatura | **Başlanmadı** | Bank checklist §4–§5 + Packaging feragat; **dış hukuk/mali onay kanıtı yok** (repo kapsamı dışı) | G-22, Bank B4 |

**Commercial Launch giriş gap sayısı:** **10** (7 başlanmadı + 2 kısmen + 1 önkoşul beta/pilot zinciri `[L1]` ayrı sayılmazsa Launch-spesifik 9 + L1).

---

## Konsolide master gap listesi

Tüm **Kısmen** + **Başlanmadı** maddeler; mükerrerler birleştirildi. Öncelik: **bir sonraki aşama giriş blockeri**.

| ID | Gap | Öncelik | Blocker for | RB / OD / Bank |
|----|-----|---------|-------------|----------------|
| **G-23** | P0/P1 triage listesi + sahip yok | **P0** | Internal Alpha giriş | — |
| **G-24** | Yazılı Internal Alpha release kapsamı (ekip onayı) | **P0** | Internal Alpha giriş | GAP-01, RB-09 |
| **G-18** | ADR-012 Alpha defer tek kayıt (Launch'ta CLOSED/defer) | **P0** | Alpha giriş / Launch | RB-01, RB-05 |
| **G-02** | Çekirdek yolculuk Alpha çıkış doğrulanmadı (≥2 hafta, P0=0) | **P1** | Closed Pilot giriş | RB-07 |
| **G-03** | Modül menüsü «henüz aktif değil» / rozet (RB-17) | **P1** | Closed Pilot giriş | RB-17, E3 |
| **G-04** | Pilot sözleşmesi + davet listesi (≤20) | **P1** | Closed Pilot giriş | — |
| **G-05** | Yazılı destek kanalı + best-effort SLA | **P1** | Closed Pilot giriş | E9 |
| **G-06** | Pilot kohort barındırılmış köprü veya tam self-host paketi | **P1** | Closed Pilot giriş | RB-02 |
| **G-07** | Yayınlanmış hukuki sayfalar (gizlilik, kullanım, iade, çerez) | **P1** | Open Beta giriş | Bank B3 |
| **G-08** | Landing / vitrin beta seviyesi | **P1** | Open Beta giriş | OD-048, Bank B5 |
| **G-09** | İletişim sayfası [KKTC] adres + e-posta | **P1** | Open Beta giriş | Bank B5 |
| **G-10** | Beta katılım / waitlist politikası | **P2** | Open Beta giriş | — |
| **G-11** | Destek ticket runbook + escalation | **P2** | Open Beta giriş | — |
| **G-12** | OD-011 uygulama (PSP, checkout, webhook, abonelik) | **P0** | Commercial Launch | OD-011 |
| **G-13** | Bank B1: PSP + merchant başvuru | **P0** | Commercial Launch | Bank B1 |
| **G-14** | Bank B2: checkout sandbox + canlı | **P0** | Commercial Launch | Bank B2 |
| **G-15** | Bank B4: fiyat + vergi/fatura [KKTC] | **P0** | Commercial Launch | Bank B4 |
| **G-16** | Publish/release CI veya runbook (RB-08) | **P0** | Commercial Launch | RB-08 |
| **G-17** | Python packaging tek `pip install` (RB-06) | **P1** | Commercial Launch | RB-06 |
| **G-19** | Release checklist dosyası (RB-07) | **P1** | Beta+ / Launch | RB-07 |
| **G-20** | İptal/iade self-servis canlı | **P1** | Commercial Launch | Packaging §6 |
| **G-21** | Pro/Business satış yolu operasyonel | **P1** | Commercial Launch | first-customer #2 |
| **G-22** | Hukuk + mali onay [KKTC] | **P0** | Commercial Launch | Bank §4–§5 |
| **G-25** | RB-02/03 köprü consume + LockState Launch kararı | **P2** | Launch (müşteri etkisi) | RB-02, RB-03 |
| **G-26** | CONTRIBUTING.md yok (OSS katkı süreci) | **P3** | Launch soft | RB-14 |
| **G-27** | OSS vs Pro tek sayfa müşteri özeti (E6) | **P2** | Pilot/Beta | E6 |

**Toplam benzersiz gap:** **25** (giriş tablolarındaki 27 satırdan birleştirme).

---

## Çıkarılan aşama vs plan

| Boyut | Plan | Repo gerçekliği |
|-------|------|-----------------|
| **Resmi aşama** | Aşama 0 Pre-Alpha | **Aşama 0 — Pre-Alpha** |
| **Internal Alpha giriş** | 5 kriter | **2/5 tamam** → giriş **kısmi** |
| **En yakın geçiş** | Pre-Alpha → Internal Alpha | **3 gap** (G-23, G-24, G-18 kısmi kapanış) |
| **Commercial Launch** | B1–B5 + OD-011 kapı | **Hazır değil** — bank checklist 22 eksik madde |

---

## Çapraz referans — `pre-commercial-release-plan.md`

| Plan bölümü | Bu belge bölümü |
|-------------|-----------------|
| §74–85 Aşama 0 | Çıkarılan aşama |
| §93–99 Alpha giriş | Aşama 1 tablosu |
| §147–155 Pilot giriş | Aşama 2 tablosu |
| §206–218 Beta giriş | Aşama 3 tablosu |
| §269–285 Launch giriş | Aşama 4 tablosu |
| §381–398 RB matrisi | Master gap RB sütunu |
| §404–418 Bank matrisi | G-07–G-15 |
| §422–441 OD-011 / ADR-012 | G-12, G-18 |

---

## Son repo doğrulamaları (2026-06-21)

| Alan | Gözlem |
|------|--------|
| CI | `main` #493 CI **success** |
| ADR-012 Wave 1 | #491, #492, #493 merged; PR-W1-05/06 **plan** aşamasında |
| Quantum | ADR-013 Faz-2 kısmi; ROADMAP quantum iskelet — **Launch blocker değil** |
| Panel | `welockai.com/panel` canlı; prod Sınırlı mod ([`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md)) |
| Packaging | `pyproject.toml` yalnız `lumos-core`; CI `PYTHONPATH` zorunlu (RB-06) |
| Docs | `GITHUB_RELEASE_CHECKLIST.md` **0 dosya**; `CONTRIBUTING.md` **0 dosya** |

---

*Son güncelleme: 2026-06-21 — analiz only; kod/PR yok.*
