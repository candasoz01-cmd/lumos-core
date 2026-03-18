# Panel manuel test akışı

**Amaç:** Backend + panel + **Kartlı sonuç** (`#yanit`) ekranının aynı şekilde doğrulanması.

---

## 1. Backend (Akış ekranı için isteğe bağlı)

Kartlı sonuç ekranı **backend istemez**. Sadece **Akış** (`#feed`) için Express API gerekir.

```bash
cd backend
npm start
```

Beklenti: API `http://127.0.0.1:3000` (veya projede tanımlı port) ayakta.

---

## 2. Panel sunucusu

**Önerilen:** `panel` klasörü kök olacak şekilde sunucu (Kartlı sonuç URL’si kısa kalır).

```bash
cd panel
python3 -m http.server 8080
```

---

## 3. Tarayıcı rotası — Kartlı sonuç

```
http://127.0.0.1:8080/#yanit
```

Alternatif (sunucu **repo kökünden** ise):

```
http://127.0.0.1:8080/panel/#yanit
```

---

## 4. Kullanıcı ne görmeli (Kartlı sonuç)

| Adım | Beklenti |
|------|----------|
| 1 | Başlık: **Kartlı sonuç**; alt başlık ve gri kutuda kısa açıklama |
| 2 | **Kısa özet** kartı en üstte, tam genişlikte, en belirgin gölge |
| 3 | Altında **Ne anladım**, **Ne öneriyorum**, **Sorular** başlıkları **kısmen üst üste** (deste hissi) |
| 4 | Bir alt başlığa **tıklayınca** o kart açılır (liste görünür); aynı başlığa tekrar tıklayınca kapanır |
| 5 | Altta **Devam et**, **Daha sade anlat**, **Uygulamaya başla** düğmeleri görünür; tıklanınca geri bildirim metni çıkar |

---

## 5. Akış ekranı (backend açıkken)

1. Backend çalışır durumda olsun.  
2. Panelde menüden **Akış** veya `#feed`.  
3. Gönderi listesi veya boş/hata mesajı (API yoksa hata beklenir).

---

## 6. Hızlı kontrol listesi

- [ ] `python3 -m http.server 8080` → `panel` dizininde  
- [ ] `http://127.0.0.1:8080/#yanit` açılıyor  
- [ ] Özet kartı tam; alt kartlar katmanlı; tıklama çalışıyor; üç buton görünüyor  
- [ ] (İsteğe bağlı) `#feed` + backend ile akış  

---

## Toplu komut (kopyala-yapıştır)

Terminal 1:

```
cd backend
npm start
```

Terminal 2:

```
cd panel
python3 -m http.server 8080
```

Tarayıcı:

```
http://127.0.0.1:8080/#yanit
```

*(Kartlı sonuç için backend şart değil; yalnızca `#feed` testinde Terminal 1 gerekir.)*

---

## İlgili belgeler

- `panel/README.md` — panel açma (en üst blok)  
- `docs/lumos-karar-ve-uygulama-listesi.md` — karar özeti  
