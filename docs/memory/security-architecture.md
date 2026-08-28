# Güvenlik mimarisi — canonical kayıt

## Amaç

ChatGPT **Saved Memories** içindeki güvenlik ilkeleri, kimlik/token/bridge sınırları, local-first davranış ve public repo kurallarına dair maddelerin repo'ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir. **Gerçek secret, token veya production credential bu dosyaya yazılmaz.**

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

## Güvenlik ilkeleri

| # | İlke | Kapsam | Not |
|---|------|--------|-----|
| 1 | Kullanıcı onayı olmadan **ödeme, domain satın alma, veri taşıma, kalıcı silme, e-posta okuma/gönderme/silme** yapılmaz. | dış etki / aksiyon | Taşındı |
| 2 | Silinen içerik kalıcı yok edilmez; **trash/silinen alana** taşınır. | veri yaşam döngüsü | Taşındı |
| 3 | İç katmanlar dışarıdan komut veya veri **doğrudan kabul etmez**; akış Lumos geçidinden geçer. | mimari sınır | Taşındı |
| 4 | Kod tabanı: **değişmez çekirdek**, kontrollü geliştirilebilir alanlar ve **sandbox ayrımı** korunur. | kod / repo | Taşındı — uygulama detayı kod sözleşmesinde |
| 5 | **İzinli yol da denetlenir.** Güvenlik yalnız erişimi kesmek değil; izin verilen yolların davranışını izlemektir. Guardrails dosyası gerçek izolasyon + izleme değildir. | izinli kanal / denetim | 2026-08-28 gerekçe — yeni yön değil; özet [`../security-architecture.md`](../security-architecture.md) SEC-006; yüzey [`../analysis/lumos-self-governance-surface.md`](../analysis/lumos-self-governance-surface.md) |
| 6 | **Ülke, fırsata duvar olmamalı; ödeme, kur, vergi ve uyum ise güven mimarisinin parçasıdır.** | güven mimarisi / ülke | 2026-08-28 gerekçe — yeni yön değil; özet [`../security-architecture.md`](../security-architecture.md) SEC-007; yüzey [`../analysis/lumos-self-governance-surface.md`](../analysis/lumos-self-governance-surface.md); ADR-017; OD-011 parkı durur |

---

## Kimlik / token / bridge güvenliği

**Uyarı:** Bu bölüm yalnızca **ilkeler ve mimari notlar** içindir. Gerçek anahtar, token, passphrase veya endpoint credential **asla** buraya yazılmaz.

| # | Konu | İlke / sınır | Not |
|---|------|--------------|-----|
| Kimlik | Dış dünya ile kimlik ve oturum akışı Lumos geçidi üzerinden yönetilir. | Taşındı |
| Token | Token ve credential'lar Lumos yüzeyinde açık tutulmaz; güvenli vault/katman tercih edilir. | Taşındı — [`vault-secret-token-decision.md`](vault-secret-token-decision.md); uygulama OD-001/002 |
| Bridge | Bridge yalnızca yetkili, onaylı ve Lumos kontrollü dış iletişim kanalıdır; iç katmanlara doğrudan köprü kurmaz. | Taşındı |
| Oturum / presence | Online işlem için kimlik ve kilit/presence koşulları sağlanmadan dış aksiyon başlatılmaz. | Taşındı — çekirdek sözleşme ile hizalı |

---

## Local-first ve offline sınırlar

Offline ve local-first davranışın güvenlik sınırları.

| # | Kural | Offline | Online | Not |
|---|--------|---------|--------|-----|
| 1 | Dış/network erişimi yalnızca online ve çağrıldığında; offline'da dış yazma/okuma yok. | evet | çağrıldığında | Çekirdek sözleşme ruhu |
| 2 | Emin olunmayan durumda dış etkili işlem yapılmaz. | evet | evet | Taşındı |
| 3 | Onaysız dış etkili aksiyon (ödeme, domain, veri taşıma, e-posta, kalıcı silme) başlatılmaz. | evet | evet | Taşındı |

**Referans ruhu (kod yok):** Offline'da dış/network yok; online'da yalnızca çağrıldığında çalışır. Emin olunmayan yerde işlem yapılmaz.

---

## Kalıcı silme ve onay kuralları

Workspace sözleşmesi ruhuyla hizalı notlar; uygulama detayı kodda, burada **politika özeti**.

| Konu | Kural (şablon — yapıştır / genişlet) |
|------|--------------------------------------|
| **Kalıcı silme** | Otomatik kalıcı silme yok; yalnızca kullanıcının açık komutu + tek satır uyarı ile; geri alınamaz. |
| **Trash prensibi** | Silinenler `.lumos/trash/` üzerinden; trash aktif state kaynağı değildir. |
| **Açık onay** | Kilidi açma, kalıcı silme, genel onaylı çok adımlı işler kullanıcı onayı gerektirir. |
| **Asla otomatik** | `permanent_delete`, dış yazma, geri dönüşsüz kullanıcı işlemi, kritik sistem ayarı — profil/onaydan bağımsız otomatik yapılmaz. |

