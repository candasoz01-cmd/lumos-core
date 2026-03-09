# V1 consent kalıcılığı — teşhis ve minimum plan

Sadece analiz; dosya değişikliği yok.

---

## 1. Şu anki consent/onboarding davranışı (kısa özet)

**Giriş noktası:** Sadece `lumos` / `lumos cli` (interaktif CLI) consent’e bakıyor. `__main__.py` içinde `_run_cli()` çağrılmadan önce `has_user_consent()` kontrol edilir. False ise `build_capability_report()` + `print_onboarding_preview(env)` çalışır: "Merhaba.", cihaz incelemesi, yapabileceklerim, izin gerektiren özellikler, "Bu bilgiler henüz kaydedilmedi." basılır. Ardından CLI her zaman başlar (`cli_main()`).

**Consent fonksiyonu:** `lumos_core.security.consent.has_user_consent()` şu an sabit `False` dönüyor. Docstring’te "Future: check ~/.lumos/consent.json" yazar; gerçekte hiç dosya okunmuyor.

**Onboarding’in anlamı:** Sadece bilgilendirme. Kullanıcıdan "kabul ediyorum" cevabı alan veya consent’i diske yazan bir adım yok. Her CLI açılışında consent False olduğu için onboarding metni her seferinde tekrar basılıyor.

**ask/chat:** `lumos ask` ve `lumos chat` consent’e hiç bakmıyor; onboarding gösterilmiyor. Doğrudan prompt/chat akışına giriyor. Persistence (user_memory, user_preferences) de consent kontrolü olmadan yapılıyor: `require_consent()` hiçbir write path’inde çağrılmıyor.

---

## 2. Eksik halka nerede

**Kalıcılık:** Consent hiçbir yerde saklanmıyor. `has_user_consent()` sadece sabit False. Bu yüzden "consent verildikten sonraki tekrar açılış" diye bir ayrım yok; her açılış "ilk açılış" gibi davranıyor (CLI’da hep onboarding çıkıyor).

**Consent verme akışı:** Kullanıcının consent’i "vermesi" ve bunun kaydedilmesi için kod yok. Onboarding sadece metin; "evet/kabul" sonrası bir bayrak yazılmıyor.

**State / dosya / bayrak:** State yok. Dokümanlarda ~/.lumos/consent.json (veya benzeri) geçiyor; kodda böyle bir dosya okunmuyor veya yazılmıyor. Base dir zaten repo’da `src/.lumos` veya `.lumos` (ve gerekirse kullanıcı ev dizini ~/.lumos) olarak kullanılıyor; consent için tek bir merkezi yer tanımlı değil.

**Özet:** Eksik halka, consent’in (a) bir kez alınıp (b) aynı base_dir’e yazılması ve (c) `has_user_consent()`’in bu dosyayı okuyup True/False döndürmesi. Şu an (a) ve (b) yok, (c) sabit False.

---

## 3. Minimum uygulanacak adımlar

- **Consent dosyası:** Base dir’de (mevcut `_lumos_dir()` ile uyumlu) tek bir dosya: örn. `consent.json`. İçerik minimal: örn. `{"granted": true}` veya sadece `granted` tarih/versiyon. `has_user_consent()` bu dosyayı okuyacak; geçerli ve "granted" ise True, yoksa False.

- **Consent verme:** Onboarding sonrası kullanıcıya tek soru: "Verileri kaydetmemi ister misin? (e/h)". "e" (veya evet/ok/yes) ise base_dir’e consent dosyasını yaz. Bu adım sadece `has_user_consent()` False iken gösterilsin; bir kez True olduktan sonra bu soru bir daha çıkmasın (tekrar onboarding’e düşme riski böyle kapanır).

- **Okuma yeri:** `consent.py` içinde base_dir’i bulmak için mevcut pattern: `__main__._lumos_dir()` veya `interactive_cli._lumos_dir()` ile aynı mantık (önce `src/.lumos`, yoksa `.lumos`). consent.py’nin tek başına path’e bağımlı olmaması için base_dir’i parametre veya env/cwd’den türetmek gerekir; mevcut modüller `_lumos_dir()` benzeri bir helper kullanıyor, consent de aynı kaynağı kullanmalı ki aynı dizine yazıp okusun.

- **Yazma koruması:** Persistence’ı consent’e bağlamak (V1’de istenirse): `require_consent()` veya `has_user_consent()` kontrolünü `apply_memory_save`, `save_user_identity`, `save_approved_preferences` (ve varsa diğer .lumos yazan yerler) öncesine eklemek. Consent yoksa yazma yapma veya exception at; böylece consent verilmeden kalıcı veri oluşmaz.

