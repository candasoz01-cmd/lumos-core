# Lumos Payment Orchestrator — konumlandırma ve fark analizi

**Kapsam notu (2026-07-24):** Bu doküman bir **kavram/konumlandırma çalışmasıdır**, karar veya taahhüt edilmiş yol haritası değildir. `lumos-core` şu an FAZ-1 stabilizasyon / STOP LIST döneminde; yeni bir iş kolu (bankacılık/POS B2B) buraya kapsam olarak eklenmiş sayılmaz. Burada yapılan tek şey: kullanıcının önerdiği "POS donanımıyla değil, karar zinciriyle rekabet et" tezini gerçek pazar kanıtına karşı test etmek ve farkın nerede gerçekten aşikar olduğunu, nerede olmadığını ayırmak. Bu konseptin roadmap'e girip girmeyeceği kararı `candasoz01-cmd/Lumos` (canonical karar deposu) sürecine aittir.

---

## 1. Tez neydi

Lumos, POS donanımıyla (Ingenico/Verifone/PAX/Newland) rekabet etmek yerine, bankanın karar zincirinin üzerine oturan bir **zekâ/orkestrasyon katmanı** olsun:

```
POS → Lumos → Fraud Engine → Identity → AML → Bank Rules → AI Review → Bank Approval → Payment
```

Lumos kart kuruluşunun, bankanın veya POS üreticisinin yerine geçmez; kararı o alır, Lumos yalnızca akışı düzenler ve sonucu insanların anlayacağı hale getirir.

Bu tezi doğrulamak için önce iki soruyu kanıtla test ettim: **(a)** bu boşluk gerçekten boş mu, **(b)** doldurursak fark gerçekten "aşikar" mı, yoksa zaten var olan bir şeyin yeniden adlandırılması mı.

## 2. Pazarda ne zaten var (kanıt)

| Oyuncu | Ne sunuyor | Kime hitap ediyor |
|---|---|---|
| **Feedzai (Whitebox AI)** | İşlem başına risk skoru + skorun arkasındaki sinyalleri açan explainability katmanı | Banka **analisti** / uyum ekibi |
| **Featurespace (ARIC)** | Gerçek zamanlı skorlama + görsel dashboard'la "neden" analizi | Banka **analisti** |
| **Hawk AI** | Kural tabanlı izleme + ML explainability, alarm başına hangi verinin tetiklediğini gösteriyor (~%40 analist inceleme süresi azalması iddiası) | Banka **analisti** |
| **Verifone (Commander Central)** | POS/terminal yönetim sistemine gömülü, gerçek zamanlı işlem skorlama — 2026'da petrol/mağaza dikeyinde canlı | **POS üreticisinin kendisi**, doğrudan terminalde |
| **Ingenico (PTMS)** | Terminal yönetim sistemi + üçüncü taraf fraud motorlarıyla entegrasyon | Satıcı/işletme, dolaylı |

**Sonuç:** "Explainable fraud AI" fikri yeni değil — banka analistine kararın gerekçesini gösteren araçlar zaten olgun bir pazar. Ayrıca POS üreticileri de (Verifone örneği) kendi terminal yönetim yazılımlarına doğrudan AI skorlama gömerek bu alana girmiş durumda. Yani "POS'un üstüne otur" tezi doğru yönde ama alan boş değil — hem back-office fraud motorları hem de POS üreticilerinin kendisi bu katmana zaten hareket ediyor.

## 3. Asıl boşluk nerede — fark burada aşikar

Yukarıdaki hiçbir oyuncu şu ikisini birlikte yapmıyor:

**(a) İnsan-yüzü açıklama, analist-yüzü değil.** Feedzai/Featurespace/Hawk AI'nin explainability'si banka içindeki analiste veya uyum ekibine gidiyor — kasiyere, müşteriye veya sahadaki işletmeciye değil. Kullanıcının önerdiği "🟢/🟡/🔴" + "temassız limit aşıldı" gibi düz dilli, kasiyer/müşteri seviyesinde anlık açıklama, mevcut ürünlerin kapsamadığı bir katman.

