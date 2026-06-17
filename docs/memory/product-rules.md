# Ürün kuralları — canonical kayıt

## Amaç

ChatGPT **Saved Memories** içindeki ürün ilkeleri, kullanıcı deneyimi kuralları ve Lumos–kullanıcı ilişkisine dair maddelerin repo'ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir.

---

## Yetki ve kaynak politikası

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak olarak kullanılır. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |
| **Public repo** | Taşınan içerik public `lumos-core` sınırına uymalıdır (gizli anahtar, PII, production URL vb. taşınmaz). |

Taşıma süreci ve durum tanımları: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Ürün ilkeleri (product principles)

| # | Madde | Not |
|---|--------|-----|
| 1 | Lumos, kullanıcıya açık **tek dış yüzey**dir. | Taşındı |
| 2 | Kando, Cando ve Bando **iç katmanlardır**; kullanıcıya gösterilmez. | Taşındı |
| 3 | Lumos, kullanıcı ile dış dünya arasında **güvenli geçit ve orkestratör** olarak konumlanır. | Taşındı |
| 4 | İç katmanlar dışarıdan komut veya veri **doğrudan kabul etmez**; akış Lumos geçidinden geçer. | Taşındı |

---

## Kullanıcı deneyimi kuralları

| # | Kural | Bağlam | Not |
|---|--------|--------|-----|
| 1 | Kullanıcı yalnızca Lumos yüzeyiyle etkileşir; iç katman adları veya arayüzleri dışa açılmaz. | panel / chat | Taşındı |
| 2 | Komut ve veri akışı **Lumos geçidi** üzerinden yönlendirilir; bypass yok. | genel | Taşındı |
| 3 | Gizli anahtarlar ideal olarak Lumos yüzeyinde tutulmaz; güvenli vault/katman yaklaşımı korunur. | güvenlik UX | needs-review — vault detayı genişletilecek |

---

## Lumos'un kullanıcıyla ilişkisi

Lumos, kullanıcının dijital uzantısı ve cihaz katmanı olarak konumlanır.

- **Dijital uzantı:** Lumos, kullanıcıdan ayrı sahiplik kurmaz; kullanıcının dijital uzantısı olarak tasarlanır.
- **Cihaz katmanı:** Cihazın akıllı katmanı olarak çalışır; kullanıcı adına koordine eder, sahip olmaz.
- **Sınır ve rol:** Dış dünya ile tek temas noktasıdır; iç katmanları kullanıcıya göstermez.
- **Güven ilişkisi:** Kullanıcı verinin sahibidir; Lumos aracı ve geçittir.

| # | Madde | Katman (dijital / cihaz / genel) | Not |
|---|--------|----------------------------------|-----|
| 1 | Lumos kullanıcıdan bağımsız sahiplik kurmaz. | dijital | Taşındı |
| 2 | Lumos, cihazın akıllı koordinasyon katmanıdır. | cihaz | Taşındı |
| 3 | Lumos, kullanıcı–dış dünya arasında güvenli orkestratördür. | genel | Taşındı |

---

## Veri sahipliği ve taşıma

Taşınacak maddeler şu eksenlerde gruplanır: **user-owned**, **consent**, **encrypted**, **reversible**.

| Eksen | Açıklama (şablon) | Taşınan madde |
|-------|-------------------|---------------|
| **User-owned** | Veri kullanıcıya aittir; Lumos aracıdır. | Veri sahibi kullanıcıdır; Lumos sahiplik iddia etmez. |
| **Consent** | Taşıma/ paylaşım açık onay gerektirir. | Veri taşıma ve dış etkili işlemler kullanıcı onayı olmadan yapılmaz. |
| **Encrypted** | Hassas veri şifreli tutulur / taşınır. | needs-review — şifreleme detayı ayrı kaynakta genişletilecek |
| **Reversible** | Geri alınabilir / taşınabilir akışlar tercih edilir. | Silinen içerik kalıcı yok edilmez; trash/silinen alana taşınır (bkz. güvenlik mimarisi). |

| # | Madde | Eksen | Not |
|---|--------|-------|-----|
| 1 | Kullanıcı verinin sahibidir. | user-owned | Taşındı |
| 2 | İç katmanlar dış kaynaktan gelen komut/veriyi doğrudan almaz. | consent / akış | Taşındı |
| 3 | Veri taşıma ve dış paylaşım açık onay gerektirir. | consent | Taşındı |

---

## Panel / chat davranış kuralları

| # | Kural | Bağlam (panel / chat / CLI) | Not |
|---|--------|-------------------------------|-----|
| 1 | Yanıt ve arayüz yalnızca Lumos kimliğiyle sunulur; iç katman adları kullanıcıya yansıtılmaz. | panel / chat | Taşındı |
| 2 | Dış etkili veya geri dönüşsüz işlemler (ödeme, domain, kalıcı silme, e-posta vb.) kullanıcı onayı olmadan başlatılmaz. | panel / chat / CLI | Taşındı — detay: `security-architecture.md` |
| 3 | Onay gerektiren adımlarda sessiz veya varsayılan-onaylı uygulama yapılmaz. | panel / chat | Taşındı |

---

## Migration tablosu

ChatGPT Saved Memories → bu dosyaya taşınan veya incelenecek maddeler.

| Kaynak | Durum | Proje ilgisi | Lumos etkisi | Not |
|--------|--------|--------------|--------------|-----|
| ChatGPT saved memory / oturum bağlamı — Lumos tek dış yüzey | Taşındı | lumos-core | Ürün sınırı | Ürün ilkeleri §1 |
| ChatGPT saved memory / oturum bağlamı — Kando/Cando/Bando iç katman | Taşındı | lumos-core | UX gizleme | Ürün ilkeleri §2 |
| ChatGPT saved memory / oturum bağlamı — Lumos güvenli geçit/orkestratör | Taşındı | lumos-core | Mimari rol | Ürün ilkeleri §3 |
| ChatGPT saved memory / oturum bağlamı — kullanıcı sahipliği, dijital uzantı | Taşındı | lumos-core | Trust modeli | Lumos–kullanıcı ilişkisi |
| ChatGPT saved memory / oturum bağlamı — iç katmanlara doğrudan dış akış yok | Taşındı | lumos-core | Gateway zorunluluğu | Veri sahipliği §2 |
| ChatGPT saved memory / oturum bağlamı — komut/veri Lumos geçidi | Taşındı | lumos-core | Akış kuralı | UX kuralları §2 |
| ChatGPT saved memory / oturum bağlamı — secret'lar Lumos yüzeyinde değil | needs-review | lumos-core | Vault vizyonu | UX §3; vault detayı genişletilecek |
| ChatGPT saved memory / oturum bağlamı — şifreleme detayı | needs-review | lumos-core | Veri koruma | Veri sahipliği ekseni Encrypted |

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

*Son güncelleme: 2026-06-17*
