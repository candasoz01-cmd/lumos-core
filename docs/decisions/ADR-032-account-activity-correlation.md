# ADR-032 — Account Activity Correlation / Security Evidence Correlation

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-09-04)** — kurucu, chat kararı |
| Uygulama durumu | **KARAR + KOD** — yerel çekirdek ve test; canlı cihaz yayını, mail ingest ve panel yok |
| Çalışma adı | Account Activity Correlation (AAC) / Security Evidence Correlation |
| Kapsam | Üçüncü taraf güvenlik uyarısını, kullanıcının izin verdiği doğrulanabilir cihaz/oturum kanıtıyla eşleştirmek |
| Kapsam dışı | Activity tracking, tarayıcı geçmişi, parola/içerik, düz metin IP, yeni panel sayfası, mail ürünü, otomatik hesap kilidi |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md), [`ROADMAP.md`](../ROADMAP.md), ADR-012, ADR-024, SEC-001/SEC-010 |
| Sözleşme | [`account-activity-correlation-v1.md`](../contracts/account-activity-correlation-v1.md) |
| Merge kapısı | Security / privacy. ADR-028 standing hattı **yok**. İnsan onayı şart |

## 1. Amaç ve dürüst durum

Kullanıcı bir servisten “yeni IP / yeni giriş” uyarısı aldığında Lumos’un
cevaplaması gereken soru “ben Grok’a 2 Eylül’de girdim mi?” değil; **“bu
uyarı, benim kayıtlı cihaz/oturum kanıtımla örtüşüyor mu?”** sorusudur.

Bu katman kullanıcıyı izlemez. Amaç, üçüncü taraf güvenlik uyarılarını
kullanıcının kendi doğrulanabilir cihaz ve oturum kanıtlarıyla eşleştirip
**muhtemelen bana ait / belirsiz / şüpheli** sonucunu üretmektir.

v0.1 bugün yalnız **KARAR + KOD** seviyesindedir: yerel çekirdek ve test
vardır. iOS/cihaz yayını, mail gövdesi okuma, panel Denetim merceği ve canlı
hesap eylemi **yoktur**. Bunlar olmadan özellik **CANLI** veya **DOĞRULANDI**
denemez.

## 2. Bu nedir / bu ne değildir

| Bu | Bu değil |
| --- | --- |
| Privacy-preserving güvenlik kanıtı korelasyonu | Activity tracking / tarama günlüğü |
| Minimal olay özeti (servis, zaman, cihaz kimliği, oturum türü, ağ sınıfı) | Raw browser history, URL, başlık, içerik |
| Kayıtlı cihaz anahtarı / attestation referansı | “iPhone 15” string’ini kimlik saymak |
| `owner_match` / `likely_owner` / `unknown` / `suspicious` | “Bu kesin sendin” |
| Ayrı kaynaklar + açıklanabilir kanıt zinciri | Tek skor, gizli gerekçe |
| İnsan onaylı eylem | Mail uyarısından otomatik şifre değiştirme / oturum kapatma |

## 3. Tehdit modeli

### Korunan varlıklar

- kullanıcının hesap oturumları ve “bu giriş bana mı ait?” kararı;
- cihaz kimliği ve attestation referansı;
- gereksiz kişisel verinin (geçmiş, içerik, düz IP) toplanmaması.

### Tehdit aktörleri

- hesabı ele geçiren üçüncü kişi (gerçek yeni giriş);
- sahte veya gecikmiş güvenlik e-postası;
- etiket sahteciliği (“iPhone 15” yazarak sahip gibi görünmek);
- tarama geçmişini toplayan aşırı geniş logger;
- uyarıyı sessizce hesaba müdahaleye çeviren otomasyon.

### Fail-closed varsayımı

Kayıt izni yoksa, cihaz Lumos kaydına bağlı değilse veya çoklu sinyal
yoksa olumlu sahip sonucu **üretilmez**. Belirsizlik `unknown`, eşleşmeyen
yeni-giriş uyarısı `suspicious` olur. Olumlu sonuç bile kesin kimlik hükmü
değildir.

## 4. Normatif gereksinimler

`MUST`, `MUST NOT`, `SHOULD` ve `MAY` sözcükleri v0.1 uyumluluk dilidir.

### AAC-01 — Minimal metadata

- Tutulabilecek alanlar **MUST** yalnız şunlar olsun: `service_id`, zaman,
  kayıtlı `device_id`, oturum türü, ağ sınıfı, isteğe bağlı ağ parmak izi
  (hash), isteğe bağlı `attestation_ref`.
