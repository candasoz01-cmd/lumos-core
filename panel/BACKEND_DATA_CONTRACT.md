# Panel — Backend Data Contract (Kalıcı referans)

**Amaç:** Panel ekranlarının beklediği veri şekillerini tek yerde, ekran bazlı ve çelişkisiz tanımlamak. Backend tarafı bu sözleşmeye göre payload üretebilir; panel `js/contracts.js` CONTRACTS ve normalizer'lar bu şemayı uygular.

**Kapsam:** Sadece dokümantasyon. Tek kaynak şema: `panel/js/contracts.js` (CONTRACTS + applyContractFallbacks + normalize*). Backend-benzeri payload şekli: `panel/scripts/read_backend_state.py` çıktısı ve `panel/js/fixtures.js` mapper'ları ile uyumlu.

**Kural:** Zorunlu = normalizer'da varsayılan ile doldurulmayan; eksik kalırsa render bozulabilir. Opsiyonel = eksikse CONTRACTS varsayılanı veya normalizer varsayılanı uygulanır. Fallback = eksik/okunamaz durumda panelde gösterilen davranış.

---

## 1. Dashboard (Gösterge Paneli)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `metrics` | ✓ | | Dizi; boş ise []. Eleman: title, value, note; valueBadge (label, variant) opsiyonel. |
| `sections` | ✓ | | Dizi; en az 3 eleman (Son Olaylar, Uyarılar, Hızlı geçişler). sections[0]: events[]; sections[1]: warnings[]; sections[2]: links (boolean). Eksikse normalizer varsayılan başlık/dizi doldurur. |

**Backend payload (snake_case) karşılığı:** `sandbox_mode`, `writing_base_dir`, `guard_status`, `recent_events`, `warnings`. Mapper: `mapDashboardPayloadToPanelData`.

---

## 2. Sandbox (Korumalı Alan)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `metrics` | ✓ | | Dizi; 4 metrik (Kaynak, Sandbox Base, Yazım Yönü, Sözleşme Durumu). valueBadge opsiyonel. |
| `sections` | ✓ | | Dizi; { title, body } (HTML/metin). Eksikse CONTRACTS varsayılanı. |

**Backend payload karşılığı:** `sandbox_mode`, `sandbox_source`, `writing_base_dir`. Mapper: `mapSandboxPayloadToPanelData`.

---

## 3. Config (Yapılandırma)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `metrics` | ✓ | | Dizi; (Mevcut Yapılandırma Özeti, Yazım Durumu, Son Config Aktivitesi). valueBadge opsiyonel. |
| `sections` | ✓ | | Dizi; { title, body }. Eksikse CONTRACTS varsayılanı. |

**Backend payload karşılığı:** `config_snapshot` (profil, workspace_root, write_status, last_activity, last_activity_text). Mapper: `mapConfigPayloadToPanelData`. Config dosya içeriği okunmaz; sadece path/mtime.

---

## 4. Identity (Kimlik)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `metrics` | ✓ | | Dizi; (Kimlik hazır mı, Son Yazım, Hedef Kapsam, Guard Sonucu). |
| `sections` | ✓ | | Dizi; { title, body }. Eksikse CONTRACTS varsayılanı. |

**Backend payload karşılığı:** `identity_state`, `identity_last_write`, `identity_target_scope`, `identity_guard_result`. Kimlik içeriği panelde gösterilmez. Mapper: `mapIdentityPayloadToPanelData`.

---

## 5. Keystore (Anahtar Kasası)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `metrics` | ✓ | | Dizi; (Hazır mı, Şifreli Durum, Son Güncelleme, Yazım Kapsamı). |
| `sections` | ✓ | | Dizi; { title, body }. Eksikse CONTRACTS varsayılanı. |

**Backend payload karşılığı:** `keystore_ready`, `keystore_state`, `keystore_last_update`, `keystore_write_scope`. Anahtar/passphrase ifşası yok. Mapper: `mapKeystorePayloadToPanelData`.

---

## 6. Tasks (Görevler)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `filters` | ✓ | | TASK_FILTERS sabiti; normalizer eksikse sabiti kullanır. |
| `activeFilter` | ✓ | | "all" veya filtre id. |
| `listItems` | ✓ | | Dizi; eleman: id, title, status, updated, lastRun, guardResult, outputSummary. Boş olabilir. |
| `selectedId` | | ✓ | null. |
| `selectedTask` | | ✓ | null veya listItems içinden seçili öğe. |
| `listUpdated` | | ✓ | null; backend'den tasks.json mtime (ISO). Yoksa null. |
| `listUpdatedText` | | ✓ | null; gösterim metni (örn. "Son güncelleme: DD.MM.YYYY HH:MM"). |
| `tasksFilePath` | | ✓ | null; çözülmüş tasks.json yolu. |
| `taskCount` | | ✓ | 0; normalizer listItems.length veya backend değeri. |
| `tasksFileExists` | | ✓ | false; normalizer boolean. |
| `emptyListTitle` | ✓ | | "Bu filtrede görev yok"; normalizer doldurur. |
| `emptyListDesc` | ✓ | | EMPTY_DESC_DEFAULT; normalizer doldurur. |
| `detailTitle` | ✓ | | "Görev Detayı"; stub/mapper. |
| `runNoteTitle` | ✓ | | "Çalıştırma notu"; stub/mapper. |
| `runNoteBody` | ✓ | | Metin; stub/mapper. |

