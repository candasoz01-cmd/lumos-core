# ADR-015: Lumos Service API Gateway

| Alan | Değer |
|------|-------|
| Durum | **Kabul edildi — public foundation; üretim taşıması bekliyor** |
| Tarih | 2026-07-15 |
| İlgili | ADR-004, ADR-006, ADR-007, ADR-010, `docs/integrations-overview.md` |

## Karar

Lumos; AI modelleri, araçlar, iletişim, sosyal medya, toplantı, ses/cihaz, bölgesel ağ ve kamu hizmeti adaptörlerini tek bir dış sözleşme altında toplayan **hizmet geçidi** olacaktır.

Bu kararın teknik karşılığı **Lumos API** adıdır. Son kullanıcı ve geliştirici Lumos ile konuşur; sağlayıcı seçimi, bölgesel uygunluk ve geri dönüş sırası Lumos tarafından planlanır. Sağlayıcılar kendi verilerinin ve yetkilendirmelerinin sahibi olmaya devam eder.

Bu public `service_gateway`, ADR-004'te kararı bekleyen birleşik AI Router değildir. Yalnızca hizmet ailelerini ve değişmeyen güven sözleşmesini sunan metadata/plan katmanıdır; model seçmez, dış çağrı yürütmez ve ADR-004'ün import/drift kapısını değiştirmez.

## Hizmet aileleri

| Aile | Hedef yol | Örnek kapsam |
|------|-----------|--------------|
| AI | `/v1/chat` | Sohbet, araç kullanımı, çoklu ortam |
| Güvenlik | `/v1/security/check` | Risk ve politika kontrolü |
| Kimlik | `/v1/verify` | Kimlik ve belge doğrulama |
| Araçlar | `/v1/tools` | Çeviri, özet, arama, video |
| Entegrasyonlar | `/v1/integrations/route` | Mesajlaşma, sosyal, toplantı, iş araçları, cihaz |
| Bölgesel ağ | `/v1/regional/route` | Bölgeye uygun sağlayıcı ve politika seçimi |
| Kamu hizmetleri | `/v1/public-services/route` | Kimlik, sağlık, eğitim, vergi, belediye ve belge sistemleri |

Bu yollar **hedef sözleşmedir**. Bu ADR, `api.lumos.ai` alan adının veya üretim HTTP uçlarının bugün canlı olduğunu iddia etmez.

## Değişmeyen güven çizgisi

Her hizmet ailesi aynı sırayı izler:

1. İstek doğrulama
2. Güven anlık görüntüsü
3. Politika kararı
4. Açık onay kapısı
5. Sağlayıcı yönlendirmesi
6. Yürüt veya reddet
7. Hassas veriden arındırılmış denetim kaydı

Dış etki oluşturan yazma, yayımlama, ödeme, kimlik doğrulama sonucu kullanma veya kamu sistemine işlem gönderme adımı onaysız çalışmaz. Router, güvenlik veya onay katmanını geçemez; yalnızca bu katmanların kararını tüketir.

## Kamu hizmetleri sınırı

Kamu hizmetleri Lumos'un devleti veya kurumu yönetmesi anlamına gelmez. Bu aile, yalnızca yetkili resmi API'ler ve sözleşmeli adaptörler üzerinden kurumlar arası veri/işlem senkronunu kapsar.

- Ülke ve kurum politikası adaptörden önce gelir.
- Kimlik bilgisi, vatandaş verisi veya resmi erişim anahtarı public repoya gömülmez.
- Resmi sistem kaynak otorite olarak kalır.
- Bölgesel veri yerleşimi ve kayıt saklama kuralları yönlendirme sinyalidir.
- Gerçek kurum bağlantısı private/controlled-access katmanda açılır.

## OSS uygulama sınırı

Public temel şu an şunları sağlar:

- `service_gateway` sağlayıcısında hizmet ailesi ve güven sözleşmesi keşfi,
- yürütme yapmayan `plan_route` çıktısı,
- `global_catalog` içinde kamu hizmeti adaptör aileleri,
- hiçbir gömülü kimlik bilgisi veya sahte bağlantı başarısı olmaması.

Public temel şunları sağlamaz:

- üretim HTTP sunucusu veya canlı `api.lumos.ai`,
- otomatik sağlayıcı seçip dış çağrı yürütme,
- gerçek devlet/kurum hesabına bağlanma,
- onaysız yazma, yayımlama, ödeme veya resmi işlem.

## Yanıt sözleşmesi hedefi

Üretim yönlendirmesi eklendiğinde yanıt, sağlayıcıyı tamamen görünmez kılmamalıdır. En az şu kanıt alanları taşınır: seçilen sağlayıcı, seçim gerekçesi, bölge/politika sınırı, fallback durumu, onay durumu ve audit kimliği.

## Sonuç

Hizmet alanı genişleyebilir; güven çizgisi değişmez. Lumos sağlayıcıların yerine geçmez. Sağlayıcıları tek, anlaşılır, denetlenebilir ve kullanıcı onaylı kapıda birleştirir.
