# Lumos Panel — Acımasız UI Denetimi (Mevcut Ekran)

| Alan | Değer |
|------|-------|
| **Tarih** | 2026-06-22 |
| **Kapsam** | `ui/src/pages/panel.astro` (mevcut), `lumos-tokens.css`, `LanguageSwitcher.astro` |
| **Kod değişikliği** | Yok — yalnızca eleştiri |
| **Yöntem** | Mevcut DOM/CSS okuma; gelecek spec özellikleri **dışarıda** |

---

## Ana soru

> **Ekrandan ne kaldırırsak ürün daha kaliteli görünür?**

**Tek cümle:** Glow’lu arka plan katmanları, 50’den fazla işlevsiz konsept kartı, demo formlar, çift navigasyon ve boş sohbetteki yığılmış açıklama kutularını kaldırırsak panel anında kurumsal bir çalışma alanına döner; kalan Sohbet, Görevler ve Dosyalar yüzeyleri zaten yeterince güçlü.

---

## Özet sayılar

| Metrik | Değer |
|--------|-------|
| **REMOVE maddesi** | **32** |
| Konsept `medya-card` örneği | 53 |
| Demo paylaşım proto bloğu | 3 (Medya, Sosyal, Posta) |
| Birincil nav öğesi | 9 (+ her birinde gereksiz «Önizleme» rozeti ×5) |
| Lumos çekirdeği nav öğesi | 9 (mobilde tamamen gizli) |
| Kuantum girişi | 2 (çift) |

---

## KEEP — Savunulabilir olanlar

Bunlar minimal/profesyonel hedefe en yakın parçalar; dokunulmadan korunmalı.

