# Lumos kendini yönetme yüzeyi — Kontrol → Denetim → Güven

| Alan | Değer |
|------|-------|
| Durum | **Yüzey modeli KARAR; uygulama FİKİR** — kod yok; yeni sayfa yok |
| Tarih | 2026-08-27 kullanıcı kararı |
| Kanıt merdiveni | Model: **KARAR**. Uygulama: **FİKİR** ([scope-accounting](./scope-accounting.md)) |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md) §1/§5, [`ROADMAP.md`](../ROADMAP.md) STOP LIST, [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) |
| İlgili | [ADR-007](../decisions/ADR-007-trust-engine-layer.md), [ADR-010](../decisions/ADR-010-guard-policy-trust-terminology.md), [ADR-017](../decisions/ADR-017-regulated-service-entity-boundaries.md), [ADR-019](../decisions/ADR-019-product-surface-separation-modelregistry.md), [ADR-027](../decisions/ADR-027-controlled-core-writer.md), [ADR-028](../decisions/ADR-028-standing-low-risk-merge-approval.md), [ADR-029](../decisions/ADR-029-dashboard-health-earned-responsibility.md), OD-011 [`payment-scope-decision.md`](../memory/payment-scope-decision.md), [`welockai-charter-draft.md`](./welockai-charter-draft.md), [`lumos-log-vs-approval.md`](./lumos-log-vs-approval.md), [`lumos-audit-log-contract.md`](./lumos-audit-log-contract.md), [`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md), KA-005 |

**Sınır notu:** Bu kayıt yeni ürün, yeni rota veya yeni orchestration katmanı **açmaz**. FAZ-1 STOP LIST (`yeni sayfa`, `yeni özellik`, `yeni agent / orchestration katmanı`) yürürlükte kalır. Uygulama ayrı kullanıcı kararı ister.

---

## Cümle

> **Lumos sadece sistemi çalıştırmaz; sistemin kendini nasıl yönettiğini de gösterir.**

Bu cümle mevcut vaadi değiştirmez; onu görünür kılar. Onay vaadi durur: *kalıcı veya riskli adım kullanıcı onayı olmadan atılmaz.* Kendini yönetme vaadi şudur: o onay, kayıt ve harcama **gizli motor değil, görünen yüzeydir**.

---

## Karar: üç ürün değil, aynı panelin üç merceği

Kullanıcı kararı (2026-08-27): yüzey **dönüşebilir**. Dönüşebiliyorsa üç ayrı merkez kurulmaz.

| Mercek | Soru | Kullanıcıya görünen |
|--------|------|---------------------|
| **Kontrol merkezi** | Ne çalışıyor, ne harcıyor, hangi işlem? | Canlı durum, maliyet/kaynak, aktif iş |
| **Denetim merkezi** | Bu işlem doğru muydu, yetkili miydi, kayıt var mı? | Kanıt, yetki, append-only iz |
| **Güven kurulu** | Bu kritik adım şimdi yapılsın mı? | İnsan / onay / kural katmanı |

Sıra bağlayıcıdır: kontrol görünmeden denetim iddiası yok; kayıt yokken güven kurulu «evet» sayılmaz. Bu, **Karar ≠ Kayıt** ile aynı omurgadır — onay geleceği yönetir, kayıt geçmişi korur; ikisi birbirinin yerine geçmez.

**Yol kuralı:** mercekler `/panel` içinde açılır. `/kontrol`, `/denetim`, `/guven` **yoktur**. `Lumos Workboard` / `Control Wall` ürünleştirilmez (ADR-019).

---

## İki yüzey, aynı mercek dili

| Mercek | Son kullanıcı (`/panel`) | Operatör (Lumos Agent Wall) |
|--------|--------------------------|-----------------------------|
| Kontrol | İşlem, durum, harcama — **Lumos dilinde** | Görev → sağlayıcı/model → oturum → süre → hata |
| Denetim | «Bu işlem kaydı var mı, yetkili miydi?» | Evidence / audit kuyruğu, correlation |
| Güven kurulu | Bekleyen onay kartı; `SECURITY_NEVER_AUTO` | Decision Queue / Human Action Queue; üçlü merge kapısı |

**«Hangi model?»** kullanıcı kontrolünün kimliği değildir. Sağlayıcı ve model adı kullanıcı yüzeyine sızmaz ([ADR-019](../decisions/ADR-019-product-surface-separation-modelregistry.md), PR-005). Teknik şeffaflık yalnız açık soru, hukuki veya sözleşmesel gerekçeyle; ürün kimliği olarak sunulmaz. Model/maliyet ayrıntısı Agent Wall’dadır.

**Güven kurulu ≠ Trust Engine.** Trust Engine (ADR-007) kimlik, kilit, consent, presence **sinyalleridir**; henüz birleşik motor yoktur. Güven kurulu o sinyallerin **insan/onay yüzüdür**. Guard ≠ trust ≠ confirmation (ADR-010) buradan değişmez.

---

## Bugünkü parçalar — yeni kod değil, mevcut bağ

Üç mercek sıfırdan yazılmaz. Panelde zaten dağınık duran sinyaller aynı bakışa çekilir.

| Mercek | Bugün var | Henüz yok |
|--------|-----------|-----------|
| Kontrol | Panel sağ/alt operasyon özeti ([`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md)); dashboard health sözlüğü ([ADR-029](../decisions/ADR-029-dashboard-health-earned-responsibility.md) — `bridge.llm` Observe); `resource_usage.jsonl` | Ölçülmemiş rozetlerin canlı bağlanması; kullanıcı dilinde harcama özeti |
| Denetim | Evidence journal; panel «Son işlem kanıtı»; [`lumos-audit-log-contract.md`](./lumos-audit-log-contract.md) taslak | Birleşik `lumos.audit_event.v1` uygulaması; yetki+kayıt tek bakış |
| Güven kurulu | `confirmation_policy`, `SECURITY_NEVER_AUTO`, pending onay; Agent Wall Decision Queue (OD-063, salt okuma) | Kullanıcı panelinde tek «kritik karar» merceği; sessiz onay yok kuralının yüzeye bağlanması |