- Raw browser history, URL, sayfa başlığı, mesaj/içerik, parola, çerez ve
  token **MUST NOT** yazılsın.

### AAC-02 — Cihaz kimliği

- Görünen etiket (`iPhone 15`) kimlik **MUST NOT** sayılsın.
- Olay, Lumos’un bildiği cihaz kaydına (`device_id` = public key özeti,
  `public_key_fingerprint`, mümkünse `attestation_ref`) **MUST** bağlansın.
- Kayıtsız veya salt-etiket cihaz **MUST** reddedilsin.

### AAC-03 — Ağ verisi

- Düz metin IP **MUST NOT** saklansın.
- Gerekirse tuzlu hash veya sınıf karşılaştırması **MAY** tutulur.
- Korelasyon sonucu yalnız `same_network` / `different_network` /
  `vpn_possible` / `unknown` **MUST** olsun.

### AAC-04 — Kesin hüküm yasağı

- Seviyeler **MUST** `owner_match`, `likely_owner`, `unknown`,
  `suspicious` olsun.
- Kullanıcıya “bu kesin sendin” **MUST NOT** denmesin. `owner_match`
  bile “kesin hüküm değildir” taşır.

### AAC-05 — Ayrı kaynaklar

- Sonuç en az şu kaynakların korelasyonundan **MUST** çıksın ve ayrı
  gösterilsin: üçüncü taraf uyarı (ör. `xAI security email`),
  `Lumos device activity`, `network observation`.

### AAC-06 — Pencere ve çoklu sinyal

- Varsayılan pencere **MUST** ±10 dakika, sıkı pencere **MUST** ±5 dakika
  olsun. Aynı gün eşlemesi **MUST NOT** yapılsın.
- Cihaz + zaman + servis güçlüdür. Yalnız zaman **MUST** `unknown` kalsın;
  kayıtlı cihaz sinyali olmadan `owner_match` / `likely_owner` **MUST NOT**
  üretilsin.

### AAC-07 — Açıklanabilirlik

- “Neden bu giriş sana ait görünüyor?” sorusuna kaynaklar, sinyaller ve
  pencere **MUST** gösterilsin. Gizli skor **MUST NOT** olsun.

### AAC-08 — Retention

- Sıradan oturum özeti **MUST** 14 gün; yüksek riskli / `suspicious` olay
  **MUST** 90 gün saklansın. Kullanıcı silmesi **MUST** mümkün olsun.
- Onay geri çekilince olay özetleri **MUST** silinsin.

### AAC-09 — Otomatik eylem yasağı

- Mail/uyarı **MUST NOT** şifre değiştirme, oturum kapatma veya hesap
  kilidine çevrilsin. Bu eylemler insan kararı ve mevcut onay kapısı
  olmadan **MUST NOT** çalışsın.

### AAC-10 — Provenance

- Hangi agent uyarıyı gördü, hangi olaylarla eşleştirdi, hangi sonucu
  üretti, kullanıcı ne karar verdi **MUST** ayrı ayrı, hash-zincirli
  kayda yazılsın. Bu zincir v0.1’de kurcalamayı görünür kılar; WORM
  değildir.

## 5. v0.1 çekirdek

`src/account_activity/engine.py` saf-Python referans modeldir:

- onay kapısı (consent) olmadan kayıt yok;
- cihaz kaydı + fingerprint olmadan olay yok;
- yasaklı alan ve düz IP reddi;
- çoklu sinyal korelasyonu ve ayrı kaynaklar;
- `execute_action` daima `human_approval_required`;
- provenance zinciri.

Canlı iOS yayını, mail parser, panel yüzeyi ve donanım attestation
doğrulaması bu dilimde **yoktur**. `attestation_ref` opak bir özetten
ibarettir.

## 6. Sonraki kapılar

1. Kayıtlı cihazın `DeviceIdentity.lumos_id` ile canlı bağlanması.
2. Onaylı cihaz istemcisinin minimal oturum özeti yayması (geçmiş yok).
3. Yapılandırılmış güvenlik uyarısı ingest’i (mail gövdesi/içerik yok).
4. Panel Denetim merceğinde açıklama (yeni sayfa yok; FAZ-1 sonrası).

## Sonuç

Lumos’un teklif ettiği şey kullanıcıyı izlemek değil; üçüncü taraf
uyarılarını, kullanıcının kendi doğrulanabilir cihaz kanıtıyla
eşleştiren dar bir güvenlik merceğidir. v0.1 fail-closed çalışır ve
kesin sahip hükmü vermez.
