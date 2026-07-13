# ADR-015: Düzenlemeye Tabi Hizmet Kuruluşu Sınırları

| Alan | Değer |
|------|-------|
| Durum | **Accepted — foundation only** (2026-07-13) |
| Kapsam | Lumos Bank, Lumos Sepet, Lumos POS ve Lumos Devlet çalışma adlarının kuruluş sınırları |
| Uygulama | `implementation-pending`; kod, ödeme akışı, kamu bağlantısı veya production altyapısı yok |
| Üst sınır | `docs/lumos-karar-sozlesmesi.md`, OD-011, public/private repo sınırı |

## Bağlam

Finansal hizmet, ticaret, ödeme kabulü ve kamu hizmetleri aynı ürün modülü gibi işletilemez. Her alan farklı yetki, lisans, veri sınıfı, denetim ve olay müdahalesi gerektirir. Tek bir ortak runtime veya marka altında sınırların belirsiz kalması; kullanıcı varlıklarının, kamu verisinin ve ticari operasyonların yanlış yetkiyle kesişmesine yol açabilir.

Bu ADR kullanıcı tarafından onaylanan kuruluş yönünü kaydeder; mevcut ödeme kapsam kararını gevşetmez ve Lumos'un bugün banka, ödeme kuruluşu ya da devlet kurumu olduğu iddiasını oluşturmaz.

## Karar

### Ayrı sorumluluk alanları

| Çalışma adı | Hedef rol | Zorunlu sınır |
|-------------|-----------|----------------|
| **Lumos Bank** | Gelecekte ayrıca yetkilendirilecek/lisanslanacak finansal kuruluş hattı | Mevduat, kredi, para saklama veya transfer yetkisi lisans ve hukuk onayı olmadan yok |
| **Lumos Sepet** | Kullanıcı tercihleri, ürün/hizmet seçimi ve kontrollü ticaret orkestrasyonu | Banka defteri veya merchant settlement sahibi değildir; satın alma açık onaysız başlamaz |
| **Lumos POS** | İşletmeler için ödeme kabulü ve merchant operasyon hattı | Sepet ve Bank'tan ayrı merchant, settlement, iade ve mutabakat sınırı |
| **Lumos Devlet** | Mevcut kamu sistemlerine güvenli entegrasyon ve birlikte çalışabilirlik çerçevesi | Bir devlet, kamu otoritesi veya mevcut sistemlerin yerine geçen platform değildir; varsayılan müdahale yetkisi yoktur |

### Lumos Devlet entegrasyon ilkesi

Lumos Devlet için ilk hedef yeni iş kuralları, merkezi bir devlet sistemi veya genel müdahale hakkı üretmek değildir. İlk hedef, talep eden ülkenin **mevcut sistemlerini authoritative kaynak olarak koruyarak** güvenli entegrasyonun mümkün olup olmadığını göstermektir.

Varsayılan sıra şöyledir:

1. Mevcut sistem, veri sahibi, teknik sahip, yetkili kurum ve protokol envanteri çıkarılır.
2. Veri sınıfları ve sistemler arası güven sınırları kaydedilir.
3. Salt-okuma uyumluluk adaptörüyle kimlik, şema, provenance, gecikme ve hata davranışı doğrulanır.
4. Öneri/taslak akışı eklenir; Lumos değişikliği uygulatmaz, yetkili sisteme ve insana sunar.
5. Yazma veya sistem müdahalesi yalnız ülkenin açık talebi, hukuk/politika onayı, ayrı yetki matrisi ve geri dönüş planıyla dar kapsamlı açılır.

**Varsayılan yetki:** `deny`. Bir kamu sistemine bağlanabilmek o sistemde işlem yapma, karar verme veya müdahale etme hakkı oluşturmaz.

Her adaptör en az şu sözleşmeyi taşır: sistem sahibi, veri sahibi, amaç, izinli operasyonlar, yasak operasyonlar, kimlik doğrulama seviyesi, veri yerleşimi, audit/provenance, zaman aşımı, hata izolasyonu, geri dönüş ve acil durdurma sahibi.

### Ortak omurga, ayrı veri ve yetki alanları

Dört alan yalnızca aşağıdaki demo-safe sözleşmeleri paylaşabilir:

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

Bir alan diğerinin yetkisini miras almaz. Örneğin Sepet'te verilen alışveriş tercihi Bank'ta para transferi onayı değildir; POS merchant yetkisi kamu birimi erişimi değildir. Her dış etkili adım için amaç, kapsam, taraf, yaklaşık maliyet/etki ve geri dönüş durumu yeniden gösterilir.

### Public/private ayrımı

Public `lumos-core` yalnızca sözleşme, demo-safe şema, politika örneği ve doğrulama testi taşıyabilir. Lisans başvuruları, gerçek müşteri/kamu verisi, KYC/AML operasyonu, banka/PSP credential'ı, production endpoint'i, settlement ve devlet bağlantısı private ve yetkili operasyon katmanında kalır.

## Aşama kapıları

1. **Foundation:** isim, sorumluluk, veri ve yetki sınırları.
2. **Sandbox:** sentetik veri; gerçek para, gerçek merchant ve gerçek kamu verisi yok.
3. **Kontrollü pilot:** hukuk onayı, sözleşmeli partner, izole tenant, insan müdahalesi ve geri dönüş planı.
4. **Düzenlemeye tabi üretim:** ilgili ülke lisansı/yetkisi, bağımsız güvenlik denetimi, operasyon ekibi, olay müdahalesi ve mali/kamusal raporlama. Lumos Devlet için ülkeye özgü adaptör ve yetki matrisi zorunludur.
5. **Ülke genişlemesi:** her ülke için ayrı mevzuat, veri yerleşimi, dil, erişilebilirlik, sağlayıcı ve bağlantı paketi.

Bir kapı geçilmeden sonraki aşamanın adı UI'da `hazır`, `aktif`, `banka`, `resmi` veya `devlet hizmeti` gibi kesin ifadelerle sunulamaz.

## Sonuçlar

### Olumlu

- Finans, ticaret, merchant ve kamu sorumlulukları birbirinden ayrılır.
- Ülkeye göre farklı paket ve sağlayıcı seçimi çekirdeği bölmeden uygulanabilir.
- Ortak güven ilkeleri korunurken lisans ve veri sınırları bağımsız denetlenebilir.

### Maliyet ve kısıtlar

- Dört alan tek uygulama özelliğinden daha pahalı ve yavaş olgunlaşır.
- Her ülke için ayrı hukuk, güvenlik ve operasyon kanıtı gerekir.
- Ortak marka, ortak veri veya ortak onay anlamına gelmez; kullanıcıya bu ayrım sürekli görünür olmalıdır.

## Kapsam dışı

- Şirket/tüzel kişilik kurma, lisans veya marka tescili başlatma.
- PSP, banka, merchant veya kamu sistemi seçimi ve canlı entegrasyon.
- Gerçek ödeme, transfer, checkout, webhook, settlement veya kamu verisi işleme.
- Fiyatlandırma, ülke lansman tarihi ve başarı yüzdesi taahhüdü.
