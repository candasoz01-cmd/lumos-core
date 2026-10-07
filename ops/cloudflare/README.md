# Lumos ürün sitesi — Cloudflare Workers

Bu dizin mevcut Astro kaynaklarından `https://lumosai.company` ürün sitesini paketler. Şirket sitesi `https://welockai.com`, uygulama girişi/paneli `https://app.lumosai.company` üzerinde kalır. Proje kararları `docs/CONSTITUTION.md`, `docs/ROADMAP.md` ve `docs/TECHNICAL_DEBT.md` içindedir.

## Kaynak ve kapsam

`build_company.py` yayın kapısını çalıştırır, Astro'yu derler, yalnız ana sayfa, accessibility, education, lab, integrations, privacy, terms, data-and-trust, slack, cyber ve connect/mac sayfalarını ve kullandıkları assetleri paketler; ardından oluşturulan paketi yeniden tarar. Ürün tanıtım bağlantıları bu domain içinde kalır. Giriş, panel ve uygulama entegrasyon yolları uygulama domainine bağlanır; bilinmeyen yollar topluca uygulamaya yönlendirilmez. API/backend veya panel pakete alınmaz. Önceki çıktı `.generated/previous-*` altında korunur. Üretilen dosyalar, node_modules ve Wrangler durumu Git'e alınmaz.

Worker yalnız tam `/auth` ve `/panel` yollarını uygulama domainine yönlendirir. API, callback ve benzer önekli bilinmeyen yollar asset katmanında404 kalır. Mevcut kayıtlı privacy/terms ve OAuth callback adresleri değiştirilmez.

## Yerel doğrulama

Repo kökünde `npm --prefix ui ci`, bu dizinde `npm ci` çalıştırın.

```sh
npm test
npm run check
npm run dev
```

`check` mevcut yayın kapısını, Astro build'i, statik paketlemeyi ve Wrangler dry-run'ı çalıştırır. Yerel adres `http://127.0.0.1:8795` olur. İndeksleme yalnız `INDEXABLE=true` ve tam `lumosai.company` hostname'i birlikte sağlanınca açılır. Worker güvenlik başlıkları ekler; önizleme indekslenmez.

## Yayın ve geri dönüş

`wrangler.jsonc` mevcut `lumos-company` Worker'ını ve `lumosai.company` custom domainini tanımlar; workers.dev ve preview URL'leri kapalıdır. Bu dosyanın Git'e alınması kendi başına Cloudflare deploy tetiklemez. Yayın ayrı açık kullanıcı yetkisi gerektirir; token/anahtar repoya eklenmez.

Yetkili yayından önce `wrangler deployments list` ile mevcut sürümü kaydedin. `wrangler deploy` build zincirini çalıştırır ve statik paketi yükler. Sonrasında ana sayfa, TR/EN metin, şirket bağlantısı, auth/panel yönlendirmeleri, privacy/terms ve404 davranışını canlı kontrol edin. Gerektiğinde kaydedilen önceki Worker version'ına dönün. Vercel şirket sitesi ayrı deployment ve geri dönüş noktasıdır.

İngilizce içerik istemci tarafı dil seçimiyle açılır; ayrı `/en` route'u yoktur. Build veya metin testi tek başına backend davranışının canlı kanıtı değildir. Teknik veri envanteri kaynak sürümünü ve doğrulanmayan ortam/harici servis sınırlarını açıkça belirtir.
