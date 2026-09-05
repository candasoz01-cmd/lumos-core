# Wall yüzey taşınabilirliği sözleşmesi — v1

| Alan | Değer |
| --- | --- |
| Durum | **TASARIM** — bu dilimde kod yok. Wall okuma ucu bugün **mevcut değil** (§3) |
| Normatiflik | §4–§7 **gelecekteki** yüzeyi bağlar; mevcut davranışı tarif etmez |
| Kapsam | Wall durumuna araç içinden erişim: kaynak gerçeği, kimlik, okuma/yazma ayrımı, tek-host sınırı, adaptör sınırları |
| Üst ilişki | [panel-tasks-auth-v1](panel-tasks-auth-v1.md) · [api-surface-v1](api-surface-v1.md) · [task-claim-v1](task-claim-v1.md) · [agent-status-v2](agent-status-v2.md) · [agent-wall-observation-v1](agent-wall-observation-v1.md) · [single-reader-gateway-v1](single-reader-gateway-v1.md) |
| Karar kaydı | ADR **yok**. Numara tahsisi kayıtlı olmadığı için (TECHNICAL_DEBT TD-31 / TD-32) yeni ADR açılmadı; tahsis temizlenince bu belge karar kaydına bağlanır |
| Kaynak gerçeği | Sözleşme ile kod ayrışırsa **kod esastır**; ayrışma borç sayılır ([api-surface-v1](api-surface-v1.md) kuralı) |
| Bu dilimin dışı | Araç adaptörleri, UI, runtime değişikliği, çok makine |

Kullanıcı hangi araçta çalışıyorsa Wall'a oradan ulaşabilmelidir. Bu belge o
erişimin **nasıl** kurulacağını değil, **neyin sözleşme olduğunu** sabitler.

## 1. Karar

**Lumos Agent Wall tek mantıksal yüzeydir.** Desteklenen araçlar kendi
arayüzlerinden aynı Wall durumuna erişir: aynı görevler, aynı claim'ler, aynı
ajan durumları, aynı gözlem kayıtları.

Araçlar **ayrı state veya ayrı yönetim paneli üretmez.** Amaç panelin birden
çok kopyası değil, tek yüzeye birden çok erişim noktasıdır. Aksi durumda
"Cursor'daki gerçek başka, Claude'daki başka" sorunu doğar; bu, sözleşmenin
önlemek için var olduğu tek şeydir.

## 2. Sözleşme yüzeyi: HTTP API

**Sözleşme HTTP API'dir. Dosya düzeni implementation detail'dir.**

Aşağıdakiler hiçbir araç için entegrasyon kontratı **değildir**; adaptörler
tarafından okunmaz, yazılmaz, kilitlenmez, izlenmez:

| Dosya | Sahibi sözleşme |
| --- | --- |
| `claims.json` | [task-claim-v1](task-claim-v1.md) |
| `agent_status_*.json` | [agent-status-v2](agent-status-v2.md) |
| `claim_events.jsonl` | [task-claim-v1](task-claim-v1.md) |
| `.lumos/logs/wall_observations.jsonl` | [agent-wall-observation-v1](agent-wall-observation-v1.md) |
| `consent.json` | §5.3 |

**Gerekçe ölçülmüştür, varsayım değildir.** `TaskClaimStore.list_claims()` bir
okuma değildir: `_locked_state()` başarılı çıkışta her durumda `_write_state()`
ve `_flush_audit()` çağırır ve süresi boyunca **exclusive `flock`** tutar
(`src/lumos_board/task_claim.py:629`, `638`, `641`, `652`). Yani "yalnız
okuyacağım" diyen bir çağıran hem `claims.json`'a yazar hem claim kapısının
kilidini tutar. Bu, gözlem katmanı yazılırken keşfedildi (`#832`) ve
düzeltilmesi birkaç tur aldı. Dosya veya kütüphane düzeyinde entegre olan her
araç bu tuzağı bağımsız olarak yeniden kurar; ayrıca TTL, expiry ve consent
semantiğini kendi başına yeniden yorumlar. Tek sözleşme yüzeyi tam olarak bunu
engellemek içindir.

## 3. Bugün ne var, ne yok

**Bu belge mevcut davranışı sabitlemiyor.** Aşağıdaki tablo bugünü ölçer;
§4–§7 ise henüz yazılmamış bir yüzeyin normatif sınırlarıdır. Yüzey
yazıldığında bu belge koda karşı yeniden doğrulanır ve ayrışma borç sayılır.

Ölçüm anı: `main` = `ed9ca2f`, dosya `panel/scripts/panel_tasks_server.py`.
Satır numaraları o commit'e aittir; kod değişince numaralar değil, **iddialar**
yeniden doğrulanmalıdır.

