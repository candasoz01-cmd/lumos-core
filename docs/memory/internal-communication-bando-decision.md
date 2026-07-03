# Bando katmanı ve iç iletişim protokolü — onaylı karar (OD-006 / OD-007)

> **Uygulama durumu:** Karar onaylandı; uygulama başlamadı. Bu doküman kod değişikliği değildir. Mimari ve politika kararlarının canonical kaydıdır.

**Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, onay ve kalıcı silme kuralları bu taslağı gevşetemez.

**Kaynak canonical dosyalar:** [`internal-agent-layers.md`](./internal-agent-layers.md), [`security-architecture.md`](./security-architecture.md), [`product-rules.md`](./product-rules.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

---

## 1. Amaç

OD-006 (Bando katman varlığı) ve OD-007 (Lumos → iç katman iletişim protokolü) için **onaylı karar kaydı** tutmak.

Bu belge:

- Bando'nun varsa hangi rolde kalacağını,
- Lumos geçidi üzerinden iç katmanlara iletişim ilkelerini,
- doğrulama / imzalama / şifreleme sınırını (teknik detay olmadan),
- public anlatım ve güvenlik olayı sınırlarını

netleştirir. Uygulama, kod, test veya operasyonel protokol tanımı **bu belgenin kapsamı dışındadır**.

---

## 2. Kapsam dışı olanlar

| Alan | Neden kapsam dışı |
|------|-------------------|
| Kod, test, panel, bridge, API uygulaması | Bu belge yalnızca karar taslağıdır; uygulama başlamadı. |
| Gerçek anahtar, token, credential, imza örneği | Güvenlik ve public repo sınırı; canonical kayıtlara yazılmaz. |
| İmzalama/şifreleme algoritması, format, endpoint, path | OD-007 uygulama bekliyor; private/gizli uygulama paketinde netleştirilecek. |
| Bando operasyonel runbook'u | Olay kaydı prosedürü OD-026 ile örtüşür; detay sonra. |
| Kando / Cando görev dağılımı detayı | Bu taslak Bando ve iç iletişim geçidine odaklanır. |
| Vault, token entegrasyonu (OD-001 – OD-005) | İlgili ama ayrı karar paketi. |

---

## 3. Netleşen ilkeler

Aşağıdaki ilkeler **firm** (kaynak canonical dosyalar ve çekirdek sözleşme ile uyumlu); bu taslakta tekrar onaylanır.

| # | İlke | Kaynak ruhu |
|---|------|-------------|
| 1 | Dış kullanıcıya görünen **tek yüzey Lumos**'tur. | product-rules §1; internal-agent-layers §2 |
| 2 | Kando, Cando ve Bando **iç katmanlardır**; kullanıcıya ad veya arayüz olarak yansıtılmaz. | product-rules §2; internal-agent-layers §3 |
| 3 | İç katmanlar dış kaynaklardan **doğrudan komut, dosya veya veri kabul etmez**. | internal-agent-layers §4; security-architecture §3 |
| 4 | Tüm dış ↔ iç akış **yalnızca Lumos geçidi** üzerinden yönlendirilir; bypass mimari ihlaldir. | internal-agent-layers §4; product-rules §4 |
| 5 | Lumos'tan iç katmanlara giden iletişim **doğrulanmalıdır**; imzalama ve/veya şifreleme tercih edilir (onaylı ilke; teknik uygulama bekliyor). | internal-agent-layers §7 |
| 6 | Doğrulanmamış veya yetkisiz iç mesaj **reddedilir**; güvenlik olayı kaydı oluşturulması hedeflenir (operasyonel detay needs-review). | internal-agent-layers §7; OD-026 |
| 7 | Public `lumos-core` içeriği **demo-safe** kalır; iç protokol, anahtarlar ve savunma akışları public'e taşınmaz. | security-architecture §Public; internal-agent-layers §8 |
| 8 | Çekirdek güvenlik, yetki profilleri ve onay kuralları bu kararları gevşetemez. | lumos-karar-sozlesmesi §2 |
| 9 | İç AI / ajan katmanları arasında **karşılıklı denetim var, yatay kontrol yoktur**. | internal-agent-layers §4; ADR-008 |

---

## 4. Bando rol kararı

**Karar (onaylı):** Bando, **yalnızca** güvenlik, gözlem ve anomali tespiti için ayrı bir katman olarak kabul edilir. Sıradan görev ajanı değildir; yürütme yapmaz; kullanıcıya görünmez; dış kaynaktan doğrudan komut, veri veya dosya kabul etmez.

| Boyut | Tanım |
|-------|--------|
| **Amaç** | İç sistemde güvenlik sinyali, gözlem ve anomali tespiti; Lumos'a raporlama. |
| **Konum** | İç katman; dışa görünmez. Lumos geçidi dışından erişilemez. |
| **İlişki** | Kando (koordinasyon) ve Cando (uygulama/yürütme) ile **rol karışmaz**; Bando iş yürütmez. |
| **Girdi** | Yalnızca Lumos geçidi üzerinden gelen, doğrulanmış iç iletişim (ve tanımlı iç gözlem kanalları). |
| **Çıktı** | Güvenlik/anomali raporu, olay kaydı tetikleyicisi; kullanıcıya doğrudan yüzey sunmaz. |

**OD-006 durumu:** **decision-approved / implementation-pending.** Bando ayrı katman olarak onaylandı (rol ve sınır tanımı firm). Dağıtım modeli, edge-case senaryoları ve Kando/Cando sınır örnekleri uygulama detayı olarak bekliyor.

---

## 5. Bando'nun yapamayacakları

Bando aşağıdaki işleri **yapmaz**; yapması veya dıştan buna yönlendirilmesi politika ihlalidir.

| # | Yasak | Gerekçe |
|---|--------|---------|
| 1 | Kullanıcı adına uygulama çalıştırma, komut yürütme, dosya yazma | Yürütme katmanı Cando/Kando alanı; Bando yürütme değildir. |
| 2 | Dış dünyadan veya kullanıcıdan **doğrudan** komut, dosya, veri kabul etme | Tüm dış girdi Lumos geçidinden geçer. |
| 3 | Lumos geçidini bypass ederek iç katmanlara veya dışa bağlanma | Mimari ihlal; güvenlik olayı. |
| 4 | Kullanıcıya görünen yanıt, panel veya chat yüzeyi sunma | Tek dış yüzey Lumos. |
| 5 | Görev motoru / yetki profili kapsamında otonom “iş tamamlama” | Sıradan görev ajanı değildir. |
| 6 | Secret, token veya credential tutma/yüzeyleme | Vault ve kimlik katmanı ayrı karar (OD-001, OD-002). |
| 7 | Başka bir iç katmana doğrudan görev vermek, onay vermek, yetki artırmak veya işlem başlatmak | Karşılıklı denetim mümkündür; yatay kontrol yoktur. |

**Güvenlik olayı (firm):** Dış kaynaktan veya kullanıcı yüzeyinden Bando'ya doğrudan ulaşma girişimi **güvenlik olayı (incident)** olarak sınıflandırılır; reddedilir ve kayıt altına alınması hedeflenir.

---

## 6. Lumos geçidi ve iç iletişim akışı

### Akış özeti

```
Dış dünya / kullanıcı → Lumos (geçit, orkestratör) → [doğrulanmış iç iletişim] → Kando / Cando / Bando
```

### Kurallar

| # | Kural |
|---|--------|
| 1 | Kullanıcı ve dış entegrasyonlar yalnızca **Lumos** ile konuşur. |
| 2 | Lumos, iç katmana ileti göndermeden önce yetki, onay ve güven sınırı kontrollerini uygular (çekirdek sözleşme ile uyumlu). |
| 3 | İç katmanlar birbirine veya dışa **Lumos bypass etmeden** bağlanmaz. |
| 4 | Bridge (varsa) Lumos kontrollü dış kanaldır; iç katmanlara doğrudan köprü kurmaz. |
| 5 | Bando'ya giden trafik de aynı geçit ve doğrulama ilkesine tabidir; istisna yoktur. |
| 6 | İç katmanlar birbirinden doğrudan görev kabul etmez; yalnızca Lumos Orkestratör üzerinden yönlendirme yapılır. |
| 7 | İç katmanlar birbirinin çıktısını denetleyebilir, risk raporu ve itiraz üretebilir; kontrol, onay veya yetki aktarımı yapamaz. |

**Ürün dili:** Kullanıcı yalnızca Lumos'un işi aldığını, başlattığını veya tamamladığını görür; iç orkestrasyon şeffaf değildir.

---

## 7. Doğrulama / imzalama / şifreleme ilkesi

| # | İlke | Durum |
|---|------|--------|
| 1 | Lumos → iç katman mesajları **doğrulanmalıdır** (kaynak, yetki, bütünlük). | Firm |
| 2 | Mümkün olduğunda iletişim **imzalı ve/veya şifreli** tutulur. | İlke onaylı; **uygulama bekliyor** (OD-007) |
| 3 | İmzalama protokolü, mesaj formatı, anahtar döngüsü, vault entegrasyonu | **Uygulama bekliyor** — public repoda tanımlanmaz; private/gizli uygulama paketinde netleştirilecek |
| 4 | Doğrulama başarısız mesajlar işlenmez; reddedilir. | Firm |
| 5 | Anahtar ve credential'lar Lumos yüzeyinde açık tutulmaz; vault katmanı tercih edilir. | İlke; vault detayı OD-001 – OD-005 |

**OD-007 durumu:** **decision-approved / implementation-pending.** Lumos → iç katman iletişimi **doğrulanmalıdır**; imzalama ve/veya şifreleme tercih edilir (onaylı ilke). Protokol, mesaj formatı, anahtar döngüsü ve vault entegrasyonu public repoda tanımlanmaz; private/gizli uygulama paketini bekler.

---

## 8. Olay / anomali kaydı

| Olay türü | Beklenen tepki (ilke) | Detay durumu |
|-----------|------------------------|--------------|
| Lumos geçidi bypass girişimi | Red + güvenlik olayı kaydı | Operasyonel prosedür needs-review (OD-026) |
| Doğrulanmamış iç mesaj | Red + olay kaydı | Operasyonel prosedür needs-review (OD-026) |
| Dış kaynaktan Bando'ya doğrudan erişim | Red + güvenlik olayı (incident) | Firm sınıflandırma |
| Bando tarafından tespit edilen anomali | Lumos'a iç rapor; kullanıcıya Bando adıyla değil, Lumos diliyle (gerekirse) | UX ve log formatı needs-review |

Bu bölüm **politika özeti**dir; log şeması, saklama süresi ve alerting **uygulama aşamasında** ve gizli/operasyonel kanalda tanımlanır.

---

## 9. Public anlatım sınırı

| # | Kural |
|---|--------|
| 1 | Public `lumos-core` dokümantasyonunda iç katman varlığı **ayrıntılandırılmayabilir** veya yalnızca demo-safe özet düzeyinde anlatılır. |
| 2 | Public'e **yazılmaz:** iç iletişim protokolü, imza/şifreleme detayı, anahtarlar, savunma akışları, gerçek güvenlik olayı prosedürü. |
| 3 | Dış vitrin dili: Lumos, kullanıcıya açık güvenli asistan ve geçit; iç mimari “kutu” olarak kalır. |
| 4 | Bu karar taslağı public repoda **ilke düzeyinde** kalabilir; operasyonel veya üretim detayı içermez. |

Public boundary: [`security-architecture.md`](./security-architecture.md) §Public repo sınırları; workspace `public-github-boundary` kuralları.

---

## 10. Uygulama bekleyen detaylar

Onaylı karar sonrası **implementation-pending** kalan başlıklar:

| Konu | İlişkili OD | Not |
|------|-------------|-----|
| İmzalama protokolü ve mesaj formatı | OD-007 | Private/gizli uygulama paketi |
| Anahtar döngüsü ve vault entegrasyonu | OD-007, OD-001 – OD-005 | Vault kararlarına bağımlı |
| Bando dağıtım modeli (süreç/ortam ayrımı) | OD-006 | Rol onaylı; deploy şekli uygulama detayı |
| Bando ↔ Kando/Cando sınır örnekleri (senaryo listesi) | OD-006 | Rol tablosu yeterli; edge case listesi uygulama detayı |
| Reddedilen iç mesaj operasyonel prosedürü | OD-026 | **needs-review** — olay kaydı §8 ile örtüşür; bu belge kapatmaz |

**Onaylı (firm):**

- Dış yüzey yalnızca Lumos.
- İç katmanlara doğrudan dış girdi yok.
- Bando = güvenlik/gözlem/anomali katmanı; sıradan görev ajanı değil; yürütme yok; kullanıcıya görünmez.
- Dış → Bando doğrudan komut/veri/dosya kabulü yok; doğrudan erişim = güvenlik olayı.
- Lumos → iç katman iletişimi doğrulanmalı; imzalama ve/veya şifreleme tercih edilir.
- Karşılıklı denetim serbesttir; yatay görev verme, onay, yetki artırma, ayar değiştirme veya işlem başlatma yasaktır.

---

## 11. OD eşleme tablosu

| OD | Kaynak | Konu | Bu belgedeki karar / durum |
|----|--------|------|----------------------------|
| **OD-006** | internal-agent-layers.md | Bando katman varlığı | **decision-approved / implementation-pending.** Ayrı katman; yalnızca güvenlik/gözlem/anomali; yürütme yok; kullanıcıya görünmez. Dağıtım modeli ve edge-case senaryoları uygulama detayı. |
| **OD-007** | internal-agent-layers.md | İç iletişim protokolü | **decision-approved / implementation-pending.** Lumos→iç iletişim doğrulanmalı; imza/şifreleme tercih edilir. Protokol, format, anahtar döngüsü, vault entegrasyonu private/gizli uygulama paketini bekler. |
| **OD-026** | internal-agent-layers.md | Doğrulanmamış iç mesaj olay kaydı | §8'de ilke olarak referans; operasyonel prosedür **needs-review** — bu belge kapatmaz. |

---

## 12. Sonraki adım

1. OD-006 ve OD-007 uygulama paketini private/gizli kanalda başlat (dağıtım modeli, protokol, format, anahtar döngüsü).
2. `internal-agent-layers.md` içinde OD-006 ve OD-007 notlarını onaylı karar durumuna senkronize et.
3. OD-026 operasyonel olay kaydı prosedürünü vault ve kimlik kararları (OD-001 – OD-002) ile birlikte sıraya al — **needs-review** olarak kalır.

**Tek net ilerleme (şimdilik):** Uygulama paketi; kod veya public repo değişikliği bu kararın kapsamı dışındadır.

---

Son güncelleme: 2026-06-17
