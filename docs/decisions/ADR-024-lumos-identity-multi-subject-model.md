# ADR-024 — Lumos Identity: Çok-Özne Kimlik Modeli

> Kapsam notu (2026-08-17): Bu belge, kurucunun 2026-08-17 tarihli mimari
> yönlendirmesini ("kapı çok-özne modeline açılsın") karar seviyesinde kayda
> geçirir. **Hiçbir kod yazılmamıştır ve bu ADR kod yazma izni değildir.**
> Kurucunun aynı gün koyduğu #336 kuralı gereği: duvarda kapının yeri açılır,
> oda Faz-1 zamanı gelmeden inşa edilmez. Aşağıdaki "mevcut kod" gözlemleri
> 2026-08-17 tarihli depo durumuna dayanır.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-17)** — kurucu, aynı gün S1/S2/S2b/S3'ün tamamını cevapladı ve beşinci özneyi (Lumos'un kendi kimliği) ekledi; §Kabul ölçütü'nün üç maddesi kapatıldı |
| Uygulama durumu | Uygulanmadı — kod yok, şema yok, migration yok; uygulama açılışı ayrı ve açık bir karardır (FAZ-1 / STOP LIST) |
| Tarih | 2026-08-17 |
| Üst ilişki | [ADR-016](ADR-016-lumos-id-memory-gateway.md) Lumos ID + Memory Gateway (bkz. §Karar çatışması), [ADR-022](ADR-022-meta-write-authority-domains.md) AuthorityDomain modeli genelleştirilir, [ADR-007](ADR-007-trust-engine-layer.md) Trust, [ADR-006](ADR-006-ai-firewall-guard-layer.md) Firewall, [ADR-023](ADR-023-lumos-representative-avatar.md) Representative ilk agent öznesidir, [ADR-015](ADR-015-lumos-service-api-gateway.md) Connect |
| Kapsam | Lumos'ta kimliğin **kökünün ne olduğu** ve özneler arası yetkinin nasıl kurulduğu — yalnız sınır ve model; kripto, protokol, şema, depolama kapsam dışı |

## Kurucu yönlendirmesi (2026-08-17)

Üç seçenek değerlendirildi:

| # | Model | Kurucu değerlendirmesi |
|---|-------|------------------------|
| 1 | **İnsan merkezli** — kök kullanıcı; cihaz/agent/servis onun altında yetkilendirilir | Basit ve anlaşılır; bağımsız çalışan agent'lar ve kurumsal kimlikler gelince dar gelir |
| 2 | **Cihaz merkezli** — kök `DeviceIdentity`; insan/hesap üstte bağlanır | Mevcut çalışan koda yakın, privacy/offline güçlü; "telefonumu değiştirdim, kimliğim ne oldu?" sorunu. **Kurucu: ana yol yapmazdım** |
| 3 | **Çok-özne** — insan, cihaz, agent, servis ayrı kimlikler; aralarında yetki ilişkisi | **Seçildi** |

Gerekçe (kurucu): Lumos'un gittiği yerde soru "kullanıcı giriş yaptı mı?"
değil, **"kim, kim adına, hangi yetkiyle, hangi veriye, ne kadar süre
erişti?"** olacak. Memory, Vault, Connect, Representative, ödeme ve ileride
gelecek diğer agent'lar bunun üzerine oturabilir.

---

## Karar

### K0 — Lumos ID bir özne değil, **identity authority / trust root**'tur

Kurucu kararı (2026-08-17): Lumos ID, dört öznenin toplamı ya da onlardan
biri **değildir**. Lumos ID, öznelerin **kim olduğunu, hangi yetkinin kimden
geldiğini ve ne zaman biteceğini** tutan üst çatıdır — kimlik otoritesi ve
güven kökü.

> "Hepsi Lumos ID'nin kendisi" değil; Lumos ID onların arasındaki **güven ve
> yetki haritasını** tutar. — kurucu, 2026-08-17

Sonuçları:

- Lumos ID **grant veren taraf değildir**; grant'ları **kaydeden, doğrulayan,
  süresini işleten ve iptali uygulayan** mercidir. Yetkiyi insan öznesi verir,
  Lumos ID onu geçerli kılar ve denetler.
