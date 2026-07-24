# Bridge / Agent Faz Geçiş Kriterleri

Bu doküman, bridge/agent katmanının hangi fazda ne yapabileceğini ve bir sonraki faza geçiş şartlarını tanımlar. Yetki sınırları için bkz. `docs/BRIDGE_AGENT_AUTHORITY_MODEL.md`.

**Genel kural:** Faz yükseltmesi otomatik değildir; kullanıcı veya operatör açık kararı gerekir. Test veya doğrulama olmadan iş tamamlanmış sayılmaz.

---

## Faz 0 — Gözlem ve analiz

### Amaç
Repo, dosya sistemi ve cihaz durumunu **sadece okuyarak** anlamak. Karar ve plan üretmek; hiçbir yan etki yaratmamak.

### İzin verilen işlemler
- Dosya/repo/durum **okuma** (read-only)
- Doküman inceleme (`docs/`, sözleşmeler, kurallar)
- Durum özeti, teşhis notu, plan taslağı üretme (metin çıktısı; kalıcı yazma yok)
- Düşük riskli listeleme (salt okuma: dizin içeriği, git status, log okuma)

### Yasak işlemler
- Her türlü dosya oluşturma, değiştirme, silme, taşıma
- Terminal komutu çalıştırma (okuma dışı)
- Uygulama/OS kontrolü
- Mail, takvim, kişiler, ödeme, domain, dış servis yazma
- Kalıcı silme veya çöp dışı silme

### Kullanıcı onayı gerektiren işlemler
- Faz 0'da **yazma veya yürütme yok**; onay gerektiren işlem tanımlı değildir.
- Faz 1'e geçiş kararı kullanıcı/onay sahibi tarafından verilir.

### Çıkış / geçiş şartı
- Hedef alan için okuma tabanlı durum özeti üretilmiş olmalı.
- Açık belirsizlikler "tahmin" olarak işaretlenmiş olmalı.
- Kullanıcı Faz 1'i açıkça onaylamalı.

### Test veya doğrulama beklentisi
- Okunan kaynaklar (dosya yolu, komut çıktısı referansı) özette belirtilmeli.
- Mock/sahte çıktı gerçek sistem çıktısı gibi sunulmamalı.

---

## Faz 1 — Düşük riskli okuma ve sınırlı dokümantasyon

### Amaç
Kontrollü listeleme ve durum okuma ile bilgi toplamak. Gerekirse **yalnızca dokümantasyon** eklemek veya güncellemek.

### İzin verilen işlemler
- Faz 0'daki tüm okuma işlemleri
- Sınırlı, düşük riskli listeleme (izin verilen kök/path altında)
- `docs/` altında **dokümantasyon** oluşturma veya güncelleme (kullanıcı isteği veya açık görev kapsamında)
- Okuma amaçlı terminal komutları (ör. `git status`, `ls`, salt okuma sorguları) — **yalnızca tanımlı allowlist ile** *(allowlist henüz kodda sabitlenmediyse: operatör onayı + tek komut kuralı geçerli; tahmin)*

### Yasak işlemler
- Uygulama kodu, config, çekirdek state dosyalarında değişiklik
- Dosya silme (geçici dahil, çöp hariç her türlü)
- Yazma gerektiren terminal komutları
- Uygulama açma, OS/cihaz kontrolü
- Mail, takvim, kişiler, ödeme, domain
- Kalıcı silme
- Geniş kapsamlı refactor veya kapsam dışı dosya değişikliği

### Kullanıcı onayı gerektiren işlemler
- `docs/` dışına herhangi bir dosya yazma
- Allowlist dışı terminal komutu
- Faz 2'ye geçiş kararı

### Çıkış / geçiş şartı
- Görev kapsamı net; dokümantasyon veya okuma çıktısı doğrulanmış olmalı.
- Yan etki yaratılmadığı (sadece izin verilen alanlara dokunulduğu) kontrol edilmeli.
- Kullanıcı Faz 2'yi açıkça onaylamalı.

### Test veya doğrulama beklentisi
- Oluşturulan/güncellenen doküman hedefe uygun mu — manuel veya checklist ile doğrulanmalı.
- İstenmeyen dosya değişikliği yok (`git status` veya eşdeğeri).

---

## Faz 2 — Onaylı dosya ve küçük kod değişiklikleri

### Amaç
Kullanıcı onayı ve dar kapsam ile dosya oluşturma/değiştirme. Kod değişiklikleri **küçük, hedefli ve testli** olmalı.