| # | Taşınan madde (ChatGPT) | Sözleşme ile uyum | Not |
|---|-------------------------|-------------------|-----|
| 1 | Onaysız kalıcı silme yok; silinen içerik trash/silinen alana taşınır. | uyumlu | Taşındı |
| 2 | Onaysız ödeme, domain, veri taşıma, e-posta okuma/gönderme/silme yok. | uyumlu | Taşındı |

---

## Public repo sınırları

Public `lumos-core` için güvenlik taşıma filtresi.

**Taşınmaz:** production secret, authentication credential, payment/licensing, user-data sistemleri, private entegrasyon, operasyonel backend altyapısı, gerçek production URL'leri, PII.

**Taşınabilir:** demo-safe ilkeler, dokümantasyon-safe notlar, placeholder/stub açıklamalar, açık kaynak foundation kuralları.

| # | Madde | Demo-safe? | Not |
|---|--------|------------|-----|
| 1 | Public repoya secret, PII ve production credential yazılmaz veya taşınmaz. | evet | Taşındı |
| 2 | Taşınan güvenlik notları yalnızca ilke ve mimari özet düzeyindedir; operasyonel detay içermez. | evet | Taşındı |

---

## Lumos Vault (gelecek)

Gizli anahtarların Lumos yüzeyinde tutulmaması ilkesi; güvenli vault/katman yaklaşımı.

| # | Not | Durum | Bağımlılık / Not |
|---|-----|--------|------------------|
| 1 | Secret'lar ideal olarak Lumos yüzeyinde değil, ayrı güvenli vault/katmanda tutulur. | Taşındı | [`vault-secret-token-decision.md`](vault-secret-token-decision.md) §1–4 |
| 2 | Vault entegrasyonu, bridge ve token yönetimi ile birlikte netleştirilecek. | Taşındı | [`vault-secret-token-decision.md`](vault-secret-token-decision.md) §12; uygulama OD-001/002 |

---

## Migration tablosu

ChatGPT Saved Memories → bu dosyaya taşınan veya incelenecek maddeler.

| Kaynak | Durum | Proje ilgisi | Lumos etkisi | Not |
|--------|--------|--------------|--------------|-----|
| ChatGPT saved memory / oturum bağlamı — onaysız dış aksiyon yasağı | Taşındı | lumos-core | Aksiyon kapısı | Güvenlik ilkeleri §1 |
| ChatGPT saved memory / oturum bağlamı — trash, kalıcı yok etme yok | Taşındı | lumos-core | Veri yaşam döngüsü | Kalıcı silme tablosu §1 |
| ChatGPT saved memory / oturum bağlamı — iç katmana doğrudan dış akış yok | Taşındı | lumos-core | Gateway zorunluluğu | Güvenlik ilkeleri §3 |
| ChatGPT saved memory / oturum bağlamı — değişmez çekirdek, sandbox | Taşındı | lumos-core | Kod güvenliği | Güvenlik ilkeleri §4 |
| ChatGPT saved memory / oturum bağlamı — public repo secret/PII yasağı | Taşındı | lumos-core | Public boundary | Public repo §1 |
| ChatGPT saved memory / oturum bağlamı — Lumos vault / secret yüzeyi | Taşındı | lumos-core | Vault vizyonu | [`vault-secret-token-decision.md`](vault-secret-token-decision.md); OD-025 closed |
| ChatGPT saved memory / oturum bağlamı — token/vault uygulama detayı | Taşındı | lumos-core | Kimlik katmanı | [`vault-secret-token-decision.md`](vault-secret-token-decision.md) §12; uygulama OD-001/002 |

**Durum kısaltmaları:** Taşındı · needs-review · eski (detay: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md)).

---

## Manuel eklenecek maddeler

Aşağıya henüz sınıflandırılmamış veya yeni kopyalanan maddeleri yapıştırın; uygun bölüme taşındıktan sonra buradan temizleyin veya durumu güncelleyin.

| # | Durum | ChatGPT metni (yapıştır) | Hedef bölüm | Not |
|---|--------|---------------------------|-------------|-----|
| 1 | incelenecek | | | |
| 2 | incelenecek | | | |
| 3 | incelenecek | | | |
| 4 | incelenecek | | | |
| 5 | incelenecek | | | |

---

*Son güncelleme: 2026-08-28 (ülke/ödeme güven mimarisi — SEC-007 gerekçe; yeni yön değil; SEC-006 durur)*
