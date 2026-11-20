# Microsoft EMEA siber dayanıklılık planı — kaynak adayı

| Alan | Değer |
| --- | --- |
| Durum | Kaynak adayı. Lumos kararı değildir. Kitap metni değildir |
| Tarih | 2026-09-26 |
| Karar günlüğü | Yeni LUMOS kimliği açılmadı. Dış eşleme yöntemi [LUMOS-0013](./BACKLOG.md) ile aynı türdedir; bu not onu tekrarlamaz |
| Outline | `lumos-book-v0.1` dondurulmuş. `docs/lumos-book-outline.md` değişmedi |

Microsoft ürün ve pazarlama cümleleri burada gerçek veya Lumos kararı değildir.
Belgenin kendi uyarısı: genel bilgi, hukuk tavsiyesi değil, doğruluk garantisi yok
(basılı s. 50; içindekiler öncesi uyarı).

## Belge

| Alan | Değer |
| --- | --- |
| Pazarlama adı | The blueprint for cyber resilience in EMEA |
| Kapak adı | The blueprint for cyber resilience in the AI-energetic era |
| Kapanış başlığı | The blueprint for cyber resilience in EMEA (basılı s. 50) |
| Yazar | Microsoft Corporation |
| PDF | 50 sayfa; oluşturulma 2025-11-03 |
| İndirme | `https://info.microsoft.com/ww-landing-blueprint-for-cyber-resilience-emea.html` formunun yönlendirdiği `marketingassets.microsoft.com/gdc/gdcopfWZZ/original` |
| Sayfa | Aşağıdaki numaralar belgedeki basılı altbilgi numaralarıdır |

s. 5 «AI-agentic era» der; kapak «AI-energetic era» der. Aynı dosyadır.

## Sınıflar

| Bulgu | Sınıf | Microsoft | Lumos dayanağı |
| --- | --- | --- | --- |
| Dış veri güvenilmez; aynı kapıdan geçer | kısmen var | s. 24, s. 48 | [LUMOS-0014](./BACKLOG.md): dış veri güvenilmez. Kapsam kimlik sürekli doğrulaması değil, giriş verisidir |
| En az yetki | zaten var | s. 6, s. 24, s. 34 | [ADR-008](../decisions/ADR-008-agent-network-boundary.md) ilke 2; karar sözleşmesi üç profil, critical/external kapalı |
| İnsan gözetimi, son karar kullanıcıda | zaten var | s. 12, s. 29, s. 30 | Kitap ana tezi; [LUMOS-0015](./BACKLOG.md); [LUMOS-0016](./BACKLOG.md) adım 4; ADR-008 ilke 4; [SEC-042](../security-architecture.md) onay yalnız riskli kapıda |
| Log, iz, kim onayladı | zaten var (ilke) | s. 30 | ADR-008 ilke 7; [LUMOS-0009](./BACKLOG.md); [LUMOS-0016](./BACKLOG.md); [ADR-031](../decisions/ADR-031-task-execution-grant.md) defter kanıttır, kapı değildir |
| «Kim, kim adına» kodda | kısmen var | s. 30 | İlke [LUMOS-0016](./BACKLOG.md) ve ADR-024’te. Kod boşluğu [TD-16](../TECHNICAL_DEBT.md) |
| Sürekli kimlik doğrulaması | kısmen var | s. 24, s. 48 | SEC-042 deny default, tek kullanımlık ve süresi dolan yetki anahtarı. Adı konmuş sürekli oturum doğrulama programı yok |
| Düzenleyiciye sürekli uyum kanıtı | yeni bakış | s. 8, s. 35 | Lumos kanıtı kendi eylem ve onay izidir. Uyum skoru veya düzenleyici portalı yok |
| EU AI Act madde atfı | yeni kaynak | s. 12, s. 29, s. 30 | Repoda yükümlülük kaydı yok. s. 30, md. 10–15’i log, iz ve gözetime bağlar. Bu, Microsoft özetidir |
| NIS2 liste | yeni kaynak | s. 11 | Kayıt yok. 24 saat ihlal bildirimi Microsoft cümlesidir, direktif metni bu notta doğrulanmadı |
| DORA liste | yeni kaynak | s. 12 | Ürün yükümlülüğü olarak kayıt yok. Finans sektörü dış manzarası için kaynak adayıdır |
| Defender, Sentinel, Entra, Purview eşlemesi | Lumos için geçerli değil | s. 6, s. 11–12, s. 24–26, s. 33–35 | Ürün iddiası. Disclaimer bunu garanti dışı bırakır |
| Müşteri örnekleri | Lumos için geçerli değil | s. 37–40 | Belge bunlara «illustrative» der |
| Otomatik yanıt akışları | Lumos için geçerli değil | s. 25 | [SECURITY_NEVER_AUTO](../lumos-karar-sozlesmesi.md) kalıcı silme, dış yazma, geri dönüşsüz işlem ve kritik ayarı otomatik yapmaz |
| «EU AI Act forthcoming» | Lumos için geçerli değil | s. 12, s. 29 | Aynı dosya s. 30’da madde numarası verir. Hukuk durumu bu notla sabitlenmez |
| Küresel ölçüt olacağı tahmini | Lumos için geçerli değil | s. 46 | Öngörü |

## Kitap için kesin sayfalar

Bunlar alınacak cümle değil, bakılacak sayfadır. Hukuk cümlesi için kaynak
Microsoft sayfası değil, düzenlemenin kendi metnidir. [LUMOS-0016](./BACKLOG.md)
hukuk incelemesini açık bırakır.

1. s. 24 — «never trust, always verify»; yanında kimlik doğrulama, en az yetki, sürekli izleme.
2. s. 48 — sözlük: ihlal varsayımı ve kimlik ile erişimin sürekli doğrulanması.
3. s. 30 — EU AI Act md. 10–15 atfı; GDPR md. 13–22 atfı.
4. s. 12 — EU AI Act liste: risk sınıfı, açıklanabilirlik, insan gözetimi, log, piyasaya çıkış sonrası izleme. «Forthcoming» hukuk tespiti değildir.
5. s. 11 — NIS2 liste: risk, süreklilik, üçüncü taraf, tedarik zinciri, bildirim, yönetim kurulu sorumluluğu.
6. s. 12 — DORA liste: olay bildirim, üçüncü taraf ve bulut gözetimi, dayanıklılık testi.
7. s. 50 — disclaimer. Bu sayfa olmadan diğer altı sayfa kaynak olmaz.

## Bu notta olmayanlar

Kitap cümlesi, mimari değişiklik, özellik, yeni LUMOS kararı, çeviri ve
`docs/lumos-book-outline.md` düzenlemesi yoktur.
