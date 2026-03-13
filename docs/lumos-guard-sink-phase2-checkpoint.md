# Phase 2 — Merkezi sink guard checkpoint özeti ve genişletme stratejisi

Mevcut yeşil baz üstünde merkezi sink guard pattern’ine alınan writer hatlarının özeti ve sonraki genişletme planı. Kod/test değişikliği yok; sadece teknik docs özeti.

**Referans:** `lumos-guard-sink-phase2-pilot.md`, `lumos-guard-zincir-durum.md`, `lumos-sozlesme-uygulama-plani.md`, `src/core/workspace_contract.py`.

---

## 1. Phase 2 checkpoint — sink özetleri

### 1.1 Aliases sink

| | |
|--|--|
| **Eski yazma noktası** | `aliases.py` içinde `save_aliases` → `base_dir / "aliases.json"` doğrudan `write_text`. Path lokal; guard zincirine bağlı değildi. |
| **Yeni merkezi sink/helper** | `workspace_contract`: `alias_file_path(base_dir)`, `save_aliases_json(base_dir, aliases, is_sandbox_mode=False)`. `aliases.save_aliases` sadece bu sink’i çağırıyor. |
| **Guard hizalaması** | `CORE_STATE_PATH_NAMES` (aliases.json); `allow_write_to_core` yazmadan önce; `is_sandbox_mode=True` → canlı çekirdek path’e yazma `CoreWriteForbidden`. |

### 1.2 Notes / SecureNotesStore sink

| | |
|--|--|
| **Eski yazma noktası** | `secure_store.py` `SecureNotesStore.save` → `self.base / filename` (notes.enc.json) doğrudan yazıyordu; path/store lokal. |
| **Yeni merkezi sink/helper** | `workspace_contract`: `notes_file_path(base_dir)`, `save_notes_enc_json(base_dir, data, is_sandbox_mode=False)`. Store şifreleme hazırlayıp sink’e veriyor; diske yazma sink’te. |
| **Guard hizalaması** | `notes.enc.json` çekirdek listede; `save_notes_enc_json` içinde `allow_write_to_core`; sandbox açıldığında aynı guard. |

### 1.3 TaskStore persistence sink

| | |
|--|--|
| **Eski yazma noktası** | `engine.py` `TaskStore._save` → `self.base_dir / "tasks.json"` doğrudan `write_text`; path/yazma TaskStore içinde lokal. |
| **Yeni merkezi sink/helper** | `workspace_contract`: `save_task_store_json(tasks_dir, data, sandbox_mode=..., live_base_dir=...)`. Path `tasks_dir / "tasks.json"`. `TaskStore._save` JSON hazırlayıp bu sink’i çağırıyor. |
| **Guard hizalaması** | `tasks/tasks.json` çekirdek (is_core_state_path özel case). `sandbox_mode=True` iken `allow_write_to_core`; `False` iken guard devre dışı. Kalıcı silme: `may_perform_permanent_delete(user_initiated)`. |

### 1.4 Presence config sink

| | |
|--|--|
| **Eski yazma noktası** | `presence_lock.py` içinde presence ayarı yazımı `base_dir / "presence.json"` (lokal path). |
| **Yeni merkezi sink/helper** | `workspace_contract`: `presence_cfg_path(base_dir)`, `save_presence_cfg_json(base_dir, data, is_sandbox_mode=False)`. `save_presence_cfg` → `save_presence_cfg_json(base_dir, asdict(cfg))`. |
| **Guard hizalaması** | `presence.json` `CORE_STATE_PATH_NAMES` içinde; `allow_write_to_core` ile aynı sandbox guard. |

### 1.5 Identity / keystore sink

| | |
|--|--|
| **Eski yazma noktası** | `identity.py` `DeviceIdentity.init` → `paths.identity_file` (base_dir / "identity.json") doğrudan yazıyordu. `keystore.py` `FileKeyStore.init` → `paths.keystore_file` (base_dir / "keystore.json") doğrudan yazıyordu. |
| **Yeni merkezi sink/helper** | `workspace_contract`: `identity_file_path(base_dir)`, `save_identity_json(base_dir, data, is_sandbox_mode=False)`; `keystore_file_path(base_dir)`, `save_keystore_json(base_dir, data, is_sandbox_mode=False)`. Identity/keystore modülleri veriyi hazırlayıp ilgili sink’i çağırıyor. |
| **Guard hizalaması** | `identity.json`, `keystore.json` çekirdek listede; her iki sink de `allow_write_to_core` ile hizalı; sandbox açıldığında canlı çekirdek path’e yazma reddedilir. |

