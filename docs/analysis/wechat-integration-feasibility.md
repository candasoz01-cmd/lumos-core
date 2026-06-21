# WeChat Entegrasyonu — Fizibilite Raporu (Lumos)

| Alan | Değer |
|------|--------|
| **Belge ID** | `wechat-integration-feasibility` |
| **Durum** | `analiz` — fizibilite / karar destek; ürün kararı değildir |
| **Tarih** | 2026-06-21 |
| **Dil** | Türkçe (birincil) |
| **Kapsam** | Lumos trust/control katmanının WeChat ekosistemi ile resmi yollarla entegrasyon fizibilitesi |
| **Varlık bağlamı** | We Lock AI / KKTC kayıtlı şirket ([`bank-readiness-checklist.md`](./bank-readiness-checklist.md), [`ip-protection-landscape.md` §7.1](./ip-protection-landscape.md#71-kktc-kuzey-kıbrıs-türk-cumhuriyeti)) |
| **Üst sınır** | [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`docs/memory/public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| **İlgili ADR'ler** | [ADR-007](../decisions/ADR-007-trust-engine-layer.md) (trust katmanı), [ADR-002](../decisions/ADR-002-mail-inbox-intelligence.md) (kanal entegrasyon ilkesi) |
| **Repo taraması** | `WeChat` / `Weixin` / `微信` — **0 eşleşme** (2026-06-21) |
| **Son güncelleme** | 2026-06-21 |

> **Sorumluluk reddi:** Bu belge **hukuki tavsiye değildir**. Tencent/WeChat platform kuralları, Çin veri mevzuatı (PIPL, DSL, CSL) ve KKTC/Türkiye şirket yapısı **hızla değişebilir**. `[doğrulanmalı]` işaretli maddeler yerel Çin hukuk danışmanı + kullanıcı varlık yapısı ile teyit edilmelidir.

---

## Yönetici özeti

WeChat ekosistemi **kişisel WeChat uygulaması** ile **işletme yüzeyleri** (Service Account / 服务号, Mini Program / 小程序, WeCom / 企业微信) arasında keskin bir ayrım yapar. Lumos'un "trust and control layer" vaadi — onay, günlük, politika kapısı, kullanıcı onayı olmadan dış etki yok — **işletme API'leri üzerinden** WeChat kullanımını bozmadan eklenebilir; **kişisel WeChat istemcisini sarmalayan veya otomatikleştiren** bir katman ise platform kurallarına aykırıdır ve uygulanamaz.

**Ana soru yanıtı:** **Kısmen — evet (koşullu), kişisel WeChat için hayır.**

| Senaryo | Lumos trust katmanı mümkün mü? | Koşul |
|---------|-------------------------------|-------|
| Doğrulanmış **yurtdışı Service Account** (webhook + Customer Service API) | **Evet** | Resmi sunucu URL'si; gönderim öncesi Lumos onay kapısı |
| **Mini Program** (sunucu tarafı API + kullanıcı oturumu) | **Evet** | Mini Program backend'ine policy middleware; kullanıcı akışı Mini Program içinde kalır |
| **WeCom** (kurumsal, external contact API) | **Kısmen — evet** | Kurumsal doğrulama; B2B senaryo; API kotaları |
| **Open Platform üçüncü taraf platform** (yetkili servis sağlayıcı) | **Evet** | Open Platform developer certification + merchant authorization |
| **Kişisel WeChat** (1:1 sohbet, grup, istemci otomasyonu) | **Hayır** | Scraping/bot/eklenti yasağı; resmi API yok |

**Önerilen fizibilite çerçevesi:** **Pilot (dar kapsam)** — yalnızca doğrulanmış işletme hesabı + resmi webhook/API; kişisel WeChat kapsam dışı. Tam ürün kararı değildir.

---

## 1. WeChat ürün haritası

| Ürün | Tencent adı | Birincil kullanım | Lumos için relevans |
|------|-------------|-------------------|---------------------|
| **Subscription Account** | 订阅号 | İçerik / yayın (günde 1 push) | Yurtdışı kuruluşlar genelde **kayıt edemez** — Service Account tercih edilir |
| **Service Account** | 服务号 | İşletme mesajlaşma, menü, OAuth, API | **Birincil aday** — yurtdışı entity ile Service Account kaydı mümkün |
| **Mini Program** | 小程序 | Uygulama içi deneyim, WeChat içi UX | **İkincil aday** — trust UI veya onay yüzeyi; backend'e Lumos kapısı |
| **WeCom (WeChat Work)** | 企业微信 | Kurumsal iletişim, external contacts, CRM | **B2B aday** — yurtdışı doğrulama mümkün; farklı API seti |
| **Open Platform** | 微信开放平台 | App birleştirme, üçüncü taraf platform, unionid | Lumos **servis sağlayıcı / middleware** modeli için |
| **WeChat Pay** | 微信支付 | Ödeme | Yurtdışı Service Account'ta **sınırlı**; Cross-Border Pay ayrı başvuru |
| **Kişisel WeChat** | 微信 | Bireysel mesajlaşma | Lumos entegrasyonu **uygun değil** (ToS) |

**Kaynaklar:**
- Service Account mesaj push / webhook: [Weixin Service — Messaging and Event Push](https://developers.weixin.qq.com/doc/service/en/guide/dev/push/)
- Yurtdışı Mini Program kayıt: [Weixin Open Community — overseas entities](https://developers.weixin.qq.com/community/business/doc/000a86174e81f0836172539ce6140d)
- Open Platform üçüncü taraf platform: [How to become a service provider](https://developers.weixin.qq.com/doc/oplatform/en/Third-party_Platforms/2.0/getting_started/how_to_be.html)

---

## 2. API erişim matrisi — KKTC / Türkiye tüzel kişiliği

**Bağlam:** Lumos ticari çatısı **We Lock AI**, banka hazırlık belgelerinde **KKTC** yargı yetkisi ile anılır ([`bank-readiness-checklist.md`](./bank-readiness-checklist.md)). Tencent platformunda KKTC genellikle **"non-Chinese Mainland" / overseas entity** olarak sınıflandırılır; Çin anakara WFOE veya ICP gerektirmez — ancak ** özellik seti mainland hesaplardan dar olabilir**.

| Yetenek | KKTC/TR overseas entity | Mainland China entity | Not |
|---------|-------------------------|----------------------|-----|
| Overseas **Service Account** kaydı | ✅ Mümkün | N/A (ayrı kanal) | Yalnızca Service Account; Subscription genelde kapalı |
| **Weixin Verification** (≈99 USD) | ✅ | ✅ | Üçüncü taraf inceleme; belge seti gerekir |
| **Webhook / server URL** (mesaj & olay) | ✅ (doğrulanmış hesap) | ✅ | Token + EncodingAESKey; AES şifreleme |
| **Customer Service API** (48h pencere) | ✅ [doğrulanmalı] | ✅ | Kota farkları olabilir |
| **OAuth2 / web auth** (openid) | ✅ | ✅ | Kullanıcı kimliği hesap bazlı openid |
| **Template / subscription messages** | ⚠️ Kısıtlı / sektör bağımlı | ✅ | Endüstri onayı gerekebilir |
| **Mini Program** (overseas entity) | ✅ | ✅ (ICP filing gerekir) | Overseas: **ICP filing muaf** [kaynak](https://developers.weixin.qq.com/community/business/doc/000a86174e81f0836172539ce6140d) |
| **WeCom** kurumsal doğrulama | ✅ | ✅ | ≈700 RMB; yıllık yenileme [doğrulanmalı] |
| **WeChat Pay (native)** | ❌ | ✅ | Overseas Service Account'ta genelde yok |
| **WeChat Cross-Border Pay** | ⚠️ Ayrı başvuru | N/A | Institution veya Merchant model; finans lisansı [doğrulanmalı](https://pay.weixin.qq.com/doc/global/v3/en/4012356433) |
| **Open Platform developer certification** | ✅ [doğrulanmalı] | ✅ | ≈300 RMB; 5 third-party platform hesabı |
| **Third-party platform** (merchant auth) | ✅ | ✅ | Resmi yetkilendirme akışı zorunlu |
| **Kişisel WeChat API** | ❌ | ❌ | Resmi API yok |
| **Scraping / RPA / istemci eklentisi** | ❌ | ❌ | [Acceptable Use Policy](https://www.wechat.com/en/acceptable_use_policy.html) |

### 2.1 Yurtdışı Service Account — bilinen kısıtlar

Tencent topluluk ve sektör kaynakları, **yurtdışı Service Account** ile **mainland Service Account** arasında işlev farkı olduğunu belirtir ([Weixin Open Community karşılaştırma](https://developers.weixin.qq.com/community/develop/article/doc/000eacf7e7c9403b0fb3437b76bc13)):

- WeChat Pay, WeChat Store, native card/coupon: genelde **desteklenmez** veya dolaylı (Cross-Border Pay partner)
- Bazı API çağrı limitleri daha düşük (ör. kullanıcı listesi)
- Mainland kullanıcı erişimi: pazarlama hedefine göre **servis sağlayıcı kanalı** gerekebilir [doğrulanmalı]

**KKTC özel not:** KKTC ticaret sicil belgesi ile overseas kayıt **muhtemelen mümkün**; Tencent'in ülke/bölge listesinde KKTC'nin nasıl sınıflandırıldığı **doğrudan başvuru öncesi teyit edilmelidir** [doğrulanmalı — Tencent destek veya yetkili partner].

---

## 3. Lumos entegrasyon desenleri (trust katmanı)

Lumos'un mevcut entegrasyon felsefesi: **resmi API tercih edilir**; kullanıcı onayı olmadan okuma/gönderme/dış yazma yok ([`external-integrations-permissions.md`](../memory/external-integrations-permissions.md)). WeChat, bu ilkeye **işletme API'leri** ile uyumludur.

### 3.1 Desen A — Webhook middleware (Service Account / WeCom)

```
WeChat Server ──POST/XML/JSON──► Lumos Policy Gate ──► İş mantığı / onay kuyruğu
                                      │
                                      ├── audit log (provenance)
                                      ├── kullanıcı onayı (gönderim öncesi)
                                      └── red / geciktir / onayla ──► WeChat Reply API
```

**Nasıl çalışır:** Geliştirici, WeChat Developer Platform'da **Server URL + Token + EncodingAESKey** tanımlar ([push guide](https://developers.weixin.qq.com/doc/service/en/guide/dev/push/)). Gelen mesaj/olay önce Lumos kapısından geçer; otomatik yanıt veya Customer Service mesajı **yalnızca onay sonrası** gönderilir.

**Mevcut kullanımı bozmaz mı?** Kullanıcı hâlâ WeChat uygulamasında aynı hesapla konuşur; değişen tek şey **sunucu tarafı yanıt pipeline'ıdır**. Kişisel WeChat sohbetlerine uygulanamaz.

### 3.2 Desen B — Sidecar (Mini Program backend)

Mini Program frontend Tencent sandbox'ta kalır; **backend API çağrıları** Lumos'a veya Lumos-protected proxy'ye gider. Hassas aksiyonlar (form gönderimi, sipariş, veri export) Lumos confirmation policy ile hizalanır ([ADR-007](../decisions/ADR-007-trust-engine-layer.md), `SECURITY_NEVER_AUTO`).

### 3.3 Desen C — Open Platform third-party authorization

Lumos (veya We Lock AI), **Open Platform service provider** olarak merchant Service Account / Mini Program'a **OAuth-style authorization** alır ([Security Management Instructions](https://developers.weixin.qq.com/doc/oplatform/en/Third-party_Platforms/Before_Develop/Security_Management_Instructions.html)). Merchant mevcut WeChat varlığını korur; Lumos yalnızca yetkilendirilmiş API kapsamında policy uygular.

**Kritik kural:** AppID/AppSecret'ı düz metin saklayan gayri resmi platformlar Tencent tarafından **riskli** sayılır; resmi authorization mekanizması zorunludur.

### 3.4 Desen D — WeCom external contact (B2B)

Marka + distribütör senaryolarında `unionid` → `external_userid` dönüşümü resmi API ile yapılır ([WeCom Help — partner space integration](https://open.work.weixin.qq.com/help2/pc/19643?person_id=0)). Lumos, CRM aksiyonları öncesi onay ve log katmanı olabilir; saatlik API kotaları (ör. 10.000/saat) tasarım kısıtıdır.

### 3.5 Lumos'a uymayan desenler (red)

| Desen | Neden red |
|-------|-----------|
| Kişisel WeChat bot / Web WeChat otomasyon | [AUP](https://www.wechat.com/en/acceptable_use_policy.html) — bot, scraper, crawler yasağı |
| Onaysız toplu mesaj / broadcast | Lumos sözleşmesi + WeChat spam kuralları |
| İstemci eklentisi / reverse engineering | [Personal Account norms](https://help.wechat.com/cgi-bin/readtemplate?lang=en_US&t=page%2Fagreement%2Fpersonal_account) |
| Gayri resmi SaaS "WeChat inbox sync" (scraping) | Hesap kapatma riski; Lumos trust modeli ile çelişir |

---

## 4. Bot / Official Account yetenekleri

| Hesap tipi | Mesajlaşma modeli | Bot benzeri davranış | Lumos uyumu |
|------------|-------------------|----------------------|-------------|
| **Subscription Account** | Yayın odaklı; sınırlı etkileşim | Kısıtlı otomasyon | Overseas kayıt genelde yok — öncelik düşük |
| **Service Account** | 48 saat etkileşim penceresi; CS API | Webhook + API ile **kural tabanlı yanıt** | **Uygun** — onay kapılı otomasyon |
| **Mini Program** | Uygulama içi UX | Sunucu tarafı logic | **Uygun** — trust UI katmanı |
| **WeCom** | Kurumsal + external contacts | Uygulama mesajları, chat API | **Uygun (B2B)** |
| **Kişisel WeChat** | P2P / grup | Resmi bot API **yok** | **Uygun değil** |

**Customer Service API:** Kullanıcı mesajına 48 saat içinde yanıt verme modeli; template message'lar ayrı onay/kategori gerektirir [doğrulanmalı — sektör bazlı].

---

## 5. Üçüncü taraf SaaS kuralları

| Kural | Kaynak | Lumos etkisi |
|-------|--------|--------------|
| Resmi **authorization** olmadan üçüncü taraf platform kullanımı güvenlik riski | [Security Management Instructions](https://developers.weixin.qq.com/doc/oplatform/en/Third-party_Platforms/Before_Develop/Security_Management_Instructions.html) | Lumos prod entegrasyonu **Open Platform auth** üzerinden tasarlanmalı |
| **Scraping / bot / crawler** yasak | [WeChat AUP](https://www.wechat.com/en/acceptable_use_policy.html), [Safety Center](https://safety.wechat.com/en_US/community-guidelines/cover/platform-authenticity-and-account-integrity) | "Inbox intelligence" için scraping tabanlı SaaS **kullanılamaz** |
| Yetkisiz eklenti / plug-in | [Personal Account norms](https://help.wechat.com/cgi-bin/readtemplate?lang=en_US&t=page%2Fagreement%2Fpersonal_account) | Lumos istemci içi eklenti **yapamaz** |
| Service provider **resmi website** zorunlu | [How to become a service provider](https://developers.weixin.qq.com/doc/oplatform/en/Third-party_Platforms/2.0/getting_started/how_to_be.html) | welockai.com vitrin gerekli (OD-048 `needs-review`) |
| Cross-Border Pay: institution / merchant model | [WeChat Pay Global docs](https://pay.weixin.qq.com/doc/global/v3/en/4012356424.md) | Ödeme trust katmanı ayrı compliance paketi |

**Hazır SaaS alternatifleri (OSS/piyasa taraması):** WeChat CRM, SCRM, Mini Program agency platformları (WeChat ecosystem partners) mevcuttur. Lumos'un **trust/onay/günlük** odaklı diferansiyasyonu, bu SaaS'ların yerine geçmekten çok **policy gate middleware** olarak konumlanmayı destekler — **sıfırdan WeChat CRM yapmak genelde gereksiz build** olur ([`ozellik-oncesi-hazir-cozum-taramasi.mdc`](../../.cursor/rules/ozellik-oncesi-hazir-cozum-taramasi.mdc) ilkesi).

---

## 6. Veri ikameti ve sınır ötesi transfer

### 6.1 Çin mevzuatı (PIPL / DSL / CSL — yüksek seviye)

| Mekanizma | Açıklama | Kaynak |
|-----------|----------|--------|
| **CAC Security Assessment** | Yüksek hacim / kritik veri | [White & Case — Standard Contract](https://www.whitecase.com/insight-alert/chinas-standard-contract-outbound-cross-border-transfer-personal-information-effect) |
| **Standard Contract (SCC) filing** | Orta ölçekli PI outbound | Aynı |
| **PI Protection Certification** | 2026 itibarıyla tamamlanan üçüncü sütun | [Morgan Lewis — Certification Measures](https://www.morganlewis.com/pubs/2025/10/chinas-data-outbound-rules-update-measures-for-the-certification) |
| **Ayrı rıza (separate consent)** | Sınır ötesi PI transferi için | [Guangzhou Internet Court case — Paul Weiss](https://www.paulweiss.com/insights/client-memos/chinese-court-releases-landmark-decision-on-requirements-for-cross-border-transfer-of-personal-information-under-the-pipl) |

**Lumos senaryosu:** Mainland Çin kullanıcılarının openid, mesaj içeriği, telefon, konum gibi verileri **KKTC/Türkiye/ABD barındırılan Lumos sunucusuna** aktarılırsa, veri sorumlusu muhtemelen **PIPL outbound compliance** yükümlülüğü altına girer [doğrulanmalı — veri hacmi, hassasiyet, işlem amacı].

### 6.2 Tencent tarafı

- WeChat mesajları Tencent altyapısında işlenir; developer yalnızca **push edilen payload**'ı alır.
- **Veri minimizasyonu:** Lumos yalnızca policy kararı için gerekli alanları saklamalı; ham mesaj arşivinin KKTC'ye taşınması **risk artırır**.

### 6.3 Lumos barındırma önerisi (fizibilite — uygulama değil)

| Veri sınıfı | Önerilen konum | Gerekçe |
|-------------|----------------|---------|
| WeChat AppSecret / token | Private vault (`.lumos/internal/`) | [`public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| Mainland user PII | **Çin içi veya onaylı cross-border mekanizma** [doğrulanmalı] | PIPL |
| Audit log (redacted) | Müşteri sözleşmesine göre; varsayılan **EU/KKTC** | GDPR + banka beklentisi |
| Lumos policy kararları | Private professional katman | Ticari sır |

---

## 7. Lisans, doğrulama ve erişim gereksinimleri checklist

### 7.1 Overseas Service Account (KKTC / TR entity)

| # | Gereksinim | Durum |
|---|------------|-------|
| 1 | Geçerli **Certificate of Incorporation / Business License** (KKTC ticaret sicil) | [doğrulanmalı] |
| 2 | **Service Account** tipi (overseas kanalı) | Kayıt |
| 3 | Admin: pasaport/kimlik + **uluslararası telefon** (SMS) | Kayıt |
| 4 | **Verification Application Letter** (imza/mühür) | Doğrulama |
| 5 | Admin **telefon faturası** (≥3 ay) | Doğrulama |
| 6 | **Weixin Verification** ücreti (≈99 USD) | Doğrulama |
| 7 | **Server URL** HTTPS (Çin'den erişilebilir latency) [doğrulanmalı] | Teknik |
| 8 | ICP **gerekmez** (overseas hosting) — mainland sunucu kullanılırsa **ICP gerekir** | [doğrulanmalı] |

### 7.2 Mini Program (overseas)

| # | Gereksinim |
|---|------------|
| 1 | Overseas entity kayıt ([community doc](https://developers.weixin.qq.com/community/business/doc/000a86174e81f0836172539ce6140d)) |
| 2 | 45 gün içinde Weixin Verification |
| 3 | ICP filing: overseas için **muaf** (2024–2026 kaynaklar); politika değişebilir |
| 4 | Trademark adı kullanılıyorsa marka belgesi |

### 7.3 WeCom (overseas)

| # | Gereksinim |
|---|------------|
| 1 | Yurtdışı telefon ile kayıt (web, İngilizce arayüz önerilir) |
| 2 | Enterprise Registration Certificate + Application Letter |
| 3 | Doğrulama ≈700 RMB; **yıllık yenileme** [doğrulanmalı] |

### 7.4 Open Platform (Lumos as service provider)

| # | Gereksinim |
|---|------------|
| 1 | Open Platform hesabı + **developer qualification certification** (≈300 RMB) |
| 2 | Resmi **website** (welockai.com — vitrin eksikleri giderilmeli) |
| 3 | Third-party platform oluşturma + permission set |
| 4 | Merchant scan authorization |

### 7.5 Çin'de temsil / WFOE / ICP

| Senaryo | WFOE / Çin temsilciliği gerekir mi? |
|---------|-------------------------------------|
| Overseas Service Account + overseas hosting | **Hayır** (genel kaynaklar) |
| Mainland WeChat Pay native | **Evet** — mainland entity |
| Mainland Mini Program + mainland sunucu | **Evet** — ICP filing |
| Sadece trust middleware (overseas entity, overseas barındırma) | **Hayır** — ancak PIPL outbound hâlâ geçerli olabilir |

---

## 8. Risk kaydı

| ID | Kategori | Risk | Olasılık | Etki | Azaltma |
|----|----------|------|----------|------|---------|
| R1 | **Regülasyon** | Mainland user PII'nin KKTC/EU'ya transferi PIPL ihlali | Orta | Yüksek | SCC/Certification/Assessment; minimizasyon; Çin hukuk danışmanı |
| R2 | **Platform ToS** | Kişisel WeChat otomasyonu / scraping | Yüksek (kapsama girerse) | Kritik | Kapsam dışı bırak; yalnızca resmi API |
| R3 | **Teknik** | Overseas OA API/limit farkları (Pay, store, rate limit) | Orta | Orta | Mainland partner veya Cross-Border Pay; feature matrix erken doğrulama |
| R4 | **Operasyonel** | Tencent doğrulama red / belge uyumsuzluğu (KKTC unvan) | Orta | Orta | Yetkili partner; belge ön inceleme |
| R5 | **Güvenlik** | AppSecret sızıntısı; gayri resmi third-party | Orta | Yüksek | Vault + Open Platform auth; [`public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| R6 | **Ürün** | Lumos birleşik trust motoru henüz yok (ADR-007) | Yüksek | Orta | Entegrasyon öncesi trust sözleşmesi daraltılmalı |
| R7 | **Coğrafi** | Server URL Çin firewall / latency sorunları | Düşük-Orta | Orta | CDN / Çin-edge hosting değerlendirmesi [doğrulanmalı] |
| R8 | **Ticari** | WeChat entegrasyonu public OSS'e sızmaması | Orta | Yüksek | Private professional katmanda impl |

---

## 9. Öneri çerçevesi (fizibilite — ürün kararı değil)

| Seçenek | Ne zaman | Lumos için anlam |
|---------|----------|------------------|
| **Proceed (dar pilot)** | B2B müşteri doğrulanmış SA/WeCom ile gelir; mainland PII minimal | Webhook middleware + onay kapısı POC |
| **Pilot** | **Önerilen varsayılan** — fizibilite olumlu ama trust motoru + PIPL belirsiz | 1 hesap, 1 use-case, private impl |
| **Defer** | Kişisel WeChat sarmalama beklentisi; mainland ağır PII; ödeme odaklı | Yanlış kanal — mail/Slack önceliği ([OD-031](../memory/mail-integration-approval-decision.md)) |

**Karar ağacı (özet):**

1. Hedef **kişisel WeChat** mi? → **Defer / red**
2. Hedef **işletme hesabı + resmi API** mi? → **Pilot uygun**
3. Mainland PII taşınacak mı? → **Hukuk review olmadan Proceed yok**
4. Lumos trust motoru birleşik değil → entegrasyon **dar policy gate** ile sınırla

---

## 10. Lumos'a özel: public OSS vs private katman

| Bileşen | Public `lumos-core` (Apache-2.0) | Private / professional katman |
|---------|-----------------------------------|-------------------------------|
| WeChat connector kodu | **Demo-safe stub only** (mail stub pattern) | OAuth/token exchange, webhook handler, retry |
| AppSecret / token | **Asla** | Vault (`purpose_codes`) |
| Webhook URL / prod endpoint | **Yok** | Barındırılan API |
| Policy / onay UI | Panel iskelet + ilke docs | Prod confirmation akışı |
| PIPL compliance dokümantasyonu | **Yok** (hassas ops) | Strategy/ops vault |
| Üçüncü taraf platform kaydı | **Yok** | We Lock AI entity adına |

**Repo kanıtı:** `src/integrations/mail/` demo stub mevcut; WeChat için **sıfır kod**. ADR-002 ilkesi (varsayılan kapalı, onaysız gönderim yok) WeChat CS API gönderimleri için **doğrudan uygulanabilir**.

**Çin dışında kalması gerekenler ([`ip-protection-landscape.md` §7.5](./ip-protection-landscape.md#75-çin-china)):**

- Production orchestration, webhook secret, tenant PII
- Cross-border data processing agreements
- WeChat Pay / Cross-Border merchant credential

**Public'te kalabilecekler:**

- Entegrasyon ilkesi (generic messaging channel)
- Trust/onay terminolojisi (ADR-007, ADR-010)
- Demo-safe interface tipleri (grant: `read`, `notify`, `send_with_approval`)

---

## 11. Repo taraması özeti

| Arama | Sonuç |
|-------|--------|
| `WeChat`, `Weixin`, `微信`, `wechat`, `weixin` | **0 eşleşme** |
| Open Decisions / OD | WeChat'e özel OD **yok** |
| `src/integrations/` | Mail + vault stub; WeChat yok |
| Kanal roadmap (OD-031) | Telegram/WhatsApp **private strategy vault**; WeChat listelenmemiş |

**Sonuç:** WeChat entegrasyonu **greenfield** fizibilite; mevcut kod borcu yok.

---

## 12. Kaynaklar (seçilmiş)

| Konu | URL |
|------|-----|
| Service Account — message push | https://developers.weixin.qq.com/doc/service/en/guide/dev/push/ |
| Message encryption | https://developers.weixin.qq.com/doc/service/guide/dev/push/encryption.html |
| Open Platform — become service provider | https://developers.weixin.qq.com/doc/oplatform/en/Third-party_Platforms/2.0/getting_started/how_to_be.html |
| Open Platform — security | https://developers.weixin.qq.com/doc/oplatform/en/Third-party_Platforms/Before_Develop/Security_Management_Instructions.html |
| Overseas Mini Program | https://developers.weixin.qq.com/community/business/doc/000a86174e81f0836172539ce6140d |
| Overseas vs mainland SA comparison | https://developers.weixin.qq.com/community/develop/article/doc/000eacf7e7c9403b0fb3437b76bc13 |
| WeCom partner integration | https://open.work.weixin.qq.com/help2/pc/19643?person_id=0 |
| WeChat Acceptable Use Policy | https://www.wechat.com/en/acceptable_use_policy.html |
| Personal Account norms | https://help.wechat.com/cgi-bin/readtemplate?lang=en_US&t=page%2Fagreement%2Fpersonal_account |
| WeChat Cross-Border Pay | https://pay.weixin.qq.com/doc/global/v3/en/4012356424.md |
| PIPL — Standard Contract | https://www.whitecase.com/insight-alert/chinas-standard-contract-outbound-cross-border-transfer-personal-information-effect |
| PIPL — Certification (2026) | https://www.morganlewis.com/pubs/2025/10/chinas-data-outbound-rules-update-measures-for-the-certification |
| Lumos public boundary | [`docs/memory/public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| Lumos external integrations | [`docs/memory/external-integrations-permissions.md`](../memory/external-integrations-permissions.md) |
| KKTC banka / entity context | [`docs/analysis/bank-readiness-checklist.md`](./bank-readiness-checklist.md) |

---

## 13. Ana soru — tek paragraf yanıt

**Lumos, mevcut WeChat kullanımını bozmadan trust and control katmanı olarak entegre olabilir mi?** **Kısmen evet:** Doğrulanmış **Service Account**, **Mini Program backend** veya **WeCom** üzerinde, Tencent'in resmi webhook ve API akışlarına **araya giren bir policy/onay/günlük middleware** (webhook gate, gönderim öncesi Lumos onayı, Open Platform yetkilendirmesi) kurulduğunda, son kullanıcı WeChat uygulamasında aynı hesapla etkileşmeye devam eder ve Lumos yalnızca sunucu tarafı kararları geciktirir veya onaylatır — bu, Lumos'un [`external-integrations-permissions.md`](../memory/external-integrations-permissions.md) ve ADR-007 trust hedefleri ile uyumludur. **Hayır** senaryosu **kişisel WeChat** (bot, scraping, istemci eklentisi) için geçerlidir; platform kuralları buna izin vermez ve Lumos'un "mevcut kullanım" tanımı işletme API kapsamıyla sınırlıdır. Koşullar: We Lock AI KKTC entity ile overseas doğrulama, HTTPS webhook, AppSecret'ların private vault'ta tutulması, mainland kullanıcı PII'si varsa PIPL outbound compliance [doğrulanmalı], ve implementasyonun **public OSS değil private professional katmanda** kalması.

---

*Belge sonu — `wechat-integration-feasibility` v2026-06-21*
