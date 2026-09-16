# Amazon Alexa+ web simülasyonu — 2026

## Jüri SHA

Çalışan demo ve e2e bu commit’e bağlıdır:

- repo: `candasoz01-cmd/lumos-core`
- dal: `amazon-alexa-plus-demo-ready-20260916`
- SHA: `53fd83aff48806ba07b8cf0bd9064d76cc3f081d`
- yüzey: `/alexa-plus-simulasyon`
- lisans: Apache-2.0 (`LICENSE`)

Bu SHA 2026-09-16T10:00Z itibarıyla local commit’tir; remote’a push edilmedi.
Jüri `git checkout` ancak push sonrası bu SHA’yı görür.

Bu SHA gerçek Alexa+ servisi, cihaz veya Amazon hesabı bağlamaz. Amazon
hackathon kurallarındaki web tabanlı Alexa+ deneyim simülasyonudur.

## Jüri çalıştırma

Node.js ≥ 22.12 gerekir. Playwright Chromium bir kez kurulur.

```bash
git clone https://github.com/candasoz01-cmd/lumos-core.git
cd lumos-core
git checkout 53fd83aff48806ba07b8cf0bd9064d76cc3f081d
cd ui
npm install
npx playwright install chromium
npm run build
npm run e2e:alexa-plus-sim
```

Beklenen satır: `ALEXA_PLUS_SIM_E2E_RESULT: PASS`.

Elle bakmak için build sonrası:

```bash
npm run preview
```

Tarayıcı: `http://127.0.0.1:4321/alexa-plus-simulasyon` (macOS’ta `127.0.0.1`
kullan; IPv6 `localhost` sapması olmasın). Varsayılan istek zaten doludur.
**Görevi hazırla** → panel onayında başlık `Servis ziyareti` ve zaman
`Yarın 14:00` → **Onayla**. Görev yazılmazsa **Vazgeç** yeter.

`npm run build` sırasında `color:{ACCENT}` CSS minify uyarısı görülebilir;
e2e PASS ile çelişmez.

## Kapsam

Bu çalışma `amazon-build-ship-shape-2026` dalında, 31 Ağustos 2026 sonrasında
oluşturulan yarışma dilimidir. Lumos paneli ve insan onaylı görev akışı önceden
vardı; yarışma dönemindeki yeni parça `/alexa-plus-simulasyon` deneyimidir.
Hazır demo SHA’sı yukarıdaki `53fd83a` düzelmesini içerir.

Bu yüzey gerçek Alexa+ servisi değildir. Amazon hackathon kurallarında izin
verilen web tabanlı Alexa+ deneyim simülasyonudur. Kullanıcı isteğini dar bir
görev sözleşmesine dönüştürür ve mevcut Lumos panelinin `proposeTask` köprüsünü
çağırır. Görev, paneldeki insan onayı verilmeden yazılmaz.

## İlk çalışan dilim

1. Kullanıcı kısa bir görev isteği yazar.
2. Simülasyon başlık, öncelik ve zaman notunu çıkarır.
3. Lumos paneli bütün yazılacak alanları kendi onay diyaloğunda gösterir.
4. `Vazgeç` hiçbir görev oluşturmaz; `Onayla` panelin normal görev yolunu kullanır.
5. Başlatma ve sonuç olayları zaman damgasıyla tarayıcı `localStorage` alanında
   tutulur ve JSON indirilebilir.

## Dürüstlük ve veri sınırı

- Alexa+ bağlantısı, Alexa cihaz testi veya gerçek MCP sunucusu iddia edilmez.
- Ham kullanıcı cümlesi olay kaydına yazılmaz; yalnız çıkarılan görev alanları
  ve sonuç tutulur.
- Bulut veritabanı yoktur. Vercel/başka statik barındırma kullanılsa bile olay
  kaydı kullanıcının tarayıcısında kalır.
- Bu ilk dilim serbest dil anlama iddiası taşımaz; görev cümleleri için dar,
  deterministik bir ayrıştırıcıdır.

## Kanıt

Komutlar ve beklenen satır yukarıdaki **Jüri çalıştırma** bölümündedir; SHA
`53fd83aff48806ba07b8cf0bd9064d76cc3f081d`. Test aynı kökenli simülasyon
sayfasından Lumos panel köprüsünü çağırır, onay diyaloğunu kontrol eder,
görevi onaylar ve ham cümlenin olay kaydına yazılmadığını doğrular.