| Parça | Durum | Kanıt |
| --- | --- | --- |
| Tasks REST + zorunlu jeton | **var** | `_require_auth` tanımı `844`; çağrı `1067` (GET), `1127` (PUT), `1190` (POST) |
| Origin kapısı (TD-24 Faz-1) | **var** | `895` (OPTIONS), `1058`, `1124`, `1187` |
| Kimliksiz kalan yollar | yalnız statik | `1062`: `/`, `/index.html`, `/js/`, `/css/` — veri ucu değil; `/tasks.json` jetonun **arkasında** |
| Loopback bağlama | **var** | `1729`: `LUMOS_PANEL_TASKS_HOST`, varsayılan `127.0.0.1` |
| Wall okuma ucu (claim / ajan durumu / gözlem) | **YOK** | Dosyada `claim`, `agent_status`, `wall_observ` hiç geçmiyor |

Yani Wall durumu bugün HTTP üzerinden **hiç** sunulmuyor; tek erişim yolu
dosya sistemidir — ve §2 tam olarak o yolu kapatır. Bu sözleşmenin ilk somut
sonucu şudur: **araç adaptörü yazılmadan önce Wall okuma ucu yazılmalıdır.**
Ters sıra, §2'nin yasakladığı entegrasyonu üretir.

## 4. Kimlik

Kimlik mevcut TD-24 hattına oturur. **Yeni paralel kimlik mekanizması icat
edilmez.** Geçerli olan [panel-tasks-auth-v1](panel-tasks-auth-v1.md)'dir:

- Taşıma `X-Kando-Token` veya `Authorization: Bearer`; gövdede ve sorgu
  dizesinde token yok.
- Fail-closed: yapılandırılmış sır yoksa `401 missing_secret`. "Sır yoksa
  açık" yok.
- Diskte ham sır değil, SHA-256; karşılaştırma `hmac.compare_digest`.
- Origin kapısı önce çalışır: yabancı Origin + geçerli jeton yine
  `403 origin_not_allowed`.

Adaptör kendi jeton deposunu, kendi oturum kavramını veya kendi yenileme
akışını **üretmez**; kütüphanenin mint ettiği oturum/servis jetonunu taşır.

## 5. Okuma ve yazma ayrık yüzeylerdir

| Yüzey | İçerik | Kural |
| --- | --- | --- |
| **Okuma** | Wall görünümü: görevler, claim'ler, ajan durumları, gözlem kayıtları | Yan etkisiz (§5.1). `GET`, `Cache-Control: no-store` |
| **Yazma** | claim alma, heartbeat, bırakma, tamamlama, consent verme | Ayrı, dar ve daha sıkı yetki kapısı |

**İlk dilimde araç adaptörleri yalnız okuma alır.** Yazma yüzeyi bu
sözleşmeyle araçlara açılmaz. Her yeni yazma noktası confused-deputy yüzeyini
büyütür; yazma yüzeyinin genişlemesi ayrı karar ister, adaptör eklemekle
gelmez.

### 5.1 "Yan etkisiz" ne demek — ve ne demek değil

Wall okuma ucu:

