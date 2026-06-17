# OD-027 Faz 1 — `src/` vs `packages/kando_*` salt-okuma modül envanteri

**Durum:** Faz 1 tamamlandı (salt okuma; kod taşıma yok).  
**Kaynak karar:** [`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md) OD-027.  
**Doğrulama tarihi:** 2026-06-18 (repo grep + dosya ağacı taraması).

---

## 1. Amaç

`src/` (canlı Lumos Core) ile `packages/kando_*` (aday/ayrık paketler) arasındaki modül eşlemesini, import bağımlılıklarını ve çift-kod alanlarını **kanıta dayalı** kaydetmek. Faz 2 hedef mimari seçenekleri (A/B/C/D) için girdi üretmek.

**Kapsam dışı:** kod taşıma, import değişikliği, entrypoint düzenleme.

---

## 2. Yöntem

1. `src/` üst düzey paket/modül ağacı listelendi (`find`, `ls`).
2. Her `packages/kando_*/src/kando_*/` ağacı listelendi; `pyproject.toml` entry point / script alanları okundu.
3. `rg` ile çapraz import: `src/` → `kando_*`, `packages/` → `src/` (`core`, `security`, `kando`, …).
4. `kando_bridge`, `kando_runtime`, `kando_core`, `kando_memory`, `kando_policy`, `kando_context` referansları `src/`, `tests/`, `panel/`, `scripts/` içinde tarandı.
5. Örtüşen dosya adları `comm` ile karşılaştırıldı; seçili dosyalarda `diff -q`.
6. CI/Makefile `PYTHONPATH` zinciri doğrulandı.

**Sınıflandırma etiketleri:** `canlı aday` | `deneysel` | `ölü kod` | `taşınacak` | `belirsiz`

---

## 3. Özet tablo

| Alan | Sınıf | Kanıt (kısa) |
|------|--------|----------------|
| `src/` (tümü, `lumos` zinciri) | **canlı aday** | `pyproject.toml` → `lumos = lumos_core.__main__:main`; `src/main.py` → `core.lumos_runtime.create_runtime` |
| `src/kando/` | **canlı aday** | `kando_bridge/server.py` → `kando.file_patch_executor`; `core/brain.py` → `kando.cursor_bridge` |
| `packages/kando_bridge` | **canlı aday** | `python -m kando_bridge`; 16 test dosyası; `Makefile`/`ci.yml` PYTHONPATH |
| `packages/kando_runtime` | **canlı aday** | Bridge + test importları; gate/dispatch/executor zinciri |
| `packages/kando_runtime/lumos_runtime.py` | **ölü kod** (aynası) | Canlı: `src/core/lumos_runtime.py`; paket kopyasına dış import yok (`rg` sıfır) |
| `packages/kando_core` | **ölü kod** / deneysel ayna | 47 modül; `from core.*` ile `src/` bağımlı; `from kando_core` dış import **yok** |
| `packages/kando_core/__main__.py` | **deneysel** + OD-028 kalıntı | `web` alt komutu + `_run_web()`; kök `lumos` çağırmaz |
| `packages/kando_memory` | **ölü kod** (ayna) | `from kando_memory` / `import kando_memory` **sıfır** (yalnızca iç `kando_context`) |
| `packages/kando_policy` | **ölü kod** (ayna) | `from kando_policy` **sıfır**; bazı dosyalar `from security.*` ile `src/` bağımlı |
| `packages/kando_context` | **ölü kod** (ayna) | Yalnızca `kando_memory` içinden import |
| `kando-ai/` | **deneysel** (yan alan) | `main.py` + `requirements.txt`; root entry / CI zincirinde yok |

---

## 4. `src/` canlı omurga özeti

**Giriş zinciri (doğrulandı):**

```
lumos (pyproject.scripts)
  → src/lumos_core/__main__.py
    → src/main.py
      → core.lumos_runtime.create_runtime()
      → cli.cli_router.run_cli_loop()
```

| Üst modül | `.py` dosya sayısı | Sınıf | Not |
|-----------|-------------------|--------|-----|
| `lumos_core` | 1 | canlı aday | Yalnızca `__main__.py` (OD-028 sonrası `web` dalı yok) |
| `core` | 53 | canlı aday | Runtime, patch, decision, panel, workspace sözleşmesi |
| `cli` | 7 | canlı aday | CLI router, görev mutasyonu, notlar |
| `task_engine` | 26 | canlı aday | Planner, executor'lar, observation |
| `security` | 16 | canlı aday | Keystore, lock, entropy, permissions |
| `policy` | 4 | canlı aday | `offline_engine`, `rules` |
| `memory` | 5 | canlı aday | `memory.py`, `schema`, `secure_store`, `session_memory` |
| `context` | 2 | canlı aday | `context.context.Context` |
| `engine` | 4 | canlı aday | `online_engine` vb. |
| `kando` | 22 | canlı aday | Patch/cursor/LLM; bridge tarafından tüketilir |
| `device` | 7 | canlı aday | `lumos_runtime` içinde entegrasyon |
| `integrations` | 8 | belirsiz | Provider stub'ları; canlı zincirde sınırlı kullanım |
| `cando` | 3 | deneysel | `pr_ready_check`, `branch_cleanup_review` — geliştirme yardımcı |
| `logs` | 0 | — | Boş dizin (runtime logları `.lumos/logs/`) |

**Önemli:** `src/kando/kando_core.py` **paket değil** — yerel modül adı; `packages/kando_core` ile karıştırılmamalı (`src/kando/agent_runner.py` içinden `kando.kando_core` importu).

---

## 5. `packages/kando_*` paket bazlı detay

### 5.1 `kando_bridge` (6 modül)

| Modül | `__main__` | Sınıf |
|-------|------------|--------|
| `server.py` | — | canlı aday (HTTP köprü, ~2k+ satır) |
| `transcribe.py`, `transcribe_engine.py` | — | canlı aday (STT; `[stt]` extra) |
| `run.py` | — | canlı aday (`scripts/run_lumos.sh` → `python -m kando_bridge.run`) |
| `__main__.py` | **evet** → `server.run` | canlı aday |

**`pyproject.toml`:** `name = kando-bridge`; `[project.scripts]` **yok**; bağımlılık: `kando-runtime>=0.1.0`.

**`src/` bağımlılığı (kanıt):** `server.py` içinde `from core.*` (chat, video, panel) ve `from kando.file_patch_executor` lazy import.

---

### 5.2 `kando_runtime` (22 modül)

| Alt alan | Ana modüller | Sınıf |
|----------|--------------|--------|
| Gate / audit | `lumos_gate.py`, `lumos_audit.py`, `controlled_bridge.py` | canlı aday |
| Dispatch | `task_dispatch.py`, `router.py`, `bridge_intent.py`, `dangerous_command.py` | canlı aday |
| Executor'lar | `file_executor`, `shell_executor`, `system_executor`, `agent_executor`, `executors/*` | canlı aday |
| Runtime aynası | `lumos_runtime.py` | ölü kod (ayna; canlı `src/core/lumos_runtime.py`) |
| Brain aynası | `brain.py` | belirsiz — `diff -q` ile `src/core/brain.py` **özdeş**; dış import yok |
| Diğer | `engine.py`, `runtime_state.py`, `executor_gate.py`, `video_executor.py` (shim) | canlı aday / iç |

**`pyproject.toml`:** `name = kando-runtime`; script entry **yok**; `openai`, `requests`.

**`src/` bağımlılığı:** `lumos_runtime.py` doğrudan `cli.*`, `core.*`, `memory.*`, `policy.*`, `security.*`, `task_engine.*` import eder (paket çalışırken `PYTHONPATH` içinde `src/` zorunlu).

---

### 5.3 `kando_core` (47 modül)

| Özellik | Değer |
|---------|--------|
| `__main__.py` | **evet** — `cli` / `web` / `decision` alt komutları (`web` → eksik `web/app.py`; OD-028 çapraz) |
| `[project.scripts]` | **yok** |
| Dış tüketim | `from kando_core` / `import kando_core` → **sıfır** |
| `src/` bağımlılığı | Yaygın `from core.*` (panel, patch, decision, workspace) |

**Örtüşme:** `src/core/` ile **43 ortak dosya adı** (`comm` listesi: `lumos.py`, `patch_pipeline.py`, `panel_runtime.py`, …).

**Sınıf:** **ölü kod** (stale ayna) + **deneysel** entry (`__main__`).

**OD-028 çapraz:** Kök `src/lumos_core/__main__.py` artık `web` içermiyor; `packages/kando_core/__main__.py` hâlâ `_run_web()` ve `web` parser'ı taşır (satır 1–57 benzer desen).

---

### 5.4 `kando_memory` (5 modül)

Modüller: `memory.py`, `schema.py`, `secure_store.py`, `session_memory.py`, `__init__.py`.

| Karşılaştırma | Sonuç |
|---------------|--------|
| `schema.py`, `secure_store.py` | `diff -q` → özdeş (`src/memory/`) |
| `memory.py` | **farklı** — `src`: `from context.context import Context`; paket: `from kando_context.context import Context` |
| `session_memory.py` | **farklı** (`diff -q`) |
| Dış import | `kando_memory` paket adına **sıfır** |

**Sınıf:** **ölü kod** (drift riskli ayna). ADR-003 ile uyumlu.

---

### 5.5 `kando_policy` (19 modül)

Modüller: `identity`, `keystore`, `lock`, `rules`, `offline_engine`, `action_policy`, `permissions`, `presence_*`, `entropy/*`, `crypto`, `aliases`, `request_signer`, …

| Karşılaştırma | Sonuç |
|---------------|--------|
| `identity.py`, `keystore.py`, `lock.py`, `rules.py`, `offline_engine.py` | Seçili dosyalar `diff -q` → `src/security` veya `src/policy` ile özdeş |
| Dış import | `from kando_policy` → **sıfır** |
| `src/` bağımlılığı | Örn. `keystore.py` → `from security.crypto import …`; `aliases.py` → `from core.workspace_contract import …` |

**Sınıf:** **ölü kod** (ayna + kısmi `src/` coupling).

---

### 5.6 `kando_context` (2 modül)

`context.py`, `__init__.py` — `src/context/` ile dosya adı örtüşmesi tam.

**Tüketim:** Yalnızca `packages/kando_memory` (`memory.py`, `session_memory.py`).

**Sınıf:** **ölü kod** (paket içi ayna).

---

### 5.7 `kando-ai/` (yan alan)

| Dosya | İçerik |
|-------|--------|
| `main.py` | OpenAI + PIL görüntü bölme demo scripti |
| `requirements.txt` | Bağımlılıklar |

Root `pyproject.toml`, `Makefile`, CI workflow içinde referans **yok**.

**Sınıf:** **deneysel** — canlı Lumos CLI zincirinde değil ([`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md) §6).

---

## 6. Çift-kod / overlap matrisi

| Domain | `src/` canonical | `packages/` karşılık | Örtüşme | Drift |
|--------|------------------|----------------------|---------|-------|
| Core / Lumos | `src/core/*` (53) | `kando_core/*` (47) | 43 ortak basename | Paket `src/core` import eder; dış tüketim yok |
| Runtime bootstrap | `src/core/lumos_runtime.py` | `kando_runtime/lumos_runtime.py` | Yüksek | Küçük fark (693. satır yorum; EOF newline) |
| Brain | `src/core/brain.py` | `kando_runtime/brain.py` | Tam kopya görünümü | `diff -q` özdeş |
| Memory | `src/memory/*` | `kando_memory/*` | 5/5 basename | `memory.py`, `session_memory.py` farklı |
| Policy / security | `src/security/*`, `src/policy/*` | `kando_policy/*` | 17+ ortak basename | Seçili dosyalar özdeş; paket `security.*` kullanır |
| Context | `src/context/*` | `kando_context/*` | 2/2 basename | Paket yalnızca `kando_memory` tarafından |
| Bridge / gate | `src/kando/*` + `src/core/*` (panel) | `kando_bridge` + `kando_runtime` (gate) | İşlevsel overlap | Canlı yol: paketler + `src/` PYTHONPATH |
| Agent patch | `src/kando/file_patch_executor` | — | Tek canonical `src/` | Bridge lazy import |

---

## 7. Import bağımlılık özeti

### 7.1 `src/` → `packages/kando_*`

| Yön | Sonuç |
|-----|--------|
| `src/` içinde `from kando_bridge` / `from kando_runtime` / `from kando_core` | **YOK** (`rg` `src/` → sıfır eşleşme) |

`src/kando/controlled_bridge_client.py` HTTP istemcisi; paket import etmez.

### 7.2 `packages/` → `src/`

| Paket | `src/` importu | Kanıt örneği |
|-------|----------------|--------------|
| `kando_bridge` | **var** | `from core.chat_memory_prompt`, `from kando.file_patch_executor` |
| `kando_runtime` | **var** (`lumos_runtime.py` tam bootstrap) | `from cli.cli_router`, `from core.lumos`, `from security.keystore` |
| `kando_core` | **var** (çoğu modül) | `from core.patch_pipeline`, `from core.runtime_state` |
| `kando_policy` | **var** (seçili) | `from security.crypto`, `from core.workspace_contract` |
| `kando_memory` | **yok** (yalnız `kando_context`) | `from kando_context.context` |
| `kando_context` | **yok** | — |

**Sonuç:** Aktif paketler (`bridge`, `runtime`) çalışmak için **`PYTHONPATH` ile `src/` gerektirir**. Tek yönlü bağımlılık: `packages → src`, tersi yok.

### 7.3 Test / script / panel referansları

| Konum | `kando_bridge` | `kando_runtime` | `kando_core` paketi |
|-------|----------------|-------------------|---------------------|
| `tests/` | 16 dosya | aynı dosyalarda | **0** |
| `scripts/` | `kando_bridge_server.py`, `bridge_start.sh`, `run_lumos.sh` | PYTHONPATH | **0** |
| `panel/e2e/` | `kando_bridge_server.py` spawn | PYTHONPATH `kando_runtime/src` | **0** |
| `Makefile` / `.github/workflows/ci.yml` | PYTHONPATH | PYTHONPATH | dahil değil |

**PYTHONPATH (kanıt):**

```
src:packages/kando_runtime/src:packages/kando_bridge/src
```

(`Makefile` satır 3; `ci.yml` satır 30)

---

## 8. Önerilen Faz 2 girdileri (A/B/C/D karar verisi)

| Seçenek | Envanter desteği | Risk / not |
|---------|------------------|------------|
| **A — Birleştir** | `kando_bridge` + `kando_runtime` modülleri `src/` altına taşınabilir; 16 test + CI PYTHONPATH sadeleşir | Büyük diff; gate/bridge güvenlik sınırı yeniden doğrulanmalı |
| **B — Ayrı kal** | Mevcut durum: paketler `src/` olmadan tam çalışmaz; zaten ince kabuk değil, **ters bağımlılık** var | İki ağaç drift (`lumos_runtime` aynası); bakım yükü |
| **C — Hibrit** | `src/` core canonical; yalnızca `kando_bridge`+`kando_runtime` paket olarak kalır; `kando_core`/`memory`/`policy`/`context` arşiv | Ayna paketlerin kaldırılması/arşivi net kazanç; import sözleşmesi dokümante edilmeli |
| **D — Dondur / arşiv** | `kando_core`, `kando_memory`, `kando_policy`, `kando_context` zaten fiilen ölü; dondurma düşük risk | `bridge`+`runtime` canlı kaldığı sürece tam D mümkün değil — kısmi dondurma |

**Taşıma adayları (yön notu, karar bekliyor):**

| Kaynak | Hedef yön | Sınıf |
|--------|-----------|--------|
| `packages/kando_core/*` | Arşiv veya silme (canonical `src/core`) | taşınacak değil — **birleştirme gereksiz** |
| `packages/kando_memory`, `kando_policy`, `kando_context` | Arşiv | ölü kod temizliği adayı |
| `packages/kando_runtime/lumos_runtime.py` | Kaldır veya `src/core` ile senkron tek kaynak | taşınacak / silinecek ayna |
| `packages/kando_bridge`, `kando_runtime` (gate/dispatch) | `src/kando_bridge` veya `src/bridge` — **A/C onayı gerekir** | taşınacak (opsiyonel) |

**Açık Faz 2 soruları (envanter cevabı):**

1. `kando_core.__main__` kaldırılsın mı, yoksa root `lumos` ile birleştirilsin mi? → Şu an **hiç çağrılmıyor**; `web` kalıntısı OD-028 ile hizalanmalı.
2. `lumos_runtime` tek kaynak `src/core` mi kalacak? → Evet (canlı kanıt); paket kopyası ölü ayna.
3. Bridge/runtime paket olarak mı kalır? → Test+CI+panel kanıtı: şu an **canlı ayrı paket**.

---

## 9. Riskler ve belirsizlikler

| Risk | Kategori | Açıklama |
|------|----------|----------|
| Sessiz drift | doğruluğu etkileyen | `kando_core` ↔ `src/core` 43 dosya; `memory.py` import yolu farkı |
| Çift runtime | doğruluğu etkileyen | `lumos_runtime.py` iki yerde; yalnızca `src/` canlı |
| PYTHONPATH kırılganlığı | blocker (geçişte) | Bridge/runtime `src/` olmadan import kırılır |
| `kando_runtime/brain.py` | belirsiz | `src/core/brain.py` ile özdeş ama hangi zincir kullanıyor net değil |
| `integrations/` | belirsiz | Canlı CLI'da rolü envanterde tam haritalanmadı |
| `kando-ai/` | opsiyonel | Ürünleştirme kapsam dışı; gelecekte scope creep riski |
| Public sınır | politika | Taşıma sırasında production/private katman sızıntısı denetimi gerekir |

---

## 10. Doğrulama komutları (tekrarlanabilir)

```bash
# src → packages import (beklenen: boş)
rg 'from kando_|import kando_' src/

# packages → src import (beklenen: çok)
rg 'from (core|security|policy|memory|cli|task_engine|kando)\.' packages/

# Ölü paket dış import (beklenen: boş)
rg 'from kando_core|from kando_memory|from kando_policy' --glob '*.py'

# Test kapsamı
rg -l 'kando_bridge|kando_runtime' tests --glob '*.py'
```

---

## 11. Sonraki adım

Faz 2 kararı onaylandı: [`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md) §7 — **Seçenek C (Hibrit)**. Uygulama paketi: ayna paket arşivi + §8 kesme checklist.

---

*Son güncelleme: 2026-06-18*