### İzin verilen işlemler
- Faz 1 izinleri
- Onaylı dosya oluşturma, düzenleme (görev kapsamındaki path'ler)
- Küçük kod değişiklikleri (tek sorumluluk, minimum diff)
- Birim/ilgili test çalıştırma ve lint (görev doğrulaması için)
- Silme yerine **çöp/yedek** mantığı: `.lumos/trash/` veya tanımlı yedek alanına taşıma *(path sözleşmesi: workspace kuralları)*

### Yasak işlemler
- Onaysız veya kapsam dışı dosya değişikliği
- Kalıcı silme (`SECURITY_NEVER_AUTO` alanları dahil)
- Mail gönderme/silme, takvim, kişiler
- Ödeme, domain alma/yenileme
- Serbest terminal / keyfi komut zinciri
- Uygulama/OS kontrolü (Faz 3 konusu)
- Büyük refactor, çok dosyalı kapsam genişletmesi
- Test veya doğrulama olmadan "tamamlandı" demek

### Kullanıcı onayı gerektiren işlemler
- Her kalıcı etkili dosya yazma/değiştirme (görev onayı = kapsam onayı)
- Çekirdek state path'lerine dokunma (`tasks/`, `config/`, vb.)
- Trash dışına taşıma veya geri alınamaz değişiklik
- Commit / push *(ayrı açık komut gerekir)*
- Faz 3'e geçiş kararı

### Çıkış / geçiş şartı
- İlgili test(ler) geçmiş veya doğrulama kanıtı kayıtlı olmalı.
- Lint/kalite kapısı (projede tanımlıysa) temiz.
- Kapsam dışı dosya değişikliği yok.
- Kullanıcı Faz 3'ü **ayrı güvenlik modeli** ile açıkça onaylamalı.

### Test veya doğrulama beklentisi
- Değişen davranış için ilgili test veya manuel VERIFY adımı zorunlu.
- CI/local test sonucu özette belirtilmeli; kanıt yoksa durum "doğrulanamadı" olmalı.

---

## Faz 3 — Komut, cihaz ve uygulama kontrolü (yüksek risk)

### Amaç
Terminal komutu, cihaz/OS işlemleri ve uygulama kontrolü gibi **yüksek riskli** işleri yalnızca ayrı güvenlik modeli ve **açık kullanıcı onayı** ile yürütmek.

### İzin verilen işlemler
- Faz 2 izinleri (onaylı yazma/test ile)
- Onaylı terminal komutu çalıştırma (allowlist + tek adım veya onaylı plan)
- Onaylı uygulama açma/kontrol, cihaz/OS işlemleri
- Onaylı dış servis **okuma** (yazma ayrı onay)
- Tüm işlemler **loglanır**: ne yapıldı, hangi komut, sonuç

### Yasak işlemler
- Açık onay olmadan Faz 3 işlemi başlatmak
- Mail, takvim, kişiler üzerinde **otomatik** işlem
- Ödeme, domain işlemleri — **asla otomatik**
- Kalıcı silme — **asla otomatik**; yalnızca kullanıcı açık komutu + uyarı
- Gizli bilgileri gereksiz toplama veya loglama
- Onaysız force push, destructive git, sistem ayarı değişikliği
- Sahte/mock çıktıyı gerçek sonuç gibi sunmak

### Kullanıcı onayı gerektiren işlemler
- **Her** terminal komutu (ilk çalıştırma veya allowlist dışı)
- Uygulama/OS/cihap kontrolü
- Dış servise yazma, mail gönderme/silme, takvim CRUD, kişiler erişimi
- Ödeme, domain, kalıcı silme
- Çok adımlı otomasyon zinciri (genel onay veya adım adım onay)

### Çıkış / geçiş şartı
- Faz 3 görevi tamamlandığında: log + doğrulama kaydı mevcut.
- Riskli işlem sonrası durum kullanıcıya özetlenmiş olmalı.
- Faz düşürme (3→2 veya 2→1): oturum/kapsam bitiminde veya kullanıcı talebiyle; varsayılan **düşük faz**a dön.

### Test veya doğrulama beklentisi
- Komut çıktısı, dosya durumu veya uygulama state'i gerçekten kontrol edilmeli.
- Beklenen yan etki olmadığı doğrulanmalı (regresyon / istenmeyen dosya değişikliği).
- Doğrulama yoksa iş **tamamlanmış sayılmaz**.

---

## Faz özeti

| Faz | Odak | Yazma | Terminal / OS | Otomatik yasaklar |
| --- | --- | --- | --- | --- |
| 0 | Okuma, analiz | Hayır | Hayır | Tüm yan etkili işler |
| 1 | Okuma + sınırlı docs | Yalnızca `docs/` | Salt okuma *(allowlist)* | Kod, silme, dış servis |
| 2 | Onaylı dosya/kod | Evet (onaylı, küçük) | Test/lint amaçlı | Faz 3 işleri, kalıcı silme |
| 3 | Komut, cihaz, uygulama | Evet (loglu) | Evet (onaylı) | Mail/ödeme/domain/kalıcı silme otomatik |

---

## Ortak kurallar (tüm fazlar)

1. **Silme:** Önce çöp/yedek; kalıcı silme yalnızca açık kullanıcı komutu.
2. **Onay:** Belirsiz veya riskli adımda dur; tahminleri açıkça işaretle.
3. **Doğrulama:** Test, lint veya kanıtlı VERIFY olmadan tamamlandı deme.
4. **Log:** Faz 2+ yazma ve Faz 3 tüm yürütme işlemleri izlenebilir olmalı.
5. **Ürün yüzü:** Son kullanıcıya Lumos; iç katman adları (Core / Local vb.) görünmez.

---

## Belirsizlik notu

- Faz 1 **terminal allowlist** içeriği kod tabanında henüz sabitlenmemiş olabilir; bu dokümanda operatör onayı + tek komut kuralı geçici çerçevedir.
- Faz 3 **ayrı güvenlik modeli** detayı (allowlist şeması, oturum kilidi) ayrı dokümanda netleştirilecektir; bu dosya geçiş kapılarını tanımlar, implementasyonu değil.