- Bir özneye "Lumos ID'sin" denemez; her özne Lumos ID **altında kayıtlıdır**.
- Kurucunun örnek zinciri bu modelde şöyle okunur:
  Candaş → MacBook'una güven verir · Candaş → Representative'a şu toplantıda
  konuşma yetkisi verir · Representative → ödeme servisine yalnız belirli bir
  işlem için çağrı hakkı **alır** · Lumos ID → bu üçünün kimliğini, yetkinin
  kaynağını ve bitişini kontrol eder.
- Üçüncü satır **N3'ü (devir varsayılan kapalı) bozmaz**: Representative bu
  hakkı kendi kendine devretmez; hak, insan öznesinin yetkisi altında Lumos ID
  tarafından o özne çiftine **verilir**.

**Lumos ID ≠ Lumos öznesi (kritik ayrım, kurucu 2026-08-17):** Lumos ID
*sistemin adıdır* — kimlerin var olduğunu ve aralarındaki güven/yetki
ilişkisini yöneten otorite. Lumos'un **"ben" diyen kendi kimliği** ise bu
otorite değil, onun altında kayıtlı **ayrı bir öznedir** (K1'deki Lumos
öznesi). Bunları aynı şey saymak, otoriteyi kendi kendine yetki üretebilen
bir aktöre çevirir; N8 bunu yasaklar.

