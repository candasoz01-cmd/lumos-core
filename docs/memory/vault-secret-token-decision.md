# Vault / Secret / Token / Şifreleme — onaylı karar (OD-001 – OD-005)

> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu doküman kod değişikliği değildir.
>
> **Üst sınır:** `docs/lumos-karar-sozlesmesi.md` — güvenlik, yetki, kalıcı silme ve onay kuralları bu taslağı gevşetemez.
>
> **Canonical kaynaklar:** `security-architecture.md`, `data-vault-user-data.md`, `product-rules.md`, `external-integrations-permissions.md`, `open-decisions-needs-review.md`.

---

## 1. Amaç

OD-001 ile OD-005 arasındaki kararları tek bir **onaylı karar belgesi** altında toplamak; vault, secret, token ve şifreleme modeli için **onaylanmış ilkeleri** sabitlemek, **henüz karar verilmeyen teknik/uygulama detaylarını** ise `implementation-pending` olarak işaretlemek.

Bu belge:

- Lumos'un **secret taşıyıcı değil**, **yetkili geçit/orkestratör** olduğunu açıkça tanımlar.
- Hassas bilginin mümkün olduğunca Lumos **yüzeyinden ayrı** tutulması ilkesini vault katman modeliyle hizalar.
- Bridge, dış entegrasyonlar ve kullanıcı onayı ile ilişkiyi çerçeveler.
- Public `lumos-core` sınırını tekrarlar; gerçek secret, PII veya production credential **bu belgeye veya repoya yazılmaz**.

**Uygulama notu:** İlke kararları onaylandı; kod, test, panel, bridge veya yapılandırma uygulaması **henüz başlamadı**.

---

## 1b. Onaylanan ilke vs bekleyen uygulama

| Katman | Durum | Kapsam |
|--------|--------|--------|
| **İlke kararları** | `decision-approved` | Lumos secret taşıyıcı değildir; secret/token/credential Lumos yüzeyinde açık tutulmaz; vault/kasa ayrı güvenli katman olarak kabul edilir; Lumos yalnızca yetkili geçit/orkestratördür; vault erişimi sınırlı, amaç bazlı, onaylı ve görünür olmalıdır; tek bileşen ele geçirildiğinde tüm sırlar açığa çıkmamalıdır; şifreleme ve anahtar yönetimi gereklidir. |
| **Teknik / uygulama detayı** | `implementation-pending` | Somut vault ürünü/teknolojisi; token formatı ve credential şeması; amaç kodu listesi ve vault-Lumos API sözleşmesi; segmentasyon modeli; şifreleme algoritması/KDF/döngü/HSM-secure enclave yolu; vault UX anlatımı; platform connector sıralaması. |

Bu belge **somut uygulama icat etmez**; onaylanan ilkeler ile bekleyen teknik detay ayrımı korunur.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| Somut vault ürünü / kütüphanesi seçimi | OD-001 — ilke onaylı; uygulama tanımı `implementation-pending` |
| Token formatı, credential şeması, endpoint tanımları | OD-002 — ilke onaylı; entegrasyon detayı `implementation-pending` |
| Amaç kodu (purpose code) listesi ve API sözleşmesi | OD-003 — ilke onaylı; amaç bazlı erişim uygulaması `implementation-pending` |
| Şifreleme algoritması, anahtar uzunluğu, KDF, HSM yolu | OD-005 — ilke onaylı; teknik spesifikasyon `implementation-pending` |
| Keystore path, dosya adı, dizin yapısı | Uygulama detayı; bu belgede yer almaz |
| Bridge, panel, `.env`, stash veya kod değişikliği | Bu belge yalnızca karar taslağıdır |
| Gerçek secret, token, API anahtarı, production URL | Asla yazılmaz |

---

## 3. Temel karar ilkeleri

Aşağıdaki ilkeler **onaylandı** (`decision-approved`); çekirdek sözleşme ve canonical memory kayıtlarıyla uyumludur.

