# Lumos sözleşmesi — uygulama bağlama planı

Bu belge, **Lumos karar mekanizması ve çekirdek sınırları sözleşmesi** (`docs/lumos-karar-sozlesmesi.md`) ile ajan çalışma akışı ve kod arasındaki bağlantıyı tanımlar. Amaç: sözleşmenin sadece belge olarak kalmaması; ajanlar ve geliştirme akışının bu sözleşmeye göre çalışması. Rol karmaşası, kapsam kayması ve çekirdeğe yanlış dokunma riskinin azaltılması.

**Kapsam (bu aşama):** Büyük kod yazımı yok; sadece bağlama planı. Mevcut yeşil davranış bozulmaz; workspace omurgası ve görev motoru mantığı değiştirilmez; sadece uygulama bağlantı katmanı düşünülür.

---

## 1. Sözleşmeden uygulamaya geçiş noktaları

### 1.1 Sadece docs olarak kalacak maddeler

| Kaynak (sözleşme bölümü) | Madde | Gerekçe |
|--------------------------|--------|--------|
| §1 Karar katmanları | Tablo: "Sadece cevap ver", "Analiz et ama uygulama yapma", "Öner ama bekle", "Açık onayla uygula", "Asla dokunma" — örnek komutlar ve açıklamalar | Referans ve ürün tanımı; ajanların davranışını yönlendiren metin. Kod zaten `profiles.py` ile sınırları uyguluyor; bu tablo dokümantasyon. |
| §2 Dokunulmaz çekirdek | "Güvenlik" satırı — kilit, keystore, presence, consent, kimlik, çocuk kullanıcı | Ürün/güvenlik tanımı; ileride implementasyon olursa o zaman kod guard gündeme gelir. |
| §2 Dokunulmaz çekirdek | "Temel politika" — offline/online, emin olmadığı yerde konuşmaz | Politika metni; mevcut kodda PolicyRules/confidence zaten var; detay docs’ta kalır. |
| §2 Dokunulmaz çekirdek | "Çekirdek davranış sözleşmesi" — karakter, güven, manipüle etmez, ilerleme ölçüsü | Davranış ilkesi; ajan kurallarında özetlenir, kodda ayrı modül yok. |
| §3 Kontrollü geliştirilebilir | Tüm tablo (prompt/cevap biçimi, görev önerileri, yardımcı araçlar, açıklama derinliği, loglama biçimi) | Geliştirme sınırları; neyin değiştirilebileceğini tarif eder; tek tek kod guard’a ihtiyaç yok. |
| §4 Sandbox | "Bu aşamada sandbox/data/exports sözleşme parçası değil" | Durum notu; açıldığında sözleşme güncellenir. |
| §5 Kullanıcı onayı mantığı | Tablo — açık onay / sadece öneri / sistem otomatik durur | Onay mantığı tarifi; kurallar ve kodla uyumlu kalır, detay docs’ta. |
| §6 Cevap disiplini | Tablo — veri yoksa, belirsizlik, risk, tamamlanmamış iş | Cevap davranışı; referanslar (UNKNOWN_CMD_TEXT, get_fallback_message, result_kind) docs’ta kalır. |
| §7 Özet | Tüm özet maddeler | Tek sayfa referans; değişiklik yapılırken güncellenir. |

### 1.2 `.cursor/rules/` içine kısa kural olarak inecek maddeler

| Sözleşme maddesi | Kural özeti | Hedef dosya / not |
|------------------|-------------|--------------------|
| §2 Yetki — üç profil sabit; critical/external asla izinli değil | Ajanlar yetki profillerini, güvenlik ve dürüstlük modelini değiştiremez; çekirdek/state modeline kapsam dışı dokunma. | Zaten `kando-lumos-multi-agent.mdc` ilke 11; sözleşmeye açık referans eklenebilir. |
| §2 Kalıcı silme | Kalıcı silme sadece kullanıcı açık komutu + tek satır uyarı; çöp yalnızca `.lumos/trash/`. | `lumos-workspace-contract.mdc` ile örtüşüyor; sözleşme maddesi rules’ta tek cümleyle pekiştirilebilir. |
| §2 Ana karar sınırları (SECURITY_NEVER_AUTO) | SECURITY_NEVER_AUTO kapsamına giren işlere (kalıcı silme, dış yazma, geri dönüşsüz işlem, kritik config) otomatik izin verilmez. | Yeni kısa kural: "Çekirdek sınırları" — örn. `lumos-core-boundaries.mdc` veya mevcut workspace contract genişletmesi. |
| §4 Sandbox overwrite yasağı | Deneme/kopya alanı aktif state kaynağı olarak kullanılmaz; tasks/notlar/config doğrudan overwrite edilmez. | Sandbox açıldığında rules’a girecek; şimdi "ileride sandbox açılırsa" notu. |
| §5 Açık onay gerekir | Kilidi açmak, kalıcı silme, genel onay ile çok adımlı iş — açık onay gerekir. | Rules’ta "Açık onay gerektiren işler" tek maddelik liste. |
| Kando ilke 11 | Çekirdek, güvenlik, yetki, dürüstlük modeli, durum modeli — kapsam dışı dokunma. | `kando-lumos-multi-agent.mdc` — sözleşme belgesine referans: `docs/lumos-karar-sozlesmesi.md`. |

