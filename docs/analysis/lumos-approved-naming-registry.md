# Lumos Onaylı İsim Kaydı (Naming Registry)

| Alan | Değer |
|------|-------|
| Durum | **Karar destek — APPROVED LOCKED** (§A) ve **EXAMPLE** (§B) ayrımı sabit |
| Tarih | 2026-06-26 |
| Kapsam | Ürün, hiyerarşi, yüzey, rol ve izin sembolleri; örnek kuruluş adları |
| İlgili | [`lumos-organization-model-draft.md`](./lumos-organization-model-draft.md), [`welockai-charter-draft.md`](./welockai-charter-draft.md), [`welockai-trust-model-draft.md`](./welockai-trust-model-draft.md), [`integrations-overview.md`](../integrations-overview.md) |

**Kullanım kuralı:** §A maddeleri dokümantasyon, UI ve ürün metninde **onay beklemeden** kullanılır. §B maddeleri yalnızca **örnek / demo** bağlamında kullanılır; ürün adı veya sabit müşteri kimliği olarak **ship edilmez**. §C maddeleri kullanılmadan önce açık onay gerektirir.

---

## A. Onay gerektirmez — sabit (APPROVED LOCKED)

Bu tablodaki isimler repoda kanıtlanmış ve **kilitleme** altındadır.

### A.1 Ürün ve marka

| İsim | Tür | Kanıt / not |
|------|-----|-------------|
| **Lumos** | Ürün (OSS çekirdek + yardımcı) | Charter §1, trust model §2.2 |
| **WeLockAI** | Ticari omurga (yazım: bitişik) | Charter §1, trust model §2.3 |
| **We Lock AI** | Marka çatısı (UI eyebrow / başlık) | `ui/` umbrella sayfaları — boşluklu görünen ad |
| **welockai.com** | Birincil domain | [`integrations-overview.md`](../integrations-overview.md), charter §4 |
| **api.welockai.com** | Üretim API host (private) | Charter §3 |
| **Lumos Cyber** | Ürün varyantı adı + kilitli tagline (§A.8) | `ui/src/pages/cyber.astro`, `ui/src/i18n/messages/umbrella/*.ts` |

### A.2 Kuruluş hiyerarşisi (canonical terimler)

| TR (sabit) | EN (sabit) | Seviye |
|------------|------------|--------|
| **Kuruluş** | **Organization** | 1 |
| **Ekip** | **Team** | 2 |
| **Proje** | **Project** | 3 |
| **Konu** | **Topic** | 4 (alt bağlam; İngilizce eşdeğerde *Channel* bağlam notu olarak geçebilir) |

Kaynak: [`lumos-organization-model-draft.md`](./lumos-organization-model-draft.md) §4.

### A.3 Yüzeyler ve rotalar (welockai.com)

| Rota | Rol |
|------|-----|
| `/panel` | Birincil web workspace |
| `/integrations` | Entegrasyon merkezi |
| `/integrations/github` | GitHub connector sayfası |
| `/integrations/google` | Google connector sayfası |
| `/integrations/mail` | Mail (Gmail) connector sayfası — OD-031 Dar v1 read-only |
| `/integrations/linear` | Linear connector sayfası — OD-033 Katman 3 planned |
| `/slack` | Slack entegrasyon yüzeyi |
| `/connect/mac` | Mac Universal Links / AASA |
| `/cyber` | Lumos Cyber erken erişim landing |
| *(planlı)* **Lumos Quantum Layer** | Kuantum kaynak kataloğu + onaylı bağlantı planı — `/cyber` altında değil; bkz. [`lumos-quantum-layer-architecture.md`](./lumos-quantum-layer-architecture.md) |

Kaynak: [`integrations-overview.md`](../integrations-overview.md), `ui/src/pages/`.

### A.4 Roller (güven modeli)

| Rol | Sabit ad |
|-----|----------|
| Son kullanıcı | **Kullanıcı** |
| OSS runtime yardımcı | **Lumos** |
| Ticari omurga | **WeLockAI** |
| Dış sistemler | **Araçlar** |
| Kurumsal yönetim | **İnsan yönetici** |

