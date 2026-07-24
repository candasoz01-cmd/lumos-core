# Lumos karar mekanizması ve çekirdek sınırları — minimum uygulanabilir sözleşme

Bu belge, Lumos’un neyi yapıp yapamayacağını, ne zaman duracağını ve kullanıcıdan ne zaman açık onay isteyeceğini tanımlar. Ürün tarafındaki sıkı kurallara referans verir; mevcut çekirdeğe uygulanabilir **minimum omurga** hedeflenir. Core (geliştirme süreci) kurallarından ayrıdır. **Geliştirme commit guard** (ruff/pytest) ürün onayı değildir; ayrım: `docs/kando-urun-onay-otomasyon-ayrimi.md`.

---

## 1. Karar katmanları

| Katman | Açıklama | Örnek |
|--------|----------|--------|
| **Sadece cevap ver** | Hiçbir state değişikliği, sadece bilgi/onay metni. | `durum`, `hazır`, `yardım`, `görevler`, `görev durumu <id>`, `yetki profili`, `hangi moddayım` |
| **Analiz et ama uygulama yapma** | Okuma/analiz/plan/özet; kalıcı yazma veya dış aksiyon yok. | Yetki profili **rapor**: tüm adımlar sadece analyze/read/plan; görev çalışsa bile uygulama yapılmaz, sadece rapor/simülasyon. |
| **Öner ama bekle** | Öneri veya taslak üret; kullanıcı onayı olmadan uygulama yapma. | `genel onay kapat` iken write_local adımlar yapılmaz; öneri/plan düzeyinde kalır. Benzer görev uyarısı: “İstersen önce onu inceleyebilirsin.” |
| **Açık onayla uygula** | Kullanıcı açık komut veya genel onay verince izin profili kapsamında uygula. | `genel onay aç` + **kisitli_otonom**: safe_local ve sınırlı write_local yürütülür. Kilidi aç: passphrase ile açık kullanıcı aksiyonu. |
| **Asla dokunma** | Profil/onaydan bağımsız; sistem bu işleri otomatik veya tek taraflı yapmaz. | Kalıcı silme (otomatik), dış servise kontrolsüz yazma, geri dönüşsüz kullanıcı işlemi, kritik sistem ayarı değişikliği. |

**Referans (kod):** `task_engine/profiles.py` — `STEP_TYPE_*`, `SECURITY_NEVER_AUTO`, `is_allowed_for_profile()`.

---

## 2. Dokunulmaz çekirdek alanlar

Bu alanlara **ürün/geliştirme sözleşmesi** ve **güvenlik sınırı** gereği dokunulmaz; gevşetilmez veya sessizce değiştirilmez.

| Alan | Kural |
|------|--------|
| **Güvenlik** | Kilit, keystore, presence, consent, kimlik (identity). Online modda kimlik ve kilit açık olmadan işlem yapılmaz. Çocuk kullanıcıda güvenlik ve ebeveyn kontrolü önceliklidir. |
| **Yetki** | Üç profil sabit: **rapor** (sadece analiz/okuma/plan), **guvenli_yurut** (+ safe_local), **kisitli_otonom** (genel onay ile + sınırlı write_local). critical ve external asla izinli değil. |
| **Temel politika** | Offline modda hiçbir dış/network işlemi yok. Online modda yalnızca çağrıldığında çalışır. Emin olmadığı yerde konuşmaz; boşluk doldurmaz. |
| **Kalıcı silme** | Doğrudan kalıcı silme **otomatik** yapılmaz. Kalıcı silme yalnızca kullanıcının açık komutu (ör. `görev sil <id>`) ile ve tek satır uyarı ile yapılır; geri alınamaz. Çöp/silinenler için yalnızca önceden tanımlı `.lumos/trash/` kullanılır (workspace sözleşmesi). |
| **Ana karar sınırları** | `SECURITY_NEVER_AUTO`: permanent_delete, external_write, irreversible_user_op, critical_system_config — bunlar asla otomatik. |
| **Çekirdek davranış sözleşmesi** | Karakter: güven verir ama manipüle etmez. İlerleme “yapmadığı yanlışlarla” ölçülür. Çekirdek, güvenlik, yetki, dürüstlük modeli ve durum modeli alanlarına kapsam dışı dokunma (Core ile uyumlu). |

---

## 3. Kontrollü geliştirilebilir alanlar

Bunlar sözleşmeyi bozmadan **biçim ve davranış detayında** geliştirilebilir; çekirdek sınırları değiştirilmez.

