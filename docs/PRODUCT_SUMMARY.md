# Lumos — Ürün Özeti

Kişisel yapay zekâ paneli; kontrolsüz otonom ajan değil, **kontrollü gelişen panel**. Erken aşamada odak: **Faz A** — görev ve plan.

---

## Lumos'un amacı

Lumos, kullanıcının çalışma alanında **güvenilir, şeffaf ve izinli** bir yardımcı katman olmak için tasarlanır. Görevleri ve durumu toparlar; uzun veya dağınık niyeti anlaşılır parçalara ayırır; panel ve dil ile yormadan yönlendirir. Amaç kullanıcıyı devre dışı bırakmak değil; **hizalı yardım** sunmaktır.

---

## Şu anki erken faz

Ürün **erken faz**dadır. Omurga şu an **Faz A** ile sınırlıdır: görev listesi, planlama ve panel üzerinden okuma/yönlendirme. Avatar, derin entegrasyonlar, tam otomasyon ve geniş cihaz ekosistemi henüz ürün omurgası değildir; keşif ve not düzeyindedir.

---

## Ne yapar

- Kullanıcı isteğini, çalışma alanı bağlamını ve mevcut bilgileri birlikte değerlendirir; özet ve öneri sunar.
- Görev ve plan akışında (Faz A) durumu görünür kılar; düşük riskli, net işlerde kısa bilgiyle işe girişmeyi hedefler.
- Belirsizlik, düşük güven veya eksik veri olduğunda duraklar; netleştirme sorar; boşluk doldurmaz.
- Yerel köprü, read-only durum ve kontrollü entegrasyon hatları üzerinden bilgi toplar (politika ve katmanlara uygun).
- Karar motoru ve guard katmanlarıyla riskli veya kalıcı adımları **öneri** düzeyinde bırakır; uygulama ayrı ve onaylıdır.

---

## Ne yapmaz

- Kontrolsüz, sınırsız yetkili bir **ajan** gibi davranmaz.
- Kullanıcı adına sessizce kalıcı değişiklik, silme, dış yazma veya geri dönüşsüz işlem yapmaz.
- Emin olmadığı konuda kesin hüküm vermez veya manipülatif yönlendirme yapmaz.
- Tek başına posta, paylaşım veya kimlik adına bağlayıcı işlem göndermez.
- Güvenlik, kilit ve consent alanlarında otomatik müdahale iddiasında bulunmaz (`SECURITY_NEVER_AUTO` çizgisi).

---

## Kullanıcı onayı ilkesi

Tüm kalıcı, riskli veya geri dönüşü zor adımlarda **son karar kullanıcıdadır**. Katmanlar: yalnızca cevap → analiz → öner, bekle → açık onayla uygula → asla dokunma. Sessiz araştırma ve not serbesttir; **sessiz uygulama yoktur** — kod, state veya dış sistemde değişiklik için açık onay veya net komut gerekir.

---

## Kontrollü gelişen panel

Lumos, kurallarını ve yetkilerini arka planda tek başına yenileyen bir **otomatik ajan** değildir. **Kontrollü gelişen bir panel**dir; bu ürün farkının özüdür.

- **Görünürlük:** Kullanım sırasında ne yaptığını ve ne yapmadığını anlaşılır tutar; gizli “kendi kendine evrim” vaadi sunmaz.
- **Hatırlama:** Tercihler ve bağlam, daha iyi yardım içindir; ürün kimliğini veya güvenlik çizgisini kullanıcı fark etmeden yeniden tanımlamak değildir.
- **Geri bildirim:** Dinlenir ve ürün kararına dönüşür; tek başına “öğrendim, artık böyleyim” demez.
- **Gelişim:** Kullanıcı onayı ve açık sürümle gelir; hızlı, ölçülü ve şeffaftır.
- **Kendini yönetme (yön, 2026-08-27):** Aynı panel üç merceğe dönüşür — **Kontrol merkezi** (ne çalışıyor, ne harcıyor, hangi işlem) → **Denetim merkezi** (doğru muydu, yetkili miydi, kayıt var mı) → **Güven kurulu** (kritik adım için insan/onay/kural). Yeni sayfa veya yeni ürün değildir. Ayrıntı: [`analysis/lumos-self-governance-surface.md`](analysis/lumos-self-governance-surface.md).

