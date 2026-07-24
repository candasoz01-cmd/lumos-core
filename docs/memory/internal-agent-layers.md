# İç ajan katmanları — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından taşınan Lumos, Core, Local ve Sentinel **iç katman ayrımı**, görünmezlik ve güvenlik sınırı maddelerinin repo'ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir.

**Üst politika:** ChatGPT Saved Memories **canonical değildir**; `docs/memory/` **canonical'dır.** Çelişki varsa repo metni esas alınır.

**Çapraz referans ruhu:** [`product-rules.md`](./product-rules.md) (dış yüzey, kullanıcı deneyimi), [`security-architecture.md`](./security-architecture.md) (geçit, bridge, iç katman sınırı).

---

## Dış yüz ilkesi

| # | İlke | Not |
|---|------|-----|
| 1 | Gerçek üründe son kullanıcı **Core'u görmez**. | Taşındı |
| 2 | Dışa açık tek yüzey **Lumos**'tur. | Taşındı |
| 3 | Local ve Core **iç çalışma/uygulama katmanları** olarak arka planda kalır. | Taşındı |
| 4 | Normal kullanımda kullanıcı yalnızca **Lumos** ile etkileşir. | Taşındı |
| 5 | Core'ya iş aktarımı **iç çalışma prensibi**dir; dışa yansıtılmaz. | Taşındı |

---

## İç katman görünmezliği

Ürün arayüzü ve mesajları iç katmanları kullanıcıya açmaz.

| # | Kural | Yasak örnek (ürün metni) | Not |
|---|--------|---------------------------|-----|
| 1 | İç katman adları kullanıcıya gösterilmez. | "Core'ya ilettim", "ajana yönlendirdim" | Taşındı |
| 2 | Başka AI / ajan varlığı ima edilmez. | "başka AI", "ajan", "iç sistem" | Taşındı |
| 3 | Kullanıcı yalnızca Lumos'un işi aldığını / başlattığını / tamamladığını görür. | — | Taşındı |

**Özet:** Kullanıcı dili her zaman Lumos merkezlidir; iç orkestrasyon şeffaf değildir.

---

## Komut ve veri akışı

| # | Kural | Not |
|---|--------|-----|
| 1 | Core, Local ve Sentinel dış kaynaklardan veya diğer kaynaklardan **doğrudan komut, dosya veya veri kabul etmez**. | Taşındı |
| 2 | Tüm akış **yalnızca Lumos geçidi** üzerinden yönlendirilir. | Taşındı |
| 3 | Bypass veya doğrudan iç katman erişimi mimari ihlal sayılır. | Taşındı |
| 4 | İç AI / ajan katmanları birbirine **doğrudan görev vermez**; yalnızca denetim, itiraz, rapor ve alternatif öneri üretebilir. | Karşılıklı denetim, sıfır kontrol |
| 5 | Lumos AI Kurulu varsa icra makamı değil, bağımsız denetim modelidir; son karar Lumos Orkestratör veya kullanıcıdadır. | Bağımsız düşün, ortak değerlendir |

**Akış özeti:**

```
Dış dünya / kullanıcı → Lumos (geçit) → [doğrulanmış iç iletişim] → Core / Local / (Sentinel)
```

İç katmanlar birbirine veya dışa Lumos bypass etmeden bağlanmaz. Yatay iç katman iletişimi kontrol, görev atama, onay veya yetki aktarımı yapamaz.

### Karşılıklı denetim, sıfır kontrol

İç AI / ajan katmanları birbirinin çıktısını okuyabilir, hata bulabilir, risk raporu yazabilir, itiraz edebilir ve alternatif çözüm önerebilir. Ancak birbirine görev veremez, birbirinin yetkisini artıramaz, ayarını değiştiremez, onayını veremez veya adına işlem başlatamaz.

Her iç AI yalnızca kullanıcıdan veya Lumos Orkestratör'den görev alır. Başka bir AI'dan doğrudan görev kabul etmek mimari ihlaldir.

```
Kullanıcı
    |
    v
Lumos Orkestratör
    |-- Chat AI
    |-- Cyber AI
    |-- Mail AI
    |-- Lab AI
    `-- ...