**(b) Düzenleyici rüzgâr bu yönde esiyor, mevcut araçlar buna göre tasarlanmamış.** AB Yapay Zekâ Yasası gibi düzenlemeler, kredi/ödeme/dolandırıcılık kararlarını yüksek riskli AI kapsamına alma ve etkilenen bireye (analiste değil) anlaşılır açıklama verme yönünde ilerliyor. Bu, kesinleşmiş bir yükümlülük olarak değil — hukuki yorum ve uygulama takvimi zamanla değişebilir — bir **yön göstergesi** olarak okunmalı. Lumos'un buradaki konumu hukuki bir iddiaya değil, teknik bir tasarım hedefine dayanmalı: **açıklanabilir karar iletişimini** (kasiyere, müşteriye, denetleyiciye düz dilde "neden") baştan tasarım hedefi olarak benimsemek — bu hedef, ilgili düzenlemeler kesinleşmese veya değişse bile kendi başına değerli kalır.

Bu iki madde birleşince pozisyon netleşiyor: **Lumos'un farkı "explainable AI icat etmek" değil — var olan risk motorlarının çıktısını insana (kasiyer, müşteri, esnaf) ve düzenleyiciye karşı savunulabilir, çok dilli, gerçek zamanlı, sesli bir arayüze çevirmek.** Bu, Feedzai'nin analist ekranıyla da, Verifone'un terminal skorlamasıyla da çakışmıyor; ikisinin de üstüne oturuyor.

**Rol ayrımı — bu raporun en önemli cümlesi:**

> Lumos fraud motoru değildir.
> Lumos; mevcut risk motorlarının, kuralların ve banka kararlarının kullanıcıya, operatöre ve denetleyiciye anlaşılır biçimde açıklanmasını sağlayan orkestrasyon ve karar iletişim katmanıdır.

