# Lumos Kurumsal Hizmet Hatları — Foundation ve Olasılık Modeli

| Alan | Değer |
|------|-------|
| Durum | **Karar destek — foundation**; uygulama bekliyor |
| Tarih | 2026-07-13 |
| Hedef | Lumos Bank · Lumos Sepet · Lumos POS · Lumos Devlet için sistemli kuruluş, aşama ve risk çerçevesi |
| Canonical karar | [`ADR-015`](../decisions/ADR-015-regulated-service-entity-boundaries.md) |
| Üst sınır | [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`payment-scope-decision.md`](../memory/payment-scope-decision.md) |

## 1. Niyet

Bu yapı dört adı aynı uygulamanın menüleri olarak değil, ayrı sorumluluk ve denetim alanları olarak ele alır. Kullanıcı deneyimi Lumos'ta tutarlı kalabilir; fakat para, merchant operasyonu, ticaret tercihi ve kamu verisi aynı yetki veya veri havuzuna girmez.

## 2. Kuruluş topolojisi

```mermaid
flowchart TB
  USER[Kullanıcı / kuruluş]
  LUMOS[Lumos kullanıcı yüzeyi]
  TRUST[Ortak güven sözleşmeleri\nkimlik · onay · politika · audit]

  BANK[Lumos Bank\nayrı lisanslı finans hattı]
  CART[Lumos Sepet\nticaret ve tercih hattı]
  POS[Lumos POS\nmerchant kabul hattı]
  GOV[Lumos Devlet\nmevcut sistem entegrasyon çerçevesi]

  USER --> LUMOS
  LUMOS --> TRUST
  TRUST --> BANK
  TRUST --> CART
  TRUST --> POS
  TRUST --> GOV

  CART -. ödeme niyeti .-> POS
  POS -. yetkili settlement .-> BANK
  GOV -. sözleşmeli birlikte çalışabilirlik .-> TRUST
```

Kesikli oklar otomatik yetki aktarımı değildir. Her geçiş yeni kapsam, politika ve açık onay değerlendirmesi gerektirir.

## 3. Sorumluluk matrisi

| Alan | Sahip olduğu bağlam | Sahip olmadığı bağlam | İlk güvenli çıktı |
|------|---------------------|-----------------------|------------------|
| Lumos Bank | Lisans sonrası finansal hesap/işlem sorumluluğu | Sepet kataloğu, merchant cihaz yönetimi, kamu yetkisi | Lisans ve partner gereksinim haritası |
| Lumos Sepet | Ürün/hizmet seçimi, tercih, teklif ve sipariş niyeti | Para saklama, settlement, tek taraflı satın alma | Sentetik katalog + onay akışı simülasyonu |
| Lumos POS | Merchant onboarding, ödeme kabul niyeti, iade/mutabakat orkestrasyonu | Banka lisansı, kullanıcı sepet profili, kamu kimliği | Sentetik merchant sandbox sözleşmesi |
| Lumos Devlet | Mevcut kamu sistemlerini bozmadan adaptör, güven ve birlikte çalışabilirlik sözleşmeleri | Devlet otoritesi, vatandaş adına karar, varsayılan yazma/müdahale yetkisi | Sistem envanteri + salt-okuma uyumluluk raporu |

## 4. Lumos Devlet: önce entegrasyon, sonra ülkeye özgü ayrıntı

Lumos Devlet mevcut kamu sistemlerini yeniden tasarlamaz ve tek bir küresel işleyiş dayatmaz. Kaynak sistem; kendi verisinin, iş kuralının ve işleminin authoritative sahibidir. Lumos yalnızca açıkça sözleşmelenmiş adaptör üzerinden bağlam, uyumluluk, risk ve onay görünürlüğü sağlar.

### Entegrasyon katmanları

| Katman | Amaç | Varsayılan |
|--------|------|------------|
| Keşif | Sistem sahibi, protokol, veri sınıfı, kimlik ve bağımlılık envanteri | Metadata; veri çekme yok |
| Salt-okuma | Şema uyumu, durum, provenance, gecikme ve hata izolasyonu | İlk teknik pilot |
| Öneri/taslak | Yetkili görevliye değişiklik önerisi veya doldurulmuş taslak sunma | İnsan uygular |
| Kontrollü yazma | Açıkça izinli tek operasyonu yetkili kaynak sisteme iletme | Kapalı; ülke talebi gerekir |
| Müdahale/acil durum | Kritik sistem işlemi veya otomatik durdurma | Tanımsız ve yasak; ayrıca hukuk, kurum ve güvenlik kararı gerekir |

### Tam entegrasyonun anlamı

`Tam entegrasyon`, sınırsız erişim değildir. Aşağıdaki koşulların birlikte sağlanmasıdır:

- mevcut sistem değişmeden authoritative kalır,
- resmi veya kurumca onaylı arayüz/adaptör kullanılır,
- kimlik ve yetki kaynak sistem tarafından doğrulanır,
- yalnız izinli alanlar ve operasyonlar görünür,
- her istek provenance ve correlation kimliği taşır,
- hata bir sistemden diğerine yayılmaz,
- bağlantı kesildiğinde kaynak sistem çalışmaya devam eder,
- ülke/kurum Lumos bağlantısını tek taraflı durdurabilir,
- audit kaydı içerik kopyası değil, gerekli olay ve kanıt özetidir.

