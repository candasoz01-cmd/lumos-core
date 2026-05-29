# Lumos Abonelik ve Ödeme Kontrol Modülü

**Durum:** Plan / not (henüz uygulanmadı)

**Amaç:** Abonelik ve ödeme takibini Lumos içinde tanımlamak; otomasyon veya kod değişikliği yapmadan davranış sınırlarını ve veri modelini netleştirmek.

**Sınırlar:** Bu belge yalnızca dokümantasyon/not altyapısıdır. Mevcut çalışan koda, API’ye, veritabanına veya UI’ya dokunulmaz.

---

## Amaç

- Kullanıcının abonelik, ödeme, yenileme ve kart hareketlerini takip etmesine yardımcı olmak.
- Otomatik ödeme başlatmamak.
- Kullanıcı onayı olmadan satın alma, yenileme, kart açma/kapama, ödeme veya iptal işlemi yapmamak.
- Yaklaşan ödeme ve başarısız ödeme durumlarında kullanıcıyı açıkça uyarmak.

---

## Kurallar

- Lumos hiçbir ödeme işlemini kullanıcı onayı olmadan başlatamaz.
- Lumos kart, banka, ödeme sağlayıcı veya abonelik ayarlarını kendi başına değiştiremez.
- Lumos sadece izleme, hatırlatma, sınıflandırma, risk uyarısı ve yönlendirme yapar.
- Kullanıcı isterse manuel işlem için adım adım rehber sunar.
- Kartlar varsayılan olarak kapalı/manuel kontrol mantığıyla ele alınır.
- Uygulama ödeme zamanı uyarı gönderdiğinde kullanıcı kartı geçici açabilir; Lumos bunu sadece hatırlatır ve takip eder.
- Cloudflare benzeri iptal/downgrade sorunlarında Lumos mail, fatura, destek kaydı ve banka itirazı kanıtlarını düzenli takip eder.

---

## Takip edilecek veri alanları

| Alan | Açıklama |
|------|----------|
| Servis adı | Abonelik veya hizmet sağlayıcı |
| Tutar | Ödeme tutarı |
| Para birimi | Örn. TRY, USD, EUR |
| Kart sonu | İlgili kartın son dört hanesi |
| Son ödeme tarihi | En son başarılı veya denenen ödeme |
| Bir sonraki yenileme tarihi | Planlanan yenileme |
| Durum | aktif / iptal planlandı / iptal edildi / itirazda / beklemede |
| Risk seviyesi | düşük / orta / yüksek |
| Kullanıcı kararı | Kullanıcının aldığı veya planladığı karar |
| Kanıt bağlantıları veya notlar | Mail, fatura, destek kaydı, banka itirazı vb. referanslar |

---

## Örnek servisler

- Cloudflare
- Cursor
- Runway
- OpenAI / ChatGPT
- Vercel
- DigitalOcean
- Apple
- Claude

---

## Öncelik

- Önce sadece dokümantasyon/not olarak ekle.
- Mevcut çalışan koda dokunma.
- Yeni API, database veya UI ekleme.