### 1.3 Kod seviyesinde guard/check gerektiren maddeler

| Madde | Nerede guard | Ne yapılır (ileride) |
|-------|--------------|----------------------|
| Kalıcı silme sadece kullanıcı komutu + uyarı | Görev silme akışı (CLI/task engine) | Kalıcı silme tetiklenmeden önce: (1) komutun kullanıcı kaynaklı olduğu, (2) tek satır uyarının gösterildiği kontrolü. |
| SECURITY_NEVER_AUTO — asla otomatik yapılmaz | `profiles.py` + görev adımı yürütümü | Zaten `is_allowed_for_profile` critical/external False döndürüyor; kalıcı silme için ayrı "asla otomatik" branch’i (ör. `permanent_delete` adım türü) engine’de açıkça reddedilmeli. |
| Çöp yalnızca `.lumos/trash/` | Persistence / silme kodları | Silinen öğe yalnızca tanımlı trash konumuna gider; başka çöp dizini oluşturulmaz (kod path kontrolü). |
| Deneme alanı aktif state’i overwrite etmez | (Sandbox açıldığında) sandbox / kopya yazma noktaları | Sandbox’a yazarken `tasks.json`, notlar, config doğrudan hedef alınmaz; guard ile engellenir. |

### 1.4 Test ile korunması gereken maddeler

| Madde | Test koruması |
|-------|----------------|
| Yetki matrisi (rapor / guvenli_yurut / kisitli_otonom) | Zaten `tests/test_task_engine.py` — `is_allowed_for_profile` ve STEP_TYPE matrisi test ediliyor. |
| SECURITY_NEVER_AUTO içeriği | Zaten test: `permanent_delete` vb. set’te. Genişletme: set’e yeni anahtar eklenirse test güncellenir. |
| Kalıcı silme: sadece açık komut + uyarı | İleride: silme akışında "sadece kullanıcı komutu" ve "uyarı verildi" senaryoları için entegrasyon/unit test. |
| Trash yalnızca `.lumos/trash/` | İleride: silme sonrası dosya/konum testi (trash path sabit). |
| critical/external asla izinli değil | Mevcut testlerde var; regression olarak korunmalı. |

---

## 2. Ajan akışına bağlama

### 2.1 Hangi kararlar hangi ajana etki eder?

| Sözleşme alanı | CI Log Hakemi | Tarayıcı | Teşhis | Cerrah | Doğrulama | Disiplin |
|----------------|---------------|----------|--------|--------|-----------|----------|
| Log okunmadan teşhis yok | Evet: sadece log çıkarımı | — | Evet: semptom önce logdan | — | — | — |
| Kök neden + dar kapsam | — | Repo state ile ilişki | Evet: kök neden, etkilenen/etkilenmeyen alan | — | — | — |
| Çekirdek/ yetki/ güvenlik/ durum modeline dokunma | — | — | Etkilenen alan "çekirdek" ise belirtir | Dokunmaz | Çekirdekte değişiklik var mı bakar | Kapsam dışı çekirdek dokunuşu arar |
| Rol kapma yasağı | Kök neden tahmini yapmaz | Çözüm üretmez | Kod yazmaz | Kapsam büyütmez | Yeni çözüm yazmaz | Teknik impl yapmaz |
| Kalıcı silme / SECURITY_NEVER_AUTO | — | İlgili dosya varsa listeler | Değişiklik bu sınırı zorluyorsa "etkilenen" der | Bu sınırı gevşeten değişiklik yapmaz | Sınır ihlali test/CI’da görünür mü bakar | Çekirdek gevşetme / kalıcı silme kuralı ihlali arar |
| Minimum değişiklik / "hazır girmişken" yok | — | — | En dar çözüm sınırı | Sadece tanımlı kırık; refactor/ek özellik yok | — | Gereksiz değişiklik / feature creep arar |

### 2.2 Rol kapma ve kapsam ihlali nasıl önlenir?

