# Lumos — Türkçe özet

Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Barındırılan sohbet, anahtar varsa kesilmiş iletiyi, oturumdaki adı ve izinli hafıza özetlerini bir model API’sine gönderir. Sohbet işleyicisi iletiyi kendi içinde veritabanına yazmaz; “hatırla” denirse en fazla 1000 karakterlik özet, saklama süresi bu depodan doğrulanamayan ayrı hafıza servisine yazılır. Yanıtta sağlayıcı ve model adı yoktur.

Onay katmanı yalnız `LUMOS_CONFIRMATION_ENABLED` değeri `1`, `true` veya `yes` iken çalışır. Sohbet yanıtı ayrı bir onay adımı beklemez. Ülkeye göre hukuk motoru yoktur. Tam bir maskeleme sistemi yoktur. Sağlayıcı saklaması bu kodla doğrulanmaz.

Aynı envanter: [docs/data-and-trust.md](docs/data-and-trust.md) · sitede `/data-and-trust`.

> **Not:** Tam Türkçe belgeler planlanıyor. Şimdilik İngilizce kaynaklar geçerlidir. Kurulum adımları aşağıdadır. Ürün cümleleri bu dosyada Türkçedir ve [README.md](README.md) ile aynı sınırı söyler.

## Hızlı başlangıç

Yeni geliştiriciler için birincil rehber (İngilizce):

- **[docs/getting-started.md](docs/getting-started.md)** — kurulum katmanları, port tablosu, `ui/` vs `panel/`
- **[README.md](README.md)** — ürün özeti ve dağıtım (İngilizce)

### Katman A (~5 dk)

Yalnızca arayüz; köprü gerekmez. Sınırlı mod **normaldir**.

```bash
cd lumos-core/ui
npm install
npm run dev
```

- Landing: http://127.0.0.1:4321/
- Panel: http://127.0.0.1:4321/panel

### Katman B (tam yerel)

Köprü + görev sunucusu + sohbet için:

- [Yerel köprü runbook](docs/local-kando-dev-runbook.md)
- [welockai.com/#kurulum](https://welockai.com/#kurulum)

## İlgili

- [docs/tr/](docs/tr/) — Türkçe belge dizini (stub)
- [We Lock AI](https://welockai.com/)