- Wall durum dosyalarına **yazmaz**,
- exclusive kilit **almaz**,
- TTL/expiry süpürmesi **tetiklemez** (§2'deki ölçüm bu maddenin sebebidir).

Bu, "her `GET` yan etkisizdir" demek **değildir** ve mevcut kodda öyle de
değildir: `GET /lumos-read-state` her çağrıda `set_panel_api_health()` üzerinden
`save_context()` çağırır, yani diske yazar
(`panel_tasks_server.py:917`, `src/core/context_store.py:140`). Bu uç kendi
işini yapıyor ve bu sözleşme onu değiştirmiyor; ama **Wall okuma ucu o deseni
kopyalamaz**. Sağlık/telemetri yazımı okuma ucunun içine gömülmez.

### 5.2 Tek okuyucu sınırıyla ilişki

Wall okuma ucu [single-reader-gateway-v1](single-reader-gateway-v1.md)'in
kullanıcıya dönük olay teslimini **değiştirmez**: board durumunu gösterir,
olay acknowledge etmez, reader lease tüketmez, lease almaz. Tek okuyucu sınırı
orada geçerli kalır; buradaki çok erişim noktası o lease'i çoğaltmaz.

Bir araç kullanıcıya dönük özet teslimi yapmak isterse bu sözleşme onu
kapsamaz — o, tek okuyucu kapısının konusudur.

### 5.3 Consent bu sözleşmeyle çoğalmaz

Bugün consent **host düzeyinde geneldir**: `POST /lumos-consent` bir
passphrase karşılığında `consent.json` dosyasına `{"granted": true}` yazar; bu
kayıt istemciye, oturuma veya araca göre kapsamlanmaz
(`panel_tasks_server.py:1279`). Yani bir araçtan verilen izin, o hosttaki
**tüm** erişim noktaları için geçerli olur.

Bu yüzden:

1. Consent verme bir **yazma** işlemidir; ilk dilimde adaptörlere açılmaz.
2. Erişim noktası çoğaltmak izin çoğaltmaz ve izin **istemez**: adaptör kendi
   consent kavramını, kendi "kilit aç" akışını veya kendi kapsamını üretmez.
3. Consent'in bugün araç bazında kapsamlanamadığı **bilinen sınırdır**.
   Araç bazlı izin isteniyorsa bu, consent modelinin değişmesini gerektirir;
   adaptör katmanında çözülemez ve bu belge onu çözmüş saymaz.

## 6. Tek host sınırı — şimdilik

Bugün tek state konumu ve tek makine vardır: durum dosya sistemindedir,
sunucu varsayılan olarak `127.0.0.1`'e bağlanır (§3).

- **Bu sözleşmenin kapsamı tek hosttur.** "Aynı makinede farklı araçlar" evet;
  "farklı makinelerde farklı araçlar" **hayır**.
- Bu sınır bugünkü kurulumdan gelir; **kalıcı bir mimari tercih değildir.**
  Kaldırılabilir — ama bu belgeye dayanılarak değil, ayrı bir kararla.
- **Bu belge dağıtık state için hiçbir taahhüt vermez.** Çok makine
  senaryosunda "tek mantıksal yüzey" ya paylaşılan bir dosya sistemi ya da
  gerçek bir servis gerektirir; ikisi de adaptör işi değildir ve buradaki
  hiçbir madde onları önceden onaylamış sayılmaz.
- Loopback dışına bağlama bu sözleşmenin konusu değildir; ayrı güvenlik
  kararıdır.

## 7. Adaptör sınırları — MUST NOT

Adaptör = bir aracın (Cursor, Claude, masaüstü istemcisi, başka bir IDE) Wall'a
bakan ince erişim katmanı.

1. Adaptör **yalnız HTTP sözleşmesini tüketir.** Aşağıdakilerin hepsi
   yasaktır ve yasak **okuma için de geçerlidir**:
   - Wall durum dosyalarını doğrudan açmak (§2 tablosu),
   - `lumos_board`, `TaskClaimStore` veya eşdeğeri iç modülleri import edip
     çağırmak,
   - aynı işi yapan bir CLI'yi veya betiği subprocess ile çağırmak,
   - dosya sistemi izleyicisiyle (`watch`/`inotify`/`FSEvents`) durum
     dosyalarını gözetlemek,
   - `.lumos/` altını taramak veya oradan türetilmiş ikinci bir kopya tutmak.
2. Adaptör **kaynak gerçeği tutmaz.** Önbellek tutabilir; çakışmada sunucu
   kazanır ve önbellek kanıt olarak gösterilemez.
3. Adaptör **yetki üretmez**, kendi kimlik mekanizmasını icat etmez (§4).
4. Adaptör Wall semantiğini — TTL, expiry, çakışma, sahiplik — **yeniden
   yorumlamaz**; sunucunun döndürdüğünü gösterir.
5. Adaptör gözlem güncesine **yazmaz**. O kaydın tek yazarı gözlemcidir
   ([agent-wall-observation-v1](agent-wall-observation-v1.md)).

Bir adaptörün ihtiyacı HTTP sözleşmesinde yoksa, doğru cevap dosyaya uzanmak
değil **sözleşmeye uç eklemektir**.

## 8. Garanti edilmeyenler

- **Eşzamanlılık garanti edilmez.** İki araçta aynı anda görülen durum birebir
  aynı olmayabilir; okuma bir anlık görüntüdür.
- **Bu katman kimlik doğrulamaz.** Claim kimliği hâlâ kendi beyanıdır (TD-10);
  bu sözleşme onu düzeltmez.
- **Bu katman bir yetki sınırı değildir.** Erişim noktası çoğaltmak yetki
  çoğaltmaz: bir araç, taşıdığı jetonun verdiğinden fazlasını göremez ve
  yapamaz.
- **Consent araç bazında kapsamlanmaz** (§5.3). Bu bilinen sınırdır, çözülmüş
  değildir.
- **Yerel ayrıcalıklı süreç bu kapıyı atlar.** Dosya sistemine doğrudan
  erişebilen bir süreç HTTP kapısının dışındadır; sözleşme tarayıcı ve araç
  istemcileri içindir, cihaz düzeyi bir sınır değildir.
