## Phase 2 — sink merkezileştirme pilot özeti

Bu not, mevcut yeşil baz üstünde yapılan üç dar pilotu özetler: `aliases`, `notes/secure_store` ve `TaskStore` için yazma noktalarının ortak bir sink/guard katmanında toplanması. Kod davranışı ve test beklentileri değiştirilmeden, sadece yazma yolları `workspace_contract` içindeki merkezi helper’lara yönlendirilmiştir.

---

## 1. Aliases sink pilotu

- **Eski yazma noktası (konsept olarak)**  
  - `src/security/aliases.py` içindeki `save_aliases` fonksiyonu, `base_dir / "aliases.json"` dosyasına doğrudan `write_text` ile yazıyordu.  
  - Sandbox / çekirdek guard zincirine bağlı değildi; path sabiti lokal mantıkla belirleniyordu.

- **Yeni merkezi sink/helper**  
  - `src/core/workspace_contract.py` içindeki:  
    - `alias_file_path(base_dir)` → `aliases.json` için tek sözleşmeli path, `CORE_STATE_PATH_NAMES` ile hizalı.  
    - `save_aliases_json(base_dir, aliases, *, is_sandbox_mode: bool = False)` → JSON içeriğini alan, gerçek diske yazma side-effect’ini yapan merkezi sink.
  - `src/security/aliases.py` artık `save_aliases` içinde sadece `save_aliases_json(base_dir, aliases)` çağırıyor; varsayılan `is_sandbox_mode=False` ile mevcut davranış korunuyor.

- **Hangi guard’larla hizalı?**  
  - `CORE_STATE_PATH_NAMES` içinde `aliases.json` → çekirdek state olarak işaretli.  
  - `is_core_state_path` ve `allow_write_to_core(live_base_dir, target_path, is_sandbox_mode)` ile aynı liste kullanılıyor.  
  - `save_aliases_json` yazmadan önce `allow_write_to_core(...)` çağırıyor; `is_sandbox_mode=True` olduğunda canlı çekirdek `aliases.json` path’ine yazma girişimi `CoreWriteForbidden` ile reddediliyor.  
  - Varsayılan `is_sandbox_mode=False` olduğu için bu pilot, sandbox açılmadığı sürece sadece gelecekteki guard için altyapı sağlıyor; mevcut davranış/testler değişmiyor.

---

## 2. Notes / SecureNotesStore sink pilotu

- **Eski yazma noktası (konsept olarak)**  
  - `src/memory/secure_store.py` içindeki `SecureNotesStore.save` metodu, şifrelenmiş notları `self.base / filename` (varsayılan `notes.enc.json`) dosyasına doğrudan yazıyordu.  
  - Path ve yazma mantığı store içinde lokal olarak tanımlıydı; sandbox / çekirdek guard zinciriyle bağlantılı değildi.

- **Yeni merkezi sink/helper**  
  - `src/core/workspace_contract.py` içindeki:  
    - `notes_file_path(base_dir)` → `notes.enc.json` için tek sözleşmeli path.  
    - `save_notes_enc_json(base_dir, data, *, is_sandbox_mode: bool = False)` → şifreli JSON gövdesini alan yazma sink’i.
  - `SecureNotesStore.save` artık:  
    - AES-GCM ile şifrelenmiş payload’ı (`data` dict’i) hazırlıyor.  
    - Dosyaya yazmak yerine `save_notes_enc_json(self.base, data)` çağırıyor.  
  - Böylece `SecureNotesStore` içindeki kriptografi ve format mantığı yerinde kalırken, diske yazma adımı ortak sink’e taşınmış oluyor.