```

Yatay ok yoktur; ihtiyaç varsa Lumos çekirdeği isteği değerlendirir ve güvenlik, yetki, trust ve onay kontrollerinden sonra ilgili iç katmana yönlendirir.

### Lumos AI Kurulu

Lumos AI Kurulu, iç ajanların veya farklı AI perspektiflerinin aynı çıktıyı bağımsız incelemesi için kullanılır. Kurul üyeleri birbirini etkilemeye, yönetmeye veya talimatlandırmaya çalışmaz; yalnızca kendi risk, itiraz, gerekçe ve alternatif önerisini üretir.

Denetim bağımsız olmalıdır. Bir AI, değerlendirmesini başka bir AI'ın sonucuna göre değil, kendi gözlem ve kanıtına göre oluşturur. Başka bir AI'ın sonucu tek başına kanıt sayılmaz; ortak değerlendirmede yalnızca karşılaştırma girdisi olabilir.

Varsayılan kurul akışı kör incelemedir: aynı kanıt paketi ilgili AI'lara gider, her AI diğer AI sonuçlarını görmeden bağımsız rapor üretir, raporlar kilitlenir ve ortak değerlendirme yalnızca kilitli raporlar üzerinden yapılır. Lumos Orkestratör veya kullanıcı nihai kararı verir.

Örnek kurul rolleri:

| Üye / perspektif | Beklenen katkı | Yapamaz |
|------------------|----------------|---------|
| Diamond | Risk ve açık adaylarını bulur | Başka AI'a düzeltme emri veremez |
| ChatGPT | Riski bağımsız değerlendirir | Başka AI adına onay veremez |
| Claude | Mantık ve mimari tutarlılığı sorgular | Yetki, ayar veya işlem başlatamaz |
| Diğer ajanlar | Tanımlı uzmanlık alanında görüş üretir | Lumos Orkestratör dışı görev alamaz |

Son söz Lumos Orkestratör veya kullanıcıdadır. Kurul çıktısı tek başına icra izni değildir.

---

## Katman görev ayrımı

Lumos, Core, Local ve Sentinel **görev alanları karıştırılmaz.**

| Katman | Rol (özet) | Dışa görünür mü |
|--------|------------|-----------------|
| **Lumos** | Kullanıcıya açık yüzey; güvenli geçit ve orkestratör | Evet |
| **Core** | İç çalışma / koordinasyon katmanı | Hayır |
| **Local** | İç uygulama / iş yürütme katmanı | Hayır |
| **Sentinel** | Ayrı katman olarak tanımlanırsa: güvenlik/gözlem (bkz. §6) | Hayır |

| # | Kural | Not |
|---|--------|-----|
| 1 | Bir katmanın görevi diğer katmana taşınmaz (rol kayması yok). | Taşındı |
| 2 | Ürün, panel ve mesajlarda katmanlar birleştirilerek sunulmaz. | Taşındı |
| 3 | İç katmanlar kullanıcı adına tek "Lumos" deneyimi olarak paketlenir. | Taşındı |

---

## Sentinel güvenlik notu

Sentinel ayrı bir katman olarak varsa **sıradan görev ajanı değildir**; özel güvenlik / izleme rolü taşır.

| # | İlke | Not |
|---|------|-----|
| 1 | Sentinel **doğrudan girdi kabul etmez**. | Taşındı |
| 2 | Dış kaynaktan Sentinel'a komut = **güvenlik olayı** (incident). | Taşındı |
| 3 | Rol: gözlem, analiz, anomali tespiti, Lumos'a raporlama. | Taşındı |
| 4 | Sentinel **yürütme / komut katmanı değildir**; iş başlatmaz, kullanıcı adına aksiyon almaz. | Taşındı |
| 5 | Sentinel'in ayrı katman olarak varlığı ve sınırları | decision-approved / implementation-pending — [`internal-communication-sentinel-decision.md`](./internal-communication-sentinel-decision.md); OD-006 |

---

## İç iletişim doğrulama

Lumos'tan iç katmanlara giden iletişim de güven sınırında tutulur.

| # | İlke | Not |
|---|------|-----|
| 1 | İç iletişim **doğrulanmalı**; tercihen imzalı ve/veya şifreli. | Taşındı |
| 2 | İmzalama protokolü, anahtar döngüsü ve şifreleme detayı | decision-approved / implementation-pending — OD-007; protokol private katmanda |
| 3 | Doğrulanmamış veya yetkisiz iç mesaj reddedilir / olay kaydı oluşturulur. | Taşındı — operasyonel prosedür OD-026 needs-review |

**Referans ruhu:** [`security-architecture.md`](./security-architecture.md) — bridge ve token ilkeleri; iç protokol detayı gizli kalır.

---

## Public anlatım sınırı

| # | Kural | Not |
|---|--------|-----|
| 1 | İç katman varlığı public açıklamada **ayrıntılandırılmayabilir**. | Taşındı |
| 2 | Güvenlik hassas konular gizli kalır: iç protokol, doğrulama, anahtarlar, savunma akışları. | Taşındı |
| 3 | Public `lumos-core` içeriği demo-safe ve sınır uyumlu olmalıdır. | Taşındı — public-github sınırı |

Dış dünyaya anlatım: Lumos kullanıcıya açık, güvenli asistan/geçit; iç mimari detay paylaşılmaz.

---

## Riskler

| # | Risk | Azaltma (özet) | Not |
|---|------|----------------|-----|
| 1 | İç katman adının UI/mesajda sızması | Metin ve panel kuralları; yalnızca Lumos dili | Taşındı |
| 2 | Lumos geçidi bypass | Mimari red; güvenlik olayı prosedürü | Taşındı |
| 3 | Rol kayması (ör. Sentinel yürütme) | Katman görev ayrımı; kod ve politika denetimi | Taşındı |
| 4 | İç iletişimde zayıf doğrulama | İmza/şifreleme tercihi — OD-007 implementation-pending |
| 5 | Public dokümanda iç protokol sızıntısı | Public anlatım sınırı; hassas detay ayrı kanal | Taşındı |
| 6 | Sentinel kapsamının belirsizliği | OD-006 karar onaylı; dağıtım modeli implementation-pending |

---

## Migration tablosu

ChatGPT Saved Memories / oturum bağlamından bu dosyaya taşınan maddeler.

| # | Kaynak özeti | Hedef bölüm | Durum |
|---|--------------|-------------|--------|
| 1 | Kullanıcı Core görmez; yalnızca Lumos dış yüzey | §2 Dış yüz ilkesi | Taşındı |
| 2 | UI'da "Core'ya ilettim", "ajan", "başka AI" yok | §3 İç katman görünmezliği | Taşındı |
| 3 | Kullanıcı Lumos aldı/başlattı/tamamladı görür | §3 İç katman görünmezliği | Taşındı |
| 4 | İç katmanlar dıştan doğrudan komut/veri almaz | §4 Komut ve veri akışı | Taşındı |
| 5 | Akış yalnızca Lumos geçidi | §4 Komut ve veri akışı | Taşındı |
| 6 | Lumos→iç iletişim doğrulanmalı; imza/şifreleme tercihi | §7 İç iletişim doğrulama | Taşındı — OD-007 decision-approved / implementation-pending |
| 7 | Sentinel: güvenlik/izleme; doğrudan girdi yok; incident | §6 Sentinel güvenlik notu | Taşındı — OD-006 decision-approved / implementation-pending |
| 8 | Katman görev alanları karışmaz | §5 Katman görev ayrımı | Taşındı |
| 9 | Public'te iç katman/protokol detayı yok | §8 Public anlatım sınırı | Taşındı |
| 10 | ChatGPT memory canonical değil; docs/memory canonical | Amaç / üst politika | Taşındı |
| 11 | İç AI'lar birbirini denetleyebilir ama kontrol edemez; görev yalnızca kullanıcı veya Lumos Orkestratör'den gelir | §4 Komut ve veri akışı | Taşındı |
| 12 | Lumos AI Kurulu bağımsız denetim modelidir; son karar Lumos Orkestratör veya kullanıcıdadır | §4 Komut ve veri akışı | Taşındı |

Durum tanımları: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Manuel eklenecek maddeler

Aşağıya ChatGPT Saved Memories veya oturum notlarından henüz işlenmemiş maddeler yapıştırılır. Taşıma tamamlanınca ilgili bölüme taşınır ve durum güncellenir.

| # | Durum | Kaynak metni (yapıştır) | Hedef bölüm | Not |
|---|--------|-------------------------|-------------|-----|
| 1 | `[queued]` | | | |
| 2 | `[queued]` | | | |
| 3 | `[queued]` | | | |
| 4 | `[queued]` | | | |
| 5 | `[queued]` | | | |

---

*Son güncelleme: 2026-07-03 (Lumos AI Kurulu bağımsız denetim ilkesi eklendi)*

---

## Legacy Naming

Eski iç katman adları (**Kando**, **Cando**, **Bando**) emeklidir. Güncel adlar: **Core**, **Local**, **Sentinel**.

Tarihçe ve teknik tanımlayıcı listesi: [`legacy-naming.md`](./legacy-naming.md). Karar: [`ADR-018`](../decisions/ADR-018-internal-layers-core-local-sentinel.md) · OD-061.

Bu bölüm dışında legacy katman adları kullanılmaz.

