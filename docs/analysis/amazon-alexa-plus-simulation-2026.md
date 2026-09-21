# Amazon Alexa+ web simülasyonu — 2026

> **Tarihsel (2026-09-18, #854; 2026-09-21 teyit).** `84c5709` web simülasyonu
> 16 Eylül yön değişikliğinden önceki denemedir. Gerçek MCP uygulaması veya
> yarışma kabul kanıtı değildir; genişletilmez ve nihai demo diye sunulmaz.
> 2026-09-21 canlı karşılaştırma (`origin/main` `ea83c338` ·
> `amazon-build-ship-shape-2026` `a55f01d7`): bu dosyalar **tarihsel kalıntı**
> olarak durur. `npm run e2e:alexa-plus-sim` güncel `main` `package.json`
> içinde **yoktur** — Amazon dalındaki e2e kancası `e2e:webmcp:mock` etiketini
> geriletirdi; kanca bu replay'e alınmadı. Güncel dilim:
> [`amazon-alexa-plus-mcp-2026.md`](amazon-alexa-plus-mcp-2026.md)
> (`python -m alexa_plus_mcp`, MCP 2025-11-25 Streamable HTTP).

## Kapsam

Bu çalışma `amazon-build-ship-shape-2026` dalında, 31 Ağustos 2026 sonrasında
oluşturulan yarışma dilimidir. Lumos paneli ve insan onaylı görev akışı önceden
vardı; yarışma dönemindeki yeni parça `/alexa-plus-simulasyon` deneyimidir.

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

## Kanıt (tarihsel; yarışma kanıtı değil)

Amazon dalında bu sayfa `npm run e2e:alexa-plus-sim` ile koşulmuştu. Güncel
`main` üzerinde o kanca yok ve eklenmez. Kilit: `tests/test_alexa_plus_mcp.py`
içindeki `test_simulation_page_is_marked_historical` — sayfa "tarihsel" der,
MCP sunucusunu işaret eder, yarışma kabul kanıtı iddiası taşımaz.
