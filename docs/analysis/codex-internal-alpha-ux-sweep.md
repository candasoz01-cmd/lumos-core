# Lumos Internal Alpha UX taraması

**Tarih:** 22 Haziran 2026

**İncelenen taban:** `origin/main` — `c45f6b8`

**Yöntem:** Panel kaynakları, TR/EN katalogları ve yerel üretim önizlemesi masaüstünde yeni kullanıcı gözüyle incelendi. Bridge, approval, LAN relay, tool-loop ve OS automation akışları çalıştırılmadı veya değiştirilmedi.

## Özet

Panelin ana gezinmesi çalışıyor ve önizleme modülleri menüde etiketleniyor. Alpha kalitesini en çok düşüren üç ortak sorun şunlar:

1. Medya, Sosyal ve Posta ekranlarında kullanıcıya ham `panel.common.demo.idleHint` anahtarı görünüyordu.
2. Yetenekler ve Ayarlar ekranları mevcut durum ile gelecek niyeti aynı yüzeyde gösteriyor; kullanılamayan işlevler aktif ayar izlenimi veriyordu.
3. Kuantum ekranı son kullanıcı paneline göre çok yoğun; `mock`, `heuristic`, `fallback`, `docs_only` ve `local_scan` gibi iç terimler içeriyor.

Bu turda yalnızca metin ve i18n yaşam döngüsü düzeltildi. CSS, bilgi mimarisi, çalışma davranışı ve korunan bağlantı hatları değiştirilmedi.

## Ekran bazında bulgular

| Ekran | Bulgu | Etki | Bu turdaki durum |
|---|---|---:|---|
| Sohbet | Ana akış anlaşılır. Ek menüde kamera, dosya ve ses seçeneklerinin izin/uygunluk durumu eylemden önce yeterince görünür değil. | Orta | Yalnızca raporlandı. |
| Görevler | “Kanıt sunucusu” ifadesi kullanıcıyı altyapı ayrıntısına yönlendiriyordu. Yerel kayıt ile doğrulanan geçmiş ayrımı anlaşılabilir ama metin yoğun. | Orta | Hata metni kullanıcı diline çevrildi. Yoğunluk raporlandı. |
| Ses | Beş kartlık açıklama niyet ve hedef diliyle yazılmıştı; çalışan ürün durumu anlaşılmıyordu. | Orta | Metinler kısa, doğrudan ve izin durumuna bağlı hale getirildi. |
| Medya | Ham i18n anahtarı görünüyordu. Salt okunur çıktı ile gönderim demosu aynı ekranda iki ayrı ana iş gibi duruyor. | Yüksek | Ham anahtar düzeltildi; ekran yoğunluğu raporlandı. |
| Sosyal | Gönderim bağlı değilken form gerçek paylaşım yüzeyi izlenimi veriyor; ham i18n anahtarı görünüyordu. | Yüksek | Ham anahtar düzeltildi; formun geleceği ürün kararı olarak bırakıldı. |
| Posta | Sosyal ekranıyla aynı aktiflik belirsizliği ve ham anahtar sorunu var. | Yüksek | Ham anahtar düzeltildi; form yapısı değiştirilmedi. |
| Dosyalar | “Lumos köprüsü”, “faz” ve biçim ayrıntıları ilk kullanım metnini teknikleştiriyordu. “Yükle ve analiz et” desteklenmeyen biçimlerde fazla geniş vaat ediyor. | Orta | Giriş metni temizlendi; düğme kapsamı raporlandı. |
| Kuantum | Son kullanıcı için fazla yoğun. İngilizce iç terimler ve örnek/veri kaynağı ayrıntıları ana yüzeyde. Küçük tablo yoğunluğu mobilde zor okunuyor. | Yüksek | Görünen `mock`, `Entropy Lab`, `heuristic`, `fallback` ve gelecek-vaadi metinleri temizlendi. Bilgi mimarisi raporlandı. |
| Yetenekler | “Aktif” tanımı sınırlı çalışma ile kanıtı birleştiriyordu. “Mac”, “deploy” ve “bridge” ürün diliyle uyumsuzdu. Bazı durumlar çalışma zamanı verisine bağlı olduğu için yalnız metinle kesinleştirilemez. | Yüksek | Durum sözlüğü ve görünen adlar temizlendi. Durum kaynağına dokunulmadı. |
| Ayarlar | Tema, bildirim, bağlantı, paylaşım ve veri saklama açıklamaları ayarlar kullanılabilir izlenimi veriyordu; gerçekte yalnız kullanıcı modu değiştirilebiliyor. | Yüksek | Metin mevcut kullanılabilirliği açıkça söylüyor. Kart yapısı raporlandı. |

## Ortak UX sorunları

### Ürün dili

Panel metinlerinde “hedefler”, “amaçlar”, “benimser”, “sağlayabilir” ve “ileride” kalıpları mevcut durumu belirsizleştiriyor. Bu turda kapsam içindeki ekranlarda şu durum dili kullanıldı:

