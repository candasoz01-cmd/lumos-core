# V1 fiziksel macOS lock: teşhis ve minimum plan

Kando v0’da presence zinciri çalışıyor; fiziksel macOS ekran kilidi tarafı tam garanti değil. V1’de kesinleştirmek için mevcut durum ve minimum adımlar. Dosya değiştirme yok; analiz.

---

## 1. Şu anki gerçek durum özeti

**Presence timeout zinciri:** Yüz yok → absence_timeout log → lock_cb çağrılıyor. lock_cb sırasıyla: do_lock (Lumos lock state, passphrase temizleme), device_lock_cli (note_memory.device_lock no-op + "Cihaz kilitlendi" veya hata), ardından cfg yüklenip Darwin ve lock_mode in (mac, lumos+mac) ise trigger_macos_screen_lock() çağrılıyor. Bu zincir presence_lock thread’inden çalışıyor; _lock_cb presence_menu içinde tanımlı ve sadece kullanıcı kamera menüsünden "ac" ile presence’ı açtığında kullanılıyor.

**macOS lock çağrısı:** presence_lock.trigger_macos_screen_lock() önce login.framework (ctypes) ile SACLockScreenImmediate(); result==0 ise True dönüyor. Exception olursa pmset displaysleepnow (subprocess, timeout=2, check=False) deneniyor; çalıştırılırsa True dönüyor. pmset’in çıkış kodu kontrol edilmiyor; yani "başarılı" sayılabilir ama ekran kilitlenmemiş olabilir. Darwin dışında False; hiçbir yerde ekran kilidi yok.

**Başarısızlık loglama:** Sadece presence_menu’deki _lock_cb içinde: trigger_macos_screen_lock() False dönerse state.log_event(macos_lock_failed); exception’da macos_lock_error. Loglar .lumos/log.txt’e _append_log ile gidiyor. trigger_macos_screen_lock() içinde log yok; hangi yöntemin kullanıldığı veya neden False döndüğü yazılmıyor. Başarı durumu hiç loglanmıyor (macos_lock_triggered yok).

**Manuel lock vs presence lock:** "Kilit" menüsünde "kapat" → sadece do_lock + device_lock_cli. device_lock_cli lumos.note_memory.device_lock() çağırıyor (memory.py’de no-op) ve "Cihaz kilitlendi" basıyor. trigger_macos_screen_lock() hiç çağrılmıyor. Yani manuel kapatma ekranı kilitlemiyor; sadece Lumos state kilitleniyor. Presence timeout path’inde ise do_lock + device_lock_cli + trigger_macos_screen_lock() var; fark bu.

**Recovery path:** Başlangıçta recover_presence → recover_if_needed; gerekirse presence thread yeniden başlatılıyor. Bu durumda kullanılan lock_cb _recovery_lock_cb. _recovery_lock_cb içinde do_lock, device_lock_cli, sonra cfg’ye göre trigger_macos_screen_lock() çağrılıyor ama sonucu ve exception’ı try/except pass ile yutuluyor; hiç log yok. Yani recovery ile tetiklenen lock’ta macOS lock başarı/başarısızlık izi bırakılmıyor.

**Özet:** Presence (kamera menüsünden açılan) timeout’ta macOS lock deneniyor ve sadece bu path’te hata loglanıyor. Manuel kilit kapat macOS lock yapmıyor. Recovery lock_cb macOS lock sonucu loglamıyor. trigger_macos_screen_lock içinde teşhis yok; pmset başarısı doğrulanmıyor.

---

## 2. Eksik halka nerede

**Tek nokta değil; birkaç zayıf halka:**

- **trigger_macos_screen_lock:** SACLockScreenImmediate private API; sandbox/izin reddinde veya farklı macOS sürümünde sessizce fail edebilir. İkinci seçenek pmset; exit code bakılmıyor, "çalıştı" diye True dönülüyor. İkisi de fail ederse False; ama hangi adımın fail ettiği logda yok.

- **Manuel "kilit kapat":** Fiziksel lock hiç tetiklenmiyor. Tasarım kararı (v0 sınır) ama ürün beklentisi "kapat deyince ekran da kilitlensin" olabilir; tek davranış noktası yok (presence var, manuel yok).

- **Recovery lock_cb:** Aynı lock zinciri (do_lock, device_lock_cli, macOS lock) çalışıyor ama sonuç loglanmıyor. Arızada logda iz kalmaz; teşhis zor.

- **Başarı logu yok:** Sadece fail loglanıyor. Logda "macos_lock_triggered" veya eşdeğeri olmadığı için "çağrıldı mı, geçti mi" ayrımı yapılamıyor; sadece "macos_lock_failed" görürsen fail biliyorsun.

