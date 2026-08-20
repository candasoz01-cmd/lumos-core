# ADR-030 — Organizasyon ağacı ve görev ayrılığı

> 2026-08-20 kurucu kararı: kod yok. ADR-029 alan sorumluluğunu kilitledi;
> bu ADR o sorumluluğun **nasıl taşındığını** ve **çekirdeğin ne olmadığını**
> kilitler. **Bu ADR kod yazma izni değildir.** Dashboard Health uygulama
> dilimini, ajan orkestrasyon katmanını veya `#770` merge’ini açmaz.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (çerçeve, 2026-08-20)** — ağaç + görev ayrılığı kilitli |
| Uygulama durumu | Uygulanmadı — rol runtime’ı, oylama motoru, yeni ajan katmanı yok |
| Tarih | 2026-08-20 |
| Üst ilişki | [ADR-029](ADR-029-dashboard-health-earned-responsibility.md); [ADR-028](ADR-028-standing-low-risk-merge-approval.md); [ADR-018](ADR-018-internal-layers-core-local-sentinel.md) (ad çakışması aşağıda); [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) |
| Merge kapısı | Governance. ADR-028 standing hattı **yok**. İnsan onayı şart |

## Karar 1 — Sorumluluk tek olabilir; ekip birden fazla olabilir

Model **“bir alan = bir ajan” değildir.**

- Bazı alanlarda tek sorumlu yeter.
- Kritik alanlarda küçük bir çalışma ekibi gerekir.
- **Sorumlu alan sonucu sahiplenir.** Altındaki uzmanlar üretir, denetler,
  tutarlılığı kanıtlar.

Unvan ve “core team / core service / çekirdek ajan” etiketi **gerçek yetki
ve kabiliyete** dayanır; bir alanı gerçekten taşıyan yapı o alanın
sorumluluğunu **kazanır** (ADR-029 merdiveni). Otomatik miras yok.

## Karar 2 — Görev ayrılığı (icra ≠ doğrulama ≠ kayıt)

```text
İcra eden  ≠  doğrulayan  ≠  nihai durum kaydını üreten
```

Bir ajan değişikliği hazırlayabilir; başka bir ajan sonucu **bağımsız**
kontrol eder. Gerektiğinde üçüncü rol **tutarlılık kontrolü** yapar:
iş sözleşmeyle, mevcut sistem durumuyla ve diğer ajan raporlarıyla
uyuşuyor mu?

Birbirinin işini denetlerler; birbirinin sonucunu **körü körüne
onaylamazlar.**

### Kör çoğunluk yok

İki ajan farklı sonuç veriyorsa Lumos **“2'ye 1, devam” demez.** Kanıtları
karşılaştırır, çelişkiyi görünür kılar; çözemiyorsa `unknown` /
`conflict` olarak **yükseltir.** Kritik işte fail-closed.

### Risk ölçekler

Her alan dört ajan kullanacak diye kural **yok.** Risk yükseldikçe görev
ayrılığı artar.

| Risk | Yeterli ayrılık (v1 çerçeve) |
| --- | --- |
| Basit, geri alınabilir, düşük-risk | Tek yürütücü + otomatik test |
| Security / privacy / permission / finance / çekirdek | Bağımsız denetim **şart** |

Dashboard Health ileride şöyle **büyüyebilir** — bugünün uygulama emri değil:

```text
Observer → Executor → Verifier → Consistency check → Evidence/status
```

Gözlem ayağı kanıtlanmadan düzeltme/yükseltme runtime’ı açılmaz
([dashboard-health-v1](../contracts/dashboard-health-v1.md) adayı, `#770`).

## Karar 3 — Ağaç: gövde / ana dal / yan dal / çekirdek

```text
çekirdek (küçük, zor değişir)
  ⊂ gövde (ortak omurga)
      → ana dal (kazanılmış sorumluluk alanı)
          → yan dal (uzman kabiliyet)
              → araç (değiştirilebilir)
```

| Katman | Ne | Ne değil |
| --- | --- | --- |
| **Gövde** | Ortak organizasyon omurgası: kimlik, yönetişim, ortak sözleşmeler, yapıyı tutan kurallar | Her önemli ürün özelliği |
| **Ana dal** | Başlı başına sorumluluk alanı (Mail, Cyber, Pay/POS, Lab, cihaz/agent … büyüdükçe) | Otomatik “çekirdek” |
| **Yan dal** | Ana dalın altındaki uzman kabiliyet (ör. Mail’de provider; Cyber’de bir analiz yeteneği) | Ana dalın kendisi |
| **Çekirdek** | Sistemin kimliğini veya değişmez çalışma sınırlarını belirleyen **küçük ve korunmuş** katman | “Önemli olan her şey”; değerli her entegrasyon |

**Bir şey çok değerli olabilir ama yine de çekirdek olmayabilir.**

Büyüme kuralı: çekirdek küçük ve zor değişir; gövde sağlamdır; ana dallar
sorumluluk **kazanır**; yan dallar çoğalabilir; **araçlar gerektiğinde
değiştirilebilir.** Lumos büyür, kimliği sulanmaz.

Yarın “bu entegrasyon çok önemli, bunu da core yapalım” denirse cevap:
önem ≠ çekirdek. Aksi halde altı ay sonra gövdeden çok çekirdek olur.

## Karar 4 — OpenAI ailesi çekirdek ilan edilmez

“OpenAI’nin Lumos oluşumunda ve temel çalışma mimarisinde özel yeri var”
**≠** “bütün OpenAI ürünleri anayasal çekirdektir.”

Piyasadan sonradan takılan sıradan bir yan araç gibi de silinmez. Konumu:
oluşturucu / temel çalışma katmanına ait **araç-omurga ilişkisi**; ürün
kataloğunun tamamı çekirdek **değildir.** Yeni OpenAI yüzeyi varsayılan
çekirdek genişlemesi değildir (STOP LIST / ADR-019 sırası durur).

## Ad çakışması — ADR-018 `Core` ≠ bu çekirdek

[ADR-018](ADR-018-internal-layers-core-local-sentinel.md) iç katman adı
**Core** (eski Kando) kullanıcıya gösterilmeyen koordinasyon katmanıdır.
Bu ADR’deki **çekirdek**, anayasal küçük sınır katmanıdır. İkisi eşlenmez.
İç katman `Core` yazmak bir alanı anayasal çekirdek yapmaz.

## Bilinçli yapılmaz

- Yeni agent / orchestration katmanı (STOP LIST)
- `#764` / `#770` dosyalarına dokunmak veya onları standing ile merge etmek
- Dashboard Health’e dört ajanlık runtime yazmak
- Her değerli servisi çekirdeğe almak
- Anlaşmazlıkta oy çokluğu
