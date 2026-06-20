# ADR-002: Mail / Inbox Intelligence (Taslak)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / gözlem** — public **demo-safe stub** mevcut (PR #413–#415); **ürün uygulanmamış**; kesinleşmiş mimari karar değildir |
| Tarih | 2026-06-06 |
| Revizyon | 2026-06-21 — OD-031 Phase 2 Step 4: public kod gerçeği + ADR drift düzeltmesi |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, onay ve yetki ilkeleri, ADR-001, [`public-repo-boundary.md`](../memory/public-repo-boundary.md) |

## Amaç

Lumos, kullanıcının **açık izni** ile e-posta okuyabilir ve gelen kutusunu **önem önceliğine** göre sunabilir. Bu ADR, böyle bir yetenek alanının ürün ve güvenlik sınırlarını **taslak** düzeyinde kayıt altına alır.

Bu belge **yalnızca dokümantasyondur**. Public repoda **demo-safe foundation stub** (`src/integrations/mail/`, `src/integrations/vault/`) vardır; **canlı OAuth handler, prod connector, panel UX ve gerçek posta ürün akışı uygulanmamıştır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). Mail okuma ve önerilen eylemler, bu sözleşmeyle uyumlu olmalıdır: onaysız okuma yok; onaysız dış etki yok.

Mail / Inbox Intelligence, ileride değerlendirilebilecek bir **ürün yönü taslağıdır**. Buradaki ifadeler **hipotez ve gözlem** düzeyindedir; finalize edilmiş veya uygulanmış bir özellik olarak sunulmamalıdır.

## Onay ve güvenlik sınırları (zorunlu)

Aşağıdaki kurallar, olası gelecek uygulama için **değiştirilemez ön koşullardır**; Lumos karar sözleşmesi ve onay ilkeleriyle hizalıdır.

| Eylem | Kural |
|-------|-------|
| Posta okuma | **Açık kullanıcı izni olmadan yapılmaz** |
| Gönderme | **Kullanıcı onayı olmadan yapılmaz** |
| Silme | **Kullanıcı onayı olmadan yapılmaz** |
| Arşivleme | **Kullanıcı onayı olmadan yapılmaz** |
| Etiketleme | **Kullanıcı onayı olmadan yapılmaz** |
| Harici / dış etkili aksiyonlar | **Kullanıcı onayı olmadan yapılmaz** |

Ek ilkeler:

- Lumos, kullanıcı adına **sessiz veya otomatik** posta işlemi yapmaz.
- Öneri ve taslak üretimi (ör. cevap taslağı) **simülasyon / önizleme** düzeyinde kalabilir; gerçek gönderim veya kutuda değişiklik yalnızca onay sonrası.
- Kalıcı silme ve geri dönüşsüz işlemler, mevcut çekirdek kurallarına uygun şekilde **açık komut + uyarı** gerektirir.
- Bu ADR, mail erişimi için ayrı bir izin akışının **önce** tanımlanmasını şart koşar (aşağıda).

## Önem kategorileri (taslak)

Gelen postalar, öncelik sunumu için aşağıdaki kategorilere ayrılabilir (*henüz algoritma veya model kararı yok*):

| Kategori | Kısa tanım |
|----------|------------|
| **acil** | Hızlı dikkat veya yanıt gerektiren ileti |
| **finans / fatura / ödeme** | Ödeme, fatura, banka veya mali içerik |
| **hesap güvenliği** | Şifre sıfırlama, 2FA, güvenlik uyarıları |
| **iş / proje** | İş, proje veya görevle ilişkili ileti |
| **kişisel** | Kişisel ve sosyal nitelikli ileti |
| **düşük öncelik / bildirim** | Bilgilendirme; acil aksiyon gerektirmeyen |
| **reklam / gereksiz** | Tanıtım, toplu veya düşük değerli içerik |

Kategori ataması **öneri** niteliğindedir; kullanıcı her zaman override edebilmelidir (gelecek tasarım hedefi).

## Mail kartı alanları (taslak)

Önem önceliğine göre sunulan her posta kartında hedeflenen alanlar:

| Alan | Açıklama |
|------|----------|
| **gönderen** | Gönderen adı veya adresi |
| **konu** | E-posta konusu |
| **kısa özet** | İçeriğin kısa, tarafsız özeti |
| **önem seviyesi** | Yukarıdaki kategorilerden biri |
| **neden önemli / düşük** | Sınıflandırma gerekçesinin kısa açıklaması |
| **önerilen aksiyon** | Lumos’un önerdiği sonraki adım (onay gerektirir) |
| **kaynak zaman** | Postanın alındığı / kaynak sistemdeki zaman |

