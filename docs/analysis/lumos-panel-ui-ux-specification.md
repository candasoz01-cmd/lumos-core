# Lumos Panel — UI/UX Ürün ve Tasarım Spesifikasyonu

| Alan | Değer |
|------|-------|
| **Sürüm** | 1.0-draft |
| **Durum** | Taslak — uygulama bekliyor |
| **Tarih** | 2026-06-22 |
| **Hedef kitle** | Cursor ajanları, UI geliştiriciler, ürün/tasarım karar vericileri |
| **Kapsam** | Lumos Panel (`ui/src/pages/panel.astro`) shell, navigasyon, sohbet, tema ve ortak bileşen dili |
| **Kod değişikliği** | Bu belge yalnızca spesifikasyondur; implementasyon ayrı PR’larda yapılır |

### İlgili belgeler

| Belge | İlişki |
|-------|--------|
| [`ui-design-audit-report.md`](./ui-design-audit-report.md) | Mevcut durum bulguları, gap tablosu kaynağı |
| [`lumos-design-language-proposals.md`](./lumos-design-language-proposals.md) | Tema yönü araştırması; bu spec **soğuk nötr açık** + mevcut koyu token hattını birleştirir |
| [`ui/src/styles/lumos-tokens.css`](../../ui/src/styles/lumos-tokens.css) | PR #525 koyu tema omurgası — genişletilecek |
| [`lumos-privacy-manifesto-draft.md`](./lumos-privacy-manifesto-draft.md) | Ton: güven, şeffaflık, manipülasyon yok — UI güven sinyalleriyle uyumlu |
| [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) | Onay, kalıcı silme, yetki — panel UX’i bu sözleşmeyi görselleştirir |