**Sınır (bu ADR'de kararlaştırılmayan):** Lumos ID = identity authority,
[ADR-007](ADR-007-trust-engine-layer.md) Trust Engine ile aynı şey değildir.
Kimlik otoritesi "kim, kimden aldığı hangi yetkiyle" sorusunu; Trust "bu
aktöre ne kadar güveniyoruz" sorusunu yanıtlar. İkisinin sınırı ve hangisinin
diğerini çağırdığı **ayrı bir karar turudur** (ADR-007 birleşik bir Trust
Engine'in bugün var olmadığını kaydediyor — bu boşluk kapatılmadan sınır
yazılamaz).

### K1 — Beş özne türü

Lumos ID'nin altında **beş ayrı özne türü** vardır. Hiçbiri diğerinin
kimliği değildir; hiçbiri diğerinin altında "alt hesap" olarak modellenmez.
Kurucunun koyduğu ayrımın amacı nettir: bir agent'a yetki verirken
**"kullanıcının kimliğiyle mi, kendi kimliğiyle mi çalışıyor?"** sorusu hiç
doğmamalıdır. Cevap her zaman aynıdır — agent **kendi kimliğiyle** çalışır,
insan öznesi **adına** ve sınırlı yetkiyle.

| Özne | Ne temsil eder | Örnek |
|------|----------------|-------|
| **İnsan** | Gerçek kişi; hukuki sorumluluk ve nihai onay mercii | Candaş |
| **Lumos** | Lumos'un kendi sürekli kimliği — "ben" diyen özne; insan öznesinden ayrı, agent'lardan üstün değil ama onlarla **aynı şey değil** | Lumos |
| **Cihaz** | Fiziksel/mantıksal uç nokta; kriptografik olarak kendini kanıtlar | MacBook, iPhone |
| **Agent** | Bir özne adına, tanımlı bir görev için iş yapan yazılım aktörü | Representative |
| **Servis (workload)** | Sistem içi/dışı çalışan bileşen | Payment service, Memory Gateway |

**Lumos öznesi neden var (kurucu, 2026-08-17):** Lumos "ben" diyorsa,
yalnızca agent'ları yöneten soyut bir gateway olamaz — insan öznesinden ayrı,
**sürekliliği olan** bir öznesi olmalıdır. Representative gibi görev
agent'ları Lumos'un kendisi değildir: agent görev ömürlüdür ve
değiştirilebilir, Lumos öznesi süreklidir. Bu ayrım olmadan "Lumos mu dedi,
Representative mi dedi, Candaş mı dedi?" sorusu denetim kaydında
cevaplanamaz.

> Not: "Lumos ben der" ilkesinin kendisi bu depoda yazılı bir karar olarak
> **bulunamadı** (2026-08-17 taraması); kurucu beyanına dayanarak buraya
> alındı. İlkenin kendi kaydının hangi belgede duracağı takip işidir.

### K2 — Kimlik ≠ yetki

**Kimlik "kimsin"i, yetki "ne yapabilirsin"i söyler; ikisi ayrı kayıttır.**
Bir öznenin kimliğe sahip olması hiçbir eylem hakkı doğurmaz. Bir agent'ın
kimliği olması, onun kurucu adına konuşabildiği anlamına gelmez — bunun için
ayrı, açık, süreli bir yetki kaydı gerekir.

### K3 — Yetki bir devir kaydıdır (delegation), taklit değil

Yetki, "Candaş → Representative'a → şu işi → şu süreyle → şu veri üzerinde"
biçiminde **kaynak özne ile hedef özneyi birlikte adlandıran** bir kayıttır.
Representative "Candaş oldu" değildir; **Candaş adına, sınırlı yetkiyle
davranan ayrı bir öznedir.** Bu ayrım denetim kaydında da korunur: her kayıt
hem eylemi yapan özneyi hem adına yapılan özneyi taşır (`actor` + `on_behalf_of`).

### K4 — Yeni yetki nesnesi icat edilmez; AuthorityDomain genelleştirilir

[ADR-022](ADR-022-meta-write-authority-domains.md)'deki `AuthorityDomain`
bugün Meta yazma eylemlerine özgüdür. Rakip bir yetki modeli kurulmaz; aynı
kayıt **özne çiftiyle** genelleştirilir:

```
AuthorityGrant (AuthorityDomain'in genelleştirilmiş hâli)
  grant_id             — kalıcı iç kimlik
  subject_from         — yetkiyi veren özne (K1'deki dört türden biri)
  subject_to           — yetkiyi alan özne
  action_class         — hangi eylem sınıfı (ADR-022 sınıfları taban)
  data_scope           — hangi veri üzerinde (ADR-016 per-provider bölmeleme geçerli)
  validity             — süre / geçerlilik koşulu
  delegable            — alan özne bu yetkiyi devredebilir mi (varsayılan: HAYIR)
  granted_at / granted_by
  status               — active | suspended (kill-switch) | expired | revoked
```

Bu kayıtların tutulduğu, doğrulandığı ve süresinin işletildiği yer **Lumos
ID'dir** (K0). Yani grant'lar özneler arasında ikili sözleşmeler olarak
dağınık durmaz; tek bir otoritede kayıtlıdır ve oradan iptal edilebilir.

### K5 — Değişmezler (invariant)

| # | Kural |
|---|-------|
| N1 | Hiçbir özne başka bir öznenin kimliğine dönüşemez; yalnız onun **adına** yetkilendirilir |
| N2 | Yetki daima **iptal edilebilir**; iptal, veren öznenin tek taraflı hakkıdır |
| N3 | Devredilebilirlik varsayılan olarak **kapalıdır**; agent, aldığı yetkiyi kendiliğinden başka bir agent'a geçiremez |
| N4 | Bir yetki, veren öznenin sahip olmadığı bir hakkı doğuramaz (yükseltme yasağı) |
| N5 | Kill-switch yetkinin ÜSTÜNDEDİR (ADR-022 ile aynı ilke) — tek hareketle tüm devirler askıya alınabilir; hiçbir grant tanımı bunu daraltamaz |
| N6 | İnsan öznesinin onayı gerektiren eylemler (kimlik doğrulama, biyometri, sözleşme, finansal işlem — ADR-023 dürüstlük sınırı) devredilemez; grant ile aşılamaz |
| N7 | Her denetim kaydı `actor` + `on_behalf_of` + `grant_id` üçlüsünü taşır; üçü eksikse eylem denetlenebilir sayılmaz |
| N8 | **Otorite kendine yetki üretemez:** Lumos ID (K0), altındaki Lumos öznesine insan öznesinin açık grant'ı olmadan yetki veremez; otorite ile Lumos öznesi aynı anahtar/oturum malzemesini paylaşmaz. Aksi hâlde güven kökü, kendi lehine karar veren bir aktöre dönüşür |
| N9 | Lumos öznesi ile agent özneleri **birbirinin yerine geçemez**: bir agent'ın yetkisi Lumos öznesinin yetkisi sayılmaz, Lumos öznesinin sürekliliği bir agent'ın ömrüne bağlanamaz |

### K6 — Bu ADR'nin kapsamadığı şeyler

Şunlar **bilinçli olarak açık bırakılmıştır** ve bu ADR'ye dayanarak
kararlaştırılmış sayılamaz: kriptografik şema ve anahtar yönetimi; kimlik
protokolü seçimi (OIDC / SPIFFE / DID / özel); depolama ve şema; cihaz
kaydı/kurtarma akışı; kurumsal kiracılık (tenancy) uygulaması; mevcut
`DeviceIdentity` ve `lumos_id_provider` için geçiş planı. Bunlar uygulama
kapısı açıldığında ayrı ADR/tasarım turudur.

---

## Karar çatışması: ADR-016 ile ilişki

`docs/CONSTITUTION.md` en-yeni-karar otoritesi gereği açıkça kaydedilir:

- **ADR-016 der ki:** "Lumos ID, kullanıcının tek ve kalıcı kimliğidir." Bu,
  yukarıdaki **Seçenek 1 (insan merkezli)** okumasıdır ve Lumos ID'yi bir
  **kimlik** olarak tanımlar.
- **ADR-024 bunu değiştirir (kurucu, 2026-08-17):** Lumos ID bir kimlik değil,
  **kimlik otoritesidir** (K0). Kullanıcının kimliği, Lumos ID altındaki
  **insan öznesidir**; cihaz, agent ve servis kimlikleri onun altında değil,
  **yanındadır** — dördü de Lumos ID'ye kayıtlıdır.
- **Terminoloji sonucu:** ADR-016'nın "Lumos ID = kullanıcı kimliği" cümlesi
  bu ADR ile **yürürlükten kalkar**; yerine "Lumos ID = identity authority /
  trust root" geçer. Bu değişiklik ADR-016 gövdesine işlenmelidir (takip işi).
- **ADR-016'nın korunan kısmı:** I1-I6 ilkelerinin tamamı yürürlüktedir —
  sağlayıcı bağımsızlığı, `source_provider` zorunluluğu, per-provider
  bölmeleme, otomatik paylaşım yasağı, çapraz kullanımda açık onay. Bu ADR
  hafıza bölmelemesini değiştirmez; yalnız **kimin adına** bölmelendiğini
  dört özneye genişletir.
- **Sonuç:** ADR-016 iptal edilmez, **kapsamı daraltılarak devam eder**.
  ADR-024 Accepted'a çekildiğinde ADR-016'ya karşılıklı referans notu
  düşülmelidir (takip işi, bu turda yapılmadı).

---

## Mevcut kod ile ilişki (2026-08-17 gözlemi — değiştirilmedi)

| Kod | Bugünkü durum | Çok-özne modelindeki yeri |
|-----|---------------|---------------------------|
| [src/security/identity.py](../../src/security/identity.py) | Gerçek ve çalışır: ed25519 + AES-GCM `DeviceIdentity` | **Cihaz öznesi** — atılmaz, modelin bir bacağı olur |
| [src/integrations/providers/lumos_id_provider.py:62](../../src/integrations/providers/lumos_id_provider.py:62) | Stub — `real_identity_storage: False`, `cross_use_status: "plan_only"` | **İnsan öznesi** sözleşmesi; gerçek depolama uygulama kapısında |
| `src/integrations/providers/service_gateway_provider.py` | `identity` = Connect altında bir capability ailesi (`/v1/verify`) | Dış kimlik **doğrulama** yeteneği; Lumos'un kendi özne modeli DEĞİL — ayrım korunmalı |
| ADR-023 Representative | Faz 0 kodu canlı | İlk gerçek **agent öznesi**; bugün kendi kimliği yok, kurucunun oturumu içinde çalışıyor |
| — | **Lumos öznesi için kod yok** | K1'in beşinci satırının bugün hiçbir kod karşılığı yok; "Lumos" bugün kod tabanında bir özne değil, ürünün adı |

Bu tablo bir borç kaydıdır: Representative bugün ayrı bir agent kimliği
olmadan çalışıyor ve Lumos öznesinin karşılığı hiç yok. Bunlar ADR-024
uygulanana kadar **bilinen ve kabul edilen** boşluklardır; "zaten var" diye
raporlanmamalıdır (`docs/TECHNICAL_DEBT.md` → TD-16).

---

## Kurucu kararları (2026-08-17 — taslağı Accepted'a çeken cevaplar)

**S1 — Kurumsal/organizasyon özne mi? → KAPSAM (ayrı özne DEĞİL).**
"Şimdiden beşinci özne yaratmaya gerek yok. İnsan/cihaz/agent/servis modeli
kurumu temsil edecek yetki ilişkilerini taşıyabilir; gerçekten ayrı özne
gerektiren vaka çıkarsa sonra açılır." Kurum, grant'ların üzerinde çalıştığı
**kapsamdır**; "şirket bir şey yapmaz, şirket adına biri yapar" ayrımı korunur.
*(Öneriyle aynı yönde.)* Bu, gelecekte yeniden açılabilir bir karardır —
tetikleyici: kurumun kendi başına eylem yapması gereken gerçek bir vaka.

**S2 — "Lumos ID" adı hangisini gösterir? → identity authority / trust root.**
Ne yalnız insan kimliği ne öznelerin toplamı: Lumos ID, öznelerin kim
olduğunu ve aralarındaki güven/yetki ilişkisini **yöneten sistemin adıdır**.
Karar K0'a işlendi. *(Benim önerim "insan kimliği kalsın" idi; kurucu kararı
bunun yerine geçti.)*

