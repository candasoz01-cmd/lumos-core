# Lumos ürün pusulası
## Lumos'un amacı
Lumos, kullanıcı adına kontrolsüz işlem yapan bir ajan değil; kullanıcının niyetini düzenleyen, sınırlarını açıkça gösteren ve güvenli karar katmanı oluşturan kişisel bir AI paneli olarak tasarlanır.
Amaç, kullanıcıya yardım etmek ve yönlendirmek; kontrolü kullanıcıdan almak değildir.
---
## Şu anki erken faz
Bu aşama Faz A olarak ele alınır.
Odak noktası:
- Görev kaydetme
- Görevleri listeleme
- Düşük riskli görevlerde kısa plan çıkarma
- İşlem yapmadan önce durumu açık göstermek
- Kod, köprü veya terminal çalıştırmadan bilgi vermek
- Yerel liste görünürlüğünü ve panel davranışını sadeleştirmek
Bu fazda Lumos gerçek sistem yetkisi kullanan bir ajan gibi davranmaz.
---
## Ne yapar
Lumos şu erken fazda şunları yapabilir:
- Görev kaydedebilir.
- Görevleri listeleyebilir.
- Görevleri durumlarına göre görünür biçimde filtreleyebilir.
- Düşük riskli görevlerde kısa plan önerebilir.
- Kullanıcıya hangi işlemin yapılmadığını açıkça söyleyebilir.
- Dosya adı, türü, boyutu ve uzantısı gibi temel bilgileri gösterebilir.
- Güvenli okuma/yazma akışları için hazırlık zemini oluşturabilir.
---
## Ne yapmaz
Lumos şu aşamada şunları yapmaz:
- Kullanıcı onayı olmadan kalıcı işlem yapmaz.
- Kendi kendine terminal veya cihaz komutu çalıştırmaz.
- Kod değiştirmez.
- Köprü yürütmesini otomatik başlatmaz.
- Mail, takvim veya kişilere erişmez.
- PDF/DOCX gibi dosyalarda derin analiz yaptığını iddia etmez.
- EXE veya kurulum dosyası çalıştırmaz.
- Kullanıcıya yapmadığı bir işlemi yapmış gibi göstermez.
---
## Kullanıcı onayı ilkesi
Kalıcı, riskli veya dış sisteme etki eden işlemler kullanıcı onayı olmadan yapılmaz.
Lumos'un görevi kullanıcıyı hızlandırmak ve yönlendirmektir. Karar, sorumluluk ve son onay kullanıcıda kalır.
Onay yalnızca görsel bir formalite değildir; sistem davranışında gerçek sınır olarak ele alınmalıdır.
---
## Cihaz bağımsız yaklaşım
Lumos yalnızca Mac veya PC için düşünülmez.
Ürün dili cihaz bağımsız olmalıdır:
- mobil
- masaüstü
- yerel cihaz
- uzak panel
- ileride mini Lumos server
Bu yüzden arayüzde platforma özel ifadeler yerine genel cihaz dili tercih edilir.
---
## Mini Lumos server uzun vadeli notu
İleride kullanıcının kendi ortamında çalışan küçük bir Lumos sunucusu düşünülebilir.
Bu mini server:
- görev senkronu,
- güvenli köprü uçları,
- yerel cihaz entegrasyonları,
- kullanıcıya ait veri sınırları
için hafif bir bağlantı katmanı olabilir.
Bu yapı merkezi SaaS'a tamamen bağımlı olmadan, yerel öncelik ve isteğe bağlı senkron yaklaşımıyla tasarlanmalıdır.
Mini Lumos server erken fazda zorunlu değildir; uzun vadeli mimari notudur.
---
## Tek cümlelik ürün vaadi
**Lumos yardım eder ve yönlendirir; kalıcı veya riskli adımı kullanıcı onayı olmadan atmaz.**
