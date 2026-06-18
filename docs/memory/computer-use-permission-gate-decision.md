# Computer Use izin kapısı — onaylı karar (OD-012)

> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`tools-technology-watchlist.md`](./tools-technology-watchlist.md), [`security-architecture.md`](./security-architecture.md), [`product-rules.md`](./product-rules.md), [`project-workflow.md`](./project-workflow.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

---

## 1. Amaç

OD-012 kapsamında OpenAI **Computer Use** (ve benzeri bilgisayar kullanımı / dış etkili otomasyon yetenekleri) için **izin kapısı onaylı karar kaydını** sabitlemek.

Bu belge:

- Computer Use'un **serbest yetkilendirilmiş bir katman olmadığını** açıkça tanımlar.
- Dış yazma, tıklama, gönderme ve benzeri etkili aksiyonlar için **kullanıcı onayı + Lumos geçidi** zorunluluğunu çerçeveler.
- Okuma/gözlem/öneri modu ile dış etkili aksiyon modunu **katı biçimde ayırır**.
- Kanıt, geri alınabilirlik ve public repo sınırını tekrarlar.

**Uygulama notu:** İlke kararları onaylandı; kod, test, panel, bridge, connector veya otomasyon yapılandırması **henüz başlamadı**.

**Entegrasyon felsefesi:** Computer Use, Lumos dış entegrasyonlarının **tanımı veya tek yolu değildir**; [`external-integrations-permissions.md`](./external-integrations-permissions.md) §Entegrasyon felsefesi kapsamında **izinli yöntemlerden biridir** (resmi API, yerel entegrasyon, erişilebilirlik katmanları ve gelecekteki izinli yöntemlerle birlikte). Amaç kullanıcının yetki verdiği kapsamda sistemi kullanabilmektir; doğrudan API connector'ları ile **aynı izin, onay ve Lumos geçidi omurgasını** paylaşır.

---

## 1b. Onaylanan ilke vs bekleyen uygulama

| Katman | Durum | Kapsam |
|--------|--------|--------|
| **İlke kararları** | `decision-approved` | Computer Use serbest yetkilendirilmiş katman değildir; Lumos geçidi, görev kapsamı ve açık kullanıcı onayı zorunludur; okuma/gözlem/öneri modu ile dış etkili aksiyon modu katı ayrılır; dış yazma/tıklama/gönderme açık onay gerektirir; geri dönüşsüz/kritik aksiyonlar otomatik yapılmaz; kullanıcıya ne/nerede/etki görünürlüğü zorunludur; gerçek kanıt sunulur (mock ≠ gerçek); public repoda secret/protokol yasağı geçerlidir; online modda kimlik/kilit koşulları sağlanmadan dış etkili oturum başlamaz. |
| **Uygulama / teknik detay** | `implementation-pending` | Computer Use teknik entegrasyonu (OpenAI = çekirdek stratejik sağlayıcı; ek sağlayıcılar mimari gerektiğinde isteğe bağlı uzantı); sandbox/izolasyon modeli; onay UX ve oturum süresi; log ve kanıt saklama politikası; gateway oturum iptali ve credential entegrasyonu (OD-001/002 ile örtüşme). Hiçbiri uygulanmadı; bu belge uygulama izni vermez. |
| **Needs-review (açık)** | `needs-review` | Etkisiz vs etkili tıklama sınıflandırması; mod geçişi UI/CLI; çok adımlı görevde ara onay sıklığı; Agents SDK / Realtime / Codex ile birlikte değerlendirme (OD-034, OD-035). |

Bu belge **somut uygulama icat etmez**; onaylanan ilkeler ile bekleyen teknik detay ayrımı korunur.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| OpenAI Computer Use API entegrasyon kodu | Uygulama başlamadı; teknik seçim needs-review |
| Tarayıcı otomasyonu, sandbox VM, OS düzeyi kontrol detayı | Operasyonel/teknik spesifikasyon; public repoda yer almaz |
| Credential, token, API anahtarı, production endpoint | Güvenlik ve public boundary; asla yazılmaz |
| Panel UX akışı, onay ekranı wireframe'i | Ürün uygulaması; ayrı karar/uygulama paketi |
| Bridge, task engine, profil kodu değişikliği | Bu belge onaylı karar kaydıdır; uygulama henüz başlamadı |
| Agents SDK, Realtime, Codex Plugins (OD-034, OD-035) | İlgili ama ayrı değerlendirme maddeleri |
| Gerçek ekran görüntüsü, otomasyon script'i, iç protokol | Demo-safe sınır dışı |

---

## 3. Netleşen ilkeler

Aşağıdaki ilkeler **onaylandı** (`decision-approved`); çekirdek sözleşme ve canonical memory kayıtlarıyla uyumludur.

| # | İlke | Kaynak özeti |
|---|------|--------------|
| CU1 | **Computer Use serbest yetkilendirilmiş bir katman değildir.** Varsayılan olarak kapalıdır; açık görev kapsamı ve onay olmadan çalışmaz. | external-integrations-permissions §OpenAI; tools-technology-watchlist §Risk |
| CU2 | **Computer Use yalnızca Lumos geçidi üzerinden** erişilir; iç katmanlara veya dış sisteme doğrudan bypass yok. | product-rules §4; security-architecture §3 |
| CU3 | **Görev kapsamı (task scope) zorunludur.** Hangi hedef, hangi süre, hangi etki alanı — kullanıcıya görünür ve sınırlıdır. | project-workflow §2; lumos-karar-sozlesmesi §1 |
| CU4 | **Dış etkili aksiyonlar açık kullanıcı onayı gerektirir** — yazma, tıklama, gönderme, satın alma, silme, ödeme, domain, e-posta, dosya gönderimi. | external-integrations-permissions §İzin; lumos-karar-sozlesmesi §2 |
| CU5 | **Okuma/gözlem/öneri modu ile dış etkili aksiyon modu katı ayrılır.** Mod karışımı veya sessiz yükseltme yasaktır. | Bu belge §7; karar katmanları |
| CU6 | **Geri dönüşsüz ve kritik aksiyonlar otomatik yapılmaz** (`SECURITY_NEVER_AUTO`: external_write, irreversible_user_op, critical_system_config). | lumos-karar-sozlesmesi §2 |
| CU7 | **Aksiyon başlamadan önce kullanıcı ne, nerede, hangi etki** görecektir — sessiz veya varsayılan-onaylı uygulama yok. | product-rules §Panel/chat §3 |
| CU8 | **Computer Use sonuçları gerçek kanıtla raporlanır;** mock veya üretilmiş çıktı gerçek sonuç gibi sunulmaz. | project-workflow §7 |
| CU9 | **Public repoda production credential, hassas iç protokol ve otomasyon sırrı bulunmaz.** | security-architecture §Public; public boundary kuralları |
| CU10 | **Online işlem için kimlik ve kilit/presence koşulları** sağlanmadan dış etkili Computer Use başlatılmaz. | security-architecture §Kimlik; lumos-karar-sozlesmesi §2 |

---

## 4. Computer Use rol tanımı

**Onaylı karar (firm):** Computer Use, Lumos'un **kontrollü dış etki aracı**dır; bağımsız veya otonom bir katman değildir. Lumos entegrasyon modelinin **bütünü değildir** — yalnızca §Entegrasyon felsefesi (`external-integrations-permissions.md`) altındaki **izinli yöntemlerden biri**; teknik yöntem ikincil, kullanıcı yetkisi birincildir.

| Boyut | Tanım |
|-------|--------|
| **Amaç** | Kullanıcı onaylı, görev kapsamına bağlı bilgisayar/tarayıcı düzeyi işlemler (okuma, gözlem veya onaylı dış etki). API connector veya diğer izinli yollar mümkün olduğunda aynı omurgada tercih edilebilir. |
| **Konum** | Lumos geçidi arkasında; kullanıcıya yalnızca Lumos yüzeyi üzerinden görünür. |
| **İlişki** | Görev motoru ve yetki profili (`rapor`, `guvenli_yurut`, `kisitli_otonom`) ile hizalı; `critical` ve `external` adımlar asla otomatik değildir. |
| **Varsayılan** | Kapalı / pasif; açık görev + onay + geçit olmadan etkinleştirilmez. |
| **Watchlist** | `tools-technology-watchlist.md` ve `external-integrations-permissions.md` altında izlenir; otomatik entegrasyon yok. |
| **Stratejik sağlayıcı (firm)** | **OpenAI**, Lumos çekirdeğinin stratejik AI sağlayıcısıdır; Computer Use değerlendirmesi ve varsayılan yön bu çerçevededir. "Hangi sağlayıcı?" sorusu **kapalı** — OpenAI çekirdek varsayılan/stratejik sağlayıcıdır. |
| **Ek sağlayıcılar** | Mimari gerektiğinde ek sağlayıcı desteği isteğe bağlı uzantı olarak düşünülebilir; çoklu-vendor spesifikasyonu bu belgede tanımlanmaz. |

**Implementation-pending:** Computer Use teknik entegrasyonu (OpenAI stratejik sağlayıcı üzerinden); sandbox/izolasyon modeli. **Needs-review:** Çok adımlı görevde ara onay sıklığı.

---

## 5. İzin kapısı ve kullanıcı onayı

Computer Use için **çok katmanlı izin kapısı** hedeflenir:

```
[ Kullanıcı görünürlüğü: ne / nerede / etki ]
        ↓
[ Görev kapsamı + yetki profili ]
        ↓
[ Mod seçimi: okuma-gözlem | dış-etkili-aksiyon ]
        ↓
[ Açık kullanıcı onayı (dış etki gerekiyorsa) ]
        ↓
[ Lumos gateway ]
        ↓
[ İzinli Computer Use oturumu ]
        ↓
[ Dış sistem / tarayıcı / uygulama ]
```

| Kapı | Kural |
|------|--------|
| **Yetki profili** | `rapor`: yalnızca analiz/okuma/plan/simülasyon; dış etki yok. `guvenli_yurut`: safe_local; dış etki yine onay kapısından. `kisitli_otonom`: genel onay açıkken sınırlı write_local; Computer Use dış etkisi ayrı onay katmanı. |
| **Genel onay** | Genel onay, Computer Use dış yazma/tıklama/gönderme için **tek başına yeterli değildir**; işlem bazlı açık onay gerekir. |
| **Kilit / kimlik** | Online modda kilit açık ve kimlik doğrulanmadan dış etkili oturum başlamaz. |
| **Kapsam sınırı** | Oturum hedefi, süresi ve izin verilen etki türü önceden tanımlı; kapsam dışı adım durdurulur. |
| **Varsayılan-onay yasağı** | Sessiz, önceden işaretli veya zaman aşımıyla geçerli sayılan onay yok. |

**Implementation-pending:** Onay UX biçimi; oturum süresi ve yenileme. **Needs-review:** Genel onay ile işlem onayı çakışma kuralları.

---

## 6. Dış yazma / tıklama / gönderme sınırı

Aşağıdaki aksiyon kategorileri **açık kullanıcı onayı olmadan** Computer Use ile yapılmaz:

| Kategori | Örnek etki (genel) | Onay |
|----------|-------------------|------|
| **Dış yazma** | Form doldurma, dosya yükleme, ayar değiştirme, commit/push benzeri dış sistem yazımı | Zorunlu |
| **Tıklama / navigasyon (etkili)** | Satın al, onayla, gönder, sil, öde, abone ol, domain al | Zorunlu |
| **Gönderme** | E-posta, mesaj, dosya paylaşımı, API POST/PUT ile dış etki | Zorunlu |
| **Ödeme / satın alma** | Kart, abonelik, fatura, domain yenileme | Zorunlu + çekirdek sözleşme |
| **Silme** | Kalıcı veya geri alınamaz silme, hesap kapatma | Zorunlu; otomatik asla |
| **Domain** | Kayıt, transfer, DNS değişikliği | Zorunlu |
| **E-posta** | Okuma, gönderme, silme, arşivleme | Ayrı onay katmanı |
| **Dosya gönderimi** | Dış platforma upload, paylaşım linki oluşturma | Zorunlu |

**Okuma/gözlem sınırı (düşük etki):** Ekran okuma, liste görüntüleme, durum kontrolü — yine Lumos geçidi ve görev kapsamı içinde; credential veya hassas veri sızdırmadan. Okuma bile kullanıcıya hangi kaynak/hedef olduğu görünür olmalıdır.

**Needs-review:** "Etkisiz tıklama" (ör. sekme değiştirme, scroll) ile "etkili tıklama" sınıflandırma listesi; form alanı düzenleme vs salt okuma ayrımı.

---

## 7. Okuma / gözlem / öneri modu ayrımı

Karar katmanları (`lumos-karar-sozlesmesi.md` §1) ile hizalı **mod ayrımı**:

| Mod | Karar katmanı | Computer Use davranışı | Dış etki |
|-----|---------------|------------------------|----------|
| **Okuma / gözlem** | Analiz et, uygulama yapma | Ekran/kaynak okuma, durum toplama; kanıtlı rapor | Yok veya minimal (salt okuma) |
| **Öneri** | Öner ama bekle | Tespit + önerilen adımlar; uygulama yok | Yok |
| **Dış etkili aksiyon** | Açık onayla uygula | Onaylı tıklama/yazma/gönderme | Var — açık onay şart |
| **Yasak** | Asla dokunma | Kalıcı silme, ödeme, kritik ayar — otomatik veya onaysız yok | Asla otomatik |

**Firm kurallar:**

1. Modlar **karıştırılamaz** — okuma oturumundan dış yazmaya sessiz geçiş yok.
2. Mod yükseltmesi (gözlem → aksiyon) **yeni onay** gerektirir.
3. `rapor` profilinde Computer Use yalnızca simülasyon veya salt okuma düzeyinde; gerçek dış etki yok.
4. Öneri modunda "yapıldı" iddiası yasak; yalnızca "şunu yapabilirim, onaylıyor musun?" düzeyi.

**Needs-review:** Mod geçişinin UI/CLI sözdizimi; ara adımlarda otomatik duraklama politikası.

---

## 8. Riskli ve yasak aksiyonlar

### Yasak (onaysız veya otomatik)

| # | Aksiyon | Gerekçe |
|---|---------|---------|
| Y1 | Onaysız dış yazma, tıklama, gönderme | external-integrations-permissions; SECURITY_NEVER_AUTO |
| Y2 | Otomatik ödeme, domain satın alma, abonelik | lumos-karar-sozlesmesi §2 |
| Y3 | Otomatik kalıcı silme, hesap kapatma | irreversible_user_op |
| Y4 | Kritik sistem / güvenlik ayarı değişikliği | critical_system_config |
| Y5 | Credential, token veya secret'ın Lumos yüzeyinde veya logda açığa çıkarılması | security-architecture |
| Y6 | Belirsiz kökenli toplu veri import veya arka plan senkronu | external-integrations-permissions §Provenance |
| Y7 | Mock veya simüle çıktının gerçek Computer Use sonucu gibi sunulması | project-workflow §7 |
| Y8 | Lumos geçidini bypass eden doğrudan Computer Use bağlantısı | product-rules §4 |
| Y9 | Kapsam dışı hedefe veya süresiz oturuma uzatma | Bu belge §5 |

### Yüksek risk (ekstra onay / tek adım — needs-review)

- Çok adımlı iş akışları (onay her N adımda mı, başta mı)
- Üçüncü taraf ödeme veya kimlik doğrulama ekranları
- Toplu dosya işlemi veya çoklu alıcıya gönderim
- Üretim ortamına (production) etkili değişiklik

---

## 9. Lumos gateway ile ilişki

Computer Use, **dış entegrasyonlar ve izinler** belgesindeki gateway ilkesiyle aynı omurgayı paylaşır:

```
[ Kullanıcı onayı ] → [ Lumos gateway ] → [ İzinli Computer Use oturumu ] → dış sistem
[ UI kısayolu ]     → tarayıcı / manuel adım (otomatik Computer Use veri akışı yok)
```

| İlke | Açıklama |
|------|----------|
| **Tek geçit** | Tüm Computer Use trafiği Lumos kontrolünden geçer; iç katmanlara doğrudan köprü yok. |
| **Bridge sınırı** | Bridge yalnızca yetkili, onaylı ve Lumos kontrollü dış iletişim kanalıdır. |
| **Otomatik vs kısayol** | UI kısayolu yalnızca yönlendirme; credential veya otomatik Computer Use akışı değildir. |
| **Provenance** | Dış içerik hangi sistem, hesap, zaman — kullanıcıya görünür. |
| **Offline** | Offline modda dış/network ve Computer Use dış etkisi yok. |

**Implementation-pending:** Gateway oturum iptali/geri çekme; bridge ile credential entegrasyonu (OD-001/002 ile örtüşme).

---

## 10. Kayıt / kanıt / geri alınabilirlik

| Gereksinim | Kural |
|------------|--------|
| **Kanıt türü** | Gerçek ekran görüntüsü, terminal/log çıktısı, dosya içeriği — mock değil. |
| **Raporlama** | Computer Use adım sonucu: başarı/başarısızlık, hedef, zaman, kapsam özeti kullanıcıya sunulur. |
| **Mock ayrımı** | Simülasyon veya taslak açıkça etiketlenir; `result_kind` / görev durumu ile uyumlu. |
| **Geri alınabilirlik** | Mümkün olan işlemlerde geri alma veya durdurma yolu hedeflenir; geri dönüşsüz işlemde tek satır uyarı zorunlu. |
| **Log** | Operasyonel log politikası `implementation-pending`; secret ve PII loga yazılmaz (firm). |
| **Trash prensibi** | Lumos içi silinen içerik trash'e; Computer Use ile dış kalıcı silme otomatik değil. |

**Implementation-pending:** Oturum kaydı saklama süresi; kanıt dosyalarının konumu; kullanıcıya gösterilecek özet derinliği (log/kanıt politikası).

---

## 11. Public repo sınırı

Public `lumos-core` için Computer Use onaylı karar filtresi:

**Taşınmaz / yazılmaz:**

- Production credential, API anahtarı, token, passphrase
- Gerçek production URL ve operasyonel endpoint
- Tarayıcı otomasyonu implementasyon detayı, selector, iç protokol
- Kullanıcı verisi, PII, hesap bilgisi
- Özel entegrasyon ve operasyonel backend altyapısı

**Taşınabilir (bu belge düzeyi):**

- İzin kapısı ilkeleri ve mod ayrımı
- Onay modeli özeti (teknik olmayan)
- Risk tablosu ve yasak aksiyon listesi
- OD eşleme ve needs-review işaretleri

Computer Use **uygulama kodu** public repoda yalnızca demo-safe, placeholder veya foundation düzeyinde olabilir; production özellikleri private katmanda kalır (`public-github-boundary` kuralları).

---

## 12. Açık kararlar

| Konu | Durum | Not |
|------|--------|-----|
| Computer Use serbest katman değil | **decision-approved** | CU1 |
| Lumos geçidi + görev kapsamı + onay zorunlu | **decision-approved** | CU2–CU4 |
| Okuma vs dış etki mod ayrımı | **decision-approved** | CU5, §7 |
| Dış yazma/tıklama/gönderme açık onay | **decision-approved** | §6 |
| Geri dönüşsüz/kritik otomatik yok | **decision-approved** | CU6 |
| Kullanıcıya ne/nerede/etki görünürlüğü | **decision-approved** | CU7 |
| Gerçek kanıt; mock ≠ gerçek | **decision-approved** | CU8 |
| Public repo secret/protokol yasağı | **decision-approved** | CU9 |
| Online kimlik/kilit koşulu | **decision-approved** | CU10 |
| OpenAI çekirdek stratejik AI sağlayıcısı | **decision-approved** | §4 — ek sağlayıcılar mimari gerektiğinde isteğe bağlı uzantı |
| Computer Use teknik entegrasyonu ve sandbox modeli | **implementation-pending** | §4 — OpenAI stratejik sağlayıcı; entegrasyon/sandbox detayı bekliyor |
| Onay UX ve oturum süresi | **implementation-pending** | §5 |
| Log ve kanıt saklama politikası | **implementation-pending** | §10 |
| Gateway oturum iptali ve credential entegrasyonu | **implementation-pending** | §9; OD-001/002 |
| Etkisiz vs etkili tıklama sınıflandırması | needs-review | §6 |
| Mod geçişi UI/CLI | needs-review | §7 |
| Agents SDK / Realtime / Codex ile birlikte değerlendirme | needs-review | OD-034, OD-035 |

---

## 13. OD eşleme tablosu

| OD | Kaynak | Konu | Bu belgedeki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-012** | external-integrations-permissions.md | Computer Use kapısı — onaysız dış yazma riskine karşı onay katmanı | Bu belgenin tamamı; §5, §6, §7 | **decision-approved / implementation-pending** |
| OD-034 | external-integrations-permissions.md | OpenAI Agents / Realtime onay kapısı | §4, §9 — ayrı değerlendirme | needs-review |
| OD-035 | external-integrations-permissions.md | Codex Plugins onay modeli | §11 public sınır | needs-review |
| OD-031 | external-integrations-permissions.md | İletişim kanalları otomasyon modeli (mail ilk kanal) | §6 e-posta satırı ile örtüşür; [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) | **decision-approved / implementation-pending** |
| OD-032 | external-integrations-permissions.md | Takvim + Kişiler — granüler izin ve onay omurgası | Aynı hibrit onay/ dış etki kapısı; [`calendar-contacts-decision.md`](./calendar-contacts-decision.md) | **decision-approved / implementation-pending** |
| OD-033 | external-integrations-permissions.md | Platform connector'ları / çalışma araçları | Aynı hibrit onay/ dış etki kapısı; Computer Use platform erişimi aynı izin tablosu; [`work-tools-connectors-decision.md`](./work-tools-connectors-decision.md) | **decision-approved / implementation-pending** |
| OD-011 | commercial-domain-payments.md | Ödeme sistemi kapsamı | §6, §8 — ödeme otomatik yok | needs-review |
| OD-041 | commercial-domain-payments.md | Ticari onay modeli | §5 — işlem bazlı onay | needs-review |
| OD-001/002 | security-architecture.md | Vault / token | §9 credential enjeksiyonu | needs-review |

**İndeks notu:** `open-decisions-needs-review.md` OD-012 satırı bu belgeyle senkron tutulur; canonical kaynak önce `external-integrations-permissions.md`, onaylı karar özeti bu dosyadır.

---

## 14. Sonraki adım

1. **Implementation-pending (devam):** Computer Use teknik entegrasyonu (OpenAI stratejik sağlayıcı), sandbox modeli, onay UX, log/kanıt politikası, credential entegrasyonu — uygulama paketi değerlendirmesi.
2. **Needs-review (devam):** Etkisiz vs etkili tıklama sınıflandırması; mod geçişi UI/CLI; çok adımlı görevde ara onay sıklığı.
3. Computer Use değerlendirmesi **tek parça** olarak watchlist kriterlerine (`tools-technology-watchlist.md` §Kabul) tabi tutulur; Agents SDK / Realtime ile toplu entegrasyon yapılmaz (OD-034, OD-035 ayrı).
4. Uygulama başlamadan önce vault/credential modeli (OD-001/002) ile gateway oturum sınırı hizalanır.

**Yasak (bu aşamada):** kod, test, panel, bridge, connector, otomasyon yapılandırması, Computer Use teknik entegrasyonu, sandbox kurulumu, credential, endpoint, secret.

---

Son güncelleme: 2026-06-18