ADR-029’un üç cümlesi aynı merdivendir: **izler** (kontrol) → **düzeltir** (denetim kanıtıyla) → **yükseltir** (güven kurulu). Meta-kural durur: Lumos bir alanın sorumluluğunu üstlenebilir; o alanı yönetmek için kendi yetki sınırını değiştiremez.

İç birleştirme (üçlü merge kapısı, standing class) **kullanıcı paneline sızmaz**. O, Agent Wall / çekirdek yazıcı rejimidir.

---

## Ne değildir

- Yeni sayfa, yeni nav öğesi, logo turu veya vitrin ekranı
- Yeni agent / orchestration katmanı veya ikinci motor
- WeLockAI ticari audit arşivinin public kopyası
- KA-005’in (`Lumos’u aç` birleşik durum) **DOĞRULANDI** ilanı — kontrol merceği o fikri kapsar; kanıt merdiveni yükselmez
- FAZ-1 uygulama izni
- Yeni küresel bordro / payroll ürünü, ülke seçici UI, public-repo üretim ödemesi

---

## Sonraki adım (uygulama değil)

**Sıra (2026-08-28):** önce insan **FAZ-1 kapanış onayı**; sonra panel bağlantısı. 2026-08-28 ülke/ödeme güven-mimarisi kaydı bu sırayı **değiştirmez** — yeni faz veya panel işi değildir. Bu ajan FAZ-1'i kapatmaz, `main`'e merge etmez, FAZ-1 bitti demez.

Gözlem (kapanış iddiası değil): ROADMAP'te FAZ-1 ürününün en zayıf halkası hâlâ **iOS / TestFlight**.

O onay gelene kadar: kod yok, yeni panel yok, yeni sayfa yok; STOP LIST sürer. Panel bağlama (mevcut operasyon özeti + kanıt şeridi + pending onay, aynı `/panel`) **ancak** o onaydan sonra.

Panel işi açılırsa sıra değişmez:

1. Mevcut sağ/alt özet + evidence şeridi + pending onay kartını **aynı mercek sözleşmesine** bağla.
2. Ölçülmeyen göstergeyi yeşil yapma (ADR-029).
3. Yeni rota açma.

