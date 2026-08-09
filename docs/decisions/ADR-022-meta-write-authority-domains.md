# ADR-022 — Meta Yazma/Yayın Yetki Alanları (Authority Domains)

| Alan | Değer |
|------|-------|
| Karar durumu | **Taslak (2026-08-10)** — çerçeve ilkesi kurucu tarafından verildi; sınıf atamaları kurucu onayı bekliyor |
| Uygulama durumu | Uygulanmadı — bu ADR Accepted olmadan hiçbir yazma/yayın kodu yazılmaz |
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
  bağlantı/ne zaman); alan askıya alınabilir (kill-switch).
- **Yeniden onay tetikleyicileri** (kapsam/risk değişimi sayılır): alana yeni
  bağlantı eklenmesi · yeni eylem sınıfı · limit artışı · ücretlendirme
  modelinin değişmesi · platform politika kategorisinin değişmesi.

## Yetki sınıfları (öneri — kurucu onayı bekliyor)

| Sınıf | Tanım | Onay modeli |
|-------|-------|-------------|
| **A — Yanıt otonomisi** | Karşı tarafın başlattığı konuşmaya cevap (inbound yanıtı) | Alan bir kez tanımlanır; içinde tam otonom |
| **B — Kendi kanalında yayın** | Kendi varlığında kamuya açık içerik | Alan + oran/şablon sınırı; içinde otonom |
| **C — Proaktif/toplu erişim** | Muhatabın başlatmadığı, ücret doğuran veya kitlesel gönderim | Her kampanya = yeni kapsam → kurucu onayı; kampanya içinde otonom |

### Dört yeteneğin sınıf ataması (öneri)

| Yetenek | Önerilen sınıf | Gerekçe |
|---------|----------------|---------|
| WhatsApp toplu mesaj (template/broadcast) | **C** | Konuşma başına ücret; spam/ban riski en yüksek; kampanya doğası gereği kapsam her seferinde değişir |
| WhatsApp grup paylaşımı | **C** | Cloud API'de grup desteği sınırlı/politika-hassas; kitlesel etki |
| Instagram DM — gelen mesaja yanıt | **A** | Muhatap konuşmayı başlatmış; 24 saatlik pencere platform kuralı zaten sınırlar |
| Instagram DM — proaktif (cold) | **C** | Politika riski; istenmeyen erişim |
| Instagram yayın (feed/story) | **B** | Kendi kanalı; kamuya açık ama muhatapsız |
| Facebook Pages yayın | **B** | Kendi Sayfası; Instagram yayınıyla aynı doğa |
| WhatsApp müşteri penceresi yanıtı | **A** | Inbound'a 24 saat penceresinde yanıt; ücretsiz/karşılıklı |

## Ön koşullar (bu ADR Accepted olsa bile kod öncesi kapılar)

1. **App Review / Advanced Access**: yazma izinleri (örn. `instagram_business_manage_messages`,
   `pages_manage_posts`, `whatsapp_business_messaging`) dev-mode dışına App Review
   ister; Review süreci ayrı operasyon işidir.
2. **Gerçek WhatsApp numarası**: hâlâ kurucu onay kapısında (ADR-021 sınırı).
3. Ücret doğuran ilk gönderim sınıf ne olursa olsun kurucu onayına bağlıdır
   (faturalama hattı kurulana kadar).

## Bu taslağın açık soruları (kurucu kararı)

- Sınıf atamaları tablosu onaylanıyor mu, değişiklik var mı?
- B sınıfında içerik onayı: tam otonom mu, yoksa ilk N gönderi için taslak-kuyruk mu?
- Alan geçerlilik süresi (süresiz mi, periyodik yeniden teyit mi)?
