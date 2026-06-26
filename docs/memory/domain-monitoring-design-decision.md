# Domain izleme ve marka koruma tasarım kararı — taslak (OD-042)

> **Durum:** `decision-approved` — ürün ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`commercial-domain-payments.md`](./commercial-domain-payments.md), [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md), [`payment-scope-decision.md`](./payment-scope-decision.md), [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

**Kaynak OD:** OD-042 (`commercial-domain-payments.md` — Domain ve marka koruma)

---

## Amaç

OD-042 kapsamında marka koruma **domain izleme**, **risk sunumu** ve **kullanıcı karar akışı** için ürün ilkelerini netleştirmek.

Bu belge:

- Hangi domain'lerin izleneceğini, veri kaynağı **kategorilerini** ve risk çerçevesini tanımlar (somut sağlayıcı seçimi değil).
- İzleme akışını satın alma/ödeme akışından **ayırır** (OD-041 hizası).
- Ödeme kapsamı dışında kaldığını tekrarlar (OD-011 hizası).
- Public repo sınırlarını sabitler.

**Uygulama notu:** İlke kararları onaylandı; kod, registrar entegrasyonu, üçüncü taraf API bağlantısı, panel/dashboard implementasyonu, alarm altyapısı veya otomatik satın alma **henüz başlamadı**.

---

## Kapsam

| Dahil | Hariç |
|-------|--------|
| Marka koruma domain izleme ilkeleri | Domain satın alma/yenileme uygulaması (OD-011 ödeme paketi) |
| Müsaitlik, fiyat sinyali, risk sunumu modeli | PSP, checkout, ödeme gateway |
| Kullanıcı karar → satın alma yönlendirme akışı (onay kapısı) | Registrar credential, production API endpoint |
| Rapor vs alarm mantığı (ilke) | OD-039 redirect teknik uygulaması |
| Watchlist ve varyasyon ilkeleri | Özel marka risk algoritması veya skor formülü |
| Oturum bazlı izleme izni (OD-041) | Otomatik domain edinimi veya yenileme |

**Çelişki çözümü:** `commercial-domain-payments.md` Domain ve marka koruma bölümündeki `[needs-review]` izleme tasarımı ifadesi bu belgeyle **netleştirilir**; canonical izleme kararı bu dosyadır.

---

## Karar özeti

**Onaylı karar (firm):** Marka koruma izleme **bilgi katmanıdır**; dış etkili ticari aksiyon değildir. Akış beş adımlıdır ve otomatik satın alma içermez.

```
[ 1. İzle ] → [ 2. Riskleri göster ] → [ 3. Kullanıcı karar verir ]
      → [ 4. Satın alma (işlem bazlı onay) ] → [ 5. Redirect (OD-039 — sonra) ]
```

| # | Kural | Durum |
|---|--------|--------|
| DM1 | Lumos, marka koruma için **benzer domain varyasyonlarını** ve kullanıcı tanımlı watchlist'i izleyebilir. | `decision-approved` |
| DM2 | Birincil marka hedefi: **`welockai.com`** — korunur, hedef olarak saklanır. | `decision-approved` |
| DM3 | Kullanıcıya **kaynak**, **müsaitlik**, **fiyat sinyali** ve **risk** bilgisi sunulur; otomatik uygulama yok. | `decision-approved` |
| DM4 | **Açık kullanıcı onayı olmadan** domain satın alma, yenileme veya ödeme başlatılmaz. | `decision-approved` |
| DM5 | İzleme ve raporlama **oturum bazlı izin** katmanındadır (OD-041 CA1); satın alma **işlem bazlı açık onay** gerektirir. | `decision-approved` |
| DM6 | İzleme akışı ödeme sistemi kapsamı **dışındadır** (OD-011); ödeme altyapısı olmadan bilgi sunumu yapılabilir. | `decision-approved` |
| DM7 | Edinilen varyasyon domain'ler birincil domain'e yönlendirilir — teknik detay **OD-039**'da kalır. | `decision-approved` (ilke) / OD-039 `implementation-pending` (teknik) — [`domain-redirect-model-decision.md`](./domain-redirect-model-decision.md) |
| DM8 | Lumos kullanıcı adına **sessiz** domain edinimi veya alarm tetiklemeli otomatik satın alma yapmaz. | `decision-approved` |

---

## 1. İzlenen domain'ler

### 1.1 Birincil marka hedefi (firm)

| Öğe | Karar |
|-----|--------|
| Birincil domain | **`welockai.com`** |
| Rol | Korunan marka hedefi; varyasyonların karşılaştırma referansı |
| Otomatik edinim | **Yasak** — yalnızca kullanıcı kararı ve işlem onayı ile |

### 1.2 Marka varyasyonları (firm ilke)

Lumos, marka koruma kapsamında **benzer domain varyasyonlarını** izleyebilir. Varyasyon üretimi **kural tabanlı ilkelerle** yapılır; sabit bir vendor listesi veya kapalı algoritma bu belgede tanımlanmaz.

**Örnek varyasyon kategorileri (ilke — exhaustive değil):**

| Kategori | Örnek desen | Amaç |
|----------|-------------|------|
| Yazım varyasyonu | Harf ekleme/çıkarma, tire/nokta farkı | Typosquatting benzeri karışıklık |
| TLD varyasyonu | Farklı üst düzey domain uzantıları | Marka taklidi farklı uzantılarda |
| Kelime birleşimi | Marka + yaygın ek (ai, app, lock vb.) | İlişkili marka karışıklığı |
| Homoglyph / görsel benzerlik | Benzer görünen karakterler | Kullanıcı yanıltma riski |

**Firm karar:** Varyasyon seti **dinamik** üretilebilir; kullanıcıya hangi varyasyonların izlendiği **şeffaf** gösterilir.

### 1.3 Kullanıcı tanımlı watchlist (firm ilke)

| Öğe | Karar |
|-----|--------|
| Kullanıcı ekleme | Kullanıcı belirli domain'leri watchlist'e ekleyebilir |
| Kapsam | Watchlist, otomatik marka varyasyon setine **ek** veya **özel** liste olabilir |
| Silme / düzenleme | Kullanıcı kontrolünde; Lumos sessizce watchlist genişletmez |
| Onay | Watchlist'e ekleme **dış etkili ticari aksiyon değildir**; oturum izni yeterlidir |

**Implementation-pending:** Watchlist UI/CLI sözdizimi, maksimum liste boyutu, paylaşılan vs kişisel watchlist modeli.

### 1.4 İzlenmeyen / kapsam dışı

- Kullanıcı onayı olmadan watchlist'e toplu ekleme
- Üçüncü taraf marka veritabanının tam kopyası veya otomatik genişletilmiş izleme (kullanıcıya açıklanmadan)
- İzleme listesinin ticari satın alma listesine **otomatik dönüşmesi**

---

## 2. Veri kaynağı kategorileri

Bu bölüm **değerlendirme adayları** ve kategori çerçevesidir; **nihai sağlayıcı seçimi yapılmamıştır**.

### 2.1 Kategori tablosu

| Kategori | Açıklama | Tipik veri | Lumos rolü |
|----------|----------|------------|------------|
| **A — WHOIS / registrar API** | Domain kayıt durumu, müsaitlik, kayıt süresi | Müsaitlik, kayıtlı mı, son kullanma (kaynak izin veriyorsa) | Bilgi toplama; oturum izni |
| **B — Üçüncü taraf marka koruma** | Marka izleme, typosquatting tespiti, ihlal raporlama hizmetleri | Risk sinyali, benzer domain listesi, ihlal uyarısı | Bilgi toplama veya rapor birleştirme; credential vault'ta |
| **C — Hibrit** | A + B veya çoklu kaynak birleştirme | Çapraz doğrulama, tekilleştirilmiş rapor | Kaynak şeffaflığı ile sunum |

### 2.2 Değerlendirme adayları (implementation-pending)

Aşağıdakiler **kategori örneğidir**; isim, sözleşme veya entegrasyon kararı **verilmemiştir**:

| Aday türü | Kategori | Not |
|-----------|----------|-----|
| Registrar WHOIS / availability API | A | Müsaitlik ve fiyat sinyali için yaygın yol |
| ICANN / RDAP tabanlı sorgu | A | Kayıt meta verisi; rate limit ve kullanım koşulları ayrı değerlendirme |
| Marka koruma SaaS (genel kategori) | B | Typosquatting listesi; **somut ürün seçilmedi** |
| Manuel / kullanıcı tetiklemeli sorgu | A veya C | Düşük frekans; oturum içi tek seferlik kontrol |

**Firm karar:**

1. Veri kaynağı seçimi **ayrı değerlendirme turu** gerektirir; bu belge seçim yapmaz.
2. Kullanıcıya her kayıt için **kaynak etiketi** gösterilir (DM3).
3. Registrar veya üçüncü taraf **credential** Lumos yüzeyinde ve public repoda **tutulmaz**.
4. Ödeme gerektiren API çağrıları izleme katmanında **satın alma onayından ayrı** değerlendirilir; ücretli sorgu varsa kullanıcıya **önceden** bildirilir (`implementation-pending` — ücret modeli).

### 2.3 Kapsam dışı veri kaynakları

- Production ödeme veya checkout endpoint'leri
- Kullanıcı PII içeren WHOIS sorgularının loglanması (gereksizse toplanmaz)
- Onaysız dış yazma veya otomatik domain rezervasyonu

---

## 3. Risk seviyeleri (çerçeve)

Bu bölüm **ürün risk çerçevesidir**; özel skor algoritması, ML modeli veya gizli formül **tanımlanmaz**.

### 3.1 Risk katmanları (firm çerçeve)

| Seviye | Etiket | Tanım (ilke) | Örnek sinyaller |
|--------|--------|--------------|-----------------|
| **Düşük** | `low` | Marka ile zayıf ilişki; kullanıcı karışıklığı düşük | Uzak TLD, zayıf yazım benzerliği, kayıtlı ve pasif |
| **Orta** | `medium` | Orta düzey karışıklık veya müsaitlik riski | Yaygın TLD'de benzer isim, müsait veya yakında boşalacak |
| **Yüksek** | `high` | Güçlü marka karışıklığı veya aktif tehdit sinyali | Yüksek benzerlik + müsait veya aktif içerik / phishing benzeri sinyal (kaynak raporluyorsa) |

### 3.2 Risk sunumu ilkeleri

| İlke | Açıklama |
|------|----------|
| Şeffaflık | Risk seviyesi **neden** kısaca açıklanır (kaynak + sinyal türü) |
| Kaynak ayrımı | Lumos üretimi vs üçüncü taraf sinyali ayırt edilir |
| Kesinlik | Kanıt yoksa "yüksek risk" iddiası **zorlanmaz**; belirsizlik açık yazılır |
| Otomasyon yasağı | Risk seviyesi **otomatik satın alma** veya **otomatik alarm → satın alma** tetiklemez |

**Implementation-pending:** Skorlama kuralları detayı, çoklu kaynak birleştirme önceliği, risk geçmişi ve trend gösterimi.

### 3.3 Fiyat sinyali

| Öğe | Karar |
|-----|--------|
| Fiyat bilgisi | Kaynak sağlıyorsa **yaklaşık** fiyat sinyali sunulabilir |
| Bağlayıcılık | Fiyat **bilgi amaçlıdır**; checkout fiyatı değildir |
| Vergi / para birimi | `implementation-pending` — gösterim formatı |
| Ödeme | Fiyat gösterimi ödeme başlatmaz (OD-011) |

---

## 4. Kullanıcı sunum modeli

### 4.1 Rapor vs Panel izleme özeti (firm ilke + bekleyen UX)

| Sunum türü | Rol | Onaylı ilke |
|------------|-----|-------------|
| **Rapor** | Periyodik veya talep üzerine özet; okuma ağırlıklı | Varsayılan bilgi yüzeyi; oturum izni yeterli |
| **Panel izleme özeti** | Sürekli görünür izleme özeti; filtre ve watchlist yönetimi | Ürün UX kararı — `implementation-pending` |
| **Kart / mesaj (chat)** | Tek domain veya kısa liste inline sunumu | UI chat deneyimi ile hizalanacak — `implementation-pending` |

**Firm karar:** Kullanıcı her kayıtta en az şunları görür:

1. **Domain adı** (izlenen)
2. **Kaynak** (hangi sorgu/hizmet)
3. **Müsaitlik durumu** (müsait / kayıtlı / belirsiz)
4. **Fiyat sinyali** (varsa, yaklaşık)
5. **Risk seviyesi** ve kısa gerekçe
6. **Son kontrol zamanı** (göreceli veya mutlak — format `implementation-pending`)

### 4.2 Kullanıcının görmediği / gizlenen

- Registrar API anahtarları, internal endpoint'ler
- Başka kullanıcıların watchlist'i (paylaşım modeli netleşene kadar)
- Otomatik satın alma veya arka planda yapılan rezervasyon

**Implementation-pending:** Wireframe, CLI çıktı formatı, export (PDF/CSV), çoklu domain sıralama ve filtreleme.

---

## 5. Alarm vs rapor mantığı

### 5.1 Tanımlar

| Mod | Davranış | Dış etki |
|-----|----------|----------|
| **Pasif rapor** | Kullanıcı talep ettiğinde veya planlı özet sunulur | Yok — bilgi only |
| **Alarm / uyarı** | Önceden tanımlı eşik veya olay tetiklenince kullanıcı bilgilendirilir | Bildirim only; **ticari aksiyon yok** |

### 5.2 Onaylı ilkeler

| # | Kural |
|---|--------|
| AR1 | Varsayılan mod: **pasif rapor** veya kullanıcı talepli sorgu |
| AR2 | Alarm açıksa bile yalnızca **bilgilendirme**; otomatik satın alma **yasak** |
| AR3 | Alarm → satın alma geçişi **ayrı kullanıcı kararı** ve **işlem bazlı onay** gerektirir (OD-041) |
| AR4 | Sessiz push veya varsayılan-onaylı alarm aksiyonu **yok** |
| AR5 | Alarm eşikleri kullanıcıya **açıklanır** ve mümkünse yapılandırılabilir (`implementation-pending`) |

### 5.3 Alarm tetik örnekleri (ilke — exhaustive değil)

| Olay | Önerilen sunum | Otomatik satın alma |
|------|----------------|---------------------|
| Yüksek risk + müsait domain | Alarm + rapor detayı | **Hayır** |
| Watchlist domain süresi dolmak üzere | Bilgi uyarısı | **Hayır** |
| Yeni varyasyon tespiti | Rapor veya isteğe bağlı alarm | **Hayır** |

**Implementation-pending:** Kontrol sıklığı, alarm kanalı (in-app, e-posta vb.), eşik varsayılanları, rate limit ve maliyet politikası.

---

## 6. Marka koruma uçtan uca akış

### 6.1 Beş adımlı akış (firm)

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ 1. İZLE     │───▶│ 2. RİSKLERİ      │───▶│ 3. KULLANICI    │
│ (oturum)    │    │    GÖSTER         │    │    KARAR VERİR  │
└─────────────┘    └──────────────────┘    └────────┬────────┘
                                                     │
                     ┌──────────────────┐    ┌────────▼────────┐
                     │ 5. REDIRECT      │◀───│ 4. SATIN ALMA   │
                     │ (OD-039 — sonra) │    │ (işlem onayı)   │
                     └──────────────────┘    └─────────────────┘
```

| Adım | Açıklama | Onay katmanı |
|------|----------|--------------|
| **1. İzle** | Varyasyon + watchlist sorgusu; veri toplama | Oturum bazlı (OD-041 CA1) |
| **2. Riskleri göster** | Kaynak, müsaitlik, fiyat sinyali, risk | Bilgi sunumu |
| **3. Kullanıcı karar verir** | Satın al, izlemeye devam, watchlist'e ekle, yok say | Karar kullanıcıda; Lumos varsayılan seçim yapmaz |
| **4. Satın alma** | Domain kaydı — ticari dış aksiyon | **İşlem bazlı açık onay** (OD-041 CA2–CA3) |
| **5. Redirect** | Varyasyon → `welockai.com` yönlendirme | OD-039 teknik detay; edinim zaten onaylı |

### 6.2 Adım 3 — kullanıcı karar seçenekleri (ilke)

| Seçenek | Ticari dış etki | Onay |
|---------|-----------------|------|
| İzlemeye devam | Yok | Oturum |
| Watchlist'e ekle/çıkar | Yok | Oturum |
| Satın almayı değerlendir | Henüz yok — bilgi ekranına geçiş | Oturum → işlem onayına hazırlık |
| **Satın al** | Var | **İşlem bazlı açık onay** |
| Yok say / arşivle | Yok | Oturum |

**Yasak:** Adım 2'den Adım 4'e **sessiz atlama**; "risk yüksek, otomatik aldım" modeli.

---

## 7. İzleme vs satın alma ayrımı (OD-041 hizası)

[`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md) ile birebir hizalı ayrım:

