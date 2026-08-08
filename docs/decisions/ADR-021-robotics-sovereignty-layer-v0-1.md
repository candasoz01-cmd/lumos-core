# ADR-021 — Lumos Robotics Sovereignty Layer v0.1

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-08)** |
| Uygulama durumu | **Şartname + çevrimdışı simülasyon prototipi** |
| Çalışma adı | Lumos Robotics Sovereignty Layer / Lumos Robot Egemenlik Katmanı |
| Kapsam | Üreticiden bağımsız robot güvenliği ve yerel sahip denetimi |
| Kapsam dışı | Gerçek robot kontrolü, firmware değiştirme, üretici SDK entegrasyonu, sertifikasyon iddiası |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md), [`ROADMAP.md`](../ROADMAP.md), ADR-007, ADR-012, ADR-015, ADR-017 |

## 1. Amaç ve dürüst durum

Lumos robot üreticisi değildir. Bu katman; robotun yetkilerini, veri akışını,
güncellemesini ve güvenli duruşunu yerel sahibin denetimine bağlayan üreticiden
bağımsız bir uyumluluk sözleşmesidir.

v0.1 bugün yalnız **KARAR + KOD** seviyesindedir: normatif şartname ve gerçek
donanım kullanmayan simülasyon vardır. Üretici erişimi, donanım belgeleri,
bağımsız laboratuvar ve fiziksel test olmadan bir robot için **CANLI**,
**DOĞRULANDI** veya **Lumos uyumlu** denemez.

## 2. Güvenlik hedefleri

Bir uyumlu robot:

1. İnternet ve üretici bulutu olmadan temel güvenli işlevlerini sürdürebilir.
2. Kamera, mikrofon, konum, telemetri ve hareket verisini açık yerel yetki
   olmadan robotun güven sınırı dışına çıkarmaz.
3. Üretici, servis hesabı veya başka bir uzak aktörden gizli komut kabul etmez;
   üretici kill-switch'i taşımaz.
4. Her eylemi Lumos'un yerel, varsayılan-red yetki sözleşmesinden geçirir.
5. Firmware/yazılım güncellemesini yalnız yerel sahibin güvenilir köküne bağlı
   geçerli imza ve açık kurulum kararıyla kabul eder.
6. Kritik kararları sıralı, hash-zincirli ve dışa aktarılabilir audit kaydına
   yazar. v0.1'in hash zinciri **kurcalamaya dayanıklı kanıt değildir**;
   değişikliği görünür kılan prototip mekanizmasıdır.
7. Ağdan, işletim sisteminden ve Lumos sürecinden bağımsız fiziksel acil
   durdurma devresine sahiptir.
8. Lumos heartbeat'i kaybolduğunda veya politika doğrulanamadığında enerjiyi
   tehlikesiz biçimde azaltır ve tanımlı güvenli duruşa geçer.

## 3. Tehdit modeli

### Korunan varlıklar

- insan yaşamı ve fiziksel çevre;
- yerel sahibin karar yetkisi ve kontrol anahtarı;
- sensör, konum, hareket, biyometrik ve ortam verileri;
- aktüatör yetkileri, firmware bütünlüğü ve audit kaydı.

### Tehdit aktörleri

- ele geçirilmiş üretici bulutu veya servis hesabı;
- kötü niyetli/yanlış yapılandırılmış uzak operatör;
- tedarik zincirine eklenmiş gizli erişim veya kill-switch;
- ağ üzerindeki saldırgan;
- yetkisini aşan yerel uygulama veya Lumos bileşeni;
- eski, replay edilmiş ya da yanlış imzalı güncelleme paketi.

### Fail-closed varsayımı

Kimlik, imza, yetki, zaman, audit yazımı veya Lumos heartbeat'i doğrulanamazsa
hareket/aktüatör isteği reddedilir. Güvenli duruşun kendisi ağ veya bulut onayı
beklemez. Acil durdurma, yazılım politikasından daha yüksek önceliklidir.

## 4. Normatif gereksinimler

`MUST`, `MUST NOT`, `SHOULD` ve `MAY` sözcükleri v0.1 uyumluluk dilidir.

