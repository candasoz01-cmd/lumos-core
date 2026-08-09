# ADR-022 — Meta Yazma/Yayın Yetki Alanları (Authority Domains)

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-10)** — kurucu onayı, iki düzeltme ve üç açık sorunun cevabıyla (bkz. §Kurucu kararları) |
| Uygulama durumu | Uygulanmadı — ilk dilim: A sınıfı WhatsApp gelen-mesaja yanıt, sandbox (ayrı küçük PR'larla) |
| Üst ilişki | [ADR-020](ADR-020-meta-communications-exception.md) salt-okunur sınırını **yalnız bu ADR Accepted olduğunda ve tanımlı alanlar kapsamında** deler; [ADR-021](ADR-021-meta-multi-connection-model.md) bağlantı modeli üzerine kurulur |
| Kapsam | Meta hatlarında (WhatsApp, Instagram, Facebook Pages) yazma/yayın yetkisinin modeli |

## Çerçeve ilkesi (kurucu, 2026-08-10)

> Lumos'a her gönderimde tekrar tekrar onay sorduran bir sistem kurmayalım.
> Yetki alanı bir kez tanımlansın; Lumos o alan içinde otonom çalışsın.
> Yeniden onay ancak kapsam/risk değiştiğinde gelsin.

Bu ilke, Lumos'un "Kontrol Sende" çizgisinin yazma yetkisindeki karşılığıdır:
kontrol, eylem başına veto ile değil, **sınırları açık bir yetki alanının bir kez
bilinçli tanımlanmasıyla** kurulur.

## Model: Yetki Alanı (Authority Domain)

Bir yetki alanı, kalıcı ve denetlenebilir tek kayıttır:

```
AuthorityDomain {
  domain_id            — kalıcı iç kimlik (ADR-021 connection_id deseni)
  connection_ids[]     — hangi bağlantılar adına (ADR-021 satırları; kopya değil referans)
  action_class         — aşağıdaki sınıflardan biri
  limits               — oran (gönderim/saat), hedef kapsamı, şablon kümesi, geçerlilik süresi
  granted_at / granted_by — kurucu onayının tarihi ve kaydı
  status               — active | suspended (kill-switch) | expired
}
```

- Her yazma eylemi gönderilmeden önce **sunucu tarafında** aktif bir alanla
  eşleştirilir; eşleşmeyen eylem gönderilmez, onay talebine dönüşür.
- Her gönderim append-only denetim kaydına yazılır (kim/hangi alan/hangi
  bağlantı/ne zaman).
- **Kill-switch yetkinin ÜSTÜNDEDİR** (kurucu, 2026-08-10): tek hareketle
  TÜM yazma alanları askıya alınabilir. Bu bir yeniden-onay süreci değil,
  acil durdurmadır; hiçbir alan tanımı kill-switch'i daraltamaz.
- **Yeniden onay tetikleyicileri** (kapsam/risk değişimi sayılır): alana yeni
  bağlantı eklenmesi · yeni eylem sınıfı · limit artışı · ücret/risk/politika
  değişimi · elle askıya alınan alanın yeniden açılması. Bunların dışında
  periyodik "hâlâ onaylıyor musun?" YOKTUR.

## Kurucu kararları (2026-08-10 — taslağı Accepted'a çeken cevaplar)

1. **Sınıf atamaları onaylı**, iki düzeltmeyle: WhatsApp gelen-mesaja yanıt = A
   (tabloda görünür satır); WhatsApp grup paylaşımı **sınıf DIŞI —
   `platform capability pending / unsupported until proven`** (Cloud API'de
   klasik gruplara gönderim standart/güvenilir bir yetenek olarak
   VARSAYILMAZ; kanıtlanmadan ADR bunu normlaştırmaz).
2. **B sınıfı tam otonom**: ilk-N taslak kuyruğu YOK (işlem-bazlı onaya geri
   dönüş olur); sınırlama gerekiyorsa oran, günlük adet, içerik türü ve hedef
   hesap sınırı AuthorityDomain limitlerinde tanımlanır.
3. **Geçerlilik varsayılan süresiz**: periyodik yeniden teyit yok; yeniden
   onay yalnız gerçek tetiklerde (yukarıdaki liste).

## Yetki sınıfları (kurucu onaylı)

| Sınıf | Tanım | Onay modeli |
|-------|-------|-------------|
| **A — Yanıt otonomisi** | Karşı tarafın başlattığı konuşmaya cevap (inbound yanıtı) | Alan bir kez tanımlanır; içinde tam otonom |
| **B — Kendi kanalında yayın** | Kendi varlığında kamuya açık içerik | Alan + oran/şablon sınırı; içinde otonom |
| **C — Proaktif/toplu erişim** | Muhatabın başlatmadığı, ücret doğuran veya kitlesel gönderim | Her kampanya = yeni kapsam → kurucu onayı; kampanya içinde otonom |

### Yeteneklerin sınıf ataması (kurucu onaylı, 2026-08-10)

| Yetenek | Sınıf | Gerekçe |
|---------|-------|---------|
| WhatsApp gelen-mesaja yanıt (24 saat müşteri penceresi) | **A** | Inbound'a yanıt; ücretsiz/karşılıklı; **ilk uygulama dilimi (sandbox)** |
| WhatsApp toplu mesaj (template/broadcast) | **C** | Konuşma başına ücret; spam/ban riski en yüksek; kampanya doğası gereği kapsam her seferinde değişir |
| WhatsApp grup paylaşımı | **sınıf dışı** | `platform capability pending / unsupported until proven` — Cloud API'de kanıtlanmadan yetenek varsayılmaz; kanıtlanırsa sınıf ataması AYRI kurucu kararıdır |
| Instagram DM — gelen mesaja yanıt | **A** | Muhatap konuşmayı başlatmış; 24 saatlik pencere platform kuralı zaten sınırlar |
| Instagram DM — proaktif (cold) | **C** | Politika riski; istenmeyen erişim |
| Instagram yayın (feed/story) | **B** | Kendi kanalı; kamuya açık ama muhatapsız |
| Facebook Pages yayın | **B** | Kendi Sayfası; Instagram yayınıyla aynı doğa |

## Ön koşullar (bu ADR Accepted olsa bile kod öncesi kapılar)

1. **App Review / Advanced Access**: yazma izinleri (örn. `instagram_business_manage_messages`,
   `pages_manage_posts`, `whatsapp_business_messaging`) dev-mode dışına App Review
   ister; Review süreci ayrı operasyon işidir.
2. **Gerçek WhatsApp numarası**: hâlâ kurucu onay kapısında (ADR-021 sınırı).
3. Ücret doğuran ilk gönderim sınıf ne olursa olsun kurucu onayına bağlıdır
   (faturalama hattı kurulana kadar).

## İlk uygulama dilimi

**A sınıfı — WhatsApp gelen-mesaja yanıt, sandbox** (Test WABA
`1533094525525137` / test numarası). En düşük risk: inbound'a yanıt, ücret yok,
gerçek numara yok. Dilim planı ayrı küçük PR'larla gelir; App Review /
`whatsapp_business_messaging` izni bu dilimin ön koşul analizinde ele alınır
(repo test guard'ı `doesNotMatch(/messaging/)` o dilimde bilinçli olarak
güncellenene kadar scope istenmez).