| Boyut | İzleme akışı | Satın alma akışı |
|-------|--------------|------------------|
| OD | **OD-042** (bu belge) | OD-041 + OD-011 (ödeme paketi) |
| Onay | Oturum bazlı izin | İşlem bazlı açık onay |
| Ödeme | **Kapsam dışı** (OD-011) | Ödeme paketi gelince; şimdilik başlatılmaz |
| Otomasyon | Bilgi toplama only | Kullanıcı onayı + gateway |
| Mod yükseltme | İzleme → satın alma **yeni onay** ister | OD-041 §Hibrit model madde 3 |
| Oturum izni | Yeterli (okuma/izleme) | **Asla yeterli değil** (CA6) |

**Firm karar:** Domain izleme paneli veya raporu, checkout veya ödeme ekranı ile **aynı onay kapısı sayılmaz**. Satın alma CTA'sı her zaman **ayrı işlem onay akışına** bağlanır.

---

## 8. Ödeme kapsamı ayrımı (OD-011 hizası)

[`payment-scope-decision.md`](./payment-scope-decision.md) §2 notu ile uyumlu:

| Özellik | OD-011 kapsamı | OD-042 konumu |
|---------|----------------|---------------|
| Domain müsaitlik sorgusu | Ödeme dışı | İzleme — oturum izni |
| Fiyat sinyali gösterimi | Ödeme dışı | Bilgi only |
| Risk raporu | Ödeme dışı | Bilgi only |
| Domain satın alma | Ödeme paketi + onay | İşlem onayı; uygulama bekliyor |
| Registrar ücretli API | `implementation-pending` | Kullanıcı bilgilendirmesi gerekir |