Bu ayrım korunduğu sürece Lumos, Feedzai'yle veya Featurespace'le rekabet etmez — onların ürettiği skorun üst katmanına oturur. Ayrım bozulup Lumos kendi risk kararını üretmeye başladığı an, bu konumlandırma çöker ve Lumos sessizce bir fraud-engine rakibine dönüşür (bkz. Bölüm 5, madde 1 ve 4'teki uyarı).

## 4. Mimari — orkestrasyon + insan-yüzü katmanı

```
POS (Ingenico/Verifone/PAX/Newland)
        │  kart okutma anı
        ▼
   Lumos (orkestrasyon + insan-yüzü katmanı)  ◄── bankanın/POS'un kendi fraud motoru (Feedzai vb.)
        │  skor + gerekçe verisini alır
        ▼
   Fraud Engine → Identity → AML → Bank Rules → AI Review
        │  karar bankada verilir
        ▼
   Bank Approval → Payment
        │
        └─► Lumos: kararı kasiyere/müşteriye düz dilde, doğru dilde, sesli/yazılı sunar
```

Lumos karar vermez, kart kuruluşunun/bankanın yerine geçmez — zincirin **girdi noktasında** (POS'ta kasiyerle konuşan) ve **çıktı noktasında** (bankanın kararını insana çeviren) oturur.

## 5. Özellik seti — kullanıcının önerisi, gerçekleşebilirlik notuyla

| # | Özellik | Not |
|---|---|---|
| 1 | Akıllı Risk Asistanı (🟢/🟡/🔴) | Karar bankada kalır — Lumos yalnızca bankanın/motorun skorunu sadeleştirip gösterir; kendi risk modelini icat etmek ayrı ve çok daha ağır bir taahhüt olur |
| 2 | Satıcı Asistanı ("neden reddedildi") | Banka hata kodlarını düz dile çevirmek — en düşük entegrasyon riskli, en hızlı kanıtlanabilir özellik |
| 3 | Çok Dilli POS | Turizm/sınır bölgesi işletmeleri için somut, ölçülebilir değer |
| 4 | Dolandırıcılık Erken Uyarı (imkânsız seyahat vb.) | Bu zaten Feedzai/Featurespace'in çekirdek işi — Lumos burada motor değil, motorun ürettiği sinyali görünür kılan katman olmalı |
| 5 | İşletme Asistanı (satış sorguları) | Fraud/uyum kapsamı dışında, ayrı bir ürün yüzeyi — karıştırılmamalı |
| 6 | Sesli Destek | Kasiyer eğitimi/iş akışı için, çok dilli desteğin doğal uzantısı |
| 7 | Offline Zekâ | Teknik olarak en ağır madde — cihaz içi model + senkronizasyon; PCI ortamında offline veri tutma ayrı bir güvenlik/regülasyon incelemesi gerektirir |

Madde 1 ve 4, "Lumos kendi risk kararını mı veriyor" sorusunu doğurur — pozisyonun tutarlı kalması için bu ikisinde de nihai skor **her zaman** banka/mevcut motordan gelmeli, Lumos yalnızca sadeleştirip sunmalı. Aksi halde Lumos sessizce bir fraud-engine rakibine dönüşür ve "karar vermeyiz" tezi çöker.

## 6. Riskler / açık sorular

- **POS üreticileri bu katmana zaten giriyor** (Verifone/Commander Central) — "POS'un üstüne otur" konumu zaman içinde POS üreticisinin kendi ürünüyle çakışabilir.
- **B2B banka satışı** ayrı bir yetkinlik ve satış döngüsü gerektirir (aylar/yıllar, uyum denetimi, pilot bankacılık müşterisi) — mevcut Lumos ürün/dağıtım modeliyle örtüşmüyor.
- **PCI DSS ve bankacılık düzenlemeleri** kapsamında üçüncü taraf bir katmanın kart verisi akışına girmesi ayrı bir güvenlik sertifikasyon yüküdür.
- **Kim bu işi yürütecek** — bu, mevcut FAZ-1/STOP LIST kapsamındaki ekip için ek bir iş kolu, ana ürün önceliğini seyreltme riski taşır.

## 7. Önerilen sonraki adım

Bu bir kavram kanıtlama notudur, uygulama planı değil. Eğer bu yön ciddiye alınacaksa, sıradaki adım roadmap kararı olarak `candasoz01-cmd/Lumos` (canonical) reposuna taşınmalı — lumos-core'a doğrudan kapsam eklenmemeli.

---

## Kaynaklar

- [Feedzai — Fraud Prevention Solutions](https://www.feedzai.com/fraud/)
- [FluxForce — Top 10 Fraud Detection Platforms for Mid-Market Banks](https://www.fluxforce.ai/blog/top-10-fraud-detection-platforms-for-mid-market-banks-in-2028)
- [Verifone — Puts AI to Work for Petroleum and Convenience Retailers](https://www.globenewswire.com/news-release/2026/05/05/3287791/0/en/verifone-puts-ai-to-work-for-petroleum-and-convenience-retailers.html)
- [Ingenico — PTMS: Next-Gen Payment Terminal Management Systems](https://ingenico.com/en/newsroom/blogs/ptms-what-you-need-know-about-next-gen-payment-terminal-management-systems)
- [Unit21 — EU AI Act 2026 FAQs for Fraud and AML Teams](https://www.unit21.ai/blog/eu-ai-act-2026-faqs-what-fraud-and-aml-teams-need-to-know)
- [EBA — AI Act: implications for the EU banking and payments sector](https://www.eba.europa.eu/sites/default/files/2025-11/d8b999ce-a1d9-4964-9606-971bbc2aaf89/AI%20Act%20implications%20for%20the%20EU%20banking%20sector.pdf)
