# Destek Raporu — ORAA Şablonu

| Alan | Değer |
|------|-------|
| **Belge türü** | Destek / debug rapor şablonu (docs only) |
| **P1 ref** | P1-04 |
| **Akış** | **O**bservation → **R**easoning → **A**ction → **A**ssessment |

Pilot ve Alpha destek kanalına giden raporları kısa, tekrarlanabilir ve geliştirici dostu tutmak için minimum iskelet.

---

## ORAA akışı

| Adım | Soru | Not |
|------|------|-----|
| **Gözlem** | Ne gördün? | Ekran, hata metni, beklenen vs gerçekleşen |
| **Hipotez** | Muhtemel neden? | Tek cümle; kesin teşhis değil |
| **Test** | Ne denedin? | Adımlar, sıra, tekrar sayısı |
| **Sonuç** | Test ne gösterdi? | Düzeldi mi, aynı mı, farklı mı |
| **Rapor** | Destek ekibine ne ileteceksin? | Özet + kanıt (ekran görüntüsü, zaman damgası) |

---

## Örnek senaryo (genel)

**Konu:** Plan yükseltme sonrası kota / limit ekranda güncellenmiyor.

| Adım | İçerik |
|------|--------|
| Gözlem | Ayarlar → Plan ekranında hâlâ eski kota; ödeme onayı e-postası geldi. |
| Hipotez | Oturum önbelleği veya senkron gecikmesi; UI eski state gösteriyor olabilir. |
| Test | 1) Plan ekranını yenile 2) Çıkış yap / tekrar giriş 3) 5 dk bekle, tekrar kontrol |
| Sonuç | Yenileme ve logout/login sonrası hâlâ eski kota görünüyor. |
| Rapor | Aşağıdaki e-posta iskeleti + zaman damgalı ekran görüntüsü |

*Bu örnek herhangi bir SaaS / IDE abonelik senaryosuna uyarlanabilir; ürün adı zorunlu değildir.*

---

## Destek e-postası — açılış örneği

```text
Merhaba,

Geliştirici refleksiyle önce kendi tarafımda test ettim; kısa özet:

- Gözlem: [ne gördün]
- Denenen adımlar: [yenileme, logout/login, vb.]
- Sonuç: Sorun devam ediyor / [kısmen düzeldi]

Ekte zaman damgalı ekran görüntüsü var. Hesap / ortam: [anonim veya pilot ID].

Teşekkürler.
```

---

## Kontrol listesi (göndermeden önce)

- [ ] Plan / kota / ilgili ayar ekranı açık ve okunaklı
- [ ] Çıkış yap → tekrar giriş denendi
- [ ] Ekran görüntüsünde tarih/saat görünüyor
- [ ] Hâlâ bozuksa rapor gönder; düzelmişse destek yükü oluşturma

---

## İlgili

- [support-channel-alpha.md](../analysis/support-channel-alpha.md) — kanal + SLA (P1-04)
- [INTERNAL_ALPHA_OPERATIONS.md](../INTERNAL_ALPHA_OPERATIONS.md) — Alpha operasyon takibi

---

*Son güncelleme: 2026-06-26 — ORAA destek rapor şablonu.*