| # | İlke | Kaynak özeti |
|---|------|--------------|
| K1 | **Lumos secret taşıyıcı değildir.** Ham secret, token ve credential Lumos yüzeyinde açık biriktirilmez. | `data-vault-user-data.md` §Vault; `security-architecture.md` §Token |
| K2 | **Lumos yalnızca yetkili geçit ve orkestratördür.** Dış dünya ile tek kontrollü temas noktasıdır; iç katmanlara doğrudan köprü kurmaz. | `product-rules.md` §Ürün ilkeleri; `security-architecture.md` §Güvenlik |
| K3 | **Secret/token bilgisi mümkün olduğunca ayrı güvenli vault/katmanda tutulur.** Lumos yüzeyi minimum hassas veri taşır. | `security-architecture.md` §Lumos Vault |
| K4 | **Vault → Lumos erişimi sınırlı, amaç bazlı ve onaylıdır.** Geniş veya süresiz erişim verilmez. | `data-vault-user-data.md` §Vault #3 |
| K5 | **Ele geçirme senaryosunda tüm sırlar tek noktada açığa çıkmamalıdır** — risk dağılımı ve segmentasyon hedeflenir. | `data-vault-user-data.md` §Vault #4, §Risk |
| K6 | **Public repoda secret, PII ve production credential bulunmaz.** | Tüm canonical kaynaklar; public boundary kuralları |
| K7 | **Onaysız dış etkili aksiyon yok** — ödeme, domain, veri taşıma, e-posta, kalıcı silme, dış yazma. | `lumos-karar-sozlesmesi.md` §2, §5 |
| K8 | **Online işlem için kimlik ve kilit/presence koşulları sağlanmadan dış aksiyon başlatılmaz.** | `security-architecture.md` §Kimlik; çekirdek sözleşme |
| K9 | **Kullanıcı verinin sahibidir;** Lumos ayrı sahiplik kurmaz. | `data-vault-user-data.md` §Veri sahipliği |

---

## 4. Vault katman modeli

Onaylı katman ayrımı — mimari rol **onaylandı**; somut uygulama detayı `implementation-pending`.

```
┌─────────────────────────────────────────────────────────┐
│  Kullanıcı yüzeyi (panel / chat / CLI)                  │
│  — Lumos tek dış yüzey; iç katman adları görünmez       │
└──────────────────────────┬──────────────────────────────┘
                           │ onaylı, amaçlı istek
┌──────────────────────────▼──────────────────────────────┐
│  Lumos geçit / orkestratör katmanı                      │
│  — secret taşımaz; yetki profili + onay kapısı          │
│  — bridge üzerinden kontrollü dış iletişim              │
└──────────────────────────┬──────────────────────────────┘
                           │ sınırlı, amaç bazlı erişim
┌──────────────────────────▼──────────────────────────────┐
│  Güvenli vault / kasa katmanı (ayrı)                    │
│  — token, credential, hassas kullanıcı verisi           │
│  — Lumos yüzeyinden fiziksel/mantıksal ayrım hedefi     │
└─────────────────────────────────────────────────────────┘
```

| Katman | Rol | Secret tutar mı? |
|--------|-----|------------------|
| Kullanıcı yüzeyi | Etkileşim, onay, görünürlük | Hayır (ilke) |
| Lumos geçit | Yönlendirme, orkestrasyon, yetki kontrolü | Hayır |
| Vault / kasa | Saklama, sınırlı erişim verme | Evet (hedef konum) |
| İç katmanlar (Kando/Cando/Bando) | Kullanıcıya gösterilmez; dışarıdan doğrudan erişim yok | Hayır (doğrudan dış akış yok) |

**OD-001 durumu:** Katman modeli ve rol ayrımı **onaylandı** (`decision-approved`); somut vault uygulaması (ürün, depolama teknolojisi, dağıtım modeli) **`implementation-pending`**.

---

## 5. Secret/token saklama sınırı

