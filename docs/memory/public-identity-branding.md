# Public kimlik ve marka — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından taşınan **dış vitrin**, **kurucu/kullanıcı anlatımı**, **çıktı sahipliği** ve **marka/görsel kimlik** notlarının repo'daki **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir.

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak olarak kullanılır. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Public repo** | Gizli anahtar, PII, production URL veya aşırı kişisel hassas detay taşınmaz. |

Taşıma süreci ve durum tanımları: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Dış vitrin fazı

**Sonraki faz:** *Lumos dış vitrin hazırlığı*

| # | Yapılacak | Durum | Not |
|---|-----------|--------|-----|
| 1 | LinkedIn profil güncellemesi | `[queued]` | Kısa, doğru, abartısız tanıtım |
| 2 | Profil fotoğrafı | `[queued]` | ChatLumos işareti (`ui/public/chat-lumos-mark.svg`) kullanılmalı — bkz. Marka ve görsel kimlik #1 |
| 3 | Kısa kişisel/proje tanıtım metni | `[queued]` | Başlangıç seviyesi vurgusu dahil |
| 4 | GitHub README metni | `[queued]` | Public repo sınırına uygun |
| 5 | Landing page kopyası | `[needs-review]` | Ton, iddia seviyesi ve hedef kitle netleşmeli |

**Aksiyon:** Dış vitrin maddeleri tek seferde değil; her kanal için ayrı taslak → gözden geçirme → yayın sırası izlenir.

---

## Kullanıcı/kurucu anlatımı

Kullanıcıyı **AI geliştirici** olarak anlatırken aşağıdaki çerçeve korunur:

- Kullanıcı, kendi perspektifinden kendini **başlangıç seviyesinde** görür; dış anlatımda bu vurgu tutarlı kalır.
- Kullanıcı hakkındaki tüm betimlemeler **AI yorumu** olarak etiketlenir; kullanıcının kendi öz-tanımı **doğrudan gerçek** gibi sunulmaz.
- Dış metinlerde abartılı, yanıltıcı veya istenmeyen kimlik iddiaları kullanılmaz.

**Örnek çerçeve (taslak):** *"AI destekli geliştirme yolculuğunda; kendi değerlendirmesiyle başlangıç seviyesinde ilerleyen bir geliştirici."*

---

## Başlangıç seviyesi vurgusu

| Kural | Açıklama |
|-------|----------|
| **Tutarlılık** | LinkedIn, README, landing ve kısa intro metinlerinde aynı çizgi korunur. |
| **Perspektif** | "Başlangıç seviyesi" kullanıcının **kendi bakış açısından** ifade edilir; dışarıdan atanmış unvan veya yetkinlik iddiası değildir. |
| **Kaynak etiketi** | Bu vurgu ChatGPT/AI oturum bağlamından taşınmıştır; kullanıcı onayı olmadan kesin profil tanımı yapılmaz. |

---

## Lumos ile üretilen çıktıların sahipliği

| Konu | Kural |
|------|--------|
| **İmza / sahiplik** | Lumos ile üretilen çıktılar **kullanıcıya** aittir; Lumos'a değil. |
| **Lumos rolü** | Lumos üretimde **destekleyen / uygulayan araç**tır; nihai sahip değildir. |
| **Sorumluluk** | Nihai sahiplik, sorumluluk ve imza **kullanıcıya** aittir. |
| **Dış anlatım** | "Lumos yaptı" yerine "kullanıcı (Lumos desteğiyle) üretti" çizgisi tercih edilir. |

---

## Marka ve görsel kimlik