- **Hangi guard’larla hizalı?**  
  - `notes.enc.json`, `CORE_STATE_PATH_NAMES` içinde çekirdek state olarak listeleniyor.  
  - `save_notes_enc_json` yazmadan önce `allow_write_to_core(live_base_dir=base_dir, target_path=notes_file_path(base_dir), is_sandbox_mode=...)` ile sandbox/çekirdek guard’ına bağlanıyor.  
  - `is_sandbox_mode` parametresi yine varsayılan `False`; böylece mevcut çalışma şekli bozulmadan, sandbox açıldığında aynı guard mantığı otomatik devreye girecek.

---

## 3. TaskStore persistence sink pilotu

- **Eski yazma noktası (konsept olarak)**  
  - `src/task_engine/engine.py` içindeki `TaskStore._save` metodu, `self.base_dir / "tasks.json"` dosyasına doğrudan `write_text` ile yazıyordu.  
  - Path seçimi ve yazma mantığı TaskStore içinde lokal; sandbox / çekirdek guard zincirinden bağımsızdı.

- **Yeni merkezi sink/helper**  
  - `src/core/workspace_contract.py` içindeki `save_task_store_json(tasks_dir, data, *, sandbox_mode: bool, live_base_dir: Path | str | None = None)` fonksiyonu:  
    - Path’i `tasks_dir / "tasks.json"` olarak belirler (TaskStore ile hizalı).  
    - JSON’ı diske yazmadan önce (sadece `sandbox_mode=True` iken) `allow_write_to_core` ile guard uygular.  
  - `TaskStore._save` artık:  
    - `_tasks` listesini tekil `task_id` ile normalize edip JSON yapısını hazırlar.  
    - Dosyaya doğrudan yazmak yerine `save_task_store_json(tasks_dir=self.base_dir, data=data, sandbox_mode=self.sandbox_mode, live_base_dir=self._live_base_dir)` çağırır.

- **Hangi guard’larla hizalı?**  
  - `CORE_STATE_PATH_NAMES` + `is_core_state_path` içinde `tasks/tasks.json` özel-casesiyle çekirdek state olarak işaretli.  
  - `save_task_store_json` içinde:  
    - `sandbox_mode=False` → guard devre dışı, mevcut davranış.  
    - `sandbox_mode=True` → `allow_write_to_core(live_base_dir or tasks_dir.parent, target_path, is_sandbox_mode=True)` ile canlı `.lumos` tabanındaki çekirdek state path’ine yazma reddediliyor (`CoreWriteForbidden`).  
  - `TaskStore.delete` için kalıcı silme tarafında da `may_perform_permanent_delete(user_initiated)` kullanılarak, kalıcı silme sözleşmesiyle hizalı bir guard zinciri kurulmuş durumda (sadece kullanıcı kaynaklı komut ile silme).

---

## 4. Ortak sink pattern’i (Phase 2 pilot seviyesi)

- **Merkezi path tanımı ve sink’ler `workspace_contract` içinde**  
  - Çekirdek state dosyaları (`tasks.json`, `aliases.json`, `notes.enc.json`, `config/`, `logs/`, `trash/` vb.) için path tanımları ve yazma helper’ları tek dosyada tutuluyor.  
  - Alan-spesifik modüller (`aliases.py`, `secure_store.py`, `TaskStore`) artık sadece kendi domain verisini hazırlayıp, path/guard kararını `workspace_contract` içindeki sink fonksiyonlarına bırakıyor.

- **`allow_write_to_core` / sandbox guard ilişkisi**  
  - `CORE_STATE_PATH_NAMES` + `is_core_state_path(base_dir, candidate_path)` → “çekirdek state mi?” sorusunun tek yanıt kaynağı.  
  - `allow_write_to_core(live_base_dir, target_path, is_sandbox_mode)` → sandbox açıldığında canlı çekirdek state path’ine yazmayı reddeden merkezi guard.  
  - Aliases, notes ve TaskStore pilotları, yazma öncesi bu guard’ı çağıran küçük sink fonksiyonları (`save_aliases_json`, `save_notes_enc_json`, `save_task_store_json`) üzerinden aynı zincire bağlanıyor.  
  - **Kritik nokta:** Tüm bu helper’larda `is_sandbox_mode` / `sandbox_mode` bayrakları varsayılan olarak mevcut davranışı koruyacak şekilde (`False`) ayarlı; böylece Phase 2 pilotu, runtime davranışını değiştirmeden sadece guard zincirini merkezileştiriyor.

