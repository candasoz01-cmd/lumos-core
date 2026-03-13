# Sandbox_mode iletim zinciri — teknik audit

Mevcut kodda `sandbox_mode` / `is_sandbox_mode` değerinin main → menu/router → workspace sink → writer çağrıları boyunca nasıl taşındığının özeti. **Kod/test değişikliği yok;** sadece teknik audit.

---

## 1. Audit edilen dosyalar

| Katman | Dosya | İncelenen |
|--------|--------|------------|
| Giriş / router | `src/main.py` | sandbox_mode değişkeni, TaskStore/save_aliases/save_presence/notes/keystore/identity çağrıları |
| Domain → sink | `src/security/aliases.py` | save_aliases → save_aliases_json |
| Domain → sink | `src/security/presence_lock.py` | _append_log → append_log_line; save_presence_cfg → save_presence_cfg_json |
| Domain → sink | `src/memory/secure_store.py` | save → save_notes_enc_json |
| Domain → sink | `src/security/identity.py` | save → save_identity_json |
| Domain → sink | `src/security/keystore.py` | init → save_keystore_json |
| Domain → sink | `src/task_engine/engine.py` | TaskStore.__init__(sandbox_mode), _save → save_task_store_json |
| Merkezi sink | `src/core/workspace_contract.py` | append_log_line, save_*_json, save_task_store_json, allow_write_to_core |

---

## 2. Sandbox_mode iletim zinciri özeti

### 2.1 main.py

- **sandbox_mode değeri:** Yok. Main içinde `sandbox_mode` veya `is_sandbox_mode` adında değişken/argüman yok.
- **Taşıma:** Parametre olarak hiçbir yere geçirilmiyor.
- **Sonuç:** Tüm yazma akışları şu an “sandbox kapalı” gibi davranıyor; bunu açacak tek kaynak mevcut değil.

### 2.2 Menu / çağrı noktaları (main içinde)

| Çağrı | sandbox_mode nereden | Parametre? | Sabit? | Not |
|-------|----------------------|------------|--------|-----|
| `save_aliases(base_dir, aliases)` | — | Hayır | — | aliases modülü sink’e kendi geçirmiyor |
| `pl.save_presence_cfg(Path(base_dir), cfg)` | — | Hayır | — | presence_lock sink’e geçirmiyor |
| `TaskStore(tasks_dir)` | — | Hayır (verilmedi) | Evet (False) | Constructor default `sandbox_mode=False` |
| `TaskStore(Path(base_dir)/"tasks")` (self-check, self_test) | — | Hayır | Evet (False) | Aynı |
| SecureNotesStore / FileKeyStore / DeviceIdentity | — | Hayır | — | Store’lar sink’e is_sandbox_mode geçirmiyor |

Hiçbir menu/router çağrısı sandbox_mode taşımıyor.

### 2.3 Domain modülleri → workspace_contract

| Çağıran | Çağrı | is_sandbox_mode / sandbox_mode |
|---------|--------|---------------------------------|
| aliases.save_aliases | save_aliases_json(base_dir, aliases) | Verilmiyor → **varsayılan False** |
| presence_lock._append_log | append_log_line(base_dir, line) | Verilmiyor → **varsayılan False** |
| presence_lock.save_presence_cfg | save_presence_cfg_json(base_dir, asdict(cfg)) | Verilmiyor → **varsayılan False** |
| SecureNotesStore.save | save_notes_enc_json(self.base, data) | Verilmiyor → **varsayılan False** |
| DeviceIdentity (identity.py) | save_identity_json(self.paths.base_dir, data) | Verilmiyor → **varsayılan False** |
| FileKeyStore (keystore.py) | save_keystore_json(self.paths.base_dir, data) | Verilmiyor → **varsayılan False** |
| TaskStore._save | save_task_store_json(..., sandbox_mode=self.sandbox_mode, ...) | **Parametre ile taşınıyor** (TaskStore’dan) |

Sadece TaskStore, sink’e `sandbox_mode` parametresi ileten modül. Diğer tüm domain çağrıları sink’in varsayılanına (False) güveniyor.

### 2.4 workspace_contract helper’ları

| Helper | Parametre | Varsayılan | Guard |
|--------|-----------|------------|--------|
| append_log_line(base_dir, line, is_sandbox_mode=**) | is_sandbox_mode | **False** | allow_write_to_core(..., is_sandbox_mode) |
| save_aliases_json(..., is_sandbox_mode=**) | is_sandbox_mode | **False** | Aynı |
| save_notes_enc_json(..., is_sandbox_mode=**) | is_sandbox_mode | **False** | Aynı |
| save_presence_cfg_json(..., is_sandbox_mode=**) | is_sandbox_mode | **False** | Aynı |
| save_identity_json(..., is_sandbox_mode=**) | is_sandbox_mode | **False** | Aynı |
| save_keystore_json(..., is_sandbox_mode=**) | is_sandbox_mode | **False** | Aynı |
| save_task_store_json(..., sandbox_mode=**, ...) | sandbox_mode | **Yok (zorunlu)** | sandbox_mode=True iken allow_write_to_core |