**S2b — İnsan öznesinin kimliğinin adı? → ERTELENDİ (bilinçli).**
"Burada acele isim koymayalım. Çünkü Lumos ID artık o isim olmamalı." Belge
dilinde geçici olarak **"insan öznesi"** kullanılır; kalıcı ad ayrı ve sonraki
bir karardır. Bu erteleme Accepted'ı bloklamaz.

**S3 — Kurtarma kökü kim? → İNSAN ÖZNESİ.**
"Cihaz kimliği kaybolabilir/değişebilir; insanın sürekliliği cihazla birlikte
ölmemeli." İnsan öznesi kök kurtarma mercii olur; bunun zorunlu sonucu, insan
öznesinin **cihazdan bağımsız kanıtlanabilir** olmasıdır (uygulama turunun
taşıması gereken kısıt). İkinci güvenilir cihaz yalnız hızlandırıcıdır, kök
değildir. *(Öneriyle aynı yönde.)*

**S4 — Lumos'un kendi kimliği (kurucu eklemesi). → BEŞİNCİ ÖZNE.**
"Lumos ben der" ilkesi varsa Lumos yalnızca agent'ları yöneten soyut bir
gateway olamaz; insan öznesinden ayrı, sürekliliği olan **Lumos öznesi**
bulunmalıdır ve Representative gibi agent'lar onunla aynı şey değildir.
K1'e beşinci satır, K5'e N8/N9 olarak işlendi. Dikkat: bu, S1'de reddedilen
"beşinci özne"den farklı bir şeydir — orada reddedilen **organizasyon**du.

