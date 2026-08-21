# ADR-009: Mail Adresi ve Domain Sınır Kararı (Taslak)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / gözlem** — uygulanmamış; kesinleşmiş mimari karar değildir |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-002 (Mail / Inbox Intelligence) |

## Amaç

Lumos mail yeteneklerini **üç ayrı katmanda** netleştirmek:

1. **Mail / Inbox Intelligence** — izinli okuma, sıralama, özetleme (ADR-002 ile hizalı)
2. **Mail gönderme** — kullanıcı onayı + mail sağlayıcı entegrasyonu gerektirir
3. **Domain mail adresi** — kullanıcı/şirket sahipli domain altında mail adresi açma

Bu belge **yalnızca dokümantasyondur**. Public repoda mail için **demo-safe foundation stub** vardır (ADR-002); **canlı SMTP/OAuth prod akışı, DNS değişikliği, domain satın alma, gerçek posta gönderimi veya kullanıcı adına mail hesabı açma uygulanmamıştır**.

## Bağlam

ADR-002, Lumos'un **açık izinle** gelen postayı okuyup önem önceliğine göre sunabileceğini **taslak** düzeyinde kaydeder. ADR-009, mail alanının **gönderme** ve **domain adresi** boyutlarını ayrı sınırlarla tamamlar.

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). Mail okuma, gönderme ve domain adresi konuları bu sözleşmeyle uyumlu olmalıdır: onaysız okuma yok; onaysız gönderim yok; onaysız dış etki yok.

---

## Bugünkü gerçek (açık ifade)

Aşağıdaki ifadeler **mevcut durum** için geçerlidir; abartılı ürün vaadi değildir.