| Konu | Karar | Durum |
|------|--------|--------|
| Lumos yüzeyinde açık token/credential | **Yasak** (onaylı ilke) | decision-approved |
| Vault/katman tercihi | Ayrı güvenli vault/kasa katmanı | decision-approved |
| Log, chat, panel çıktısında secret | Yazılmaz; maskeleme/eksiltme politikası uygulama aşamasında | implementation-pending |
| Connector credential'ları | Vault katmanında; Lumos yalnızca onaylı geçit | decision-approved (ilke); entegrasyon detayı implementation-pending |
| Trash / workspace state | Secret aktif state kaynağı değildir; `.lumos/trash/` prensibi ayrı | decision-approved (çekirdek sözleşme) |

**OD-002 durumu:** Token ve vault'un **birlikte çalışacağı** ilke **onaylandı**; token formatı, credential şeması ve bridge + kimlik katmanı entegrasyon akışı **`implementation-pending`**.

---

## 6. Amaç bazlı erişim modeli

Vault, Lumos'a **genel veya süresiz** erişim vermez. Erişim:

1. **Amaçla sınırlı** — belirli iş (ör. tek connector çağrısı, tek oturum) için.
2. **Kapsamla sınırlı** — yalnızca gerekli minimum yetki.
3. **Onayla bağlı** — kullanıcı iradesi ve izin profili üzerinden.
4. **Görünür** — kullanıcı hangi amaçla erişim verildiğini anlayabilmeli (UX detayı ayrı: OD-023).

Taslak akış:

```
Kullanıcı onayı → yetki profili kontrolü → amaç tanımı → vault kısa süreli/scope'lu erişim → Lumos işi yürütür → erişim sona erer
```

| Açık soru | Durum |
|-----------|--------|
| Amaç kodu (purpose code) listesi | implementation-pending |
| Erişim süresi / otomatik iptal kuralları | implementation-pending |
| Vault-Lumos API sözleşmesi | implementation-pending |
| İzin profili (rapor / guvenli_yurut / kisitli_otonom) ile vault eşlemesi | implementation-pending |

**OD-003 durumu:** Sınırlı, amaçlı, onaylı ve görünür erişim ilkesi **onaylandı** (`decision-approved`); amaç kodu şeması, API sözleşmesi ve yetki eşlemesi **`implementation-pending`**.

---

## 7. Segmentasyon ve risk dağılımı

**Hedef:** Lumos veya tek bir bileşen ele geçirildiğinde tüm sırların tek seferde açığa çıkmaması.

| Strateji | Açıklama | Durum |
|----------|----------|--------|
| Yüzey / vault ayrımı | Secret'lar Lumos sürecinde değil vault katmanında | decision-approved |
| Amaç bazlı parçalama | Tek amaç = minimum gerekli secret alt kümesi | decision-approved (ilke) |
| Connector bazlı izolasyon | Her dış entegrasyon kendi credential kapsamında | implementation-pending |
| Segment başına şifreleme | Vault içi segmentler — teknik model belirsiz | implementation-pending |

Risk tablosu (`data-vault-user-data.md` ile hizalı):

| Risk | Azaltma (taslak) |
|------|------------------|
| Hassas verinin Lumos yüzeyinde birikmesi | Vault katmanı; yüzeyde minimum tutma |
| Tek noktada tüm sırların açığa çıkması | Dağıtılmış yükleme ve segmentasyon — detay implementation-pending |
| Public repo'ya sızma | Politika + review; örnek veri yok |
| Onaysız credential kullanımı | Gateway + onay kapısı |

**OD-004 durumu:** «Tek bileşen ele geçirildiğinde tüm sırlar açığa çıkmamalı» hedefi **onaylandı** (`decision-approved`); somut segmentasyon ve izolasyon modeli **`implementation-pending`**.

---

## 8. Şifreleme / anahtar yönetimi

**Önemli:** Bu bölüm teknik spesifikasyon icat etmez. Algoritma, anahtar formatı, döngü periyodu ve depolama yolu **`implementation-pending`** olarak bırakılır.