| Öğe | Neden |
|-----|-------|
| **Sohbet compose bar** (`chat-compose--gpt`) | Tek odaklı iş akışı; GPT-benzeri düzen tanıdık ve işlevsel. |
| **Görev kartları + detay diyaloğu** | Gerçek veri, net hiyerarşi, `--lumos-card-border` dili tutarlı. |
| **Dosyalar yükleme + sonuç yığını** | Çalışan özellik; gereksiz süs yok. |
| **`lumos-tokens.css` omurgası** | `#0a0e14` / teal / spacing değişkenleri doğru yönde; sorun token değil uygulama aşırılığı. |
| **`LanguageSwitcher`** | Kompakt, token uyumlu; header’da tek işi var. |
| **Onay diyaloğu** (`lumos-confirm-dialog`) | Güven modelini görselleştirir; abartılı değil. |
| **iOS `max(16px, 1em)` kuralı** | Mobil zoom disiplini — profesyonel ürün işareti. |
| **Posta/Sosyal’de gizlenen `medya-card-list`** | Bilinçli odak kararı (#525); doğru yönde. |

---

## SIMPLIFY — Azalt / birleştir (işlev kalır)

| ID | Önem | Öğe | Ne yapılmalı |
|----|------|-----|--------------|
| S-01 | Yüksek | **Mod rozeti + Ayarlar mod kartı** | Aynı «Offline / Sınırlı / Tam» kontrolü header’da ve `#panel-ayarlar` içinde iki kez; biri kalmalı. |
| S-02 | Yüksek | **Altyapı özeti** | Header `panel-conn-badge` + Ayarlar `panel-infra-status-dl` aynı bilgiyi iki yerde anlatıyor; tek yüzey yeter. |
| S-03 | Yüksek | **Compose ek düğmeleri** | `+` menüsü içinde kamera, pano, ses; ayrıca bağımsız kamera ve ses düğmeleri — üç kanal aynı işe gidiyor. |
| S-04 | Orta | **Modül başlık üçlüsü** | `panel-module-eyebrow` + `h2` + `panel-module-lead` her önizleme modülünde aynı ritim; eyebrow kalkınca lead tek satıra iner. |
| S-05 | Orta | **Görevler üst metinleri** | `[Yerel]` rozeti + uzun intro + `gorevler-codex-warning` — üç katman aynı «yerel / dikkatli ol» mesajını veriyor. |
| S-06 | Orta | **Medya modülü** | Outbox (işlevsel) + 5 konsept kart + demo form; outbox tek başına modülü taşır, geri kalanı sadeleştirilmeli. |
| S-07 | Orta | **Kuantum canlı + mock** | API gelince progressive disclosure var; şimdilik banner + intro + mock + 4 konsept kartı dört katman — iki katmana inmeli. |
| S-08 | Orta | **Yetenekler tablosu** | `lumos-capability-legend` (3 satır sözlük) + 7 satır grid; legend kalkınca tablo okunur kalır. |
| S-09 | Düşük | **Hardcode renkler** | `#e9eef5`, `#f2efe6`, `rgb(210 232 252)` → token’a çekilince glow azaltmadan bile tutarlılık artar. |
| S-10 | Düşük | **Radius dağınıklığı** | 4px rozet, 5px bubble kuyruk, 10px capability kart — token dışı; tek ölçek hissi için birleştir. |

### On kriter — SIMPLIFY eşlemesi

| # | Kriter | SIMPLIFY karşılığı |
|---|--------|-------------------|
| 3 | Gereksiz boşluklar | S-04, S-05 — üst başlık yığını ve çift padding |
| 4 | Gereksiz metinler | S-05, S-06 — tekrarlayan uyarı ve intro |
| 6 | Gereksiz menü hiyerarşisi | S-01, S-02 — çift kontrol yüzeyleri |
| 8 | Okunabilirlik | S-09, S-10 — token dışı küçük puntolar |

---

## REMOVE — Tamamen gitmeli (görsel/UX gürültüsü)

Her madde işlevi **bozmadan** kaldırılabilecek gürültüdür. Önem: **Kritik** / **Yüksek** / **Orta** / **Düşük**.

### Arka plan, glow, efekt (Kriter 1–2)

| ID | Önem | Kaldır | Gerekçe |
|----|------|--------|---------|
| R-01 | **Kritik** | `body` üzerinde `--panel-body-wash` (4 katmanlı radial + gradyan) | Sayfa zaten koyu; wash «kontrol odası» hissi veriyor, içeriği gölgeliyor. |
| R-02 | **Yüksek** | `.panel-main` `radial-gradient(ellipse … rgb(12 40 88 / 0.18))` | Body wash üstüne ikinci vurgu — gereksiz derinlik. |
| R-03 | **Kritik** | `.chat-history-shell` `--panel-chat-wash` + `inset 0 1px 48px teal-deep / 0.22` | Sohbet alanı neon tüp gibi parlıyor; mesajlar ikinci planda. |
| R-04 | **Kritik** | `.chat-thread` `inset 0 0 72px teal-deep / 0.2` | R-03 ile aynı bütçeyi ikiye katlıyor. |
| R-05 | **Yüksek** | Aktif nav `box-shadow: 6px 0 22px … 2px 0 12px` teal glow | Sekme seçimi için üç katman gölge — sol border yeter. |
| R-06 | **Yüksek** | `.panel-conn-badge[data-state="ok"]` cyan metin + `0 0 14px` dış glow | «Bağlı» durumu kutlama yapıyor; nötr metin yeter. |
| R-07 | **Orta** | `.panel-user-mode-badge[data-mode="full"]` `0 0 8px` teal glow | Mod rozeti alarm değil bilgi; parlaması profesyonelliği düşürür. |
| R-08 | **Orta** | Nav/chat scrollbar `--lumos-teal-40` / `48` thumb | Dekoratif dikkat çekici; `--lumos-teal-22` yeter. |
| R-09 | **Düşük** | Header `border-bottom: var(--lumos-teal-38)` | Fazla parlak ayırıcı; `--lumos-border` yeter. |
| R-10 | **Düşük** | Dialog `backdrop-filter: blur(2px)` | Glassmorphism izi; düz yarı saydam overlay yeter. |

### Konsept kartları ve demo yüzeyleri (Kriter 7, 10)

| ID | Önem | Kaldır | Gerekçe |
|----|------|--------|---------|
| R-11 | **Kritik** | Tüm `medya-card-list` konsept kartları (**53 adet**) | Ses, Medya, YZ, Yayıncılık, Entegrasyon, Kimlik, Güvenlik, Dünya, Ayarlar (çoğu), Kuantum altı — pazarlama metni yığını; işlev yok. |
| R-12 | **Kritik** | `panel-share-proto--demo` ×3 (Medya, Sosyal, Posta) | Devre dışı «Gönder (demo kapalı)» + doldurulabilir form = wireframe; güveni zedeler. |
| R-13 | **Kritik** | `panel-quantum-readiness-mock` varsayılan görünür blok | Mock güvenlik raporu ürün gibi sunuluyor; API yokken tek satır «veri yok» yeter. |
| R-14 | **Yüksek** | `panel-quantum-readiness-banner` içindeki 4 rozet (DEMO, docs, no-live, mvp) | Aynı «bu gerçek değil» mesajı dört kez. |
| R-15 | **Yüksek** | Kuantum `Entropy Lab` başlık + açıklama + gizli `dl` | Boş deneysel alan; modülü daha da şişiriyor. |
| R-16 | **Yüksek** | Kuantum altı 4 `medya-card` (c1–c4) | R-13 mock ile aynı temayı tekrar ediyor. |

### Sohbet boş durumu (Kriter 4, 5)

| ID | Önem | Kaldır | Gerekçe |
|----|------|--------|---------|
| R-17 | **Yüksek** | `chat-capability-card` (Yapabilirim / Şu an yapmam) | Boş thread’de kart + 4 madde + 4 madde; ilk bakışta «uygulama mı dokümantasyon mu?» sorusu. |
| R-18 | **Yüksek** | Boş thread’de 3–4 `lumos-security-note` (onay, gizli bilgi, kamera izni) | Tek cümle yeter; dört dipnot chat alanını hukuk metnine çeviriyor. |
| R-19 | **Orta** | `chat-empty-hint` mavi-gri `rgb(210 232 252)` renk | Token dışı palet; «Lumos hazır» tek satır neutral tone ile yeter. |

### Navigasyon ve rozet gürültüsü (Kriter 6)

| ID | Önem | Kaldır | Gerekçe |
|----|------|--------|---------|
| R-20 | **Kritik** | `panel-nav__lumos` ikinci sütun (9 öğe, 8 önizleme) | Masaüstünde sol sütunun yarısını konsept menü kaplıyor; mobilde zaten `display: none`. |
| R-21 | **Yüksek** | Kuantum çift giriş (`panel-nav-research-chip` primary + lumos nav) | Aynı modül iki yerde; kafa karıştırıcı. |
| R-22 | **Yüksek** | `panel-nav-collapsible` toggle («Çalışma», «Lumos çekirdeği») | Tek grup, varsayılan açık/kapalı — gereksiz tıklama katmanı. |
| R-23 | **Yüksek** | Nav’da her inactive modülde `lumos-soon-badge` «Önizleme» (×12 toplam) | Modül adı + sekme yeter; 12 mini rozet visual noise. |
| R-24 | **Orta** | `panel-nav-research-chip` özel chip stili | Kuantum’u «araştırma» diye ayırır; diğer önizleme modüllerinden tutarsız. |
| R-25 | **Düşük** | `panel-nav-sig` («Lumos panel») | Zaten `display: none`; ölü DOM. |

### Metin ve tekrar (Kriter 4)

| ID | Önem | Kaldır | Gerekçe |
|----|------|--------|---------|
| R-26 | **Orta** | `panel-header-tagline` («Kontrollü çalışma alanı») | `h1` Lumos Panel zaten konumu söylüyor; header kalabalık. |
| R-27 | **Orta** | Rozet metni `Mod ·` ön eki | «Sınırlı» tek başına anlaşılır; nokta-ayırıcı teknik his. |
| R-28 | **Orta** | `panel-data-flow-badge` köşeli etiketler (`[Yerel]`, `[Harici Servis]`, `[Demo — bağlı değil]`) | 2000’ler wiki sözdizimi; gövde metnine bir cümle olarak gömülebilir veya kalkar. |
| R-29 | **Orta** | `gorevler-codex-warning` («Bu panel önizleme sürümüdür…») | Nav’da zaten önizleme rozetleri var; görevler çalışan modül — uyarı yanlış ton. |
| R-30 | **Orta** | Uzun `panel-module-lead` / `medya-intro` paragrafları (Ses 4 cümle, Medya 3 cümle vb.) | Önizleme modülünde başlık + tek cümle yeter; paragraf manifesto hissi. |
| R-31 | **Orta** | `panel-module-eyebrow` («Önizleme», «Operasyon») | `h2` ile aynı bilgi; uppercase 0.62rem okunaksız. |

### Profesyonelliği düşüren detaylar (Kriter 9)

| ID | Önem | Kaldır | Gerekçe |
|----|------|--------|---------|
| R-32 | **Orta** | `gorevler-proto` / `panel-share-proto` sınıf adları ve görsel «proto» çerçeveleri | İsim ve stil «henüz bitmedi» bağırıyor; çalışan görev/dosya akışıyla aynı kutuda durmamalı. |

*Not: R-11 tek başına 53 DOM öğesi sayılır; REMOVE maddesi sayısı **32** bağımsız karar grubudur.*

---

## On kriter — tam eşleme

| # | Kriter | Ana teşhis | Önem | REMOVE / SIMPLIFY |
|---|--------|------------|------|-------------------|
| 1 | Görsel karmaşa | Üst üste wash + kart + border + rozet | Kritik | R-01–04, R-11, R-17–18 |
| 2 | Glow / blur / efekt | Teal inset 48–72px, nav glow, conn neon | Kritik | R-03–08, R-10 |
| 3 | Gereksiz boşluklar | Modül head üçlüsü, çift panel çerçevesi | Orta | S-04, S-05 |
| 4 | Gereksiz metinler | 53 konsept kartı, uzun intro, güvenlik yığını | Kritik | R-11, R-18, R-28–30 |
| 5 | İlk bakışta anlaşılmayan | Mod vs bağlantı vs önizleme; mock = gerçek sanılır | Yüksek | R-06, R-12–13, R-17, S-01 |
| 6 | Gereksiz menü hiyerarşisi | İki sütun nav, collapsible, çift Kuantum | Kritik | R-20–24, S-01 |
| 7 | Tekrar eden kartlar | 5’li `medya-card` şablonu ×11 modül | Kritik | R-11, R-16 |
| 8 | Okunabilirlik | Mobil 0.4–0.58rem nav/rozet; mavi-gri metin | Kritik | R-19, S-09; mobil CSS satırları ~3290–3375 |
| 9 | Profesyonelliği düşüren | Demo form, mock quantum, proto sınıfları | Kritik | R-12–13, R-32 |
| 10 | Silinmesi gereken | Yukarıdaki REMOVE listesi | — | **32 madde** |

---

## Modül bazlı acımasız notlar

### Sohbet
Çalışan çekirdek compose iyi; boş durum bir «mini landing page» gibi davranıyor. Capability kart + dört güvenlik notu kalkınca thread nefes alır. Chat wash kalkınca bubble’lar öne çıkar.

### Görevler
En olgun modül. `gorevler-codex-warning` ve `[Yerel]` rozeti gereksiz özgüven eksikliği sinyali. Altın odak halkası (S-09 kapsamında) teal ile çelişiyor — glow değil ama simplify.

### Dosyalar
Sade ve işlevsel. Native file input çirkin ama REMOVE değil SIMPLIFY (özel buton).

### Ses / Medya / Sosyal / Posta
Önizleme modülleri ürün değil broşür. Medya’da outbox gerçek; geri kalanı %90 gürültü. Sosyal/Posta’da yalnızca demo form var — kartlar zaten gizli, formlar da gitmeli.

### Kuantum
En tehlikeli modül: mock veri + DEMO banner + teknik dl + 4 felsefe kartı. Güven ürününde sahte veri varsayılan gösterilmez.

### Lumos çekirdeği (Yayıncılık … Ayarlar)
Nav’ın yarısı; içeriklerin %90’ı `medya-card`. Yetenekler ve Ayarlar’daki infra kartı hariç hepsi konsept. Mobilde nav tamamen kaybolunca Yetenekler/Ayarlar erişilemez — bu bir REMOVE değil ama R-20’nin yan etkisi.

### Header
İki rozet + dil + marka + tagline dar ekranda 0.4rem puntoda sıkışıyor. Tagline ve «Mod ·» ön eki ilk kaldırılacaklar.

### `LanguageSwitcher`
Temiz. Aktif pill gölgesi (R-09 benzeri düşük öncelik) dışında dokunma.

### `lumos-tokens.css`
`--panel-body-wash` ve `--panel-chat-wash` tanımları «premium» adıyla cyberpunk bütçesi açıyor; token dosyası simplify edilmeli ama bu rapor uygulama önermez — sadece wash’ların fiilen kaldırılması gerektiğini kaydeder.

---

## Öncelik sırası (kaldırma — uygulama yok, sadece sıra)

1. **R-03, R-04, R-01** — glow bütçesi (en hızlı «wow ama ucuz» kazanım)
2. **R-11, R-12** — konsept kartları + demo formlar (prototip hissini keser)
3. **R-20, R-21, R-23** — nav sadeleştirme
4. **R-17, R-18** — boş sohbet sadeleştirme
5. **R-13, R-14** — Kuantum mock şeffaflığı

---

## Önceki raporla fark

[`ui-design-audit-report.md`](./ui-design-audit-report.md) 31 bulgu + landing kapsar; bu belge **yalnızca panel**, **kaldırma odaklı** ve spec’teki gelecek özellikleri (tema toggle, geçmiş paneli, Lucide nav) **saymaz**. Aynı glow ve demo bulguları burada REMOVE ID’leriyle keskinleştirildi.

---

*Bu belge yalnızca analiz amaçlıdır; kod, tasarım mockup veya yeni özellik önerisi içermez.*
