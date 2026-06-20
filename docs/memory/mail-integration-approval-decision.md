# İletişim kanalları otomasyon modeli — onaylı karar (OD-031)

> **Mail = ilk kanal.** Bu belge OD-031 kapsamında **genel iletişim kanalları otomasyon ilke modelini** tanımlar; **e-posta (mail) uygulamada ilk uygulanacak kanaldır**. Telegram, WhatsApp, Messenger, SMS, sosyal DM ve benzeri mesajlaşma kanalları **gelecek genişleme adaylarıdır** (`implementation-pending`).
>
> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`computer-use-permission-gate-decision.md`](./computer-use-permission-gate-decision.md), [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md), [`vault-secret-token-decision.md`](./vault-secret-token-decision.md), [`security-architecture.md`](./security-architecture.md), [`product-rules.md`](./product-rules.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

**Kaynak OD:** OD-031 (`external-integrations-permissions.md` — İletişim kanalları; mail ilk kanal)

**Dosya adı notu:** Geçmiş uyumluluk için dosya adı `mail-integration-approval-decision.md` korunur; kapsam artık yalnızca mail değil, **kanal-agnostik ürün davranış ilkesidir**.

---

## Çekirdek çerçeve

**Lumos, kullanıcının kontrollü dijital uzantısıdır.** Kullanıcının adına veya yerine iletişim kanallarında hareket edebilir; ancak yalnızca şu sınırlar içinde:

1. **Kullanıcının açık isteği veya tanımlı kuralı**
2. **Verilmiş izin paketi** (granüler, geri alınabilir, denetlenebilir)
3. **Çekirdek güvenlik ve ürün kuralları** ([`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`product-rules.md`](./product-rules.md), OD-012, OD-041)

Lumos **kendi kendine tam yetki üstlenmez**; izin paketi ve kurallar olmadan kanal okuma, bildirim, taslak, gönderim veya silme yapmaz.

**Entegrasyon yöntemi ikincildir:** İletişim kanalları otomasyonu **tek bir teknik yönteme bağlı değildir** — resmi API, yerel bağlayıcı, Computer Use veya gelecekteki izinli yollar aynı izin paketi ve onay omurgası altında değerlendirilir. Amaç kullanıcının yetki verdiği kapsamda kanalı kullanabilmektir; yöntem seçimi kanal/platform bazlı uygulama kararıdır. Bkz. [`external-integrations-permissions.md`](./external-integrations-permissions.md) §Entegrasyon felsefesi.

---

## Amaç

OD-031 kapsamında **iletişim kanalları otomasyon modelinin** kapsamını, izin seviyelerini ve onay omurgasını netleştirmek.

Bu belge:

- Modeli **yalnızca pasif okuma/özet** veya **“özetleme ile sınırlı”** bir entegrasyon olarak **tanımlamaz**; kullanıcı tanımlı sınırlar içinde **tam otomasyon mümkündür**.
- Kullanıcı izin verdiğinde kanal takibi, bildirim kuralları, kişi/kaynak/içerik/görev bazlı sınıflandırma, taslak yanıt, kural-kapsamlı otomatik yanıt, bildirim bastırma veya zorunlu bildirim gibi davranışları **ayrı izin katmanları** ile tanımlar.
- **Mail’i ilk uygulama kanalı** olarak işaretler; diğer kanalları aynı ilke omurgasına **gelecek genişleme** olarak kaydeder.
- OD-041 (hibrit onay), OD-012 (Computer Use / dış etki kapısı) ve `product-rules.md` ile **gerilimi açık biçimde çözer**.
- Vault/credential modeli (OD-001/002) ve public repo sınırı ile hizalar.

**Uygulama notu:** İlke kararları onaylandı; kod, test, connector, provider entegrasyonu, onay UX veya otomasyon yapılandırması **henüz başlamadı**.

---

## Kapsam

### Kanal kapsamı

| Durum | Kanallar |
|-------|----------|
| **İlk kanal (implementation-pending)** | E-posta (mail) |
| **Gelecek genişleme adayları (implementation-pending)** | Telegram, WhatsApp, Messenger, SMS, sosyal DM ve benzeri mesajlaşma kanalları |

Her kanal için **teknik entegrasyon yolu** (resmi API, OAuth, yerel bağlayıcı, Computer Use, erişilebilirlik katmanı vb.) **ayrı değerlendirilir**; kanal otomasyonu **yalnızca bir yönteme kilitlenmez** — bkz. [`external-integrations-permissions.md`](./external-integrations-permissions.md) §Entegrasyon felsefesi. Bu belge **ürün davranış ilkesidir** — teknik bypass, scraping veya platform kurallarını aşma izni **vermez** (§Kapalı platformlar).

### Kullanıcı izin verdiğinde Lumos ne yapabilir?

Açık izin paketi ve tanımlı kurallar dahilinde:

| Yetenek | Açıklama |
|---------|----------|
| **Okuma / takip** | Gelen mesajları izin kapsamında okuma ve izleme |
| **Bildirim kuralları** | Kullanıcıya bildir, bildirme, her zaman bildir |
| **Sınıflandırma** | Kişi, kaynak, içerik, konu, görev veya önem bazlı gruplama |
| **Taslak yanıt** | Yanıt taslağı hazırlama (gönderim ayrı izin) |
| **Kural-kapsamlı otomatik yanıt** | Kullanıcı kuralı ile sınırlı otomatik yanıt |
| **Bildirim bastırma** | Belirli kişi/kural için kullanıcıyı rahatsız etmeme |
| **Zorunlu bildirim** | Belirli kişi/kaynak için her eşleşmede bildirim |
| **Sınırlı operasyon** | Kullanıcı adına arşiv, etiket, taslak+onaylı gönderim vb. — izin seviyesine bağlı |

**Firm ifade:** Kullanıcı tanımlı **tam otomasyon**, verilen **izin paketi sınırları** ve **açık kurallar** içinde mümkündür; varsayılan mod pasiftir, tam otomasyon **opt-in** ile açılır.

### Dahil / hariç tablosu

| Dahil | Hariç |
|-------|--------|
| Kanal-agnostik iletişim otomasyon ilkeleri | Mail dışı kanalların teknik connector seçimi — `implementation-pending` |
| Mail = ilk uygulama kanalı | Provider seçimi (Gmail OAuth / IMAP vb.) — `implementation-pending` |
| İzin seviyeleri: okuma, bildirim, taslak, gönder, arşiv, etiket, sil | Vault API sözleşmesi ve credential şeması — OD-001/002 uygulama |
| Kural bazlı otomasyon (kanal, kişi, domain, konu, içerik, görev, önem) | Onay UX wireframe, sync sıklığı, çakışma algoritması detayı |
| Varsayılan pasif / güvenli mod (izin yok = okuma yok) | Production endpoint, token, mesaj içeriği |
| OD-041 / OD-012 / product-rules hizası | Computer Use teknik entegrasyonu (OD-012 uygulama) |
| Public repo sınırı (credential / mesaj içeriği yok) | Takvim, kişiler (OD-032); çalışma araçları GitHub/Slack/Drive vb. (OD-033) |
| Kapalı platformlar: resmi API + platform kuralları ayrı değerlendirme | Scraping, unofficial API, platform bypass |

**Çelişki çözümü:** `external-integrations-permissions.md` Mail entegrasyonu bölümündeki eski “yalnızca izinle okur, özetler” veya pasif-özet sınırlaması ifadeleri bu belgeyle **geçersiz kılınır**; canonical kapsam bu dosyadır.

**Kapsam çerçevesi (firm):** “İzinli okuma/özet” veya “özetleme ile sınırlı entegrasyon” değil — **kullanıcı tanımlı iletişim kanalları takip ve otomasyon modeli**; mail ilk kanal.

---

## Firm ilkeler

| # | İlke | Durum |
|---|------|--------|
| CC1 | **Varsayılan pasif:** İzin olmadan okuma, takip veya dış etki yok. | `decision-approved` |
| CC2 | **Otomasyon açık yetki ile:** Kanal, kişi, konu, içerik veya görev bazında yalnızca kullanıcı **açıkça yetkilendirdiğinde**. | `decision-approved` |
| CC3 | **Tam otomasyon mümkün:** Kullanıcı tanımlı izin paketi ve kurallar sınırları içinde tam otomasyon (ör. kural-kapsamlı otomatik yanıt) **mümkündür** — varsayılan değildir. | `decision-approved` |
| CC4 | **İzin paketi:** Geri alınabilir, daraltılabilir, denetlenebilir; Lumos kendi kendine tam yetki üstlenmez. | `decision-approved` |
| CC5 | **Ayrı seviyeler:** `read`, `notify`, `draft_prep`, `send_reply`, `archive`, `label`, `delete` — üst seviye alt seviyeyi otomatik kapsamaz. | `decision-approved` |
| CC6 | **Kalıcı silme asla otomatik değil** — [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) trash prensibi. | `decision-approved` |
| CC7 | **Kural çakışmasında güvenli kazanır:** taslak + kullanıcı onayı, otomatik gönderimden önce. | `decision-approved` |
| CC8 | **Credential Lumos yüzeyinde değil** — vault/kasa (OD-001/002). | `decision-approved` |
| CC9 | **İçerik public repo, gereksiz log ve kalıcı bellekte değil** — minimum tutma, provenance. | `decision-approved` |
| CC10 | **Sessiz onay yok;** varsayılan-onay yok; carry-forward yok — OD-041 CA4. | `decision-approved` |
| CC11 | **Kapalı platformlar ayrı teknik değerlendirme** — bu belge ürün ilkesi; bypass/scraping kapsam dışı. | `decision-approved` |

---

## Karar özeti

**Onaylı karar (firm):** İletişim kanalları entegrasyonu, kullanıcının **açık ve granüler izin paketi** ile çalışan, **kural tabanlı, geri alınabilir ve denetlenebilir** bir takip/otomasyon modelidir. Pasif mod ve salt okuma+bildirim yalnızca **varsayılan güvenli tabandır**; kullanıcı tanımlı sınırlar içinde **tam otomasyon mümkündür**.

| # | Kural | Durum |
|---|--------|--------|
| CC1–CC11 | Yukarıdaki firm ilkeler tablosu | `decision-approved` |

*(Geçmiş MI1–MI10 numaraları CC1–CC10 ile hizalanmıştır; CC11 kapalı platform ayrımıdır.)*

---

## İzin seviyeleri

Kanal-agnostik; mail ilk uygulamada aynı tablo geçerlidir.

| Seviye | Kod | Etki | Varsayılan | Onay modeli |
|--------|-----|------|------------|-------------|
| **Okuma** | `read` | Gelen mesaj okuma, takip, sınıflandırma | Kapalı (izin gerekir) | Oturum + kanal/kapsam (OD-041 CA1) |
| **Bildirim** | `notify` | Kullanıcıya bildirim / uyarı | Güvenli modda açılabilir — ayrı grant | Oturum + kapsam |
| **Taslak hazırlama** | `draft_prep` | Yanıt taslağı; **göndermez** | Kapalı | Kural veya işlem bazlı açık izin |
| **Yanıt gönderme** | `send_reply` | Taslak veya kural onaylı yanıt gönderme | Kapalı | **İşlem bazlı veya kural-kapsamlı açık izin** |
| **Arşivleme** | `archive` | Mesaj arşivleme | Kapalı | İşlem veya kural-kapsamlı izin |
| **Etiketleme** | `label` | Etiket / klasör / etiket atama | Kapalı | İşlem veya kural-kapsamlı izin |
| **Silme** | `delete` | Çöp / sil (geri alınabilir) | Kapalı | **Yüksek risk — açık onay zorunlu** |
| **Kalıcı silme** | — | Geri dönüşsüz silme | **Asla otomatik** | Kullanıcı açık komutu + tek satır uyarı; `SECURITY_NEVER_AUTO` |

**Firm ilkeler:**

1. Üst seviye izin, alt seviyeyi **otomatik olarak kapsamaz** — her seviye ayrı tanımlanır ve kullanıcıya görünür olmalıdır.
2. `send_reply` otomatik yalnızca **açık kural + kural-kapsamlı grant** ile; kural yoksa her gönderim işlem onayı gerektirir.
3. Tam otomasyon (`send_reply`, `archive`, `label` kural-kapsamlı) yalnızca **CC3/CC4** izin paketi sınırları içinde.
4. `delete` ve kalıcı silme **Computer Use §6 e-posta/mesaj satırı** ve **lumos-karar-sozlesmesi kalıcı silme** ile aynı omurgayı paylaşır.

---

## Kullanıcı tanımlı otomasyon modeli

Kullanıcı, açık izin verdiğinde Lumos'a **kural tabanlı** iletişim akış yönetimi tanımlayabilir. Kurallar **kanal, kişi, kaynak, konu, içerik, görev** boyutlarında birleştirilebilir.

### Kural boyutları (firm — kapsam)

| Boyut | Örnek |
|-------|--------|
| **Kanal** | Mail, Telegram, SMS (gelecek kanallar ayrı grant) |
| **Kişi** | Belirli gönderen (Angel, Leyla, Hasan, Müşteri X) |
| **Kaynak / domain** | `@musteri.com`, belirli grup veya sohbet |
| **Konu** | "Fatura", "Acil" |
| **İçerik** | Anahtar kelime / içerik eşleşmesi |
| **Görev / bağlam** | Kullanıcı tanımlı iş veya proje bağlamı |
| **Önem seviyesi** | Kullanıcı tanımlı öncelik |
| **Özel kural** | Kullanıcı tanımlı bileşik koşul |

### Örnek kurallar (yalnızca illüstrasyon — uygulama değil)

Aşağıdaki örnekler **ürün davranışı tanımı değildir**; kullanıcıya kural modelini göstermek için kayıtlıdır. Mail ve mesaj kanalları için aynı ilke geçerlidir.

| # | Kullanıcı kuralı (illüstrasyon) | Gerekli izin seviyeleri | Beklenen davranış (ilke) |
|---|----------------------------------|-------------------------|---------------------------|
| E1 | "Angel'dan mail/mesaj gelirse bana bildir." | `read`, `notify` | Bildirim; otomatik yanıt yok |
| E2 | "Leyla'dan gelenleri içeriğe göre sen cevapla, bana bildirme." | `read`, `send_reply` + **açık kural** (Leyla) | Kural-kapsamlı otomatik yanıt; bildirim kapalı |
| E3 | "Hasan'dan gelenleri mutlaka bana bildir." | `read`, `notify` + **açık kural** (Hasan) | Her eşleşmede bildirim |
| E4 | "Müşteri X'ten gelenlere taslak hazırla; göndermeden önce sor." | `read`, `draft_prep` | Taslak + **işlem bazlı gönder onayı** |
| E5 | "Grup mesajlarını takip et; yalnızca önemli olanları bana bildir." | `read`, `notify` + **içerik/önem kuralı** | Takip sürekli; bildirim seçici |

**Firm kurallar:**

1. Her kural **açık opt-in** ile oluşturulur; sessiz veya varsayılan kural yok.
2. Kural **revoke edilebilir** — kanal, kişi veya kural bazında durdurma anında geçerli olmalıdır (UX detayı `implementation-pending`).
3. E2 gibi "bana bildirme" isteği, `notify` seviyesinin o kural için **bilinçli olarak kapalı** olduğunu gösterir — çakışmada CC7 uygulanır.
4. E4, **taslak + onay** modelinin canonical örneğidir; otomatik `send_reply` yerine tercih edilir (çakışmada CC7).
5. E5, **grup/sohbet** senaryosunda takip ile bildirimin ayrılabileceğini gösterir.

---

## Kapalı platformlar (Telegram, WhatsApp, Messenger vb.)

Bu bölüm **ürün davranış ilkesi** ile **teknik entegrasyon iznini** ayırır.

| Konu | Bu belgede | Ayrı değerlendirme (implementation-pending) |
|------|------------|-----------------------------------------------|
| Kullanıcı tanımlı otomasyon, izin seviyeleri, onay omurgası | **Evet** — kanal-agnostik ilke | — |
| Resmi API, OAuth, bot/token modeli | İlke referansı | Provider/kanal bazlı teknik karar |
| Platform ToS, rate limit, mesaj türü kısıtları | Uyum zorunlu — bypass yok | Entegrasyon tasarımında |
| Scraping, unofficial client, otomasyon bypass | **Yasak / kapsam dışı** | — |

**Firm:** WhatsApp, Telegram, Messenger gibi kapalı veya kısıtlı platformlarda Lumos yalnızca **resmi, kullanıcı-onaylı, platform kurallarına uygun** entegrasyon yollarını değerlendirir. Bu belge **scraping veya yetkisiz erişim** için izin vermez.

---

## Hibrit onay modeli (OD-041 / OD-012 / product-rules)

İletişim kanalları entegrasyonu, ticari onay (OD-041), Computer Use (OD-012) ve `product-rules.md` (Lumos geçidi, ne/nerede/etki) ile **aynı hibrit omurgayı** kullanır; kanal alanına özgü granülerlik ekler.

```
[ Oturum / görev kapsamı + kanal scope ]
        →  düşük risk: read · notify · sınıflandırma (varsayılan güvenli mod — grant ile)

[ Kural-kapsamlı açık izin ]
        →  kullanıcı tanımlı kural ile sınırlı: draft_prep · send_reply · archive · label
           (yalnızca kural eşleşmesinde; kural revoke = anında dur)

[ İşlem bazlı açık onay ]
        →  kural dışı veya yüksek risk: send · delete · kalıcı silme
           ne / kimden / kime / hangi kanal / etki görünür
```

### OD-041 hizası (oturum vs işlem)

| OD-041 ilkesi | İletişim kanalları karşılığı |
|---------------|------------------------------|
| CA1 — düşük riskli okuma/izleme oturum bazlı | `read`, `notify`, sınıflandırma — oturum + kanal kapsamı içinde |
| CA2 — dış etkili aksiyon işlem bazlı | Kural dışı `send_reply`, `delete`, arşiv/etiket (kural yoksa) |
| CA4 — sessiz / carry-forward onay yok | Kanal kuralları ve izin yükseltmesi açık opt-in |
| CA6 — oturum izni ≠ dış etki yetkisi | Oturum `read`/`notify` ≠ `send_reply` / `delete` |
| CA7 — ne/nerede/etki | Gönder/sil öncesi alıcı, kanal, konu, etki özeti zorunlu |

### OD-012 hizası

| OD-012 ilkesi | İletişim kanalları karşılığı |
|---------------|------------------------------|
| CU4 — dış etkili aksiyon açık onay | Gönderme, silme, arşiv = dış etki; ayrı kapı |
| CU5 — okuma vs dış etki mod ayrımı | Okuma/takip modu ↔ gönder/sil modu karışmaz |
| §7 — mod yükseltmesi yeni onay | `read` oturumundan `send_reply`'a sessiz geçiş yok |
| §6 — e-posta/mesaj ayrı onay katmanı | Kanal connector kendi granüler izin tablosunu kullanır |
| CU6 — geri dönüşsüz otomatik yok | Kalıcı silme asla otomatik |

### product-rules hizası

| product-rules ilkesi | İletişim kanalları karşılığı |
|----------------------|------------------------------|
| Lumos tek dış yüzey / geçit | Tüm kanal connector'ları Lumos geçidi üzerinden; bypass yok |
| Ne, nerede, hangi etki (panel/chat) | Gönder/sil/otomasyon öncesi kullanıcıya görünür özet |
| Gizli anahtarlar Lumos yüzeyinde tutulmaz | CC8; vault bridge (OD-001/002) |
| Encrypted / veri sahipliği ekseni | Mesaj içeriği gereksiz kalıcı yüzeyde tutulmaz (CC9) |

**Gerilim çözümü (firm):**

| Soru | Çözüm |
|------|--------|
| Oturum izni mesaj okumaya yetiyor mu? | Evet — **yalnızca** verilen kanal/kapsam grant'ı ile `read` + isteğe bağlı `notify` (CA1). |
| Oturum izni otomatik yanıta yetiyor mu? | **Hayır** — otomatik yanıt yalnızca **açık kural + `send_reply` kural-kapsamlı izin** ile. |
| Genel onay (`kisitli_otonom`) mesaj göndermeye yetiyor mu? | **Hayır** — OD-012 §5 ve OD-041 CA6: işlem veya kural-kapsamlı açık izin gerekir. |
| Tam otomasyon mümkün mü? | **Evet** — CC3: kullanıcı tanımlı izin paketi + kurallar sınırları içinde; varsayılan değil. |
| Kural ile işlem onayı nasıl ayrılır? | Kural = **önceden açık opt-in, revoke edilebilir, sınırlı kapsam**; kural dışı veya çakışma = **işlem onayı veya güvenli fallback (taslak)**. |

**Canonical ifade:** **Oturum izni** salt okuma/bildirim/takip katmanını genişletir; **gönder, sil, arşiv, etiket ve kural bazlı otomatik yanıt** oturum izninden **türemez** — ya **kural-kapsamlı açık grant** ya da **işlem bazlı açık onay** gerekir.

---

## Vault / credential (OD-001 / OD-002)

| Konu | Karar | Durum |
|------|--------|--------|
| Kanal OAuth token / API credential | Vault/kasa katmanında; Lumos yüzeyinde **açık tutulmaz** | decision-approved (ilke) |
| Connector erişimi | Bridge üzerinden amaç bazlı, kapsam sınırlı | decision-approved (ilke); API `implementation-pending` |
| Log / chat / panel | Credential ve ham mesaj içeriği **yazılmaz** | decision-approved |
| Kanal/kapsam scope | Hangi hesap, kutu, sohbet, etiket — kullanıcıya görünür | decision-approved (ilke); UX `implementation-pending` |

**OD-001/002 durumu:** Kanal credential'larının vault'ta tutulacağı ve Lumos'un secret taşımayacağı ilkesi **onaylandı**; token formatı, mail/messaging connector credential şeması ve bridge entegrasyon akışı **`implementation-pending`**.

---

## Gizlilik ve public repo sınırı

| Gereksinim | Kural |
|------------|--------|
| **Public repo** | Mesaj içeriği, credential, token, production endpoint, ham gövde **yazılmaz** |
| **Log** | PII ve mesaj içeriği operasyonel loga yazılmaz (firm); detay `implementation-pending` |
| **Kalıcı bellek** | Mesaj içeriği gereksiz yere kalıcı workspace state'e yazılmaz; özet/provenance minimum tutma |
| **Provenance** | Özet/aksiyon hangi kanal, hesap, gönderen, zaman — kullanıcıya görünür |
| **Demo-safe** | Public repoda yalnızca ilke, onay modeli, placeholder — production akış private katmanda |

Trash prensibi: Lumos içi silinen içerik `.lumos/trash/`; dış kanal kalıcı silme **asla otomatik** — kullanıcı açık komutu + tek satır uyarı.

---

## Kural çakışması

**Firm kural (CC7):** Çakışan kurallarda **daha güvenli davranış kazanır.**

| Durum | Tercih edilen davranış |
|-------|------------------------|
| Bir kural `send_reply`, diğeri `draft_prep` / onay istiyor | **Taslak + kullanıcı onayı** — otomatik gönderim yapılmaz |
| Bir kural bildir, diğeri bildirme | **Bildir** (kullanıcıya bilgi kaybı riski daha yüksek) |
| Otomatik yanıt vs "göndermeden önce sor" | **Taslak + onay** kazanır |
| Silme vs arşivle | **Arşivle** veya **kullanıcıya sor** — otomatik silme yapılmaz |
| Belirsiz / eşit öncelik | **Dur + kullanıcıya sor** — otomatik dış etki yok |

**Implementation-pending:** Çakışma öncelik algoritması, kural öncelik numarası UX'i, çoklu kural birleştirme sözdizimi.

---

## Yasak (onaysız veya otomatik)

| # | Aksiyon | Gerekçe |
|---|---------|---------|
| Y1 | Onaysız kanal okuma, gönderme, silme, arşivleme | external-integrations-permissions; CC1 |
| Y2 | Oturum izni ile otomatik yanıt (kural olmadan) | CC2/CC3; OD-041 CA6 |
| Y3 | Otomatik kalıcı mesaj silme | lumos-karar-sozlesmesi; CC6 |
| Y4 | Credential'ın Lumos yüzeyinde veya logda açığa çıkması | OD-001/002; CC8 |
| Y5 | Mesaj içeriğinin public repo veya gereksiz kalıcı belleğe yazılması | CC9; public boundary |
| Y6 | Sessiz kural, varsayılan-onaylı otomasyon, carry-forward izin | CC10; OD-041 CA4 |
| Y7 | Kural çakışmasında otomatik gönderim | CC7 |
| Y8 | Genel onayın tek başına mesaj gönderme yetkisi | OD-012 §5; OD-041 |
| Y9 | Platform bypass, scraping, unofficial API | CC11 |

---

## Mail — ilk uygulama kanalı

Mail (e-posta), bu modelin **ilk somut uygulama kanalıdır**.

| Konu | Durum |
|------|--------|
| İlke modeli (izin seviyeleri, kurallar, onay) | **decision-approved** — bu belgenin tamamı |
| Gmail OAuth / IMAP / provider seçimi | **implementation-pending** |
| Mail connector, sync, kural UX | **implementation-pending** |

Diğer kanallar (Telegram, WhatsApp, Messenger, SMS, sosyal DM) **aynı CC/OD omurgasını** paylaşır; kanal başına teknik entegrasyon ve platform uyumu **ayrı implementation-pending paket** olarak değerlendirilir.

---

## Implementation-pending

Aşağıdakiler **henüz uygulanmadı**; bu belge uygulama izni vermez.

| Konu | Durum | Not |
|------|--------|-----|
| **Mail** — provider (Gmail OAuth, IMAP) | **implementation-pending** | İlk kanal |
| **Diğer kanallar** — Telegram, WhatsApp, Messenger, SMS, sosyal DM | **implementation-pending** | Genişleme adayı; teknik + platform değerlendirme |
| Vault API ve kanal credential şeması | **implementation-pending** | OD-001/002 ile birlikte |
| Onay UX, kural editörü, wireframe | **implementation-pending** | Kanal/kişi/kural oluşturma/revoke |
| Sync sıklığı, push vs poll | **implementation-pending** | Kanal bazlı operasyonel model |
| Kural çakışma algoritması detayı | **implementation-pending** | CC7 ilke sabit; algoritma sonra |
| Connector kodu, bridge entegrasyonu | **implementation-pending** | Public repoda yalnızca demo-safe |
| Log / kanıt saklama (kanal özelinde) | **implementation-pending** | İçerik loga yazılmaz ilkesi firm |
| Kapalı platform resmi API seçimi | **implementation-pending** | CC11 — ürün ilkesi ayrı |

**Needs-review (açık alt detay):**

- Çoklu hesap / paylaşılan kanal senaryosu
- Ek dosya (attachment) okuma/gönderme izin sınırı
- Kanal + Computer Use birleşik senaryo (tarayıcı vs API connector)
- Grup/sohbet kimliği ve bildirim eşiği UX'i

---

## Mail pilot implementation checklist (public stub)

| # | Madde | Durum | Not |
|---|--------|--------|-----|
| M1 | Mail provider seçimi (Gmail OAuth / IMAP) | implementation-pending | Resmi API |
| M2 | Vault mail credential şeması | implementation-pending | OD-001/002 private |
| M3 | Granüler izin grant UI | implementation-pending | OD-041 hibrit |
| M4 | Kural editörü (kişi/kaynak/içerik) | implementation-pending | OD-031 CC |
| M5 | Sync modeli (poll vs push) | implementation-pending | — |
| M6 | Çakışma algoritması (taslak vs otomatik) | implementation-pending | CC7 |
| M7 | İlk kanal smoke — **onaylı impl paketi gerekir** | blocked | Public kod yok |

**DL-E02 sync:** «Karar onaylı, uygulama bekliyor» — ilke onaylı; M1–M7 private/onaylı paket.

---

## Açık kararlar özeti

| Konu | Durum |
|------|--------|
| İletişim kanalları ≠ yalnızca pasif özet / özetleme sınırı | **decision-approved** | CC1, CC3 |
| Kullanıcı tanımlı tam otomasyon (izin paketi sınırları içinde) | **decision-approved** | CC3, CC4 |
| Varsayılan pasif mod; grant ile güvenli okuma/bildirim | **decision-approved** | CC1, CC2 |
| Granüler izin seviyeleri | **decision-approved** | CC5, §İzin seviyeleri |
| Kural bazlı otomasyon (açık opt-in, revoke) | **decision-approved** | CC2, CC4 |
| Kalıcı silme asla otomatik | **decision-approved** | CC6 |
| Vault credential modeli | **decision-approved** (ilke) | CC8; uygulama pending |
| İçerik public repo/log yasağı | **decision-approved** | CC9 |
| Kural çakışmasında güvenli davranış | **decision-approved** | CC7 |
| OD-041 / OD-012 / product-rules hibrit hiza | **decision-approved** | §Hibrit onay |
| Mail ilk kanal; diğer kanallar genişleme adayı | **decision-approved** (ilke) | §Mail — ilk kanal |
| Kapalı platform: ürün ilkesi ≠ teknik bypass | **decision-approved** | CC11 |
| Provider, UX, sync, algoritma, diğer kanallar | **implementation-pending** | §Implementation-pending |

---

## OD eşleme

| OD | Kaynak | Konu | Bu belgedeki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-031** | external-integrations-permissions.md | İletişim kanalları otomasyon modeli (mail ilk kanal) | Bu belgenin tamamı | **decision-approved / implementation-pending** |
| OD-012 | computer-use-permission-gate-decision.md | Computer Use / dış etki kapısı | §OD-012 hizası; §Gerilim çözümü | decision-approved / implementation-pending |
| OD-041 | commercial-approval-model-decision.md | Hibrit onay modeli | §OD-041 hizası; oturum vs işlem vs kural | decision-approved / implementation-pending |
| OD-001 | security-architecture.md | Vault uygulaması | §Vault — katman ilkesi | decision-approved / implementation-pending |
| OD-002 | security-architecture.md | Token / vault entegrasyonu | §Vault — bridge, credential | decision-approved / implementation-pending |
| OD-032 | external-integrations-permissions.md | Takvim / kişiler | İletişim kanalları ile birlikte değil; ayrı | decision-approved / implementation-pending — [`calendar-contacts-decision.md`](./calendar-contacts-decision.md) |
| OD-033 | external-integrations-permissions.md | Çalışma araçları connector'ları | İletişim kanalları ile birlikte değil; ayrı | decision-approved / implementation-pending — [`work-tools-connectors-decision.md`](./work-tools-connectors-decision.md) |

**İndeks notu:** `open-decisions-needs-review.md` OD-031 satırı bu belgeyle senkron tutulur; canonical kaynak önce `external-integrations-permissions.md`, onaylı karar özeti bu dosyadır.

---

## Sonraki adım

1. **Implementation-pending (mail):** Provider değerlendirmesi (Gmail OAuth / IMAP), vault mail credential şeması, kural editörü UX, sync modeli, çakışma algoritması — uygulama paketi ayrı.
2. **Implementation-pending (genişleme):** Telegram, WhatsApp, Messenger, SMS, sosyal DM — kanal başına resmi API ve platform uyumu değerlendirmesi; aynı CC/OD omurgası.
3. Vault modeli (OD-001/002) netleşmeden kanal credential **Lumos yüzeyine taşınmaz**.
4. Computer Use (OD-012) tarayıcı tabanlı kanal senaryolarında **aynı granüler izin tablosu** referans alınır; ayrı gevşek model icat edilmez.
5. Ticari onay (OD-041) ve product-rules ile tutarlı: oturum = düşük risk okuma/bildirim/takip; dış etkili kanal aksiyonu = işlem veya kural-kapsamlı onay.

**Yasak (bu aşamada):** kod, test, connector, provider entegrasyonu, credential, production endpoint, mesaj içeriğinin repoya yazılması, otomasyon yapılandırması, platform bypass/scraping.

---

Son güncelleme: 2026-06-20 (mail pilot checklist — envanter ab791c14 §12 #5)
