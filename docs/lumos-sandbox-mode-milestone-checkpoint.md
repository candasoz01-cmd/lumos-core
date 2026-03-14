# Sandbox_mode tek kaynak — milestone teknik checkpoint

Mevcut yeşil baz üstünde, sandbox_mode tek kaynak yaklaşımının bu milestone sonunda ulaştığı kapsamın kısa teknik özeti. Kod/test değişikliği yok; sadece checkpoint.

**Amaç:** TaskStore + presence + notes + aliases + identity/keystore hattına kadar yayılan sandbox_mode tek kaynak yaklaşımının seviyesini tek yerde netleştirmek. Sonraki aşamada rastgele genişleme yerine mevcut milestone kapsamı ve sınırları sabitlensin.

**Referans:** `lumos-guard-sink-phase2-checkpoint.md`, `src/core/workspace_contract.py`, `src/main.py` (satır 928: `sandbox_mode = False` tek kaynak).

---

## 1. Dokunduğum dosya

- Bu checkpoint için **hiçbir kod/test dosyasına dokunulmadı**. Sadece bu doküman eklendi.

---

## 2. Milestone checkpoint başlıkları

- **Tek kaynak:** `main()` içinde `sandbox_mode = False` (satır 928); şimdilik sabit; ileride env/CLI’dan okunabilir.
- **İletim:** Tüm sink’lere ve store’lara bu değişken/argüman iletilir; dağıık `True`/`False` sabiti yok.
- **Guard:** `workspace_contract.allow_write_to_core(live_base_dir, target_path, is_sandbox_mode)`. `is_sandbox_mode=True` iken canlı çekirdek path’e yazma → `CoreWriteForbidden`.
- **Sink’ler:** Path + yazma `workspace_contract`’ta; domain modülleri veriyi hazırlayıp sink’e verir; her sink yazmadan önce guard kullanır.

---

## 3. Mevcut sandbox_mode tüketicileri

| Tüketici | Bağlanan hat | Guard/sink hizalaması |
|----------|--------------|------------------------|
| **TaskStore** | `TaskStore(tasks_dir, sandbox_mode=...)` → `save_task_store_json(..., sandbox_mode=..., live_base_dir=...)` | `save_task_store_json` içinde `sandbox_mode=True` iken `allow_write_to_core`; path `tasks/tasks.json`. |
| **Presence (presence_lock)** | `save_presence_cfg`, `start_presence_lock`, `stop_presence_lock`, `log_event` → `save_presence_cfg_json(..., is_sandbox_mode=...)`, `append_log_line(..., is_sandbox_mode=...)` | `save_presence_cfg_json` ve `append_log_line` içinde `allow_write_to_core`; path’ler `presence.json`, `logs/log.txt`. |
| **Notes** | `SecureNotesStore(base_dir, is_sandbox_mode=...)` → `save_notes_enc_json(..., is_sandbox_mode=...)` | Sink’te `allow_write_to_core`; path `notes.enc.json`. |
| **Aliases** | `save_aliases(base_dir, data, is_sandbox_mode=...)` → `save_aliases_json(..., is_sandbox_mode=...)` | Sink’te `allow_write_to_core`; path `aliases.json`. |
| **Identity** | `DeviceIdentity(base_dir, is_sandbox_mode=...)` → `save_identity_json(..., is_sandbox_mode=...)` | Sink’te `allow_write_to_core`; path `identity.json`. Init’te canlı çekirdek path’e yazma sandbox’ta red. |
| **Keystore** | `FileKeyStore(base_dir, is_sandbox_mode=...)` → `save_keystore_json(..., is_sandbox_mode=...)` | Sink’te `allow_write_to_core`; path `keystore.json`. Init’te canlı çekirdek path’e yazma sandbox’ta red. |
| **Log (append)** | `append_log_line(base_dir, line, is_sandbox_mode=...)` | Sink’te `allow_write_to_core`; path `logs/log.txt`. Presence ve CoreState üzerinden log_event ile de aynı sink. |
| **CoreState** | `CoreState(..., sandbox_mode=...)` → `log_event` → `pl.log_event(..., is_sandbox_mode=self._sandbox_mode)` | Log satırı presence_lock → `append_log_line`; guard yukarıdaki log sink’inde. |
| **run_startup_self_check** | `run_startup_self_check(..., sandbox_mode=sandbox_mode)` | Parametre iletimi; doğrudan disk yazımı yok, self-check okuma/kontrol. |
| **run_menu / alt akışlar** | `run_menu(..., sandbox_mode=sandbox_mode)`; menü içi TaskStore, aliases, notes, presence, identity/keystore çağrılarına `sandbox_mode` iletilir | Tüm yazım bu tüketiciler üzerinden sink’lere gider. |

---

## 4. Bilerek dokunulmayan alanlar

- **config.json yazma:** `config_file_path` ve `CORE_STATE_PATH_NAMES` içinde `config.json` var; fakat **merkezi bir `save_config_json` sink’i yok**. Config yazma henüz workspace_contract sink/guard zincirine alınmadı.
- **Log rotasyonu / logs/ altı diğer dosyalar:** Append tek dosya (`logs/log.txt`) sink’te; rotasyon veya ek log dosyaları bu milestone kapsamı dışı.
- **Trash yazma:** Trash’e taşıma yazan kodlar sandbox_mode ile merkezi sink’e alınmadı; `is_allowed_trash_path` ve `may_perform_permanent_delete` sözleşmede sabit.
- **sandbox_mode kaynağı:** Değer hâlâ sabit `False`; env/CLI’dan okuma veya UI’dan açma bu milestone’da yok.
- **Runtime sandbox hedefi:** Sandbox açıkken “nereye yazılır” (kopya/sandbox dizini) bu checkpoint’te tanımlı değil; sadece “canlı çekirdek path’e yazma reddedilir” guard’ı var.

---

## 5. Phase 3 için sıradaki teknik adaylar (kısa)

1. **config.json merkezi sink:** `save_config_json(base_dir, data, is_sandbox_mode=False)` + `allow_write_to_core`; config yazan yerleri bu sink’e bağlamak.
2. **sandbox_mode kaynağı:** `main()`’de env (örn. `LUMOS_SANDBOX`) veya CLI argümanından okuma; tek kaynak kalır, değer değişir.
3. **Trash/silme akışları:** Trash’e yazan adımların path + guard ile merkezi sözleşmeye alınması (lumos-guard-sink-phase2-checkpoint’teki “orta/yüksek risk” ayrımına göre).
4. **Sandbox hedef dizini:** Sandbox açıkken yazılacak kopya/sandbox base path’in tanımı ve sink’lerin (isteğe bağlı) oraya yazma seçeneği; mevcut guard korunur.

---

## 6. Yeni commit

- **Kod/test değişikliği yok** → davranış değişmedi; CI aynı kalır.
- **Yeni commit:** Sadece bu checkpoint dokümanını repoya eklemek istiyorsan **evet** (isteğe bağlı). Dokümanı eklemezsen commit gerekmez.
