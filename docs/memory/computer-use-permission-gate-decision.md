# Computer Use izin kapısı — karar taslağı (OD-012)

> **Durum:** Karar taslağı — **uygulama başlamadı**; bu doküman kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu taslağı gevşetemez.
>
> **Canonical kaynaklar:** [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`tools-technology-watchlist.md`](./tools-technology-watchlist.md), [`security-architecture.md`](./security-architecture.md), [`product-rules.md`](./product-rules.md), [`project-workflow.md`](./project-workflow.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

---

## 1. Amaç

OD-012 kapsamında OpenAI **Computer Use** (ve benzeri bilgisayar kullanımı / dış etkili otomasyon yetenekleri) için **izin kapısı karar taslağını** sabitlemek.

Bu belge:

- Computer Use'un **serbest yetkilendirilmiş bir katman olmadığını** açıkça tanımlar.
- Dış yazma, tıklama, gönderme ve benzeri etkili aksiyonlar için **kullanıcı onayı + Lumos geçidi** zorunluluğunu çerçeveler.
- Okuma/gözlem/öneri modu ile dış etkili aksiyon modunu **katı biçimde ayırır**.
- Kanıt, geri alınabilirlik ve public repo sınırını tekrarlar.

**Uygulama notu:** Bu aşamada kod, test, panel, bridge, connector veya otomasyon yapılandırması değişikliği yapılmaz; yalnızca karar çerçevesi dokümante edilir.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| OpenAI Computer Use API entegrasyon kodu | Uygulama başlamadı; teknik seçim needs-review |
| Tarayıcı otomasyonu, sandbox VM, OS düzeyi kontrol detayı | Operasyonel/teknik spesifikasyon; public repoda yer almaz |
| Credential, token, API anahtarı, production endpoint | Güvenlik ve public boundary; asla yazılmaz |
| Panel UX akışı, onay ekranı wireframe'i | Ürün uygulaması; ayrı karar/uygulama paketi |
| Bridge, task engine, profil kodu değişikliği | Bu belge yalnızca karar taslağıdır |
| Agents SDK, Realtime, Codex Plugins (OD-034, OD-035) | İlgili ama ayrı değerlendirme maddeleri |
| Gerçek ekran görüntüsü, otomasyon script'i, iç protokol | Demo-safe sınır dışı |

---

## 3. Netleşen ilkeler

Aşağıdaki ilkeler **firm** (kesin) kabul edilir; çekirdek sözleşme ve canonical memory kayıtlarıyla uyumludur.

| # | İlke | Kaynak özeti |
|---|------|--------------|
| CU1 | **Computer Use serbest yetkilendirilmiş bir katman değildir.** Varsayılan olarak kapalıdır; açık görev kapsamı ve onay olmadan çalışmaz. | external-integrations-permissions §OpenAI; tools-technology-watchlist §Risk |
| CU2 | **Computer Use yalnızca Lumos geçidi üzerinden** erişilir; iç katmanlara veya dış sisteme doğrudan bypass yok. | product-rules §4; security-architecture §3 |
| CU3 | **Görev kapsamı (task scope) zorunludur.** Hangi hedef, hangi süre, hangi etki alanı — kullanıcıya görünür ve sınırlıdır. | project-workflow §2; lumos-karar-sozlesmesi §1 |
| CU4 | **Dış etkili aksiyonlar açık kullanıcı onayı gerektirir** — yazma, tıklama, gönderme, satın alma, silme, ödeme, domain, e-posta, dosya gönderimi. | external-integrations-permissions §İzin; lumos-karar-sozlesmesi §2 |
| CU5 | **Okuma/gözlem/öneri modu ile dış etkili aksiyon modu katı ayrılır.** Mod karışımı veya sessiz yükseltme yasaktır. | Bu taslak §7; karar katmanları |
| CU6 | **Geri dönüşsüz ve kritik aksiyonlar otomatik yapılmaz** (`SECURITY_NEVER_AUTO`: external_write, irreversible_user_op, critical_system_config). | lumos-karar-sozlesmesi §2 |
| CU7 | **Aksiyon başlamadan önce kullanıcı ne, nerede, hangi etki** görecektir — sessiz veya varsayılan-onaylı uygulama yok. | product-rules §Panel/chat §3 |
| CU8 | **Computer Use sonuçları gerçek kanıtla raporlanır;** mock veya üretilmiş çıktı gerçek sonuç gibi sunulmaz. | project-workflow §7 |
| CU9 | **Public repoda production credential, hassas iç protokol ve otomasyon sırrı bulunmaz.** | security-architecture §Public; public boundary kuralları |
| CU10 | **Online işlem için kimlik ve kilit/presence koşulları** sağlanmadan dış etkili Computer Use başlatılmaz. | security-architecture §Kimlik; lumos-karar-sozlesmesi §2 |

---

## 4. Computer Use rol tanımı

**Karar taslağı (firm):** Computer Use, Lumos'un **kontrollü dış etki aracı**dır; bağımsız veya otonom bir katman değildir.

| Boyut | Tanım |
|-------|--------|
| **Amaç** | Kullanıcı onaylı, görev kapsamına bağlı bilgisayar/tarayıcı düzeyi işlemler (okuma, gözlem veya onaylı dış etki). |
| **Konum** | Lumos geçidi arkasında; kullanıcıya yalnızca Lumos yüzeyi üzerinden görünür. |
| **İlişki** | Görev motoru ve yetki profili (`rapor`, `guvenli_yurut`, `kisitli_otonom`) ile hizalı; `critical` ve `external` adımlar asla otomatik değildir. |
| **Varsayılan** | Kapalı / pasif; açık görev + onay + geçit olmadan etkinleştirilmez. |
| **Watchlist** | `tools-technology-watchlist.md` ve `external-integrations-permissions.md` altında izlenir; otomatik entegrasyon yok. |

**Needs-review:** Hangi sağlayıcı/API (OpenAI Computer Use veya eşdeğer) önce değerlendirilecek; sandbox/izolasyon modeli; çok adımlı görevde ara onay sıklığı.

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

**Needs-review:** Onay UX biçimi (tek tık / passphrase / adım adım); oturum süresi ve yenileme; genel onay ile işlem onayı çakışma kuralları.

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
| Y9 | Kapsam dışı hedefe veya süresiz oturuma uzatma | Bu taslak §5 |

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

**Needs-review:** Gateway içinde Computer Use oturum kimliği, iptal/geri çekme API'si, bridge ile vault/credential enjeksiyon modeli (OD-001/002 ile örtüşme).

---

## 10. Kayıt / kanıt / geri alınabilirlik

| Gereksinim | Kural |
|------------|--------|
| **Kanıt türü** | Gerçek ekran görüntüsü, terminal/log çıktısı, dosya içeriği — mock değil. |
| **Raporlama** | Computer Use adım sonucu: başarı/başarısızlık, hedef, zaman, kapsam özeti kullanıcıya sunulur. |
| **Mock ayrımı** | Simülasyon veya taslak açıkça etiketlenir; `result_kind` / görev durumu ile uyumlu. |
| **Geri alınabilirlik** | Mümkün olan işlemlerde geri alma veya durdurma yolu hedeflenir; geri dönüşsüz işlemde tek satır uyarı zorunlu. |
| **Log** | Operasyonel log formatı needs-review; secret ve PII loga yazılmaz. |
| **Trash prensibi** | Lumos içi silinen içerik trash'e; Computer Use ile dış kalıcı silme otomatik değil. |

**Needs-review:** Oturum kaydı saklama süresi; kanıt dosyalarının konumu; kullanıcıya gösterilecek özet derinliği.

---

## 11. Public repo sınırı

Public `lumos-core` için Computer Use karar taslağı filtresi:

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

Aşağıdaki maddeler bu taslakta **firm ilke** olarak sabitlenmiş; **teknik/ürün detayı** `needs-review` olarak kalır:

| Konu | Durum | Not |
|------|--------|-----|
| Computer Use serbest katman değil | **firm** | CU1 |
| Lumos geçidi + görev kapsamı + onay zorunlu | **firm** | CU2–CU4 |
| Okuma vs dış etki mod ayrımı | **firm** | CU5, §7 |
| Dış yazma/tıklama/gönderme açık onay | **firm** | §6 |
| Geri dönüşsüz/kritik otomatik yok | **firm** | CU6 |
| Kullanıcıya ne/nerede/etki görünürlüğü | **firm** | CU7 |
| Gerçek kanıt; mock ≠ gerçek | **firm** | CU8 |
| Public repo secret/protokol yasağı | **firm** | CU9 |
| Sağlayıcı seçimi ve sandbox modeli | needs-review | §4 |
| Onay UX ve oturum süresi | needs-review | §5 |
| Etkisiz vs etkili tıklama sınıflandırması | needs-review | §6 |
| Mod geçişi UI/CLI | needs-review | §7 |
| Gateway oturum iptali ve credential enjeksiyonu | needs-review | §9; OD-001/002 |
| Log ve kanıt saklama politikası | needs-review | §10 |
| Agents SDK / Realtime / Codex ile birlikte değerlendirme | needs-review | OD-034, OD-035 |

---

## 13. OD eşleme tablosu

| OD | Kaynak | Konu | Bu taslaktaki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-012** | external-integrations-permissions.md | Computer Use kapısı — onaysız dış yazma riskine karşı onay katmanı | Bu belgenin tamamı; §5, §6, §7 | needs-review → taslak firm ilkeler |
| OD-034 | external-integrations-permissions.md | OpenAI Agents / Realtime onay kapısı | §4, §9 — ayrı değerlendirme | needs-review |
| OD-035 | external-integrations-permissions.md | Codex Plugins onay modeli | §11 public sınır | needs-review |
| OD-031 | external-integrations-permissions.md | Mail entegrasyonu onay modeli | §6 e-posta satırı ile örtüşür | needs-review |
| OD-011 | commercial-domain-payments.md | Ödeme sistemi kapsamı | §6, §8 — ödeme otomatik yok | needs-review |
| OD-041 | commercial-domain-payments.md | Ticari onay modeli | §5 — işlem bazlı onay | needs-review |
| OD-001/002 | security-architecture.md | Vault / token | §9 credential enjeksiyonu | needs-review |

**İndeks notu:** OD-012 bu taslakla **karar çerçevesi netleşmiş** sayılır; uygulama ve teknik detaylar kapanmadan indeks durumu `needs-review` kalabilir (kaynak dosya senkronu ayrı adım).

---

## 14. Sonraki adım

1. Bu taslağı `external-integrations-permissions.md` §OpenAI ajan ve computer-use araçları ile çapraz referans olarak işaretle (manuel senkron — bu oturumda yapılmadı).
2. Onay UX ve etkili/etkisiz aksiyon sınıflandırması için dar ürün oturumu aç; tek ihtiyaç: **işlem öncesi görünürlük metni**.
3. Computer Use değerlendirmesi **tek parça** olarak watchlist kriterlerine (`tools-technology-watchlist.md` §Kabul) tabi tutulur; Agents SDK / Realtime ile toplu entegrasyon yapılmaz.
4. Uygulama başlamadan önce vault/credential modeli (OD-001/002) ile gateway oturum sınırı hizalanır.

---

Son güncelleme: 2026-06-17
