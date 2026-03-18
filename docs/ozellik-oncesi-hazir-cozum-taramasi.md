# Özellik öncesi hazır çözüm taraması (özet)

**Amaç:** Sıfırdan geliştirmeden önce hazır alternatifleri görmek; gereksiz yükü azaltmak.

## Kontrol listesi

1. **SaaS** — Benzer ihtiyacı karşılayan hazır ürün var mı?
2. **Açık kaynak** — Eşdeğer veya kısmi OSS var mı?
3. **Ucuz / satın alınabilir** — Doğrudan alınabilecek düşük maliyetli çözüm var mı?

## Karar

- Yüksek benzerlik varsa: kısa karşılaştırma, **“yine de kendimiz mi yapalım?”** ve geliştirme/bakım yükünü net yaz.
- **Güçlü açık kaynak** aynı işi karşılıyorsa: **öner** → **neden kendi yapmaması gerektiğini** (bakım, güvenlik, süre, olgunluk) açıkla → **seçenek sun** (OSS / entegrasyon / sıfırdan).
- **Gereksiz iş reddetme (karar motoru):** Güçlü OSS / SaaS / çok ucuz hazır varken: (1) kısa analiz (2) 2–3 alternatif (3) “Sıfırdan mantıklı mı?” açık cevap (4) isterse yine uygula (5) **default önce öner**; **ek:** bilinçli sıfırdan → **gereksiz build = zaman kaybı** işaretle.
- Kullanıcı **ısrar ederse** sıfırdan veya kendi yoluyla: **yine uygula**; öneri kayıtlı kalsın, engelleme yok.
- OSS kullanımında: **lisans uyumu** şart; kör kopyalama yok; **minimal, anlaşılır entegrasyon**.

## Derinlik

| Talep | Tarama |
|-------|--------|
| Basit, risksiz | Kısa |
| Ürünsel, uzun | Zorunlu (SaaS + OSS + maliyet özeti) |

**Not:** Lumos onay, güvenlik ve çekirdek kuralları bu pratikten bağımsız kalır.

---

Ajan / editör ayrıntısı: `.cursor/rules/ozellik-oncesi-hazir-cozum-taramasi.mdc`.
