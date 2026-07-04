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

### Orkestrasyon / niyet akışı (Work + Connectors tohumu)

> **Lumos, menü arayarak ömür tüketmeyi bitirir; niyet → hazırlık → onay → uygulama.**

- Durum: ⚪ çekmece · faz tohumu **M0–M1** — Lumos Key veya production connector değil; vizyon örneği.
- **Dış yayın = 🔴 açık onay** — LUMOS-0015 (sorumluluk dengesi) ve LUMOS-0016 (denetim zinciri) ruhu: öner → risk/gerekçe → kullanıcı onayı → kayıt.

**Örnek tohum (LinkedIn makale yayını):**

| Adım | Kim |
|------|-----|
| «LinkedIn'de yeni makale yayınlamak istiyorum» | Kullanıcı niyeti |
| Profil → makale yaz → taslak → kapak → etiket öner → önizleme | Lumos hazırlık |
| Açık **«Yayınla»** onayı | Kullanıcı — dış etki kapısı |

Kullanıcı platform menüsünü aramaz; Lumos adımları hazırlar, dış etkili adımda durur.

### Lumos Orkestratör v1 — orkestra şefi katmanı

> **Orkestra kalabalık; eksik parça başka bir enstrüman değil, konduktör.** Lumos daha fazla zeka eklemek değil — dağınık araçları koordine etmektir.

| Alan | Değer |
|------|-------|
| **Durum** | ⚪ çekmece — vizyon tohumu |
| **Olgunluk** | **M0 Concept** ([`knowledge-repository-lifecycle.md`](../knowledge-repository-lifecycle.md) §5) |
| **Katman** | Vision Memory |
| **Karar Duvarı** | Bu madde `LUMOS-*` kaydı **değildir** |

**M0 onayı:** Kavram düzeyi tohum — **implementasyon, kod, PR veya uygulama planı değildir**. Repo'da parçalı yürütme hatları vardır; birleşik orkestratör katmanı henüz yoktur ([ADR-008](../decisions/ADR-008-agent-network-boundary.md)).

**Çekirdek içgörü:** Eksik katman koordinasyon / konduktörlüktür; ek zeka veya yeni araç değil. Orkestra zaten kalabalık: Cursor, Codex, ChatGPT, GitHub, Gmail, panel, köprü (bridge), MCP, CLI, görev motoru… Kullanıcı bunları tek tek yönetmemeli; **niyet bir kez söylenir**, Lumos yönlendirir, birleştirir, kaydeder, özet döner.

**Temel ilke — koordinasyon, zeka değil:** Lumos bir «daha akıllı model» değil; dağınık enstrümanları tek niyet altında koordine eden konduktördür. Yeni zeka veya yeni araç eklemek sorunu çözmez — eksik parça **tek koordinasyon yüzeyi**dir.

---

#### Parça haritası (M0 — mevcut vs eksik)

- **Mevcut parçalar:** Karar Duvarı / BACKLOG · ADR'ler · Knowledge Repository lifecycle · panel · bridge proxy · çok-ajan kuralları · yetki matrisi (LUMOS-0008) · model orkestrasyonu (LUMOS-0017) · bağımsız denetim (ADR-008) · denetim zinciri (LUMOS-0016)
- **Eksik katman:** Tek koordinasyon yüzeyi — niyet yönlendirme, araç/ajan seçimi (gerekçeli), birleşik sonuç, araçlar arası oturum sürekliliği

Parçalar dağınık ve birleşik değil; orkestratör bunları *hedef olarak* tek akışta bir araya getirir. ADR-008 özeti: parçalı hatlar birbirine bağlı ama **merkezi orchestrator / coordinator yok**.