Ülkeye özgü erişim seviyesi, müdahale hakkı, saklama süresi, veri yerleşimi ve kurumlar arası akış bu public foundation'da sabitlenmez; talep eden ülkenin sözleşmeli `country_pack` kaydında belirlenir.

## 5. Olasılık hesabı: tahmin değil, kanıt skoru

Kanıt olmadan yüzdelik başarı tahmini üretmek yanıltıcıdır. Bunun yerine her hat için aynı **100 puanlık hazır olma skoru** kullanılır:

| Boyut | Ağırlık | Kanıt örneği |
|-------|---------|--------------|
| Hukuk/lisans/yetki | 30 | Yazılı hukuk görüşü, lisans sınıfı, yetkili partner/sözleşme |
| Güvenlik ve veri izolasyonu | 25 | Threat model, bağımsız test, veri yerleşimi ve incident planı |
| Operasyon | 20 | Sorumlu ekip, destek, mutabakat/itiraz veya kamu olay süreci |
| Partner ve teknik uygulanabilirlik | 15 | Sandbox, resmi API, SLA, geri dönüş planı |
| Kullanıcı/kamu değeri | 10 | Pilot kanıtı, erişilebilirlik ve ölçülebilir ihtiyaç |

```text
readiness_score = legal*0.30 + security*0.25 + operations*0.20
                + partner*0.15 + value*0.10
```

Her boyut 0–100 arası yalnızca belgelendirilmiş kanıtla puanlanır. Sonuç istatistiksel başarı olasılığı değildir; yatırım ve aşama kararı için karşılaştırılabilir kanıt skorudur.

| Skor | Karar sınıfı | İzin verilen seviye |
|------|--------------|---------------------|
| 0–39 | Keşif | Doküman ve sentetik sandbox |
| 40–59 | Pilot adayı | Eksik kapılar kapatılır; canlı kullanıcı/para/kamu verisi yok |
| 60–79 | Kontrollü pilot incelemesi | Sınırlı partner ve izole ortam; ayrıca insan onayı |
| 80–100 | Üretim incelemesi | Otomatik yayın değil; bağımsız hukuk/güvenlik/operasyon onayı |

### Sıfırlayan kapılar

Aşağıdaki koşullardan biri yoksa ilgili **canlı aşama skordan bağımsız olarak geçilemez**:

- Lumos Bank: gerekli lisans/yetki veya lisanslı partner sözleşmesi.
- Lumos POS: merchant/PSP hukuki modeli, settlement ve itiraz sorumlusu.
- Lumos Sepet: açık satın alma onayı, iade/iptal ve tüketici hakları akışı.
- Lumos Devlet: yetkili kamu sözleşmesi, mevcut sistem envanteri, veri sınıflandırması, veri yerleşimi ve operasyon bazlı yetki matrisi.
- Tüm hatlar: amaç bazlı erişim, tenant izolasyonu, audit, olay müdahalesi ve geri dönüş planı.

## 6. Olasılık senaryoları

| Senaryo | Sinyal | Karar |
|---------|--------|-------|
| En iyi durum | Hukuk ve lisans yolu net; resmi partner; sandbox kanıtı; bağımsız güvenlik testi | Dar ülke/pilot paketi hazırlanır |
| Temel durum | Kullanıcı değeri net fakat lisans, partner veya veri yerleşimi eksik | Foundation + sandbox sürer; public vaat yok |
| Kötü durum | Lisans belirsiz, veri izolasyonu zayıf, partner API'si kapanıyor veya kamu yetkisi yok | Canlı hat durur; yalnız araştırma kaydı korunur |

## 7. Ülke paketi

Tek küresel varsayım yerine her ülke için sürümlü bir politika paketi gerekir:

```text
country_pack = {
  existing_system_inventory,
  system_and_data_owners,
  legal_authority,
  allowed_services,
  allowed_and_forbidden_operations,
  adapter_contracts,
  approval_and_intervention_matrix,
  data_residency,
  identity_assurance,
  payment_and_banking_partners,
  public_sector_contract,
  language_and_accessibility,
  connectivity_and_offline_policy,
  incident_and_dispute_owner,
  effective_from,
  evidence_version
}
```

Paket kullanıcı tercihini ve Lumos önerisini sınırlar; genişletmez. Kullanıcı tercihi ülke hukukunu, kuruluş politikasını veya `SECURITY_NEVER_AUTO` sınırını aşamaz.

## 8. Uygulama sırası

1. İsim ve sorumluluk sınırlarını registry/ADR ile kilitle.
2. Dört alan için ayrı veri sınıflandırması ve threat model hazırla.
3. Sentetik sandbox sözleşmelerini birbirinden bağımsız tanımla.
4. Lumos Devlet için ilk ülkenin mevcut sistem envanteri ve salt-okuma uyumluluk adaptörünü tanımla.
5. İlk ülke için hukuk/lisans/partner kanıt paketini oluştur.
6. Yalnız sıfırlayan kapılar kapandıktan sonra kontrollü pilot kararı ver.
7. Canlı pilot sonrası skorları gerçek kanıtla güncelle; ülke çoğaltmasını ayrı karar yap.

## 9. Bu PR'ın sınırı

**Dahil:** kuruluş topolojisi, isim sınıfı, sorumluluk ayrımı, ülke paketi, kanıt skoru ve aşama kapıları.

**Dahil değil:** tüzel kişilik, ödeme/banka/PSP kodu, canlı connector, kamu sistemi bağlantısı, lisans başvurusu, production credential, web sitesi satış iddiası veya tarih/fiyat taahhüdü.
