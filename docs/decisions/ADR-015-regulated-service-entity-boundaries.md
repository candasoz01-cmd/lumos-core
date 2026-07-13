# ADR-015: Düzenlemeye Tabi Hizmet Kuruluşu Sınırları

| Alan | Değer |
|------|-------|
| Durum | **Accepted — foundation only** (2026-07-13) |
| Kapsam | Lumos Bank, Lumos Sepet, Lumos POS, Lumos Dünya ve Ülke Sistemleri Entegrasyon Katmanı sınırları |
| Uygulama | `implementation-pending`; kod, ödeme akışı, kamu bağlantısı veya production altyapısı yok |
| Üst sınır | `docs/lumos-karar-sozlesmesi.md`, OD-011, public/private repo sınırı |

## Bağlam

Finansal hizmet, ticaret, ödeme kabulü, küresel kullanıcı katılımı ve ülke sistemleri entegrasyonu aynı ürün modülü gibi işletilemez. Her alan farklı yetki, lisans, veri sınıfı, denetim ve olay müdahalesi gerektirir. Tek bir ortak runtime veya marka altında sınırların belirsiz kalması; kullanıcı varlıklarının, ülke verilerinin ve ticari operasyonların yanlış yetkiyle kesişmesine yol açabilir.

Bu ADR kullanıcı tarafından onaylanan kuruluş yönünü kaydeder; mevcut ödeme kapsam kararını gevşetmez. `candasoz01-cmd/Lumos` PR #102 ve #103 ile uygulanan karar uyarınca eski **Lumos Devlet** adı kaldırılmıştır; küresel yüzey **Lumos Dünya**, ülke sistemleri bağlantısı ise marka/kuruluş olmayan teknik entegrasyon katmanıdır.

### «Lumos Devlet» adı neden kaldırıldı?

- **Resmî otorite algısı:** Ad, Lumos'un bir devlet kurumu, egemen otorite veya kamu adına karar veren sistem olduğu izlenimini yaratabilir.
- **Müdahale/yetki algısı:** Entegrasyon kabiliyetini, mevcut sistemleri yönetme veya onlara sınırsız müdahale hakkı gibi gösterebilir.
- **Tek kalıp riski:** Ülkelerin hukuk, kurum, kültür, veri yerleşimi ve teknik altyapı farklarını tek bir merkezî model altında topluyormuş izlenimi verir.
- **İnsan odaklı yönle çelişki:** Lumos'un rolü yönetmek değil; hizmeti, riski, seçeneği ve kullanıcı kararını görünür kılmaktır.
- **Kuruluş sınırı karışıklığı:** Lumos Dünya'nın küresel insan katılımı rolü ile private/sözleşmeli ülke sistemi entegrasyonu birbirine karışır.

Bu nedenle ad yalnız pazarlama yüzeyinden değil, kuruluş modeli ve teknik yetki tanımından da çıkarılmıştır. Kaldırma, ülke sistemleriyle çalışmaktan vazgeçmek değildir; bağlantıyı daha doğru sınıra taşımaktır.

## Karar

### Ayrı sorumluluk alanları

| Çalışma adı | Hedef rol | Zorunlu sınır |
|-------------|-----------|----------------|
| **Lumos Bank** | Gelecekte ayrıca yetkilendirilecek/lisanslanacak finansal kuruluş hattı | Mevduat, kredi, para saklama veya transfer yetkisi lisans ve hukuk onayı olmadan yok |
| **Lumos Sepet** | Kullanıcı tercihleri, ürün/hizmet seçimi ve kontrollü ticaret orkestrasyonu | Banka defteri veya merchant settlement sahibi değildir; satın alma açık onaysız başlamaz |
| **Lumos POS** | İşletmeler için ödeme kabulü ve merchant operasyon hattı | Sepet ve Bank'tan ayrı merchant, settlement, iade ve mutabakat sınırı |
| **Lumos Dünya** | İnsan odaklı küresel tanışma ve katılım yüzeyi; ticari birimlerden ayrı | Devlet, kamu otoritesi veya ülke sistemleri yönetim yüzeyi değildir |
| **Ülke Sistemleri Entegrasyon Katmanı** | Talep eden ülkenin mevcut sistemlerine güvenli adaptör ve birlikte çalışabilirlik sözleşmesi | Public marka/kuruluş değildir; mevcut sistemlerin yerine geçmez ve varsayılan müdahale yetkisi yoktur |