- **Neden dar pilot yaklaşımı?**  
  - Yalnızca üç sink (aliases, notes, TaskStore) seçilerek:  
    - Path/sandbox guard kombinasyonunun gerçek kodda nasıl görüneceği netleştirildi.  
    - `workspace_contract` içindeki çekirdek state listesi ile alan-spesifik yazıcıların nasıl hizalanacağı pratikte test edildi.  
    - Diğer yazıcılar (presence config, keystore/identity, runtime logs vb.) üzerinde davranış değişikliğine gitmeden, ileride aynı pattern’in uygulanabileceği bir “şablon” oluşturuldu.  
  - Böylece hem guard zinciri hem de sandbox hazırlığı, minimum riskle ve rollback’i kolay olacak şekilde denenmiş oldu.

---

## 5. Sonraki mantıklı sink adayları (risk seviyesine göre)

### 5.1 En düşük riskli adaylar

- **Presence / ayar yazıcıları**  
  - Örn. `save_presence_cfg` benzeri basit JSON konfigürasyon yazıcıları.  
  - Data formatı yalın, hata durumunda kurtarma kolay; aynı `allow_write_to_core` guard zincirine bağlanmaları düşük riskli.

- **Ek küçük JSON state dosyaları**  
  - Çekirdek omurga dışında ama `.lumos` altındaki yardımcı JSON dosyaları (örn. hafif metadata).  
  - Path’leri `workspace_contract` içine alınarak, sandbox açıldığında core/sandbox ayrımının daha net korunması sağlanabilir.

### 5.2 Orta riskli adaylar

- **Keystore / identity persistence**  
  - Güvenlik açısından kritik ama yazma sıklığı ve hacmi sınırlı.  
  - `workspace_contract` içindeki çekirdek state listesine ve `allow_write_to_core` guard’ına bağlanmaları önemli; fakat yanlış yapılandırma doğrudan kimlik/anahtar erişimini etkileyebileceği için değişiklikler dikkatli planlanmalı.

- **Config / logs dizinleri için yazıcılar**  
  - Konfigürasyon ve log dosyalarının path/sink mantığı da merkezi hale getirilebilir.  
  - Davranış değişikliği riski (özellikle log rotasyonu ve mevcut dosya yapısı) orta düzeyde olduğu için, pilotlardaki pattern oturduktan sonra ele alınmaları uygun.

### 5.3 Yüksek riskli adaylar

- **Tasks / notes dışındaki diğer kalıcı silme veya taşımalar**  
  - Kalıcı silme sözleşmesi (`may_perform_permanent_delete`, sabit trash path, `.lumos/trash/` dışına taşmama) ile bağlantılı tüm yazma/silme akışları.  
  - Bu alanlarda sink merkezileştirme, sadece path/sandbox guard’ı değil, aynı zamanda kalıcı silme politikasının da sıkı uygulanmasını gerektirir; bu nedenle değişiklikler ancak mevcut pilotların CI/test düzeyinde uzun süre yeşil kaldığı doğrulandıktan sonra yapılmalı.

- **Yeni sandbox modlarının açılması (runtime seviyesinde)**  
  - CLI/UI’den gelen `sandbox_mode` bayraklarının yaygınlaştırılması ve tüm yazıcıların bu moda göre davranış değiştirmesi.  
  - Bu adım, kullanıcı deneyimini ve hata yüzeyini doğrudan etkilediği için, sink merkezileştirme pattern’i tamamen oturduktan sonra ayrı bir fazda ele alınmalıdır.