| Yetenek | Bugünkü durum |
|---------|---------------|
| **Lumos kendi başına mail gönderemez** | Prod gönderim altyapısı ve onaylı gönderim akışı **ürün olarak uygulanmamış** |
| **Lumos kendi başına mail hesabı açamaz** | Domain altında mailbox oluşturma, sağlayıcı hesabı açma veya DNS yönetimi **Lumos tarafından otomatik yapılmaz** |
| **Inbox Intelligence (okuma/özet)** | ADR-002 taslak; public demo-safe stub (PR #413–#415); **ürün uygulanmamış** |
| **Domain mail adresi** | Bu ADR'de tanımlanan **hedef sınır**; uygulama yok |

Lumos, kullanıcı adına **sessiz veya otomatik** posta göndermez ve **sessiz veya otomatik** mail hesabı oluşturmaz.

---

## Üç katman ayrımı

### 1. Mail / Inbox Intelligence (ADR-002)

**İzin verilen (taslak hedef):** Kullanıcının **açık izni** ile gelen postayı okumak, sıralamak, özetlemek, önem kategorisi sunmak.

| Eylem | Kural |
|-------|-------|
| Okuma | Açık kullanıcı izni olmadan yapılmaz |
| Sıralama / özet / sınıflandırma | Okuma izni kapsamında; kutuda değişiklik yapmaz |
| Önerilen aksiyon (cevap taslağı vb.) | Simülasyon / önizleme; gerçek gönderim ayrı katman |

Detay: `docs/decisions/ADR-002-mail-inbox-intelligence.md`.

### 2. Mail gönderme

**Ayrı katman;** Inbox Intelligence ile karıştırılmamalıdır.

| Koşul | Açıklama |
|-------|----------|
| Kullanıcı onayı | Her gönderim **açık onay** gerektirir; otomatik gönderim yok |
| Mail sağlayıcı entegrasyonu | Public demo-safe sözleşme/stub; **prod connector private impl bekliyor** |
| Lumos tek başına gönderemez | Altyapı ve entegrasyon olmadan gönderim mümkün değildir |

Gönderim, silme, arşivleme ve kutuda değişiklik yapan tüm adımlar ADR-002 onay tablosu ile uyumludur.

### 3. Domain mail adresi

Kullanıcı veya şirketin **sahip olduğu ve kontrol ettiği** bir domain altında mail adresi tanımlama hedefi.

**Temel kural:** Bir mail adresi yalnızca **Lumos'un veya kullanıcının/şirketin kontrolündeki domain** altında anlamlıdır. Domain kontrolü yoksa o domain altında adres **kullanılamaz**.

---

## Domain ve adres sınırları

### lumos.com örneği

| Senaryo | Sonuç |
|---------|-------|
| `lumos.com` **bizim kontrolümüzde** | Örn. `degetlo@lumos.com` gibi adresler **teknik olarak mümkün** olabilir — domain sahipliği, DNS, mail sağlayıcı ve onay akışı tamamlandığında |
| `lumos.com` **bizim kontrolümüzde değil** | `degetlo@lumos.com` veya `@lumos.com` altındaki **hiçbir adres kullanılamaz**; Lumos bu domain üzerinde mailbox açamaz veya gönderim yapamaz |

Domain sahipliği doğrulanmadan `@lumos.com` adresi **vaat edilmez** ve **kullanılmaz**.

### welockai.com — doğrulanmış durum (2026-08-21)

Bu bölüm önceki hâlinde dört adresi *"hipotez; henüz açılmamış"* diye listeliyordu. Domain artık kontrol altında ve gerçek durum aşağıdadır. **Operasyonel ayrıntı (yönlendirme hedefleri, hesap sahipliği, kural yapılandırması) bu public repoda tutulmaz** — bkz. [`docs/mail-strategy-private-notice.md`](../mail-strategy-private-notice.md).

| Adres | Durum | Not |
|-------|-------|-----|
| `admin@welockai.com` | **Tanımlı** | Cloud Identity kullanıcısı + gelen posta yönlendirmesi; posta kutusu değil |
| `lumos@welockai.com` | **Tanımlı** | Yalnız gelen posta yönlendirmesi — posta kutusu değil |
| `candasoz@welockai.com` | **Tanımlı** | Yalnız gelen posta yönlendirmesi — posta kutusu değil |
| `support@welockai.com` | **Tanımlı değil** | Açılmadı |
| `noreply@welockai.com` | **Tanımlı değil** | Gönderici kimliği olarak kullanılabilmesi için ayrıca outbound mail sağlayıcısı + SPF/DKIM/DMARC gerekir |
| ~~`degetlo@welockai.com`~~ | **Kullanımda değil** | Önceki taslakta örnek olarak geçiyordu; tanımlı bir adres değil |

**Gelen ve giden asimetrisi.** Mevcut yapı yalnız gelen postayı yönlendirir. Domain adına outbound gönderim yeteneği kurulmuş değildir. Bu nedenle `noreply@` gibi gönderim amaçlı bir kimlik, ayrı bir outbound sağlayıcı ve gerekli DNS doğrulamaları kurulmadan kullanılamaz.

Gönderim zinciri §Gerekli altyapı'da tanımlıdır ve **gelen posta yolunu değiştirmeden** kurulabilir; ikisi ayrı katmandır.

Lumos bu adresleri **kendisi açmaz** ve bu domain üzerinde **DNS veya sağlayıcı işlemi yapmaz**; yukarıdaki yapı kurucu tarafından elle kurulmuştur.

---

## Gerekli altyapı (gelecek uygulama ön koşulları)

Domain mail adresi veya güvenilir gönderim için aşağıdaki altyapı **önce** tanımlanmalıdır. Bu ADR altyapıyı **kurmaz**; yalnızca karar sınırını kaydeder.

### Domain sahipliği

- Domain'in **kimde** olduğu (kullanıcı, şirket, registrar) net kayıt altında olmalıdır.
- Lumos, sahipliği doğrulanmamış domain üzerinde adres veya mailbox **oluşturmaz**.
- Domain transferi veya satın alma bu ADR kapsamında **yapılmaz**.

### DNS ayarları

- MX, A/AAAA, CNAME ve sağlayıcıya özgü kayıtlar **kontrol edilen domain** üzerinde yapılır.
- DNS değişikliği Lumos tarafından **otomatik veya onaysız yapılmaz**.
- Gerçek DNS yönetimi ve secret'lar **private/professional katmanda** kalır (aşağıda).

### Mail sağlayıcı

- Gmail Workspace, Microsoft 365, Zoho, transactional provider vb. seçimi **ayrı karar** gerektirir.
- Sağlayıcı API anahtarları, OAuth client secret'ları ve SMTP kimlik bilgileri **public repo'da olmaz**.
- Lumos bugün **hiçbir mail sağlayıcısına bağlı değildir**.

### SPF / DKIM / DMARC

| Mekanizma | Amaç (kısa) |
|-----------|-------------|
| **SPF** | Hangi sunucuların domain adına gönderebileceğini DNS'te beyan |
| **DKIM** | Mesaj bütünlüğü ve domain imzası |
| **DMARC** | SPF/DKIM uyumu ve spoofing politikas |

Güvenilir gönderim ve teslim edilebilirlik için bu kayıtlar **domain kontrolü + sağlayıcı kurulumu** sonrası zorunlu kabul edilir. Lumos bu kayıtları **bugün yönetmez**.

### Gönderim limitleri ve güvenlik

- Sağlayıcı kotası, rate limit ve bounce/complaint yönetimi tanımlanmalıdır.
- Toplu veya otomatik gönderim **kullanıcı onayı ve politika** ile sınırlı olmalıdır.
- Phishing, spoofing ve yetkisiz gönderim riski için firewall/trust/onay katmanları (ADR-006, ADR-007, `lumos-karar-sozlesmesi`) bypass edilmemelidir.

### Kullanıcı onay akışı

Mail gönderimi ve kutuda değişiklik yapan eylemler için **ayrı, açık onay** zorunludur:

1. Kullanıcıya ne gönderileceği, hangi adresten ve kime gideceği **açıkça** gösterilir.
2. Kullanıcı **bilinçli onay** verir; varsayılan kapalı kalır.
3. Onay geri alınabilir olmalıdır.
4. Domain adresi açma veya DNS değişikliği **ayrı onay** gerektirir; Lumos otomatik açmaz.

Inbox okuma izni (ADR-002) ile gönderim onayı **birleştirilmemelidir**; ayrı akışlar hedeflenir.

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`).

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Bu ADR ve ADR-002 (karar, sınır, taslak hedef) | Gerçek mailbox ve posta kutusu erişimi |
| Üç katman ayrımı (okuma / gönderme / domain adresi) | Mail sağlayıcı API anahtarları |
| Domain/adres **örnekleri** (welockai.com, lumos.com senaryoları) | DNS secret'ları ve zone yönetim kimlik bilgileri |
| SPF/DKIM/DMARC **ilkeleri** (dokümantasyon) | OAuth token'ları, refresh token'lar |
| Onay akışı **tasarım hedefi** | SMTP kullanıcı adı / parola / credential |
| "Bugün gönderemez / hesap açamaz" dürüst ifadesi | Prod mail connector / canlı OAuth (private katman) |
| Demo-safe stub veya placeholder referansı | Operasyonel mail altyapısı ve prod gönderim |

Karar belgesi public'te kalabilir; **gerçek posta, sağlayıcı anahtarları, DNS secret'ları ve OAuth/SMTP kimlik bilgileri private katmanda** tutulur.

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent, kilit ve kalıcı silme alanları **dokunulmaz**; bu ADR o sınırları gevşetmez.

---

## Bilinçli sınırlar (bu ADR kapsamında yapılmaz)

| Yapılmaması gereken | Gerekçe |
|---------------------|---------|
| Kod / API / panel UI | Bu tur yalnızca ADR |
| Mail sağlayıcı entegrasyonu | Ayrı checkpoint; onay + altyapı şart |
| SMTP / prod mail connector | Ürün uygulanmamış; public foundation stub only |
| Domain satın alma veya transfer | Kullanıcı/şirket işlemi; Lumos otomatik yapmaz |
| DNS değişikliği | Kontrollü, onaylı, private katman |
| Gerçek mail gönderimi | Onay + sağlayıcı olmadan mümkün değil |
| Kullanıcı adına mail hesabı açma | Lumos bugün hesap açamaz |
| `@lumos.com` kontrolsüz kullanım | Domain sahipliği yoksa adres kullanılamaz |
| Abartılı ürün vaadi | Teslim tarihi veya tam kapsam taahhüdü yok |

---

## ADR-002 ile ilişki

| Konu | ADR-002 | ADR-009 |
|------|---------|---------|
| Okuma / özet / sıralama | Ana konu | Katman 1 referansı |
| Gönderim onayı | Tablo kuralı | Katman 2 detayı + altyapı ön koşulu |
| Domain / `@` adres | Kapsam dışı | Katman 3 — bu ADR'nin odağı |
| Prod mail connector | Public stub only | Private impl (aynı sınır) |

ADR-009, ADR-002'yi **genişletmez**; gönderme ve domain adresi sınırlarını **ayrı katman** olarak tamamlar.

---

## Sonuç (geçici)

Lumos mail yetenekleri **üç ayrı katmanda** düşünülmelidir: (1) izinli Inbox Intelligence, (2) onaylı gönderim + sağlayıcı entegrasyonu, (3) kontrol altındaki domain'de mail adresi. **Bugün Lumos kendi başına mail gönderemez ve mail hesabı açamaz.** `degetlo@lumos.com` yalnızca `lumos.com` kontrolümüzdeyse anlamlıdır; değilse kullanılamaz. Kontrol altındaki domain örneği `welockai.com` ise `lumos@`, `support@`, `noreply@`, `degetlo@` gibi adresler **taslak örnektir** — uygulama, DNS, sağlayıcı ve onay akışı olmadan açılmaz.

## Sonraki gözden geçirme

- Mail gönderim onay akışı için ayrı checkpoint veya ADR eki
- Domain sahipliği doğrulama modeli (kullanıcı/şirket vs Lumos)
- ADR-002 izin akışı ile gönderim onayının ayrıştırılması
- Private katmanda sağlayıcı seçimi ve SPF/DKIM/DMARC runbook'u
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