**Firm karar:** İzleme özelliği, ödeme altyapısı (PSP, checkout, webhook) **olmadan** tasarlanabilir; satın alma adımı ödeme uygulama paketi gelene kadar **bilgi ve onay hazırlığı** seviyesinde kalır.

---

## 9. Public repo sınırları

Public `lumos-core` deposu açık kaynak **foundation** katmanıdır.

**Taşınmaz / yazılmaz:**

- Registrar veya marka koruma API credential'ı
- Production WHOIS/registrar endpoint URL'leri (operasyonel)
- Kullanıcı watchlist verisi, PII
- Otomatik satın alma script'i veya arka plan job credential'ı
- Ödeme veya checkout entegrasyon detayı

**Taşınabilir (bu belge gibi):**

- Demo-safe politika ve karar notları
- Risk çerçevesi ve akış ilkeleri
- Değerlendirme adayı **kategorileri** (somut vendor adı olmadan veya genel kategori olarak)

**Firm karar:** Public repoda domain izleme **implementasyonu**, gerçek API anahtarı veya operasyonel altyapı **bulunmaz**; yalnızca politika ve karar belgeleri.

---

## 10. Ürün davranış soruları — yapısal yanıt

Aşağıdaki tablo OD-042 kapsamındaki açık ürün sorularını **yapısal** yanıtlar; teknik detay `implementation-pending` olarak kalır.

