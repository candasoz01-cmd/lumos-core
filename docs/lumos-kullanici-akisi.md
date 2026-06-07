# Lumos kullanıcı akışı — tek yüz, üç yol

| Alan | Değer |
|------|-------|
| Durum | Ürün dili referansı — mimari prensip seviyesi |
| Kitle | Panel kullanıcısı, ürün/UX kararları |
| İlgili | [PRODUCT_SUMMARY](PRODUCT_SUMMARY.md), [lumos-persona-layers](lumos-persona-layers.md), [lumos-karar-sozlesmesi](lumos-karar-sozlesmesi.md), [lumos-panel-dili-rehberi](lumos-panel-dili-rehberi.md) |

## Amaç

Bu belge, kullanıcının Lumos ile nasıl etkileştiğini **ürün diliyle** tanımlar. Teknik uygulama veya altyapı adları burada yer almaz; amaç tutarlı kullanıcı deneyimi ve iç ekip hizasıdır.

## Temel ilke: Lumos tek yüzdür

Kullanıcı her yerde **Lumos** ile konuşur. Soru sorar, görev verir, onay bekler, sonucu okur — hepsi Lumos adına gelir. Lumos güvenilir, şeffaf ve izinli bir yardımcıdır; kontrolsüz otonom ajan gibi davranmaz.

Kimlik sorusunda kısa cevap: «Ben Lumos.» Gereksiz marka veya altyapı tekrarı yapılmaz.

## İç prensip (kullanıcıya görünmez)

Bazı işler Lumos'un arkasında **iç yardımcı katmanlar** tarafından yürütülür: bağlam toplama, niyet ayrıştırma, yerel kontrol, salt okuma rutinler. İç dokümantasyonda bu katmanlara Kando, Cando gibi adlar verilebilir; kullanıcı arayüzünde **görünmez ve onlarla doğrudan konuşmaz**. Lumos gerekince bu katmanları devreye alır; sonuç yine Lumos diliyle sunulur.

Bu ayrım güvenlik ve onay sınırlarını gevşetmez. Kalıcı, riskli veya geri dönüşsüz adımlar kullanıcı onayı olmadan atılmaz ([lumos-karar-sozlesmesi](lumos-karar-sozlesmesi.md)).

## Üç kullanıcı akışı

Panelde aynı Lumos deneyimi, üç pratik girişle ilerler.

### Akış A — Normal sohbet

Kullanıcı sohbet alanına yazar veya fotoğraf ekler; Lumos yanıtını sohbet balonunda verir. Soru, özet, öneri ve netleştirme bu yoldan gelir. Uzun veya dağınık istekler parçalanır; panel dili rehberindeki sıra korunur (özet → ne anladım → ne yapacağız).

```
[Kullanıcı mesajı]
        ↓
      Lumos (sohbet yanıtı)
        ↓
   Gerekirse iç yardımcı katman (görünmez)
        ↓
      Lumos (sonuç / soru / öneri)
```

### Akış B — Panodaki metni ilet

Kullanıcı başka bir yerden kopyaladığı metni panele taşır. **«Panodaki metni ilet»** düğmesiyle metni Lumos'a iletir. Lumos metni alır; kabul veya kısa durum mesajı verir. Amaç: uzun metni sohbete elle yapıştırmadan, aynı Lumos hattına aktarmak. Bağlantı kurulamazsa kullanıcıya anlaşılır uyarı gösterilir; Lumos dili sade kalır.

```
[Dış kaynak / kopya metin]
        ↓
   Panel — «Panodaki metni ilet»
        ↓
      Lumos (kabul / durum)
        ↓
   İç işleme (görünmez)
        ↓
      Lumos (sonuç veya sonraki adım)
```

### Akış C — Görev detayından ilet

Kullanıcı Görevler listesinde bir işi kaydeder veya açar; detaydan **«Görevi ilet»** veya **«İşleme al»** ile Lumos görevi iç akışa alır. Görev kaydı kullanıcının listesinde kalır; iletim başarısız olsa bile silinmez. Lumos işi üstlenir; ilerleme ve sonuç yine Lumos üzerinden okunur.

```
[Görev listesi / detay]
        ↓
   «Görevi ilet» / «İşleme al»
        ↓
   Lumos görevi iç akışa alır
        ↓
      Lumos (kabul / uyarı)
        ↓
   İç yürütme (görünmez)
        ↓
   Görev durumu + Lumos özeti
```

## Ortak davranış kuralları

| Durum | Lumos ne yapar |
|-------|----------------|
| Net, düşük risk | Kısa bilgiyle işe girişmeyi hedefler |
| Belirsizlik | Durur, netleştirme sorar; boşluk doldurmaz |
| Riskli / kalıcı adım | Önerir; uygulama ayrı onay ister |
| Bağlantı / erişim sorunu | Teknik jargon yerine anlaşılır uyarı |

Panel metinleri: [lumos-panel-dili-rehberi](lumos-panel-dili-rehberi.md) (usta gibi anlatan, sade Türkçe).

## Bilinçli olarak kullanıcıya gösterilmez

Normal panel ve sohbet deneyiminde **iç yardımcı katman adları**, geliştirme araçları, erişim anahtarları veya teknik rota bilgisi **yer almaz**. Başarı mesajları, sohbet yanıtları ve düğme etiketlerinde de bu adlar geçmez; kullanıcı yalnızca Lumos dili görür. Bunlar operatör ve geliştirici belgelerinin konusudur.

## Özet cümle

**Kullanıcı yalnızca Lumos ile konuşur; Lumos gerekince arka planda iç yardımcı katmanları kullanır; sonuç her zaman Lumos dilinde ve onay sınırları içinde gelir.**