- **Kurallar metninde:** `kando-lumos-multi-agent.mdc` ve `ci-diagnosis.mdc` zaten rol sınırlarını ve sırayı net yazıyor. Sözleşme ile uyum için:
  - "Çekirdek sınırları" = `docs/lumos-karar-sozlesmesi.md` §2 (dokunulmaz alanlar) + §7 özet olarak rules’ta referanslansın.
  - Disiplin Ajanı’nın aradığılar listesine şu eklenebilir: "Çekirdek sınırları sözleşmesine aykırı değişiklik (yetki/güvenlik/kalıcı silme/ SECURITY_NEVER_AUTO gevşetme)."
- **Sıra korunursa** (CI Log → Tarayıcı → Teşhis → Cerrah → Doğrulama → Disiplin) rol kapma doğal olarak sınırlı kalır; Teşhis’te "CI semptomu" ve "Repo kök nedeni" yoksa Cerrah kod yazmaz.
- **Kapsam ihlali:** Disiplin’in "kapsam dışı çekirdek dokunuşu" ve "gereksiz değişiklik" kontrolleri, sözleşmedeki "dokunulmaz çekirdek" ve "asla dokunma" maddeleriyle aynı hizada tutulur.

---

## 3. Kod seviyesinde gelecekte guard gerektiren alanlar (sadece tespit)

Aşağıdakiler **şu an sadece tespit**; bu aşamada kod yazılmaz, sadece plana alınır.

| Alan | Açıklama | Guard fikri |
|------|----------|-------------|
| **Yetki** | Profil veya genel onay dışı adımın yürütülmemesi | Zaten `is_allowed_for_profile` kullanılıyor; tüm adım yürütüm noktalarında kullanıldığından emin olunmalı (audit). |
| **Kalıcı silme** | Otomatik kalıcı silme olmaması; sadece açık kullanıcı komutu + uyarı | Silme komutunda "explicit user command" + "warning shown" flag/check; `SECURITY_NEVER_AUTO` ile birlikte engine’de red. |
| **Çekirdek overwrite** | tasks.json, notlar, config’in doğrudan overwrite edilmemesi (sandbox/kopya senaryosunda) | Sandbox/kopya yazma path’lerinde hedef whitelist veya "active state path’lere yazma yasak" kontrolü. |
| **Sandbox dışına taşma** | Deneme/kopya alanının aktif state kaynağı olarak kullanılmaması | Okuma kaynağı sabit: sadece tanımlı omurga (tasks, notes store, config); sandbox path’inden okuma yapılmaz. |
| **Açık onay gerektiren işler** | Kilidi açma, kalıcı silme, genel onay ile çok adımlı iş | Bu işlerin tek giriş noktalarında "açık onay alındı mı?" kontrolü (ileride UI/CLI ile birlikte). |

---

## 4. En dar ilk uygulama paketi (2–3 madde)

Tüm sözleşmeyi bir anda koda gömmek yerine, ilk turda **en dar ve en güvenli** uygulanacaklar:

1. **Rules’ta sözleşme referansı ve "çekirdek sınırları" özeti**  
   - `kando-lumos-multi-agent.mdc` (ve gerekirse `ci-diagnosis.mdc`) içinde: "Çekirdek/dokunulmaz alanlar" tanımı için `docs/lumos-karar-sozlesmesi.md` §2 ve §7’ye açık referans.  
   - İlke 11’in yanına: "Detay: Lumos karar ve çekirdek sınırları sözleşmesi (docs/lumos-karar-sozlesmesi.md)."  
   - **Neden ilk:** Kod değişmediği için risk yok; ajanların aynı belgeye bakması sağlanır.

2. **Çekirdek sınırları için tek sayfalık rule (opsiyonel ama önerilen)**  
   - Yeni `.cursor/rules/lumos-core-boundaries.mdc` (kısa):  
     - Dokunulmaz: güvenlik, yetki profilleri, temel politika, kalıcı silme kuralı, SECURITY_NEVER_AUTO, karakter/dürüstlük.  
     - Ajanlar bu alanlara kapsam dışı dokunmaz; gevşetme veya sessiz değişiklik yapılmaz.  
   - **Neden ilk:** Rol/kapsam ihlali azalır; Disiplin ve Cerrah için net referans olur.

3. **Disiplin çıktısına "çekirdek sözleşmesi" kontrolü**  
   - Disiplin Ajanı’nın "Aradığın şeyler" listesine madde: "Çekirdek sınırları sözleşmesine aykırı değişiklik (yetki, güvenlik, kalıcı silme, SECURITY_NEVER_AUTO gevşetme)."  
   - **Neden ilk:** Sadece rule metni; kod/test değişmez; ajan davranışı sözleşmeye hizalanır.

İlk pakette **kod guard veya test değişikliği yok**; sadece docs + rules bağlantısı.

---

## 5. Test koruması — hangi maddeler ileride test ile korunmalı?

