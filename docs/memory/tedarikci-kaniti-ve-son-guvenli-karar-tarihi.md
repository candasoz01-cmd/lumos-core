# Tedarikçi kanıtı ve son güvenli karar tarihi — gelecek özellik notu (OD-064)

> **Durum:** `ürün notu / gelecek özellik` — iki ilke çıkarımı kayda alındı; **karar onayı ve uygulama yok** (`implementation-pending`). Bu belge kod değişikliği değildir; kod, şema, panel, alan veya test üretilmedi.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, onay ve kalıcı silme kuralları bu notu gevşetemez.
>
> **Hedef alan:** kurumsal yönetişim / risk motoru (henüz mevcut olmayan yüzey).

**Kaynak:** 2026-09-23 kurucu girdisi (ürün karar kaydı talebi).

---

## Amaç

Kurumsal yönetişim ve risk/uyum takibi ileride ele alındığında iki çıkarımın
kaybolmaması. Her ikisi de aynı kök sorundan gelir: **bir kaydın "iyi"
görünmesi, riskin gerçekten kapandığı anlamına gelmez.**

1. Tedarikçi beyanı, kanıt yerine geçemez.
2. Resmî son tarih, karar için güvenli son tarih değildir.

---

## Kapsam

| Dahil | Hariç |
|-------|--------|
| Tedarikçi / servis sağlayıcı uyum ve yetenek iddialarının kayıt modeli | Belirli bir sertifika rejiminin (ISO, SOC, PQC vb.) teknik doğrulaması |
| Kanıt, kapsam, geçerlilik ve güncellik alanlarının gösterim ilkesi | Otomatik tedarikçi reddi, puanlama motoru veya skor yayını |
| Risk/uyum maddelerinde ikinci bir tarih alanının (son güvenli karar tarihi) tutulması ilkesi | Takvim/bildirim uygulaması, panel ekranı, veri şeması, API |
| Alternatif tedarikçiye geçiş süresinin karar tarihine dahil edilmesi | Tedarikçi seçimi, sözleşme ve satın alma süreci |
| İleride açılacak kurumsal yönetişim/risk motoru için giriş ilkeleri | Mevcut entegrasyon ve ödeme kapsamı (OD-011, OD-033 sınırları sürer) |

---

## Çıkarım 1 — Beyan tek başına yeterli değildir

**İlke:** Tedarikçinin veya servis sağlayıcının «destekliyoruz / hazırız /
uyumluyuz» beyanı, tek başına **uyum kanıtı sayılmaz**. Lumos, mümkün olduğunda
bu iddiayı **doğrulanabilir kanıt, sertifika, kapsam ve güncel durumla birlikte**
gösterir.

Kayıt ileride açıldığında bir iddianın yanında en az şunlar taşınır:

| Alan | Anlamı |
|------|--------|
| İddia | Tedarikçinin ne dediği (ham beyan, olduğu gibi) |
| Kanıt türü | Sertifika, denetim raporu, test çıktısı, sözleşme maddesi, yok |
| Kanıt kimliği / kaynağı | Belge numarası, denetleyen kurum, yayın yeri |
| Kapsam | Kanıtın hangi ürün, bölge, sürüm ve hizmet sınırını kapsadığı |
| Geçerlilik | Kanıtın düzenlenme ve bitiş tarihi |
| Son doğrulama | Lumos tarafında en son ne zaman kontrol edildiği |
| Durum | `doğrulanmış` · `süresi dolmuş` · `kapsam dışı` · `doğrulanmamış beyan` |

**Gösterim kuralı:** Kanıtı olmayan iddia silinmez; **`doğrulanmamış beyan`**
olarak görünür. Bu, iddianın yanlış olduğu anlamına gelmez; yalnız kanıt
düzeyini gizlemez. Doğrulanmamış beyan tek başına bir riski «kapalı» yapmaz.

**Dikkat edilecek ayrım:** Kanıtın varlığı ile kapsamın örtüşmesi ayrı
sorulardır. Geçerli bir sertifikanın, kullanılan hizmeti veya bölgeyi
kapsamaması sık görülen sessiz boşluktur; bu yüzden «kapsam» ayrı alandır.

---

## Çıkarım 2 — Son güvenli karar tarihi

**İlke:** Risk ve uyum takibinde yalnız **resmî son tarih** tutulmaz; ayrıca
**son güvenli karar tarihi** tutulur. Bu ikinci tarih, kararın hâlâ sakin ve
kontrollü biçimde uygulanabileceği en geç andır.

