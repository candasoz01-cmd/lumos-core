# ADR-002: Mail / Inbox Intelligence (Taslak)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / gözlem** — uygulanmamış; kesinleşmiş mimari karar değildir |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, onay ve yetki ilkeleri, ADR-001 |

## Amaç

Lumos, kullanıcının **açık izni** ile e-posta okuyabilir ve gelen kutusunu **önem önceliğine** göre sunabilir. Bu ADR, böyle bir yetenek alanının ürün ve güvenlik sınırlarını **taslak** düzeyinde kayıt altına alır.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, API, panel arayüzü, OAuth, IMAP, Gmail veya gerçek posta entegrasyonu **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). Mail okuma ve önerilen eylemler, bu sözleşmeyle uyumlu olmalıdır: onaysız okuma yok; onaysız dış etki yok.

Mail / Inbox Intelligence, ileride değerlendirilebilecek bir **ürün yönü taslağıdır**. Buradaki ifadeler **hipotez ve gözlem** düzeyindedir; finalize edilmiş veya uygulanmış bir özellik olarak sunulmamalıdır.

## Onay ve güvenlik sınırları (zorunlu)

Aşağıdaki kurallar, olası gelecek uygulama için **değiştirilemez ön koşullardır**; Lumos karar sözleşmesi ve onay ilkeleriyle hizalıdır.

| Eylem | Kural |
|-------|-------|
| Posta okuma | **Açık kullanıcı izni olmadan yapılmaz** |
| Gönderme | **Kullanıcı onayı olmadan yapılmaz** |
| Silme | **Kullanıcı onayı olmadan yapılmaz** |
| Arşivleme | **Kullanıcı onayı olmadan yapılmaz** |
| Etiketleme | **Kullanıcı onayı olmadan yapılmaz** |
| Harici / dış etkili aksiyonlar | **Kullanıcı onayı olmadan yapılmaz** |

Ek ilkeler:

- Lumos, kullanıcı adına **sessiz veya otomatik** posta işlemi yapmaz.
- Öneri ve taslak üretimi (ör. cevap taslağı) **simülasyon / önizleme** düzeyinde kalabilir; gerçek gönderim veya kutuda değişiklik yalnızca onay sonrası.
- Kalıcı silme ve geri dönüşsüz işlemler, mevcut çekirdek kurallarına uygun şekilde **açık komut + uyarı** gerektirir.
- Bu ADR, mail erişimi için ayrı bir izin akışının **önce** tanımlanmasını şart koşar (aşağıda).

## Önem kategorileri (taslak)

Gelen postalar, öncelik sunumu için aşağıdaki kategorilere ayrılabilir (*henüz algoritma veya model kararı yok*):

| Kategori | Kısa tanım |
|----------|------------|
| **acil** | Hızlı dikkat veya yanıt gerektiren ileti |
| **finans / fatura / ödeme** | Ödeme, fatura, banka veya mali içerik |
| **hesap güvenliği** | Şifre sıfırlama, 2FA, güvenlik uyarıları |
| **iş / proje** | İş, proje veya görevle ilişkili ileti |
| **kişisel** | Kişisel ve sosyal nitelikli ileti |
| **düşük öncelik / bildirim** | Bilgilendirme; acil aksiyon gerektirmeyen |
| **reklam / gereksiz** | Tanıtım, toplu veya düşük değerli içerik |

Kategori ataması **öneri** niteliğindedir; kullanıcı her zaman override edebilmelidir (gelecek tasarım hedefi).

## Mail kartı alanları (taslak)

Önem önceliğine göre sunulan her posta kartında hedeflenen alanlar:

| Alan | Açıklama |
|------|----------|
| **gönderen** | Gönderen adı veya adresi |
| **konu** | E-posta konusu |
| **kısa özet** | İçeriğin kısa, tarafsız özeti |
| **önem seviyesi** | Yukarıdaki kategorilerden biri |
| **neden önemli / düşük** | Sınıflandırma gerekçesinin kısa açıklaması |
| **önerilen aksiyon** | Lumos’un önerdiği sonraki adım (onay gerektirir) |
| **kaynak zaman** | Postanın alındığı / kaynak sistemdeki zaman |

Bu alanlar **ürün tasarım hedefidir**; şu an kod veya API ile temsil edilmemektedir.

## Önerilen aksiyonlar (taslak)

Aşağıdaki aksiyonlar Lumos tarafından **önerilebilir**; kutuda veya dış sistemde **değişiklik yapan** tüm adımlar kullanıcı onayı gerektirir:

| Önerilen aksiyon | Not |
|------------------|-----|
| **cevap taslağı hazırla** | Taslak üretimi; gönderim onay gerektirir |
| **sonra hatırlat** | Zamanlı hatırlatma önerisi; uygulama onay gerektirir |
| **takvime ekle** | Etkinlik / deadline önerisi; ekleme onay gerektirir |
| **düşük öncelik olarak işaretle** | Öncelik değişikliği önerisi; uygulama onay gerektirir |
| **kullanıcı onayıyla arşivle** | Arşivleme yalnızca açık onay sonrası |

Lumos, bu aksiyonları **otomatik uygulamaz**; yalnızca sunar veya onay bekler.

## Gelecek: ayrı mail erişim izin akışı

Herhangi bir uygulama (okuma, sınıflandırma, öneri) başlamadan **önce** tanımlanması gereken ayrı bir izin akışı:

1. Kullanıcıya mail erişiminin kapsamı açıkça anlatılır (ne okunur, ne okunmaz, ne saklanır).
2. Kullanıcı **bilinçli ve açık** onay verir; varsayılan kapalı kalır.
3. İzin geri alınabilir olmalıdır.
4. OAuth, IMAP, Gmail veya benzeri sağlayıcı entegrasyonu **bu ADR turunda yoktur**; izin akışı tasarımı ayrı belgede ele alınacaktır.

Bu akış onaylanmadan ve dokümante edilmeden **kod veya entegrasyon çalışması başlatılmamalıdır**.

## Bilinçli sınırlar

| Konu | Durum |
|------|-------|
| Kod / API / panel UI | **Bu turda yok** — yalnızca ADR |
| OAuth / IMAP / Gmail / gerçek posta | **Kapsam dışı** |
| Otomatik gönder / sil / arşiv / etiket | **Yasak** (onaysız) |
| Jilee | **Lumos özelliği değildir**; ayrı fikir, gözlemde |
| Üretim vaadi | **Yok** — taslak / gelecek / gözlem |

Abartılı ürün vaadi yapılmaz. Bu belge, olası bir yönü kayıt altına alır; teslim tarihi veya tam kapsam taahhüdü içermez.

## Sonuç (geçici)

Mail / Inbox Intelligence, Lumos’un **izinli okuma + önem önceliği sunumu** hedefini tanımlayan **taslak ADR**dir. Uygulanmamıştır. Somut adımlar: (1) mail erişim izin akışının ayrı tasarımı, (2) onay sınırlarının korunması, (3) ayrı checkpoint veya revizyon ile kapsam netleştirme.

## Sonraki gözden geçirme

- Mail erişim izin akışı için ayrı ADR veya checkpoint belgesi
- Önem sınıflandırma kuralları ve kullanıcı override modeli
- Public repo sınırına uygun demo / stub kapsamı netleşince revizyon
- ADR-001 ile çakışmayan, çekirdek stabilizasyon sonrası uygulama değerlendirmesi
