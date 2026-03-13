# Phase 2 — Log/config writer hattı checkpoint ve kalan alt paketler

Mevcut yeşil baz üstünde, orta riskli log/config writer hattında bu turda oturan parçaların kısa özeti ve kalan işlerin küçük alt paketlere bölünmüş planı. **Kod/test değişikliği yok;** sadece teknik özet ve parçalama.

**Referans:** `lumos-guard-sink-phase2-pilot.md`, `lumos-guard-zincir-durum.md`, `lumos-guard-sink-phase2-checkpoint.md`, `workspace_contract.py`, `presence_lock.py`, `config.py`, `main.py`.  
**İlgili commitler:** 3ac0773, 4b72c4a, e539847.

---

## 1. Bu turda oturan parçalar

### 1.1 Log/config path helper hizası (3ac0773)

- **Yapılan:** `workspace_contract` içinde log ve config path’leri merkezi helper’lara alındı.
- **Helper’lar:** `logs_dir_path(base_dir)`, `logs_file_path(base_dir)`, `config_file_path(base_dir)`. Hepsi `CORE_STATE_PATH_NAMES` ile hizalı; `config`, `config.json`, `logs` zaten listede.
- **Tüketiciler:** `config.load_config` zaten `config_file_path(base)` kullanıyor; `main.py` durum/snapshot için `logs_file_path(base_dir)` kullanıyor. Path tek kaynak.

### 1.2 Presence log sink hizası (4b72c4a, e539847)

- **Yapılan:** Log satırı yazımı merkezi sink’e taşındı; presence event’leri aynı sink üzerinden yazılıyor.
- **Sink:** `workspace_contract.append_log_line(base_dir, line, is_sandbox_mode=False)` — path `logs_file_path(base_dir)`, yazmadan önce `allow_write_to_core`. Append semantiği (read mevcut + concat + write) sink içinde.
- **Çağıran:** `presence_lock._append_log(message, base_dir=None)` satırı `"{ts} | {message}"` formatında hazırlayıp `append_log_line(base_dir, line)` çağırıyor. Format (timestamp | event=... key=val) parser/test beklentisiyle aynı.

### 1.3 base_dir akışı / log hedefi düzeltmesi (e539847)

- **Sorun:** `main.py` içinde `_P(base_dir)` tanımsızdı; presence menü subprocess’te NameError ile düşüyordu; presence_enabled/presence_disabled event’leri hiç yazılmıyordu.
- **Düzeltme:** `_P(base_dir)` → `Path(base_dir)` (main); log_event zincirine base_dir iletildi: `CoreState(base_dir=Path(base_dir))` → `state.log_event` → `pl.log_event(message, base_dir=self._base_dir)` → `_append_log(message, base_dir=...)`. Böylece log hedefi her zaman main’in base_dir’i ile aynı; self_check ve presence event’leri aynı dosyada.

---

## 2. Hâlâ orta risk taşıyan parçalar

| Parça | Neden orta risk |
|-------|------------------|
| **config.json yazıcı** | Şu an kodda config.json’a yazan bir fonksiyon yok (sadece okuma var). İleride eklenirse path + sink merkezileştirmesi davranışı etkileyebilir; tek yazma noktası olmalı. |
| **Log rotasyonu / dosya yapısı** | Mevcut davranış tek dosya append; rotasyon veya yapı değişikliği birçok okuyucuyu (durum, test, TUI) etkiler. |
| **sandbox_mode tek kaynaktan iletimi** | Tüm sink’lere (log, presence, aliases, notes, TaskStore, identity, keystore) `is_sandbox_mode` / `sandbox_mode` bayrağının CLI/main’den tek kaynaktan gelmesi; etki alanı geniş, yanlış iletim guard’ı bozabilir. |
| **Diğer log yazıcıları** | `config.report_config_invalid_once` vb. dolaylı log_event kullanıyor; log_event zaten presence_lock → append_log_line. Yeni doğrudan log dosyası yazan nokta eklenirse aynı sink’e bağlanmalı. |

---

## 3. Kalan işler — küçük alt paketler

### Paket A: config.json yazıcı sink’i (yazıcı çıkarsa)

| | |
|--|--|
| **Hedef dosyalar** | `src/core/workspace_contract.py` (opsiyonel `save_config_json`), config yazan modül (şu an yok). |
| **Risk** | Düşük–orta. Sadece yazıcı eklendiğinde; path zaten `config_file_path`, guard aynı pattern. |
| **Neden ayrı** | Config yazıcı şu an yok; eklenince tek commit’te path + sink ile alınabilir. |

### Paket B: sandbox_mode iletim zinciri denetimi (audit)

| | |
|--|--|
| **Hedef dosyalar** | `src/main.py` (sandbox bayrağı nereden geliyor), `workspace_contract` çağıran tüm noktalar (aliases, notes, TaskStore, presence_lock, identity, keystore). |
| **Risk** | Orta. Sadece denetim/rapor; kod değişikliği yok. |
| **Neden ayrı** | Hangi sink’in şu an `is_sandbox_mode`/`sandbox_mode` aldığını ve main’de tek kaynak olup olmadığını netleştirmek; sonraki iletim PR’ları için taban. |

### Paket C: sandbox_mode tek kaynak (uygulama)

| | |
|--|--|
| **Hedef dosyalar** | `src/main.py` (tek sandbox_mode değişkeni/argümanı), tüm sink çağrılarına bu değerin iletilmesi. |
| **Risk** | Orta. Davranış değişmez (varsayılan False); iletime hata olursa sandbox açıldığında yanlış izin. |
| **Neden ayrı** | Paket B tamamlandıktan sonra; küçük adımlarla (ör. önce main’de tek değişken, sonra sink’lere parametre). |

### Paket D: Log rotasyonu / yapı (ileride)

| | |
|--|--|
| **Hedef dosyalar** | `workspace_contract` (logs path/sink), log okuyan yerler (state.snapshot, TUI, test). |
| **Risk** | Orta–yüksek. Mevcut tek-dosya append değişirse test ve okuyucular etkilenir. |
| **Neden ayrı** | İhtiyaç doğana kadar ertelenebilir; ihtiyaç olunca ayrı tasarım + test odaklı küçük PR. |

---

## 4. Sonraki tek uygulanacak alt paket

- **Seçilen:** **Paket B — sandbox_mode iletim zinciri denetimi (audit)**.
- **Gerekçe:** Kod/test değişikliği yok; sadece mevcut çağrı zincirinin ve bayrağın nereden geldiğinin dokümante edilmesi. Sonraki sandbox iletim adımları (Paket C) için güvenli taban. Yeşil davranışla çelişmez.

**Beklenen çıktı (Paket B):** Kısa rapor: main’de sandbox ile ilgili bayrak/argüman var mı; her sink’in (`append_log_line`, `save_*_json`, `save_task_store_json`) şu an hangi `is_sandbox_mode`/`sandbox_mode` değerini aldığı (sabit False mu, parametre mi); tek kaynak önerisi (ör. `main()` içinde `sandbox_mode = False` ve tüm menü/sink çağrılarına iletilmesi).

---

## 5. Dokunulan dosya (bu belge)

- **Dosya:** `docs/lumos-guard-sink-phase2-checkpoint-log-config.md` (yeni).
- **İçerik:** Bu turda oturan parçalar (log/config path, presence log sink, base_dir akışı); kalan orta riskli parçalar; küçük alt paketler (A–D); sonraki tek adım (Paket B audit).

*Mevcut yeşil davranış ve guard zinciri ile çelişmez; genişletme yok.*
