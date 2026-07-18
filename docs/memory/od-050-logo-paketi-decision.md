# OD-050/051 — Logo sistemi kararı

**Durum:** **`decision-approved`** — 15 Temmuz 2026 kullanıcı kararı. **Amendment (17 Temmuz 2026):** ana marka işareti ChatLumos'a değişti — bkz. § 4.
**Kaynak OD:** OD-050 (önceki logo arayışı), OD-051 (logo kullanım kuralları).
**Canonical assetler (17 Temmuz 2026 amendment sonrası):** `ui/public/chat-lumos-mark.svg` (ana marka işareti), `ui/public/lumos-tree-logo.svg` (ikincil kurumsal mühür), `ui/public/lumos-logo-mark.svg`.

---

## 1. Kilitli kimlik

| Katman | Sabit anlam |
|------|-------------|
| Ağaç | Ana sembol; We Lock AI ekosistemi ve insan merkezli kök |
| Ay | Arka planda destekleyici alan; ana sembolün önüne geçmez |
| Kuantum yıldızı | Küçük, merkezde çekirdek; teknoloji ve gelecek güvenliği |
| Altın + koyu zemin | Kurumsal ana renk dili |
| ChatLumos | Sohbet kabuğu + özgün kuantum çekirdeği; yalnızca sohbet yüzeylerinde |

---

## 2. Kullanım ilkeleri

| # | İlke |
|---|----------------|
| L1 | Ana geometri ağaç + ay + kuantum yıldızıdır; yeni bağımsız logo aranmaz |
| L2 | Küçük boyutta sade vektör, uygulama ikonunda koyu ve derinlikli varyant kullanılır |
| L3 | Hizmet kimlikleri ana geometriyi değiştirmez; yalnızca ikincil rozet, kısa etiket veya kontrollü vurgu rengi ekler |
| L4 | Distorsiyon, düşük kontrast, rastgele renk/efekt ve başka marka logosuyla birleşim yasaktır |
| L5 | Üçüncü taraf kurum logoları bağlantı yüzeyinde ayrı gösterilir; ortaklık izlenimi oluşturacak şekilde ana markaya katılmaz |
| L6 | Model sağlayıcısı sohbet yüzeyinde ayrı bir motor rozetiyle belirtilir; sağlayıcı logosu ChatLumos işaretinin geometrisine katılmaz |

---

## 3. OD eşleme

| OD | Durum |
|----|--------|
| OD-050 | closed — skull ve alternatif ana logo arayışı kapatıldı |
| OD-051 | decision-approved — kullanım sistemi sabitlendi |

**Sonraki adım:** Yeni hizmet çıktığında bu kurala bağlı ikincil varyant türetilir; ana logo yeniden tartışmaya açılmaz.

---

## 4. Amendment (17 Temmuz 2026) — ChatLumos ana marka işareti oldu

**Durum:** `decision-approved` — kullanıcı kararı, § 1-3'teki önceki kararı **değiştirir**, silmez.

Kullanıcı kararı: **ChatLumos artık tek ana marka işareti** — iOS (apple-touch-icon), web (favicon, nav, hero), OAuth, sosyal profil ve ürün UI dahil tüm Lumos yüzeylerinde birincil. Ağaç + ay + kuantum yıldızı işareti (`lumos-tree-logo.svg`) bu yüzeylerden çekildi; yalnızca **ikincil kurumsal mühür** olarak kalıyor.

| Önceki (§ 1, L1) | Yeni (bu amendment) |
|---|---|
| Ana geometri ağaç + ay + kuantum yıldızı; ChatLumos yalnızca sohbet yüzeylerinde | ChatLumos ana marka işareti; ağaç + ay + kuantum yıldızı ikincil kurumsal mühür |

**Kapsam netleştirmesi (bu oturumda yapılan yorum, açık teyit bekliyor):** Kod taramasında ağaç işaretinin iki farklı rolde kullanıldığı görüldü — (a) `ui/src/pages/index.astro` içindeki ayrı "We Lock AI" şirket nav bloğu (marka metni gerçekten "We Lock AI"), (b) `WeLockSiteNav.astro` paylaşılan bileşeni ve `index.astro` hero başlığı (marka metni "Lumos"). **En dar/tersinir yorum uygulandı:** ağaç işareti yalnızca (a) — index.astro'daki gerçek "We Lock AI" nav bloğu — içinde kaldı; (b) dahil "Lumos"u temsil eden her yer ChatLumos'a geçti. Kullanıcı "kurumsal mühür" ile daha geniş bir kapsam kastettiyse (ör. `WeLockSiteNav` de dahil), bu netleştirilip genişletilebilir.

**Değişen yüzeyler:**

| Yüzey | Dosya | Değişiklik |
|---|---|---|
| Web favicon / apple-touch-icon | `ui/src/pages/index.astro` ve 13 diğer sayfa (`accessibility`, `cyber`, `education`, `lab`, `integrations`, `slack`, `privacy`, `integrations/guide`, `integrations/google`, `integrations/github`, `integrations/mail`, `connect/mac`, `integrations/linear`) | `lumos-tree-logo.svg` → `chat-lumos-mark.svg` |
| Paylaşılan site nav ("Lumos" markalı, 13 sayfada kullanılıyor) | `ui/src/components/WeLockSiteNav.astro` | `lumos-tree-logo.svg` → `chat-lumos-mark.svg` |
| Homepage hero "Lumos" lockup | `ui/src/pages/index.astro` (hero, h1 "Lumos" yanı) | `lumos-tree-logo.svg` → `chat-lumos-mark.svg` |
| Ecosystem map "Lumos" merkez ikonu | `ui/src/pages/integrations.astro` | `lumos-tree-logo.svg` → `chat-lumos-mark.svg` |
| macOS uygulama ikonu | `macos/LumosApp/build-app.sh` | Kaynak `lumos-skull-mark.svg` idi (OD-050/051'de "retire edildi" denmişti ama script hiç güncellenmemişti — bu amendment aynı zamanda o eksik güncellemeyi de kapatıyor) → `chat-lumos-mark.svg` |
| Web app manifest (PWA ikon) | `ui/public/manifest.webmanifest` | Zaten `chat-lumos-mark.svg` kullanıyordu — değişiklik gerekmedi |
| Ürün UI (panel) | `ui/src/pages/panel.astro` | Zaten `chat-lumos-mark.svg` kullanıyordu — değişiklik gerekmedi |
| **Değişmeyen:** "We Lock AI" şirket nav bloğu | `ui/src/pages/index.astro` (ayrı inline nav, `aria-label="We Lock AI — sayfa başı"`) | `lumos-tree-logo.svg` korundu — ikincil kurumsal mühür kullanımı |
| OAuth consent ekranı ikonu, sosyal profil fotoğrafları | Repo dışı (Google/GitHub OAuth konsolu, LinkedIn/X vb. profil ayarları) | Repo'da dosya yok; bu amendment ile birlikte bu kanallara yüklenecek görsel **ChatLumos** olmalı — bkz. `public-identity-branding.md` § Marka ve görsel kimlik |

**Sonraki adım:** OAuth uygulama ikonu ve sosyal profil fotoğrafı yükleme işlemleri repo dışı, manuel adımlardır; kullanıcı bu kanalları güncellerken kaynak dosya olarak `ui/public/chat-lumos-mark.svg` kullanmalı.

---

Son güncelleme: 2026-07-17 (amendment — bkz. § 4)
