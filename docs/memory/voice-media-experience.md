# Lumos ses / medya / kamera / görsel deneyimi — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından gelen Lumos **sesli mod, STT/TTS, ses dosyası, kamera ve görsel destek** notlarının repo'ya taşınmış **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir.

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |

Taşıma süreci ve durum tanımları: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Sesli mod ilkeleri

### Ürün vaadi

- Sesli konuşma ürün akışında **kaybolmamalı**; **ürün vaadi** olarak izlenir.
- Sesli konuşma, **TTS / sesli okuma**, **ses yükleme ve işleme** temel beklentilerdir.

### STT boru hattı

1. Kullanıcı konuşması önce **metne transkribe** edilir.
2. Metin **ana sisteme yazı gibi** girer.
3. Ses katmanı **yalnızca UI değildir**; STT sonrası **bağlam, niyet, güvenlik sınırı ve önceki kararlarla tutarlılık** kontrollerinden geçmelidir.
4. Lumos ses modunda **varsayıma koşmaz**; belirsizlikte **kısa netleştirme** sorar.

---

## Ses-yazı devamlılığı

- Ses ve yazı modları **kopuk çalışmaz**; görev **modlar arası süreklilik** taşır.
- Kullanıcı yazılı / arka planda çalışan görev varken **konuşabilir**; sonuç veya netleştirme **ses moduna geri dönebilir**.
- Ses modu **ayrı sohbet kanalı değildir**; yazılı görev motoruna bağlı **giriş / geri bildirim katmanıdır**.

---

## Güvenlik ve niyet kontrolü

- STT sonrası metin, yazılı kanaldakiyle **aynı güvenlik ve niyet sınırından** geçer.
- Önceki kararlar ve bağlam ile **tutarlılık** zorunludur; ses hızı nedeniyle kontrol atlanmaz.
- Belirsiz niyette **kısa netleştirme**; otomatik varsayım yok.

### Kanıt ve çıktı ayrımı

- Debug / proje akışında **gerçek kanıt olmadan sonuç sunulmaz**.
- **Mock** ile **gerçek** çıktı ayrımı korunur.

---

## Ses dosyası ve TTS beklentileri

| Beklenti | Davranış |
|----------|----------|
| **Sesli konuşma** | Ürün vaadi; akışta kaybolmaz |
| **TTS / sesli oku** | Cevap kartları ve ses modunda temel beklenti |
| **Ses yükleme / kayıt** | Giriş menüsünden; işleme ana sisteme metin/bağlam olarak bağlanır |
| **Ses işleme** | STT sonrası yazılı görev motoru ile aynı kurallar |

İlgili UI notları: [`ui-chat-experience.md`](./ui-chat-experience.md) — giriş menüsü ve cevap kartı TTS aksiyonları.

---

## Kamera ve fotoğraf fikri

- **Kamera erişimi** ve **fotoğraf kalitesi iyileştirme** gelecek için izlenen fikirlerdir.
- **Cihaz izni**, **kullanıcı onayı** ve **güvenlik sınırı** zorunludur; onaysız erişim yok.
- Foto / arka plan düzenleme akışları **ürün kapsamı netleşene kadar** `needs-review`.

Giriş menüsünde galeri / kamera / dosya ayrımı: [`ui-chat-experience.md`](./ui-chat-experience.md).

---

## Görsel üretim / görsel destek

- **Görsel üretim** ve **görsel destek** beklentisi izlenir.
- Tasarım, kart/mesaj modeli ve ürün kapsamı **netleşene kadar** `needs-review`.
- Chat içi görsel destek UX ile hizalanacak.

---

## Riskler

Aşağıdaki ChatGPT ses modu riskleri Lumos için **izlenen risk maddeleri**dir:

| Risk | Açıklama |
|------|----------|
| **Bağlam kaybı** | Oturum / görev bağlamının ses modunda düşmesi |
| **Yanlış yorumlama** | STT veya niyet çıkarımı hatası |
| **Beklenmeyen davranış** | Ses katmanının yazılı motor kurallarını bypass etmesi |

**Azaltma:** STT → metin → aynı güvenlik/niyet kontrolü; belirsizlikte kısa netleştirme; mock/gerçek ayrımı; ses-yazı görev sürekliliği.

---

## Migration tablosu

ChatGPT Saved Memories / oturum bağlamından bu dosyaya taşınan maddeler.

| # | Durum | Kaynak özeti | Hedef bölüm | Not |
|---|--------|--------------|-------------|-----|
| 1 | `[migrated]` | Sesli konuşma ürün akışında kaybolmamalı; ürün vaadi | Sesli mod ilkeleri | Taşındı |
| 2 | `[migrated]` | Sesli konuşma, TTS, ses yükleme/işleme temel beklenti | Ses dosyası ve TTS beklentileri | Taşındı |
| 3 | `[migrated]` | Ses-yazı kopuk değil; görev sürekliliği modlar arası | Ses-yazı devamlılığı | Taşındı |
| 4 | `[migrated]` | Yazılı/arka plan görev varken konuşma; sonuç ses moduna dönebilir | Ses-yazı devamlılığı | Taşındı |
| 5 | `[migrated]` | Ses modu ayrı kanal değil; yazılı görev motoruna bağlı giriş/geri bildirim | Ses-yazı devamlılığı | Taşındı |
| 6 | `[migrated]` | Konuşma önce STT ile metne; ana sisteme yazı gibi girer | Sesli mod ilkeleri | Taşındı |
| 7 | `[migrated]` | Ses katmanı UI-only değil; bağlam, niyet, güvenlik, önceki karar tutarlılığı | Güvenlik ve niyet kontrolü | Taşındı |
| 8 | `[migrated]` | Ses modunda varsayıma koşma; belirsizlikte kısa netleştirme | Güvenlik ve niyet kontrolü | Taşındı |
| 9 | `[migrated]` | Gerçek kanıt olmadan sonuç yok; mock/gerçek ayrımı | Güvenlik ve niyet kontrolü | Taşındı |
| 10 | `[migrated]` | ChatGPT ses modu: bağlam kaybı, yanlış yorum, beklenmeyen davranış → risk | Riskler | Taşındı |
| 11 | `[needs-review]` | Görsel üretim / görsel destek beklentisi | Görsel üretim / görsel destek | Tasarım ve kapsam netleşecek |
| 12 | `[needs-review]` | Kamera erişimi, foto kalitesi iyileştirme | Kamera ve fotoğraf fikri | İzin, onay, güvenlik sınırı |
| 13 | `[needs-review]` | Foto / arka plan düzenleme akışları | Kamera ve fotoğraf fikri | Ürün kapsamı netleşecek |

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
