# ADR-001: Lumos Quantum ve İleri Modül Yönü (Taslak)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / hipotez** — kesinleşmiş mimari karar değildir; bkz. [Güncel durum](#güncel-durum-2026-06-11) |
| Tarih | 2026-06-05 (güncel durum: 2026-06-11) |
| İlgili | Panel geliştirme günlüğü, ileri katman araştırmaları, `ROADMAP.md`, [ADR-013](ADR-013-lumos-quantum-security-readiness.md) (Quantum Security Readiness MVP) |

## Güncel durum (2026-06-11)

Kuantum alanı Lumos'ta **kaldırılmadı, iptal edilmedi ve "hiç çalışılmadı" sayılmaz**. Bugün **aktif üretim özelliği değildir**; geçmişte vizyon, taslak, placeholder, demo ve araştırma düzeyinde ele alınmıştır.

| Boyut | Durum |
|------|-------|
| Üretim özelliği | Yok — panelde görünür iskelet / demo düzeyi |
| Geçmiş çalışma | Vizyon notları, bu ADR taslağı, `lumos-quantum/` placeholder alanı, panel kuantum modülü iskeleti |
| IBM / ücretli API | Aktif kullanım yok; maliyet henüz açılmadı — bu **iptal veya vazgeçme** anlamına gelmez |
| Gelecek aday | Lumos güvenlik mimarisinde kuantum tabanlı güvenli iletişim / anahtar dağıtımı |

**Dürüst ifadeler:** "Kuantum üretim özelliği mevcut" veya "hiç çalışılmadı" yazılmamalıdır. Ücretli API'nin açılmamış olması, alanın terk edildiği anlamına gelmez.

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
| Quantum üretim entegrasyonu | Erken hedef değil; alan iptal değil — araştırma / aday |
| IBM / ücretli quantum API | Maliyet açılmadı; aktif entegrasyon yok — vazgeçme değil |

## Sonuç (geçici)

Bu belge **mimari yön taslağıdır**, uygulanmış karar listesi değildir. İlk somut adımlar panel ve çekirdek stabilizasyonu ile sınırlı kalmaya devam eder; ileri modüller ayrı ADR veya checkpoint belgeleriyle güncellenecektir.

## Quantum Security Readiness (ADR-013)

Kuantum alanının somut MVP tanımı — **Lumos Quantum Readiness** (yerel, salt okunur, kanıtlı kuantum sonrası güvenlik hazırlık tarayıcısı), rapor alanları, Entropy Lab sınırları, panel spesifikasyonu — **[ADR-013](ADR-013-lumos-quantum-security-readiness.md)** belgesindedir. Bu ADR (001) yön ve öncelik taslağını korur; readiness ayrıntısı ADR-013'e bırakılır.

## Sonraki gözden geçirme

- Temel routing + trust + memory tasarımı için ayrı ADR veya checkpoint
- IBM / quantum POC gereksinimleri netleşince ADR-002 veya bu belgenin revizyonu
- Readiness Faz-2 probe — bkz. ADR-013 (onay gerekir)
