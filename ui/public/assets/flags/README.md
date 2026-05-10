# Bayrak SVG kaynakları ve lisans

Bu klasördeki vektörler **Wikimedia Commons** üzerinden alınmış **orijinal Commons SVG gövdelerinin** projeye kopyalarıdır (içerik elle uydurulmamıştır).

## Repoda dosya yolları (Astro `public`)

| Dosya | Yol |
|--------|-----|
| Türkiye | `ui/public/assets/flags/tr.svg` |
| KKTC | `ui/public/assets/flags/kktc.svg` |

Statik sitede kök URL: `/assets/flags/tr.svg`, `/assets/flags/kktc.svg` (`ui/` uygulama kökündeki `public/` klasörü build çıktısına kopyalanır).

## tr.svg

- **Kaynak dosya (Commons):** [File:Flag_of_Turkey.svg](https://commons.wikimedia.org/wiki/File:Flag_of_Turkey.svg)
- **Kalıcı bağlantı (sayfa):** https://commons.wikimedia.org/wiki/File:Flag_of_Turkey.svg

## kktc.svg

- **Kaynak dosya (Commons):** [File:Flag_of_the_Turkish_Republic_of_Northern_Cyprus.svg](https://commons.wikimedia.org/wiki/File:Flag_of_the_Turkish_Republic_of_Northern_Cyprus.svg)
- **Kalıcı bağlantı (sayfa):** https://commons.wikimedia.org/wiki/File:Flag_of_the_Turkish_Republic_of_Northern_Cyprus.svg

## Lisans ve atıf

- **Güncel lisans ve atıf şartları** yalnızca ilgili **Wikimedia Commons dosya sayfasındaki “Licensing” / “Permission”** bölümüne göre belirlenir; bu metin hukuki tavsiye değildir.
- Yayın veya ürün politikası gerektiriyorsa her iki sayfayı doğrudan kontrol edin; **CC-BY-SA** gibi lisanslar **atıf veya aynı lisansla paylaşım** isteyebilir.
- Özet kopya: çoğu resmi bayrak SVG’si Commons’ta **kamu malı (PD)** veya benzeri olarak işaretlenir; **kesin metin için Commons sayfasını okuyun.**

## Kullanım (UI)

`GlobalMay19Corner.astro` bileşeni bu dosyaları `<img src="/assets/flags/tr.svg">` ve `<img src="/assets/flags/kktc.svg">` ile yükler.
