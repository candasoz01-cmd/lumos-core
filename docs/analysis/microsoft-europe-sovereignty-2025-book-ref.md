# Microsoft Avrupa dijital egemenlik (2025) — kitap ve mimari referans

| Alan | Değer |
|------|--------|
| **Belge ID** | `microsoft-europe-sovereignty-2025-book-ref` |
| **Durum** | `kayıt` — dış kaynak kartı; ürün kararı, ADR veya uygulama taahhüdü değil |
| **Tarih** | 2026-09-13 |
| **Dil** | Türkçe |
| **Ana katman** | Research Memory + Vision Memory (kitap kaynağı) |
| **Üst sınır** | [`docs/lumos-book-outline.md`](../lumos-book-outline.md) v0.1 dondurma; [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md); [ADR-012](../decisions/ADR-012-lumos-security-codex.md) |
| **Kitap backlog işaretçisi** | [`docs/drafts/BACKLOG.md`](../drafts/BACKLOG.md) `KITAP-KAYNAK-2026-09-13-MS-SOVEREIGNTY` |
| **İlgili iç kayıt** | `KITAP-VIZYON-2026-09-13` (canlı servis gösterme; hizmet üretmek değil doğru hizmetlerle konuşmak) |

---

## Ne bu kayıt

Microsoft, 2025’te Avrupa kurumlarına kabaca şunu söylüyor: bulutu kullan; verinin nerede olduğunu, kimin erişebildiğini, şifreleme anahtarlarını ve operasyonel kontrolü mümkün olduğunca sen belirle.

Bu kart **Lumos’un ürününü Microsoft’un yaptığı anlamına gelmez.** Büyük kurumsal dünyada şu ilkelerin resmi karşılığını gösterir:

**kullanıcı/kurum kontrolü → sınırlandırılmış yetki → insan gözetimi → görünür ve kanıtlanabilir erişim → farklı sağlayıcılarla çalışma.**

Tüketici / AI-agent dilindeki karşılık (`KITAP-VIZYON-2026-09-13`): arka planda hangi servis çalışıyor, neye erişiyor, ne yapıyor; kullanıcı isterse canlı görsün. *Bağlıyoruz ama perde arkasında saklamıyoruz.*

v0.1 kitap iskeletine yazılmaz. v0.2 editoryal geçişte dış referans adayıdır.

---

## Birincil kaynaklar (doğrulandı)

| Kaynak | Ne | Erişim |
|--------|----|--------|
| Microsoft resmi blog, 2025-06-16 | Sovereign Public Cloud; Data Guardian, External Key Management, Regulated Environment Management duyurusu | [Announcing comprehensive sovereign solutions…](https://blogs.microsoft.com/blog/2025/06/16/announcing-comprehensive-sovereign-solutions-empowering-european-organizations/) |
| Microsoft Learn | Data Guardian: bölgesel insan onayı, gerçek zamanlı izleme, değiştirilmeye karşı korunan kayıt | [Data Guardian overview](https://learn.microsoft.com/en-us/azure/azure-sovereign-clouds/public/data-guardian) |
| Microsoft’s European Digital Commitments | Avrupa mevzuatı, operasyonel dayanıklılık ve egemenlik taahhütleri çerçevesi | [European Digital Commitments](https://marketingassets.microsoft.com/gdc/gdcbgQN58/original) |

Canlı doğrulama: WebFetch · Microsoft Blog + Learn · 2026-09-13.

---

## Kitapta kullanılabilecek çekirdek noktalar

Microsoft’un kendi tarifinden (ürün vaadi olarak kopyalanmaz; dış örnek olarak):

1. **Data Guardian.** Avrupa’daki sistemlere Microsoft mühendislerinin uzaktan erişimi, Avrupa’da bulunan personel tarafından gerçek zamanlı onaylanır ve izlenir. Her erişim olayı, sonradan değiştirilmeye karşı korunan bir deftere yazılır (Learn: Azure confidential ledger).
2. **External Key Management.** Müşteri şifreleme anahtarlarını Azure dışında tutabilir: kendi HSM’inde veya güvenilen üçüncü taraf / başka bir sağlayıcıda.
3. **Confidential Computing / müşteri kontrolünde şifreleme.** İşlenen veriye bulut yöneticilerinin bile erişememesi hedeflenir; müşteri hangi donanım/yazılım kombinasyonunun veriye erişeceğini belirtir (European Digital Commitments).
4. **Çerçeve.** Microsoft bunu dijital egemenlik, Avrupa hukuku ve operasyonel dayanıklılık altında sunar; tek bir özellik değil, kamu + özel + ulusal ortak bulut seçenekleri.

---

## Lumos ile hiza (ve sınır)

| Microsoft kurumsal dil | Lumos’ta yakın ilke | Bu kayıt ne demez |
|------------------------|---------------------|-------------------|
| Kurum verinin yerini, erişimi, anahtarı ve operasyonu belirler | Kullanıcı kararı merkezde; kalıcı / dış etkili adımda son söz kullanıcıda | Lumos Azure Data Guardian’ı kopyalar veya satar |
| Uzaktan erişim için insan-in-the-loop onay + gerçek zamanlı izleme | Dur-kanıt-onay; otomatik kalıcı silme / dış yazma yok | Bugün Lumos’ta Avrupa personel onay hattı vardır |
| Değiştirilemez / kanıtlanabilir erişim kaydı | Görünür kayıt, audit, sahte kesinlik yasağı | Lumos confidential ledger ürünü vardır |
| Anahtar başka yerde; birden fazla sağlayıcı | Hizmetleri kendisi üretmez; doğru hizmetlerle konuşur | Belirli bir HSM veya bulut ortağı seçildi |

**Kitap cümlesi (aday, henüz metne işlenmedi):** “Biz böyle düşünüyoruz” demenin yanında, Microsoft’un 2025 Avrupa egemenlik mimarisinde kontrol, gerçek zamanlı gözetim ve denetlenebilir kaydı kurumsal ölçekte uyguladığını gösterebiliriz.

---

## Kapsam dışı

- `docs/lumos-book-outline.md` v0.1’e doğrudan yazma
- Yeni ADR, ürün vaadi, tarih taahhüdü
- Hukuki uygunluk hükmü (CLOUD Act, GDPR sonucu vb. — Microsoft metnini tekrar etmek hüküm değildir)
- UI, paket veya fikrî mülkiyet arşivi dosyalarına bağlama