---

## 2. Ortak pattern özeti

- **Merkezi sink mantığı (`workspace_contract`)**  
  Çekirdek state path’leri tek listede (`CORE_STATE_PATH_NAMES`). Her çekirdek dosya için: (1) tek path helper (`*_file_path(base_dir)`), (2) tek yazma sink (`save_*_json(...)`). Domain modülleri sadece veriyi hazırlar; path ve yazma kararı workspace_contract’ta.

- **`allow_write_to_core` / sandbox guard ilişkisi**  
  “Bu path çekirdek mi?” → `is_core_state_path(base_dir, candidate_path)` (aynı liste). “Yazabilir mi?” → `allow_write_to_core(live_base_dir, target_path, is_sandbox_mode)`: sandbox kapalıyken her zaman izin; sandbox açıkken canlı çekirdek path’e yazma → red (`CoreWriteForbidden`). Tüm sink’ler yazmadan önce bu guard’ı kullanıyor.

- **Neden dar pilot sonra checkpoint**  
  Önce az sayıda hat (aliases, notes, TaskStore) ile path + guard kombinasyonu ve `workspace_contract`–domain hizalaması pratikte doğrulandı; davranış değişmeden şablon oturdu. Sonra presence, identity, keystore aynı şablona alındı. Böylece tek tek pilotlar yerine risk seviyesine göre gruplanmış genişletme planına geçilebilir.

---

## 3. Genişletme stratejisi

### 3.1 Aynı pattern ile hızlı alınabilecek — düşük risk

- **Ek küçük JSON state dosyaları**  
  `.lumos` altında, çekirdek omurga dışı yardımcı JSON (hafif metadata). Path’leri `CORE_STATE_PATH_NAMES` / path helper + sink ile workspace_contract’a alınabilir; format basit, geri alma kolay.

- **Config / logs yazıcıları (sadece path/sink merkezileştirme)**  
  Config veya log dosyası yazan kodlar aynı path + `save_*` sink şablonuna bağlanabilir; veri formatı ve rotasyon mevcut kalmak koşuluyla sadece yazma noktası merkezileşir.

### 3.2 Orta risk — yönetilebilir

- **Config / logs tam entegrasyonu**  
  Konfig ve log path/sink mantığının tam merkezileşmesi ve sandbox guard’a bağlanması. Davranış (özellikle log rotasyonu ve mevcut dosya yapısı) değişebileceği için pilotlar oturduktan sonra, test/CI ile adım adım.

- **CLI/main’den sandbox_mode’un sink’lere iletimi**  
  `sandbox_mode` bayrağının tek kaynaktan (CLI/main) tüm yazıcı katmanına iletilmesi. Pattern belli; etki alanı geniş olduğu için ayrı küçük PR’larla.

### 3.3 Ayrı tasarım — yüksek risk

- **Kalıcı silme / trash dışı taşıma**  
  Kalıcı silme sözleşmesi (`may_perform_permanent_delete`, sabit trash path, `.lumos/trash/` dışına taşmama) ile bağlı tüm yazma/silme akışları. Sadece path/sandbox değil, kalıcı silme politikasının sıkı uygulanması da gerekir; mevcut pilotlar uzun süre yeşil doğrulandıktan sonra ayrı faz.

- **Runtime sandbox modunun yaygınlaştırılması**  
  CLI/UI’den gelen sandbox modunun tüm yazıcılarda davranış değiştirmesi; kullanıcı deneyimi ve hata yüzeyi doğrudan etkilenir. Sink merkezileştirme tam oturduktan sonra ayrı faz.

- **Keystore/identity ek güvenlik katmanları**  
  Kimlik/anahtar erişimini doğrudan etkileyebilecek ek guard veya kullanım kısıtları; mevcut sink guard’ı korunarak ayrı tasarım ve ince ayar gerekir.

---

*Bu belge mevcut guard zinciri ve pilot dokümanlarla çelişmez; tekrarlı metin kısaltılmıştır.*