Kaynak: [`welockai-trust-model-draft.md`](./welockai-trust-model-draft.md) §2.

### A.5 İzin sembolleri ve profiller

| Sembol / terim | Anlam |
|----------------|-------|
| **Read ✅** | Okuma / analiz — onaysız profil ile uyumlu |
| **Write 🔒** | Yazma — onay veya kurumsal politika gerekir |
| **Delete 🚫** | Silme / geri dönüşsüz — özel izin; `SECURITY_NEVER_AUTO` sınıfı |
| `rapor` | Lumos profil — salt analiz |
| `guvenli_yurut` | Lumos profil — safe_local |
| `kisitli_otonom` | Lumos profil — sınırlı write_local, genel onay ile |

Kaynak: Charter §5, trust model §4, ADR-012.

### A.6 Faz / program adları

| Ad | Anlam |
|----|-------|
| **Internal Alpha** | Ekip-içi foundation build fazı |
| **Closed Pilot** | Sınırlı müşteri pilotu (≤20 davet vb.) |

Kaynak: `docs/INTERNAL_ALPHA_RELEASE_SCOPE.md`, trust model §9 Alpha notları.

### A.7 Teknik placeholder (onaylı format — değer değil)

| Kalıp | Kullanım |
|-------|----------|
| `XXXXXXXXXX` | Apple Team ID **yer tutucu** — gerçek ID ship öncesi dış kaynaktan |
| `com.welockai.lumos` | Bundle ID **yer tutucu** — Mac istemci ship öncesi doğrulanır |

Kaynak: [`mac-app-link-layer.md`](../mac-app-link-layer.md), `ui/src/i18n/messages/umbrella/*.ts`.

### A.8 Slack eşlemesi ve demo kuruluş kalıpları (2026-06-26 onay)

| Kalıp / terim | TR (sabit) | EN (sabit) | Not |
|---------------|------------|------------|-----|
| Slack workspace | **Kuruluş özel alanı** | **Organization private area** | Kuruluşun özel workspace'i; Slack workspace eşlemesi olabilir, model Slack'e indirgenmez |
| Slack kanal (ürün bağlamı) | **Konu** | **Topic** | Proje altında; hiyerarşi §A.2 |
| Duyuru yüzeyi | **duyuru konusu** | **announcement topic** | `#general` gibi sabit kanal adları ürün metninde **kullanılmaz** |
| Demo kuruluş adı | **ÖrnekKuruluş-A** / **-B** / **-C** | aynı | Dokümantasyon ve demo; gerçek müşteri adı değil |

**Lumos Cyber — kilitli tagline (TR):** «Lumos Cyber, We Lock AI çatısı altında güvenlik operasyonları, risk görünürlüğü ve politika odaklı çalışma için planlanan varyanttır. Ayrı bir cyberpunk arayüz değil; profesyonel kontrol katmanıdır.»

**Lumos Cyber — locked tagline (EN):** «Lumos Cyber is the planned We Lock AI variant for security operations, risk visibility, and policy-focused work. It is not a cyberpunk UI — it is a professional control layer.»

Kaynak: kullanıcı onayı «uygundur uygula» (2026-06-26); [`lumos-organization-model-draft.md`](./lumos-organization-model-draft.md) §4–§9.

**§A toplam: 44 kilitli isim / terim / kalıp** (ürün 6 + hiyerarşi 8 + rota 9 + rol 5 + izin 6 + faz 2 + teknik kalıp 2 + Slack/demo 6).

---

## B. Örnek / onay gerekir (EXAMPLE — ürün adı olarak ship etme)

Bu tablodaki isimler **yalnızca dokümantasyon ve demo örneği** içindir. UI, API veya kalıcı config'te **literal müşteri / kuruluş adı** olarak kullanılmaz.

### B.1 Teknoloji şirketi örnekleri (org adı değil)

