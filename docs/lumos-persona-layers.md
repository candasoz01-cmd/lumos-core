# Lumos Persona Katmanları (Kısa Not)

| Alan | Değer |
|------|-------|
| Durum | **Referans notu** — kod taşıması yok; persona ve güven sınırı tanımı |
| Tarih | 2026-06-07 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, [ADR-008](decisions/ADR-008-agent-network-boundary.md), [ADR-010](decisions/ADR-010-guard-policy-trust-terminology.md) |

## Ana mimari

Lumos, Core ve Local **bağlı katmanlardır** — ayrı rakip ürünler veya bağımsız runtime isimleri değildir. Tek sistem; dışa Lumos, içe Core, operasyonel rutinlerde Local.

```
[Dış dünya] → Lumos (gateway, koruma, iletişim)
                  ↓ doğrulanmış kanal
              Core (bağlam, niyet, karar, yerel kontrol)
                  ↓ read-only rutinler
              Local (recipe / runbook — branch cleanup, pr-ready-check vb.)
```

---

## Katman rolleri

### Lumos

Kullanıcıya dönük **güvenlik, iletişim ve dış gateway** katmanı. Korur ve iletişim kurar; dış dünyayla tek kontrollü yüzey. İç katmanlara (Core, Local) giden iş yalnızca Lumos üzerinden ve doğrulanmış kanaldan geçer.

### Core

**Derin bağlam, karar, niyet analizi** ve **yerel/kişisel kontrol çekirdeği**. Düşünür ve yönetir; görev motoru, planlama, profil/onay sınırları bu tarafta. Local rutinleri Core tarafında çalışır — Local ayrı bir “dördüncü ürün” veya köprü/runtime adı değildir.

### Local

**Salt okuma yerel recipe / runbook** katmanı. Örnekler: branch cleanup incelemesi, pr-ready-check. Operasyonel rutinler; state’e yazmaz, dış etki üretmez. Core’nun altında tanımlı, tekrarlanabilir kontrol listeleri — bridge veya execution katmanının rakip adı olarak kullanılmaz.

### Sentinel (ileride, yalnızca gerekirse)

**Mevcut modelde execution veya ajan katmanı değildir.** İleride ihtiyaç doğarsa: özel **güvenlik / anomali gözlem** katmanı.

- Dış komut, iş, dosya veya veri **kabul etmez** — doğrudan giriş yok.
- Yalnızca gözlem, analiz, anomali tespiti; rapor **Lumos’a**.
- Sentinel’ya dışarıdan iletişim veya komut girişimi = **güvenlik olayı** → koruma modu.

---

## Güven sınırları (trust boundaries)

Core ve Local doğrudan dış komut, iş, dosya veya veri kabul etmez; bu girişler yalnızca doğrulanmış Lumos kanalı üzerinden alınır — Sentinel varsa ona doğrudan giriş de güvenlik olayı sayılır.

| Kural | Açıklama |
|-------|----------|
| **Tek giriş: Lumos** | Core ve Local işi **yalnızca doğrulanmış Lumos kanalından** kabul eder. |
| **Local read-only** | Recipe/runbook çıktısı öneri veya rapor; otomatik yazma veya dış aksiyon yok. |
| **Sentinel izole** | Varsa yalnızca iç sinyal okur; dış yüzey yok. |
| **Public sınır** | Bu not public foundation kapsamındadır; prod orchestration private katmanda (ADR-008, public-github-boundary). |

---

## Offline çalışma prensibi

Offline modda da **Lumos tek kullanıcı ve dış yüz** kalır; dış dünyaya çıkış yalnızca Lumos üzerinden ve açık onayla olur.

- **Core / Local:** Yalnızca **cihaz içi** ve **izinli yerel kaynaklarla** çalışır; dış ağ, bulut veya doğrudan dış komut yok.
- **Local (offline):** Read-only yerel kontrol yapabilir (ör. yerel repo/dosya incelemesi). PR, CI veya bulut gerektiren kontrollerde **“online gerekir”** raporu verir; otomatik dış aksiyon yok.
- **Sentinel (varsa, offline):** Cihaz içi **anomali gözlem** katmanı olarak çalışabilir; komut çalıştırmaz, dışarıdan iş veya veri kabul etmez, yalnızca **Lumos’a** raporlar.
- **Kuyruk ve senkron:** Offline’da bekleyen işler internet gelince **otomatik dışarı gönderilmez**. Senkron, push, PR, mail, bulut veya API işlemleri için **Lumos doğrulaması ve kullanıcı onayı** gerekir.

---

## Secret / hassas bilgi taşıma prensibi

Lumos **tek dış geçittir**; şifre, token ve gizli kullanıcı bilgileri için **ana depo değildir**. Hassas bilgiler mümkün olduğunca **ayrı güvenli katmanda** veya **ilgili iç bileşende** tutulur.

- **Erişim:** Lumos, gerektiğinde yalnızca **amaç bazlı, sınırlı ve doğrulanmış** erişim ister; geniş veya kalıcı sır toplama hedeflenmez.
- **Sonuç odaklı iletişim:** Mümkün olduğunca Lumos **sırrın kendisini değil**, yetkili işlemin **sonucunu** alır (ör. “bağlantı başarılı”, “işlem reddedildi”).
- **Risk azaltma:** Tek noktada sır birikimi önlenir; Lumos ele geçirilse bile tüm hassas bilgilerin açığa çıkması riski düşürülür.

Uygulama ayrı checkpoint; bu bölüm yalnızca persona ve sınır ilkesidir.

---

## Anti-Lumos taklit (iç iletişim ilkesi)

Lumos dışından veya Lumos’u taklit eden kaynaktan gelen iç mesajlar **güvenilir sayılmaz**.

**Hedef ilke (kısa):** Core ↔ Lumos (ve gerektiğinde Local) iç iletişimde **doğrulama, imzalama veya şifreleme** — kanal bütünlüğü; sahte Lumos veya sahte iç komut reddedilir. Uygulama ayrı checkpoint; bu belge yalnızca persona ve sınır tanımıdır.

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent ve kilit alanları dokunulmaz; bu not o sınırları gevşetmez.