**Backend payload karşılığı:** `task_list`, `task_filter`, `selected_task_id`, `list_updated`, `list_updated_text`, `tasks_file_path`, `tasks_file_exists`, `task_count`. listItems elemanı: id, title, status, updated, last_run, guard_result, output_summary. Mapper: `mapTasksPayloadToPanelData`. Status panelde: aktif, bekleyen, tamamlandı, başarısız, engellenen (engine status → _TASK_STATUS_MAP).

---

## 7. Trash (Silinenler)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `summaryMetrics` | ✓ | | Dizi; (Çöp Konumu, Son Taşıma, Öğe Sayısı, Kapsam). |
| `listItems` | ✓ | | Dizi; eleman: id, name, originalPath, trashPath, movedAt, scope. Boş olabilir. |
| `selectedId` | | ✓ | null. |
| `selectedItem` | | ✓ | null veya listItems içinden seçili. |
| `detailTitle` | ✓ | | "Seçilen öğe"; stub/mapper. |
| `emptyListTitle` | ✓ | | "Çöp listesi boş"; stub/mapper. |
| `emptyListDesc` | ✓ | | EMPTY_DESC_DEFAULT ile metin; stub/mapper. |
| `emptyDetailPlaceholder` | ✓ | | "Listeden bir öğe seçin."; normalizer doldurur. |
| `trashItemCount` | | ✓ | 0; normalizer listItems.length veya backend. |
| `trashDirExists` | | ✓ | false; normalizer boolean. |
| `trashScopeFallbackNote` | | ✓ | ""; original_path/scope okunamadığında açıklama; backend gönderebilir. |

**Backend payload karşılığı:** `trash_location`, `trash_last_move`, `trash_items`, `trash_dir_exists`, `trash_item_count`, `trash_scope_fallback_note`. listItems elemanı: id, name, original_path, trash_path, moved_at, scope (FS'den meta yoksa "—"). Mapper: `mapTrashPayloadToPanelData`.

---

## 8. Logs (Kayıtlar)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `filters` | ✓ | | LOG_FILTERS sabiti; normalizer eksikse sabiti kullanır. |
| `activeFilter` | ✓ | | "all" veya filtre id. |
| `events` | ✓ | | Dizi; eleman: id, kind, text, ts. Boş olabilir. |
| `logFileUpdated` | | ✓ | null; backend'den log dosyası mtime (ISO). Dosya yoksa null. |
| `logUpdatedText` | | ✓ | null; gösterim metni. |
| `logLocation` | | ✓ | null; çözülmüş log dosyası yolu. |
| `sectionTitle` | ✓ | | "Kayıt listesi"; stub/mapper. |
| `logLineCount` | | ✓ | 0; normalizer events.length veya backend. |
| `logFileExists` | | ✓ | false; normalizer boolean. |

**Backend payload karşılığı:** `log_items`, `log_filter`, `log_file_updated`, `log_updated_text`, `log_location`, `log_file_exists`, `log_line_count`. events elemanı: id, kind, text, ts. Mapper: `mapLogsPayloadToPanelData`.

---

## 9. System (Sistem Durumu)

| Alan | Zorunlu | Opsiyonel | Fallback |
|------|---------|-----------|----------|
| `title` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `subtitle` | ✓ | | CONTRACTS: ""; stub/mapper doldurur. |
| `healthCards` | ✓ | | Dizi; eleman: title, status, note. Sıra: read_backend_state.py SYSTEM_HEALTH_KEYS ile uyumlu (workspace_contract, task_engine, sandbox_source, trash_contract, config_sink, identity_sink, keystore_sink, general). Eksik kartlar "—" / "Veri yok." ile doldurulur. Opsiyonel ek kartlar: system_paths varsa "Çalışma yolları"; system_summary varsa "Çekirdek dosya özeti". |

**Backend payload karşılığı:** `system_health` (key → { status, note }), isteğe bağlı `system_paths` (writing_base, trash, sandbox_base, config, logs, tasks), isteğe bağlı `system_summary` (config_exists, tasks_file_exists, task_count, trash_dir_exists, trash_item_count, log_file_exists, log_line_count). Mapper: `mapSystemPayloadToPanelData`. healthCards key sırası: contracts.js buildSystemStub / fixtures.js mapSystemPayloadToPanelData ile aynı.

---

## 10. Uyumluluk ve referanslar

- **Panel şema kaynağı:** `panel/js/contracts.js` — CONTRACTS, applyContractFallbacks, normalize*.
- **Backend çıktı şekli:** `panel/scripts/read_backend_state.py` — JSON root: dashboard, sandbox, config, identity, keystore, tasks, trash, logs, system (snake_case).
- **Panel şekline dönüşüm:** `panel/js/fixtures.js` — map*PayloadToPanelData; bridge çıktısı veya fixture aynı mapper ile contract şekline gelir.
- **Binding haritası:** Ekran → backend kaynak adayları ve risk: `BACKEND_BINDING_MAP.md`. Bu belge sadece **veri alanı sözleşmesi**; binding map entegrasyon planı için.

Bu tur: **sözleşme netleştirme**. Yeni veri alanı uydurulmadı; mevcut CONTRACTS ve Phase 2 read-only hattı referans alındı.
