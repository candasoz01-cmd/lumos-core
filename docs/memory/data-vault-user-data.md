# Veri sahipliği, kullanıcı verisi ve Vault — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamındaki veri sahipliği, dış platform taşıma, güvenli kasa (vault) ve public repo sınırı notlarının repo'ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir. **Gerçek secret, PII, credential veya kullanıcı verisi örneği bu dosyaya yazılmaz.**

---

## Yetki ve kaynak politikası

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak olarak kullanılır. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |
| **Public repo** | Taşınan içerik demo-safe olmalıdır; production secret, PII ve operasyonel altyapı detayı taşınmaz. |

Taşıma süreci ve durum tanımları: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Veri sahipliği

| # | İlke | Not |
|---|------|-----|
| 1 | **Kullanıcı verinin sahibidir.** | Taşındı |
| 2 | Lumos kullanıcıdan ayrı bir sahiplik kurmaz; kullanıcının **dijital uzantısı** ve cihazın **akıllı katmanı** olarak davranır. | Taşındı |
| 3 | Lumos'un otoritesi kullanıcının **açık iradesi**, **cihaz sahipliği** ve **verilen izinlerden** gelir. | Taşındı |

**Özet:** Veri kullanıcıya aittir; Lumos yalnızca kullanıcı adına, izin ve irade çerçevesinde hareket eder.

---

## Kullanıcı izni ve yetki kaynağı

| # | Kural | Not |
|---|--------|-----|
| 1 | Dış platformdan veri çekme, kalıcı taşıma/import veya kullanıcı adına silme/temizleme **kullanıcı onayı olmadan** yapılmaz. | Taşındı — çekirdek sözleşme ile hizalı |
| 2 | Lumos yetkisi: açık irade + cihaz sahipliği + izin profili. | Taşındı |
| 3 | Onaysız dış etkili aksiyon (ödeme, domain, e-posta, kalıcı silme, veri taşıma) başlatılmaz. | Taşındı — `security-architecture.md` ile uyumlu |

---

## Dış platformlardan veri taşıma

**Hedef (gelecek):** Kullanıcı dağınık kişisel bilgisini Lumos vault altında kendi kontrolünde birleştirir.

| # | İlke | Not |
|---|------|-----|
| 1 | Kullanıcılar zamanla diğer platformlardan veriyi Lumos'a taşıyabilmelidir. | Taşındı — gelecek özellik |
| 2 | Profil, içerik, kayıtlar, notlar, belgeler, medya, ayarlar ve benzeri kişisel veriler kullanıcının güvenli kasasına import edilebilir olmalıdır. | Taşındı |
| 3 | Taşıma: **kullanıcı kontrollü**, **onaylı**, **şeffaf**, **geri alınabilir**, **kaynak atıflı** olmalıdır. | Taşındı |
| 4 | Lumos, kullanıcı onayı olmadan dış platformlardan veri **çekmez**. | Taşındı |
| 5 | Lumos, kullanıcı onayı olmadan kalıcı migration/import **başlatmaz**. | Taşındı |
| 6 | Lumos, kullanıcı onayı olmadan kullanıcı adına silme/temizleme **yapmaz**. | Taşındı |

**Aksiyon özeti:** Çekme yok · onaysız kalıcı import yok · onaysız silme/temizleme yok · hedef = kullanıcı kontrollü konsolidasyon.

---

## Lumos Vault / güvenli kasa yaklaşımı

| # | İlke | Not |
|---|------|-----|
| 1 | Hassas kullanıcı bilgisi mümkün olduğunca Lumos **yüzeyinde** tutulmaz. | Taşındı |
| 2 | Lumos yetkili **geçit / orkestratör** rolündedir; ham secret'ları yüzeyde biriktirmez. | Taşındı |
| 3 | Gerektiğinde güvenli vault/katman, Lumos'a **sınırlı, amaç bazlı** erişim verir. | decision-approved / implementation-pending — [`vault-secret-token-decision.md`](./vault-secret-token-decision.md); OD-003 |
| 4 | Lumos ele geçirilirse tüm sırlar tek yerde açığa çıkmamalı; yük ve risk **dağıtılmış** olmalıdır. | decision-approved / implementation-pending — OD-004; somut segmentasyon modeli bekliyor |
| 5 | Token ve credential'lar Lumos yüzeyinde açık tutulmaz; güvenli vault/katman tercih edilir. | decision-approved / implementation-pending — OD-005; `security-architecture.md` ile hizalı |

**Referans ruhu:** Vault = kullanıcı kontrolünde güvenli katman; Lumos = izinli geçit.

---

## Public repo sınırı

| # | Kural | Not |
|---|--------|-----|
| 1 | Public `lumos-core` reposuna **secret**, **PII** veya **production credential** yazılmaz. | Taşındı |
| 2 | Bu dosya yalnızca **politika ve mimari not** içerir; gerçek kullanıcı verisi veya örnek credential taşınmaz. | Taşındı |
| 3 | Taşınan içerik demo-safe ve dokümantasyon-safe olmalıdır. | Taşındı — `public-github-sinirlari` ile uyumlu |

---

## Silme/temizleme sınırı