| Örnek | Doğru kullanım | Yanlış kullanım |
|-------|----------------|-----------------|
| **Apple** | Mac / AASA / Team ID teknik bağlamı (`/connect/mac`) | Kuruluş veya pilot müşteri adı |
| **Android** | Mobil platform notu (readiness / watchlist) | Kuruluş adı veya ürün markası |
| **Huawei** | Org modeli tartışma örneği (§8) | Kuruluş adı veya entegrasyon markası |

### B.2 Kuruluş türü örnekleri (tip — sabit isim değil)

| Örnek tür | Not |
|-----------|-----|
| Belediye, üniversite, hastane, startup | Kamu / eğitim / sağlık / KOBİ **tür** örnekleri |
| Teknoloji şirketi (generic) | Apple/Android/Huawei **yerine** «teknoloji şirketi» veya `ÖrnekKuruluş-*` |

### B.3 Yer tutucu kuruluş adları (tercih edilen kalıp)

| Kalıp | Kullanım |
|-------|----------|
| **ÖrnekKuruluş-A**, **ÖrnekKuruluş-B**, **ÖrnekKuruluş-C** | Çok kiracılı senaryo, üyelik, paylaşımlı proje — **tercih edilen** demo kalıbı (§A.8) |
| **Org A** / **Org B** | Eski kısa not; **yeni metinde kullanma** — `ÖrnekKuruluş-A` kullan |
| **Acme Corp**, **Example Inc.** | Jenerik İngilizce demo — onay olmadan üretim metninde kullanma |

### B.4 Entegrasyon demo metinleri

| Örnek | Not |
|-------|-----|
| `#general`, `#proj-x` | Slack **kanal** anti-pattern örnekleri — org modeli değil |
| Placeholder workspace adları | Gerçek Slack workspace adı ship etme |

**§B toplam: 14 örnek kategorisi / kalıp** (B.1: 3 + B.2: 5 tür + B.3: 4 kalıp + B.4: 2).

---

## C. Onay durumu

### C.1 Çözüldü — APPROVED LOCKED (2026-06-26)

Kullanıcı onayı «uygundur uygula» ile kilitlendi; ayrıntı §A.8.

| Konu | Karar |
|------|-------|
| Slack workspace adlandırma | Slack workspace = **Kuruluş özel alanı**; org modeli Slack kanal listesini tanımlamaz |
| Slack kanal (ürün metni) | **Konu** (Proje altı); sabit `#general` vb. yok — **duyuru konusu** / **announcement topic** |
| Demo kuruluş adları | Dokümantasyon ve demo: yalnızca `ÖrnekKuruluş-A` / `-B` / `-C` |
| **Lumos Cyber** tagline | §A.8'de kilitli (hero `lead` metni) |

### C.2 Owner action — placeholder locked (PENDING real values)

Gerçek müşteri adları, destek e-postası ve Apple kimlik değerleri **repoda commit edilmez**. Aşağıdaki **kalıplar kilitlidir** (§A.7, §A.8, §B.3); yalnızca değerler owner tarafından doldurulur.

| Konu | Kalıp (kilitli) | Durum | Owner adımları |
|------|-----------------|-------|----------------|
| Pilot / müşteri kuruluş adları | `ÖrnekKuruluş-A` / `-B` / `-C` (demo); gerçek ad **Closed Pilot sözleşmesinde** | **OWNER_ACTION** | 1) [`pilot-contract-template.md`](./pilot-contract-template.md) doldur 2) Gerçek adı yalnızca private sözleşme / davet listesinde tut — public repoya yazma |
| Resmi destek e-postası | `support@<DOMAIN_TBD>` (örnek format; `support@welockai.com` **onaylanmadı**) | **OWNER_ACTION** | 1) Domain + posta kutusu oluştur 2) [`support-channel-alpha.md`](./support-channel-alpha.md) §Kanal tanımı güncelle 3) Bu tabloda §C.2 satırını APPROVED LOCKED yap |
| Apple Team ID | `XXXXXXXXXX` (10 karakter yer tutucu) | **OWNER_ACTION** | 1) [Apple Developer](https://developer.apple.com/help/account/manage-your-team/locate-your-team-id/) Team ID al 2) AASA dosyasında **deploy ortamında** güncelle — repoda gerçek ID yok |
| Bundle ID | `com.welockai.lumos` (yer tutucu) | **OWNER_ACTION** | 1) Mac app target bundle ID doğrula 2) AASA `appID` = `{TeamID}.{bundleId}` ship öncesi 3) [`mac-app-link-layer.md`](../mac-app-link-layer.md) SHIP BLOCKER kapat |

