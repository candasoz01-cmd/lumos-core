# Phase 3 — Merkezi sink + guard omurga teknik checkpoint

Mevcut yeşil baz üstünde, Phase 3 sonunda merkezi sink + guard omurgasının ulaştığı kapsamın kısa teknik özeti. Kod/test değişikliği yok; sadece checkpoint.

**Amaç:** TaskStore + presence + notes + aliases + identity/keystore + config.json + trash path/sink hattına kadar gelen merkezi sink + guard yapısının seviyesini tek yerde netleştirmek. Bundan sonraki genişlemelerde rastgele ilerlemek yerine mevcut kapsam ve sınırlar sabitlensin.

**Referans:** `lumos-sandbox-mode-milestone-checkpoint.md`, `lumos-guard-sink-phase2-checkpoint.md`, `src/core/workspace_contract.py`, `docs/lumos-guard-sandbox-kopya-siniri.md`.

---

## 1. Dokunduğum dosya

- Bu checkpoint için **hiçbir kod/test dosyasına dokunulmadı**. Sadece bu doküman eklendi: `docs/lumos-phase3-sink-guard-checkpoint.md`.

---

## 2. Checkpoint başlıkları

- **Çekirdek state tek listesi:** `workspace_contract.CORE_STATE_PATH_NAMES` — tasks.json, config, config.json, logs, trash, aliases.json, notes.enc.json, presence.json, identity.json, keystore.json.
- **Path tek kaynağı:** Her çekirdek dosya/dizin için tek helper: `trash_path`, `alias_file_path`, `notes_file_path`, `presence_cfg_path`, `identity_file_path`, `keystore_file_path`, `config_file_path`, `logs_dir_path`, `logs_file_path`; TaskStore path: `tasks_dir / "tasks.json"`.
- **Merkezi sink’ler:** Tüm çekirdek yazımlar workspace_contract üzerinden; domain veriyi hazırlar, sink path + guard uygular.
- **Guard:** `allow_write_to_core(live_base_dir, target_path, is_sandbox_mode)`. `is_sandbox_mode=True` iken canlı çekirdek path’e yazma → `CoreWriteForbidden`. Çekirdek tanımı: `is_core_state_path(base_dir, candidate_path)` (CORE_STATE_PATH_NAMES + tasks/tasks.json + config/logs/trash altları).
- **Trash sözleşmesi:** Tek hedef `trash_path(base_dir)`; `is_allowed_trash_path`; kalıcı silme `may_perform_permanent_delete(user_initiated)`.

---

## 3. Merkezi sink/guard omurgasına bağlı alanlar

| Alan | Helper / path | Sink | Guard hizalaması |
|------|----------------|------|-------------------|
| **TaskStore** | `tasks_dir / "tasks.json"` | `save_task_store_json(tasks_dir, data, sandbox_mode=..., live_base_dir=...)` | `sandbox_mode=True` iken `allow_write_to_core`; path çekirdek (tasks/tasks.json). |
| **Presence** | `presence_cfg_path(base_dir)` | `save_presence_cfg_json(base_dir, data, is_sandbox_mode=...)` | Sink içinde `allow_write_to_core`; path `presence.json`. |
| **Log (append)** | `logs_file_path(base_dir)` | `append_log_line(base_dir, line, is_sandbox_mode=...)` | Sink içinde `allow_write_to_core`; path `logs/log.txt`. Presence/CoreState log_event → bu sink. |
| **Notes** | `notes_file_path(base_dir)` | `save_notes_enc_json(base_dir, data, is_sandbox_mode=...)` | Sink içinde `allow_write_to_core`; path `notes.enc.json`. |
| **Aliases** | `alias_file_path(base_dir)` | `save_aliases_json(base_dir, aliases, is_sandbox_mode=...)` | Sink içinde `allow_write_to_core`; path `aliases.json`. |
| **Identity** | `identity_file_path(base_dir)` | `save_identity_json(base_dir, data, is_sandbox_mode=...)` | Sink içinde `allow_write_to_core`; path `identity.json`. |
| **Keystore** | `keystore_file_path(base_dir)` | `save_keystore_json(base_dir, data, is_sandbox_mode=...)` | Sink içinde `allow_write_to_core`; path `keystore.json`. |
| **Config** | `config_file_path(base_dir)` | `save_config_json(base_dir, data, is_sandbox_mode=...)` | Sink içinde `allow_write_to_core`; path `config.json`. Config modülü bu sink’e delegasyon. |
| **Trash path/sink** | `trash_path(base_dir)` | `ensure_trash_dir(base_dir, is_sandbox_mode=...)`, `move_to_trash(base_dir, source_path, is_sandbox_mode=...)` | Hedef tek: `trash_path`; `is_allowed_trash_path` + `allow_write_to_core`. `ensure_trash_dir` main’den çağrılıyor; `move_to_trash` sink hazır, uygulama akışında henüz kullanılmıyor. |

---

## 4. Bilerek dokunulmayan alanlar

- **Log rotasyonu / logs/ altı diğer dosyalar:** Sadece `logs/log.txt` append sink’te; rotasyon veya ek log dosyaları bu kapsam dışı.
- **move_to_trash çağrı noktaları:** Sink ve guard hazır; “silinen öğeyi trash’e taşı” akışları henüz bu sink’i kullanacak şekilde bağlanmadı (ileride bağlanabilir).
- **sandbox_mode kaynağı:** Hâlâ sabit `False` (main); env/CLI/UI bu checkpoint dışı.
- **Sandbox hedef dizini:** Sandbox açıkken yazılacak kopya/sandbox base tanımsız; sadece “canlı çekirdek path’e yazma red” guard’ı var.
- **Kalıcı silme / çekirdek inviolable:** `may_perform_permanent_delete`, çekirdek sabitler, açık onay guard’ları aynen; bu doküman sadece sink/guard omurga kapsamını tarif ediyor.

---

## 5. Sonraki teknik adaylar (kısa)

1. **sandbox_mode kaynağı:** main’de env (örn. `LUMOS_SANDBOX`) veya CLI’dan okuma; tek kaynak kalır.
2. **Sandbox hedef dizini:** Sandbox açıkken yazılacak base path sözleşmesi ve (isteğe bağlı) sink’lerin oraya yazma seçeneği.
3. **move_to_trash’ı akışlara bağlama:** Silme/taşıma akışlarında merkezi `move_to_trash` kullanımı.
4. **Log rotasyonu (opsiyonel):** logs/ altı diğer dosyaların path/sink/guard ile uyumu; düşük öncelik.

---

## 6. Yeni commit

- **Kod/test değişikliği yok** → davranış değişmedi; CI aynı kalır.
- **Yeni commit:** Sadece bu checkpoint dokümanını repoya eklemek istiyorsan **evet** (isteğe bağlı). Dokümanı eklemezsen commit gerekmez.