- **çalışır / kullanılabilir:** doğrulanmış eylem,
- **kapalı / bağlı değil:** mevcut bağlantı yok,
- **onay bekler:** kullanıcı kararı olmadan ilerlemeyen eylem,
- **önizleme:** bilgi veya demo yüzeyi; gerçek işlem yapmaz.

Kapsam dışındaki Kimlik, Güvenlik, Dünya ve diğer tanıtım kartlarında aynı gelecek-niyeti dili sürüyor. Bu turda değiştirilmedi.

### Ham i18n anahtarı

Medya, Sosyal ve Posta paylaşım önizlemeleri katalog hazır olmadan bir kez çevriliyor, ham değer sabit olarak saklanıyordu. Dil değişiminde de aynı sabit tekrar kullanılıyordu. Metin artık gösterildiği anda mevcut katalogdan çözülüyor. TR ve EN kataloglarında bu turda yeni anahtar eklenmedi; duplicate-key yüzeyi oluşmadı.

### Okunabilirlik

- Mobil başlık durum rozetleri yaklaşık `0.4rem`, mobil menü etiketleri `0.56rem`, bazı form etiketleri `0.62rem`; erişilebilir bir alpha için küçük.
- Mobil menü çok sayıda yatay öğeyi kaydırmalı şeritte topluyor; “daha fazla ekran var” işareti zayıf.
- Taslak metin alanları yaklaşık `0.94rem` ve yeterli yükseklikte; mevcut ana sorun alanın boyutu değil, çevresindeki açıklama ve kart yoğunluğu.
- Kuantum tabloları ile durum rozetleri mobilde bilgi yoğunluğunu daha da artırıyor.

## Cihaz merkezli panel yönü — kodsuz taslak

Panelin ana nesnesi modül değil cihaz olabilir:

1. **Bu cihaz:** Lumos’un şu anda hangi cihaz üzerinde çalıştığını ve bağlantı durumunu gösterir.
2. **Lumos PC / Lumos Mobile:** cihazlar aynı listede, açık ad ve son görülme bilgisiyle yer alır.
3. **Onay bekleyen işlemler:** cihazlar arası ortak kuyruk; işlem, hedef cihaz, istenen izin ve süre görünür.
4. **Cihaz durumu:** `Bağlı`, `Çevrimdışı`, `Kurulum gerekli`, `Onay bekliyor` gibi kullanıcı diliyle sınırlı durum kümesi.
5. **Kullanıcı kontrolü:** her cihaz için izinleri görme, bağlantıyı kesme ve geçmiş işlemi inceleme yüzeyi.

Önerilen sayfa sırası: **Bu cihaz → Onay bekleyenler → Kullanılabilir işlemler → Son etkinlik → Diğer cihazlar**. Bu, “bridge sağlıklı mı?” sorusunu “Lumos bu cihazda hazır mı?” sorusuna dönüştürür. Uygulama öncesinde cihaz kimliği, durum kaynağı ve onay sözleşmesi ayrıca doğrulanmalıdır.

## Sıcak açık tema — uygulanabilir tasarım notu

- **Renk dili:** arka plan `#F7F3EA`, yüzey `#FFFDF8`, ana metin `#252A2E`, ikincil metin `#626A70`, sınır `#DED7CA`; ana vurgu için koyu turkuaz `#2F6F6A`, uyarı için amber `#B8792E`, hata için `#B64B4B` başlangıç değerleri olabilir. Kontrast doğrulaması zorunludur.
- **Font ve boşluk:** gövde en az 16 px, yardımcı metin en az 13–14 px; 8 px tabanlı boşluk düzeni. `0.4rem–0.62rem` aralığındaki kullanıcı metinleri kaldırılmalı.
- **Kart yoğunluğu:** tek ekranda birincil kart + en fazla 2–3 ikincil kart. Açıklama kartları açılır “Nasıl çalışır?” alanına taşınabilir.
- **Menü:** ilk seviye 4–5 ana hedef; önizleme ve uzman ekranları “Daha fazla” altında gruplanabilir. Aktiflik rozeti menü adının yerine geçmemeli.
- **Mobil:** alt gezinmede en sık kullanılan 4 hedef + “Diğer”; yatay kayan uzun menüden kaçınılmalı. Durum ve onay sayısı üstte sabit, form eylemleri başparmak erişiminde olmalı.

Bu değerler uygulama değil, tema token’ı ve yoğunluk deneyi için başlangıç taslağıdır.

## Güven ve gizlilik mikro metinleri — TR/EN taslak

Bu metinler panel yerleşimi için taslaktır; yayımlanmadan önce gerçek izin ve veri sözleşmesiyle doğrulanmalıdır.

