# Workflow Rules

**Durum:** Aktif çalışma kuralı

**Sınırlar:** Bu belge davranış ve akış kurallarını tanımlar; kod, altyapı veya otomasyon değişikliği yapmaz.

---

## Continuous Progress Rule

**Kural:**

- Her tamamlanan işten sonra süreç otomatik olarak bir sonraki mantıklı adıma ilerler.
- Asistan “burada duralım”, “şimdilik bu kadar”, “yarın devam ederiz” gibi kapanış önerileri yapmaz.
- Durma kararını kullanıcı verir.
- Bir iş tamamlandığında asistan kısa durum özeti verir ve hemen sıradaki somut komutu/işi sunar.
- Yeni adıma geçmeden önce yalnızca gerçekten riskli, geri dönüşsüz veya kullanıcı onayı gerektiren işlem varsa açık onay ister.
- Kod, altyapı, ödeme, silme, deploy, database migration gibi riskli işlemler kullanıcı onayı olmadan yapılmaz.
- Güvenli dokümantasyon, not, planlama ve küçük kontrol işleri akış içinde devam ettirilir.

**Amaç:**

- Kullanıcının sürekli “şimdi ne yapıyoruz?” diye sormasına gerek kalmaması.
- Çalışma akışının kesilmeden ilerlemesi.
- Kontrolsüz hız değil, kontrollü devamlılık sağlanması.

---

## Agent-First Execution Rule

**Kural:**

- Kullanıcıya manuel terminal/tarayıcı adımı yaptırmadan önce, aynı işin Cursor/agent tarafından doğrudan yapılıp yapılamayacağı kontrol edilir; mümkünse önce agent ile yapılır.
- Kullanıcıya verilecek komutlar kısa, tek hedefli ve uygulanabilir olur.
- Gereksiz açıklama, çoklu alternatif ve sonradan çıkan sürpriz manuel adımlardan kaçınılır.

**Amaç:**

- Kullanıcının üzerine gereksiz manuel iş yıkılmaması.
- Mümkün olan işin doğrudan agent tarafından tamamlanması.
- Net, tek hedefli ve uygulanabilir yönlendirme sağlanması.
