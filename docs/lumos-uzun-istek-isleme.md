# Lumos — uzun kullanıcı isteğini işleme

**Amaç:** Uzun, dağınık anlatımı **uygulanabilir yapıya** çevirmek. Gereksiz soru yok; **kritik** belirsizlikler atlanmaz.

**Uyum:** Karar motoru **`docs/lumos-karar-motoru.md`** (sınıf, parça, onay, §3b hazır çözüm). Bu belge **nasıl okunup parçalanacağını** tarif eder; aynı kuralları tekrar etmez.

---

## 1. Ayrıştırma (mesajdan çıkar)

| Çıktı | Ne |
|--------|-----|
| **Ana amaç** | Tek cümle: kullanıcı aslında ne istiyor? |
| **Özellikler** | Somut istekler (madde madde). |
| **Açık kısıtlar** | “Şunu kullan”, “şunu yapma”, süre, platform vb. |
| **Örtük beklentiler** | Söylenmemiş ama bağlamdan çıkan (varsayımla etiketle). |
| **Belirsiz noktalar** | Netleşmeyen hedef, kapsam, öncelik. |
| **Riskli / karar gerektiren** | Mimari seçim, güvenlik, maliyet, ürün yönü. |

---

## 2. Sınıflandırma

Aynı **`lumos-karar-motoru.md` §1** seviyeleri: **basit** | **orta** | **ürünsel / uzun iş**.

Uzun metin ≠ otomatik ürünsel; metin uzun olsa da tek net eylem varsa **basit/orta** kalabilir.

---

## 3. Parçalama (ürünsel / uzun iş)

Yalnızca **ürünsel** (veya açıkça çok parçalı orta) için:

- İsteği **uygulanabilir parçalara** böl; her parça **kısa başlık**.
- **Bağımlılık sırası** yaz (A → B → C veya A+B paralel).
- **Tek seferde tümünü bitirmeye çalışma** — bir parça = bir sorumluluk / commit disiplinine uy.

---

## 4. Soru stratejisi

| Yap | Yapma |
|-----|--------|
| **Kritik** belirsizlikleri topla | Her küçük detay için soru |
| **Tek mesajda**, mümkünse **“3 kritik nokta”** gibi grupla | Soruları tek tek yağdır |
| Net olanla ilerle | Her şeyi bloklamak için soru |

**Kritik:** Karar vermeden yanlış yön seçilirse geri dönüşü zor veya pahalı olanlar (kapsam, güvenlik, tek stack, “kim / hangi ortam”).

---

## 5. Hazır çözüm (ürünsel uzun iş)

**§3 ve §3b** (`lumos-karar-motoru`): güçlü OSS, SaaS, ucuz hazır — tara, öner; kullanıcı **custom build** isterse **devam et**.

---

## 6. Uygulama kuralı

- **Tam net değilse büyük işe sıçrama** — özellikle ürünsel gövdeyi tek hamlede kodlamaya başlama.
- **Netleşen kısmı uygula** (ilk parça veya güvenli dilim).
- **Kalan belirsizlik** → soru listesinde kalsın; **yarım dosya / yarım kural** bırakma (karar motoru §6).

---

## 7. Çıktı formatı (özet şablonu)

Uzun istek işlendikten sonra (iç veya kullanıcıya kısa özet). **Panel / operatör görünümünde** kullanıcıya giderken sunum: **`docs/lumos-panel-dili-rehberi.md`**.

```
• Anladığım ana amaç: …
• Çıkardığım parçalar: (başlık + sıra/bağımlılık)
• Kritik belirsizlikler: …
• Önce sorulması gerekenler: (tercihen gruplu, örn. 3 madde)
• Hazır çözüm notu: (gerekirse kısa; yoksa “—”)
• Uygulamaya hemen geçilebilecek kısım: …
```

---

## 8. Akış (kısa tablo)

| Adım | Eylem |
|------|--------|
| 1 | Metni ayrıştır (§1). |
| 2 | Sınıf seç (§2). |
| 3 | Ürünsel ise parçala + bağımlılık (§3); hazır çözüm §5. |
| 4 | Kritik sorular varsa toplu sor (§4); değilse net kısım uygula (§6). |
| 5 | Özeti §7 formatında bırak; sonra normal karar motoru akışı. |

---

*Referans: `docs/lumos-karar-motoru.md`, `.cursor/rules/lumos-uzun-istek-isleme.mdc`.*
