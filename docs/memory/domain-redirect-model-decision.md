# Domain varyasyon redirect modeli — onaylı karar (OD-039)

> **Durum:** `decision-approved / implementation-pending` — ürün ilkeleri ve redirect modeli (301; registrar forwarding **veya** Cloudflare tabanlı yönlendirme) onaylandı; **somut kurulum ve UX uygulaması başlamadı**. Bu belge kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`commercial-domain-payments.md`](./commercial-domain-payments.md), [`domain-monitoring-design-decision.md`](./domain-monitoring-design-decision.md), [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md), [`payment-scope-decision.md`](./payment-scope-decision.md), [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

**Kaynak OD:** OD-039 (`commercial-domain-payments.md` — Domain ve marka koruma, migration #5)

---

## Amaç

OD-039 kapsamında edinilen **marka koruma varyasyon domain'lerinin** birincil hedef **`welockai.com`**'a nasıl yönlendirileceğine ilişkin **ürün ilkelerini** ve **teknik değerlendirme çerçevesini** netleştirmek.

Bu belge:

- Varyasyon domain'lerde **ayrı içerik barındırılmaması** ve **birincil domain'e yönlendirme** ilkesini sabitler.
- Domain **satın alma onayı** ile **DNS/redirect onayının** ayrı olduğunu tanımlar (OD-041 hizası).
- Redirect işleminin **ödeme kapsamı dışında** kaldığını tekrarlar (OD-011 hizası).
- OD-042 beş adımlı akışın **5. adımı** (redirect) için canonical karar kaydıdır.
- Onaylı redirect modelini sabitler: **HTTP 301** varsayılan; **registrar forwarding** veya **Cloudflare tabanlı redirect** kabul edilen uygulama yolları; davranış sabiti: kullanıcı her zaman birincil domain'e iner.

**Uygulama notu:** Karar katmanı kapandı; belirli registrar kurulumu, Cloudflare kural detayı, SSL, apex/www, rollback ve onay UX wireframe'leri **henüz uygulanmadı**.

---

## Kapsam dışı

| Hariç | Not |
|-------|-----|
| Domain satın alma / yenileme / ödeme akışı | OD-011 ödeme paketi + OD-041 işlem onayı |
| Domain izleme, müsaitlik, risk raporu | OD-042 |
| Belirli registrar paneli / Cloudflare zone kurulum detayı | `implementation-pending` — yol onaylı, somut config yok |
| Credential, token, production DNS/registrar API endpoint | Vault + public repo sınırı |
| Varyasyon domain'de bağımsız site, landing veya içerik barındırma | İlke: yasak |
| Otomatik redirect (satın alma onayından sonra sessiz uygulama) | İlke: yasak — ayrı DNS/redirect onayı |
| Ödeme gateway, checkout, PSP | OD-011 kapsam dışı |

**Çelişki çözümü:** `commercial-domain-payments.md` Domain ve marka koruma bölümündeki redirect maddeleri bu belgeyle **hizalanır**; canonical redirect kararı bu dosyadır.

---

## Mevcut durum

| Katman | Durum | Açıklama |
|--------|--------|----------|
| **Ürün ilkeleri** | `decision-approved` | Hedef domain, onay ayrımı, şeffaflık, ödeme dışı kapsam |
| **Redirect modeli** | `decision-approved` | Varsayılan **301**; registrar forwarding **veya** Cloudflare redirect; davranış sabiti: `welockai.com` |
| **Somut kurulum** | `implementation-pending` | Registrar/Cloudflare config, SSL, apex/www, rollback, onay UX |
| **Önkoşul akış** | OD-042 adım 1–4 | İzleme onaylı; satın alma işlem onaylı; redirect adım 5 |
| **Onay modeli** | OD-041 | DNS değişikliği = işlem bazlı açık onay (CA3) |

---

## Karar özeti

**Onaylı karar (firm):** Edinilen tüm varyasyon domain'ler **`welockai.com`**'a yönlendirilir; varyasyon üzerinde ayrı içerik barındırılmaz. Redirect, satın alma onayından **bağımsız**, **işlem bazlı açık onay** gerektiren DNS düzeyinde bir adımdır.

```
[ OD-042 Adım 4: Satın alma onayı + edinim ] → [ OD-039: Redirect onayı + DNS değişikliği ] → welockai.com
```

| # | Kural | Durum |
|---|--------|--------|
| DR1 | Edinilen **tüm** varyasyon domain'ler **`welockai.com`**'a yönlendirilir. | `decision-approved` |
| DR2 | Varyasyon domain'lerde **ayrı içerik, landing veya bağımsız site barındırılmaz**. | `decision-approved` |
| DR3 | Domain **satın alma onayı** ≠ **DNS/redirect onayı**; redirect için **ayrı işlem bazlı açık onay** zorunludur (OD-041 CA3). | `decision-approved` |
| DR4 | DNS/redirect öncesi kullanıcı **ne / nerede / hangi etki / yaklaşık maliyet** görür (OD-041 CA7). | `decision-approved` |
| DR5 | **Sessiz**, **varsayılan-onaylı** veya **önceki onayın otomatik devri** (carry-forward) ile redirect uygulanmaz (OD-041 CA4). | `decision-approved` |
| DR6 | Redirect yalnızca kullanıcı onaylı **edinim tamamlandıktan sonra** başlar (OD-042 adım 5). | `decision-approved` |
| DR7 | Redirect işlemi **OD-011 ödeme kapsamı dışındadır**; ödeme altyapısı olmadan DNS değişikliği planlanabilir. | `decision-approved` |
| DR8 | Birincil hedef sabit: **`welockai.com`** (OD-042 DM2 ile hizalı). | `decision-approved` |
| DR9 | Varsayılan redirect modeli: **HTTP 301 Permanent Redirect**; park sayfası veya meta refresh **birincil mekanizma değildir**. | `decision-approved` |
| DR10 | Kabul edilen uygulama yolları: **registrar forwarding** **veya** **Cloudflare tabanlı redirect**; somut yol işlem onayı bağlamında seçilir. | `decision-approved` |
| DR11 | **Davranış sabiti:** Uygulama yolu ne olursa olsun kullanıcı **her zaman** birincil domain **`welockai.com`** üzerinde sonlanır. | `decision-approved` |
| DR12 | Public repoda credential, production DNS API otomasyonu veya operasyonel endpoint **yazılmaz**. | `decision-approved` |

---

## Onaylı ilkeler (firm)

### 1. Hedef ve içerik

| İlke | Açıklama |
|------|----------|
| Birincil hedef | **`welockai.com`** — tüm edinilen varyasyonlar buraya yönlendirilir |
| Varyasyon içeriği | **Yok** — varyasyon yalnızca yönlendirme köprüsü; marka karışıklığını önlemek için ayrı sayfa/içerik barındırılmaz |
| www / apex | Her iki form da birincil hedefe yönlendirilir (`implementation-pending` — teknik uygulama detayı) |

### 2. Onay ayrımı (satın alma ≠ redirect)

[`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md) ile birebir hizalı:

| Adım | İşlem | Onay katmanı | Oturum izni yeterli mi? |
|------|--------|--------------|-------------------------|
| Satın alma | Domain kaydı / yenileme | **İşlem bazlı açık onay** (CA2, CA3) | Hayır |
| Redirect | DNS kaydı değişikliği (A/CNAME/ALIAS, forwarding vb.) | **Ayrı işlem bazlı açık onay** (CA3 — DNS değişikliği) | Hayır |

**Firm karar:** Satın alma onayı, redirect'i **otomatik yetkilendirmez**. Çok adımlı akışta her adım kendi onay kapısından geçer (OD-041 hibrit model madde 2).

**Kullanıcı görünürlüğü (redirect onayı öncesi):**

1. **Ne:** Hangi varyasyon domain(ler) yönlendirilecek
2. **Nerede:** Hangi DNS/registrar katmanında değişiklik yapılacak (kategori düzeyinde)
3. **Etki:** Tüm istekler `welockai.com`'a gidecek; varyasyonda içerik kalmayacak
4. **Yaklaşık maliyet:** Varsa registrar/DNS ücreti veya SSL maliyeti (`implementation-pending` — format)

### 3. Yasaklar

- Satın alma sonrası **sessiz** veya **varsayılan** redirect
- Önceki oturum/satın alma onayının redirect'e **carry-forward** edilmesi
- Onaysız DNS kaydı güncelleme
- Varyasyon domain'de bağımsız içerik yayını
- Ödeme kapsamına redirect'i sokarak ödeme paketi bekletme

### 4. Ödeme kapsamı

[`payment-scope-decision.md`](./payment-scope-decision.md) §2 notu ile uyumlu:

| Özellik | OD-011 | OD-039 |
|---------|--------|--------|
| Domain satın alma ücreti | Ödeme paketi + onay | Önkoşul (adım 4) |
| DNS/redirect yapılandırması | **Kapsam dışı değil** — ödeme altyapısından **bağımsız** | Bilgi + DNS onayı; PSP gerektirmez |
| Registrar yönetim API ücreti | `implementation-pending` | Kullanıcı bilgilendirmesi gerekir |

**Firm karar:** Redirect planlaması ve DNS değişikliği, ödeme sistemi uygulama paketi (OD-011) **tamamlanmadan** tasarlanabilir; satın alma adımı ödeme paketine bağlı kalır.

### 5. Public repo sınırları

Public `lumos-core` deposu açık kaynak **foundation** katmanıdır.

**Taşınmaz / yazılmaz:**

- Registrar veya DNS sağlayıcı credential'ı
- Production DNS/registrar API endpoint URL'leri (operasyonel)
- Otomatik DNS değişikliği script'i veya arka plan job credential'ı
- Kullanıcıya özel domain envanteri (PII)

**Taşınabilir (bu belge gibi):**

- Demo-safe politika ve karar notları
- Teknik değerlendirme adayı **kategorileri** (somut vendor seçimi olmadan)
- Onay ve akış ilkeleri

---

## Onaylı uygulama yolları

**Firm karar (kapalı):** Varsayılan redirect modeli **HTTP 301 Permanent Redirect**'tir. Kabul edilen uygulama yolları:

| Yol | Katman | Durum | Not |
|-----|--------|--------|-----|
| **Registrar forwarding** | Registrar paneli / forwarding hizmeti | `decision-approved` (yol) | 301 semantiği sağlayıcıya bağlı; onay ekranında yol açıkça belirtilir |
| **Cloudflare tabanlı redirect** | Edge / Page Rules / Redirect Rules | `decision-approved` (yol) | 301 kuralı edge'de; zone yapılandırması `implementation-pending` |

**Davranış sabiti (DR11):** Hangi yol seçilirse seçilsin, son kullanıcı **her zaman** **`welockai.com`** üzerinde sonlanır; varyasyon domain'de içerik barındırılmaz.

**Birincil mekanizma olarak kabul edilmeyenler:** Park sayfası, meta refresh, geçici 302 (varsayılan model olarak).

**Uygulama seçimi:** Registrar forwarding ile Cloudflare redirect **ikisi de geçerli**; belirli domain/işlem için hangi yolun kullanılacağı **redirect işlem onayı** (DR3) bağlamında seçilir — satın alma onayı bu seçimi otomatik yapmaz.

### Destekleyici DNS katmanı (`implementation-pending`)

Aşağıdakiler tek başına redirect modeli değildir; seçilen yola göre destekleyici yapılandırma olarak değerlendirilir:

| Katman | Rol | Durum |
|--------|-----|--------|
| CNAME | Alt alan çözümlemesi | `implementation-pending` |
| ALIAS / ANAME | Apex çözümlemesi | `implementation-pending` |
| A kaydı | IP işaret — barındırma gerektirir | `implementation-pending` |

**Somut kurulum bekleyenler:** Apex (`@`) ve `www` tutarlılığı; SSL/TLS varyasyon domain için; seçilen yolun registrar/Cloudflare config detayı.

---

## Satın alma sonrası operasyonel akış

OD-042 §6 beş adımlı akışın **5. adımı** için operasyonel sıra:

```
┌─────────────────────┐
│ 4. Edinim tamamlandı │  ← Satın alma işlem onayı (OD-041) + kayıt
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5a. Redirect bilgi   │  Kaynak varyasyon, hedef welockai.com, etki özeti
│     ekranı           │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5b. DNS/redirect     │  Ne / nerede / etki / yaklaşık maliyet (CA7)
│     işlem onayı      │  Ayrı onay — satın alma onayı yetmez (DR3)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5c. Teknik uygulama  │  Onaylı yol: registrar forwarding veya Cloudflare 301 (`implementation-pending` — somut config)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5d. Doğrulama        │  Varyasyon → welockai.com; içerik yok (DR1, DR2)
│     + kullanıcıya    │
│     kanıt            │
└─────────────────────┘
```

| Aşama | Dış etki | Onay |
|-------|----------|------|
| 5a Bilgi | Yok | Oturum (bilgi sunumu) |
| 5b Onay | DNS değişikliği planı | **İşlem bazlı açık onay** |
| 5c Uygulama | Canlı DNS/redirect | Onaylı işlem yürütülür |
| 5d Doğrulama | Yok (salt okuma) | Oturum |

**Yasak:** Adım 4 tamamlanır tamamlanmaz **5b atlanarak** otomatik redirect.

**Çoklu varyasyon:** Her domain veya her DNS değişikliği paketi için **ayrı işlem onayı** değerlendirilir (`implementation-pending` — toplu onay UX'i).

---

## OD-041 / OD-042 / OD-011 çapraz

### OD-041 — Ticari onay modeli

| OD-041 | OD-039 karşılığı |
|--------|------------------|
| CA3 — DNS değişikliği işlem bazlı onay | Redirect = DNS değişikliği; DR3 |
| CA4 — sessiz / carry-forward yok | DR5 |
| CA6 — oturum ≠ ticari yetki | Satın alma onayı redirect yetkisi vermez |
| CA7 — ne/nerede/etki/maliyet | Redirect onay ekranı §2.2 |
| Mod yükseltmesi yeni onay | Satın alma → redirect ayrı kapı |

### OD-042 — Domain izleme ve marka koruma

| OD-042 | OD-039 karşılığı |
|--------|------------------|
| DM2 — `welockai.com` birincil hedef | DR8 |
| DM7 — varyasyon → birincil redirect | DR1; teknik detay bu belge |
| Adım 5 — redirect | Bu belgenin operasyonel akışı |
| Adım 4 önkoşul | DR6 — edinim önce |

### OD-011 — Ödeme kapsamı

| Boyut | İlişki |
|-------|--------|
| Ödeme altyapısı | Redirect **bekletilmez**; DNS işlemi ödeme paketinden bağımsız |
| Domain satın alma | Ödeme paketi + işlem onayı — adım 4 |
| Bilgi sunumu | Redirect planı bilgi katmanı; ödeme başlatmaz |

---

## Implementation-pending

Aşağıdakiler **henüz uygulanmadı**; bu belge uygulama izni vermez.

### Teknik bekleyenler

| Konu | Durum |
|------|--------|
| Belirli registrar forwarding kurulumu (panel/API adımları) | `implementation-pending` |
| Cloudflare redirect kuralı / zone yapılandırması | `implementation-pending` |
| SSL/TLS sertifikası varyasyon domain için | Planlanmadı |
| Apex (`@`) ve `www` tutarlı yönlendirme | Planlanmadı |
| Rollback prosedürü (redirect geri alma) | Planlanmadı |
| Çoklu varyasyon toplu redirect onay UX'i | Planlanmadı |
| Redirect sonrası doğrulama (HTTP status, zincir) | Planlanmadı |
| Propagasyon süresi kullanıcı bilgilendirmesi | Planlanmadı |

### Onay UX bekleyenleri

- Redirect işlem onay ekranı wireframe / CLI sözdizimi
- Yaklaşık maliyet gösterimi (DNS ücreti, SSL, registrar forwarding ücreti)
- Satın alma tamamlandıktan sonra redirect önerisi sunumu (otomatik uygulama yok)

### Çapraz OD bekleyenleri

| OD | Konu | İlişki |
|----|------|--------|
| OD-011 | Ödeme paketi | Adım 4 satın alma |
| OD-041 | Onay UX | Adım 5b işlem onayı |
| OD-042 | İzleme akışı | Adım 1–3 önkoşul |
| OD-001–005 | Vault | Registrar/DNS credential |

---

## Riskler

| Risk | Azaltma (onaylı ilke) |
|------|------------------------|
| Satın alma sonrası sessiz redirect | DR3, DR5; ayrı DNS onayı |
| Varyasyonda istenmeyen içerik | DR2 — ayrı içerik yasak |
| Yanlış hedef domain | DR8 — `welockai.com` sabit |
| Apex/www tutarsızlığı | Onaylı uygulama yolları; apex `implementation-pending` |
| Zayıf redirect (park/meta refresh) | DR9 — birincil mekanizma değil |
| Ödeme kapsamı kayması | DR7 — OD-011 ayrımı |
| Credential sızıntısı | Public repo §5 |
| SSL uyarısı / güven kaybı | SSL `implementation-pending`; kullanıcı bilgilendirmesi |
| ChatGPT memory drift | Bu belge canonical |

---

## OD eşleme

| OD | Kaynak | Konu | Bu belgedeki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-039** | commercial-domain-payments.md | Domain varyasyon redirect | Bu belgenin tamamı | **decision-approved / implementation-pending** (301 + registrar/Cloudflare yolları onaylı; somut kurulum bekliyor) |
| OD-042 | domain-monitoring-design-decision.md | Marka koruma akışı | §Satın alma sonrası akış — adım 5 | decision-approved / implementation-pending |
| OD-041 | commercial-approval-model-decision.md | Ticari onay modeli | §Onay ayrımı — DNS = işlem onayı | decision-approved / implementation-pending |
| OD-011 | payment-scope-decision.md | Ödeme kapsamı | §Ödeme kapsamı — redirect ödeme dışı | decision-approved / implementation-pending |
| OD-040 | commercial-domain-payments.md | Maliyet paylaşımı | Kapsam dışı | needs-review |

**İndeks notu:** `open-decisions-needs-review.md` OD-039 satırı bu belgeyle senkron tutulur; canonical kaynak önce `commercial-domain-payments.md`, onaylı karar özeti bu dosyadır.

---

## Sonraki adım

1. **Implementation-pending:** Onaylı yollardan (registrar forwarding veya Cloudflare 301) somut kurulum: apex/www, SSL, rollback, doğrulama.
2. Redirect onay UX'i: OD-041 işlem onay akışına **ayrı ekran** olarak bağlanır; yol seçimi (registrar vs Cloudflare) bu ekranda açıkça gösterilir; satın alma onayı ile birleştirilmez.
3. Edinim sonrası kullanıcıya redirect **önerisi** sunulabilir; **otomatik uygulama yok** (DR5).
4. `commercial-domain-payments.md` redirect maddeleri bu belgeyle senkron tutulur.

**Yasak (bu aşamada):** kod, onaysız DNS değişikliği, otomatik redirect, credential, production endpoint, uydurma API anahtarı veya operasyonel URL.

---

Son güncelleme: 2026-06-18