**Not (belge çelişkisi):** `lumos-design-language-proposals.md` yönetici önerisi olarak Tema 2 (sıcak açık / Notion) önerir. Bu spesifikasyon, kullanıcı mandate’i ve north star (“kurumsal kalite + modern teknoloji”) doğrultusunda **soğuk nötr açık tema** token’larını (OpenAI / Linear / Notion karışımı) tanımlar. Sıcak açık alternatif, [Açık kararlar](#11-açık-kararlar) bölümünde tutulur.

---

## 1. Belge meta

Bu belge, dağınık tasarım notlarını **tek kaynak** halinde birleştirir. Amaç: Cursor ve ekip için uygulanabilir, ölçülebilir ve fazlara bölünmüş bir panel UI/UX sözleşmesi sunmak.

**Sınıflandırma etiketleri (belge boyunca):**

| Etiket | Anlam |
|--------|-------|
| **🆕 YENİ** | Bugün repoda yok; yeni rota, panel veya etkileşim gerektirir |
| **✨ CİLA** | Mevcut yüzeyin görsel/UX iyileştirmesi; davranış çoğunlukla aynı kalır |
| **📋 MEVCUT** | Repoda var; spec ile hizalanacak veya korunacak |

---

## 2. Tasarım hedefi ve north star

### North star

> **Kurumsal kalite ile modern teknoloji ürünü arasında dengeli, sade ve güven veren arayüz.**

Panel bir «gece operasyon merkezi» veya «cyberpunk kontrol odası» değil; kullanıcının işine odaklandığı, Lumos’un güven ve onay modelini görselleştiren **profesyonel bir çalışma alanıdır**.

### Tasarım hedefleri (öncelik sırasıyla)

1. **Minimal** — Gereksiz çerçeve, kutu ve dekorasyon yok.
2. **Profesyonel** — Enterprise SaaS çizgisi; prototip/demo hissi minimize.
3. **Modern ve teknolojik** — Güncel referans ürünlerle (ChatGPT, Linear) uyumlu; abartılı futurizm yok.
4. **Yorgunluk düşük** — Uzun oturumlarda gözü yormayan kontrast ve glow bütçesi.
5. **Kalite ve güven > gösteriş** — Parlama, neon ve animasyon güven sinyali taşımaz; içerik ve durum netliği taşır.

### Duygusal ton (gizlilik manifestosu ile uyum)

- Güven **manipülasyonla** değil **şeffaflık ve okunabilirlikle** kurulur.
- «Önizleme» ve «henüz aktif değil» modüller kullanıcıyı cezalandırmaz; sakin, dürüst dil.
- Durum rozetleri (bağlantı, mod, onay) bilgi verir; alarm estetiği üretmez.

---

## 3. Genel ilkeler

### 3.1 Bilgi önceliği

| İlke | Uygulama |
|------|----------|
| İçerik önce | UI chrome (border, glow, gradyan) içeriği gölgelemez |
| Tek kartta topla | Dağınık mini-kutular yerine anlamlı gruplar tek yüzeyde |
| Her öğenin amacı var | Dekoratif çerçeve, boş divider, anlamsız badge yok |
| UI dikkat dağıtmaz | Aktif görev (sohbet, görev, dosya) alanı görsel olarak baskın |

### 3.2 Görsel disiplin

| Yap | Yapma |
|-----|-------|
| Kontrollü teal yalnızca birincil accent ve aktif durum | Cyberpunk, aşırı neon, çok katmanlı cyan glow |
| Tek focus ring token’ı (tüm form ve nav) | Sohbette teal, görevlerde altın gibi çift accent |
| 4px grid spacing; token dışı padding yok | 12+ farklı kart padding değeri |
| `--lumos-radius-sm|md|lg` + pill `999px` | 4px, 5px, 6px, 14px, 16px dağınık radius |
| Glow yalnızca: aktif sekme, odaklı input, kritik durum | Genel arka plan wash, bağlı rozet, scope ikonu glow |
| Lucide ikonlar — tutarlı 18–20px stroke | Emoji veya karışık ikon seti |

### 3.3 Ölçülebilir kabul kriterleri

| Kriter | Hedef |
|--------|-------|
| Normal metin kontrastı | WCAG AA ≥ 4.5:1 (`--lumos-text` / `--lumos-bg` veya `--lumos-panel`) |
| İkincil metin | ≥ 4.5:1 tercih; kritik bilgi caption’da tek başına bırakılmaz |
| Dokunma hedefi (mobil) | Min **44×44 CSS px** tüm interaktif nav, rozet, tema düğmesi |
| Glow katmanı (koyu tema) | Aktif nav ve chat wash: **en fazla 1** dış/ iç vurgu katmanı |
| Border sayısı (sohbet mesaj satırı) | Bubble + container: **≤ 2** görünür kenar; iç içe kutu derinliği ≤ 1 |
| Animasyon | `prefers-reduced-motion` destekli; dekoratif animasyon yok |

---

## 4. Bilgi mimarisi

### 4.1 Shell düzeni (hedef)

```
┌─────────────────────────────────────────────────────────────┐
│ Header: marka · durum rozetleri · tema · dil                │
├──────────┬──────────────────────────────┬───────────────────┤
│ Sol nav  │ Ana içerik (modül paneli)    │ 🆕 Geçmiş paneli  │
│ (primary)│                              │ (sohbet modunda)  │
│          │                              │                   │
│ ──────── │                              │                   │
│ Alt menü │                              │                   │
│ Geçmiş   │                              │                   │
│ Ayarlar  │                              │                   │
│ Yardım   │                              │                   │
└──────────┴──────────────────────────────┴───────────────────┘
```

Mobil dar ekranda: sol nav ikon şeridi; geçmiş paneli overlay veya tam genişlik sheet.

### 4.2 Birincil navigasyon (sol — hedef liste)

**📋 MEVCUT modüller korunur; IA sadeleştirilir.**

| Sıra | Modül | `data-module` | Durum (2026-06) | Not |
|------|-------|---------------|-----------------|-----|
| 1 | Sohbet | `sohbet` | Aktif | Varsayılan modül |
| 2 | Görevler | `gorevler` | Aktif | |
| 3 | Ses | `ses` | Önizleme | RB-17 inactive |
| 4 | Medya | `medya` | Önizleme | |
| 5 | Sosyal | `sosyal` | Önizleme | |
| 6 | Posta | `posta` | Önizleme | |
| 7 | Dosyalar | `dosyalar` | Aktif | |
| 8 | Kuantum | `kuantum` | Önizleme | Tek giriş; çekirdek nav tekrarı kaldırılır |

**Hedefte kaldırılan / taşınan (birincil nav dışı):**

| Öğe | Mevcut konum | Hedef |
|-----|--------------|-------|
| «Çalışma» grup başlığı | `panel-nav__primary` collapsible | ✨ Kaldır veya görsel olarak sadeleştir — düz liste |
| «Lumos çekirdeği» grubu | `panel-nav__lumos` (Yayıncılık, YZ, Entegrasyon, Kimlik, Yetenekler, Güvenlik, Dünya, Ayarlar) | Modül panelleri kodda kalabilir; **birincil nav’da gösterilmez**. Yetenekler/Ayarlar erişimi alt menü veya Ayarlar altına |
| Kuantum (çift) | Hem primary chip hem lumos nav | Tek Kuantum girişi — primary’de |
| Ayarlar modülü | Lumos çekirdeği nav, önizleme | **🆕** Alt menü → Ayarlar |

### 4.3 Alt menü (sol alt) — 🆕 YENİ

| Öğe | Amaç | Davranış |
|-----|------|----------|
| **Geçmiş** | Sohbet oturum listesi | Geçmiş yan panelini aç/kapat; Sohbet dışında da erişilebilir (son görüşmeler) |
| **Ayarlar** | Kullanıcı ve panel tercihleri | Mevcut `#panel-ayarlar` içeriğine veya sadeleştirilmiş ayarlar shell’ine yönlendirir; tema tercihi burada da tekrarlanabilir |
| **Yardım** | Dokümantasyon, kısayollar, destek | Harici docs linki veya in-panel yardım özeti; üretim URL’leri public boundary’e uygun placeholder |

Alt menü birincil modül nav’ından **görsel olarak ayrılır** (ince üst border veya `margin-top: auto`); üç öğe her zaman görünür.

### 4.4 Modül haritası (içerik alanı)

| Modül | Panel ID | İçerik türü |
|-------|----------|-------------|
| Sohbet | `#panel-sohbet` | Chat thread + compose |
| Görevler | `#panel-gorevler` | Liste, kart, detay |
| Ses / Medya / Sosyal / Posta | `#panel-*` | Önizleme → hedefte `panel-module-state` şablonu |
| Dosyalar | `#panel-dosyalar` | Yükleme, geçmiş |
| Kuantum | `#panel-kuantum` | Readiness; mock varsayılan gizli (audit H-03) |
| Lumos çekirdeği modülleri | `#panel-yayincilik` vb. | Deep link / ayarlar altı; birincil nav dışı |

---

## 5. Bileşen spesifikasyonları

### 5.1 Sol navigasyon

**✨ CİLA + 🆕 ikonlar**

| Özellik | Spesifikasyon |
|---------|---------------|
| Genişlik (masaüstü) | 13.5–15rem; dar modda 3.5rem ikon şeridi |
| Öğe yüksekliği | Min 40px (masaüstü), **44px (mobil)** |
| Aktif durum | `aria-current="true"`; sol 2px `--lumos-accent-primary` border; arka plan `--lumos-surface-raised`; **glow yok** veya `--lumos-teal-12` tek wash |
| Pasif | `--lumos-text-soft`; hover: `--lumos-surface` |
| Önizleme modülü | «Önizleme» pill — nötr outline; semantic success/error **kullanılmaz** (design language RB-17) |
| İkon + etiket | Lucide 18px; etiket `--panel-font-body` |

#### Lucide ikon eşlemesi (önerilen)

| Modül | Lucide ikon | Not |
|-------|-------------|-----|
| Sohbet | `MessageSquare` | |
| Görevler | `ListTodo` veya `CheckSquare` | |
| Ses | `Mic` | Önizleme |
| Medya | `Image` veya `Film` | Önizleme |
| Sosyal | `Share2` | Önizleme |
| Posta | `Mail` | Önizleme |
| Dosyalar | `FolderOpen` | |
| Kuantum | `Atom` veya `Shield` | Research chip stili kaldırılır — normal nav öğesi |
| Geçmiş (alt) | `History` | 🆕 |
| Ayarlar (alt) | `Settings` | 🆕 |
| Yardım (alt) | `CircleHelp` | 🆕 |

**Mevcut gap:** Nav yalnızca metin etiketi kullanıyor; ikon yok (`panel.astro` ~4369–4397).

### 5.2 Alt menü (Geçmiş, Ayarlar, Yardım) — 🆕 YENİ

| Durum | Görünüm |
|-------|---------|
| Varsayılan | Üç düğme, birincil nav ile aynı tipografi; daha küçük ikon (16px) kabul edilir |
| Aktif (Geçmiş panel açık) | Geçmiş öğesi aktif nav stili |
| Hover / focus | Birincil nav ile aynı focus ring |
| Dar nav | Yalnızca ikon + `title` / tooltip |

### 5.3 Sohbet geçmişi paneli — 🆕 YENİ

**Not:** Repoda `chat-history-shell` yalnızca **aktif sohbet mesaj thread’i**dir; oturum listesi yok.

| Özellik | Spesifikasyon |
|---------|---------------|
| Konum | Sağ yan panel veya sol nav’dan açılan overlay; genişlik 16–20rem |
| Tetikleyici | Alt menü «Geçmiş» veya Sohbet modülü içi «Geçmiş» kısayolu |
| Gruplar | **Bugün** · **Dün** · **Geçen hafta** · (daha eski: ay veya «Daha eski») |
| Liste öğesi | Başlık (ilk kullanıcı mesajından veya otomatik özet), saat, isteğe bağlı mod ikonu |
| Aktif oturum | Vurgulu arka plan; silme/taşıma **onaylı** (karar sözleşmesi) |
| Boş durum | «Henüz kayıtlı sohbet yok» + kısa açıklama; dekoratif illüstrasyon yok |
| Yükleme | Skeleton 3 satır; shimmer animasyonu yok |
| Kapalı | Panel tamamen DOM’dan gizlenebilir veya `hidden`; ana sohbet genişler |

**Örnek liste (placeholder içerik — UI mock):**

```
Bugün
  · Görev planı taslağı          14:32
  · Dosya yükleme hatası         11:05
Dün
  · Lumos yetenekleri özeti      18:40
Geçen hafta
  · Haftalık görev özeti         Sal
```

**i18n:** Grup başlıkları `data-i18n` ile TR/EN; göreli tarih formatı locale’e bağlı (bkz. [Açık kararlar](#11-açık-kararlar)).

### 5.4 Tema sistemi — 🆕 YENİ

| Özellik | Spesifikasyon |
|---------|---------------|
| Konum | Header sağ üst — `LanguageSwitcher` yanında |
| Seçenekler | **Açık** · **Koyu** · **Sistem** (varsayılan **Sistem**) |
| UI | Segmented control veya ikon düğmesi + dropdown; seçim `localStorage` + `prefers-color-scheme` |
| DOM | `data-theme="light|dark"` veya `.lumos-theme-light` / `.lumos-theme-dark` on `<html>` |
| `theme-color` meta | Seçime göre güncellenir |
| Geçiş | `color-scheme` CSS; animasyon ≤ 150ms veya `prefers-reduced-motion`’da anlık |

**Mevcut gap:** Yalnızca koyu tema; `theme-color` sabit `#0a0e14` (`panel.astro` ~47).

### 5.5 Durum rozetleri — ✨ CİLA

#### Kullanıcı modu rozeti (`panel-user-mode-badge`)

| Mevcut metin | Hedef metin | Stil |
|--------------|-------------|------|
| `Mod · Sınırlı` | **Sınırlı** | Minimal pill; uppercase kaldırılır veya sentence case |
| `Mod · Offline` | **Çevrimdışı** | Nötr dot + metin alternatifi kabul |
| `Mod · Tam` | **Tam** | Teal accent yalnızca border; glow kaldır |

#### Bağlantı rozeti (`panel-conn-badge`)

| `data-state` | Hedef metin (TR) | Stil |
|--------------|------------------|------|
| `pending` | Bağlanıyor | Uyarı tonu; glow yok |
| `ok` | Bağlı | `--lumos-text-soft` metin; glow **kaldır** (audit M-10) |
| `bad` | Bağlantı yok | Hata semantic |
| `limited` | Sınırlı | Altın nötr; «MOD-SINIRLI» gibi teknik kod yok |

**Genel rozet kuralları:** `font-size` min 11px (0.6875rem); `padding` ile **44px** dokunma yüksekliği; `letter-spacing` normale yakın; pill `border-radius: 999px`.

### 5.6 Mesaj alanı ve compose — ✨ CİLA

| Alan | Hedef |
|------|-------|
| Thread arka planı | Düz `--lumos-chat-history-bg`; inset teal wash **%40–50 azalt** veya kaldır (audit H-07) |
| Bubble | Tek border veya border yok + yüzey farkı; kuyruk `--lumos-chat-tail: 5px` token |
| Capability kartı | Tek kart; iç bölümler border’sız spacing ile ayrılır |
| Güvenlik notları | `--lumos-text-soft`; mavi-gri hardcode yok (M-11) |
| Compose bar | `--lumos-compose-bg`; üst gölge hafif; iç içe border yok |
| Boşluk | Mesajlar arası min 12px; bölüm arası 16–20px |
| Compose yüksekliği | Mobilde min 44px dokunma; iOS 16px font korunur |

### 5.7 Tipografi ölçeği — ✨ CİLA

**Aile:** `ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif` — tek stack.

| Rol | Boyut | Ağırlık | CSS değişken (hedef) |
|-----|-------|---------|----------------------|
| Başlık (panel / modül) | 18–20px | 600 (SemiBold) | `--panel-font-title` → `1.125–1.25rem` |
| Gövde | 14–15px | 400 (Regular) | `--panel-font-body` → `0.875–0.9375rem` |
| Caption / rozet / meta | 12–13px | 500–600 | `--panel-font-caption` → `0.75–0.8125rem` |
| Mono (Kuantum tablo, ID) | 13px | 400 | `--panel-font-mono` |

**Kısıt:** Yalnızca Regular (400) ve SemiBold (600); Bold (700) kullanılmaz.

### 5.8 Responsive davranış — ✨ CİLA

| Kırılım | Davranış |
|---------|----------|
| **Geniş** ≥ 1024px | Sol nav: ikon + etiket; geçmiş paneli yan sütun |
| **Orta** 768–1023px | Nav daraltılabilir; etiketler görünür veya kısaltılmış |
| **Dar** < 768px | Nav: **yalnızca ikon**; hover/focus tooltip veya genişleyen drawer |
| Lumos çekirdeği | Mevcut mobil gizleme (H-05) yerine: alt menü + «Daha fazla» veya Ayarlar içi linkler |
| Touch | Tüm nav ve rozet min 44×44px (H-04) |
| Zoom | `user-scalable=no` kaldırılır (H-09) |

---

## 6. Tema tokenları

### 6.1 Birleşik token tablosu

Koyu sütun: PR #525 `lumos-tokens.css` (mevcut). Açık sütun: **🆕** yeni tanım. Uygulama Phase 3’te.

| Token | Koyu (mevcut) | Açık (hedef) | Kullanım |
|-------|---------------|--------------|----------|
| `--lumos-bg` | `#0a0e14` | `#F6F7F8` | Sayfa zemin |
| `--lumos-panel` / `--lumos-surface` | `#121a24` | `#FCFCFC` | Kart, sidebar yüzey |
| `--lumos-surface-raised` | `#1a2433` | `#FFFFFF` | Yükseltilmiş kart (saf beyaz yalnızca raised) |
| `--lumos-border` | `rgba(100,130,170,0.15)` | `#E5E7EB` | Ayırıcı |
| `--lumos-text` | `#e8edf4` | `#1F2937` | Birincil metin |
| `--lumos-text-soft` | `#94a3b8` | `#6B7280` | İkincil metin |
| `--lumos-muted` | `#64748b` | `#9CA3AF` | Meta, placeholder |
| `--lumos-accent-primary` | `#2dd4bf` | `#14b8a6` | Teal accent (her iki tema) |
| `--lumos-accent-primary-deep` | `#14b8a6` | `#0d9488` | Hover / pressed |
| `--lumos-heading-warm` | `#d4c4a8` | `#374151` | Başlık vurgusu (açıkta nötr) |
| `--lumos-gold` / altın vurgu | `#d4a574` | `#b45309` (seyrek) | İkincil vurgu; açıkta minimal |
| `--lumos-input-bg` | `#0a0e14` | `#F1F5F9` | Input inset |
| `--lumos-sidebar-bg` | `#0a0e14` | `#FCFCFC` | Sol nav |
| `--lumos-chat-history-bg` | `#121a24` | `#FCFCFC` | Thread zemin |
| `--lumos-compose-bg` | `rgba(18,26,36,0.94)` | `#FFFFFF` | Compose bar |
| `--lumos-focus-ring` | *(tanımlanacak)* | `2px solid var(--lumos-accent-primary)` | Tüm odak |
| `--lumos-radius-sm` | `8px` | `8px` | Input, badge |
| `--lumos-radius-md` | `10px` | `8px` | Buton, nav |
| `--lumos-radius-lg` | `12px` | `12px` | Kart |
| `--lumos-chat-tail` | *(eklenecek)* `5px` | `5px` | Bubble kuyruk istisnası |
| `--panel-body-wash` | Çok katmanlı teal radial | **Yok** veya tek %2 neutral | Açıkta wash yok |
| `--panel-strip-bg` | Koyu gradyan | Düz `--lumos-panel` | Header |

### 6.2 Koyu tema polish (Phase 0 — ✨ CİLA)

Mevcut token yapısı korunur; uygulama değişiklikleri:

- `--lumos-accent-blue-bright` (`#5eead4`) ve sky-blue hardcode kullanımı kaldırılır.
- `--lumos-teal-40+` scrollbar / glow tüketimi → `--lumos-teal-28` varsayılan.
- `--panel-chat-wash` opaklık düşürülür veya `--panel-body-wash` ile birleştirilir.
- Altın vurgu yalnızca ikincil emphasis (görev kartı hover); birincil accent teal kalır.

### 6.3 Açık tema referansları

- **OpenAI / ChatGPT:** nötr gri zemin, sakin sidebar.
- **Linear:** soğuk nötr, keskin tipografi.
- **Notion:** içerik önceliği, yumuşak border — **renk olarak soğuk nötr tercih edilir** (sıcak krem değil).

**Saf beyaz (`#FFFFFF`) yalnızca `--lumos-surface-raised` için;** sayfa zemin `#F6F7F8`, panel `#FCFCFC`.

---

## 7. Erişilebilirlik

| Konu | Gereksinim |
|------|------------|
| Kontrast | AA 4.5:1 gövde; UI bileşenleri 3:1 |
| Dokunma | 44×44px min (nav, rozet, tema, compose gönder) |
| Focus | Görünür `--lumos-focus-ring`; klavye ile tüm modüller erişilebilir |
| `aria-current` | Aktif modül ve geçmiş oturum |
| `aria-live` | Bağlantı rozeti, sohbet thread — mevcut korunur |
| Zoom | Viewport kısıtı kaldırılır |
| `prefers-reduced-motion` | Tema geçişi ve hover animasyonları devre dışı |
| `prefers-color-scheme` | Sistem teması ile senkron |
| Renk körlüğü | Durum yalnızca renkle değil; metin + ikon/dot |

---

## 8. Kaçınılacaklar ve referans ürünler

### 8.1 Kaçınılacaklar

- Cyberpunk estetik, grid arka plan, scanline
- Aşırı neon, blur, glassmorphism şovu
- Çok renkli badge yığını
- Gereksiz micro-animation (bounce, pulse dekoratif)
- Demo form + devre dışı gönder üçlüsü (prototip hissi — audit H-02)
- Mock veri varsayılan görünür (Kuantum — H-03)
- Parliament-navy ağır gradyan «törensel» dil (pivot tamamlanmış sayılır — #525)

### 8.2 Referans ürünler (hedef his)

| Ürün | Alınacak ders |
|------|----------------|
| **ChatGPT** | Sohbet odaklı sade shell, geçmiş listesi, tema toggle |
| **Linear** | Spacing disiplini, soğuk nötr açık tema, durum pill’leri |
| **Notion** | İçerik kartları, taslak alanı okunabilirliği |
| **Arc** | Sakin chrome, dikkat dağıtmayan nav |
| **Raycast** | Kompakt nav, net ikonografi |
| **GitHub** | Kurumsal güven, minimal renk, net meta |

---

## 9. Mevcut durum vs hedef

Özet kaynak: [`ui-design-audit-report.md`](./ui-design-audit-report.md) + bu spec mandate’i.

| Alan | Mevcut (2026-06) | Hedef | Tür |
|------|------------------|-------|-----|
| Tema | Yalnızca koyu (#525 tokens) | Açık + Koyu + Sistem | 🆕 |
| Sol nav modülleri | 8 çalışma + lumos çekirdeği grubu (10+) | 8 düz modül + alt menü 3 | 🆕 + ✨ |
| Nav ikonları | Yok | Lucide eşlemesi | 🆕 |
| Alt menü | Yok | Geçmiş, Ayarlar, Yardım | 🆕 |
| Sohbet geçmişi listesi | Yok (yalnızca thread) | Yan panel, gruplu liste | 🆕 |
| Tema düğmesi | Yok | Header sağ üst | 🆕 |
| Aktif nav glow | Teal sağ glow (M-04) | Düz yüzey + sol border | ✨ |
| Chat wash | Ağır inset teal (H-07) | Azaltılmış / kaldırılmış | ✨ |
| Durum rozetleri | UPPERCASE, küçük font (H-04) | Minimal pill, sentence case | ✨ |
| Conn badge OK | Neon cyan metin (M-10) | Soft metin, glow yok | ✨ |
| Tipografi | Karışık clamp/hardcode | 18–20 / 14–15 / 12–13 ölçeği | ✨ |
| Mesaj nesting | Capability kart + çoklu border | Tek kart, spacing | ✨ |
| Mobil nav | < 44px, lumos gizli (H-04, H-05) | 44px, alt menü erişimi | ✨ |
| Önizleme modülleri | Demo proto formlar (H-02) | Birleşik önizleme empty-state | ✨ |
| Spacing/radius | Token dışı dağınık (M-01, M-02) | 4px grid enforce | ✨ |
| Focus ring | Teal vs altın çift sistem (M-08) | Tek `--lumos-focus-ring` | ✨ |
| Viewport zoom | `user-scalable=no` (H-09) | İzin ver | ✨ |
| Ayarlar | Lumos çekirdeği önizleme modülü | Alt menü birincil giriş | 🆕 |

---

## 10. Uygulama fazları

**Bu belge implementasyon içermez.** Gelecek PR’lar için önerilen sıra:

### Phase 0 — Token ve görsel cila (yeni rota yok)

- Koyu tema glow/wash bütçesi (H-07, M-04, M-10, D-08)
- Spacing, radius, surface hardcode temizliği (M-01–M-03)
- Tek focus ring; tipografi ölçeği hizası
- Mesaj alanı border azaltma; conn/user mode rozet sadeleştirme
- Viewport zoom; mobil 44px hedefler (kısmi)
- **Çıktı:** Görsel regresyon testleri yeşil (`test_panel_visual_polish.py`)

### Phase 1 — Navigasyon ve rozetler

- Lucide ikonları birincil nav + alt menü iskeleti
- Düz 8 modül listesi; lumos çekirdeği birincil nav’dan kaldırma
- **🆕** Alt menü: Geçmiş, Ayarlar, Yardım (Ayarlar routing)
- Durum rozetleri metin/stil güncellemesi
- Dar/geniş responsive nav davranışı
- **Çıktı:** Nav IA testleri, mobil erişilebilirlik spot check

### Phase 2 — Sohbet geçmişi paneli

- **🆕** Oturum listesi API / localStorage sözleşmesi (ayrı teknik spec gerekebilir)
- Yan panel UI: gruplar, boş durum, seçim
- Geçmiş ↔ aktif thread geçişi
- i18n grup başlıkları
- **Çıktı:** E2E sohbet geçmişi akışı

### Phase 3 — Açık tema

- `lumos-tokens.css` light variant veya `[data-theme="light"]` bloğu
- **🆕** Tema toggle (Açık / Koyu / Sistem)
- `theme-color` ve `color-scheme` güncellemesi
- Landing–panel açık tema hizası (isteğe bağlı alt PR)
- Kontrast doğrulama (açık zemin üzerinde tüm modüller)
- **Çıktı:** İki tema görsel test snapshot’ları

---

## 11. Açık kararlar

| # | Konu | Seçenekler | Not |
|---|------|------------|-----|
| 1 | **Ses / Medya kapsamı** | (a) Önizleme kalır (b) Sohbet içi attach ile birleşir (c) Ayrı modül olarak aktifleştirme | Spec modülleri korur; aktivasyon ürün kararı |
| 2 | **Lumos çekirdeği modülleri** | (a) Tamamen ayarlar altında (b) «Gelişmiş» expandable nav (c) Kaldır, yalnızca docs | Yetenekler şu an aktif — erişim korunmalı |
| 3 | **Geçmiş veri kaynağı** | localStorage vs sunucu oturum API | Phase 2 öncesi teknik spec gerekir |
| 4 | **i18n tarih grupları** | Göreli («Bugün») vs mutlak tarih | `Intl.RelativeTimeFormat` + locale |
| 5 | **Açık tema sıcaklığı** | Soğuk nötr (bu spec) vs sıcak Notion (design language Tema 2) | Kullanıcı mandate soğuk; revizyon possible |
| 6 | **Kuantum nav stili** | `panel-nav-research-chip` kaldırıldı — normal öğe mi, hâlâ «araştırma» etiketi mi? | Spec: normal öğe |
| 7 | **Yardım hedefi** | In-app sheet vs `docs/` link vs her ikisi | Public boundary — üretim URL yok |
| 8 | **Altın ikincil vurgu** | Koyu temada koru vs tamamen teal-monokrom | Spec: altın seyrek ikincil |

---

## Ek: Özet sayılar (uygulama planlama)

| Kategori | Adet |
|----------|------|
| Uygulama fazı | **4** (Phase 0–3) |
| **🆕 YENİ** özellik | **4** — (1) alt menü, (2) sohbet geçmişi paneli, (3) tema sistemi, (4) nav Lucide ikon seti |
| **✨ CİLA** öğe | **12** — glow/wash, rozetler, tipografi, mesaj nesting, spacing/radius, focus ring, mobil touch, viewport zoom, önizleme empty-state, chat wash, conn badge, responsive nav genişlik |

*Lucide ikonları yalnızca cila sayılmış alternatif: birincil nav IA değişikliği ile birlikte **🆕** sayılabilir; bu belgede **🆕** (4. özellik) olarak sınıflandırıldı.*

---

*Son güncelleme: 2026-06-22 — Birleşik panel UI/UX spesifikasyonu v1.0-draft.*