### RSL-01 — Çevrimdışı çalışma

- Robot temel güvenli işlevler ve güvenli duruş için üretici bulutuna **MUST
  NOT** bağımlı olmalıdır.
- Yerel başlangıç, kimlik doğrulama ve politika yükleme internetsiz **MUST**
  çalışmalıdır.
- Bulut erişimi kesildiğinde robot yetki genişletmemeli; aynı veya daha dar
  yetkiyle devam etmeli ya da güvenli durmalıdır.

### RSL-02 — Veri çıkışı ve mahremiyet

- Sensör verisi varsayılan olarak cihaz içinde kalmalıdır.
- Her dış aktarım; veri sınıfı, amaç, hedef, süre ve sahibin açık onayını
  taşıyan yerel imzalı izin belgesine bağlı olmalıdır.
- Üretici telemetrisi opt-in olsa bile kapatılabilir ve ağ seviyesinde
  doğrulanabilir olmalıdır. Gizli veya belgelenmemiş endpoint **MUST NOT**
  bulunmalıdır.

### RSL-03 — Komut kaynağı ve gizli erişim

- Komutlar doğrulanmış yerel sahip/Lumos kimliğine bağlanmalıdır.
- Üretici, bakım hesabı veya uzak servis varsayılan ayrıcalık elde etmemelidir.
- Belgelenmemiş hesap, port, debug arayüzü, sabit anahtar ve üretici
  kill-switch'i **MUST NOT** bulunmalıdır.
- Uzak bakım gerekirse süreli, amaç-kısıtlı, yerel olarak görünür ve sahibin
  iptal edebildiği yetki belgesi gerektirir.

### RSL-04 — Lumos yetki matrisi

- Her sensör ve aktüatör ayrı kabiliyet olarak tanımlanmalıdır.
- Bilinmeyen komut/kabiliyet varsayılan olarak reddedilmelidir.
- Hız, kuvvet, çalışma alanı, süre ve insan yakınlığı gibi fiziksel sınırlar
  üretici adaptörünün altında bağımsız güvenlik denetleyicisinde korunmalıdır.
- Lumos hiçbir zaman fiziksel güvenlik denetleyicisini devre dışı bırakamaz.

### RSL-05 — Yerel imzalı güncelleme

- Güven kökü yerel sahibin kontrolünde olmalıdır; üretici tek başına kurulum
  yetkisine sahip olmamalıdır.
- Paket imzası, sürüm monotonluğu, içerik özeti, donanım hedefi ve geri dönüş
  politikası kurulumdan önce doğrulanmalıdır.
- İmza/metadata hatasında güncelleme reddedilmeli ve çalışan son güvenli sürüm
  korunmalıdır.

### RSL-06 — Audit ve kanıt

- Komut kabul/redleri, yetki değişiklikleri, veri çıkışları, güncelleme
  kararları, heartbeat kaybı ve acil durdurma kaydedilmelidir.
- Kayıtlar monoton sıra, güvenilir zaman kaynağı ve önceki kayıt özetiyle
  zincirlenmelidir.
- Üretim profili append-only/WORM veya donanım destekli imzalı günlük
  kullanmalıdır; salt hash zinciri değişmezlik iddiası için yeterli değildir.
- Ham kamera/mikrofon içeriği audit kaydına yazılmamalıdır.

### RSL-07 — Fiziksel acil durdurma

- E-stop fiziksel olarak erişilebilir, ağdan bağımsız ve enerji kesme/güvenli
  tork durumuna doğrudan bağlı olmalıdır.
- E-stop sonrası yeniden başlatma otomatik olmamalı; fiziksel reset ve yerel
  yeniden yetkilendirme gerektirmelidir.

### RSL-08 — Lumos kaybında güvenli duruş

- Robot zaman sınırlı yerel heartbeat izlemelidir.
- Süre dolunca yeni hareket reddedilmeli, mevcut hareket kontrollü biçimde
  sonlandırılmalı ve tanımlı güvenli duruş uygulanmalıdır.
- Heartbeat geri gelse bile hareket kendiliğinden devam etmemelidir.

## 5. Üretici uyumluluk arayüzü