Workspace trash prensibi ve çekirdek sözleşme ruhuyla hizalı.

| # | Kural | Not |
|---|--------|-----|
| 1 | Kullanıcı adına silme/temizleme **onay olmadan** yapılmaz. | Taşındı |
| 2 | Otomatik kalıcı silme yok; yalnızca kullanıcının açık komutu + tek satır uyarı ile. | Taşındı — çekirdek sözleşme |
| 3 | Silinen içerik trash/silinen alana taşınır; trash aktif state kaynağı değildir. | Taşındı — `.lumos/trash/` prensibi |
| 4 | Dış platform migration sırasında kaynak tarafta temizlik/silme Lumos tarafından **otomatik** tetiklenmez. | Taşındı |

---

## Riskler

| # | Risk | Azaltma / not |
|---|------|----------------|
| 1 | Onaysız dış veri çekimi veya import | Kullanıcı onayı zorunlu; şeffaf akış |
| 2 | Hassas verinin Lumos yüzeyinde birikmesi | Vault katmanı; yüzeyde minimum tutma |
| 3 | Tek noktada tüm sırların açığa çıkması | Dağıtılmış yükleme ve risk — OD-004 implementation-pending |
| 4 | Public repo'ya PII/secret sızması | Politika + review; bu dosyada örnek veri yok |
| 5 | Migration geri alınamaz veya kaynak atıfsız | Geri alınabilirlik ve kaynak atıfı zorunlu tasarım hedefi |
| 6 | Vault şifreleme ve erişim modeli belirsiz | OD-005 implementation-pending — private katmanda netleştirilecek |

---

## Migration tablosu

ChatGPT / oturum bağlamından taşınan maddelerin hedef dosya ve durum özeti.

| # | Konu | ChatGPT / bağlam özeti | Hedef bölüm | Durum |
|---|------|------------------------|-------------|--------|
| 1 | Veri sahipliği | Kullanıcı sahibi; Lumos ayrı sahiplik kurmaz | Veri sahipliği | `[migrated]` |
| 2 | Lumos rolü | Dijital uzantı + cihaz akıllı katmanı | Veri sahipliği | `[migrated]` |
| 3 | Yetki kaynağı | Açık irade, cihaz sahipliği, izinler | Kullanıcı izni ve yetki kaynağı | `[migrated]` |
| 4 | Dış platform taşıma hedefi | Dağınık kişisel veriyi vault altında birleştirme | Dış platformlardan veri taşıma | `[migrated]` |
| 5 | Import kapsamı | Profil, içerik, kayıt, not, belge, medya, ayar | Dış platformlardan veri taşıma | `[migrated]` |
| 6 | Taşıma ilkeleri | Kontrollü, onaylı, şeffaf, geri alınabilir, kaynak atıflı | Dış platformlardan veri taşıma | `[migrated]` |
| 7 | Onaysız çekme yasağı | Dış platformdan kullanıcı onayı olmadan veri çekilmez | Dış platformlardan veri taşıma | `[migrated]` |
| 8 | Onaysız kalıcı import yasağı | Kalıcı migration/import onaysız başlamaz | Dış platformlardan veri taşıma | `[migrated]` |
| 9 | Onaysız silme yasağı | Kullanıcı adına silme/temizleme onaysız yapılmaz | Silme/temizleme sınırı | `[migrated]` |
| 10 | Vault yüzey ayrımı | Hassas veri ideal olarak Lumos yüzeyinde değil | Lumos Vault / güvenli kasa | `[migrated]` |
| 11 | Geçit rolü | Lumos yetkili geçit/orkestratör | Lumos Vault / güvenli kasa | `[migrated]` |
| 12 | Amaç bazlı erişim | Vault sınırlı, amaç bazlı erişim verir | Lumos Vault / güvenli kasa | `[decision-approved / implementation-pending]` OD-003 |
| 13 | Risk dağılımı | Ele geçirmede tek yerde tüm sırlar açığa çıkmamalı | Lumos Vault / güvenli kasa | `[decision-approved / implementation-pending]` OD-004 |
| 14 | Public repo | Secret, PII, production credential yok | Public repo sınırı | `[migrated]` |
| 15 | Platform connector'ları | Belirli dış platform entegrasyonları | — | `[needs-review]` |
| 16 | Şifreleme modeli | Vault içi şifreleme ve anahtar yönetimi | Lumos Vault / güvenli kasa | `[decision-approved / implementation-pending]` OD-005 |

---

## Manuel eklenecek maddeler

Aşağıdaki tabloya ChatGPT Saved Memories veya oturum bağlamından kopyalanan yeni maddeleri yapıştırın. Taşıma tamamlanınca durumu güncelleyin ve ilgili bölüme taşıyın.

| # | Durum | ChatGPT / bağlam metni (yapıştır) | Hedef bölüm | Not |
|---|--------|-------------------------------------|-------------|-----|
| 1 | `[queued]` | | | |
| 2 | `[queued]` | | | |
| 3 | `[queued]` | | | |
| 4 | `[queued]` | | | |
| 5 | `[queued]` | | | |

---

*Son güncelleme: 2026-06-20 (OD-003–005 doc-sync — envanter ab791c14 §13)*