| # | Madde | Durum | Not |
|---|--------|--------|-----|
| 1 | ChatLumos ana marka işareti | `[decision-approved]` | 17 Temmuz 2026 amendment — bkz. `od-050-logo-paketi-decision.md` § 4. iOS, web, favicon, OAuth, sosyal profil ve ürün UI'de birincil |
| 2 | Ağaç + ay + merkez kuantum yıldızı — ikincil kurumsal mühür | `[decision-approved]` | Artık ana kimlik değil; yalnızca `index.astro`'daki "We Lock AI" şirket nav bloğunda kalıyor |
| 3 | Logo kullanım alanları (README, landing, sosyal, uygulama) | `[decision-approved]` | ChatLumos küçük vektör ve koyu/derin uygulama ikonunda aynı geometriyi korur |
| 4 | Renk dili | `[decision-approved]` | Altın + koyu zemin; sakin ve kurumsal kullanım |
| 5 | Hizmet varyantları | `[approved-rule]` | Ana logo değişmez; hizmete göre ikincil rozet/etiket/vurgu türetilir |

**Kısıt:** Görsel dosya bu migration kapsamında eklenmez; yalnızca not ve gelecek karar alanı kaydı tutulur.

---

## Public anlatım sınırı

Dış vitrin ve public metinlerde **olmaması gerekenler:**

- Abartılı yetkinlik veya deneyim iddiaları
- Kullanıcının onaylamadığı öz-tanım veya unvan
- Lumos'un çıktı sahibi veya imza sahibi gibi sunulması
- Gizli anahtar, PII, production URL, ticari/gizli katman detayı
- İç katman adlarının (Kando, Cando, Bando vb.) kullanıcıya dönük vitrinde öne çıkarılması

**Olması gerekenler:**

- Kısa, doğrulanabilir, demo-safe ifadeler
- AI yorumu / kullanıcı perspektifi ayrımının korunması
- Lumos'un destekleyici araç rolünün netliği

---

## Riskler

| Risk | Etki | Önlem |
|------|------|--------|
| ChatGPT memory ile repo metni çelişir | Yanlış dış anlatım | `docs/memory/` canonical; çelişkide repo güncellenir |
| Başlangıç seviyesi vurgusu kaybolur | Tutarsız veya abartılı profil | Tüm vitrin metinlerinde kontrol listesi |
| Lumos çıktı sahibi gibi sunulur | Sahiplik / sorumluluk karışıklığı | Sahiplik bölümüne sabit referans |
| Hizmet varyantı ana logodan kopar | Marka tutarsızlığı | Ana geometri korunur; yalnızca ikincil katman türetilir |
| AI yorumu gerçek gibi yazılır | Yanıltıcı kurucu profili | "AI yorumu" etiketi zorunlu |

---

## Migration tablosu

ChatGPT Saved Memories / oturum bağlamından bu dosyaya taşınan maddeler:

| # | Durum | Kaynak özeti | Hedef bölüm | Not |
|---|--------|--------------|-------------|-----|
| 1 | `[migrated]` | Dış vitrin fazı: LinkedIn, foto, intro, README, landing | Dış vitrin fazı | |
| 2 | `[migrated]` | Kullanıcı AI geliştirici; kendi gözünde başlangıç seviyesi | Kullanıcı/kurucu anlatımı · Başlangıç seviyesi vurgusu | AI yorumu etiketi eklendi |
| 3 | `[migrated]` | Çıktılar kullanıcıya ait; Lumos destekleyici araç | Lumos ile üretilen çıktıların sahipliği | |
| 4 | `[closed]` | Eski skull/alternatif ana logo arayışı | Marka ve görsel kimlik | Ağaç + ay + kuantum yıldızı kararıyla kapatıldı |
| 5 | `[migrated]` | Abartısız, istenmeyen iddia yok | Public anlatım sınırı | |
| 6 | `[needs-review]` | Landing page tonu ve kopya detayı | Dış vitrin fazı · Marka | Kanal bazlı taslak gerekli |
| 7 | `[decision-approved]` | Logo kullanım kuralları | Marka ve görsel kimlik | OD-050/051 ile sabitlendi |

---

## Manuel eklenecek maddeler

Aşağıdaki tabloya ChatGPT Saved Memories'ten veya oturum notlarından kopyalanan yeni maddeleri yapıştırın. Taşıma tamamlanınca durumu güncelleyin.

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
