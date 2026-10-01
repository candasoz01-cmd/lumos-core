# Çok Dilli Yayın Mimarisi

| Alan | Değer |
| --- | --- |
| Karar | [LUMOS-0020](./BACKLOG.md) |
| Tarih | 2026-09-26 |
| Durum | Karar kaydı. Hat kurulmadı; çeviri üretilmedi |
| Katman | L2 — kitap yayın mimarisi |
| Kaynak | Kullanıcı kararı, bu oturum |
| Onay alanı | Boş. Ayrı kurul adı yazılmaz ([LUMOS-0003](./BACKLOG.md)) |

Bu not, kitap karar günlüğündeki LUMOS-0020 kaydının mimari dökümüdür.
Karar cümlesi [`BACKLOG.md`](./BACKLOG.md) içindedir. Çelişide o kayıt geçerlidir.

## Karar

Türkçe ana metin kitabın tek kaynağıdır. Çevirinin bağlandığı şey bu
kaynağın sabit bir sürümüdür. Dil sürümleri bağımsız metin değildir; o
kaynağa ve o sürüme bağlı türevdir.

Bu kayıt hiçbir çeviri üretmez. Sözlük doldurulmaz. Kitap yayımlanmaz.

## Amaç

Aynı kitabın anlamı, platformların otomatik çevirisine bağlı kalmadan,
mümkün olduğunca çok dilde korunabilsin.

## Kaynak ve türev

- Türkçe ana metin tek kaynaktır.
- Her dil sürümü belirli bir Türkçe kaynak sürümüne bağlanır. Bağ, yüzen
  güncel metne değil, sabitlenmiş bir sürüme (commit veya tag) kurulur.
- Kaynak yeni bir sürüme geçebilir. Eski sürüme bağlı türev kendiliğinden
  yeni metin sayılmaz.
- Dil sürümü ikinci bir kanon açmaz. Aynı dilin okuma veya kitap yüzü,
  [Belge §10](../lumos-book-outline.md) üç yüz modelinde olduğu gibi o dil
  türevinden üretilir; elle senkron tutulan ikiz metin yaşamaz.
- Platform otomatik çevirisi ne kaynak, ne senkron yöntemi, ne de onaydır.

## Öngörülen hat

Hat bugün yoktur. İleride bir dil sürümü ancak şu sıra ile yönetilir:

1. **Sabit kavram/terim sözlüğü.** Karşılıklar çeviri geçişinin içinde
   sessizce değişmez. Sözlüğe ekleme, değiştirme veya çıkarma insan
   kararıdır.
2. **AI ilk çeviri.** İlk metin taslaktır. Yayımlanmış dil sürümü değildir.
3. **Bağımsız anlam-tutarlılık kontrolü.** İlk çeviriyi üreten geçiş kendi
   çıktısını onaylamaz. Kontrol ayrı bir geçiştir ve anlamın kaynak
   sürümle tutup tutmadığına bakar.
4. **Kritik kavramlarda insan onayı.** Aşağıdaki kavramlar insan onayı
   olmadan hedef dilde kesin karşılık almış sayılmaz.
5. **Stale işaretleme.** Kaynak sürümü değişince, etkilenen dil sürümleri
   `stale` olur. Etki ayrıca kaydedilmeden bir türev güncel kalmaz;
   etki belirsizse türev güncel sayılmaz.
6. **Dil bazında sürüm ve provenance.** Her dil sürümü kendi sürümünü ve
   aşağıdaki köken kaydını taşır.

`stale` bir dil sürümü güncel yayım sayılmaz. İşaret, türev yeni kaynak
sürümüne aynı hat ile yeniden bağlanmadan kalkmaz.

## Köken kaydı

Her dil sürümü için öngörülen kayıt:

- dil
- bağlı Türkçe kaynak sürümü
- dil sürümünün kendi sürümü
- kullanılan sözlük sürümü
- ilk çeviriyi üreten geçiş
- bağımsız anlam-tutarlılık kontrolünün sonucu
- kritik kavramlar için insan onayının durumu
- `stale` durumu ve bu durumu doğuran kaynak sürümü

Alan ancak gerçekten oluştuğunda doldurulur. Boş alan olabilir; uydurma
geçiş, model veya onay yazılmaz.

## Sessiz yeniden yorum yok

Şu Project Lumos kavramları hedef dilde sessizce yeniden yorumlanmaz:

- Bilinç uzantısı
- insan merkezlilik
- yetki
- onay
- güven kökü
- Stajyer
- Duvar

Hedef dilde birebir karşılık güvenilir değilse bu, çevirmenin veya
modelin çözeceği bir üslup seçimi değildir. Sistem noktayı karar
gerektiren iş olarak insana getirir. Güvenilir karşılık yokken en yakın
kelimeyi kesin karşılık diye yazmaz.

Bu liste sözlüğün başlangıç kritik kümesidir. Kümeye kavram eklemek veya
kümeden kavram çıkarmak da insan kararıdır; bir çeviri geçişinin yan
ürünü değildir.

## Mevcut kitap yapısıyla ilişki

Kontrol 2026-09-26, `main` `4357f6df`. Aynı karar repoda yoktu; bu kayıt
onu açar, kopyasını üretmez.

| Yer | Ne var | Bu kararla ilişki |
| --- | --- | --- |
| `docs/lumos-book-outline.md` Belge §6 | Açık soru: yalnızca Türkçe mi, yoksa Türkçe ana metin ve İngilizce özet/terim sözlüğü mü | Bu karar soruyu daraltır: Türkçe ana metin tek kaynak ve sabit sürümdür; diğer diller türevdir; kapsam yalnızca İngilizce özet ve sözlük değildir. `lumos-book-v0.1` dondurulduğu için outline satırı bu görevde değiştirilmez |
| Belge §10 | Tek kaynak, çok yüz; web ve PDF aynı dilden ayrı metin olarak senkron tutulmaz. Uzun vadede «çoklu dil» boş bir satırdır | Dil türevleri ikinci kanon değildir. Çoklu dil satırının mimarisi bu nottur. Outline'a işlenmez |
| [LUMOS-0002](./BACKLOG.md) | Panel ve arayüz yerelleştirmesi; Belge §12 dil engeli | Ürün arayüzü kararıdır. Kitap metni kararı değildir. Birleştirilmez; ilişkili karar olarak durur |
| [ADR-014](../decisions/ADR-014-personal-workspace-language.md) | Kişisel katman ile örgütsel kayıt arasında normalizasyon | Kitap çevirisi değildir |

Dondurulmuş iskelet: `lumos-book-v0.1` (`0799c34`). Yeni fikir outline'a
yazılmaz; karar günlüğü veya taslak not burasıdır.

## Bu görevde yapılmayanlar

- Çeviri üretilmez.
- Sözlük karşılığı yazılmaz.
- Kitap, web okuma sürümü veya dil sürümü yayımlanmaz.
- Pull request merge edilmez.
- Deploy yapılmaz.
- Hat için kod, iş akışı veya dil dosyası açılmaz.
