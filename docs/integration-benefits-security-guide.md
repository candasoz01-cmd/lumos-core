# Lumos entegrasyonları: kolaylık ve güvenlik rehberi

**Durum:** Public foundation / yaşayan rehber
**Kapsam:** We Lock AI sitesinde anlatılan Lumos entegrasyon yaklaşımı ile açık kaynak `lumos-core` kayıtlarını aynı dilde tutmak.
**Önemli sınır:** Katalogda yer almak, canlı OAuth veya üretim bağlantısının hazır olduğu anlamına gelmez. Durum sütunu gerçeği açıkça gösterir.

## Lumos neyi kolaylaştırır?

Lumos'un hedefi kullanıcıyı her servis için tekrar tekrar menü, izin ve hesap ekranlarında dolaştırmak değildir. Cihaz, tarayıcı veya oturum tarafından gerçekten görülebilen bir bağlantı sinyali varsa Lumos bunu tek bir teklife çevirir: “Bu hesabınız veya cihazınız bulundu; birlikte kullanalım mı?” Kullanıcı kabul ettiğinde Lumos en düşük sürtünmeli resmî yolu seçer: önce mevcut hesap ve yerel bağlantı, sonra ücretsiz katman, son olarak canlı fiyatı doğrulanmış ücretli seçenek.

Lumos hiçbir zaman bölgeye bakıp hesap varmış gibi davranmaz. Bölge yalnızca LINE, KakaoTalk, NAVER WORKS, VK veya Yandex gibi yerel önemi yüksek seçenekleri **öneri** olarak öne çıkarır. “Tespit edildi” ifadesi yalnızca işletim sistemi, kurulu uygulama, tarayıcı uzantısı, OAuth oturumu, Bluetooth taraması veya yerel ağ keşfi gibi gerçek bir sinyal varsa kullanılır.

## Ortak güvenlik modeli

1. **Sinyal destekli keşif:** Hesap veya cihaz varlığı tahmin edilmez; kaynağı belli bir keşif sinyali gerekir.
2. **Teklif, yetki değildir:** “Birlikte kullanalım mı?” onayı bağlantı hazırlığını başlatır; sınırsız okuma/yazma yetkisi vermez.
3. **En az yetki:** Önce metadata, durum ve özet; tam içerik yalnızca gerekli ve izinli kapsamda.
4. **Yazma ayrı onay:** Mesaj gönderme, toplantı oluşturma, dosya paylaşma veya cihaz kontrolü işlem bazlı onay ister.
5. **Silme ve geri dönüşü zor işlemler:** Varsayılan kapalıdır; özel izin ve ek doğrulama gerekir.
6. **Ödeme ayrımı:** Entegrasyon onayı kart, satın alma veya abonelik yetkisi değildir. Fiyat canlı doğrulanır; Lumos otomatik satın alma yapmaz.
7. **Secret sınırı:** Token, parola, kart ve API anahtarı kullanıcı arayüzü veya public repoda tutulmaz; sunucu tarafı vault/credential katmanı gerekir.
8. **Resmî yol:** OAuth, resmî API, belgeli yerel protokol veya işletim sistemi köprüsü kullanılır; belgesiz tersine mühendislik varsayılan yol değildir.
9. **Bölgesel uyum:** Sağlayıcı izinleri, veri yerleşimi, kota ve ülke koşulları bağlantıdan önce değerlendirilir.
10. **Dürüst durum:** `foundation`, `limited`, `connection-check`, `catalog/planned` ve `local-discovery` birbirinden ayrılır; katalog kaydı “canlı bağlı” diye sunulmaz.

## 24 popüler uygulama ve cihaz bağlantısı