**Tam kart modeli yok**; public stub yalnızca `MailMessageSummary` (4 alan: gönderen, konu, kısa özet, kaynak zaman). Önem seviyesi, sınıflandırma gerekçesi ve önerilen aksiyon **henüz kod/API yok**.

## Public kod gerçeği (demo-safe stub)

| Konu | Public stub | Ürün / private |
|------|-------------|----------------|
| Connector | `StubMailConnector` default; vault+grant OK → `GmailOAuthConnector` | Canlı mailbox prod akışı |
| OAuth | `oauth_contract.py` types/spec | HTTP handler, token exchange |
| Vault | `DemoVaultCredentialBridge` / env-gated adapter | Operatör credential yönetimi |
| Grants | `read` + `notify` validation; `send_reply` reddedilir | Tam izin akışı UX |
| API smoke | `LUMOS_GMAIL_SMOKE=1` operator-only | CI/default'ta kapalı |
| Send/archive/delete | Grant reddi / stub | Onaylı gönderim (ADR-009) |

Stub, izin akışını **substitute etmez**; ayrı UX/onay tasarımı hâlâ zorunludur.

## Önerilen aksiyonlar (taslak)

Aşağıdaki aksiyonlar Lumos tarafından **önerilebilir**; kutuda veya dış sistemde **değişiklik yapan** tüm adımlar kullanıcı onayı gerektirir:

| Önerilen aksiyon | Not |
|------------------|-----|
| **cevap taslağı hazırla** | Taslak üretimi; gönderim onay gerektirir |
| **sonra hatırlat** | Zamanlı hatırlatma önerisi; uygulama onay gerektirir |
| **takvime ekle** | Etkinlik / deadline önerisi; ekleme onay gerektirir |
| **düşük öncelik olarak işaretle** | Öncelik değişikliği önerisi; uygulama onay gerektirir |
| **kullanıcı onayıyla arşivle** | Arşivleme yalnızca açık onay sonrası |

Lumos, bu aksiyonları **otomatik uygulamaz**; yalnızca sunar veya onay bekler.

## Gelecek: ayrı mail erişim izin akışı

Herhangi bir uygulama (okuma, sınıflandırma, öneri) başlamadan **önce** tanımlanması gereken ayrı bir izin akışı:

1. Kullanıcıya mail erişiminin kapsamı açıkça anlatılır (ne okunur, ne okunmaz, ne saklanır).
2. Kullanıcı **bilinçli ve açık** onay verir; varsayılan kapalı kalır.
3. İzin geri alınabilir olmalıdır.
4. Sağlayıcı entegrasyonu **ürün olarak uygulanmamıştır**; public'te yalnızca demo-safe sözleşme tipleri ve stub arayüzleri vardır (PR #413–#415). Tam izin akışı ve operatör impl → **private katman**.

Bu akış onaylanmadan ve private impl paketi tamamlanmadan **prod entegrasyon çalışması başlatılmamalıdır**.

## Bilinçli sınırlar

| Konu | Durum |
|------|-------|
| Ürün kod / panel UI / canlı posta akışı | **Uygulanmamış** — yalnızca demo-safe stub + ADR |
| Public stub (`src/integrations/mail/`, `vault/`) | **Mevcut** — foundation; prod değil |
| Canlı OAuth / prod connector / gerçek posta | **Private impl bekliyor** |
| Otomatik gönder / sil / arşiv / etiket | **Yasak** (onaysız) |
| Jilee | **Lumos özelliği değildir**; ayrı fikir, gözlemde |
| Üretim vaadi | **Yok** — taslak / gelecek / gözlem |

Abartılı ürün vaadi yapılmaz. Bu belge, olası bir yönü kayıt altına alır; teslim tarihi veya tam kapsam taahhüdü içermez.

## Sonuç (geçici)

Mail / Inbox Intelligence, Lumos'un **izinli okuma + önem önceliği sunumu** hedefini tanımlayan **taslak ADR**dir. **Ürün uygulanmamıştır**; public demo-safe stub mevcuttur. Somut adımlar: (1) mail erişim izin akışının private tasarımı, (2) onay sınırlarının korunması, (3) onaylı private impl paketi.

## Sonraki gözden geçirme

- Mail erişim izin akışı için ayrı ADR veya checkpoint belgesi
- Önem sınıflandırma kuralları ve kullanıcı override modeli
- Public stub gerçeği revizyonu — **tamamlandı** (OD-031 Phase 2 Step 4); private impl checkpoint
- ADR-001 ile çakışmayan, çekirdek stabilizasyon sonrası uygulama değerlendirmesi