- **pmset doğrulanmıyor:** subprocess.run check=False; returncode 0 değilse bile True dönülüyor. Ürünlük için en azından returncode kontrolü veya log gerekir.

---

## 3. Ürünlük için minimum adımlar

**trigger_macos_screen_lock güvenilirliği:** (a) İlk yöntem (SACLockScreenImmediate) denendikten sonra result ve gerekirse errno/hata bilgisi loglansın; exception’da hangi exception olduğu kısa loglansın. (b) pmset fallback’te subprocess çıkış kodu kontrol edilsin; 0 değilse False dönülsün ve isteğe bağlı log (pmset_failed, returncode=…). (c) Başarılı tetiklemede tek satır log (örn. macos_lock_triggered, method=sac|pmset) — teşhis ve denetim için.

**Tek davranış noktası (opsiyonel ama önerilen):** Fiziksel lock tetiklemesi tek fonksiyondan (trigger_macos_screen_lock veya ince bir sarmalayıcı) yapılsın; hem presence lock_cb hem manuel "kilit kapat" bu noktayı çağırsın. Böylece manuel kapat da ekranı kilitleyebilir; presence ve manuel aynı garantiyi paylaşır. Şu an manuel hiç çağırmıyor; eklenmesi minimum kod değişikliği.

**Recovery lock_cb loglama:** _recovery_lock_cb içinde trigger_macos_screen_lock sonucu ve exception’ı presence_menu’deki _lock_cb ile aynı şekilde loglansın (macos_lock_failed / macos_lock_error). Böylece recovery ile tetiklenen lock’ta da iz kalır.

**Başarısızlık anlamı:** macos_lock_failed / macos_lock_error zaten var (sadece presence_menu path’inde). Logda method (sac vs pmset) veya err bilgisi olursa sahada neden fail ettiği daha net anlaşılır. trigger_macos_screen_lock içinde veya hemen çağrı sonrası tek satır yeterli.

---

## 4. Test / doğrulama yaklaşımı

**Birim seviyesi:** trigger_macos_screen_lock’u mock’layarak: (a) False döndüğünde presence path’inde macos_lock_failed log’unun yazıldığı, (b) exception fırlattığında macos_lock_error log’unun yazıldığı, (c) True döndüğünde (ve ileride başarı logu eklendiyse) macos_lock_triggered veya eşdeğerinin yazıldığı assert edilebilir. Darwin dışı platformda False ve log üretilmemesi de test edilebilir. Dosya değişmediği için bu maddeler "planlanan testler" olarak not.

**Entegrasyon (gerçek ortam):** macOS’ta presence aç → yüzü kapat / kameradan uzaklaş → timeout sonrası ekranın kilitlendiği ve .lumos/log.txt’te device_locked, (opsiyonel) macos_lock_triggered veya macos_lock_failed görüldüğü manuel veya yarı otomatik script ile doğrulanır. Manuel "kilit kapat" için: plan uygulanırsa aynı log + ekran kilidi beklenir.

**Başarısızlık senaryosu:** İzin verilmeyen veya sandbox’lı ortamda (örn. bazı CI) SACLockScreenImmediate ve pmset fail edebilir; logda macos_lock_failed veya macos_lock_error görülmeli. Bu ortamda "ekran kilitlendi" iddia edilmemeli (False + log).

**Recovery:** recover_if_needed ile presence’ın yeniden başlatıldığı senaryoda timeout tetiklenince _recovery_lock_cb çalışır; plan uygulanırsa bu path’te de aynı loglar (başarı/başarısızlık) yazılmalı ve testte kontrol edilebilir.

---

## 5. Özet (teşhis → plan)

**Teşhis:** Fiziksel macOS lock sadece presence timeout path’inde (ve recovery’de aynı cb ile) tetikleniyor; manuel "kilit kapat" tetiklemiyor. Başarısızlık sadece presence_menu _lock_cb’de loglanıyor; recovery’de log yok. trigger_macos_screen_lock içinde teşhis yok; pmset başarısı doğrulanmıyor; başarı hiç loglanmıyor.

**Minimum plan:** (1) trigger_macos_screen_lock: başarı/başarısızlık ve kullanılan yöntem (sac/pmset) için tek satır log; pmset returncode kontrolü. (2) Recovery lock_cb: macOS lock sonucunun aynı loglarla yazılması. (3) İsteğe bağlı: manuel "kilit kapat"ın da trigger_macos_screen_lock çağırması (tek davranış noktası). (4) Test: mock ile fail/success log assert; macOS’ta gerçek timeout + log kontrolü; recovery path’te log doğrulama.

Dosya referansları: presence_lock.py (trigger_macos_screen_lock, lock_cb wrapper, _append_log), interactive_cli.py (presence_menu _lock_cb, _recovery_lock_cb, lock_menu kapat path).
