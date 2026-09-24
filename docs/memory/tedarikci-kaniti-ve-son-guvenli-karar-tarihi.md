# Tedarikçi kanıtı ve son güvenli karar tarihi — gelecek özellik notu (OD-065)

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

## Ek — dış inceleme çıkarımları (2026-09-23)

**Kaynak:** DigiCert Quantum Central ürün tanıtımı (Temmuz 2026) ve World Quantum
Readiness Day 2026 «From Blueprint to Build» içeriği üzerine yapılan **salt okuma**
incelemesi. Hesap açılmadı, deneme başlatılmadı, form gönderilmedi.

**Kanıt düzeyi (kendi PR-060 kuralımız bu nota da uygulanır):** ürünün *var olduğu ve
hangi başlıkları kapsadığı* ikincil kaynaklarla teyitli; *nasıl çalıştığı* (tarama
yöntemi, skor formülü) **doğrulanmadı** — birincil ürün dokümanına erişilemedi. Aşağıdaki
maddeler bir ürünün kopyası değil, kendi kaydımızda **eksik bulduğumuz alanlardır**
(PR-007: benzer genel işlev tek başına kopya sayılmaz).

### 1. Tedarikçi PQC değerlendirme alanları

Çıkarım 1'deki kanıt alanlarına **ek**; yalnız tedarikçi kriptografi veya güvenlik
hizmeti verdiğinde doldurulur.

| Alan | Anlamı |
|------|--------|
| `vendor_pqc_roadmap` | Tedarikçinin PQC geçiş planı ve algoritma destek takvimi |
| `hybrid_mode_support` | Klasik + PQC hibrit modun destekleniyor olup olmadığı |
| `fips_140_3_scope` | FIPS 140-3 doğrulamasının **kapsamı** (hangi modül, hangi sürüm) |
| `firmware_upgradeable` | Cihaz/ürün sahada kripto güncellemesi alabiliyor mu |
| `cbom_available` | Tedarikçi kriptografik malzeme listesi (CBOM) veriyor mu |

Bu alanlar da Çıkarım 1'e tabidir: doldurulmuş olması doğrulandığı anlamına gelmez;
kanıt yoksa `doğrulanmamış beyan` kalır. `fips_140_3_scope` özellikle kapsam alanıdır —
geçerli bir doğrulamanın kullanılan modülü kapsamaması sessiz boşluktur.

### 2. Bulguya bağlanabilecek operasyon alanları

Mevcut bulgu kaydımız (`evidenced_findings`) bulguyu **işe** çevirmiyor: sahibi, bileti
ve tarihi yok. İleride eklenmesi değerlendirilecek alanlar:

| Alan | Anlamı |
|------|--------|
| `owner` | Bulgunun sahibi (kişi veya rol) |
| `change_request` | Bağlı değişiklik kaydı / bilet referansı |
| `target_date` | Hedeflenen tamamlanma tarihi |
| `last_safe_decision_date` | Çıkarım 2'deki son güvenli karar tarihi |

`target_date` ile `last_safe_decision_date` **ayrı alanlardır**; biri hedef, diğeri
kararın sıkışmadan verilebileceği en geç andır.

### 3. Dış düzenleyici / uyum tarihine bağlama

Uygun olduğunda bir bulgu, dış bir düzenleyici veya uyum tarihine **referansla**
bağlanabilmeli (opsiyonel alan; her bulguda gerekmez). Amaç, iç hedef tarih ile dış
zorunluluğu ayırmak ve Çıkarım 2'yi dış tarihin üzerine kurabilmek.

Belirli bir rejim, tarih veya yargı alanı bu nota **sabitlenmez** — düzenlemeler
değişir, bağlayıcılığı ülke ve sektöre göre farklıdır ve Lumos hukuki danışmanlık
vermez. Referansın kendisi de Çıkarım 1'e tabidir: kaynağı ve son doğrulama tarihi
taşınır.

