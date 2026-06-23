# Lumos UI Tasarım Denetim Raporu

| Alan | Değer |
|------|-------|
| **Tarih** | 2026-06-22 |
| **Baseline** | PR #525 — `ui/src/styles/lumos-tokens.css` (landing + panel ortak tokenlar) |
| **Kapsam** | `ui/src/pages/panel.astro`, `ui/src/pages/index.astro`, `ui/src/components/**`, `lumos-tokens.css` |
| **Kod değişikliği** | Yok — yalnızca analiz |

---

## 1. Özet

PR #525 ile `#0a0e14` tabanlı premium koyu tema, kontrollü teal vurgu ve altın ikincil ton `lumos-tokens.css` üzerinden landing ve panele taşınmış durumda. Token katmanı sağlam bir omurga sunuyor; ancak her iki yüzeyde de **token dışı renkler**, **çoklu border-radius ölçeği**, **demo/önizleme modüllerinin ürün hissi** ve **mobil dokunma hedefi** sorunları kurumsal SaaS çizgisinin altında kalan alanlar üretiyor.

**Denetim kapsamı:** Panel modülleri (Sohbet, Görevler, Dosyalar, Yetenekler, Ses, Medya, Posta, Sosyal, Kuantum, Lumos çekirdeği sekmeleri), landing bölümleri (hero, modüller, dünya, kurulum), paylaşılan bileşenler (`LanguageSwitcher`, `GlobalMay19Corner`, `I18nInit`).

### Önem derecesine göre sorun sayısı

| Önem | Adet |
|------|------|
| **Yüksek** | 9 |
| **Orta** | 14 |
| **Düşük** | 8 |
| **Toplam** | **31** |

---

## 2. Metodoloji