| Konu | Onaylı ilke | Durum |
|------|-------------|--------|
| Hassas veri şifreli tutulur | `product-rules.md` Encrypted ekseni; vault içi koruma gerekli | decision-approved |
| Anahtar Lumos yüzeyinde açık tutulmaz | Vault katmanı sorumluluğu | decision-approved |
| Anahtar döngüsü (rotation) | Gerekli — periyot, tetikleyici, kullanıcı bildirimi tanımlanacak | implementation-pending |
| Kullanıcı passphrase / kilit ilişkisi | Çekirdek sözleşme: kilidi açma açık onay gerektirir | decision-approved |
| Yedekleme ve kurtarma | Kullanıcı kontrollü, geri alınabilir tasarım hedefi | implementation-pending |
| İç katman iletişim şifrelemesi | OD-007 ile çapraz; bu belgenin kapsamı dışı | ayrı karar |

**OD-005 durumu:** «Şifreleme ve anahtar yönetimi gerekli» ilkesi **onaylandı** (`decision-approved`); algoritma, KDF, döngü politikası ve HSM/secure enclave yolu **`implementation-pending`**.

---

## 9. Bridge ve dış entegrasyonlarla ilişki

| Konu | İlke | Kaynak |
|------|------|--------|
| Bridge rolü | Yalnızca yetkili, onaylı ve Lumos kontrollü dış iletişim kanalı | `security-architecture.md` §Bridge |
| İç katmana köprü | Bridge iç katmanlara doğrudan köprü kurmaz | `security-architecture.md` §Güvenlik #3 |
| Dış sistem akışı | `[Kullanıcı onayı] → [Lumos gateway] → [İzinli connector] → dış sistem` | `external-integrations-permissions.md` |
| Credential yönetimi | Connector credential'ları vault katmanında; bridge üzerinden ham secret taşınmaz | taslak — OD-002 ile örtüşür |
| Otomatik vs kısayol | Otomatik dış ops onay + gateway zorunlu; UI kısayolu yalnızca yönlendirme | `external-integrations-permissions.md` |
| Kalıcı import | Açık onay olmadan yok | firm |
| Computer Use / dış yazma | Sıkı onay kapısı — ayrı OD (OD-012) | needs-review (ayrı madde) |

Bridge, vault'tan alınan **amaçlı ve kapsamlı** erişimle dış çağrı yapar; secret'ı kalıcı olarak Lumos veya bridge katmanında biriktirmez (ilke).

---

## 10. Kullanıcı onayı ve görünürlük

| Tür | Kural |
|-----|--------|
| Vault erişimi verme | Kullanıcı onayı ve/veya açık komut; sessiz varsayılan-onay yok |
| Dış etkili işlem | Ödeme, domain, veri taşıma, e-posta, kalıcı silme, dış yazma — onaysız başlamaz |
| Kilidi açma | Passphrase ile açık kullanıcı aksiyonu |
| Genel onay | `kisitli_otonom` profilinde çok adımlı iş için |
| Görünürlük | Hangi amaçla vault erişimi istendiği kullanıcıya anlatılabilir olmalı (UX: OD-023) |
| Provenance | Dış içerik hangi sistem/kaynak — kullanıcıya görünür |

**SECURITY_NEVER_AUTO** (çekirdek sözleşme): `permanent_delete`, `external_write`, `irreversible_user_op`, `critical_system_config` — profil/onaydan bağımsız otomatik yapılmaz.

---

## 11. Public repo sınırı

Public `lumos-core` için vault/secret karar taslağı filtresi:

| Taşınmaz | Taşınabilir (bu belge düzeyinde) |
|----------|----------------------------------|
| Production secret, authentication credential | Demo-safe ilkeler ve mimari özet |
| Payment/licensing, user-data sistemleri | Placeholder/stub açıklamalar |
| Private entegrasyon, operasyonel backend | Dokümantasyon-safe politika notları |
| Gerçek production URL, PII | Açık kaynak foundation kuralları |

Bu belge ve public repo **yalnızca ilke ve mimari özet** içerir; operasyonel vault uygulaması private/professional katmanda değerlendirilir (public boundary kuralları).

---

## 12. Bekleyen uygulama detayları (implementation-pending)

