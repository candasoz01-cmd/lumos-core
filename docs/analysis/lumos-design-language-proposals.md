# Lumos Tasarım Dili — Tema Yönü Önerileri

| Alan | Değer |
|------|-------|
| **Belge türü** | Tasarım sistemi önerisi — uygulama yok |
| **Tarih** | 2026-06-21 |
| **Kapsam** | Renk paleti, tipografi, spacing, bileşen tonu; kod/CSS değişikliği yok |
| **Bağlam** | Internal Alpha panel (`ui/src/pages/panel.astro`), RB-17 inactive rozetleri, Posta/Sosyal taslak alanları, Kuantum hazırlık bölümü |
| **Pivot** | Mevcut **parliament-navy** (parliament-lacivert) yönünden çıkış |

---

## Özet

Lumos paneli bugün koyu control-center estetiğinde; parliament-lacivert gradyanlar, teal vurgu ve altın ikincil tonlarla «kurumsal gece» hissi veriyor. Bu belge, **premium, insan odaklı, güvenilir, modern SaaS** hedefi için üç ayrı tema yönü önerir. Her tema yalnızca tasarım dili ve renk paletini kapsar; implementasyon adımı içermez.

**Panel bağlam notları (uygulama değil, referans):**

- **Control center:** üst şerit, modül navigasyonu, bağlantı rozeti, profil/guard durumları — hiyerarşi ve güven sinyalleri kritik.
- **RB-17 inactive rozetleri:** Ses, Medya, Sosyal, Posta, Kuantum modüllerinde «Önizleme» / `inactiveBadge` dili; aktif olmayan modül ile taslak modül ayrımı net kalmalı.
- **Posta / Sosyal taslak alanları:** form, özet, gönderim öncesi onay — içerik okunabilirliği ve «henüz gönderilmedi» tonu öncelikli.
- **Kuantum alanı:** DEMO banner, readiness rozetleri, tablo/liste yoğunluğu — teknik içerik, abartılı dramatik koyuluk gerektirmez.

---

## Mevcut parliament-navy yönünden pivot gerekçesi

