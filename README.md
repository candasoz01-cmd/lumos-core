# Lumos-core

Lumos tek bir karaktere sahiptir.

- Emin olmadığı yerde konuşmaz.
- Boşluk doldurmaz.
- Kullanıcıya güven verir ama manipüle etmez.
- Offline modda hiçbir işlem yapmaz.
- Online modda yalnızca çağrıldığında çalışır.
- Çocuk ve yetişkin kullanıcıyı ayırt eder.
- Çocuk kullanıcıda güvenlik ve ebeveyn kontrolü önceliklidir.

Lumos'un ilerlemesi, yaptığı doğrulardan çok yapmadığı yanlışlarla ölçülür.

---

## Nasıl başlatılır

**Tek komut (paket kurulumu sonrası):**

```bash
lumos
```

veya:

```bash
python -m lumos_core
```

İlk kullanım öncesi proje kökünde paketi kurun:

```bash
python3 -m venv .venv && source .venv/bin/activate   # Linux/macOS
pip install -e .
lumos
```

Açılışta önce "Lumos başlatılıyor." yazılır, ardından **self-check** çalışır, sonra `Sen:` promptu gelir.

- **Alt komutlar:** `lumos` veya `lumos cli` → etkileşimli CLI; `lumos web` → Web v1 sunucusu (repo kökünden).
- **Sürüm:** `lumos --version`
- **Mod:** `LUMOS_MODE=online lumos` veya `LUMOS_MODE=offline lumos` (varsayılan: offline)

---

## Self-check

Açılışta otomatik çalışan kısa doğrulamadır. Config, log, notlar, parser ve state kontrol edilir; 2–5 saniyeyi aşmaz. Çıktıda her adım için `ok` veya `fail` görürsünüz; hepsi geçerse `overall: ready`, aksi halde eksik alanlar listelenir. CLI akışı self-check’ten sonra başlar.

---

## Self test

Derin doğrulama: config, log, not ekleme/düzenleme/özetleme, alias ve yardım blokları test edilir. **Çalıştırma:** CLI içinde promptta `self test` veya `self test` yazın. Sonuç satırı: `self test: passed (N/M)` veya `self test: failed (N/M)`.

---

## Paketleme (yerel)

- Proje kökünde: `pip install -e .` ile kurulum. Tek giriş komutu: **`lumos`** veya **`python -m lumos_core`**.
- Geliştirme: `make run` aynı komutu kullanır; `scripts/run.sh` ise `cd src && python3 main.py` ile doğrudan geliştirme akışıdır.
- Tam kurulum (sdist) için: `pip install .` (kaynak dağıtımından). Entry point: `lumos = "lumos_core.__main__:main"` (pyproject.toml).

**`lumos --version` çalışmıyorsa / `cd: no such file or directory: --version` alıyorsanız:** Kabukta tanımlı bir `lumos` alias veya function, pip’in kurduğu script’i gölgeliyor olabilir. Kontrol: `which lumos`, `type lumos`, `command -V lumos`. Çıktı `.venv/bin/lumos` (veya kullandığınız venv’in `bin/lumos`) olmalı; alias/function ise `unalias lumos` veya doğrudan `./.venv/bin/lumos --version` kullanın.

---

## Quick start (geliştirici)

```bash
# Sanal ortam (önerilir)
python3 -m venv .venv && source .venv/bin/activate
pip install -e .   # veya pip install -r requirements.txt varsa

# Doğrulama
make check

# Çalıştır (tek komut)
make run
```

## Make hedefleri

| Hedef | Açıklama |
|-------|----------|
| `make check` | Tek doğrulama kapısı: compile + test + smoke + cli + web |
| `make compile` | `py_compile` (main, presence_lock, state, …) |
| `make test` | `pytest -q` |
| `make smoke` | `bash scripts/smoke_presence.sh` |
| `make cli` | `bash scripts/smoke_cli.sh` |
| `make web` | `bash scripts/smoke_web.sh` |
| `make run` | `lumos` (veya `python -m lumos_core`) — etkileşimli CLI |
| `make cleanlog` | `.lumos/logs/log.txt` dosyasını temizler |

---

## Çalışma yapısı

Lumos, çalışırken bulunduğu dizini çalışma kökü olarak kabul eder ve altında sabit bir omurga kullanır:

- `.lumos/` — çalışma kökü (paketli modda da sabittir)
  - `tasks/` — görev deposu (`tasks.json` burada tutulur, görevlerin tek kalıcı kaynağıdır)
  - `logs/` — çalışma logları (`log.txt` burada tutulur)
  - `trash/` — silinen/taşınan öğeler için arşiv alanı (aktif state kaynağı değildir)
  - `config/` — isteğe bağlı yerel ayar/override dosyaları (yoksa dahili varsayılanlar kullanılır)

Açılışta self-check, çalışma kökünü ve bu klasörlerin varlığını/yazılabilirliğini kontrol eder; eksikler mümkün olduğu yerde otomatik oluşturulur, kritik hatalar kullanıcıya kısa mesajla raporlanır.

## Presence smoke (Option B)

`scripts/smoke_presence.sh` şu akışı çalıştırır: **kamera aç → evet → 10 → kamera kapat → çık**.

Garanti edilen log sırası:

- `presence_enabled` → `presence_started` → `presence_disabled`
- Bu akışta **`presence_stopped` görünmez** (disable, silent stop kullanır; Option B).

Boot desync durumunda (config enabled ama thread yok) yalnızca `presence_autostarted | reason=boot_desync` loglanır.

---

## Web v1 (read-only)

Web v1, core’u değiştirmeden durum okumak için minimal HTTP sunucusudur. **Sadece okuma** yapar; kilit veya presence yönetimi yok.

### Çalıştırma

```bash
# Repo kökünden
python web/app.py
# Varsayılan: http://127.0.0.1:8765 (PORT=8765)
```

### Endpoint’ler

| Endpoint   | Açıklama |
|-----------|----------|
| `GET /health` | `{"ok": true, "version": "..."}` — sunucu sağlık kontrolü |
| `GET /status` | Core ile aynı bilgiyi JSON: `lock_status`, `presence_enabled`, `presence_running`, `mode`, `last_log_ts` (offline + locked/presence snapshot) |

Örnek:

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/status
```

### Doğrulama

- `make check` — compile, test, presence smoke, CLI smoke ve **web smoke** (`make web` → `scripts/smoke_web.sh`) çalıştırır.
- Web smoke: sunucu arka planda başlatılır, `/health` ve `/status` curl ile istenir, başarılıysa "OK: smoke_web passed" yazılır.

**Not:** Web v1 = read-only. Kilit açma/kapama veya presence aç/kapat işlemleri yapılmaz; sadece mevcut durum okunur.

---

## Güvenlik ve entropy

Şifreleme, keystore ve imza için rastgele veri `security.entropy` üzerinden alınır: `entropy(n, provider="os")`, `get_random_bytes(n)`. **Varsayılan:** OS CSPRNG (`os.urandom`). Provider seçimi: `LUMOS_ENTROPY_PROVIDER=os|qiskit_aer|ibm_runtime`.

### Quantum entropy (experimental)

Varsayılan kaynak kriptografik olarak güvenli OS CSPRNG’dir. İsteğe bağlı deneysel provider’lar: `qiskit_aer` (yerel simülatör), `ibm_runtime` (IBM Quantum). IBM Quantum runtime bağlantısı hazırsa gerçek backend kullanılabilir; yoksa veya hata durumunda otomatik olarak os.urandom’a düşülür.