| Konu | Türkçe | English |
|---|---|---|
| Lumos ne yapabilir? | **Lumos bu cihazda ne yapabilir?** Seçtiğiniz dosyaları okuyabilir, yerel görevleri tutabilir ve kullanılabilir cihaz işlemlerini gösterebilir. | **What can Lumos do on this device?** It can read files you choose, keep local tasks, and show available device actions. |
| Ne yapamaz? | **Lumos ne yapamaz?** Kapalı veya bağlı olmayan özellikleri çalıştıramaz. Kalıcı işlemleri sizden gizleyerek tamamlamaz. | **What can’t Lumos do?** It cannot run features that are off or disconnected. It does not complete permanent actions without showing you. |
| Hangi işlem onay ister? | **Onay gereken işlemler** Dışarı gönderme, paylaşma, silme ve cihazda değişiklik yapma gibi işlemler uygulanmadan önce onayınızı bekler. | **Actions that require approval** Sending, sharing, deleting, and device changes wait for your approval before they run. |
| Veriye yaklaşım | **Veriniz nasıl ele alınır?** İşlem mümkünse bu cihazda kalır. Dış servis gerektiğinde hedef ve gönderilecek içerik önce gösterilir. | **How is your data handled?** Work stays on this device when possible. When an external service is needed, the destination and content are shown first. |

## Uygulanan küçük düzeltmeler

- Medya, Sosyal ve Posta ekranlarındaki ham i18n anahtarı giderildi.
- Görev hata metninden “kanıt sunucusu” kaldırıldı.
- Ses ve Medya açıklamaları kısa, doğrudan durum diline çevrildi.
- Dosyalar girişinden bridge/faz dili kaldırıldı.
- Kuantum ekranındaki seçili iç terimler kullanıcı diline çevrildi.
- Yetenekler durum sözlüğü `Aktif / Kapalı / Önizleme` olarak netleştirildi; “Mac”, “deploy” ve görünen bridge ifadeleri temizlendi.
- Ayarlar metni yalnızca kullanıcı modunun değiştirilebildiğini açıkça belirtiyor.

## Yalnızca raporlanan, uygulanmayan konular

- Mobil tipografi, menü mimarisi ve kart yoğunluğu.
- Önizleme modüllerinin gizlenmesi, salt bilgi ekranına dönüşmesi veya tutulması.
- Kuantum ekranının ana paneldeki yeri ve uzman görünümü.
- Yetenek durumlarının çalışma zamanı kaynakları ve `Kısıtlı` durumunun ürün sözleşmesi.
- Dosya düğmesinin desteklenen biçimlere göre daha dar adlandırılması.
- Sohbet ek menüsünde izin ve uygunluk bilgisinin eylem öncesinde gösterilmesi.
- Sıcak açık tema uygulaması.

## Korunan kapsam

PR-RB-05, PR-RB-06 ve PR-RB-07 bağlantı hattı; pending approval; LAN relay; OpenAI tool-loop adapter ve OS automation dosyaları değiştirilmedi. Bu tur gerçek paylaşım, posta, sosyal gönderim, terminal veya cihaz otomasyonu başlatmadı.

## Kalan büyük ürün kararları

1. Ana panel modül merkezli mi, cihaz merkezli mi olacak?
2. Önizleme modülleri menüde kalacak mı, “Daha fazla” altında mı toplanacak, yoksa alpha’dan gizlenecek mi?
3. `Aktif`, `Kısıtlı`, `Kapalı` ve `Onay bekliyor` durumlarının tek doğruluk kaynağı ne olacak?
4. Kuantum son kullanıcı özelliği mi, uzman tanılama ekranı mı?
5. Güven mikro metinlerindeki yerel işlem ve onay ifadeleri hangi çalışma zamanı garantilerine bağlanacak?

## Sabah için önerilen ilk 5 karar

1. **Cihaz modeli:** `Bu cihaz`, `Lumos PC` ve `Lumos Mobile` kimliklerinin kapsamı.
2. **Önizleme politikası:** bağlı olmayan modülün gizlenmesi, bilgi ekranı olarak kalması veya demo sunması.
3. **Durum sözleşmesi:** Yetenekler ve cihaz durumunda kullanılacak ortak durumlar ve veri kaynağı.
4. **Kuantum konumu:** ana gezinme, uzman görünümü veya ayrı deneysel alan.
5. **Mobil taban çizgisi:** minimum yazı boyutu, ana menü öğesi sayısı ve kart yoğunluğu.

## Doğrulama kaydı

- `pytest -q tests/test_panel_i18n_v1.py tests/test_panel_module_nav_inactive_badge.py tests/test_panel_visual_polish.py`: **125 geçti**.
- `npm run build --prefix ui`: **geçti**.
- `npm run e2e:smoke --prefix ui`: **geçti** (`SMOKE_UI_RESULT: PASS`).
- Yerel üretim önizlemesinde Medya, Sosyal, Posta ve Kuantum ekranları TR/EN dolaşıldı: ham anahtar ve temizlenen eski terimler görünmedi.
- `ruff check .`: **geçti**.
- Tam `pytest` koleksiyonu: **1205 geçti, 3 atlandı**.
- GitHub CI sonucu PR açıldıktan sonra ayrıca izlenecektir.