### Ülke sistemleri entegrasyon ilkesi

Entegrasyon katmanının ilk hedefi yeni iş kuralları, merkezi bir devlet sistemi veya genel müdahale hakkı üretmek değildir. İlk hedef, talep eden ülkenin **mevcut sistemlerini authoritative kaynak olarak koruyarak** güvenli entegrasyonun mümkün olup olmadığını göstermektir.

#### İlk kullanım maksadı ve olası hizmetler

İlk kullanım maksadı; devlet ölçeğinde hâlihazırda kullanılan sistemler arasında güvenli bağlantı, uyumluluk ve hizmet sürekliliği sağlamaktır. Olası hizmetler:

| Hizmet alanı | İlk güvenli kapsam |
|--------------|--------------------|
| Sistem ve servis envanteri | Kurum, sistem sahibi, protokol, veri sınıfı ve bağımlılık haritası |
| Birlikte çalışabilirlik | Mevcut API, standart ve kurumca onaylı adaptörler arasında şema/protokol uyumu |
| Kimlik ve yetki federasyonu | Mevcut kimlik kaynağını değiştirmeden oturum ve operasyon bazlı yetki doğrulama |
| Güvenli veri alışverişi | Minimum gerekli veri, amaç sınırı, provenance, correlation ve veri yerleşimi kontrolü |
| Hizmet yönlendirme | Kullanıcıyı doğru mevcut servise yönlendirme; form/talep taslağı hazırlama, kararı yetkili sisteme bırakma |
| Risk ve olay görünürlüğü | Kesinti, yetki sapması, veri akışı ve güven sinyallerini yetkili ekiplere görünür kılma |
| Audit ve kanıt | İçerik kopyalamadan işlem özeti, onay, kaynak ve sonuç kanıtı üretme |
| Dil ve erişilebilirlik | Mevcut hizmetleri farklı dil, cihaz ve erişilebilirlik ihtiyaçlarında anlaşılır sunma |
| Bağlantı dayanıklılığı | Düşük bant, kesinti ve offline koşullarında güvenli kuyruk, tekrar deneme ve kaynak sistem sürekliliği |

Bu liste ürün vaadi veya otomatik yetki değildir. Hangi hizmetin açılacağı, talep eden ülkenin ihtiyacı, mevcut sistemleri, sözleşmesi ve `country_pack` kanıtlarıyla belirlenir.

Varsayılan sıra şöyledir:

1. Mevcut sistem, veri sahibi, teknik sahip, yetkili kurum ve protokol envanteri çıkarılır.
2. Veri sınıfları ve sistemler arası güven sınırları kaydedilir.
3. Salt-okuma uyumluluk adaptörüyle kimlik, şema, provenance, gecikme ve hata davranışı doğrulanır.
4. Öneri/taslak akışı eklenir; Lumos değişikliği uygulatmaz, yetkili sisteme ve insana sunar.
5. Yazma veya sistem müdahalesi yalnız ülkenin açık talebi, hukuk/politika onayı, ayrı yetki matrisi ve geri dönüş planıyla dar kapsamlı açılır.

**Varsayılan yetki:** `deny`. Bir kamu sistemine bağlanabilmek o sistemde işlem yapma, karar verme veya müdahale etme hakkı oluşturmaz.

Her adaptör en az şu sözleşmeyi taşır: sistem sahibi, veri sahibi, amaç, izinli operasyonlar, yasak operasyonlar, kimlik doğrulama seviyesi, veri yerleşimi, audit/provenance, zaman aşımı, hata izolasyonu, geri dönüş ve acil durdurma sahibi.

### Ortak omurga, ayrı veri ve yetki alanları