Son güvenli karar tarihi, resmî son tarihten **geriye doğru** şu süreler
düşülerek belirlenir:

| Düşülen süre | Örnek içerik |
|--------------|--------------|
| Entegrasyon | Teknik bağlantı, konfigürasyon, veri taşıma |
| Test | Fonksiyonel, güvenlik ve regresyon doğrulaması |
| Doğrulama | Kanıt toplama, denetim/onay turu (Çıkarım 1 alanları) |
| Değişiklik yönetimi | Onay kapıları, iletişim, eğitim, kademeli açılış |
| Alternatif tedarikçiye geçiş | Tedarikçi başarısız olursa yedeğe geçme süresi |
| Tampon | Gecikme ve sürprizler için makul pay |

Bu tarih bir tahmindir; **kesin hüküm değildir**. Süreler değiştikçe tarih
yeniden hesaplanır ve gerekçesiyle birlikte kayıtta kalır.

**Kullanım anlamı:**

| Durum | Anlamı |
|-------|--------|
| Son güvenli karar tarihinden önce | Karar normal akışta verilebilir |
| Tarih geçti, resmî son tarih duruyor | Karar hâlâ mümkün ama artık **sıkışık**; alternatife geçiş şansı daralıyor veya kalmadı — açıkça görünür |
| Resmî son tarih geçti | Uyum ihlali alanı; ayrı konu |

Kritik nokta: alternatif tedarikçiye geçiş süresi hesaba katılmazsa, «zaman var»
görünen bir madde fiilen **tek tedarikçiye mahkûm** hale gelir. İkinci tarihin
asıl işlevi bu sessiz kilitlenmeyi erken göstermektir.

---

## Ne değildir

| İddia | Durum |
|-------|--------|
| Tedarikçi puanlama / skor motoru | **Hayır** — kanıt düzeyi gösterimi; sıralama veya not değil |
| Otomatik tedarikçi reddi veya sözleşme aksiyonu | **Hayır** — Lumos kendiliğinden ticari aksiyon başlatmaz (PR-012, OD-041) |
| Otomatik takvim, bildirim veya hatırlatma ürünü | **Hayır** — bu notta uygulama yok |
| Hukuki veya denetim danışmanlığı | **Hayır** — iç yönetişim kaydı |
| Yeni ürün yüzeyi / yeni panel sayfası | **Hayır** — ileride kurumsal yönetişim/risk motoru kapsamında değerlendirilir |
| Dış tedarikçi verisinin toplanması veya yayılması | **Hayır** — veri kaynağı, saklama ve paylaşım ayrı karar ister |

---

## Bekleyen (ayrı karar gerektirir)

- Kurumsal yönetişim / risk motorunun ürün yüzeyi ve sahipliği.
- Kanıt kaydının veri modeli, saklama yeri ve gizlilik sınırı (tedarikçi
  belgeleri ticari gizlilik taşıyabilir; public repo sınırı geçerlidir).
- «Doğrulanmış» sayılma eşiği: hangi kanıt türü, kim tarafından, hangi tazelikte.
- Son güvenli karar tarihinin kim tarafından, hangi girdiyle hesaplanacağı.
- Tarih geçtiğinde ne olacağı — yalnız görünürlük mü, onay kapısı mı (kapı
  önerisi ayrı onay ister; bu not kapı kurmaz).

---

## İlişkili belgeler

- [`docs/product-rules.md`](../product-rules.md) — PR-060, PR-061
- [`docs/decision-log.md`](../decision-log.md) — DL-F09
- [`open-decisions-needs-review.md`](open-decisions-needs-review.md) — OD-064
- [`docs/decisions/ADR-013-lumos-quantum-security-readiness.md`](../decisions/ADR-013-lumos-quantum-security-readiness.md) — hazırlık iddiası ≠ uygulama ayrımı; aynı ayrımın tedarikçi tarafı
- [`docs/decisions/ADR-017-regulated-service-entity-boundaries.md`](../decisions/ADR-017-regulated-service-entity-boundaries.md) — düzenlemeye tabi alanlarda kanıt ve yetki sınırı
- [`commercial-approval-model-decision.md`](commercial-approval-model-decision.md) — ticari aksiyonlarda insan onayı
- [`work-tools-connectors-decision.md`](work-tools-connectors-decision.md) — tedarikçi/connector değerlendirme sırası

---

Son güncelleme: 2026-09-23 (ilk kayıt — iki çıkarım; uygulama yok)
