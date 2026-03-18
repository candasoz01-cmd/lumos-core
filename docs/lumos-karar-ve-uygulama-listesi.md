# Lumos — alınan kararlar ve sıralı uygulama listesi

Konuşma ve dokümantasyonda **kaybolmaması** için ürün/panel/davranış kararlarının tek özeti. Tekrarlar çıkarıldı.

---

## Şimdi (uygulanmış / geçerli)

| # | Karar | Kaynak / not |
|---|--------|----------------|
| 1 | Panel **Kartlı sonuç** (`#yanit`): kısa özet üstte tam kart; alt kartlar deste gibi kısmen görünür; başlığa tıklayınca açılır/kapanır | `panel/js/app.js`, `panel/css/app.css` |
| 2 | Aksiyonlar: Devam et, Daha sade anlat, Uygulamaya başla (geri bildirim metni) | Panel |
| 3 | Menü etiketi **«Kartlı sonuç»** (eski “Yanıt” belirsizdi) | `panel/js/app.js` |
| 4 | Ekran girişinde kısa açıklama kutusu (ne işe yarar) | Panel |
| 5 | **Panel dili:** profesyonel-samimi Türkçe; zorunlu cevap sırası; jargon sadeleştirme | `docs/lumos-panel-dili-rehberi.md`, `.cursor/rules/lumos-panel-dili.mdc` |
| 6 | **Konuşmadan görev:** tetik sinyali → niyet; net+düşük risk → kısa bilgi + başlat; riskli → sor; sessiz başlama yok | `docs/lumos-konusmadan-gorev-cikarma.md` |
| 7 | **Karar motoru** akışına örtük görev + vizyon/araştırma bağlandı | `docs/lumos-karar-motoru.md` |
| 8 | **Vizyon + sessiz araştırma disiplini:** OSS/piyasa sadece güçlü sinyalde; sessiz uygulama yok | `docs/lumos-urun-vizyon-ve-arastirma-cercevesi.md` |
| 9 | Akış ekranı başlığında “skor sıralı” ifadesi kaldırıldı (kullanıcıya gereksiz) | `panel/js/app.js` |
| 10 | Örnek senaryolar: konuşmadan görev testleri | `examples/lumos-konusmadan-gorev-senaryolari.md` |

---

## Sonra (sıradaki uygulama adayları)

| # | Karar / iş | Not |
|---|------------|-----|
| S1 | Kartlı sonuç verisini gerçek Lumos/ajan çıktısına bağlama | Adapter + kaynak; onaylı |
| S2 | Manuel test listesini CI’da otomatikleştirme (Playwright vb.) | İsteğe bağlı |
| S3 | `read_backend_state.py --write` sonrası Kartlı sonuçta alan gösterme | Tasarım gerekir |

---

## İleride (keşif / yön)

| # | Alan | Not |
|---|------|-----|
| İ1 | Kök + katkı paylaşım ürünü | Ürün keşfi; klasik feed değil |
| İ2 | Görev motorunda örtük niyet parser | Kod + sözleşme uyumu |
| İ3 | Avatar, cihaz, tarayıcı entegrasyonu | Vizyon belgesinde geçiyor |

---

## Panel ve test — tek link

Açma yolu ve doğrulama adımları: **`docs/panel-manuel-test.md`** ve **`panel/README.md`** (en üst blok).

---

*Güncelleme: yeni karar alındıkça bu listeye madde eklenir.*
