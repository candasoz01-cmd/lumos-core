# ADR-016: Lumos ID + Memory Gateway

| Alan | Değer |
|------|-------|
| Durum | **Kabul edildi — public foundation; üretim taşıması bekliyor**. **Kısmen güncellendi: "Lumos ID = kullanıcı kimliği" tanımı [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) ile değişti (bkz. aşağıdaki not); I1-I6 hafıza ilkeleri aynen yürürlükte** |
| Tarih | 2026-07-15 (tanım güncellemesi: 2026-08-17) |
| İlgili | ADR-015, ADR-007, ADR-008, [ADR-024](ADR-024-lumos-identity-multi-subject-model.md), `docs/integrations-overview.md` |

## Karar

> **Güncelleme (ADR-024, 2026-08-17):** Aşağıdaki "Lumos ID, kullanıcının tek
> ve kalıcı kimliğidir" tanımı **yürürlükten kalkmıştır**. Lumos ID bir kimlik
> değil, **kimlik otoritesidir** (identity authority / trust root); kullanıcının
> kimliği, Lumos ID altındaki **insan öznesidir** ve yanında Lumos, cihaz, agent,
> servis özneleri vardır. Bu paragrafın "sağlayıcı sahibi değildir / sağlayıcılar
> yalnızca adaptördür" kısmı ile I1-I6 ilkelerinin tamamı **değişmeden geçerlidir**;
> yalnız "tek kimlik" ifadesi "insan öznesi" olarak okunur.

**Lumos ID**, kullanıcının tek ve kalıcı kimliğidir. Hiçbir sağlayıcı (OpenAI, Google/Gemini, Apple, GitHub, Gmail, Meta, vb.) bu kimliğin sahibi değildir; sağlayıcılar Lumos ID'ye bağlanan birer **kimlik adaptörü**dür. Sağlayıcı değişse veya eklense/çıkarılsa bile Lumos ID ve altındaki hafıza değişmez.

**Memory Gateway**, kullanıcı hafızasını bu tek kimlik altında, sağlayıcı bazında ayrılmış ve zorunlu kaynak etiketiyle saklar. Sağlayıcılar arası veri **hiçbir zaman otomatik paylaşılmaz**; çapraz kullanım yalnızca kullanıcının açık, kayıtlı onayıyla (ADR-015'teki aynı `requires_approval` sözleşmesi) mümkündür.

## İlkeler

| # | İlke |
|---|------|
| I1 | Lumos ID tekildir ve sağlayıcıdan bağımsızdır; hiçbir sağlayıcı token'ı veya hesabı kimliğin kendisi değildir. |
| I2 | Her hafıza kaydı zorunlu `source_provider` etiketi taşır; etiketsiz kayıt kabul edilmez. |
| I3 | Veri sağlayıcı bazında bölmelenir (per-provider segregation); bir sağlayıcının verisi varsayılan olarak yalnızca o sağlayıcının bağlamında görünür. |
| I4 | Sağlayıcılar arası otomatik veri paylaşımı yoktur. |
| I5 | Çapraz kullanım (bir sağlayıcının verisini başka bir bağlamda kullanmak) yalnızca açık kullanıcı onayı ile, onay kaydı tutularak yapılabilir. |
| I6 | Sağlayıcı ekleme/çıkarma/değiştirme Lumos ID veya mevcut hafızayı bozmaz; yeni sağlayıcı eklemek yalnızca yeni bir adaptör kaydı kadar basit olmalıdır (registry'ye yeni `provider` eklemek). |

## Değişmeyen güven çizgisi

Memory Gateway, ADR-015'in yedi aşamalı güven zincirini kullanır: istek doğrulama → güven anlık görüntüsü → politika kararı → açık onay kapısı → sağlayıcı yönlendirmesi → yürüt veya reddet → hassas veriden arındırılmış denetim kaydı. Çapraz kullanım isteği bu zincirin **açık onay kapısı** adımını asla atlayamaz.

## OSS uygulama sınırı

Public temel şu an şunları sağlar:

- `lumos_id` sağlayıcısında kimlik + hafıza sözleşmesi keşfi (`describe_contract`),
- kayıtlı örnek kaynak etiketlerinin (sağlayıcı adaptörlerinin) keşfi (`list_memory_sources`),
- yürütme yapmayan çapraz kullanım planı (`plan_cross_use`) — her zaman onay ister, onaylansa bile gerçek veri taşımaz,
- hiçbir gerçek kullanıcı oturumu, gerçek hafıza deposu veya gerçek çapraz paylaşım yürütme yok.

Public temel şunları sağlamaz:

- üretim kimlik doğrulama/oturum sistemi (bu sınır ADR-007'nin private/controlled-access katmanında kalır),
- gerçek hafıza kaydı (disk/DB'de gerçek kullanıcı verisi),
- otomatik veya onaysız çapraz sağlayıcı veri paylaşımı,
- sağlayıcı hesaplarının gerçek bağlanması (bu, mevcut `*_provider.py` `verify_connection` sözleşmelerinin sorumluluğunda kalır; Memory Gateway bunların **üzerine** kaynak-etiketi ilkesini koyar, onların yerine geçmez).

## İlişki: mevcut sağlayıcılarla

Memory Gateway, mevcut `communications_provider.py`, `youtube_provider.py`, vb. sağlayıcıları **değiştirmez**. Her sağlayıcı kendi `verify_connection` sözleşmesiyle bağlanmaya devam eder; Memory Gateway yalnızca bu sağlayıcılardan gelecek/gelen verinin **hangi kaynak etiketiyle, hangi izinle saklanacağı ve çapraz kullanılıp kullanılamayacağı** sözleşmesini tanımlar.

## Sonuç

Sağlayıcı sayısı artabilir, sağlayıcılar değişebilir; Lumos ID ve hafıza ilkeleri değişmez. Lumos, kullanıcının kimliğini ve hafızasını hiçbir tek sağlayıcıya kilitlemez.