---

## Bu kapı ne zaman "açılmış" sayılır (ADR seviyesinde kabul ölçütü)

1. ✅ S1/S2/S2b/S3 cevaplandı ve belgeye işlendi; kurucu eklemesi S4 (Lumos öznesi) modele girdi.
2. ✅ Karar durumu Accepted'a çekildi; ADR-016'ya karşılıklı referans notu düşüldü ve "Lumos ID = kullanıcı kimliği" cümlesi düzeltildi.
3. ✅ Agent-kimliği ve Lumos-öznesi boşlukları `docs/TECHNICAL_DEBT.md` → **TD-16** olarak kayda geçti (TD-14 `lumos-dosya-akisi-analiz.md`'de panel trash/upload borcuna rezerve).

Üçü tamamlandı: **model kilitlendi (2026-08-17)**. Uygulama (şema, depolama,
kripto, migration, protokol seçimi) bundan sonra bile **otomatik başlamaz** —
FAZ-1 / STOP LIST durumu ayrıca değerlendirilir ve kurucu ayrıca açar.

### Kilitlendikten sonra açık kalanlar (uygulama turuna devredildi)

| Konu | Neden şimdi karar verilmedi |
|------|------------------------------|
| İnsan öznesinin kalıcı adı (S2b) | Kurucu bilinçli erteledi |
| Lumos ID ↔ Trust Engine sınırı | ADR-007: birleşik Trust Engine bugün yok; boşluk kapanmadan sınır yazılamaz |
| "Lumos ben der" ilkesinin kendi kaydı | Bu depoda yazılı karar olarak bulunamadı; hangi belgeye yazılacağı takip işi |
| Kripto/protokol/şema/kurtarma akışı | K6 kapsam dışı; uygulama kapısı açılınca ayrı tur |
