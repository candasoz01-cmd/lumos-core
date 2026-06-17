# Lumos UI / panel / chat deneyimi — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından gelen Lumos **panel, chat ve mesaj UX** notlarının repo'ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir.

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |

Taşıma süreci ve durum tanımları: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Chat cevap kartları

Her AI cevabı bağımsız bir **çıktı kartı** gibi davranır.

- Cevabın altında **hızlı aksiyon alanı** bulunur.
- Kart aksiyonları:
  - **Kopyala**
  - **Paylaş / gönder**
  - **Yeniden üret** (regenerate)
  - **TTS / sesli oku**
  - **Yeni dal / sohbet olarak çatalla** (fork as new branch/chat)
  - **Taşma menüsü** — ek aksiyonlar için overflow menu

---

## Giriş alanı ve medya yükleme

Chat giriş alanında **+ dosya/medya yükleme menüsü** olmalı.

Ayrı seçenekler (tek ikon altında karıştırılmaz):

| Seçenek | Davranış |
|---------|----------|
| **Dosya yükleme** | Genel dosya seçimi |
| **Foto / galeri** | Galeriden görsel seçimi |
| **Canlı kamera** | Anlık çekim |
| **Ses yükleme / kayıt** | Ses dosyası veya kayıt |

**Kural:** Foto ikonu **doğrudan kamerayı açmaz**; galeri / dosya / kamera ayrımı kullanıcıya sunulur.

---

## Mesaj ayrımı ve düzenleme

### Görsel ayrım

- Kullanıcı ve asistan mesajları **net görsel ayrımla** gösterilir.

### Kullanıcı mesajları

- **Düzenlenebilir**
- **Kopyalanabilir**

### Asistan cevapları

- **Kopyalanabilir**
- **Paylaşılabilir**
- **Mesaj olarak gönderilebilir**

### İzlenen özellikler

| Özellik | Durum |
|---------|--------|
| **Yeni sohbet menüsü** | İzleniyor — henüz tam spesifikasyon yok |
| **Mevcut sohbetten dal oluşturma** (branch-from-current) | İzleniyor — henüz tam spesifikasyon yok |

### Giriş alanı düzeni

- Uzun kullanıcı mesajları sağda **taşmamalı / gizlenmemeli**.
- Giriş alanı **çok satırlı textarea** olarak genişlemeli veya satır kaydırmalı olmalı; gerekirse **iç scroll** ile okunabilir kalmalı.

---

## Platform bağımsız UI dili

Lumos yalnızca PC/Mac değildir; **mobil kullanıcılar birincil kitle**dir.

| Kullan | Kullanma |
|--------|----------|
| **cihaz uygulamaları** | Mac uygulamaları |
| **yerel cihaz işlemleri** | Mac'e özgü ifadeler |
| Cihaz/OS bağımsız, kısa ve pratik dil | Platforma kilitli varsayımlar |

---

## Dış servis kısa yolları

Panelde sık yapılan manuel işlemler için **kısa rehber veya buton** alanı:

- **Render**
- **Vercel**
- **GitHub**

Amaç: kullanıcıyı dış panellere yönlendirmek veya adım adım kısa yol sunmak; otomatik dış yazma veya onaysız işlem **değildir**.

---

## Lumos panel tonu

- **Doğal, pratik, cihaz-yerel** ton.
- Kullanıcıyı **genel güvenlik boilerplate** ile yorma.
- Gerekli uyarılar kısa ve bağlama özel olsun; tekrarlayan şablon metinlerden kaçın.

---

## Kaynak / şeffaflık gösterimi

AI cevaplarında **kaynak / köken (provenance)** görünür olmalı:

| Gösterim | Açıklama |
|----------|----------|
| **Web kullanıldı mı?** | Evet/hayır veya ikon ile |
| **Kaynaklar** | Varsa listelenir |
| **Belirsizlik vs tahmin** | Tahmin, emin olunan bilgi ve belirsizlik ayrımı net olmalı |

---

## Görsel destek beklentisi

Görsel üretim / görsel destek beklentisi **izleniyor**; tasarım ve kapsam netleşene kadar uygulama kararı verilmez.

| Konu | Durum |
|------|--------|
| Görsel üretim (image generation) | **needs-review** — tasarım ve ürün kapsamı netleşecek |
| Chat içi görsel destek UX | **needs-review** — kart/mesaj modeli ile hizalanacak |

---

## Migration tablosu

ChatGPT Saved Memories / oturum bağlamından bu dosyaya taşınan maddeler.

| # | Durum | Kaynak özeti | Hedef bölüm | Not |
|---|--------|--------------|-------------|-----|
| 1 | `[migrated]` | AI cevap kartı + hızlı aksiyon alanı (kopyala, paylaş, yeniden üret, TTS, çatalla, overflow) | Chat cevap kartları | Taşındı |
| 2 | `[migrated]` | + menü: dosya, galeri, kamera, ses; foto ikonu doğrudan kamera açmaz | Giriş alanı ve medya yükleme | Taşındı |
| 3 | `[migrated]` | Kullanıcı/asistan görsel ayrımı; kullanıcı düzenleme; cevap kopyala/paylaş/gönder | Mesaj ayrımı ve düzenleme | Taşındı |
| 4 | `[queued]` | Yeni sohbet menüsü | Mesaj ayrımı ve düzenleme | Özellik izleniyor |
| 5 | `[queued]` | Mevcut sohbetten dal oluşturma | Mesaj ayrımı ve düzenleme | Özellik izleniyor |
| 6 | `[migrated]` | Uzun mesaj taşması; multiline textarea + scroll | Mesaj ayrımı ve düzenleme | Taşındı |
| 7 | `[migrated]` | Platform bağımsız dil: cihaz uygulamaları, yerel cihaz işlemleri | Platform bağımsız UI dili | Taşındı |
| 8 | `[migrated]` | Render / Vercel / GitHub kısa yolları | Dış servis kısa yolları | Taşındı |
| 9 | `[migrated]` | Doğal panel tonu; generic güvenlik boilerplate yok | Lumos panel tonu | Taşındı |
| 10 | `[migrated]` | Kaynak, web kullanımı, belirsizlik vs tahmin gösterimi | Kaynak / şeffaflık gösterimi | Taşındı |
| 11 | `[needs-review]` | Görsel üretim / görsel destek beklentisi | Görsel destek beklentisi | Tasarım ve kapsam netleşecek |

---

## Manuel eklenecek maddeler

Aşağıya ChatGPT Saved Memories veya oturum notlarından henüz işlenmemiş maddeleri yapıştırın.

| # | Durum | ChatGPT / oturum metni (yapıştır) | Hedef bölüm | Not |
|---|--------|-----------------------------------|-------------|-----|
| 1 | `[queued]` | | | |
| 2 | `[queued]` | | | |
| 3 | `[queued]` | | | |
| 4 | `[queued]` | | | |
| 5 | `[queued]` | | | |

*(Boş satırlar kasıtlıdır; gerektiğinde yeni satır ekleyin.)*

---

*Son güncelleme: 2026-06-17*