1. **Token dosyası** (`lumos-tokens.css`) — renk, radius, spacing, gölge sözleşmesi okundu.
2. **Panel** (`panel.astro`, ~15k satır) — tüm `module-panel` bölümleri, mobil `@media` blokları (479–767px), sohbet/görevler/dosyalar CSS’i tarandı.
3. **Landing** (`index.astro`) — hero, nav, modül kartları, dünya vizyon, kurulum ve mobil düzenlemeler incelendi.
4. **Bileşenler** — `LanguageSwitcher.astro`, `GlobalMay19Corner.astro` stilleri token uyumu için kontrol edildi.
5. **Grep taramaları** — `#38`, `cyan`, `rgb(56`, token dışı hex, `border-radius`, `padding` dağınıklığı.
6. **Test referansı** — `tests/test_panel_visual_polish.py` (#525 beklentileri) doğrulama bağlamı olarak kullanıldı; bu rapor test değiştirmez.

Her bulgu yalnızca repoda mevcut ekran/bileşenlere dayanır; uydurma ekran yoktur.

---

## 3. Bulgular tablosu

Önem sırasına göre (yüksek → düşük). Tablo sütunları: ID, ekran, sorun, öneri, etki.

| ID | Ekran / bileşen | Sorun | Önerilen düzeltme | Etki |
|----|-----------------|-------|-------------------|------|
| H-01 | Landing — hero soru CTA (`.lumos-hero-ask__submit`) | Parlak mavi gradyan (`rgb(26 108 168)`, `rgb(118 198 238)`) teal token sisteminden kopuk; SaaS marka bütünlüğünü kırar | CTA’yı `--lumos-accent-primary` / `--lumos-accent-primary-deep` gradyanına veya `--lumos-hero-btn--primary` ile hizala | **Yüksek** |
| H-02 | Panel — Posta / Sosyal / Medya paylaşım (`.panel-share-proto--demo`) | `[Demo — bağlı değil]` rozeti, devre dışı «Gönder (demo kapalı)» — canlı ürün değil prototip hissi | Tek tip «Önizleme modu» empty-state; form yerine salt okunur özet + «yakında» CTA; demo rozeti üst banner’da bir kez | **Yüksek** |
| H-03 | Panel — Kuantum (`#panel-kuantum`, `.panel-quantum-readiness-mock`) | `DEMO` banner + «Örnek hazırlık özeti (mock)» + `docs_only` kanıt — güven ürünü gibi görünüp doğrulanmamış veri sunuyor | Mock’u varsayılan gizle; API yoksa sadeleştirilmiş «veri yok» durumu; canlı tarama gelince progressive disclosure | **Yüksek** |
| H-04 | Panel — mobil üst nav (`.panel-nav__primary button`, `.panel-conn-badge`) | Sekme `font-size: 0.58rem`, rozet `0.4rem`, `min-height: 1.24rem` — WCAG 2.5.5 (44×44px) altında | Min 44px dokunma hedefi; kısa etiket + ikon veya bottom sheet modül seçici | **Yüksek** |
| H-05 | Panel — mobil Lumos çekirdeği (`nav.panel-nav__lumos { display: none }`) | Yayıncılık, YZ, Entegrasyon, Kimlik, Yetenekler, Güvenlik, Dünya, Ayarlar mobilde gizli; yalnızca Kuantum chip | Çekirdek modüller için «Daha fazla» menüsü veya ikinci satır scroll; Yetenekler/Ayarlar erişilebilir kalmalı | **Yüksek** |
| H-06 | Landing — kurulum dipnotları (`.lumos-install-copy-disclaimer`, `.lumos-install-step-note`) | Metin rengi `rgb(var(--lumos-land-teal-deep) / 0.48–0.5)` — `#0a0e14` üzerinde ~3:1 kontrast, küçük puntoda okunaksız | `--lumos-text-soft` veya min 4.5:1 kontrastlı `--lumos-muted` türevi; 12px altı kullanma | **Yüksek** |
| H-07 | Panel — Sohbet geçmişi (`.chat-history-shell`, `.chat-thread`) | İç gölge + wash: `inset 0 1px 48px teal-deep / 0.22`, `inset 0 0 72px` — neon/cyan «kontrol odası» aşırı parlaması | Wash opaklığını %40–50 azalt; tek radial highlight; scrollbar thumb’u `--lumos-teal-22` ile sınırla | **Yüksek** |
| H-08 | Panel — önizleme modülleri (Ses, Medya, Yayıncılık, YZ, …) | Beşli `medya-card-list` konsept kartları — işlevsel UI yok, pazarlama metni yığını | `panel-module-state` şablonu + 1 özet kart; geri kalanı «yol haritası» linkine taşı | **Yüksek** |
| H-09 | Panel — viewport (`maximum-scale=1, user-scalable=no`) | Zoom kapatılmış — erişilebilirlik ve kurumsal uyumluluk riski | `user-scalable=yes` veya kaldır; iOS zoom zaten `font-size: max(16px)` ile yönetiliyor | **Yüksek** |
| M-01 | Landing + Panel — border-radius | Token: 8/10/12px; saha: 4, 5, 6, 14, 16px, `0.45rem`, `0.7rem`, `999px` karışık | Yalnızca `--lumos-radius-sm|md|lg` + `pill: 999px` + chat-tail `5px` istisnası dokümante et | **Orta** |
| M-02 | Panel — spacing | `--panel-space-section/block` tanımlı ama kartlarda 0.45–1.15rem arası ~12 farklı padding | 4px grid: `space-1` (4px) … `space-5` (20px) tokenları; kart içi tek değer (`--panel-space-block`) | **Orta** |
| M-03 | Panel — kart arka planları | `rgba(4, 8, 16, 0.92)` / `rgba(6, 10, 20, 0.92)` tekrarlı hardcode — `--lumos-surface` ile uyumsuz ton | `--lumos-surface` veya `--panel-surface-raised` tek kaynak | **Orta** |
| M-04 | Panel — aktif nav (`.panel-nav button[aria-current="true"]`) | Sağa `6px 0 22px` teal glow — parlak cyan kenar vurgusu | Altın sol border + düz `background: var(--lumos-surface-raised)`; glow kaldır veya `--lumos-teal-12` | **Orta** |
| M-05 | Landing — modül ikonları (`.lumos-scope-card__icon`) | Üç katmanlı `drop-shadow` + `0 0 36px teal` — «neon/cyan» yorumu kodda açık | Tek `drop-shadow`; hover’da hafif `translateY`; `--lumos-teal-18` üst sınır | **Orta** |
| M-06 | Landing — dünya vizyon kartı (`.lumos-dunya-hero__vizyon-card`) | `border-radius: 16px`, çoklu dış glow (`0 0 32px`, `0 0 60px` teal), hardcode gradyan `#01040d` | `--lumos-radius-lg` (12px) veya yeni `--lumos-radius-xl: 16px` token; glow tek katman | **Orta** |
| M-07 | Landing — roadmap link (`.lumos-roadmap-inline a`) | `rgb(120 228 255 / 0.92)` — token dışı parlak sky-blue | `--lumos-interactive-fg` / `--lumos-interactive-fg-hover` | **Orta** |
| M-08 | Panel — form odak (`.gorevler-field:focus` vs chat compose) | Görevler/dosyalar altın odak; sohbet teal — çift accent sistemi | Tek «focus ring» tokenı: `--lumos-focus-ring` (teal veya altın, biri seçilmeli) | **Orta** |
| M-09 | Panel — Yetenekler (`.lumos-capability-list`) | Ham grid: isim + `AKTİF`/`GELİŞTİRME AŞAMASINDA` — iç araç tablosu estetiği | Durum pill + ikon; monospace route gizle (prod); tablo satır yüksekliği ve hover | **Orta** |
| M-10 | Panel — bağlantı rozeti OK (`.panel-conn-badge[data-state="ok"]`) | `rgb(196 234 255)` metin + teal glow — bağlı durumda bile neon | `--lumos-text-soft` metin; border `--lumos-teal-28`; glow kaldır | **Orta** |
| M-11 | Panel — sohbet boş durum (`.chat-empty-hint__text`) | `rgb(210 232 252 / 0.92)` — sohbet alanında mavi-beyaz, bubble’lardan farklı palet | `var(--lumos-text)` veya `--lumos-heading-warm` | **Orta** |
| M-12 | `GlobalMay19Corner.astro` | `#0a0a0a`, `#f2ebe0`, `rgba(93, 201, 197)` — `lumos-tokens` dışı; panel/landing ile görsel kopukluk | Token import; `--lumos-surface`, `--lumos-heading-warm`, `--lumos-teal-38` outline | **Orta** |
| M-13 | Panel — mobil modül paneli | `@media (max-width: 767.98px)` — `.module-panel` `border-radius: 0`, padding sıfırlanmış; masaüstü kart çerçevesi kayboluyor | Mobilde yatay `padding-inline: var(--panel-space-block)` koru; üst köşe radius tutarlılığı | **Orta** |
| M-14 | Landing — hero başlık gradyanı (`@supports background-clip`) | `#9eb4d4` ara ton — soğuk mavi-gri; teal-altın marka ekseni dışı | Gradyanı `--lumos-land-title` → `--lumos-heading-warm` eksenine çek | **Orta** |
| D-01 | `LanguageSwitcher` — aktif pill | `color: #0a0e14` hardcode (token’da `--lumos-bg` ile aynı ama ad hoc) | `color: var(--lumos-bg)` | **Düşük** |
| D-02 | Panel — `.lumos-mark` | `#0c1428`, `#080f1e`, `#030714` gradyan — token yüzeylerinden ayrı | `--lumos-surface-raised` → `--lumos-bg` gradyan | **Düşük** |
| D-03 | Panel — başlık renkleri | `#e9eef5`, `#f2efe6` tekrar — `--lumos-text` yerine | `var(--lumos-text)` / `var(--lumos-heading-warm)` | **Düşük** |
| D-04 | Panel — `.lumos-soon-badge` | `border-radius: 4px` — `--lumos-radius-sm` (8px) altı | `border-radius: var(--lumos-radius-sm)` veya pill | **Düşük** |
| D-05 | Panel — Dosyalar `#dosyalar-file-input` | Native file input — marka dışı görünüm | Özel «Dosya seç» butonu + gizli input pattern | **Düşük** |
| D-06 | Panel — chat bubble kuyruk (`5px`) | `--panel-radius-lg` (12px) ile kasıtlı uyumsuzluk | Chat istisnasını tokenla: `--lumos-chat-tail: 5px` | **Düşük** |
| D-07 | Medya modülü — inline style | `style="margin-top: 1rem"` paylaşım proto üzerinde | Utility class: `margin-top: var(--panel-space-section)` | **Düşük** |
| D-08 | Panel — scrollbar thumb | `--lumos-teal-40` / `48` — navigasyon dışında dikkat çekici | `--lumos-teal-28` varsayılan; hover’da `32` | **Düşük** |

---

## 4. Kriter bazlı bölümler

### 4.1 Prototip hissi veren alanlar

| ID | Detay |
|----|-------|
| H-02 | `panel-share-proto--demo`, `panel-data-flow-badge--demo`, devre dışı gönder butonları — `panel.astro` ~5055–5182 |
| H-03 | `panel-quantum-readiness-mock`, `data-quantum-readiness-mock="true"` — ~5332–5386 |
| H-08 | Ses/Medya/Yayıncılık/YZ/Entegrasyon/Kimlik/Dünya/Güvenlik/Ayarlar: `medya-card-list` konsept kartları, işlev yok |
| M-09 | `lumos-capability-list` ham durum metinleri — iç panel/debug hissi |
| D-07 | Inline `style` — bakım ve tasarım sistemi dışı |

**Neden sorun:** Kurumsal SaaS’ta kullanıcı «çalışan ürün» veya «net yol haritası» bekler; demo form + kapatılmış buton + mock veri tablosu üçlüsü «yarım wireframe» algısı yaratır.

### 4.2 Tutarsız spacing

| ID | Detay |
|----|-------|
| M-02 | Token `--panel-space-section: 1.25rem`, `--panel-space-block: 0.85rem` vs kart `padding: 0.92rem 1.05rem`, `0.65rem 0.85rem`, mobil header `0.08rem 0.24rem` |
| M-13 | Mobil modül panelinde padding `0.45rem 0` — yatay nefes alanı kaybı |
| D-07 | Inline margin token zincirini bypass eder |

**Neden sorun:** Ritim kırıldığında modüller aynı uygulamanın parçası gibi hissettirmez; göz hizası ve kart yoğunluğu ekranlar arası zıplar.

### 4.3 Tutarsız border-radius

| ID | Detay |
|----|-------|
| M-01 | `lumos-tokens.css` 8px grid vs `index.astro` 14px/16px kartlar, `panel.astro` 4px/5px/6px rozetler |
| M-06 | Dünya vizyon `16px` — token üstü |
| D-04 | `lumos-soon-badge` 4px |
| D-06 | Chat bubble 5px kuyruk — belgelenmemiş istisna |

**Neden sorun:** Köşe dili ürün «ciddiyetini» taşır; karışık radius değerleri wireframe birleştirme izlenimi verir.

### 4.4 Fazla parlak cyan kullanımı

| ID | Detay |
|----|-------|
| H-01 | Hero mavi CTA — `index.astro` ~346–385 |
| H-07 | Chat history wash — `panel.astro` ~2083–2102 |
| M-04 | Aktif nav teal glow — ~780–783 |
| M-05 | Scope ikon drop-shadow — `index.astro` ~1533–1551 |
| M-06 | Vizyon kart dış glow — ~845–847 |
| M-07 | Roadmap sky-blue link — ~1651 |
| M-10 | Conn badge OK metin rengi — `panel.astro` ~127 |
| D-08 | Scrollbar doygun teal thumb |

**Neden sorun:** PR #525 «controlled teal» hedefliyor; `#5eead4`, sky-blue ve çok katmanlı glow eski «elektrik cyan» yönüne geri çeker.

### 4.5 Düşük kontrastlı metinler

| ID | Detay |
|----|-------|
| H-06 | Kurulum dipnotları `/ 0.48–0.52` opaklık |
| M-11 | Chat empty hint mavi-gri |
| — | `.panel-header-tagline` `rgba(168, 188, 210, 0.72)` — `panel.astro` ~568 |
| — | `.panel-module-state__note` `rgba(156, 152, 146, 0.92)` — ~966 |
| — | `.gorevler-list-empty` `rgba(180, 176, 168, 0.92)` — ~1405 |
| — | `var(--lumos-muted)` (#64748b) yoğun kullanım — nav pasif, kart gövde |

**Neden sorun:** WCAG AA (4.5:1 normal metin) kurumsal satın alma ve erişilebilirlik denetimlerinde sık kontrol edilir; «muted» ile «disabled» ayrımı bulanıklaşır.

### 4.6 Kurumsal / SaaS kalitesinin altında kalan ekranlar

| ID | Detay |
|----|-------|
| H-02, H-03, H-08 | Önizleme ve demo yüzeyleri |
| M-09 | Yetenekler durum tablosu |
| M-08 | Çift focus accent |
| H-05 | Mobilde çekirdek modül erişimi |
| H-09 | Zoom kilidi |
| — | Tek dosyada 15k+ satır panel — tasarım borcu (tutarlılık riski, #525 sonrası regresyon) |

**Neden sorun:** Enterprise alıcı «bitmiş kontrol paneli» arar; konsept kartı yığını ve mock güvenlik raporu güvenilirlik algısını zedeler.

### 4.7 Mobil görünüm sorunları

| ID | Detay |
|----|-------|
| H-04 | Küçük nav ve rozet tipografi |
| H-05 | Gizli Lumos çekirdeği nav |
| M-13 | Modül kart çerçevesinin mobilde düzleşmesi |
| H-09 | `user-scalable=no` |
| — | `.panel-header-brand { padding-right: 2.72rem }` — rozetlerle başlık çakışma riski, dar ekranda — `panel.astro` ~3341 |
| — | Yatay scroll nav (`overflow-x: auto`) — scroll ipucu zayıf; `panel-nav-research-chip` tek görünür çekirdek kısayolu |
| — | Landing nav `lumos-site-nav__list--scroll-hint` mask fade var; panel nav’de eşdeğer yok |

**Neden sorun:** Panel mobil-first iş akışı (sohbet, görev) için dokunma ve keşif kritik; gizli modül menüsü ve küçük hedefler operasyonel sürtünme yaratır.

---

## 5. Modül bazlı özet

### Sohbet (Chat)
- **Güçlü:** Bubble yapısı, compose bar token uyumu, iOS 16px font kuralı.
- **Zayıf:** History wash/glow (H-07), empty hint rengi (M-11), chat-tail radius belgelenmemiş (D-06).

### Görevler
- **Güçlü:** Kart hiyerarşisi, badge durum renkleri, detail dialog shell.
- **Zayıf:** Altın odak halkası chat’ten ayrı (M-08); `gorevler-proto` sınıf adı prototip çağrışımı.

### Dosyalar
- **Güçlü:** Sonuç kartları `--panel-radius-lg` ile hizalı.
- **Zayıf:** Native file input (D-05); history meta `var(--lumos-muted)` yoğun.

### Posta / Sosyal / Medya (paylaşım)
- **Güçlü:** Genişletilmiş textarea (rows 6/8), `#panel-sosyal/posta .medya-card-list { display: none }` ile odak taslağa kaydırılmış (#525).
- **Zayıf:** Demo proto formlar (H-02); Medya’da hem outbox hem kart listesi hem proto — bilgi mimarisi kalabalık.

### Kuantum
- **Güçlü:** DEMO şeffaflığı metinde açık; tablo yapısı canlı veri için hazır.
- **Zayıf:** Mock varsayılan görünür (H-03); banner + mock + konsept kartları üç katman.

### Landing
- **Güçlü:** `lumos-tokens.css` import; sticky nav; modül kart grid responsive.
- **Zayıf:** Mavi hero CTA (H-01); scope ikon neon (M-05); kurulum kontrast (H-06); hero başlık gradyanı (M-14).

### Nav / Header (Panel)
- **Güçlü:** Conn badge durum makinesi; user mode badge; tagline eklendi (#525).
- **Zayıf:** Mobil tipografi (H-04); aktif glow (M-04); çekirdek nav gizleme (H-05).

### Yetenekler (Skills)
- Aktif modül; «Beceri» adıyla değil `yetenekler` — capability matrix iç araç görünümü (M-09).

### Ses / Yayıncılık / YZ / Entegrasyon / Kimlik / Dünya / Güvenlik / Ayarlar
- Önizleme (`inactiveBadge`); konsept `medya-card-list` — H-08 kapsamında.

---

## 6. Mobil özet

| Alan | Durum | Referans |
|------|-------|----------|
| Panel layout | Flex kolon, sohbet `min-height: 0` zinciri — iyi | `panel.astro` ~3186–3427 |
| Safe area | `env(safe-area-inset-*)` uygulanmış | ~3177–3180 |
| iOS zoom | `max(16px, 1em)` form/button — iyi | ~3147–3158 |
| Nav erişimi | Lumos çekirdeği gizli — **kritik** | H-05 |
| Touch target | Rozet/sekme < 44px — **kritik** | H-04 |
| Modül çerçevesi | `border-radius: 0` — düz ekran | M-13 |
| Landing | Nav scroll-hint, hero clamp — kabul edilebilir | `index.astro` ~1975–2169 |
| Zoom | `user-scalable=no` — **kritik** | `panel.astro` ~41 |

---

## 7. Öncelikli düzeltme listesi (gelecek PR — şimdi uygulanmaz)

### P0 — Marka güveni ve mobil kullanılabilirlik

1. **H-01:** Landing hero «Sor» CTA’sını `lumos-tokens` teal/altın sistemine taşı; mavi gradyanı kaldır.
2. **H-04 + H-05:** Panel mobil nav — min 44px hedef, Lumos çekirdeği modülleri için «Daha fazla» erişimi; rozet font min ~11px (0.6875rem).
3. **H-02 + H-03:** Demo/mock yüzeylerde birleşik «Önizleme modu» bileşeni; Kuantum mock varsayılan kapalı.

### P1 — Görsel tutarlılık

4. **H-07 + M-04 + M-05:** Cyan glow budget — chat wash, aktif nav ve scope ikonlarında tek katman, düşük opaklık.
5. **M-01 + M-02 + M-03:** Radius ve spacing token enforce; kart arka planlarını `--lumos-surface` türevine kilitle.
6. **H-06 + M-11:** Metin kontrastı — muted türevleri min 4.5:1 doğrula (özellikle 12px altı).

### P2 — İyileştirme

7. **M-09:** Yetenekler tablosunu enterprise durum bileşenine yükselt.
8. **M-12:** GlobalMay19Corner token hizası.
9. **D-05:** Dosyalar özel file picker.
10. **H-09:** Viewport zoom kısıtını gevşet.

---

## 8. İyi örnekler (PR #525 sonrası çalışanlar)

1. **Ortak token dosyası** — `lumos-tokens.css` landing ve panelde import; `--lumos-bg`, `--lumos-land-teal`, `--panel-radius-*` tek kaynak.
2. **Modül başlık IA** — `.panel-module-head`, `.panel-module-eyebrow`, `.panel-module-lead` ile önizleme modüllerinde tutarlı hiyerarşi (`panel.astro` ~819–862).
3. **Posta/Sosyal odak** — Bilgi kartları gizlenip taslak alanı öne alınmış (`#panel-sosyal .medya-card-list { display: none }`) — bilinçli UX kararı.
4. **LanguageSwitcher** — Token border/background; aktif pill `--lumos-accent-primary` — kompakt ve markaya yakın.
5. **Görev kartları** — `--lumos-card-border`, `--panel-edge-inset`, hover/focus altın border — premium kart dili.
6. **Panel body wash** — `--panel-body-wash` kontrollü teal/altın; header `--panel-strip-bg` ile uyumlu.
7. **Landing hero butonları** — `.lumos-hero-btn--primary/ghost` teal token kullanımı (CTA hariç tutarlı).
8. **iOS form zoom önleme** — Panel ve landing’de `max(16px, 1em)` — mobil UX disiplini.
9. **Test güvencesi** — `test_panel_visual_polish.py` premium dark marker’ları — regresyon ağı.

---

## Ek: Dosya referans özeti

| Dosya | Rol |
|-------|-----|
| `ui/src/styles/lumos-tokens.css` | Tasarım sistemi omurgası |
| `ui/src/pages/panel.astro` | Panel shell + tüm modül UI/CSS |
| `ui/src/pages/index.astro` | Landing |
| `ui/src/components/LanguageSwitcher.astro` | TR/EN kontrol |
| `ui/src/components/GlobalMay19Corner.astro` | Tarihsel köşe widget (token dışı) |
| `tests/test_panel_visual_polish.py` | #525 görsel beklenti testleri |

---

*Bu belge yalnızca analiz amaçlıdır; kod veya PR içermez.*