| Soru | Onaylı ilke | Implementation-pending |
|------|-------------|------------------------|
| **Hangi domain'ler?** | `welockai.com` birincil; marka varyasyonları + kullanıcı watchlist | Varyasyon üretim kuralları detayı, maksimum liste |
| **Kontrol sıklığı?** | Talep üzerine ve/veya planlı özet; sabit aralık **bu belgede tanımlanmadı** | Periyodik job sıklığı, maliyet/rate limit politikası |
| **Nasıl gösterilir?** | Kaynak + müsaitlik + fiyat sinyali + risk + zaman | Rapor vs dashboard vs chat kartı UX |
| **Yalnızca rapor mu?** | Varsayılan pasif rapor; isteğe bağlı alarm (bilgi only) | Alarm varsayılanları, kanal seçimi |
| **Alarm var mı?** | Evet — yapılandırılabilir bilgilendirme; otomatik satın alma yok | Eşik, kanal, sıklık |
| **Marka riski nasıl hesaplanır?** | Düşük/orta/yüksek **çerçeve**; şeffaf gerekçe; özel algoritma yok | Skor kuralları, çoklu kaynak birleştirme |
| **Veri kaynağı?** | Kategori A/B/C; değerlendirme adayları | Nihai sağlayıcı seçimi, sözleşme, entegrasyon |

