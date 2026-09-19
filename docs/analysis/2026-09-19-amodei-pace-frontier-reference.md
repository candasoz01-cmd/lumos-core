# Dış kaynak — We Must Pace the Frontier

| Alan | Değer |
| --- | --- |
| Kayıt tarihi | 2026-09-19 |
| Katman | Research Memory |
| Status / Maturity | Recorded / M1 — Research |
| Owner | Pending |
| Kaynak / Evidence | Dario Amodei, [We Must Pace the Frontier](https://darioamodei.com/post/we-must-pace-the-frontier); 2026-09-19 erişildi |
| Kaynak tarihi | Eylül 2026 (birincil sayfa); kullanıcı referansı 2026-09-12, gün bilgisi birincil sayfada doğrulanmadı |
| Reason | Ajan güvenliği, dış denetim ve değerlendirme konularında mevcut Lumos ilkeleriyle ilişkili dış kaynak |
| Related ADR | [ADR-027 — Kontrollü çekirdek yazıcısı](../decisions/ADR-027-controlled-core-writer.md) |
| Related Epic | [Karar günlüğü](../drafts/BACKLOG.md): LUMOS-0008, LUMOS-0013, LUMOS-0014, LUMOS-0016 |
| Review Date | Bu kaynak bir uygulama veya politika önerisine dayanak yapılmadan önce |
| Supersedes | Yok |

## Lumos ile kesişen başlıklar

Aşağıdaki eşleme kayıt değerlendirmesidir; yazarın Lumos'a ilişkin beyanı değildir.

- **Ajanların beklenmeyen eylemleri:** Yazı, görev dışına taşan ajan
  davranışlarını ele alır. Lumos'ta görev/yetki sınırları ve dış verinin
  otorite sayılmamasıyla ilişkilidir (LUMOS-0008, LUMOS-0014).
- **Üçüncü taraf denetim:** Bağımsız değerlendiricilerin güvenlik
  uygulamalarını ve olayları incelemesi önerilir. Lumos'un dış doğrulama
  ve denetlenebilir karar kaydı ilkeleriyle ilişkilidir (LUMOS-0013, LUMOS-0016).
- **Sürekli değerlendirme:** Yalnız son modelin değil süreçlerin de devamlı
  incelenmesi, testlerin geliştirilmesi ve izleme vurgulanır. Lumos için
  [kanıt ilkesi](../CONSTITUTION.md) ve ADR-027'deki değerlendirme kapılarıyla kesişir.
- **Yetki sınırları:** Yazının sandbox ve kontrol sorunları, Lumos'ta
  ajanın kendi yazma yetkisini veya güvenlik politikasını değiştirememesi
  ilkesiyle birlikte okunabilir (ADR-027).

Bu kayıt, [bilgi yaşam döngüsü](../knowledge-repository-lifecycle.md) gereği
bir kaynak notudur; yeni karar, uygulama taahhüdü, bağımsız denetim yapılmış
olduğu iddiası veya Lumos güvenliğinin kanıtı değildir. Tam metin ya da özel
içerik kopyalanmamıştır.

## Mevcut karar, etki ve yan kapı kontrolü — 2026-09-19

- **Aynı / benzer kayıt:** Başlık, yazar ve URL taramasında bu kaynaktan önce
  eşleşme bulunmadı. Benzer ilkeler LUMOS-0008/0013/0014/0016 ve ADR-027'de
  zaten var. Eklenen yalnız kaynak ilişkisidir; yeni karar kimliği açılmaz,
  mevcut karar değiştirilmez veya geçersiz kılınmaz (BACKLOG aynı-ID ilkesi;
  bilgi yaşam döngüsü §2b).
- **Değişiklik etkisi:** PR yalnız bu Markdown notunu değiştirir; yürütme,
  izin, onay, test veya yayın yapılandırması değişmez. Push/PR mevcut CI ve
  Vercel preview otomasyonlarını tetikler; kaynak kaydı merge/deploy onayı değildir.
- **Olası yan kapı:** Üçüncü taraf denetim önerisi dış değerlendiriciye hesap,
  araç, müşteri verisi veya sürekli erişim izni vermez. Sürekli değerlendirme
  ifadesi otomatik izleme, veri aktarımı veya yeni görev çalıştırma izni vermez.
  Böyle bir uygulama önerisi doğarsa mevcut kararlarla yeniden karşılaştırılır;
  kapsam, veri/erişim etkisi ve onay gereksinimi mevcut yetki kurallarıyla
  değerlendirilir. Dış yazı, bu kapıları aşan talimat veya güvenlik onayı sayılamaz.