### 4. Standart formatta dışa aktarılabilir kanıt (değerlendirilecek)

Kanıt kaydının ileride **CBOM veya benzeri standart bir formatta** dışa aktarılabilmesi
değerlendirilecektir. Gerekçe: üçüncü tarafa kanıt verme anı geldiğinde kendimize özgü
şema karşı tarafta okunmaz. Bu bir karar değil, açık bir değerlendirme maddesidir;
format seçimi, kapsam ve gizlilik sınırı ayrı karar ister.

### 5. Ürün ilkeleri (bu notun bağlayıcı özeti)

| # | İlke |
|---|------|
| 1 | **Tek hazırlık skoru yerine kanıta bağlı bulgular önceliklidir.** Skor üretilirse bile bulguların yerine geçmez; bir yüzde, hangi iddianın doğrulanmadığını gizler. |
| 2 | **Doğrulanmamış tedarikçi beyanı ayrı gösterilir** — silinmez, doğrulanmış kanıtla aynı görsel ağırlığı da almaz (PR-060). |
| 3 | **Son güvenli karar tarihi, resmî son tarihten ayrı korunur** (PR-061); biri diğerinin yerine geçmez. |

### 6. DigiCert Quantum Central ücretsiz denemesi — başlatılmayacak

**Karar:** Bu aşamada ücretsiz deneme **başlatılmayacak**. Hesap açılmadı.

**Gerekçe (kısa):** Ürünün asıl değeri bilinmeyen geniş bir kripto envanterini
keşfetmektir; Lumos'un envanteri dar ve zaten dosya-satır kanıtıyla kayıtlıdır
([`lumos-quantum-readiness-checklist.md`](../analysis/lumos-quantum-readiness-checklist.md)),
ayrıca yönetilen bir sertifika/PKI filosu yoktur. Buna karşılık deneme, tedarikçi
ilişkisi ve kendi kripto duruşumuzun envanterinin dış platforma taşınması anlamına gelir
— kazanımı küçük, sınırı hassastır. Öğrenilmek istenen alan listesi ve format bilgisi
hesap açmadan elde edilebilir.

**Yeniden değerlendirme koşulu:** gerçek tedarikçi envanteri olan kurumsal yüzey
açıldığında, üçüncü tarafa standart formatta kanıt istendiğinde veya kendi
sertifika/TLS yüzeyimiz envantere dahil edildiğinde — o zaman da değerlendirilecek olan
deneme değil, **format uyumudur**.

**Sınır:** Bu ek yalnız dokümantasyondur. Kod, şema, panel, test veya entegrasyon
üretilmedi; yeni ADR/OD açılmadı; ticari aksiyon alınmadı.

---

## İlişkili belgeler

- [`docs/product-rules.md`](../product-rules.md) — PR-060, PR-061
- [`docs/decision-log.md`](../decision-log.md) — DL-F09
- [`open-decisions-needs-review.md`](open-decisions-needs-review.md) — OD-065
- [`docs/decisions/ADR-013-lumos-quantum-security-readiness.md`](../decisions/ADR-013-lumos-quantum-security-readiness.md) — hazırlık iddiası ≠ uygulama ayrımı; aynı ayrımın tedarikçi tarafı
- [`docs/decisions/ADR-017-regulated-service-entity-boundaries.md`](../decisions/ADR-017-regulated-service-entity-boundaries.md) — düzenlemeye tabi alanlarda kanıt ve yetki sınırı
- [`commercial-approval-model-decision.md`](commercial-approval-model-decision.md) — ticari aksiyonlarda insan onayı
- [`work-tools-connectors-decision.md`](work-tools-connectors-decision.md) — tedarikçi/connector değerlendirme sırası

---

Son güncelleme: 2026-09-23 (ek — tedarikçi PQC alanları, operasyon alanları, düzenleyici tarih bağlama, CBOM değerlendirmesi, ürün ilkeleri, deneme başlatılmama kararı)