Tüm save_* ve append_log_line API’si hazır: is_sandbox_mode/sandbox_mode alıyor ve guard’a iletiyor. Şu an tüm çağrılar ya varsayılan False kullanıyor ya da (sadece TaskStore) constructor’dan gelen False’u geçiriyor.

---

## 3. Riskli / kopuk noktalar

| Nokta | Risk | Açıklama |
|-------|------|----------|
| **main’de tek kaynak yok** | Yüksek | sandbox_mode main’de tanımlı değil; ileride “sandbox açık” demek için nereye yazılacağı belli değil. |
| **Domain katmanı parametre almıyor** | Orta | save_aliases, save_presence_cfg, SecureNotesStore.save, identity/keystore init — hiçbiri is_sandbox_mode parametresi almıyor; zincir main’den kopuk. |
| **TaskStore tek parametreli** | Orta | Sadece TaskStore sandbox_mode alıyor (constructor) ve sink’e iletiyor; main yine de bu argümanı vermiyor (hep default False). Tutarlı “sandbox açık” için main’in TaskStore(..., sandbox_mode=True) yapması gerekir; şu an böyle bir bayrak yok. |
| **İsim farkı** | Düşük | TaskStore/save_task_store_json `sandbox_mode` kullanıyor; diğer sink’ler `is_sandbox_mode`. Anlam aynı; ileride tek isim tercih edilebilir. |

Özet: Zincir workspace_contract’a kadar **tek taraflı**: sink’ler parametreyi kabul edip guard’a bağlıyor, ama main ve domain katmanı bu parametreyi **hiçbir yerden almıyor ve iletmiyor**. Tek “taşıma” TaskStore’un kendi constructor default’u (False); bu da main’den beslenmiyor.

---

## 4. Tek kaynak önerisi

- **Tek kaynak:** **main (giriş katmanı)**. Örn. `main()` içinde `sandbox_mode: bool = False` (veya env/CLI’dan okunacak tek değişken) tanımlanmalı; tüm menü/store/sink çağrılarına bu değer parametre olarak iletilmeli.
- **Yayılma:** main → (1) TaskStore(tasks_dir, sandbox_mode=sandbox_mode), (2) save_aliases(base_dir, aliases, is_sandbox_mode=sandbox_mode) gibi imzalar ve (3) presence/notes/identity/keystore/store’lara is_sandbox_mode geçecek şekilde çağrı zinciri. Domain modülleri (aliases, presence_lock, secure_store, identity, keystore) imzalarına is_sandbox_mode ekleyip workspace_contract sink’lerine iletmeli.
- **Mevcut davranış:** Varsayılan False bırakıldığı sürece davranış değişmez; guard sadece sandbox=True iken devreye girer.

---

## 5. Sonraki tek uygulanacak kod adımı

- **Gerçekten kod ihtiyacı var mı?** **Evet.** Audit sadece “şu an sandbox_mode nereden geliyor, nereye gidiyor” sorusunu yanıtladı. Tek kaynak ve tutarlı iletim için **kod değişikliği gerekir**: main’de tek değişken + bu değerin TaskStore ve (ileride) diğer sink çağrılarına parametre olarak iletilmesi.
- **Ne yapılmadı?** Bu dokümanda sadece audit yapıldı; hiçbir kod veya test değiştirilmedi.
- **Önerilen sonraki tek adım (kod):** **main’de `sandbox_mode` tek değişkeni tanımla ve sadece TaskStore’a ilet.**  
  - main’de örn. `sandbox_mode = False` (sabit veya ileride env’den).  
  - TaskStore oluşturulan üç yerde: `TaskStore(..., sandbox_mode=sandbox_mode)` geçir.  
  - Kapsam: sadece main + TaskStore çağrıları; diğer sink’ler (aliases, presence, notes, identity, keystore) bu adımda dokunulmadan bırakılabilir. Böylece “tek kaynak” main’e girer, en az bir sink (TaskStore) bu kaynağa bağlanır; diğer sink’ler sonraki küçük paketlerde aynı değişkene bağlanabilir.

---

*Mevcut yeşil davranışa dokunulmadı; audit sadece mevcut zinciri raporlar.*