OD-001 – OD-005 için **ilke kararları onaylandı**; aşağıdaki maddeler **`implementation-pending`** kalır:

| Alan | Açık soru |
|------|-----------|
| Vault ürün/teknoloji seçimi | Hangi vault/kasa implementasyonu? |
| Token yaşam döngüsü | Oluşturma, yenileme, iptal, bridge geçişi |
| Amaç kodu şeması | Purpose code listesi ve vault API |
| Segmentasyon detayı | Kaç segment, hangi sırada şifreleme |
| Şifreleme spesifikasyonu | Algoritma, anahtar türetme, rotation politikası |
| Vault UX anlatımı | OD-023 — kullanıcıya nasıl gösterilir |
| Şifreleme detayı (ürün ekseni) | OD-024 — Encrypted ekseni genişletme belgesi |
| Vault migration | OD-025 — ChatGPT kaynaklı maddelerin uygulama tanımına taşınması |
| Platform connector sırası | OD-036 — dış platform import planı |
| İç katman iletişim | OD-007 — imzalama/şifreleme protokolü (çapraz) |

**Çelişki kuralı:** Kaynak dosyalar arası çelişkide `docs/lumos-karar-sozlesmesi.md` ve ilgili canonical memory dosyası esas alınır; bu belge onları gevşetmez.

---

## 13. OD eşleme tablosu

| ID | Konu | Kaynak | Onaylanan ilke | Bekleyen uygulama | Durum |
|----|------|--------|----------------|-------------------|--------|
| OD-001 | Lumos Vault uygulaması | `security-architecture.md` | Katman modeli; Lumos secret taşımaz; vault ayrı katman | Somut vault ürünü/teknolojisi, depolama ve dağıtım modeli | **decision-approved** / **implementation-pending** |
| OD-002 | Token / vault entegrasyonu | `security-architecture.md` | Token/credential yüzeyde açık tutulmaz; bridge kontrollü geçit | Token formatı, credential şeması, bridge entegrasyon akışı | **decision-approved** / **implementation-pending** |
| OD-003 | Vault amaç bazlı erişim | `data-vault-user-data.md` | Sınırlı, amaçlı, onaylı ve görünür erişim | Amaç kodu listesi, vault-Lumos API sözleşmesi, yetki eşlemesi | **decision-approved** / **implementation-pending** |
| OD-004 | Risk dağılımı / segmentasyon | `data-vault-user-data.md` | Tek bileşen ele geçirildiğinde tüm sırlar açığa çıkmamalı | Somut segmentasyon, connector izolasyonu ve şifreleme modeli | **decision-approved** / **implementation-pending** |
| OD-005 | Şifreleme ve anahtar yönetimi | `data-vault-user-data.md` | Şifreleme ve anahtar yönetimi gerekli | Algoritma, KDF, döngü politikası, HSM/secure enclave yolu | **decision-approved** / **implementation-pending** |

**Durum açıklaması:**

- **decision-approved** — ilke kararı onaylandı; bu belge referansıdır.
- **implementation-pending** — teknik/uygulama detayı henüz tanımlanmadı; icat edilmedi.
- **closed** değil — uygulama tamamlanana kadar OD-001 – OD-005 açık kalır.

İndeks (`open-decisions-needs-review.md`) OD-001 – OD-005 satırları bu belgeyle **senkronize edildi** (2026-06-17).

---

## 14. Sonraki adım

1. OD-001 için vault **uygulama seçenekleri** (OSS/SaaS/harman) ayrı değerlendirme notu olarak hazırlansın — bu belgede seçim yapılmaz.
2. OD-003 amaç kodu şeması ve vault-Lumos API taslağı ayrı teknik belgede `implementation-pending` olarak açılsın.
3. OD-023 (Vault UX) ve OD-024 (Encrypted ekseni) ile çapraz hizalama kontrol edilsin.
4. Uygulama başladığında ilgili kod/test/bridge değişiklikleri ayrı commit/PR ile ve onaylı ilkelere uygun ilerler.

---

Son güncelleme: 2026-06-17
