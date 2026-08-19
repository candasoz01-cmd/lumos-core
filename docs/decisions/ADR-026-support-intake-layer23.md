# ADR-026 — Destek intake: sınıflandırma öneri, ticket yazma onay

> 2026-08-19 kurucu yönlendirmesi: kullanıcı organizasyon şemasını bilmek
> zorunda kalmaz; destek akışı paneldeki "hayata alan aç" ilkesinin Layer
> ayrımına oturur. **Bu ADR kod yazma izni değildir.** STOP LIST (yeni
> entegrasyon / yeni sayfa / yeni orchestration) ihlal edilmez. Uygulama,
> cyber/STT/görsel/embedding/moderasyon oturup ölçüm haftası bittikten sonra
> ayrı açık kararla açılır.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (tasarım, 2026-08-19)** — akış kilitli; kod sırasına girmez |
| Uygulama durumu | Uygulanmadı — ticket UI yok, LLM sınıflandırıcı yok, kanal yazıcı yok |
| Tarih | 2026-08-19 |
| Üst ilişki | [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) §Karar katmanları; [`lumos-log-vs-approval.md`](../analysis/lumos-log-vs-approval.md); CU4 onay iskeleti; ops dürüstlük (`stale`/`unknown`) Layer 1A ile **aynı ilke, ayrı taksonomi** |
| Canlı destek (bugün) | [`support-channel-alpha.md`](../analysis/support-channel-alpha.md) — Slack `#lumos-pilot-support`; bu ADR onu değiştirmez |

## İsim sınırı (karışmasın)

Bu belgedeki **Layer 2 / Layer 3**, karar sözleşmesindeki **«Öner ama bekle»**
ve **«Açık onayla uygula»** katmanlarıdır. Ops **Layer 1A** pulse, grounded-phase
roadmap katmanları veya OD-033 connector katmanları **değildir**. Karışırsa
güven kaybolur.

| Bu akışta | Karar sözleşmesi | Ne üretir |
|-----------|------------------|-----------|
| Sınıflandırma | Öner ama bekle | Öneri. Kesin durum değil. Kullanıcı düzeltir. |
| Ticket açma | Açık onayla uygula | Dış yazma. Ajan doğrudan yazmaz. |
| Durum söyleme | Sadece cevap ver | Yalnız doğrulanabilir iddia. |

## Neden şimdi kod yok

Bu özellik entegrasyon kapatmaz; entegrasyonların **üstüne** kurulur:
amaç-bazlı model (`OPENAI_MODEL_CHAT` / `_CYBER` / `_STT`), envanterden
teknik bağlam, Layer 3 onay yüzeyi. Cyber fail-closed ve STT açılış kapısı
önce oturmalı. Sıranın **sonrası**.

## Akış (v1 hedefi — yalnız sınıflandırma + onaylı ticket)

```
Kullanıcı derdini söyler
  → Layer 2: sabit kategoriden önerir + gözlemlenen bağlamı toplar
  → Kullanıcıya literal önizleme:
      kategori (düzeltilebilir)
      kanal (kod eşlemesi; LLM üretmez)
      bağlam (sürüm, yüzey, zaman — çıkarım ayrı işaretlenir)
      metin = kullanıcının sözü, LLM özeti DEĞİL
      "Göndereyim mi?"
  → Kullanıcı onaylar (Layer 3 / CU4 tarzı kapı)
  → Ticket açılır
  → "İletildi. Takip no: X."
```

Bildirim vaadi (push) yok. İnsan cevabı garanti değil.

## Sabitler

1. **Kategori listesi kodda kapalı.** LLM yalnız şunlardan birini önerir:
   `bug` | `özellik` | `hesap` | `güvenlik` | `genel`. Serbest kanal/yol üretemez.
2. **Kategori → kanal eşlemesi kodda, LLM'in erişemeyeceği yerde.**
   Injection yüzeyi: serbest metin sınıflandırmayı manipüle edemez.
3. **Onay ekranı literal ticket'tır** — merge onayındaki gibi ajan özeti değil.
4. **Gözlenen bağlam ≠ çıkarım.** Sürüm/istemci/saat ölçülürse "gözlem";
   "ses modülü" gibi yorum Layer 2'dır ve düzeltilebilir.
5. **`güvenlik` yukarı yapışkan.** LLM veya kullanıcı kategoriyi `güvenlik`'e
   yükseltebilir. `güvenlik` → `genel` düşürmek ikinci açık onay ister
   (yanlış kuyruk + injection).
6. **Hedef sistem (Linear / GitHub / Slack) seçilmedi.** Eşleme sabittir;
   yazma ucu ayrı karardır. P1-04 Slack bugünün canlı hattıdır.
7. **Pull sorgusu ayrı yetenektir.** "Bu numarayla durumu buradan sor"
   cümlesi, okuma yüzeyi yokken söylenmez — push vaadinin dürüstlük tuzağı
   pullda da oluşur. v1 kapanışı: **"İlgili ekibe iletildi. Takip numaran: X."**
   Okuyucu gelince pull cümlesi ayrı dilimde açılır.
8. **Amaç karışmaz.** Destek sınıflandırması `OPENAI_MODEL_CYBER` veya STT
   yolunu kullanmaz. Realtime ve gerçek Meet sesi ADR-025 kapısındadır.

## Dürüstlük (Layer 1A `stale` ile aynı ilke)

Bilmiyorsan "iyi" / "haber vereceğim" deme. Ticket açıldıysa numara gerçektir.
Durum değişimini görecek sistem yoksa bildirim vaat etme.

## STOP LIST

Kod, yeni sayfa, yeni entegrasyon veya yeni orchestration **şimdi yok**.
Ölçüm haftası + çalışan entegrasyonlar + gerçek Layer 1 verisi sonrası
**yalnız sınıflandırma + onaylı ticket, bildirim vaadi yok** ilk sürüm olarak
ayrı kurucu kararıyla konuşulur.