Üretici ticari sırlarını açmak zorunda değildir; aşağıdaki denetlenebilir
sınırları sağlamalıdır:

| Arayüz | Asgari sözleşme |
|---|---|
| `CapabilityManifest` | Sensör/aktüatör kimliği, limitler, risk sınıfı, varsayılan durum |
| `LocalCommandPort` | Yerel kimlik doğrulama, replay koruması, süreli komut, varsayılan-red |
| `NetworkManifest` | Tüm endpoint/protokoller, kapatma anahtarı, paket yakalama testi |
| `UpdateVerifier` | Yerel güven kökü, imza/rollback doğrulaması, atomik geri dönüş |
| `SafetyController` | Lumos'tan bağımsız limitler, heartbeat ve güvenli duruş |
| `PhysicalEStop` | Ağ/yazılım dışı kesme, manuel reset, durum okunabilirliği |
| `AuditExporter` | Sıralı, zincirli/imzalı, kişisel veri minimizasyonlu kayıt |
| `AttestationReport` | Firmware, boot zinciri, debug durumu ve etkin politika özeti |

## 6. v0.1 uyumluluk test profili

Bir model ancak aşağıdaki kanıtların tamamıyla aday olabilir:

1. **Offline boot:** DNS/internet/üretici bulutu kapalıyken yerel başlangıç ve
   güvenli duruş.
2. **Egress deny:** Paket yakalamada onaysız sensör/telemetri çıkışı olmaması.
3. **Remote command deny:** Üretici hesabı, uzak ağ ve replay komutlarının
   reddi.
4. **Capability deny:** Tanımsız veya kapsam dışı aktüatör komutunun reddi.
5. **Update gate:** Geçersiz, eski ve yanlış hedefli paketlerin reddi; yalnız
   yerel kök + açık onayla kabul.
6. **Audit tamlığı:** Kritik olayların sırası ve zincir doğrulaması; kontrollü
   kurcalama testinde bozulmanın görünmesi.
7. **E-stop:** Ağ ve ana işlem kapalıyken fiziksel durdurma; otomatik yeniden
   hareket olmaması.
8. **Lumos loss:** Heartbeat süresi sonunda ölçülen durma süresinin risk
   analizindeki üst sınırı aşmaması.

Testler bağımsız laboratuvarda, model/firmware sürümüne bağlı ve yeniden
üretilebilir olmalıdır. Geçme sonucu bütün üretici ailesine genellenemez.

## 7. Simülasyon prototipi

`src/robotics_sovereignty/simulator.py` şu davranışları kanıtlayan saf-Python
bir referans modeldir:

- bilinmeyen/uzak/üretici komutunu varsayılan-red;
- yalnız yetkili kabiliyetle hareket;
- varsayılan ağ kilidi ve denetlenebilir bağlantı kesme olayı;
- sensör çıkışında yerel imza + açık onay + hedef allowlist;
- firmware güncellemesinde yerel imza + açık onay;
- fiziksel E-stop ve Lumos kaybında güvenli duruş;
- hash-zincirli, kurcalamayı görünür kılan audit kaydı.

Bu model robot sürücüsü, güvenli gerçek-zaman kontrolörü, kriptografik anahtar
yönetimi veya donanım attestation'ı değildir.

## 8. Sonraki kapılar

1. Simülasyon senaryolarını bağımsız saldırı/test matrisiyle genişletmek.
2. Açık API'li küçük robot seçimi için güvenlik ve tedarik değerlendirmesi.
3. Ayrı kullanıcı kararıyla üretici adaptörü ve fiziksel test laboratuvarı.
4. Kanıtlar tamamlanınca üretici görüşme paketi: şartname, test raporu,
   uyumluluk arayüzü ve başarısızlık kayıtları.

## Sonuç

Lumos'un teklif ettiği şey üretici yazılımını sahiplenmek değil; yerel sahibin
son kararını teknik olarak uygulanabilir ve denetlenebilir kılan ortak bir
uyumluluk sınırıdır. v0.1 standardı fail-closed çalışır ve donanım kanıtı
olmadan uyumluluk iddiasına izin vermez.
