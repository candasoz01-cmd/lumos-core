# Panel dili — uzun istek çıktısı örneği

Bu dosya, **`docs/lumos-uzun-istek-isleme.md` §7**’deki özet şablonunun aynı içeriği **panel dili** (`docs/lumos-panel-dili-rehberi.md`) ile nasıl sunulacağını gösterir.

**Varsayılan senaryo:** Kullanıcı uzun, dağınık bir istek yazmış; ajan önce ayrıştırmış. Aşağıda önce **eski madde şablonu**, sonra **yeniden üretilmiş panel cevabı** var.

---

## Örnek uzun istek (girdi özeti)

*“Paylaşım olsun ama klasik sosyal medya gibi olmasın; insanlar bir şey üretsin, başkaları anlamlı tepki versin, like olmasın, geliştirme eklenebilsin. Karmaşık olmasın, az özellik ama boş da hissettirmesin. Sıfırdan mı yapalım bilmiyorum. Backend var ama tam değil. Auth basit olsun. Performans önemli ama önce çalışsın.”*

---

## Eski çıktı (§7 şablonu — referans)

```
• Anladığım ana amaç: …
• Çıkardığım parçalar: (başlık + sıra/bağımlılık)
• Kritik belirsizlikler: …
• Önce sorulması gerekenler: (tercihen gruplu, örn. 3 madde)
• Hazır çözüm notu: (gerekirse kısa; yoksa “—”)
• Uygulamaya hemen geçilebilecek kısım: …
```

**Aynı içerikle doldurulmuş (kuru liste):**

- Anladığım ana amaç: Ortak üretim + zincirleme ekleme; klasik feed/like değil; sade MVP.
- Çıkardığım parçalar: (1) veri modeli kök+ek, (2) basit auth, (3) önce çalışır okuma-yazma, (4) performans sonra.
- Kritik belirsizlikler: İçerik türü (metin mi medya mı); eklentiler herkese açık mı onaylı mı.
- Önce sorulması gerekenler: Paylaşım türü; onay modeli; ana liste sıralaması.
- Hazır çözüm notu: Tam sıfır sosyal ağ ağır; hazır parça + ince özel deneyim genelde daha mantıklı.
- Uygulamaya hemen geçilebilecek kısım: Tek cümle ürün vaadi + kök/ek API taslağı.

---

## Panel dilinde yeniden üretilmiş cevap

**1. Kısa özet**

İstediğin şey: tek yönlü akış değil, **paylaşılan bir köke kısa ekler** ile büyüyen, sade bir deneyim. Önce çalışan ince bir hat; auth ve altyapıyı basit tutup performansı sonraya bırakmak doğru sıra.

**2. Ne anladım**

- Klasik beğeni/feed hissi istemiyorsun; **“üzerine anlamlı parça ekleme”** istiyorsun.
- Çok özellik değil ama **boş his** de vermesin — yani ilk giren ne yapacağını anlasın.
- Backend kısmen var; auth şimdilik **hafif** olsun; **önce çalışsın** önceliği.

**3. Ne öneriyorum / ne yapacağız**

En mantıklısı şu olur: **bir kök kayıt + sıralı ekler** (like yok). Ekranda net iki yol: *yeni kök* / *şuna ekle*.  
Sıfırdan “her şeyi” kurmak yerine: **hazır parçalar** (basit giriş, veritabanı, barındırma) üzerine bu **dar deneyimi** özel yazmak — hem bakım hem farklı his için genelde daha iyi.

Hemen gidilebilecek adım: **tek cümle vaat** (örn. “Bırak, üzerine kısa ekle”) + kök ve ek listesi için **en küçük veri şekli** taslağı.

**4. Örnek / sade açıklama**

Düşün ki bir **ortak not defteri**: ilk satırı biri açar, alttaki satırlar **devam** — hepsi görünür, kim ne eklediği belli. Like yok; “beğen” yerine **“bir satır daha yaz”** var.

**5. Sorular**

Netleşince yol çok açılır; üç nokta yeter:

1. Paylaşılan şey çoğunlukla **yazı mı**, yoksa görsel/kod da olacak mı?  
2. Ekler **hemen herkese görünsün mü**, yoksa kök sahibi **onaylasın mı**?  
3. Ana liste **en son hareket** mi, **en yeni kökler** mi?

---

*Bu örnek, “mevcut uzun kullanıcı isteği çıktısı”nın panel diline çevrilmiş halidir; gerçek ürün kararı değil, anlatım kalıbı örneğidir.*