| Alan | Açıklama |
|------|----------|
| **Prompt/cevap biçimi** | `Sen:` promptu, yardım metinleri, komut örnekleri, kısa/uzun yardım blokları. |
| **Görev önerileri** | “Bana ne önerirsin”, “bir sonraki adım ne”, “en önemli eksik ne” cevaplarının içeriği ve sırası. |
| **Yardımcı araçlar** | Alias, self test, durum özeti, hazır özeti — işlev korunur, arayüz/metin iyileştirilebilir. |
| **Açıklama derinliği** | Hata mesajları, “neden anlamadın” cevabı, fallback metinleri (nötr / aile bazlı). |
| **Loglama/raporlama biçimi** | Log satır formatı, event adları, rapor çıktı biçimi — yol ve yetki değişmez. |

---

## 4. Sandbox / kopya alanı

Lumos kendi üzerinde deneme yapacaksa (ör. gelecekte taslak/deneme özelliği):

| Kural | Açıklama |
|-------|----------|
| **Hangi alan** | Bu aşamada `sandbox/`, `data/`, `exports/` sistem sözleşmesinin parçası değil; açılacaksa sözleşme ve dokümantasyonla tanımlanır. |
| **Sınırlar** | Deneme/kopya alanı **aktif state kaynağı** olarak kullanılmaz; görev/not/durum okuması yalnızca tanımlı omurga (tasks, notes store, config) üzerinden yapılır. |
| **Overwrite yasağı** | Kullanıcı verisi veya çekirdek state (tasks.json, notlar, config, log) doğrudan overwrite edilmez; kopya/deneme ayrı konumda tutulur. |

---

## 5. Kullanıcı onayı mantığı

| Tür | Ne zaman | Örnek |
|-----|----------|--------|
| **Açık onay gerekir** | Kilidi açmak (passphrase), kalıcı silme (`görev sil <id>`), genel onay ile çok adımlı iş (kisitli_otonom: `genel onay aç`). |
| **Sadece öneri verilir** | Genel onay kapalıyken write_local adımlar; benzer görev uyarısı; “İstersen …” ile biten yönlendirmeler. |
| **Sistem otomatik durur** | Yetki profili veya genel onay dışı adım: “Bu adım yetki profili veya genel onay kapsamında değil.” Online’da kilit/kimlik yoksa işlem yapılmaz. Emin değil (confidence < eşik): cevap verilmez (PolicyRules). |

---

## 6. Cevap disiplini

| Durum | Davranış |
|-------|----------|
| **Veri yoksa** | Boşluk doldurmaz. “Kayıtlı görev yok.”, “Görev bulunamadı.”, “Henüz kayda değer bir işlem yapmadım.” gibi net ifade. |
| **Belirsizlik varsa** | “Bunu anlamadım.” + örnek komutlar veya aile önerisi (fallback). Online’da confidence düşükse cevap üretilmez (Emin değil). |
| **Risk varsa** | Kalıcı silme sonrası tek satır uyarı: “Dikkat: Bu görev kalıcı olarak silindi ve geri alınamaz.” Güvenlik durumu: “Şu an tam güvenli değilsin …” / “Şu an güvenlisin.” |
| **Tamamlanmamış iş** | Görev durumu: status (tamamlandi, kismi, simulasyon, dogrulanamadi, hata); adım sonuç türü (verified/simulation/error). “self test: failed (N/M)” + kırık alanlar. |

**Referans:** `UNKNOWN_CMD_TEXT`, `get_fallback_message()`, `_get_guvenli_cevap()`, task status ve `result_kind`.

---

## 7. En dar uygulanabilir sözleşme (özet)

- **Karar katmanları:** Sadece cevap → analiz (uygulama yok) → öner (bekle) → açık onayla uygula → asla dokunma.
- **Dokunulmaz çekirdek:** Güvenlik, yetki profilleri, temel politika, kalıcı silme kuralı, SECURITY_NEVER_AUTO, karakter/dürüstlük.
- **Kontrollü alanlar:** Prompt/cevap biçimi, görev önerileri, yardımcı araçlar, açıklama derinliği, loglama/raporlama biçimi.
- **Sandbox:** Bu aşamada sözleşme dışı; açılırsa tanımlı alanda, aktif state overwrite edilmeden.
- **Onay:** Açık onay (kilit, kalıcı silme, genel onay); öneri (genel onay kapalı / write_local); otomatik dur (yetki dışı, kilit/kimlik yok, emin değil).
- **Cevap disiplini:** Veri yoksa boşluk doldurma; belirsizlikte “anlamadım” + örnek; riskte uyarı; tamamlanmamış işte açık status/result_kind.

Bu sözleşme, mevcut Lumos çekirdeği (profiles, policy, workspace sözleşmesi, CLI akışı) ile uyumlu minimum omurgadır; genişletme yapılırken dokümantasyon güncellenir.
