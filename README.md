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

## Quick start

```bash
# Sanal ortam (önerilir)
python3 -m venv .venv && source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt   # varsa

# Doğrulama
make check

# Çalıştır
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
| `make run` | `PYTHONPATH=src python src/main.py` (etkileşimli CLI) |
| `make cleanlog` | `.lumos/log.txt` dosyasını temizler |

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
