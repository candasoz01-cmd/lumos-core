# ADR-001: Lumos Quantum ve İleri Modül Yönü (Taslak)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / hipotez** — kesinleşmiş mimari karar değildir |
| Tarih | 2026-06-05 |
| İlgili | Panel geliştirme günlüğü, ileri katman araştırmaları |

## Bağlam

Lumos çekirdeğinde güvenlik, yetki ve workspace sözleşmesi önceliklidir. Bu ADR, ileride değerlendirilebilecek **modüler yetenek alanlarını** kayıt altına alır. Buradaki ifadeler **öneri ve hipotez** düzeyindedir; ürün veya kod tabanında finalize edilmiş bir mimari olarak sunulmamalıdır.

## Taslak modül alanları (henüz karar değil)

Aşağıdaki başlıklar araştırma ve olası yön olarak not edilmiştir:

1. **AI Firewall** — Model ve araç çağrıları için politika, filtre ve sınır katmanı (*hipotez*).
2. **AI Router** — İstekleri yetki, maliyet ve güvenilirlik kriterlerine göre yönlendirme (*hipotez*).
3. **Memory Graph** — Oturumlar ve görevler arası ilişkisel bellek modeli (*hipotez*).
4. **Trust Engine** — Kaynak, eylem ve çıktı güven skoru (*hipotez*).
5. **Agent Network** — Koordineli ajanlar arası görev paylaşımı (*hipotez*).
6. **IBM services** — Olası harici entegrasyon adayları; kapsam ve lisans net değil (*bilinmiyor / sonra değerlendirilecek*).
7. **Quantum optimization** — Belirli optimizasyon problemleri için kuantum veya kuantum-esinli yaklaşımlar (*uzun vadeli araştırma*).

## Öncelik sırası (taslak hipotez)

**Quantum erken hedef değildir.** Önce şu alanların oturması önerilir (kesin sıra henüz onaylanmadı):

1. Güvenli yönlendirme (routing) ve politika sınırları
2. Trust / güven değerlendirme modeli
3. Bellek (memory) ve bağlam tutarlılığı
4. Ajan koordinasyonu ve görev sınırları

Quantum ve IBM tarafı, üstteki temeller netleşmeden üretim hedefi olarak konumlanmamalıdır.

## Bilinçli olarak ertelenen / beklemede

| Konu | Durum |
|------|-------|
| AI Gateway / canonical layer | Beklemede — daha sonra güçlü modelle tekrar ele alınacak |
| Jilee | Ayrı fikir; gözlemde, ürüne aktarılmadı |
| Quantum üretim entegrasyonu | Erken hedef değil |

## Sonuç (geçici)

Bu belge **mimari yön taslağıdır**, uygulanmış karar listesi değildir. İlk somut adımlar panel ve çekirdek stabilizasyonu ile sınırlı kalmaya devam eder; ileri modüller ayrı ADR veya checkpoint belgeleriyle güncellenecektir.

## Sonraki gözden geçirme

- Temel routing + trust + memory tasarımı için ayrı ADR veya checkpoint
- IBM / quantum POC gereksinimleri netleşince ADR-002 veya bu belgenin revizyonu
