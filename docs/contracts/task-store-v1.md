# Görev deposu sözleşmesi — v1 (TD-01)

| Alan | Değer |
| --- | --- |
| Durum | KOD — bu PR ile |
| Borç kaydı | [TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md) TD-01 |
| Kod karşılığı | `src/core/task_store_mirror.py` + `TaskStore._mirror_to_canonical` |
| Faz | FAZ-1 (Görev sistemi) |

## Karar

1. **Kullanıcı-görünür tek görev kaynağı canonical panel dokümanıdır:**
   `<base>/tasks.json` — `{"v": 1, "tasks": [...], "events": [...]}`.
   Panel CRUD (panel_tasks_server) bu dokümanın sahibi olmaya devam eder.
2. **TaskEngine deposu** (`<base>/tasks/tasks.json`) **çalıştırma
   günlüğüdür**, kullanıcı görev listesi değildir; kullanıcı yüzeyleri onu
   doğrudan okumaz.
3. **Ayna kuralı:** her engine görevi canonical listeye `engine-<task_id>`
   kimlikli tek satır yansıtır (`source: "engine"`): create/update →
   upsert; `tamamlandi` → `done`, diğer tüm durumlar → `active`;
   soft_delete/delete/archive → satır kaldırılır (panel delete ile hizalı —
   çöp kaydını engine zaten panel formatında yazıyor).
4. **Sandbox çalıştırmaları canonical'a yansımaz.**
5. **Göç:** `migrate_engine_tasks(engine_file, base)` mevcut engine
   görevlerini tek seferde yansıtır; idempotenttir.

## Geçiş köprüsü (compatibility bridge, GEÇİCİ)

Big-bang göç yerine uyumlu geçiş: canonical format tek olsa da okuma tarafı
geçiş süresince iki şemayı da anlar.

- **Yazma:** yalnız canonical format üretilir (`{id, title, status:
  active|done}`) — hem panel CRUD hem `task_store_mirror`.
- **Okuma:** `panel_bridge_state._read_tasks_payload` geçiş süresince eski
  TaskEngine satırlarını da okur ve normalize eder: `task_id` → `engine-<id>`,
  Türkçe statü → `active|done` (`tamamlandi` → `done`, diğerleri → `active`).
- **Bilinmeyen statü sessizce kabul edilmez:** `active`'e düşürülür ve
  `warnings`'e yazılır (veri hataları görünür kalsın).
- **Bozuk/kimliksiz satır ezilmez:** atlanır ve `skipped_rows`'a raporlanır.
- **Tekilleştirme:** aynı `id` için son-yazılan kazanır — göç anında eski
  satır + aynalı canonical satır tek kayda iner.

**TODO (göç sonrası):** Eski-format okuma desteği kalıcı değildir. Tüm canlı
`tasks.json` dosyaları canonical'a geçtiğinde (`migrate_engine_tasks` +
doğrulama), `_read_tasks_payload` içindeki legacy dalları ve
`_LEGACY_*_STATUSES` kaldırılır. Bu, ayrı bir teknik borç kaydı olarak
izlenir: **TD-01-followup — legacy görev formatı okuma desteğinin kaldırılması**
(TECHNICAL_DEBT.md'ye ayrı, kapsamı dar bir PR ile eklenecek).

## Bilinen v1 sınırları (dürüst)

- Ayna best-effort'tur: canonical doküman bozuksa üstüne yazmaz ve engine
  akışını durdurmaz; bozukluk panel_bridge_state sağlık sinyalinde görünür.
- Panel server ile engine süreçleri arasında dosya kilidi yoktur; eşzamanlı
  yazma yarışı teorik olarak mümkündür (tek kullanıcılı yerel kurulumda
  düşük risk; TD kaydına not düşüldü).
- Ters yön (panel satırının engine'e taşınması) kapsam dışıdır — panel
  görevleri çalıştırılabilir iş değildir.