| Madde | Mevcut durum | İleride yapılacak |
|-------|--------------|--------------------|
| Yetki matrisi `is_allowed_for_profile` | Test var | Regression olarak sürdür; profil/set değişirse test güncelle. |
| SECURITY_NEVER_AUTO içeriği | Test var | Set değişince test güncelle; yeni "asla otomatik" türü eklenirse test ekle. |
| critical/external asla True dönmez | Test var | Korunmaya devam. |
| Kalıcı silme: sadece kullanıcı komutu + uyarı | Yok | Silme akışı netleşince: "kalıcı silme otomatik tetiklenmez", "uyarı verilir" senaryoları. |
| Trash yalnızca `.lumos/trash/` | Yok | Silme sonrası konum testi (path sabit). |
| Sandbox overwrite yasağı | Yok (sandbox yok) | Sandbox açıldığında: aktif state path’lere yazma yapılmadığı testi. |

---

## 6. Özet tablolar (istediğin çıktı formatı)

### 6.1 Docs’ta kalacaklar

- §1 Karar katmanları tablosu (örnek komutlar, açıklamalar).  
- §2 Güvenlik satırı (kilit, keystore, kimlik, çocuk kullanıcı).  
- §2 Temel politika, Çekirdek davranış sözleşmesi.  
- §3 Kontrollü geliştirilebilir alanlar (tüm tablo).  
- §4 Sandbox’ın "şu an sözleşme dışı" notu.  
- §5 Onay mantığı tablosu.  
- §6 Cevap disiplini tablosu.  
- §7 Özet.

### 6.2 Rules’a inecekler

- Yetki/çekirdek dokunulmazlık: mevcut ilke 11 + `docs/lumos-karar-sozlesmesi.md` referansı.  
- Kalıcı silme + trash: `lumos-workspace-contract.mdc` ile uyumlu tek cümle (gerekirse pekiştirme).  
- SECURITY_NEVER_AUTO / "asla otomatik" özeti: yeni kısa kural (örn. `lumos-core-boundaries.mdc`).  
- Sandbox overwrite yasağı: "Sandbox açılırsa" notu.  
- Açık onay gerektiren işler: tek maddelik liste.  
- Disiplin: "Çekirdek sözleşmesi ihlali" arama maddesi.

### 6.3 Kod guard gerektirenler

- Kalıcı silme: sadece kullanıcı komutu + uyarı (silme akışında).  
- SECURITY_NEVER_AUTO: engine’de kalıcı silme ve diğer "asla otomatik" adımların açıkça reddi.  
- Çöp yalnızca `.lumos/trash/`: path kontrolü.  
- (Sandbox açıldığında) Aktif state overwrite edilmez: sandbox yazma guard’ı.

### 6.4 Test koruması gerektirenler

- Yetki matrisi ve SECURITY_NEVER_AUTO (mevcut; sürdür).  
- Kalıcı silme koşulları (ileride).  
- Trash path (ileride).  
- Sandbox overwrite yasağı (sandbox açıldığında).

### 6.5 En dar ilk uygulama paketi

1. Rules’ta sözleşme referansı (kando + isteğe bağlı ci-diagnosis).  
2. `lumos-core-boundaries.mdc` benzeri kısa "çekirdek sınırları" kuralı.  
3. Disiplin’e "çekirdek sözleşmesi ihlali" kontrolü eklenmesi.

### 6.6 Önerilen uygulama sırası

1. **Faz 1 (şimdi, sadece docs + rules)**  
   - `kando-lumos-multi-agent.mdc`: sözleşme referansı + ilke 11’e "detay: docs/…" notu.  
   - Yeni `lumos-core-boundaries.mdc`: dokunulmaz alanlar özeti.  
   - Disiplin bölümüne: "Çekirdek sözleşmesi ihlali" arama maddesi.  
   - (İsteğe bağlı) `lumos-workspace-contract.mdc`: kalıcı silme/trash tek cümle pekiştirme.

2. **Faz 2 (sonra, kod guard)**  
   - Silme akışında "kullanıcı komutu + uyarı" ve SECURITY_NEVER_AUTO reddi.  
   - Trash path’in tek olması guard’ı.

3. **Faz 3 (test)**  
   - Kalıcı silme ve trash path testleri.  
   - Mevcut yetki ve SECURITY_NEVER_AUTO testlerinin sürdürülmesi.

4. **Sandbox açıldığında**  
   - Rules’a sandbox maddeleri.  
   - Overwrite yasağı guard + test.

---

*Bu plan, mevcut yeşil bazı bozmadan sadece bağlantı katmanını tanımlar; görev motoru mantığı ve workspace omurgası değiştirilmez.*
