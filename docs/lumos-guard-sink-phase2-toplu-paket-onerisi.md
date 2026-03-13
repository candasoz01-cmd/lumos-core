# Phase 2 — Düşük riskli writer adayları ve ilk toplu paket önerisi

Teşhis: Merkezi sink pattern’ine henüz alınmamış, aynı pattern ile hızlı alınabilecek düşük riskli yazma noktaları ve en dar uygulanabilir toplu paket. Kod yazılmadı; davranış değiştirilmedi; sadece liste ve öneri.

**Referans:** `lumos-guard-sink-phase2-pilot.md`, `lumos-guard-sink-phase2-checkpoint.md`, `workspace_contract.py`, mevcut Phase 2 sink’ler (aliases, notes, TaskStore, presence, identity, keystore).

---

## 1. Düşük riskli aday listesi

### 1.1 Log append (`.lumos/logs/log.txt`)

| | |
|--|--|
| **Mevcut yazma noktası** | `src/security/presence_lock.py`: `_append_log(message)` → `Path.cwd() / ".lumos" / "logs" / "log.txt"`. Dizin oluşturup dosyayı read+concat+write ile append ediyor. Tek çağrı yeri; `log_event` ve presence start/stop/lock logları buradan yazılıyor. |
| **Merkezi sink’e alma** | `workspace_contract`: `log_file_path(base_dir)` (ve gerekirse `logs_dir_path`), `append_log_line(base_dir, line, is_sandbox_mode=False)`. Guard: `allow_write_to_core` — `logs/` zaten çekirdek (`is_core_state_path` altında). presence_lock sadece satırı hazırlayıp sink’e verecek. Append semantiği sink içinde (read mevcut + append + write). |
| **Risk** | **Düşük.** Tek nokta, basit format, aynı guard pattern; base_dir parametresi şu an `Path.cwd()` sabit — ileride base_dir geçirilirse tek kaynak olur. |

### 1.2 Diğer potansiyel düşük riskliler (şu an yazıcı yok)

- **config.json** — Sadece okuma var (`config.load_config`). İleride config yazıcı eklenirse: path + `save_config_json` benzeri sink ile tek commit’te alınabilir.
- **consent.json** — Sadece okuma (exists) var (`startup_health._consent_ok`). Consent yazan modül bu repoda taranan yüzeyde yok; ileride eklenirse aynı pattern adayı.

Bunlar için şu an **uygulama paketi yok**; sadece “ileride çıkarsa aynı pattern” notu.

---

## 2. Önerilen ilk toplu paket

- **İçerik:** Yalnızca **log append** sink’i (yukarıdaki tek somut düşük riskli aday).
- **Tek commitlik mi?** **Evet.** Tek yazma noktası (presence_lock._append_log), tek path (logs/log.txt), tek guard kullanımı. Değişiklik: workspace_contract’a path + `append_log_line` sink’i; presence_lock’ta _append_log’un bu sink’i çağırması.
- **İki commitlik yapmak gerekir mi?** Gerek yok. Küçük ve atomik; geri alması kolay; test aynı davranışı (append, path) doğrulayabilir.
- **Neden daha büyük paket değil?** Config/consent yazıcıları kodda olmadığı için “toplu” pakette sadece log append kaldı. Aynı karakterde başka aktif writer bulunmadı.

---

## 3. Orta ve yüksek risk — sadece not (dokunulmuyor)

- **Orta risk:** Config/logs tam entegrasyonu (path + rotasyon davranışı); CLI’dan `sandbox_mode`’un tüm sink’lere iletilmesi. Checkpoint dokümanındaki gibi ayrı adım.
- **Yüksek risk:** Kalıcı silme/trash akışları, runtime sandbox yaygınlaştırma, keystore/identity ek güvenlik katmanları. Ayrı tasarım; bu paket kapsamı dışı.

---

## 4. Sonraki uygulama sırası

1. **Şimdi (tek commit):** Log append → `log_file_path` + `append_log_line` sink; presence_lock._append_log bu sink’i kullanacak şekilde değiştirilir (ilk toplu paket).
2. **Sonra:** Config/consent yazıcıları kodda belirirse, aynı pattern ile ayrı küçük paketler.
3. **Daha sonra:** Orta riskli maddeler (config/logs tam entegrasyon, sandbox_mode iletimi) checkpoint’e göre planlanır.

---

*Mevcut yeşil guard zinciri ve Phase 2 checkpoint ile çelişmez; genişletme yok.*