Bugünkü panel `--lumos-panel-navy` (#1e3a5f), `--lumos-panel-navy-deep` (#0f1f35) ve çok koyu zemin (#020408) üzerine teal/altın vurgu kullanıyor. Bu yön:

- **Landing ile panel arasında duygusal kopukluk** yaratıyor (landing daha elektrik cyan; panel daha parliament-lacivert).
- **İnsan odaklı güven** yerine «kurumsal otorite / gece operasyonu» çağrışımı güçlü; taslak ve önizleme modülleri ağır hissediliyor.
- **Uzun okuma ve form alanlarında** (Posta/Sosyal) kontrast ve yorgunluk dengesi zor; muted metinler koyu zemin üzerinde «pasif» ile «devre dışı» ayrımını zorlaştırıyor.
- **Modern SaaS beklentisi** (açık hiyerarşi, sakin nötrler, net durum renkleri) ile çelişiyor; RB-17 rozetleri altın/teal içinde kaybolabiliyor.

Pivot hedefi: Lumos’u «parliament gece paneli» değil, **güven veren, sakin, ürün kalitesinde** bir asistan yüzeyi olarak konumlandırmak.

---

## Tema 1 — Geliştirici Konsolu (OpenAI eski developer panel hissi)

**Tek satır konumlandırma:** Koyu, ölçülü, teknik güven — geliştirici ve power-user için sessiz otorite.

### Tasarım ilkeleri

- **Restraint:** Az renk, yüksek bilgi yoğunluğu; dekoratif gradyan yok.
- **Technical trust:** Durum ve hata mesajları net; parlak vurgu yalnızca etkileşim anında.
- **Monokrom öncelik:** Nötr gri katmanlar; accent yalnızca birincil eylem ve bağlantı durumunda.
- **Okunabilir kod/veri:** Tablo, badge ve monospace alanlar için tutarlı arka plan kontrastı.
- **Gece modu kalıcılığı:** Uzun oturumlarda göz yorgunluğunu minimize eden düşük luminance.

### Renk paleti

| Token adı | Hex | Kullanım |
|-----------|-----|----------|
| `bg-base` | `#171717` | Ana zemin (body, shell) |
| `bg-sidebar` | `#202020` | Yan navigasyon, ikincil şerit |
| `surface-raised` | `#212121` | Kart, form paneli, chat history |
| `surface-inset` | `#2a2a2a` | Input, compose, taslak editörü |
| `text-primary` | `#ececec` | Başlık, birincil içerik |
| `text-secondary` | `#9b9b9b` | Yardımcı metin, caption |
| `accent-primary` | `#10a37f` | Birincil CTA, aktif nav, bağlı durum |
| `accent-hover` | `#0d8f6e` | Hover / pressed accent |
| `border-default` | `#2f2f2f` | Kart ve bölüm ayırıcıları |
| `border-subtle` | `#262626` | İç inset çizgiler |
| `success` | `#3fb950` | Tamamlandı, onay, hazır |
| `warning` | `#d29922` | Beklemede, kısmi, demo |
| `error` | `#f85149` | Hata, red, kritik uyarı |
| `inactive` | `#6e6e6e` | Devre dışı modül metni; `%55` opacity overlay |

### Tipografi ölçeği

| Rol | Aile | Boyut | Ağırlık | Not |
|-----|------|-------|---------|-----|
| Display | `ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif` | `1.125rem` (18px) | 600 | Panel başlık, modül adı |
| Title | Aynı stack | `1rem` (16px) | 600 | Bölüm başlığı |
| Body | Aynı stack | `0.875rem` (14px) | 400–450 | Form, liste, chat |
| Caption | Aynı stack | `0.75rem` (12px) | 500 | Rozet, meta, RB-17 |
| Mono | `ui-monospace, "SF Mono", Consolas, monospace` | `0.8125rem` (13px) | 400 | Kuantum tablo, ID, log satırı |

Letter-spacing: başlıklarda `-0.02em`; uppercase rozetlerde `+0.06em`.

### Spacing ve radius token’ları

4px taban grid; ana ritim 8px katları.

| Token | Değer | Kullanım |
|-------|-------|----------|
| `space-1` | 4px | İkon–metin gap, rozet padding dikey |
| `space-2` | 8px | Form alanı iç boşluk, nav item gap |
| `space-3` | 12px | Kart iç padding (kompakt) |
| `space-4` | 16px | Bölüm arası, sidebar padding |
| `space-5` | 24px | Modül üst boşluk |
| `space-6` | 32px | Geniş içerik marjı |
| `radius-sm` | 6px | Input, küçük badge |
| `radius-md` | 8px | Nav item, buton |
| `radius-lg` | 12px | Kart, modal |
| `radius-pill` | 999px | Durum rozeti, conn badge |

### Bileşen ton notları

- **Nav:** Düz sidebar; aktif item hafif accent wash (`accent @ 18%`), inactive modüller soluk metin + outline «Önizleme» pill.
- **Kartlar:** İnce border; gölge yok veya `0 1px 2px rgba(0,0,0,0.4)`.
- **Badge:** Uppercase caption; success/warn/error semantic; DEMO/Kuantum için `warning` tonu.
- **Taslak alanları (Posta/Sosyal):** `surface-inset` editör; gönder butonu secondary/disabled görünüm — accent yalnızca «Özeti göster» gibi güvenli eylemlerde.
- **Inactive modüller:** Opacity + `inactive` metin rengi; RB-17 rozeti border-only, accent kullanmaz.

### Lumos panel için ne zaman seçilir?

- Hedef kitle ağırlıklı **teknik / geliştirici / operasyon** kullanıcısıysa.
- Panel «CLI’nin görsel uzantısı» gibi konumlanacaksa.
- Kuantum, log ve tablo yoğun ekranlar ön plandaysa.
- Landing’den bağımsız, **her zaman koyu** bir control center isteniyorsa.

### Parliament-navy ile zıtlık

Parliament-navy dramatik gradyan ve altın ikincil ile «törensel» his verir; Tema 1 **düz, utilitarian, yeşil-accent** ile OpenAI eski panel sadeliğine döner — teknik güven evet, kurumsal ağırlık hayır.

---

## Tema 2 — Sıcak Açık (Notion benzeri)

**Tek satır konumlandırma:** Sıcak, davetkar, içerik öncelikli — taslak ve okuma deneyiminde insan merkezli sakinlik.

### Tasarım ilkeleri

- **Content-first:** UI chrome geri planda; metin ve form alanı ön planda.
- **Warm neutrality:** Soğuk mavi-gri yerine krem/bej nötrler; «ofis kağıdı» sıcaklığı.
- **Soft hierarchy:** Kalın border ve gölge yerine boşluk + hafif yüzey farkı.
- **Approachable trust:** Korkutmayan durum renkleri; hata mesajları açıklayıcı, agresif değil.
- **Draft-friendly:** Taslak modüllerde «henüz değil» tonu yumuşak; kullanıcıyı cezalandırmayan inactive dili.

### Renk paleti

| Token adı | Hex | Kullanım |
|-----------|-----|----------|
| `bg-base` | `#FBFBFA` | Ana zemin |
| `bg-sidebar` | `#F7F6F3` | Nav, ikincil şerit |
| `surface-raised` | `#FFFFFF` | Kart, modül paneli |
| `surface-inset` | `#F1F0ED` | Textarea, taslak editörü, input bg |
| `text-primary` | `#37352F` | Başlık, gövde (Notion-charcoal benzeri) |
| `text-secondary` | `#787774` | Yardımcı, placeholder, meta |
| `accent-primary` | `#2383E2` | Birincil link/CTA (sakin mavi) |
| `accent-secondary` | `#9065B0` | İkincil vurgu, research chip (Kuantum) |
| `border-default` | `#E9E9E7` | Kart, bölüm çizgisi |
| `border-strong` | `#D3D1CB` | Focus, seçili nav |
| `success` | `#0F7B6C` | Hazır, onaylı, tamamlandı |
| `warning` | `#CB912F` | Demo, kısmi, bekleyen |
| `error` | `#E03E3E` | Hata, red (yumuşak ama net) |
| `inactive` | `#C4C4C0` | Devre dışı modül; `%70` opacity metin |

### Tipografi ölçeği

| Rol | Aile | Boyut | Ağırlık | Not |
|-----|------|-------|---------|-----|
| Display | `ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif` | `1.25rem` (20px) | 600 | Modül başlığı |
| Title | Aynı stack | `1.0625rem` (17px) | 600 | Alt bölüm |
| Body | Aynı stack | `0.9375rem` (15px) | 400 | Taslak metin, açıklama |
| Caption | Aynı stack | `0.75rem` (12px) | 500 | RB-17 «Önizleme», tarih |
| Mono | `ui-monospace, monospace` | `0.8125rem` | 400 | Kuantum tablo (seyrek) |

Line-height: body `1.6`; form alanlarında rahat okuma.

### Spacing ve radius token’ları

8px taban grid; içerik nefes alanı geniş.

| Token | Değer | Kullanım |
|-------|-------|----------|
| `space-1` | 4px | Rozet içi |
| `space-2` | 8px | Label–input gap |
| `space-3` | 12px | Kart padding (dar) |
| `space-4` | 16px | Kart padding (standart) |
| `space-5` | 24px | Bölüm arası |
| `space-6` | 40px | Modül üst, geniş içerik |
| `radius-sm` | 4px | Badge, tag |
| `radius-md` | 6px | Input, buton |
| `radius-lg` | 8px | Kart (Notion yumuşak köşe) |
| `radius-xl` | 12px | Büyük panel, özet kutusu |

### Bileşen ton notları

- **Nav:** Geniş satır yüksekliği; hover `surface-inset`; aktif item hafif gri wash + sol accent çizgi (`accent-primary @ 1.5px`).
- **Kartlar:** Beyaz yüzey, ince border; gölge çok hafif (`0 1px 3px rgba(0,0,0,0.06)`).
- **Badge:** Pastel arka plan + koyu metin; RB-17 «Önizleme» = `surface-inset` + `text-secondary`, success/error ile karışmaz.
- **Taslak alanları:** Posta/Sosyal textarea geniş, `surface-inset`; özet kutusu `surface-raised` + `border-strong`.
- **Inactive modüller:** Soluk nav + pill rozet; tıklanabilir ama «önizleme» hissi — kilit ikonu yerine açıklayıcı metin.

### Lumos panel için ne zaman seçilir?

- **Posta/Sosyal taslak** ve uzun metin okuma ön plandaysa.
- Lumos «insan asistanı» kimliği **sıcaklık ve erişilebilirlik** ile anlatılacaksa.
- RB-17 inactive modüller **korkutmadan merak uyandırmalıysa**.
- Internal Alpha’da landing’den panele geçişte **duygusal süreklilik** (açık/krem ton) isteniyorsa.

### Parliament-navy ile zıtlık

Parliament-navy koyu gradyan + altın/teal ile ağır ve gece odaklıdır; Tema 2 **gündüz, kağıt, içerik** metaforuna geçer — güven otorite değil **şeffaflık ve okunabilirlik** üzerinden kurulur.

---

## Tema 3 — Soğuk Nötr (Linear benzeri)

**Tek satır konumlandırma:** Serin nötr, keskin tipografi, ince derinlik — ürün kalitesinde modern SaaS cilası.

### Tasarım ilkeleri

- **Product-grade polish:** Her piksel hizalı; spacing disiplini katı.
- **Cool neutral calm:** Mavi-gri nötrler; duygusal sıcaklık düşük, profesyonel sakinlik yüksek.
- **Subtle depth:** Tek yönlü hafif gölge + 1px highlight; flat değil, abartılı değil.
- **Crisp type:** Küçük boyutlarda bile net hiyerarşi; letter-spacing kontrollü.
- **Status as design:** Bağlantı, profil, modül durumu renk kodlu ama pastel-değil, net semantic.

### Renk paleti

| Token adı | Hex | Kullanım |
|-----------|-----|----------|
| `bg-base` | `#F4F5F8` | Ana zemin (hafif cool gray) |
| `bg-sidebar` | `#EEEFF2` | Nav shell |
| `surface-raised` | `#FFFFFF` | Kart, panel içeriği |
| `surface-sunken` | `#E8EAED` | Input bg, code block |
| `text-primary` | `#1A1D26` | Birincil metin |
| `text-secondary` | `#6B7280` | İkincil, meta |
| `accent-primary` | `#5E6AD2` | Birincil CTA, aktif nav (Linear-mor-mavi) |
| `accent-muted` | `#8B92D6` | Hover, seçili arka plan wash |
| `border-default` | `#E2E4EA` | Standart ayırıcı |
| `border-focus` | `#5E6AD2` | Focus ring |
| `success` | `#28A745` | Başarı, connected |
| `warning` | `#F2C94C` | Demo, pending (koyu metin ile) |
| `error` | `#EB5757` | Hata, disconnected |
| `inactive` | `#9CA3AF` | Devre dışı modül metni ve ikon |

### Tipografi ölçeği

| Rol | Aile | Boyut | Ağırlık | Not |
|-----|------|-------|---------|-----|
| Display | `Inter, ui-sans-serif, system-ui, sans-serif` | `1.125rem` (18px) | 600 | `-0.025em` tracking |
| Title | Aynı stack | `0.9375rem` (15px) | 600 | Bölüm, nav grup |
| Body | Aynı stack | `0.8125rem` (13px) | 450 | Linear sıkı gövde |
| Caption | Aynı stack | `0.6875rem` (11px) | 500 | Rozet, timestamp |
| Mono | `"JetBrains Mono", ui-monospace, monospace` | `0.75rem` (12px) | 400 | Kuantum tablo, ID |

### Spacing ve radius token’ları

4px taban; yoğun UI için 8px ritim.

| Token | Değer | Kullanım |
|-------|-------|----------|
| `space-1` | 4px | İç micro gap |
| `space-2` | 8px | Kompakt padding |
| `space-3` | 12px | Kart içi |
| `space-4` | 16px | Standart blok |
| `space-5` | 20px | Linear-tight section gap |
| `space-6` | 24px | Modül header altı |
| `radius-sm` | 4px | Badge, tag |
| `radius-md` | 6px | Buton, input |
| `radius-lg` | 8px | Kart |
| `radius-xl` | 10px | Büyük panel (panel.astro mevcut `--panel-radius` ile uyumlu) |

### Bileşen ton notları

- **Nav:** İnce, kompakt; aktif = `accent-primary` sol border + hafif `accent-muted @ 12%` bg.
- **Kartlar:** `surface-raised` + `border-default` + `0 1px 2px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.02)`.
- **Badge:** Küçük, keskin; semantic renkler doygun ama küçük alanda; RB-17 outline badge (`border-default`, `text-secondary`).
- **Taslak alanları:** Sunken input; primary gönder disabled — `text-secondary` + `surface-sunken`.
- **Inactive modüller:** Nav’da `inactive` renk; quantum research chip accent-secondary ile ayrılır ama inactive rozeti nötr kalır.
- **Control center header:** Tek satır strip, conn badge pill — success/error net semantic.

### Lumos panel için ne zaman seçilir?

- Panel öncelikle **operasyon / durum / modül orchestration** yüzeyiyse.
- **Profil guard, bağlantı, enforcement** gibi güven sinyalleri görsel hiyerarşide ön plandaysa.
- Ekip **Linear/Stripe kalitesinde** SaaS hissi hedefliyorsa.
- Landing’den bağımsız; panel = **profesyonel ürün konsolu** narrativi isteniyorsa.

### Parliament-navy ile zıtlık

Parliament-navy dekoratif wash ve altın vurgu ile «iç mekan» estetiği taşır; Tema 3 **soğuk, düz, ürün UI** diline geçer — güven **tutarlılık ve keskinlik** ile inşa edilir, dramatik koyulukla değil.

---

## Ortak cross-theme token’lar

Tema seçiminden bağımsız olarak Lumos panelinde sabit kalması önerilen kurallar:

### Erişilebilirlik — minimum kontrast

| Bağlam | WCAG hedefi | Kural |
|--------|-------------|-------|
| Gövde metin / zemin | AA (4.5:1) | `text-primary` on `bg-base` veya `surface-raised` |
| İkincil metin | AA büyük metin veya 4.5:1 tercih | `text-secondary` yalnızca caption/meta; kritik durumda primary |
| UI bileşen / border | 3:1 (non-text) | Focus ring ve aktif nav indicator |
| Semantic (success/warn/error) | AA ikon + metin çifti | Arka plan wash kullanılıyorsa metin rengi koyulaştırılır |
| Disabled / inactive | Bilinçli istisna | Kontrast düşürülebilir ama **min 3:1** okunabilirlik; tam kaybolma yok |

Koyu temalarda (Tema 1): muted metin `#9b9b9b` on `#171717` ≈ 5.5:1 — uygun.  
Açık temalarda (Tema 2–3): secondary metin asla `#aaa` altına inmemeli.

### Inactive modül dili (RB-17)

Tüm temalarda tutarlı semantik:

| Öğe | Kural |
|-----|-------|
| Rozet metni | «Önizleme» / «Preview» — `INTERNAL_ALPHA_UX_FINDINGS` ile uyumlu |
| Görsel ton | Semantic success/error/warning **kullanılmaz**; nötr outline veya inset pill |
| Nav item | Tıklanabilir kalır; opacity `%70–90` aralığı tema bazında ayarlanır |
| Aktif modül ayrımı | `aria-current` + birincil accent; inactive asla accent wash almaz |
| Taslak modül içi | Form aktif, dış gönderim kapalı — «demo hint» warning semantic, nav inactive değil |

### Diğer paylaşılan token’lar

| Token | Öneri |
|-------|-------|
| `focus-ring` | 2px solid accent + 2px offset; keyboard nav zorunlu |
| `motion-reduce` | `prefers-reduced-motion` — transition ≤ 0.01ms |
| `touch-min` | İnteraktif hedef min 44×44px (mobil panel) |
| `content-max` | Geniş modül gövdesi ~44–52rem (mevcut panel rhythm ile uyum) |
| `demo-banner` | Her temada `warning` semantic; parliament altınından bağımsız |

---

## Yönetici önerisi (Executive recommendation)

**Önerilen tema: Tema 2 — Sıcak Açık (Notion benzeri)**

**Gerekçe (insan odaklı + güven):**

1. **İnsan merkezli:** Lumos bir «gece operasyon merkezi» değil, kullanıcıyla birlikte düşünen asistan; sıcak nötrler ve geniş okuma ritmi Posta/Sosyal taslak deneyimini destekler.
2. **Güven modeli:** Parliament-navy otoriter kurumsallık taşır; Tema 2 güveni **açıklık ve okunabilirlik** ile kurar — Internal Alpha’da «henüz gönderilmiyor / önizleme» mesajları daha dürüst ve az tehditkar okunur.
3. **RB-17 uyumu:** Inactive «Önizleme» rozetleri pastel-nötr dilde success/error ile karışmaz; kullanıcı hangi modülün tasarım aşamasında olduğunu sakin bir tonla anlar.
4. **Kuantum alanı:** Teknik tablo içerikleri açık zeminde daha uzun süre taranabilir; DEMO uyarısı warning semantic ile net kalır, dramatik koyuluk gerekmez.
5. **Modern SaaS:** Notion-benzeri dil günümüz kullanıcı beklentisiyle uyumlu; premium his boşluk ve tipografi disipliniyle gelir, gradyan şovuyla değil.

**Güçlü alternatif:** Control center ağırlığı artarsa (profil guard, enforcement, çok modüllü durum panosu) **Tema 3** shell + Tema 2 taslak modül içleri hibriti değerlendirilebilir — ancak tek tema seçimi zorunluysa insan odaklı güven için Tema 2 önceliklidir.

**Bilinçli dışlama:** Tema 1, `frontend/index.html` ve eski OpenAI panel referansıyla uyumlu olsa da Lumos’un «premium human-centered SaaS» hedefinde **geliştirici aracı** hissini güçlendirir; parliament-navy’den farklı bir koyu yön olur, pivot’un asıl amacı olan sıcaklık ve geniş kitle güvenine daha az hizmet eder.

---

## Sonraki adım (bu belge kapsamı dışı)

Tema seçimi onaylandıktan sonra ayrı bir uygulama belgesi: token → CSS custom property eşlemesi, panel.astro migrasyonu, landing–panel duygusal hizası ve RB-17/Posta/Sosyal/Kuantum bileşen doğrulama checklist’i. **Bu dosya yalnızca öneridir; implementasyon içermez.**

---

## Referanslar

- Mevcut panel tema değişkenleri: `ui/src/pages/panel.astro` (`--lumos-panel-navy`, `--panel-body-wash`)
- RB-17 inactive badge: `tests/test_panel_module_nav_inactive_badge.py`, `docs/INTERNAL_ALPHA_UX_FINDINGS.md`
- Eski OpenAI-benzeri referans: `frontend/index.html` (`--accent: #10a37f`)
- Parliament-navy pivot bağlamı: panel `:root` yorumu — «Parliament-lacivert vurgu»