---

## 11. Implementation-pending

Aşağıdakiler **henüz uygulanmadı**; bu belge uygulama izni vermez.

### Teknik bekleyenler

- Veri kaynağı nihai seçimi (WHOIS/registrar vs marka koruma SaaS vs hibrit)
- Kontrol sıklığı ve maliyet politikası
- Risk skorlama kuralları detayı (çerçeve dışı formül)
- Rapor/dashboard/chat sunum UX'i
- Alarm eşikleri ve bildirim kanalları
- Watchlist UI/CLI ve limitler
- Ücretli API çağrısı kullanıcı bilgilendirmesi

### Çapraz OD bekleyenleri

| OD | Konu | İlişki |
|----|------|--------|
| OD-039 | Domain varyasyon redirect | Adım 5 — edinim sonrası teknik uygulama |
| OD-011 | Ödeme paketi | Adım 4 — satın alma altyapısı |
| OD-041 | Onay UX | Adım 3→4 geçiş ekranı |
| OD-001–005 | Vault | Registrar credential depolama |

### İzleme bilgi akışı (bekleyen UX taslağı)

```
[ Oturum / görev kapsamı ]
        ↓
[ İzleme sorgusu — kaynak etiketli ]
        ↓
[ Rapor veya alarm — risk · müsaitlik · fiyat sinyali ]
        ↓
[ Kullanıcı kararı ]
        ↓
( Satın alma seçildiyse → OD-041 işlem onayı → gateway → OD-011 ödeme paketi bekler )
        ↓
( Edinim tamamlandıysa → OD-039 redirect )
```

