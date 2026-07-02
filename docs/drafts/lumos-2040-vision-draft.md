# Lumos 2040+ / Uzun Vadeli Vizyon (Taslak)

> **TASLAK — kesin karar değil; Karar Duvarı (`LUMOS-*`) kaydı sayılmaz.**
>
> Bu belge bir **vizyon çekmecesi**dir: aklına geldikçe eklenir, zamanı gelince yeniden değerlendirilir. Buradaki hiçbir madde onay, taahhüt veya roadmap kilidi değildir.

---

## Çekmece kuralları

1. **Aklına geldikçe ekle** — eksik veya dağınık olması normaldir; tamamlanmayı bekleme.
2. **Hiçbir madde kesin karar sayılmaz** — uygulama, yatırım veya lansman iddiası taşımaz.
3. **Her madde zamanı gelince yeniden değerlendirilir** — çekmeceden çıkmak ayrı bir süreçtir (aşağıdaki kontrol listesi).
4. **O günün teknolojisi, hukuku ve gerçekleriyle tekrar test edilir** — dün mantıklı olan bugün geçersiz olabilir; tersi de mümkündür.

**Kesin kararlar için:** [`docs/drafts/BACKLOG.md`](./BACKLOG.md) — yalnızca `LUMOS-*` kayıtları Karar Duvarı sayılır.

**Karar şeması / ilişki:** [`docs/drafts/decision-engine-schema.md`](./decision-engine-schema.md) — bir fikir çekmeceden mezun olursa buradaki alanlar doldurulur; uydurma onay yazılmaz.

---

## Kurumsal ilke (vazgeçilmez)

> **Hiçbir yapı vazgeçilmez değildir; ilkeler vazgeçilmezdir.**

| Değişebilir | Vazgeçilmez ilkeler |
|-------------|---------------------|
| Ürün aileleri, modüller, teknoloji yığını | **Şeffaflık** — kullanıcı neyin neden yapıldığını görebilmeli |
| Kurumsal model, vakıf / şirket yapısı | **Denetlenebilirlik** — karar ve eylem izlenebilmeli |
| Donanım ortaklıkları, platform seçimleri | **Çok seslilik** — tek ses / tek model hakimiyeti hedef değil |
| Fazlar, isimler, kanal stratejisi | **Kullanıcıyı temsil etme** — kullanıcı adına konuşmak, kullanıcı yerine karar vermek değil |
| | **İnsan odaklılık** — teknoloji insanı merkeze alır; insanı ikame etmez |

---

## Yönetişim omurgası

> **Sistem, tek kişinin iyi niyetine değil; sağlam yönetişim, denetim ve kurallara dayanmalıdır.**

Bu cümle teknik bir gerekliliktir: Lumos'un uzun vadeli güvenilirliği kişisel güvene değil; kayıtlı kurallara, denetlenebilir yetki katmanlarına ve açık sınırlara dayanır. İyi niyet varsayımı tasarım gerekçesi olamaz.

---

## Mezuniyet kontrol listesi (çekmeceden çıkarken)

Bir madde buradan **Karar Duvarı** veya somut plana taşınmadan önce:

| Soru | Amaç |
|------|------|
| **Hukuken uygulanabilir mi?** | Yetki, sorumluluk, veri, sektör regülasyonu |
| **Teknik olarak mümkün mü?** | Bugünkü ve makul horizon'daki mühendislik gerçeği |
| **Finansal olarak sürdürülebilir mi?** | İşletme, bakım, destek maliyeti |
| **İnsanlara gerçekten fayda sağlıyor mu?** | Ölçülebilir veya savunulabilir kullanıcı değeri |
| **Açıkları ve kötüye kullanım senaryoları neler?** | Kötü niyet, yan etki, edge case — erken düşün |

Hepsi «evet» değilse madde çekmecede kalır veya daraltılır. Mezun olan madde [`BACKLOG.md`](./BACKLOG.md) üzerinden `LUMOS-*` kaydı olur; bu dosyaya otomatik karar eklenmez.

---

## Tohum maddeler (taslak — karar değil)

Aşağıdaki maddeler son konuşmalardan ve uzun vadeli yönelimden türetilmiş **tohum fikirlerdir**. Durum: ⚪ çekmece.

### Kurumsal model — Lumos 2040+

- Vakıf-benzeri, çok paydaşlı veya «foundation-like» kurumsal çerçeve araştırma konusu olabilir.
- Amaç: tek kişi / tek şirket bağımlılığını azaltmak; ilkeleri kurumsal yapıdan ayırmak (yukarıdaki «yapı değişir, ilke kalır»).
- Detay yapı, coğrafya ve hukuk **henüz tanımlı değil**.

### Ürün aileleri (vizyon tohumları)

Tek sayfalık harita fikri; implementasyon veya modül listesi değil. Aileler birbirini tamamlayan vizyon alanları olarak düşünülebilir:

| Aile | Kısa yön (taslak) |
|------|-------------------|
| **Trust** | Kimlik, yetki, anahtar, güven katmanı |
| **Work** | İş, süreç, üretkenlik |
| **Mobility** | Hareket, ulaşım, sahadaki bağlam |
| **Home** | Ev, cihaz, günlük yaşam |
| **Health** | Sağlık bilgisi ve engel azaltma — profesyonel yerine geçmez |
| **Finance** | Kişisel finans okuryazarlığı ve güvenli araçlar — danışmanlık değil |
| **Robotics** | Platform katmanı — aşağıda ayrı madde |
| **Accessibility** | Erişilebilirlik her aileye yatay ilke |
| **MicroTools** | Küçük, onaylı, sınırlı görev araçları |

İlgili **kesin karar referansı** (harita onayı): [`BACKLOG.md` — LUMOS-0012](./BACKLOG.md). Bu çekmece maddesi LUMOS-0012'yi genişletmez; yalnızca uzun vadeli tohumları tutar.

### Lumos Key ekosistemi

- Donanım / yazılım anahtar modeli; güvenin yalnızca modele değil mimariye dayanması.
- Ekosistem: üretim, kanıt cihazı, rotasyon, kullanıcı kontrolü — detay çekmecede.
- İlgili karar: [`BACKLOG.md` — LUMOS-0009](./BACKLOG.md) (Trust Layer / Lumos Key).

### Karar Duvarı / paylaşılan proje hafızası

- `LUMOS-*` kayıtları: neden, kapsam, iptal zinciri, ilişkili kararlar.
- Uzun vadede: yeni ajan / katkıcı yalnızca son kodu değil karar bağlamını okur.
- Şema taslağı: [`decision-engine-schema.md`](./decision-engine-schema.md).

### Temsilci model (representative)

- Lumos **kullanıcı adına hareket edebilir**; **kullanıcı yerine karar vermez**.
- Belirsizlikte seçenekleri açar; nihai karar kullanıcıda kalır.
- İlke: [`decision-engine-schema.md`](./decision-engine-schema.md) — belirsizlik ve onay bütünlüğü.

### Risk / hukuk kapısı ve destek yolu

- Yüksek riskli veya regülasyon gerektiren alanlarda otomatik «evet» yok.
- Destek yolu: uygun vakıf, uzman veya resmî kanala **yönlendirme** (Lumos tek başına hukuk / tıp / yatırım otoritesi olmaz).
- Somut ortaklık listesi **henüz yok** — çekmece notu.

### Robotics — platform katmanı, donanım satıcısı değil

- Lumos robot üreticisi olmayı hedeflemez; **orkestrasyon, güvenlik, yetki ve connector** katmanı olmayı hedefleyebilir.
- Donanım: ortak ekosistem, sertifikasyon, güvenli tool çağrıları — vizyon düzeyi.

### Fabrication / 3B — fazlı vizyon

- Ev veya atölye ölçeğinde üretim / 3B, **erken fazda değil**; uzun vadeli «Home + Work» kesişimi olarak çekmecede.
- Güvenlik, malzeme, sorumluluk mezuniyet listesinde ayrıca test edilmeli.

### Bootstrap / orkestrasyon — «Lumos'u aç»

- Tek komut veya ritüel ile: ortam, yetki, bağlam, görev motorunun tutarlı açılışı.
- «Lumos'u aç» = kullanıcı için güvenilir başlangıç durumu; arka planda dağınık script değil.
- Uygulama detayı çekmecede; V1 taahhüdü değil.

### Dış doğrulama notu (referans — karar BACKLOG'da)

Endüstride de «güvenlik yalnızca modele değil, çevreleyen mimariye dayanır» yönü desteklenmektedir. Bu çekmece maddesi **dış referans notudur**; kesin karar ve tema eşlemesi:

- [`BACKLOG.md` — LUMOS-0013](./BACKLOG.md) — External validation, AI güvenlik mimarisi (security bulletin analizi; LUMOS-0008, 0009, 0010 ile hizalı).

Burada sahte onay, «Approved by» veya vendor endorsement **yazılmaz** (bkz. LUMOS-0003 onay bütünlüğü).

---

## Nasıl kullanılır

1. Yeni fikir → uygun alt başlığa madde ekle veya yeni alt başlık aç.
2. Fikir olgunlaştı → mezuniyet kontrol listesini uygula.
3. Geçtiyse → [`BACKLOG.md`](./BACKLOG.md) üzerinde yeni `LUMOS-*` kaydı öner; **bu dosyadan otomatik karar türetme**.
4. Karar iptal / supersede → BACKLOG güncellenir; çekmece maddesi gerekirse arşiv veya «iptal» notu alır.

---

## İlişkili taslaklar

| Belge | İlişki |
|-------|--------|
| [`BACKLOG.md`](./BACKLOG.md) | Kesin kararlar (`LUMOS-*`) |
| [`decision-engine-schema.md`](./decision-engine-schema.md) | Karar alanları, onay bütünlüğü, mezuniyet sonrası şema |
| [`section-14-lumos-academy-vision.md`](./section-14-lumos-academy-vision.md) | Academy uzun vadeli vizyon (ayrı çekmece / arşiv taslağı) |

---

*Son güncelleme: 2026-07-02 · Belge durumu: TASLAK / çekmece*