Canonical yön: [`ROADMAP.md`](../ROADMAP.md) § Panel kendini yönetme yüzeyi. Ürün cümlesi: [`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md).

---

## Gerekçe malzemesi (2026-08-28) — yeni yön değil

Kontrol dili güçlenir; ROADMAP, STOP LIST ve uygulama merdiveni **değişmez**. Bu maddeler yeni sayfa, yeni SOC, yeni cihaz entegrasyonu veya yeni CI ürünü **açmaz**.

> **Lumos’ta güvenlik sadece erişimi kesmek değil; izin verilen yolların da davranışını izlemek olmalı.**

Özet kural: [`security-architecture.md`](../security-architecture.md) SEC-006.

| Malzeme | Güçlenen ilke | Lumos karşılığı | Ne değildir |
|---------|---------------|-----------------|-------------|
| **Sandbox yetmez** | Guardrails dosyası ≠ gerçek izolasyon + izleme | Workspace sandbox + guard; denetim merceği | Yeni sandbox ürünü |
| **İç servis yan kanalı** | Ajan internete çıkmasa bile paket yöneticisi / log / depo izinli haberleşme kanalı olabilir; **izinli kanal da denetlenir** | SEC-021 köprü + evidence / audit | Yeni IDS |
| **AI SOC elemesi** | Yalnız triage değil; yaşam döngüsü boyunca **kayıtlı aksiyon ve onay** | Denetim merceği + güven kurulu; confirmation + evidence | Yeni SOC ürünü |
| **Ev/cihaz gizliliği** | Router hareket, araba ekranı, TV/proxy, WebAudio parmak izi — kişisel cihaz katmanının **kanıtı** | Mevcut cihaz/presence/gizlilik anlatısı | Yeni entegrasyon (STOP LIST) |
| **Tedarik zinciri** | Geliştirici araçları, paketler, CI, sahte demo siteleri | Mevcut dependency / CI / merge kapısı | Yeni CI ürünü |

Panel zamanı gelince bağlanan yüzey hâlâ aynıdır: özet + kanıt + pending onay. İzinli yolun izlenmesi denetim merceğinin gerekçesidir; üçüncü bir merkez değildir.

---

## Gerekçe malzemesi (2026-08-28) — ülke ve güven mimarisi; yeni yön değil

Kontrol dili büyür; kapsam büyümez. Bu madde FAZ-5, yeni sayfa, yeni katkıcı ürünü veya STOP LIST istisnası **açmaz**. SEC-006 durur; bu bitişik güven gerekçesidir, yerine geçmez. Sıra değişmez: önce insan FAZ-1 kapanış onayı, sonra panel bağlantısı.

> **Ülke, fırsata duvar olmamalı; ödeme, kur, vergi ve uyum ise güven mimarisinin parçasıdır.**

Küresel ekip ve katkıcı modeli ülke sınırına takılmaz. Kullanıcının veya katkıcının ülkesi fırsata gereksiz duvar olmaz.

Ödeme, kur (FX), vergi ve uyum ürünün dışına dökülen detay değildir; **güven mimarisinin** parçasıdır. Güven kurulu bunların insan / onay / kural yüzüdür — yeni Trust Engine (ADR-007) veya yeni ticari ürün değildir. Üretim yeri WeLockAI / private katmandır; public `lumos-core` production billing, PSP credential veya PII **almaz**.

Özet kural: [`security-architecture.md`](../security-architecture.md) SEC-007. Kuruluş sınırları: [ADR-017](../decisions/ADR-017-regulated-service-entity-boundaries.md). Ödeme uygulama parkı: OD-011 / [DL-E01](../decision-log.md).

| Malzeme | Güçlenen ilke | Lumos karşılığı | Ne değildir |
|---------|---------------|-----------------|-------------|
| **Ülke ≠ fırsat duvarı** | Global katılım ülke sınırına takılmaz; ülke sahte ürün duvarı değildir | Lumos Dünya küresel yüzey (ADR-017); güven kurulu | Ülke seçici UI; yeni katkıcı ürünü; ülke sistemi uygulaması |
| **Ödeme / kur / vergi / uyum** | «Başkasının sorunu» diye dışarı atılmaz; güven mimarisinde durur | Güven kurulu + WeLockAI ticari omurga; OD-011 parkı durur | Public-repo üretim ödemesi; checkout/PSP kodu; FAZ-1 kapanışı |
| **Kamu / ülke sistemi** | Bağlantı markasız private/sözleşmeli katmandır; otorite algısı yok | ADR-017 Ülke Sistemleri Entegrasyon Katmanı | Lumos Devlet; kamu yönetim yüzeyi |

### Ne değildir (bu madde)

- Yeni küresel bordro / payroll ürünü
- Yeni ülke seçici UI veya ülke bazlı fırsat duvarı
- FAZ-1 kapanışı veya panel kodu / panel bağlama
- Public repoda üretim ödemesi, faturalama, PSP, PII
- OD-011 uygulama parkının açılması veya ADR-017 kuruluş birimlerinin birleşmesi

### DECISION_CONFLICT — yok; gerilim kaydı

ADR-017 ve OD-011 / DL-E01 **sessizce geçersiz kılınmaz**. Gerilim şudur: ödeme «aktif kapsam dışı» park edilmiş; yeni cümle ödeme/vergi/kur/uyumu güven mimarisine koyuyor. Çözüm (2026-08-28 kullanıcı hizası):

- **Uygulama parkı durur.** DL-E01 / OD-011 checkout, PSP, settlement, fatura motoru yazdırmaz. Bu kayıt «şimdi kod» değildir.
- **Konu dışarı atılmaz.** Park, ödeme/vergi/kur/uyumun «başkasının sorunu» olduğu anlamına gelmez; güven mimarisinde durur. Üretim WeLockAI / private; OSS demo-safe kalır ([`public-repo-boundary.md`](../memory/public-repo-boundary.md), [`welockai-charter-draft.md`](./welockai-charter-draft.md)).
- **Ülke sahte ürün duvarı değildir.** ADR-017 Lumos Dünya’yı küresel katılım yüzeyi, ülke sistemini markasız private katman sayar. Bu kayıt ülke sistemi uygulaması veya `country_pack` açmaz; katkıcı/kullanıcı fırsatını ülke ile kesmez.