| Parça | Rol (bugün) | Orkestratörle ilişki |
|-------|-------------|----------------------|
| **Karar Duvarı / BACKLOG** | `LUMOS-*` kesin kararlar, gerekçe, iptal zinciri | Hedef: her yönlendirme ve seçim gerekçesi buraya veya ilişkili kayda işlenir |
| **ADRs** | Mimari karar kayıtları (`docs/decisions/`) | Hedef: araç/ajan seçimi ADR sınırlarına uygun kalır |
| **Knowledge Repository** | Status, Maturity, kanıt, Review Date disiplini | Hedef: orkestrasyon kararları lifecycle ile izlenir |
| **Panel** | Görev/kayıt görünürlüğü, demo-safe yüzey | Hedef: kullanıcıya özet sonuç ve durum; orkestratör arka plan |
| **Bridge proxy** | `cursor_bridge`, `kando_bridge` — yürütme, onay kuyruğu | Hedef: seçilen araca delegasyon hattı; tek başına koordinatör değil |
| **Çok-ajan kuralları** | Rol sırası, rol kapma yasağı, CI teşhis zinciri | Hedef: alt iş rol bazlı; agent-to-agent komut yok ([ADR-008](../decisions/ADR-008-agent-network-boundary.md)) |
| **Yetki matrisi** | `task_engine/profiles.py` — 🟢 Oku · 🟡 Öner · 🟠 Yürüt · 🔴 Kritik onay (LUMOS-0008) | Hedef: her yönlendirme ve delegasyon bu matristen geçer; yetki emanet |
| **Model orkestrasyonu** | LUMOS-0017 — görev bazlı model/ajan seçimi, gerekçe kaydı | Hedef: hangi motor seçildiyse **neden** kayıtlı; model arka planda kalabilir |
| **Bağımsız denetim** | ADR-008 — kör inceleme, orkestratör tek hakem değil | Hedef: kritik adımda ikinci kanıt veya kullanıcı onayı |
| **Denetim zinciri** | LUMOS-0016 — kurul sentezi, kanıt zinciri | Hedef: seçim ve sonuç bağımsız doğrulanabilir |

---

#### Akış iskeleti (M0)

**niyet → orkestratör → araç seçimi → yürütme → Karar Duvarı kaydı → 🟢 / 🟡 / 🔴 özet**

```
Kullanıcı niyeti
    → Lumos Orkestratör (tek giriş — konduktör)
        → niyet ayrıştırma + risk / yetki kontrolü (fail-closed)
        → araç / ajan seçimi (LUMOS-0017 gerekçe)
        → yürütme (bridge proxy, görev motoru, dış araç)
        → bağımsız denetim (gerekirse — ADR-008 / LUMOS-0016)
        → Karar Duvarı / kayıt (seçim gerekçesi + sonuç özeti)
    → kullanıcıya kısa sonuç (🟢 / 🟡 / 🔴 format)
```

