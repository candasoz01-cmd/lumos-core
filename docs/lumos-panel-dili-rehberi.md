# Lumos panel dili — rehber

**Amaç:** Teknik doğruluk kalsın; kullanıcıya sade, anlaşılır, samimi anlatım. Panel çıktıları okunur ve güven verici olsun. Ton: resmi değil, gevşek değil — **usta gibi anlatan**.

**Kapsam:** Panel arayüz metinleri, demo senaryo açıklamaları, operatör görünümünde kullanıcıya giden kısa mesajlar. Cursor ajanı **panel ile ilgili** kullanıcıya cevap verirken veya panel kopyası yazarken bu rehberi uygular.

**Tamamlayıcı:** Uzun isteği işleme mantığı `docs/lumos-uzun-istek-isleme.md` ile çelişmez; bu rehber **nasıl anlatılacağını** tarif eder.

---

## 1) Cevap yapısı (zorunlu sıra)

Her kullanıcıya dönük cevap şu sırada olsun:

| Sıra | Bölüm | İçerik |
|------|--------|--------|
| 1 | **Kısa özet** | 1–2 cümle: özün ne olduğu. |
| 2 | **Ne anladım** | Kullanıcının isteğini kendi cümlelerinle, net. |
| 3 | **Ne öneriyorum / ne yapacağız** | Somut adım veya seçenek; belirsizlik yok. |
| 4 | **Örnek / sade açıklama** | (Varsa) tek küçük örnek veya benzetme. |
| 5 | **Sorular** | (Varsa) kritik netleştirme; gereksiz soru yok. |

Eksik bölüm yoksa atlanır; sıra bozulmaz.

---

## 2) Dil kuralı

- **Varsayılan:** sade Türkçe.
- **Teknik terim:** Mümkünse kullanma. Şartsa **parantez içinde** gündelik karşılık yaz.

| Kullanma | Yeğle |
|----------|--------|
| snippet | küçük kod parçası (snippet) |
| endpoint | sistemin giriş noktası (endpoint) |
| deploy | canlıya alma |
| fallback | yedek / yedek davranış |

---

## 3) Ton

- Cümle başlarında bazen yönlendirici ifadeler: *“Şöyle düşünebiliriz…”*, *“Burada iki seçenek var…”*, *“En mantıklısı şu olur…”*
- Abartılı emoji yok; ara sıra **👉** veya tek nokta için yeterli.
- Öğretici değil, **birlikte netleştiren** üslup.

---

## 4) Yasaklar

- Jargon bombardımanı.
- Uzun paragraf (3–4 cümleden fazla blokları böl; liste veya kısa parça kullan).
- Belirsiz cümle (“belki yapılır”, “duruma göre” tek başına — yerine ne yapılacağını veya neyin netleşmesi gerektiğini yaz).

---

## 5) Basitleştirme

Kullanıcı teknik değilse:

- Anlatımı sadeleştir.
- Mümkünse tek örnek ver.
- Gerekirse **benzetme** (abartısız): örn. “yedek rota gibi çalışır”.

---

## 6) Uzun isteklerde

- Parçala; her parça **kısa başlık**.
- Liste kullan.
- Uzun-istek **içerik** ayrıştırması: `docs/lumos-uzun-istek-isleme.md` — **sunum** bu rehberdeki yapı ve ton ile yapılır.

---

## 7) Başarı ölçütü

Kullanıcı:

- Tek okumada anlasın.
- Aynı şeyi tekrar sormak zorunda kalmasın.
- Güven hissetsin (“nasıl yapıldığı” ve “sınır ne” açık).

---

## Örnek (uzun istek çıktısının panel dilinde yeniden üretimi)

Eski madde işaretli özet şablonunun panel dilinde karşılığı: **`docs/lumos-panel-dili-uzun-istek-ornegi.md`**.

---

*Güncelleme yeri: bu dosya ve `.cursor/rules/lumos-panel-dili.mdc`.*
