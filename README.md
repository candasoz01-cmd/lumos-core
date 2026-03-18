# Lumos-core

**Lumos Core** is the CLI and core library for Lumos: task/state handling, decision pipeline, patch pipeline, and workspace contract. It does not apply changes to files automatically; proposals are validated and optionally run in a sandbox first.

---

## Project overview

### What Lumos Core is

Lumos Core provides:

- Interactive CLI and read-only web status.
- **Decision pipeline**: goal + target paths → candidate options → simulation → ranking → chosen option → patch proposals (no apply).
- **Patch pipeline**: propose → validate (fingerprint) → optional sandbox → apply only when explicitly gated.
- **Workspace contract**: fixed `.lumos/` layout, trash rules, core-state protection.

### Main components

| Component | Role |
|-----------|------|
| **Decision pipeline** | Explorer generates options; simulator and ranker (using adaptive weights) pick the best; runner turns it into proposals and runs validation/sandbox. No file writes. |
| **Patch pipeline** | Creates `PatchProposal`s, validates against current file fingerprint, optionally runs sandbox validation. Apply is a separate, guarded step. |
| **Sandbox validation** | Writes proposed content to a temp file only; real target path is never touched. Used for extra checks (e.g. parse, tests). |
| **Adaptive weights** | Ranking weights (success, risk, impact) live in `.lumos/weights.json`; strategy updater can adjust them from decision-feedback log. |
| **Logs and history** | `logs/lumos_evolution.jsonl` (lifecycle events), `logs/lumos_decision_feedback.jsonl` (run outcomes for weights), `logs/lumos_decision_history.jsonl` (readable decision audit). |

### Demo decision script

From the repo root:

```bash
PYTHONPATH=src python scripts/demo_decision.py
```

Uses goal `"test decision"` and target `src/core/state.py`; prints proposal preview. No file changes; use `update_weights_after_run=False` in the script so no weights are written.

### Where logs and weights are stored

- **Logs:** Under `logs/` (repo root): `lumos_evolution.jsonl`, `lumos_decision_feedback.jsonl`, `lumos_decision_history.jsonl`. Runtime log: `.lumos/logs/log.txt`.
- **Weights and state:** `.lumos/weights.json` (ranking weights), `.lumos/strategy_updater_state.json`, `.lumos/strategy_feedback_state.json`. Tasks: `.lumos/tasks/` (e.g. `tasks.json`).

### Safety design

- **No automatic apply:** The decision pipeline only produces proposals and runs validation/sandbox. Applying to the real filesystem requires an explicit call to `apply_patch` with the right flags; protected/core targets require `allow_protected_apply` and review.
- **Sandbox validation:** Proposed content is written to a temporary file for checks; the actual target file is not modified in this step.
- **Protected targets:** When `base_dir` is set, core paths (e.g. under `.lumos/`) are marked `protected_target`; apply remains blocked unless explicitly allowed.

See `docs/ARCHITECTURE.md` for more detail.

---

## Lumos karakteri

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

**Demo Express API (`backend/`):** Gönderi, rating (Bearer token), feed, soft delete. Kurulum ve endpoint’ler: `backend/README.md`. Sunucu çalışırken repo kökünde `./test_api.sh` veya `make test-api`.

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

### Commit guard (geliştirme — ürün onayından ayrı)

Commit atmadan önce **otomatik** `ruff check .` ve `pytest -q`; geçmezse commit **olamaz**. Tam açıklama: **`docs/dev-commit-guard.md`**.

```bash
make setup-commit-guard    # tek kurulum komutu (repo kökü)
pip install -e . && pip install -U pytest ruff   # venv içinde
```

Atlama (istisna): `git commit --no-verify`. Ürün tarafında onay modeli: **`docs/kando-urun-onay-otomasyon-ayrimi.md`**.

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
| `make setup-commit-guard` | Commit öncesi `ruff` + `pytest` hook (bir kez); `install-git-hooks` aynı iş |

---

## Çalışma yapısı

Lumos, çalışırken bulunduğu dizini çalışma kökü olarak kabul eder ve altında sabit bir omurga kullanır:

- `.lumos/` — çalışma kökü (paketli modda da sabittir)
  - `tasks/` — görev deposu (`tasks.json` burada tutulur, görevlerin tek kalıcı kaynağıdır)
  - `logs/` — çalışma logları (`log.txt` burada tutulur)
  - `trash/` — silinen/taşınan öğeler için arşiv alanı (aktif state kaynağı değildir)
  - `config/` — isteğe bağlı yerel ayar/override dosyaları (yoksa dahili varsayılanlar kullanılır)

Açılışta self-check, çalışma kökünü ve bu klasörlerin varlığını/yazılabilirliğini kontrol eder; eksikler mümkün olduğu yerde otomatik oluşturulur, kritik hatalar kullanıcıya kısa mesajla raporlanır.

---

## Çalışma sözleşmesi

Bu bölüm, paketli çalışma omurgasının ürün/geliştirme sözleşmesini tanımlar. Kod ve test davranışı bu sözleşmeye göre tutarlı kalmalıdır.

### 1. Workspace omurgası

- **Çalışma kökü sabit:** Lumos, çalıştığı dizini (CWD) çalışma kökü kabul eder; altında tek sabit dizin `.lumos/` kullanılır.
- **Temel omurga:** `tasks/`, `logs/`, `trash/`, `config/` — dört alan sabit ve tanımlıdır.
- **trash aktif state kaynağı değildir:** Görevler, notlar veya durum okuması trash’ten yapılmaz; sadece arşiv/taşıma alanıdır.

### 2. Silme ve çöp kuralı

- **Doğrudan kalıcı silme yok:** Kullanıcı verisi, onay olmadan kalıcı olarak silinmez.
- **Önceden tanımlı çöp alanı:** Silinen/taşınan öğeler için yalnızca `.lumos/trash/` kullanılır.
- **Kalıcı temizleme kullanıcı kararı:** Çöp alanının kalıcı boşaltılması kullanıcı aksiyonuna bağlıdır.
- **Sistem yeni çöp alanı oluşturmaz:** Sistem kendi inisiyatifiyle başka bir “çöp” veya “silinenler” dizini açmaz.

### 3. Geliştirme sınırı

- **Bu aşamada açılmamış alanlar:** `sandbox/`, `data/`, `exports/` vb. şu an sistem sözleşmesinin parçası değildir.
- İleride ihtiyaçla açılabilir; açıldığında sözleşme ve dokümantasyon güncellenir.

### 4. Doğrulama ve uyumluluk notu

- **Paketli omurga doğrulandı:** Çalışma kökü, tasks/logs/trash/config yapısı, görev store, log akışı ve kalıcılık gerçek çalıştırma ile doğrulanmıştır.
- **Log yolu:** Resmî log dosyası `.lumos/logs/log.txt` içindedir. Eski veya harici kod `.lumos/log.txt` (kök altında doğrudan) bekliyorsa bu **tarihsel/legacy** bir beklentidir; yeni davranış ve dokümantasyon `.lumos/logs/log.txt` ile uyumludur.

---

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