**Yasak:** Public repoda sahte müşteri adı, gerçek görünümlü e-posta veya Apple Team ID commit etmek.

### C.3 Mimari ad onaylı — dış kullanım düzenleme kapılı (2026-07-13)

Kullanıcı yönüyle aşağıdaki çalışma adları **mimari ve karar belgelerinde onaylıdır**. Bunlar §A gibi koşulsuz public ürün iddiası değildir; ilgili hukuk, lisans, tüzel kişilik, marka ve kamu yetkisi kapıları geçilmeden UI'da aktif/resmi hizmet olarak ship edilmez.

| Çalışma adı | Mimari sınıf | Dış kullanım kapısı |
|-------------|---------------|---------------------|
| **Lumos Bank** | Ayrı düzenlemeye tabi finansal kuruluş hedefi | Banka/finans lisansı veya yetkili partner modeli + hukuk/marka onayı |
| **Lumos Sepet** | Ayrı ticaret ve kullanıcı tercih hizmeti hedefi | Tüketici, sözleşme, iade/iptal ve ödeme-onay modeli |
| **Lumos POS** | Ayrı merchant ödeme kabul hizmeti hedefi | PSP/merchant, settlement, itiraz ve ülke mevzuatı onayı |
| **Lumos Dünya** | İnsan odaklı küresel tanışma ve katılım yüzeyi; ticari birimlerden ayrı | `candasoz01-cmd/Lumos` PR #102 uygulandı; canonical kilit kurucu onayı bekliyor |
| **Ülke Sistemleri Entegrasyon Katmanı** | Mevcut ülke sistemleri için private/sözleşmeli teknik kabiliyet; public ürün adı değil | Yetkili sözleşme + ülkeye özgü adaptör/yetki matrisi |

**Kaldırılan ad:** **Lumos Devlet** — public marka, kuruluş birimi veya ürün yüzeyi olarak kullanılmaz. Küresel yüzey **Lumos Dünya**; ülke sistemleri bağlantısı markasız teknik entegrasyon katmanıdır.

**Zorunlu ifade sınırı:** Lumos bugün banka, PSP, ödeme kuruluşu veya devlet/kamu otoritesi olarak tanıtılmaz. Canonical sorumluluk ayrımı: [`ADR-015`](../decisions/ADR-015-regulated-service-entity-boundaries.md); kanıt ve aşama modeli: [`lumos-institutional-service-foundation.md`](./lumos-institutional-service-foundation.md).

**Çapraz:** NA-03, NA-05 — [`todo-fixme-sweep-report.md`](./todo-fixme-sweep-report.md); P1-03 / P1-04 — [`INTERNAL_ALPHA_OPERATIONS.md`](../INTERNAL_ALPHA_OPERATIONS.md).

---

## Çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`lumos-organization-model-draft.md`](./lumos-organization-model-draft.md) | Hiyerarşi §A.2; örnek org §B |
| [`welockai-charter-draft.md`](./welockai-charter-draft.md) | Ürün rolleri, izin matrisi §A.5 |
| [`welockai-trust-model-draft.md`](./welockai-trust-model-draft.md) | Rol adları §A.4 |
| [`integrations-overview.md`](../integrations-overview.md) | Yüzey URL'leri §A.3 |
| [`public-repo-boundary.md`](../memory/public-repo-boundary.md) | Public vs private içerik sınırı |

---

*Bu kayıt isim kararlarının tek indeksidir. Yeni APPROVED LOCKED madde eklemek için bu dosyada §A güncellenir ve ilgili foundation belgesine çapraz referans eklenir. EXAMPLE maddelerin ürün adına terfi etmesi açık onay gerektirir.*
