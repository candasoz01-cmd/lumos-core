# İç ajan katmanları — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından taşınan Lumos, Kando, Cando ve Bando **iç katman ayrımı**, görünmezlik ve güvenlik sınırı maddelerinin repo'ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir.

**Üst politika:** ChatGPT Saved Memories **canonical değildir**; `docs/memory/` **canonical'dır.** Çelişki varsa repo metni esas alınır.

**Çapraz referans ruhu:** [`product-rules.md`](./product-rules.md) (dış yüzey, kullanıcı deneyimi), [`security-architecture.md`](./security-architecture.md) (geçit, bridge, iç katman sınırı).

---

## Dış yüz ilkesi

| # | İlke | Not |
|---|------|-----|
| 1 | Gerçek üründe son kullanıcı **Kando'yu görmez**. | Taşındı |
| 2 | Dışa açık tek yüzey **Lumos**'tur. | Taşındı |
| 3 | Cando ve Kando **iç çalışma/uygulama katmanları** olarak arka planda kalır. | Taşındı |
| 4 | Normal kullanımda kullanıcı yalnızca **Lumos** ile etkileşir. | Taşındı |
| 5 | Kando'ya iş aktarımı **iç çalışma prensibi**dir; dışa yansıtılmaz. | Taşındı |

---

## İç katman görünmezliği

Ürün arayüzü ve mesajları iç katmanları kullanıcıya açmaz.

| # | Kural | Yasak örnek (ürün metni) | Not |
|---|--------|---------------------------|-----|
| 1 | İç katman adları kullanıcıya gösterilmez. | "Kando'ya ilettim", "ajana yönlendirdim" | Taşındı |
| 2 | Başka AI / ajan varlığı ima edilmez. | "başka AI", "ajan", "iç sistem" | Taşındı |
| 3 | Kullanıcı yalnızca Lumos'un işi aldığını / başlattığını / tamamladığını görür. | — | Taşındı |

**Özet:** Kullanıcı dili her zaman Lumos merkezlidir; iç orkestrasyon şeffaf değildir.

---

## Komut ve veri akışı

| # | Kural | Not |
|---|--------|-----|
| 1 | Kando, Cando ve olası Bando dış kaynaklardan veya diğer kaynaklardan **doğrudan komut, dosya veya veri kabul etmez**. | Taşındı |
| 2 | Tüm akış **yalnızca Lumos geçidi** üzerinden yönlendirilir. | Taşındı |
| 3 | Bypass veya doğrudan iç katman erişimi mimari ihlal sayılır. | Taşındı |

**Akış özeti:**

```
Dış dünya / kullanıcı → Lumos (geçit) → [doğrulanmış iç iletişim] → Kando / Cando / (Bando)
```

İç katmanlar birbirine veya dışa Lumos bypass etmeden bağlanmaz.

---

## Katman görev ayrımı

Lumos, Kando, Cando ve Bando **görev alanları karıştırılmaz.**

| Katman | Rol (özet) | Dışa görünür mü |
|--------|------------|-----------------|
| **Lumos** | Kullanıcıya açık yüzey; güvenli geçit ve orkestratör | Evet |
| **Kando** | İç çalışma / koordinasyon katmanı | Hayır |
| **Cando** | İç uygulama / iş yürütme katmanı | Hayır |
| **Bando** | Ayrı katman olarak tanımlanırsa: güvenlik/gözlem (bkz. §6) | Hayır |

| # | Kural | Not |
|---|--------|-----|
| 1 | Bir katmanın görevi diğer katmana taşınmaz (rol kayması yok). | Taşındı |
| 2 | Ürün, panel ve mesajlarda katmanlar birleştirilerek sunulmaz. | Taşındı |
| 3 | İç katmanlar kullanıcı adına tek "Lumos" deneyimi olarak paketlenir. | Taşındı |

---

## Bando güvenlik notu

Bando ayrı bir katman olarak varsa **sıradan görev ajanı değildir**; özel güvenlik / izleme rolü taşır.

| # | İlke | Not |
|---|------|-----|
| 1 | Bando **doğrudan girdi kabul etmez**. | Taşındı |
| 2 | Dış kaynaktan Bando'ya komut = **güvenlik olayı** (incident). | Taşındı |
| 3 | Rol: gözlem, analiz, anomali tespiti, Lumos'a raporlama. | Taşındı |
| 4 | Bando **yürütme / komut katmanı değildir**; iş başlatmaz, kullanıcı adına aksiyon almaz. | Taşındı |
| 5 | Bando'nun ayrı katman olarak varlığı ve sınırları | needs-review — mimari karar netleştirilecek |

---

## İç iletişim doğrulama

Lumos'tan iç katmanlara giden iletişim de güven sınırında tutulur.

| # | İlke | Not |
|---|------|-----|
| 1 | İç iletişim **doğrulanmalı**; tercihen imzalı ve/veya şifreli. | Taşındı |
| 2 | İmzalama protokolü, anahtar döngüsü ve şifreleme detayı | needs-review — uygulama ve protokol ayrı kaynakta |
| 3 | Doğrulanmamış veya yetkisiz iç mesaj reddedilir / olay kaydı oluşturulur. | Taşındı — operasyonel detay needs-review |

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
| 3 | Rol kayması (ör. Bando yürütme) | Katman görev ayrımı; kod ve politika denetimi | Taşındı |
| 4 | İç iletişimde zayıf doğrulama | İmza/şifreleme tercihi | needs-review |
| 5 | Public dokümanda iç protokol sızıntısı | Public anlatım sınırı; hassas detay ayrı kanal | Taşındı |
| 6 | Bando kapsamının belirsizliği | Mimari karar ve needs-review takibi | needs-review |

---

## Migration tablosu

ChatGPT Saved Memories / oturum bağlamından bu dosyaya taşınan maddeler.

| # | Kaynak özeti | Hedef bölüm | Durum |
|---|--------------|-------------|--------|
| 1 | Kullanıcı Kando görmez; yalnızca Lumos dış yüzey | §2 Dış yüz ilkesi | Taşındı |
| 2 | UI'da "Kando'ya ilettim", "ajan", "başka AI" yok | §3 İç katman görünmezliği | Taşındı |
| 3 | Kullanıcı Lumos aldı/başlattı/tamamladı görür | §3 İç katman görünmezliği | Taşındı |
| 4 | İç katmanlar dıştan doğrudan komut/veri almaz | §4 Komut ve veri akışı | Taşındı |
| 5 | Akış yalnızca Lumos geçidi | §4 Komut ve veri akışı | Taşındı |
| 6 | Lumos→iç iletişim doğrulanmalı; imza/şifreleme tercihi | §7 İç iletişim doğrulama | Taşındı (protokol needs-review) |
| 7 | Bando: güvenlik/izleme; doğrudan girdi yok; incident | §6 Bando güvenlik notu | Taşındı (varlık needs-review) |
| 8 | Katman görev alanları karışmaz | §5 Katman görev ayrımı | Taşındı |
| 9 | Public'te iç katman/protokol detayı yok | §8 Public anlatım sınırı | Taşındı |
| 10 | ChatGPT memory canonical değil; docs/memory canonical | Amaç / üst politika | Taşındı |

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

*Son güncelleme: 2026-06-17*
