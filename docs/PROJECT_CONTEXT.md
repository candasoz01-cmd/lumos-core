# Lumos Project Context

## Active project root

`/Users/candasoz/work_2026/lumos-core`

`work_2026` genel klasördür; proje kökü gibi kullanılmamalıdır. Aktif gerçek proje kökü `lumos-core` klasörüdür. `lumos-demo` varsa ayrı/yan klasör olarak değerlendirilmelidir.

## Current migration status

Business workspace eski bağlam/yedek olarak korunuyor. Plus tarafında `Project_Lumos` yeni devam alanı olarak kuruldu. Kod işi henüz başlatılmadı.

## Work style

- Türkçe, kısa, net ve doğal ilerlenir.
- Aynı anda tek hedef seçilir.
- Kapsam genişletilmez.
- Kullanıcının açıkça istemediği refactor, dosya taşıma, tasarım değişikliği veya yan düzeltme yapılmaz.
- Kod değiştirmeden önce ne yapılacağı kısa yazılır.
- Minimum değişiklik tercih edilir.
- Test veya doğrulama yapılmadan iş tamamlanmış sayılmaz.
- Emin olunmayan yerde tahmin açıkça belirtilir.
- Gerçek dosya, terminal çıktısı veya repo durumu görülmeden kesin konuşulmaz.
- Sahte/mock ekran veya hayali çıktı gerçek sistem çıktısı gibi sunulmaz.

## Terminal and file rules

- Terminal komutları kısa ve doğrudan olmalıdır.
- Terminal komutlarında yorum satırı kullanılmaz.
- Komut ile dosya içeriği karıştırılmamalıdır.
- Gerekirse `TERMINAL` ve `DOSYA` başlıklarıyla ayrılmalıdır.

## Product rules

- Son kullanıcıya görünen dış yüz Lumos’tur.
- Kando/Cando gibi iç katman adları ürün arayüzünde görünmemelidir.
- Lumos güvenli geçit/orchestrator gibi düşünülür.
- Silinen içerikler kalıcı yok edilmez; çöp/silinenler alanına taşınır.
- Kalıcı silme kararı kullanıcıda kalır.
- Lumos açık onay olmadan ödeme yapmaz, domain almaz, mail göndermez/silmez, dosya kalıcı silmez veya riskli işlem başlatmaz.

## Current decision

Codex klasör seçme tarafı zorlanmayacak. Cursor dosyaları gördüğü için gerçek kod işleri Cursor üzerinden yürütülecek. Plus tarafı bağlam/karar/plan alanı olarak kullanılacak.