---

## 12. Riskler

| Risk | Azaltma (onaylı ilke) |
|------|------------------------|
| İzlemeden sessiz satın alma | DM4, DM8; OD-041 mod yükseltmesi yasağı |
| Alarmın otomatik ticari aksiyona dönüşmesi | AR2, AR3 |
| Yanlış yüksek risk iddiası | Risk çerçevesi §3.2 — kanıt yoksa zorlama yok |
| Ödeme kapsamı kayması | OD-011 ayrımı §8 |
| Credential sızıntısı | Public repo + vault ilkeleri §9 |
| Watchlist şeffaflığı eksikliği | DM1 — izlenen domain'ler görünür |
| ChatGPT memory drift | Bu belge canonical; `commercial-domain-payments.md` güncellendi |

---

## 13. OD eşleme

| OD | Kaynak | Konu | Bu belgedeki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-042** | commercial-domain-payments.md | Domain izleme tasarımı | Bu belgenin tamamı | **decision-approved / implementation-pending** |
| OD-041 | commercial-approval-model-decision.md | Ticari onay modeli | §7 — izleme oturum, satın alma işlem onayı | decision-approved / implementation-pending |
| OD-011 | payment-scope-decision.md | Ödeme kapsamı | §8 — izleme ödeme dışı | decision-approved / implementation-pending |
| OD-039 | commercial-domain-payments.md | Domain redirect | §6 adım 5 | decision-approved / implementation-pending — [`domain-redirect-model-decision.md`](./domain-redirect-model-decision.md) |
| OD-040 | commercial-domain-payments.md | Maliyet paylaşımı | Kapsam dışı | needs-review |

**İndeks notu:** `open-decisions-needs-review.md` OD-042 satırı bu belgeyle senkron tutulur; canonical kaynak önce `commercial-domain-payments.md`, onaylı karar özeti bu dosyadır.

---

## 14. Sonraki adım

1. **Implementation-pending:** Veri kaynağı değerlendirme turu, kontrol sıklığı, sunum UX (rapor/dashboard), alarm politikası.
2. Satın alma yolu: OD-041 işlem onay UX'i + OD-011 ödeme paketi hazır olunca bağlanır; **ayrı model icat edilmez**.
3. Redirect: OD-039 ayrı karar turunda teknik detay.
4. `commercial-domain-payments.md` Domain ve marka koruma bölümü durumu bu belgeyle güncellenir.

**Yasak (bu aşamada):** kod, registrar entegrasyonu, otomatik satın alma, credential, production endpoint, ödeme gateway, alarm → satın alma otomasyonu.

---

Son güncelleme: 2026-06-18