[Orkestrasyon / niyet akışı](#orkestrasyon--niyet-akışı-work--connectors-tohumu) ile hizalı: hazırlık → **🔴 açık onay** (dış etki) → uygulama.

---

#### İlkeler (hizalı — bağlayıcı değil)

| İlke | Kısa |
|------|------|
| **Hakem + yol arkadaşı** | Teşhis ve seçenek sunar; birlikte iş yapar; nihai karar kullanıcıda (LUMOS-0005) |
| **Yetki emanet** | Yetki matrisi her yönlendirmede; otomatik genişleme yok (LUMOS-0008) |
| **Karar Duvarı** | Seçim gerekçesi ve sonuç paylaşılan hafızada; yeni ajan bağlamı okur |
| **Model-agnostik** | Lumos = motor değil, orkestratör; gerekçe kayıtlı (LUMOS-0017) |
| **Fail-closed** | Emin değilse, yetki yoksa, onay yoksa — dur; boşluk doldurma yok |
| **Kısa cevap** | Varsayılan 🟢 Sonuç · 🟡 Alternatif · 🔴 Emin değilsem — [Cevap formatı](#cevap-formatı--önce-özet-detay-isteğe) |

**Örnek yönlendirme (tohum — bağlayıcı değil):**

| Kullanıcı niyeti | Lumos yönlendirmesi | Onay kapısı |
|------------------|---------------------|-------------|
| «Bu PR'ı incele» | GitHub + inceleme ajanı (ör. Codex) | Salt okuma — onay gerekmez |
| «Bu hatayı düzelt» | Cursor / kod ajanı | Değişiklik önizlemesi → kullanıcı onayı |
| «Bu kararı kaydet» | Karar Duvarı (`BACKLOG.md`) | Açık komut — kalıcı kayıt kapısı |
| «Güvenlik bültenini değerlendir» | Araştırma ajanı + mimari eşleme | Öneri paketi → kullanıcı kararı |

**Anti-pattern:** Lumos = tek model wrapper; kullanıcı her aracı ayrı açar; orkestratör kendi çıktısını denetlemez; seçim gerekçesi kayıtsız; agent-to-agent komut zinciri.

---

#### Kapsam dışı (M0 — açık)

**Kapsam dışı:** kod, PR, implementasyon planı — yalnızca vizyon tohumu.

- Kod, modül, API, PR, migration
- Uygulama planı, sprint, milestone taahhüdü
- Production multi-agent orchestration (public sınır dışı — ADR-008)
- Yeni `LUMOS-*` kaydı — mezuniyet kontrol listesi geçmeden BACKLOG'a taşınmaz

**Çapraz referans:**

- [Orkestrasyon / niyet akışı](#orkestrasyon--niyet-akışı-work--connectors-tohumu) — niyet → hazırlık → onay → uygulama.
- [Karar Duvarı / paylaşılan proje hafızası](#karar-duvarı--paylaşılan-proje-hafızası) — `LUMOS-*` bağlam hafızası.
- [Bootstrap / orkestrasyon — «Lumos'u aç»](#bootstrap--orkestrasyon--lumosu-aç) — tutarlı başlangıç durumu.
- [`knowledge-repository-lifecycle.md`](../knowledge-repository-lifecycle.md) — M0 = Concept.
- [`ADR-008`](../decisions/ADR-008-agent-network-boundary.md) — parçalı hatlar, hedef orkestratör rolü.
- [`BACKLOG.md` — LUMOS-0017](./BACKLOG.md) — model bağımsızlığı.
- [`BACKLOG.md` — LUMOS-0005](./BACKLOG.md) — hakem modeli.
- [`BACKLOG.md` — LUMOS-0008](./BACKLOG.md) — L0 yetki matrisi.
- [`BACKLOG.md` — LUMOS-0016](./BACKLOG.md) — denetim zinciri.

### Bilgi odağı — sinyal, gürültü değil

- Lumos, bilgiye ulaşmanı değil; **gerçekten ihtiyacın olan bilgiye** ulaşmanı hedefler. Geri kalan gürültüyü filtreler.
- Durum: ⚪ çekmece · **M0–M1** tohum — gereksiz enerji/sohbet gürültüsü ile «emin değilsem konuşmam» ilkesiyle hizalı; Karar Duvarı kaydı değil.


### Cevap formatı — önce özet, detay isteğe

- Lumos yanıtları varsayılan olarak **karar özeti** verir; uzun anlatım gürültü sayılır.
- Durum: ⚪ çekmece · **M0–M1** karakter/UX tohumu; Karar Duvarı (`LUMOS-*`) kaydı değil.

**Varsayılan format (3–5 satır):**

- 🟢 **Sonuç:** En olası neden (veya «%70 A çünkü…»)
- 🟡 **Alternatif:** İkinci olası neden (varsa; veya «%30 B çünkü…»)
- 🔴 **Emin değilsem:** «Kanıt yetersiz.» (+ iki olasılık listesi kısa, ilk kontrol satırı)

**Genişletme kuralı:** Detay yalnızca kullanıcı «Aç.» veya ayrıntı istediğinde; baştan 20 paragraf yok.

**İlke:** Kullanıcı karar verecek bilgiyi ister; tüm ihtimalleri anlatmak gereksiz uzatma. [Bilgi odağı — sinyal, gürültü değil](#bilgi-odası--sinyal-gürültü-değil) ile hizalı; [`BACKLOG.md` — LUMOS-0005](./BACKLOG.md) belirsizlik / ikilem açık tutma ruhu (bu madde yeni `LUMOS-*` kaydı değil).

**Örnek (kısa — tarayıcı vs güvenlik anahtarı):**

> 🟢 **Sonuç:** %70 tarayıcı oturumu/çerez — yan sekmede eski oturum hata üretiyor olabilir.
> 🟡 **Alternatif:** %30 Lumos Key doğrulaması düşmüş — yeniden kilitle/aç gerekebilir.
> 🔴 **Emin değilsem:** Kanıt yetersiz; önce gizli pencerede dene, sonra Key durumuna bak.

### Güvenlik ve AI güvenliği — konuşma filtresi (varsayılan)

- Durum: ⚪ çekmece · **M0–M1** tohum — ajan varsayılan davranış tohumu; haber/sohbette savunma odağı ve güvenlik sınırı. Karar Duvarı (`LUMOS-*`) kaydı değil.

**🟢 Konuşulabilir:** yeni savunma teknikleri, güvenlik mimarileri, AI güvenliği, OSS araçlar, akademik araştırma, güvenlik kültürü/süreç, zafiyet neden/önleme

**🟡 Dikkatli:** yeni yamalanmamış kritik açıklar, saldırı zinciri ayrıntıları, kötüye kullanılabilir otomasyon fikirleri — yanıt: «Bu haber savunma açısından önemli. Ayrıntısına girmeyelim; alınması gereken ders şu...»

**🔴 Konuşulmaz:** adım adım saldırı, malware geliştirme ayrıntıları, kimlik avı/hesap ele geçirme uygulanabilir içerik, gerçek sistemlere zarar kolaylaştıran bilgi — yanıt: «Bunu okudum. Lumos açısından ders var ama teknik ayrıntısını konuşmamız doğru olmaz. Sadece savunma tarafını özetleyeceğim.»

**İlke:** Haberde asıl değer «bundan ne öğreniyoruz, Lumos'ta ne yapmalıyız?» — saldırı ayrıntısı değil; zaman tasarrufu + güvenlik sınırı.

**Çapraz referans (tek satır):** [Güvenlik istihbaratı → Lumos aksiyon katmanı](#güvenlik-istihbaratı--lumos-aksiyon-katmanı-security-intelligence--lumos-action-layer), [Bilgi odağı — sinyal, gürültü değil](#bilgi-odası--sinyal-gürültü-değil), [`BACKLOG.md` — LUMOS-0014](./BACKLOG.md) güvenilmeyen dış veri sınırı ruhu.


### Deneyim Katmanı (Experience Layer)

> **Deneyim, «doğru» demek değildir; «yaşandı ve öğrenildi» demektir.**

- Durum: ⚪ çekmece · faz tohumu **M0–M1** — production Knowledge Repository değil; vizyon tohumu. Karar Duvarı (`LUMOS-*`) kaydı değil.
- Hafıza **dogma deposu değil**, **deneyim deposudur** — «Eskiden böyleydi, hâlâ böyledir» refleksi en büyük tehlikelerden biridir.
- «Lumos, haber tüketmez; deneyim biriktirir» ilkesi — bkz. [Güvenlik istihbaratı → Lumos aksiyon katmanı](#güvenlik-istihbaratı--lumos-aksiyon-katmanı-security-intelligence--lumos-action-layer) (bu çekmece).

**MCP 2026 örneği (tohum):** 2026'da eklenen bir kural yalnızca «MCP riski vardı» diye sonsuza dek kutsal sayılmaz; kayıt şöyle yaşar: «2026 MCP riski nedeniyle eklendi; güncel sürümde zorunlu olmayabilir — yeniden değerlendirilsin.»

**Benzetme:** Yama görmüş lastik — yol alır, ama her yama «orijinal lastik» iddiasını taşımaz; ne zaman değişeceği kayıtlı olmalıdır.

**Kayıt alanları (vizyon tohumu — lifecycle Review Date / Supersedes ruhu):**

| Alan | Soru |
|------|------|
| Kural | Ne eklendi / ne değişti? |
| Neden eklendi? | Hangi risk veya ihtiyaç? |
| Hangi olay tetikledi? | Olay, bülten, olay kaydı |
| Son doğrulama tarihi | En son ne zaman test edildi / doğrulandı? |
| Hâlâ geçerli mi? | Evet / belirsiz / hayır |
| Yeniden değerlendirme önerisi | Sonraki gözden geçirme veya supersede notu |

**İsimlendirme notu:** İleride «Knowledge Repository» yanında veya yerine **«Deneyim Katmanı»** dili kullanılabilir; bu çekmece maddesi [`docs/knowledge-repository-lifecycle.md`](../knowledge-repository-lifecycle.md) v1.0 belgesini yeniden adlandırmaz — yalnızca uzun vadeli vizyon tohumudur. Lifecycle'daki **Review Date** ve periyodik **gözden geçirme** ruhu buradaki «Son doğrulama» / «Hâlâ geçerli mi?» alanlarıyla hizalıdır.

**Çapraz referans:**

- [Bilgi odağı — sinyal, gürültü değil](#bilgi-odası--sinyal-gürültü-değil) — deneyim, gürültüyü değil öğrenilen dersi biriktirir.
- [`docs/knowledge-repository-lifecycle.md`](../knowledge-repository-lifecycle.md) — Review Date, gözden geçirme disiplini (v1.0; bu dosyada rename yok).

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

### Güvenlik istihbaratı → Lumos aksiyon katmanı (Security Intelligence → Lumos Action Layer)

> **Lumos haber takip etmez; haberden savunma üretir.**

**İlke:** «Lumos, haber tüketmez; deneyim biriktirir.»

**Kontrast (tohum):**

- Klasik: haber → oku → unut
- Bir tık iyi: haber → özetle → kaydet
- Lumos: haber → etki? → katman? → ADR/test/kural önerisi

**Sabah brifingi (vizyon tohumu):** 17 haber akışından 14'ü gürültü olarak elenir, 2'si izlemeye alınır, 1'i doğrudan ilgilidir; kullanıcı 17 makale okumaz — tek karar paketi görür: önerilen aksiyonlar (ör. ADR-008, MCP Trust Preflight, connector testi).

**Odak:** «Alakasız şeylerden uzak tut» / bilgi odağı ilkesi — bkz. [Bilgi odağı — sinyal, gürültü değil](#bilgi-odası--sinyal-gürültü-değil) (bu çekmece).

- Durum: ⚪ çekmece · faz tohumu **M0–M1** — production özellik değil; Research Memory vizyon tohumu. Karar Duvarı (`LUMOS-*`) kaydı değil.

**Akış (tohum):**

1. **Kaynak izleme** — tl;dr sec, OpenAI, MCP, Microsoft, GitHub, CVE, vendor blog, bülten
2. **Sınıflandırma** — bizi ilgilendiriyor mu? connector / agent / auth / secret / prompt injection
3. **Mimari eşleme** — örn. MCP → Connector Layer, Trust Preflight, Permission Chain, Log Redaction
4. **Aksiyon** — ADR güncelle, test ekle, env default, connector sandbox; yalnızca **öneri**; otomatik uygulama yok
5. **Gürültü eleme** — yalnızca kırmızı risk, mimari etki, savunma fikri, Lumos dersi

**Çapraz referans:**

- Bilgi odağı / sinyal ilkesi — gürültü değil, mimariye indirgenmiş savunma sinyali.
- [`BACKLOG.md` — LUMOS-0013](./BACKLOG.md) — external validation, güvenlik mimarisi teması.
- [`BACKLOG.md` — LUMOS-0014](./BACKLOG.md) — untrusted data / dış veri sınırı.

---

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

*Son güncelleme: 2026-07-04 · Belge durumu: TASLAK / çekmece*