Bu yapılar yalnızca aşağıdaki demo-safe sözleşmeleri paylaşabilir:

- kimlik ve amaç bazlı yetki sözleşmesi,
- açık onay ve risk görünürlüğü,
- politika değerlendirme arayüzü,
- audit olay şeması ve provenance,
- ülke/bölge politika paketi seçimi,
- erişilebilirlik, yerelleştirme ve bağlantı dayanıklılığı.

Aşağıdakiler ortak depoda veya ortak tenant'ta birleştirilemez:

- banka defteri, müşteri varlığı ve finansal credential,
- POS merchant anahtarları, settlement ve iade kayıtları,
- Sepet sipariş/ödeme niyeti ile finansal işlem gerçeği,
- kamu kimlikleri, sınıflandırılmış veri, kurum içi politika ve sistem müdahale yetkileri,
- üretim secret'ları, banka/PSP endpoint'leri ve gerçek kamu bağlantıları.

### Yetki kesişimi

Bir alan diğerinin yetkisini miras almaz. Örneğin Sepet'te verilen alışveriş tercihi Bank'ta para transferi onayı değildir; POS merchant yetkisi ülke sistemleri entegrasyon yetkisi değildir. Her dış etkili adım için amaç, kapsam, taraf, yaklaşık maliyet/etki ve geri dönüş durumu yeniden gösterilir.

### Public/private ayrımı

Public `lumos-core` yalnızca sözleşme, demo-safe şema, politika örneği ve doğrulama testi taşıyabilir. Lisans başvuruları, gerçek müşteri/kamu verisi, KYC/AML operasyonu, banka/PSP credential'ı, production endpoint'i, settlement ve devlet bağlantısı private ve yetkili operasyon katmanında kalır.

## Aşama kapıları

1. **Foundation:** isim, sorumluluk, veri ve yetki sınırları.
2. **Sandbox:** sentetik veri; gerçek para, gerçek merchant ve gerçek kamu verisi yok.
3. **Kontrollü pilot:** hukuk onayı, sözleşmeli partner, izole tenant, insan müdahalesi ve geri dönüş planı.
4. **Düzenlemeye tabi üretim:** ilgili ülke lisansı/yetkisi, bağımsız güvenlik denetimi, operasyon ekibi, olay müdahalesi ve mali/kamusal raporlama. Ülke sistemleri entegrasyonu için ülkeye özgü adaptör ve yetki matrisi zorunludur.
5. **Ülke genişlemesi:** her ülke için ayrı mevzuat, veri yerleşimi, dil, erişilebilirlik, sağlayıcı ve bağlantı paketi.

Bir kapı geçilmeden sonraki aşamanın adı UI'da `hazır`, `aktif`, `banka`, `resmi` veya `devlet hizmeti` gibi kesin ifadelerle sunulamaz.

## Sonuçlar

### Olumlu

- Finans, ticaret, merchant ve kamu sorumlulukları birbirinden ayrılır.
- Ülkeye göre farklı paket ve sağlayıcı seçimi çekirdeği bölmeden uygulanabilir.
- Ortak güven ilkeleri korunurken lisans ve veri sınırları bağımsız denetlenebilir.

### Maliyet ve kısıtlar

- Üç ticari birim, Lumos Dünya ve ülke entegrasyon katmanı tek uygulama özelliğinden daha pahalı ve yavaş olgunlaşır.
- Her ülke için ayrı hukuk, güvenlik ve operasyon kanıtı gerekir.
- Ortak marka, ortak veri veya ortak onay anlamına gelmez; kullanıcıya bu ayrım sürekli görünür olmalıdır.

## Kapsam dışı

- Şirket/tüzel kişilik kurma, lisans veya marka tescili başlatma.
- PSP, banka, merchant veya kamu sistemi seçimi ve canlı entegrasyon.
- Gerçek ödeme, transfer, checkout, webhook, settlement veya kamu verisi işleme.
- Fiyatlandırma, ülke lansman tarihi ve başarı yüzdesi taahhüdü.
