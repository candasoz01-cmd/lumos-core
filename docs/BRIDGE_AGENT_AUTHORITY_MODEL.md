# Bridge / Agent Yetki Mimarisi - Baslangic Tasarim Notu

## Amac

Bu dokuman, Lumos ile Mac/cihaz tarafinda calisacak bridge/agent katmaninin yetki sinirlarini netlestirmek icin olusturuldu.

Hedef, Lumos'un cihaz uzerinde kontrolsuz ve serbest yetkiyle davranmasini engellemek; her islemi sinirli, izlenebilir, onayli ve fazlara ayrilmis hale getirmektir.

## Lumos'un rolu

- Lumos, kullanici ile cihaz/dis dunya arasinda guvenli gecit ve orchestrator gibi davranir.
- Son kullaniciya gorunen ana yuz Lumos'tur.
- Lumos, kullanici niyetini degerlendirir ve gerekirse bridge/agent katmanina sinirli is verir.
- Lumos kendi basina serbest terminal, dosya sistemi veya OS yetkisi kullanmamalidir.
- Lumos riskli islemlerde kullanicidan acik onay almadan ilerlememelidir.

## Bridge / agent katmaninin rolu

- Bridge/agent katmani, Mac veya cihaz islemleri icin ayri ve kontrollu bir araci katmandir.
- Lumos'tan gelen yetkili ve onayli isleri uygular.
- Terminal, dosya sistemi, uygulama acma, mail, takvim ve kisiler gibi alanlar icin ayri izin modeli gerekir.
- Bridge/agent yalnizca tanimli, sinirli ve loglanabilir isleri yapmalidir.

## Yetki sinirlari

| Alan | Ilk faz yaklasimi |
| --- | --- |
| Gozlem / durum okuma | Dusuk riskli olabilir |
| Listeleme | Kontrollu ve sinirli olabilir |
| Dosya yazma / degistirme | Onayli olmali |
| Terminal / komut yurutme | Ilk fazda kapali veya cok sinirli olmali |
| Uygulama acma / kontrol | Sonraki faza birakilmali |
| Mail / takvim / kisiler | Ayrica izin modeli olmadan acilmamali |
| Ag / dis servis yazma | Acik onay olmadan yapilmamali |

## Kullanici onayi gereken islemler

- Terminal komutu calistirma
- Dosya olusturma, degistirme veya silme
- Uygulama acma veya uygulama icinde islem yapma
- Mail gonderme, silme veya arsivleme
- Takvim etkinligi olusturma, silme veya guncelleme
- Kisiler verisine erisme
- Domain alma, odeme yapma veya dis servislerde islem baslatma
- Kalici silme veya geri alinmasi zor islem yapma

## Yasak / kacinilacak islemler

- Kullanici acik onayi olmadan riskli islem yapmak
- Dosyayi kalici silmek
- Odeme baslatmak
- Domain satin almak veya yenilemek
- Mail gondermek ya da silmek
- Gizli bilgileri gereksiz yere Lumos uzerinde tutmak
- Sahte/mock ciktiyi gercek sistem ciktisi gibi sunmak
- Kando/Cando gibi ic katman adlarini urun arayuzunde gostermek

## Loglama ve dogrulama

- Bridge/agent tarafinda yapilan islemler loglanmalidir.
- Hangi islem yapildi, hangi dosyaya dokunuldu, hangi komut calisti ve sonuc ne oldu acikca kaydedilmelidir.
- Lumos, gercek dosya, terminal ciktisi veya repo durumu gormeden kesin sonuc bildirmemelidir.
- Test veya dogrulama yapilmadan is tamamlanmis sayilmamalidir.

## Ilk fazda yapilmayacaklar

- Serbest terminal yurutme
- Serbest dosya sistemi yetkisi
- Mail/takvim/kisiler uzerinde otomatik islem
- Odeme/domain islemleri
- Kalici silme
- Kullanici onayi olmadan uygulama veya OS kontrolu
- Gizli bilgileri tek noktada toplama

## Sonraki faz karari

Ilk fazda bridge/agent katmani sadece gozlem, listeleme, durum okuma ve dusuk riskli islemler icin dusunulmelidir.

Komut yurutme, dosya degistirme, uygulama kontrolu ve dis servis islemleri daha sonra ayri guvenlik modeli ve kullanici onayi ile acilmalidir.
