# Lumos Panel — Senior Product Designer Review

| Alan | Değer |
|------|-------|
| **Tarih** | 2026-06-22 |
| **Rol** | Senior product designer (analiz only) |
| **Kapsam** | `ui/src/pages/panel.astro` (PR #525 sonrası), `lumos-tokens.css`, `LanguageSwitcher.astro` |
| **Referanslar** | ChatGPT, Linear, Notion, Raycast, Arc Browser |
| **Kod / özellik önerisi** | Yok |

---

## Executive summary

Lumos Panel’in omurgası doğru: koyu yüzey, teal aksan, GPT-benzeri compose bar ve çalışan Görevler/Dosyalar modülleri gerçek bir ürün iskeleti sunuyor. Sorun tasarım dili değil — **görsel bütçenin yanlış harcanması**. ChatGPT boş sohbette tek cümle + input; Linear navigasyonda etiket, rozet yok; Notion önizleme sayfalarında bile “henüz yok” demek yerine boş yüzey bırakır. Lumos ise aynı ekranda dört katmanlı arka plan wash’ı, 53 konsept kartı, 12 «Önizleme» rozeti ve boş thread’de mini dokümantasyon kartı üst üste bindiriyor. Sonuç: **fonksiyonel çekirdek var, algı «premium araç» değil «kontrol odası demosu»**.

Token sistemi (`#0a0e14`, spacing, radius) Raycast/Arc seviyesinde sakin kalmaya uygun; uygulama katmanı bu disipline ihanet ediyor. %20 kalite sıçraması yeni özellik değil, **gürültü çıkarma** ile gelir — özellikle glow stack, konsept kartları ve çift navigasyon.

---

## KEEP — Savunulabilir olanlar

| Öğe | Gerekçe |
|-----|---------|
| **Sohbet compose bar** (`chat-compose--gpt`) | ChatGPT ile aynı mental model: tek input satırı, yan eylemler, altta sabit. Kullanıcı 5 saniyede «buradan yazacağım» der. |
| **Görev kartları + detay diyaloğu** | Linear issue row’a yakın: başlık, durum, net tıklanabilir alan. Gerçek veri; kart dili `--lumos-card-border` ile tutarlı. |
| **Dosyalar yükleme akışı** | Notion import yüzeyi kadar sade — form, sonuç, fazla süs yok. |
| **`lumos-tokens.css` renk omurgası** | Arc/Linear dark palette ile uyumlu navy + kontrollü teal. Sorun token değil, token dışı hardcode ve wash aşırılığı. |
| **`LanguageSwitcher`** | Raycast settings pill’e benzer kompaktlık; header’da tek iş, token uyumlu. Aktif TR pill’deki hafif gölge tolere edilebilir. |
| **Onay diyaloğu** (`lumos-confirm-dialog`) | Güven ürününde görünür onay doğru; Linear’ın destructive confirm’i gibi abartısız kalmalı (mevcut hali uygun). |
| **iOS `max(16px, 1em)` textarea kuralı** | Profesyonel mobil disiplin; ChatGPT mobile ile aynı sınıf. |
| **Sohbet modülünün border’sız tam genişlik düzeni** | `#panel-sohbet` diğer modüllerden farklı — chat uygulaması gibi edge-to-edge; doğru IA kararı. |
| **Posta/Sosyal’de gizlenen `medya-card-list`** | Bilinçli odak (#525); Notion’da «coming soon» grid yerine boşluk bırakma refleksiyle uyumlu. |

---

## SIMPLIFY — Azalt / birleştir (işlev kalır)

| Öğe | Gerekçe | Referans karşılaştırma |
|-----|---------|------------------------|
| **Mod rozeti + Ayarlar mod kartı** | Aynı Offline/Sınırlı/Tam bilgisi header ve Ayarlar’da iki kez. | Raycast: mod/ortam tek yerde (menü veya status bar), çift kontrol yok. |
| **Bağlantı rozeti + Ayarlar infra özeti** | `panel-conn-badge` ve `panel-infra-status-dl` aynı hikâyeyi anlatıyor. | Linear: connection/sync tek satır status; detay settings’e gömülü. |
| **Compose ek düğmeleri** | `+` menüsünde kamera/ses + bağımsız kamera/mikrofon ikonları — üç kanal. | ChatGPT: attach tek giriş; ses/kamera ya menüde ya dışarıda, ikisi birden değil. |
| **Modül başlık üçlüsü** | `panel-module-eyebrow` + `h2` + `panel-module-lead` her önizleme modülünde aynı ritim. | Notion: sayfa başlığı + opsiyonel tek satır açıklama; eyebrow (0.62rem uppercase) gereksiz katman. |
| **Görevler üst metinleri** | `[Yerel]` rozeti + uzun intro + `gorevler-codex-warning` aynı mesajı üç kez veriyor. | Linear: issue oluştururken uyarı yok; çalışan modül «önizleme» tonu taşımamalı. |
| **Medya modülü** | Outbox işlevsel; 5 konsept kart + demo form geri kalanı şişiriyor. | Arc: çalışan özellik önde; roadmap metni sidebar’da değil release notes’ta. |
| **Kuantum katmanları** | Banner + intro + mock + 4 konsept kartı dört katman. | Güven ürünlerinde (1Password, Raycast) sahte veri tek satır «veri yok» ile sınırlanır. |
| **Yetenekler legend + tablo** | `lumos-capability-legend` tabloyu tekrar ediyor. | Notion database: legend ayrı blok değil, sütun başlıkları yeter. |
| **Gönder CTA stili** | Altın gradient + hover teal glow; teal aksanla çift dil. | ChatGPT: gönder tek renk (filled circle/icon); secondary CTA görünümü primary aksanı böler. |
| **Aktif nav vurgusu** | Sol border + gold metin + üç katman teal box-shadow. | Linear sidebar: arka plan tint veya sol çizgi — biri yeter, ikisi değil. |

---

## REMOVE — Tamamen gitmeli

| Öğe | Gerekçe | 10 alan eşlemesi |
|-----|---------|------------------|
| **`--panel-body-wash` (4 katmanlı radial + gradyan)** | Sayfa zaten `#0a0e14`; wash içeriği gölgeler, «kontrol odası» hissi verir. Arc/Linear düz surface kullanır. | 1 Görsel ağırlık, 3 Glow, 10 Premium bozan |
| **`.panel-main` üst radial gradyan** | Body wash üstüne ikinci vurgu — derinlik yanılsaması gereksiz. | 1, 3 |
| **`.chat-history-shell` chat-wash + 48px teal inset** | Sohbet alanı neon tüp gibi; mesajlar ikinci planda. ChatGPT thread: düz `#212121` benzeri yüzey, inset glow yok. | 1, 3, 2 Boş alan (içerik nefes almıyor) |
| **`.chat-thread` 72px inset glow** | R-03 ile aynı bütçeyi ikiye katlıyor. | 3 |
| **Aktif nav teal box-shadow (6px/2px glow)** | Sekme seçimi için üç katman gölge; sol border veya hafif bg yeter (Linear). | 3, 6 Navigasyon |
| **`panel-conn-badge[data-state="ok"]` cyan glow** | «Bağlı» kutlama yapıyor; nötr metin yeter (Raycast status dot). | 7 Durum rozetleri, 10 Premium bozan |
| **`panel-user-mode-badge[data-mode="full"]` teal glow** | Mod bilgisi alarm değil; parlaması ucuz his verir. | 7 |
| **Nav/chat scrollbar teal-40/48 thumb** | Dekoratif dikkat; `--lumos-teal-22` veya nötr gri yeter. | 3 |
| **53 `medya-card` konsept kartı** | Pazarlama metni yığını; işlev yok. Notion boş sayfa > 11 modül × 5 kart broşürü. | 1, 5 Kart yapıları, 9 İlk 5 sn |
| **`panel-share-proto--demo` ×3 (Medya, Sosyal, Posta)** | Doldurulabilir form + «demo kapalı» güveni zedeler. | 9, 10 |
| **`panel-quantum-readiness-mock` varsayılan görünür** | Mock güvenlik raporu ürün gibi sunuluyor. | 9, 10 |
| **Kuantum banner’daki 4 rozet (DEMO, docs, no-live, mvp)** | Aynı «gerçek değil» mesajı dört kez. | 7 |
| **`chat-capability-card` (boş thread)** | Boş sohbette kart + 8 madde; ChatGPT’te «How can I help?» tek satır. | 2, 4 Yazı hiyerarşisi, 9 |
| **Boş thread’de 3–4 `lumos-security-note`** | Tek cümle yeter; dört dipnot hukuk metnine çeviriyor. | 4, 2 |
| **`panel-nav__lumos` ikinci sütun (9 öğe, 8 önizleme)** | Masaüstünde sol yarıyı konsept menü kaplıyor; mobilde zaten gizli. | 6 |
| **Kuantum çift giriş (primary chip + lumos nav)** | Aynı modül iki yerde. | 6 |
| **`panel-nav-collapsible` toggle’lar** | Tek grup, varsayılan açık — gereksiz tıklama (Linear flat sidebar). | 6 |
| **Nav’da ×12 `lumos-soon-badge` «Önizleme»** | Modül adı yeter; 12 mini rozet visual noise. | 6, 7 |
| **`panel-header-tagline`** | «Kontrollü çalışma alanı» header’ı kalabalıklaştırır; h1 yeter. | 4 |
| **`Mod ·` ön eki** | «Sınırlı» tek başına anlaşılır. | 4, 7 |
| **`panel-data-flow-badge` köşeli etiketler** | `[Yerel]` wiki sözdizimi; gövde metnine gömülür veya kalkar. | 4, 7 |
| **`gorevler-codex-warning`** | Çalışan Görevler modülünde «önizleme» uyarısı yanlış ton. | 4, 10 |
| **Uzun `panel-module-lead` / `medya-intro` paragrafları** | Önizleme modülünde başlık + tek cümle yeter. | 2, 4 |
| **`panel-module-eyebrow` (0.62rem uppercase)** | `h2` ile bilgi tekrarı; okunaksız. | 4 |
| **`chat-empty-hint` mavi-gri hardcode** | `rgb(210 232 252)` token dışı; nötr `--lumos-text-soft` yeter. | 4, 10 |
| **Header `border-bottom: --lumos-teal-38`** | Fazla parlak ayırıcı; `--lumos-border` yeter. | 1 |
| **Dialog `backdrop-filter: blur(2px)`** | Hafif glassmorphism izi; düz overlay (Linear modal) yeter. | 3, 10 |

---

## On analiz alanı → bucket haritası

| # | Alan | Ana teşhis | Bucket |
|---|------|------------|--------|
| 1 | **Görsel ağırlık dengesi** | Wash + kart + border + rozet aynı anda konuşuyor; içerik kayboluyor | REMOVE: body/main/chat wash, medya-card. KEEP: sohbet edge-to-edge, görev kartları |
| 2 | **Boş alan kullanımı** | Boş thread ve önizleme modülleri metin/kart ile doldurulmuş; negatif alan yok | REMOVE: capability card, security notes yığını. SIMPLIFY: modül head üçlüsü |
| 3 | **Glow ve efekt yoğunluğu** | Teal inset 48–72px, nav glow, conn neon, send hover glow — bütçe 3–4× fazla | REMOVE: chat wash/inset, nav shadow, conn ok glow. SIMPLIFY: send CTA |
| 4 | **Yazı hiyerarşisi** | 4 seviye aynı modülde (eyebrow/h2/lead/badge); 0.58–0.62rem rozetler okunmuyor | REMOVE: eyebrow, tagline, bracket badges. SIMPLIFY: görevler üst metin |
| 5 | **Kart yapıları** | `medya-card` şablonu ×11 modül = broşür grid; gerçek kartlar (görev) iyi | KEEP: görev kartları. REMOVE: 53 konsept kartı, quantum mock kartları |
| 6 | **Navigasyon netliği** | İki sütun, collapsible, çift Kuantum, 12 önizleme rozeti | REMOVE: lumos nav sütunu, collapsible, rozetler, çift kuantum. KEEP: primary 3 çalışan modül netliği |
| 7 | **Durum rozetleri** | Conn/mod/header rozetleri kutlama ve tekrar yapıyor | REMOVE: conn glow, Mod· ön eki, quantum 4'lü banner. SIMPLIFY: mod + conn tek yüzey |
| 8 | **CTA (Gönder) görünürlüğü** | Compose bar iyi konumda; CTA altın+teal çift dil ve mobilde 0.62rem’e küçülüyor | KEEP: compose yerleşimi. SIMPLIFY: tek aksan (teal filled), mobil min touch |
| 9 | **İlk 5 saniyelik algı** | «Sohbet mi, demo mu, güvenlik dokümanı mı?» — capability card + mock quantum karışıyor | REMOVE: empty state kartları, demo formlar, mock quantum. KEEP: «Lumos hazır» + input |
| 10 | **Premium hissi bozan detaylar** | Cyberpunk wash, wiki badge’ler, proto sınıf adları, hardcode mavi-gri | REMOVE: wash stack, bracket badges, codex warning. KEEP: token omurgası, LanguageSwitcher |

---

## Key question

> **Bu ekranı %20 daha kaliteli göstermek için neyi kaldırırdın?**

ChatGPT bir boş sohbette yalnızca input’a güvenir; Linear sidebar’da çalışmayan özelliği göstermez veya tek «beta» ile sınırlar. Lumos’un %20 sıçraması yeni piksel değil — **yanlış katmanların çıkarılması**. Aşağıdaki sıra, en yüksek algı kazancı / en düşük işlev riski oranına göre:

| Sıra | Kaldır | Neden (~% etki) |
|------|--------|-----------------|
| **1** | Sohbet alanı glow stack (`--panel-chat-wash` + 48px + 72px inset) | Anında «ucuz neon» algısı gider; mesajlar öne çıkar. ChatGPT parity. **~%6** |
| **2** | Body + main radial wash katmanları | Tüm panel sakinleşir; Arc/Linear düz yüzey hissi. **~%4** |
| **3** | 53 `medya-card` konsept kartı (tüm önizleme modülleri) | Prototip broşürü kesilir; çalışan modüller «ürün» olarak okunur. **~%4** |
| **4** | Boş thread `chat-capability-card` + fazla `lumos-security-note` | İlk 5 sn «sohbet uygulaması» algısı; ChatGPT empty state. **~%3** |
| **5** | `panel-nav__lumos` sütunu + nav «Önizleme» rozetleri (×12) | Sol nav nefes alır; Linear-benzeri sade sidebar. **~%2** |
| **6** | Demo paylaşım formları (`panel-share-proto--demo` ×3) | Wireframe güven kaybı gider. **~%1** |
| **7** | Kuantum mock raporu varsayılan görünür + 4 banner rozeti | «Sahte veri = ürün» algısı kesilir. **~%1** |

**Toplam ~%21** — yeni özellik, sayfa veya menü eklemeden; yalnızca mevcut ekrandan çıkarma.

### Top 3 REMOVE (özet)

1. **Sohbet glow stack** — chat-wash + çift inset; en hızlı premium kazanım.
2. **53 konsept `medya-card`** — broşür yığını; çekirdek modüller öne çıkar.
3. **Boş thread capability kartı + güvenlik notu yığını** — ChatGPT-empty-state disiplini.

---

## Referans ürün notları (aynı pattern nasıl çözülür)

| Pattern | Lumos (mevcut) | Referans |
|---------|----------------|----------|
| Boş sohbet | Hint + capability kart + 4 güvenlik notu | **ChatGPT:** tek karşılama + input; kurallar settings/help’te |
| Sidebar önizleme | 12 «Önizleme» rozeti + ikinci sütun | **Linear:** yalnızca erişilebilir özellikler; beta tek etiket |
| Primary CTA | Altın gradient gönder, hover teal glow | **ChatGPT:** filled icon/button, tek aksan |
| Arka plan | 4 katman wash + chat inset | **Arc / Raycast:** düz veya tek subtle gradient |
| Durum | Bağlı = neon cyan glow | **Raycast:** küçük dot veya nötr metin |
| Konsept içerik | 53 statik kart | **Notion:** boş state veya tek satır; roadmap ayrı kanal |

---

## Brutal audit ile ilişki

[`lumos-panel-brutal-ui-audit.md`](./lumos-panel-brutal-ui-audit.md) REMOVE ID’leri (R-01–R-32) ile örtüşür; bu belge **senior lens** ve **referans ürün karşılaştırması** ekler, sayısal ID listesini tekrarlamaz. Gelecek spec özellikleri (`lumos-panel-ui-ux-specification.md`) kapsam dışıdır.

---

*Analiz only — kod, mockup veya yeni özellik önerisi içermez.*
