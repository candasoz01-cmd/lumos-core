# Güvenlik mimarisi — canonical kayıt

## Amaç

ChatGPT **Saved Memories** içindeki güvenlik ilkeleri, kimlik/token/bridge sınırları, local-first davranış ve public repo kurallarına dair maddelerin repo’ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir. **Gerçek secret, token veya production credential bu dosyaya yazılmaz.**

---

## Yetki ve kaynak politikası

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak olarak kullanılır. |
| **`docs/memory/`** | **Canonical’dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |
| **Public repo** | Taşınan içerik demo-safe olmalıdır; production secret, PII ve operasyonel altyapı detayı taşınmaz. |

Taşıma süreci ve durum tanımları: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Güvenlik ilkeleri

*(ChatGPT Saved Memories’ten manuel yapıştır — boş bırakılacak şablon.)*

| # | İlke | Kapsam | Not |
|---|------|--------|-----|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## Kimlik / token / bridge güvenliği

**Uyarı:** Bu bölüm yalnızca **ilkeler ve mimari notlar** içindir. Gerçek anahtar, token, passphrase veya endpoint credential **asla** buraya yazılmaz.

*(Placeholder — ChatGPT’ten taşınacak maddeleri yapıştır.)*

| # | Konu | İlke / sınır | Not |
|---|------|--------------|-----|
| Kimlik | | | |
| Token | | | |
| Bridge | | | |
| Oturum / presence | | | |

---

## Local-first ve offline sınırlar

Offline ve local-first davranışın güvenlik sınırları.

| # | Kural | Offline | Online | Not |
|---|--------|---------|--------|-----|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**Referans ruhu (kod yok):** Offline’da dış/network yok; online’da yalnızca çağrıldığında çalışır. Emin olunmayan yerde işlem yapılmaz.

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
| 1 | | | |
| 2 | | | |

---

## Public repo sınırları

Public `lumos-core` için güvenlik taşıma filtresi.

**Taşınmaz:** production secret, authentication credential, payment/licensing, user-data sistemleri, private entegrasyon, operasyonel backend altyapısı, gerçek production URL’leri, PII.

**Taşınabilir:** demo-safe ilkeler, dokümantasyon-safe notlar, placeholder/stub açıklamalar, açık kaynak foundation kuralları.

| # | Madde | Demo-safe? | Not |
|---|--------|------------|-----|
| 1 | | | |
| 2 | | | |

---

## Lumos Vault (gelecek)

*(Placeholder — henüz tanımlanmamış veya ChatGPT’ten taşınacak vizyon notları.)*

| # | Not | Durum | Bağımlılık / Not |
|---|-----|--------|------------------|
| 1 | | gelecek | |
| 2 | | gelecek | |

---

## Migration tablosu

ChatGPT Saved Memories → bu dosyaya taşınan veya incelenecek maddeler.

| Kaynak | Durum | Proje ilgisi | Lumos etkisi | Not |
|--------|--------|--------------|--------------|-----|
| | Taşındı / incelenecek / eski | | | |
| | Taşındı / incelenecek / eski | | | |
| | Taşındı / incelenecek / eski | | | |

**Durum kısaltmaları:** Taşındı · incelenecek · eski (detay: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md)).

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
