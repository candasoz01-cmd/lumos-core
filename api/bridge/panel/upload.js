/**
 * Vercel serverless route: /api/bridge/panel/upload
 *
 * `[...path].js` catch-all'ı prod'da yalnız tek segmentli köprü yollarını
 * eşliyor; çok segmentli `panel/upload` istekleri fonksiyona hiç ulaşmadan
 * platform 404'üne düşüyordu (allowlist'te olmasına rağmen). Canonical yolu
 * doğrudan aynı proxy handler'ına bağlıyoruz.
 *
 * Mantık kopyalanmaz: allowlist, çağıran yetkisi ve secret enjeksiyonu tek
 * yerde kalsın diye handler ve config yeniden dışa aktarılır. Handler
 * segmentleri `req.url` üzerinden de çözdüğü için (`/api/bridge/` öneki
 * ayrıştırması) bu dosyadan gelen istek de `["panel", "upload"]` olarak
 * allowlist'e girer.
 */

export { config, default } from "../[...path].js";