- **ask/chat:** İlk açılış davranışı için: ask/chat’ta da consent yoksa onboarding göstermek isteyebilirsin; bu ayrı karar. Minimum plan sadece CLI’da consent sorusu + dosyaya yazma + `has_user_consent()` okuma ile "tekrar açılışta onboarding’e düşme"yi çözer. ask/chat’a aynı consent dosyasına güvenmek yeterli; ek state gerekmez.

---

## 4. Test / smoke yaklaşımı

- **İlk açılış (consent dosyası yok):** `lumos cli` çalıştırıldığında "Merhaba." ve onboarding metni çıkar; ardından "Verileri kaydetmemi ister misin? (e/h)" (veya seçilen metin) gelir. "e" sonrası base_dir’de consent dosyası oluşur. Sonraki komutlarda (help, durum, kamera, exit) davranış değişmez.

- **Tekrar açılış (consent verilmiş):** Aynı base_dir’de consent dosyası varken `lumos cli` çalıştırıldığında onboarding ve "Verileri kaydet..." sorusu çıkmamalı; doğrudan izin satırı (varsa) ve "Sen: " gelmeli.

- **Smoke uyumu:** `scripts/smoke_kando_v0.sh` pipe ile help, durum, kamera, cik, exit gönderiyor; "Kando v0", "kilit | kamera", "LOCKED | Presence:", "Mode:", "Kamera:", "enabled=", "OK" aranıyor. Onboarding metni ("Merhaba") assert edilmiyor. Consent kalıcılığı gelince iki senaryo: (1) Smoke consent dosyası olmadan çalışırsa ilk çıktıda onboarding + soru gelir; script "e" göndermediği için kullanıcı "e" girmemiş olur, consent yazılmaz, bir sonraki smoke çalışmasında yine onboarding çıkar. (2) Smoke’tan önce consent dosyası oluşturulursa (veya smoke’un ilk girdisi "e" olursa) onboarding atlanır, mevcut check’ler aynen geçer. Öneri: Smoke’u consent verilmiş kabul edecek şekilde ayarla (test öncesi consent dosyası yarat veya pipe’a "e" ekle); böylece "tekrar açılış" davranışı da smoke ile doğrulanır ve yanlışlıkla tekrar onboarding’e düşme regresyonu yakalanır.

- **CLI dışı:** `lumos ask` / `lumos chat` için ayrı smoke varsa, consent dosyası varken çalıştığını varsaymak yeterli. Consent yokken ask/chat’a onboarding eklenirse, o zaman "consent yok" senaryosu için ayrı bir kısa test eklenebilir.

---

## 5. Yanlışlıkla tekrar onboarding’e düşme riski

- **Tek kaynak:** Consent durumu yalnızca bir dosyadan okunmalı (consent.json). Başka bayrak veya dağınık state olmamalı.

- **Base dir tutarlılığı:** Consent dosyası, CLI’ın kullandığı base_dir ile aynı yerde olmalı. `_lumos_dir()` (veya eşdeğeri) tek kullanılsın; böylece "src/.lumos" ile ".lumos" karışması olmaz, bir kez consent verildikten sonra aynı dizin tekrar açıldığında dosya bulunur.

- **Dosya silinirse:** Consent dosyası silinirse `has_user_consent()` False döner; bir sonraki CLI açılışında onboarding + soru tekrar çıkar. Bu beklenen davranış (kullanıcı consent’i geri aldı kabul edilebilir).

- **Ask/chat:** Ask/chat aynı base_dir’i kullanıyorsa (user_identity, user_memory path’leri ile) consent dosyası aynı yerde olduğu sürece tutarlılık korunur; ek risk yok.

---

## Özet

- **Şu an:** Sadece CLI’da consent kontrolü var; `has_user_consent()` hep False. Onboarding her seferinde gösteriliyor, consent hiç yazılmıyor. ask/chat consent’e bakmıyor, persistence’ta require_consent() yok.
- **Eksik:** Consent’in diske yazılması ve `has_user_consent()`’in oradan okuması; onboarding sonrası "kaydetmemi ister misin?" ve "e" ile yazma.
- **Minimum:** consent.json (veya eşdeğeri) tek kaynak; onboarding sonrası tek soru + yazma; consent.py’de bu dosyayı oku; persistence path’lerinde require_consent() (V1’de); smoke’u consent verilmiş senaryoya göre güncelle ve tekrar açılışta onboarding çıkmadığını doğrula.