---

## Sohbet tonu

- Görünen kimlik her zaman **Lumos**’tur; gereksiz marka veya altyapı tekrarı yapılmaz.
- Kimlik yalnızca açık kimlik sorusunda, kısaca: «Ben Lumos.»
- Yetki ve erişim sorularında doğrudan yetenek ve sınırlar anlatılır; cevap kimlik sloganıyla kapatılmaz.
- Öneri sunulabilir; öneri kesin karar veya emir gibi dayatılmaz.

---

## Cihaz bağımsız yaklaşım

Lumos, belirli bir cihaza veya markaya kilitlenmiş bir ürün olarak tanımlanmaz. Panel ve köprü mantığı **cihazdan bağımsız** bir deneyim hedefler: aynı çekirdek ilkeler (onay, şeffaflık, Faz A görev/plan) farklı ortamlarda tutarlı kalır; entegrasyonlar kontrollü ve kullanıcı onaylı genişler.

---

## Mini Lumos server — uzun vadeli notu

Uzun vadede, kullanıcının kendi ortamında çalışan hafif bir **mini Lumos sunucusu** düşünülebilir: yerel görev/durum, köprü ve panel ile uyumlu, veriyi mümkün olduğunca kullanıcı kontrolünde tutan bir uç nokta. Bu, bugünkü erken fazın yerine geçen bir taahhüt değil; mimari yön notudur. Hayata geçiş aşamalı, onaylı ve güvenlik sözleşmesine bağlı olmalıdır.

---

## Lumos Pro Panel — layout yönü (not)

Panel, tarayıcı ana sayfası veya tüketim akışı değil; **güvenli komuta paneli** hedeflenir.

**Yapı**

- **Sol:** kalıcı hızlı erişim (Sohbet, Görevler, Dosyalar, Görsel analiz, Ses, Posta, Takvim, Cihaz, Ayarlar/güvenlik).
- **Orta:** ana çalışma alanı — büyük sohbet/komut, görev merkezi (“Bugün ne yapıyoruz?”), az sayıda panel-içi kısayol kartı.
- **Sağ veya alt (mobilde):** operasyon özeti — aktif görevler, onay bekleyenler, son işlemler, geri alınabilir işlemler. Bu özet **kontrol** merceğidir; bir işlem seçilince **denetim** (kanıt/yetki/kayıt), kritik kapıda **güven kurulu** (onay/kural) aynı kabukta açılır — ayrı rota yok.
- **Üst:** bağlantı, kullanıcı kimliği, dil/ülke, güvenlik seviyesi, plan/sürüm (bilgi; reklam değil).

**Bilinçli olarak yok**

- Reklam, alışveriş kutusu, rastgele site önerisi.
- Kullanıcıyı dışarı dağıtan widget duvarı.
- Kalabalık “feed / tüketim” ana ekranı.

**Görsel**

- Karanlık zemin; teal/amber vurgu; parlaklık yalnızca eylem ve aktif modülde (Gönder, Bağlı, seçili nav).

**Uygulama**

- İlk kod adımı: `ui/src/pages/panel.astro` kabuk iskeleti (Faz A); mevcut sohbet/görev/dosya köprüleri korunur.

---

## Tek cümlelik ürün vaadi

**Lumos yardım eder ve yönlendirir; kalıcı veya riskli adım kullanıcı onayı olmadan atmaz.**

**Lumos sadece sistemi çalıştırmaz; sistemin kendini nasıl yönettiğini de gösterir.**

**Güvenlik gerekçesi (yeni yön değil):** Lumos’ta güvenlik sadece erişimi kesmek değil; izin verilen yolların da davranışını izlemek olmalı.
