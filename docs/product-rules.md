# Ürün kuralları — kalıcı repo kaydı

**Durum:** Aktif referans belgesi (kod değildir).  
**Üst sınır:** `docs/lumos-karar-sozlesmesi.md`  
**Genişletilmiş canonical:** `docs/memory/product-rules.md`, `docs/memory/ui-chat-experience.md`, `docs/memory/voice-media-experience.md`

Bu dosya, sohbet/bellek kaybına karşı repo içinde kalıcı tutulan **ürün kuralları ve notları** özetidir. Kod veya test değiştirmez.

---

## Kaynak ve öncelik

| Kaynak | Rol |
|--------|-----|
| `docs/lumos-karar-sozlesmesi.md` | Bağlayıcı çekirdek sözleşme |
| `docs/product-rules.md` (bu dosya) | Ürün kuralları — hızlı erişim özeti |
| `docs/memory/*.md` | Detaylı canonical kayıtlar |
| ChatGPT Saved Memories | **Canonical değil** — yalnızca geçici referans |

---

## Ürün ilkeleri

| # | Madde | Statü |
|---|--------|--------|
| PR-001 | Lumos, kullanıcıya açık **tek dış yüzey**dir. | **aktif kural** |
| PR-002 | Gerçek ürün tarafında son kullanıcı **Kando / Cando / Bando** görmez; bunlar iç katmanlardır. | **aktif kural** |
| PR-003 | Lumos, kullanıcı ile dış dünya arasında **güvenli geçit ve orkestratör** olarak çalışır. | **aktif kural** |
| PR-004 | İç katmanlar dışarıdan komut veya veri **doğrudan kabul etmez**; akış Lumos geçidinden geçer. | **aktif kural** |

---

## Kullanıcıya görünen dil ve kimlik

| # | Madde | Statü |
|---|--------|--------|
| PR-010 | Product UI ve mesajlarda «Kando'ya ilettim», «ajan», «başka AI» gibi **iç katman adları** görünmez. | **aktif kural** |
| PR-011 | Yanıt ve arayüz yalnızca **Lumos kimliği** ile sunulur. | **aktif kural** |
| PR-012 | Dış etkili veya geri dönüşsüz işlemler (ödeme, domain, kalıcı silme, e-posta vb.) kullanıcı onayı olmadan başlatılmaz. | **aktif kural** |

---

## Lumos'un kullanıcıyla ilişkisi

| # | Madde | Statü |
|---|--------|--------|
| PR-020 | Lumos, kullanıcıdan ayrı bir varlık gibi değil; kullanıcının **dijital uzantısı** ve cihazın **akıllı katmanı** olarak ele alınır. | **ürün notu** |
| PR-021 | Lumos kullanıcıdan bağımsız sahiplik kurmaz. | **aktif kural** |
| PR-022 | Lumos, cihazın akıllı koordinasyon katmanıdır; kullanıcı adına koordine eder, sahip olmaz. | **aktif kural** |

---

## Veri sahipliği ve taşıma

| # | Madde | Statü |
|---|--------|--------|
| PR-030 | **Kullanıcı verisinin sahibi kullanıcıdır.** Lumos, kullanıcıyı ve cihazı temsil eden kontrollü katmandır. | **aktif kural** |
| PR-031 | Veri taşıma ve dış paylaşım **açık onay** gerektirir. | **aktif kural** |
| PR-032 | Diğer platformlardaki kişisel veriler ileride Lumos çatısı altındaki **güvenli kasaya** taşınabilir; yalnızca **izinli, şeffaf, geri alınabilir ve kullanıcı kontrollü** olacak. | **ileride değerlendirilecek** |
| PR-033 | Silinen içerik kalıcı yok edilmez; trash/silinen alana taşınır (çekirdek sözleşme ile uyumlu). | **aktif kural** |

---

## Panel tonu ve sohbet deneyimi

| # | Madde | Statü |
|---|--------|--------|
| PR-040 | Lumos panel tonu genel asistan gibi değil; **cihazın kendi sistemi** gibi olacak — yerel, pratik, sade öneriler. | **ürün notu** |
| PR-041 | Doğal, pratik, cihaz-yerel ton; generic güvenlik boilerplate'ten kaçınılır. | **ürün notu** |
| PR-042 | Panel sohbet girişinde uzun kullanıcı mesajı sağa **taşmayacak**; giriş alanı uzun metni **sarmalayacak** veya çok satırlı textarea gibi büyüyüp kaydıracak. | **takip maddesi** |
| PR-043 | Uzun mesajlar gizlenmemeli; gerekirse iç scroll ile okunabilir kalmalı. | **takip maddesi** |

---

## Ses ve yazı sürekliliği

| # | Madde | Statü |
|---|--------|--------|
| PR-050 | Sesli ve yazılı mod **birbirinden kopuk çalışmayacak**; ses modu yazılı görev motoruna bağlı giriş/geri bildirim katmanı gibi tasarlanacak. | **ürün notu** |
| PR-051 | Sesli konuşma metne çevrildikten sonra bağlam, niyet, güvenlik sınırı ve önceki kararlarla **tutarlılık kontrolünden** geçecek. | **ürün notu** |
| PR-052 | Ses modu ayrı sohbet kanalı değildir; görevler modlar arası süreklilik taşır. | **ürün notu** |

---

## CI / kapsam dışı bırakılan ürün maddeleri

Aşağıdaki maddeler CI veya public sınır nedeniyle ertelendi veya taşındı; **kaybolmaz**.

| ID | Madde özeti | Statü | Not |
|----|-------------|--------|-----|
| PR-D01 | Ödeme / PSP tam entegrasyonu | **geçici ertelendi** | Şirket yapısı netleşene kadar — bkz. `docs/memory/commercial-domain-payments.md` |
| PR-D02 | Chat içi image generation kapsamı | **ileride değerlendirilecek** | OD-013 — `docs/memory/ui-chat-experience.md` |
| PR-D03 | Vault UX detay metinleri | **ileride değerlendirilecek** | OD-023 — şifreleme/vault spec ayrı belgede |

---

## İlişkili belgeler

- `docs/security-architecture.md` — gizli bilgi ve kasa ilkeleri
- `docs/project-map.md` — dizin ve runtime haritası
- `docs/decision-log.md` — karar ve erteleme günlüğü

---

Son güncelleme: 2026-06-17