| Alan | Uygulama / cihaz | Lumos ile kazanılan kolaylık | Güvenlik yaklaşımı | Mevcut durum |
|---|---|---|---|---|
| Geliştirme | **GitHub** | Issue, PR ve CI durumunu tek görev bağlamında özetler; takip ve inceleme yükünü azaltır. | Yorum/label/assign onaylı; merge ve force-push yüksek risk kapısında; silme varsayılan kapalı. | Public foundation |
| Verimlilik | **Gmail** | Gelen kutusunu önceliklendirir, thread özetler ve yanıt taslağı hazırlar. | Okuma bile açık grant ister; Dar v1 göndermez/silmez; credential vault dışında görünmez. | Dar v1 limited |
| Verimlilik | **Google Calendar** | Uygun zaman, çakışma ve hazırlık ihtiyacını tek yerde gösterir. | Etkinlik oluşturma/taşıma onaylı; iptal ve katılımcı değişikliği ayrı onay. | Planned |
| Verimlilik | **Google Drive** | Dosya arama, metadata ve izinli özetleri görev bağlamına getirir. | Tam arşiv yok; paylaşma ve silme ayrı grant; kaynak dosya otorite olarak kalır. | Planned |
| İletişim | **Slack** | Konu, mention ve kararları özetleyip iş bağlamına dönüştürür. | Kanal kapsamı sınırlı; mesaj gönderme onaylı; silme varsayılan kapalı. | Planned |
| Toplantı | **Zoom** | Toplantı, gündem, katılımcı ve izinli kayıt özetini görevlerle birleştirir. | OAuth scope dar tutulur; kayıt ve transcript hassas veri sayılır; toplantı başlatma ayrı onay. | Catalog / planned |
| Mesajlaşma | **WhatsApp** | Müşteri konuşmalarını izinli iş bağlamında toplar ve yanıt hazırlığını hızlandırır. | Meta Cloud API kontrolü; gönderme onaylı; telefon/token UI'da tutulmaz; kişisel sohbetler varsayılan dışı. | Connection check |
| Mesajlaşma | **Telegram** | Bot ve kanal bildirimlerini görev/uyarı akışına bağlar. | Bot token sunucu tarafında; `getMe` ile salt okunur doğrulama; kullanıcı başlatmadan konuşma yok. | Connection check |
| Bölgesel | **LINE** | Japonya, Tayvan ve Tayland'daki resmî hesap konuşmalarını Lumos akışına taşır. | Webhook imzası, dar kanal tokenı ve kullanıcı rızası; broadcast ayrı izin ve kota kontrolü. | Catalog |
| Bölgesel | **KakaoTalk** | Güney Kore'deki servis içi iletişim ve kullanıcı onaylı mesaj akışlarını birleştirir. | Kakao Login consent ve servis içi sınırlar korunur; arkadaş mesajı ek izin ister. | Catalog |
| İletişim | **Microsoft Teams** | Mesaj, toplantı ve takvim bağlamını iş görevleriyle birleştirir. | Microsoft Graph scope'ları dar; tenant politikası ve yönetici onayı görünür; gönderme ayrı onay. | Catalog |
| Verimlilik | **Notion** | Sayfa ve veritabanı bağlamını görev özetine dönüştürür. | Yalnızca paylaşılan workspace/page kapsamı; sayfa değişikliği onaylı; silme kapalı. | Planned |
| Geliştirme | **Jira** | Issue, sprint ve proje durumlarını tek öncelik listesinde toplar. | Proje kapsamı grant ile sınırlı; durum değişimi ve issue oluşturma onaylı. | Catalog |
| Geliştirme | **Linear** | Issue ve proje bağlamını hızlı, sade görev akışına taşır. | Issue yazma ve durum değişimi ayrı onay; silme varsayılan kapalı. | Planned |
| Tarayıcı | **Google Chrome** | Açık sekme ve sayfa bağlamını kullanıcı seçimiyle Lumos görevine aktarır. | Cookie, parola ve local storage okunmaz; yalnızca görünür/seçilmiş sayfa; form gönderimi onaylı. | Catalog |
| Tarayıcı | **Apple Safari** | Apple cihazlarında seçilen web bağlamını Lumos ile paylaşır. | Safari extension scope'u ve site izni açıkça gösterilir; Keychain verisine doğrudan erişim yok. | Catalog |
| AI | **OpenAI** | Metin, görsel ve araç kullanımını Lumos görev/karar katmanında birleştirir. | API anahtarı sunucu tarafında; araç çağrıları politika kapısından geçer; hassas içerik minimize edilir. | Registered foundation |
| AI | **Google Gemini** | Google ekosistemiyle uyumlu çok modlu analiz seçeneği sunar. | Model yönlendirme ve veri kapsamı görünür; Workspace verisi ayrı OAuth izni ister. | Catalog |
| AI | **DeepSeek** | Bölgesel/model çeşitliliği ve alternatif akıl yürütme seçeneği sağlar. | Sağlayıcı ve veri bölgesi açıkça gösterilir; hassas görevler politikaya göre yerel/başka modele yönlendirilir. | Catalog |
| Cihaz | **Bluetooth Audio** | Kulaklık, hoparlör ve mikrofonu A2DP/HFP/AVRCP veya LE Audio yetenekleriyle tanır. | Yalnızca işletim sistemi köprüsü; sessiz eşleştirme yok; mikrofon kullanımı görünür izin ister. | Local discovery |
| Cihaz | **Matter** | Farklı marka akıllı ev cihazlarını ortak keşif ve durum modelinde gösterir. | Yerel fabric ve cihaz yetkisi korunur; kilit/kapı/ısı gibi etkili komutlar işlem onayı ister. | Catalog |
| Cihaz | **Home Assistant** | Yerel cihaz ve otomasyonları tek bağlamda toplar; bulut bağımlılığını azaltır. | Yerel API ve dar token; hangi entity'nin okunup kontrol edileceği ayrı kapsamlanır. | Catalog |
| Cihaz | **Samsung SmartThings** | Kore ve küresel SmartThings cihazlarını rutin ve durum akışına bağlar. | OAuth scope ve location/device sınırı; kilit, kamera ve alarm yüksek risk sınıfında. | Catalog |
| Cihaz | **Sonos** | Oda, hoparlör grubu ve oynatma durumunu Lumos medya görevleriyle birleştirir. | Hesap/ev kapsamı dar; ses başlatma ve grup değişimi kullanıcı politikasıyla; mikrofon içeriği alınmaz. | Catalog |

## En düşük maliyetli bağlantı kuralı

Lumos fiyatı tahmin etmez ve eski katalog fiyatını “en ucuz” diye sunmaz. Sıralama şöyledir:

1. Mevcut işletim sistemi veya yerel protokol bağlantısı.
2. Kullanıcının zaten sahip olduğu hesap/abonelik.
3. Sağlayıcının doğrulanmış ücretsiz katmanı.
4. Canlı toplam maliyeti ve veri koşulları doğrulanmış ücretli plan.
5. Yalnızca resmî partner yolu varsa, satın alma öncesi fiyat ve sözleşme özeti.

Her ödeme, abonelik veya satın alma işlemi ayrı işlem onayı ister. Entegrasyon onboarding onayı ödeme yetkisine dönüşmez.

## Kod ve durum kaynakları

- Küresel katalog: `src/integrations/providers/global_catalog_provider.py`
- Giriş sonrası teklif sözleşmesi: `src/integrations/providers/integration_onboarding_provider.py`
- WhatsApp / Telegram bağlantı kontrolü: `src/integrations/providers/communications_provider.py`
- Ortak registry: `src/integrations/registry.py`
- Site rehberi: `ui/src/pages/integrations/guide.astro`

Bu belge public repoya uygundur; gerçek token, credential, kart, production endpoint veya özel hesap bilgisi içermez.
