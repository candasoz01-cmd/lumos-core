# Lumos Persona — Kando/Cando bypass giriş envanteri

| Alan | Değer |
|------|-------|
| Durum | **Salt okuma envanter** — davranış değişikliği yok |
| Tarih | 2026-06-07 |
| İlgili PR | [#100](https://github.com/candasoz01-cmd/lumos-core/pull/100) (persona katmanları), [#101](https://github.com/candasoz01-cmd/lumos-core/pull/101) (checkpoint + gap kaydı) |
| Plan | [lumos-persona-security-checkpoint.md](lumos-persona-security-checkpoint.md) |
| Gap kaydı | [lumos-persona-security-implementation-gaps.md](lumos-persona-security-implementation-gaps.md) |

## Amaç

Persona ilkesi: dış etkili komut/iş/dosya yalnızca doğrulanmış **Lumos kanalı** (`run_lumos_gate` + policy + onay) üzerinden Kando/Cando’ya ulaşmalı. Bu belge, repo taramasıyla **Lumos dışı veya kısmi kapı** yollarını listeler; sonraki faz invariant testlerinin girdisidir.

**Kapsam dışı:** protokol, anahtar, algoritma, wire-format; penetrasyon tarifleri.

---

## Özet

| Metrik | Değer |
|--------|-------|
| Envantere alınan giriş noktası | **22** |
| Tam `lumos_gate` zinciri | 4 (+ 1 onay sonrası yürütme) |
| Bilinen bypass / kısmi kapı | **11** |
| Salt okuma / Kando hedef değil | 7 |

---

## Envanter tablosu

| # | Giriş noktası | Hedef (Kando/Cando) | Gate / Lumos? | Bypass? | Not |
|---|---------------|---------------------|---------------|---------|-----|
| 1 | `kando_bridge` `POST /task` | Kando: patch / agent / dispatch | `run_lumos_gate` → `policy_check` → `lumos_gate_execute` | Hayır | Loopback zorunlu; `KANDO_BRIDGE_SECRET` boşsa token atlanır (yerel risk). Yıkıcı yüzey ön taraması var. |
| 2 | `kando_bridge` `POST /agent-run` | Kando: agent job | Aynı `_complete_through_gate` | Hayır | `goal` zorunlu; gate tam. |
| 3 | `kando_bridge` `POST /chat` → task yönlendirme | Kando: gate boru hattı | `_complete_through_gate` (task intent) | Hayır | `classify_bridge_message_intent` == task ve kısa yol devreye girmezse. |
| 4 | `kando_bridge` `POST /chat` → `simple_chat_task` | Kando: doğrudan dosya yazımı | **Yok** | **Evet** | `core/simple_chat_task.run_task` gate’siz `test.py` yazar; persona tek kapı ihlali. |
| 5 | `kando_bridge` `POST /chat` → saf sohbet | LLM yanıt (Kando yürütme yok) | Gate yok | Kısmi | Kando motoru tetiklenmez; dış LLM çağrısı persona “tek geçit” kapsamı dışında ama izlenmeli. |
| 6 | `kando_bridge` `POST /approve` | Kando: onaylı yürütme | Gate yalnızca pending oluşturulurken; yürütmede `execute_approved_pending_record` (gate tekrar yok) | Kısmi | `approval_token` + disk kaydı gerekir; sahte iç onay riski ayrı checkpoint (§6). |
| 7 | `kando_bridge` `POST /controlled` | Kando: `workspace/` read/write | `controlled_bridge.execute_controlled` + `policy_allows_normalized`; **tam `lumos_gate` değil** | **Evet (kısmi)** | Dar yüzey; shell/silme/mail bloklu. Persona “tek kapı” ile tam eşdeğer sayılmaz. |
| 8 | `kando_bridge` `POST /replay` | Audit (yürütme yok) | `replay_lumos_gate` dry_run | Hayır | Yalnızca denetim; executor replay modunda atlanır. |
| 9 | `kando_bridge` GET (`/health`, `/outbox`, …) | Okuma / durum | Secret (bazı uçlar); gate yok | Hayır | Kando komut kabul etmez; bilgi sızıntısı ayrı konu. |
| 10 | `src/main.py` → CLI `görev oluştur` | TaskEngine (`brain_run`) | `action_policy.check_policy` | **Evet** | `run_lumos_gate` yok; köprüden bağımsız görev yürütme. Gap #1. |
| 11 | CLI `görev iptal` / `görev sil` / arşiv | TaskEngine / TaskStore | Seçili mutasyonlarda policy; gate yok | **Evet** | Kalıcı silme kullanıcı komutu + uyarı; yine de lumos_gate dışı. |
| 12 | `scripts/cando_local.py` `recipe … --dry-run` | Cando recipe modülleri | **Yok** | **Evet** | `branch_cleanup_review`, `pr_ready_check`; salt okuma sınırı script seviyesinde, kanal doğrulama yok. Gap #2. |
| 13 | `src/cando/*` (doğrudan import/çağrı) | Cando read-only git/gh | **Yok** | **Evet** | Resmi CLI dışı `python -c` / test import ile aynı boşluk; yabancı giriş reddi yok. |
| 14 | `scripts/kando_send.py` → köprü URL | Kando (köprü üzerinden) | Köprü gate’ine tabi | Hayır | Dolaylı giriş; hedef yine `POST /task`. |
| 15 | `python -m kando.cursor_bridge` (doğrudan) | Kando patch/ brain hattı | **Yok** (CLI) | **Evet** | Köprü gate sonrası subprocess normal; **doğrudan modül çağrısı** bypass. |
| 16 | `python -m kando.repl` | Kando LLM (`kando.llm`) | **Yok** | **Evet** | Etkileşimli yerel REPL; policy/gate yok. |
| 17 | `kando/agent_runner.start_agent_job` (doğrudan) | Kando agent pipeline | **Yok** (CLI/script) | **Evet** | Köprü/onay dışı çağrıda `push_if_possible` dahil pipeline gate’siz (Gap #3 ile ilişkili). |
| 18 | `kando/file_patch_executor.run` (doğrudan) | Kando dosya patch | **Yok** | **Evet** | Gate yalnızca köprü `_complete_through_gate` içinden sarmalanır. |
| 19 | Panel `panel_tasks_server` `POST /tasks` (+ complete/delete) | `.lumos/tasks.json` (TaskEngine CRUD değil; panel state) | `_task_actions_gate()` her zaman `enabled: True` | **Evet** | Kando motoru değil; persona “tek dış geçit” açısından ayrı yazım yüzeyi. `lumos_gate` yok. |
| 20 | Panel / UI `POST` köprü `/task` (`ui/panel.astro`, E2E) | Kando köprü | Köprü gate | Hayır | Görev listesi CRUD (satır 19) ile karıştırılmamalı. |
| 21 | `task_engine.TaskEngine` (`core/brain.run` içi) | Çekirdek görev adımları | Profil + `may_execute_step_at_runtime`; **lumos_gate yok** | **Evet** | CLI ve brain yolunun motoru; köprü policy ile hizalı değil. |
| 22 | `kando/controlled_bridge_client` → `POST /controlled` | Kando controlled workspace | Satır 7 ile aynı | **Evet (kısmi)** | Python istemci; dar izin modeli. |

---

## Bilinen boşluklar (envanter ↔ gap)

| Gap | Envanter satırları | Kısa doğrulama |
|-----|-------------------|----------------|
| [#1 Kando CLI bypass](lumos-persona-security-implementation-gaps.md#1-lumos-dışından-kandoya-komut--cli--taskengine-bypass) | 10, 11, 21 | `src/` altında `lumos_gate` import yok; CLI → `brain_run` → TaskEngine. |
| [#2 Cando doğrudan](lumos-persona-security-implementation-gaps.md#2-cando-doğrudan-dosya--komut--yabancı-giriş-ve-lumos-kanalı) | 12, 13 | Recipe runner gate/kanal kontrolü içermiyor. |
| [#3 Offline push](lumos-persona-security-implementation-gaps.md#3-offline-kuyruk--internet-gelince-otomatik-dış-aksiyon-yok) | 17 | `agent_runner` push fazı ayrı trace PR’ında; bu envanter yalnızca giriş noktası işaret eder. |

---

## Checkpoint “Şimdi” — bu PR vs ertelenen

### Bu PR ile kapanan / kapsanan

| Checkpoint maddesi | Kapsam |
|--------------------|--------|
| Öncelik 1: Giriş envanteri tablosu (köprü / CLI / Cando / panel) | Tam tablo (22 satır) |
| §1 Giriş envanteri (endpoint → gate evet/hayır) | Köprü + CLI + Cando + panel + doğrudan modül |
| §1 CLI/TaskEngine gate bypass trace | Satır 10–11, 21; kod referansı doğrulandı |
| §2 CLI gate’siz / `cando_local` dry-run | Satır 12–13 |
| Gap #1–#2 ilk assertion (envanter) | Tablo + özet metrikler |

### Ertelenen “Şimdi” maddeler (sonraki PR / manuel)

| Madde | Sınıf | Neden ertelendi |
|-------|-------|-----------------|
| Köprü policy-blocked → 403 manuel test | §1 | Davranış testi; bu PR salt okuma |
| Offline reconnect / panel gözlemi | §3 | Ayrı trace belgesi |
| `agent_runner` push fazı trace | §3 | Gap #3; kod yürütme envanterinden ayrı |
| Keystore / secret bellek envanteri | §4 | Kando/Cando bypass dar kapsam dışı |
| Log/audit secret pattern taraması | §4 | Aynı |
| Bando runtime grep doğrulama | §5 | Kando/Cando bypass dışı (tek satır: runtime yok) |
| Anti-taklit auth envanteri + `KANDO_BRIDGE_SECRET` manuel | §6 | Protokol detayı yok kuralı; ayrı checkpoint PR |

### Sonraki faz (bilerek kapsam dışı)

- Tek kapı invariant test paketi
- Cando yabancı giriş reddi davranış testi
- Offline auto-push yok invariant testi
- Gateway sonuç-only contract testi

---

## Referans dosyalar (salt okuma)

| Rol | Yol |
|-----|-----|
| Köprü HTTP | `packages/kando_bridge/src/kando_bridge/server.py` |
| Lumos gate | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` |
| CLI mutasyon | `src/cli/cli_tasks_mutation.py` |
| Brain / TaskEngine | `src/core/brain.py`, `task_engine/engine.py` |
| Cando runner | `scripts/cando_local.py`, `src/cando/` |
| Chat kısa yolu | `src/core/simple_chat_task.py` |
| Agent pipeline | `src/kando/agent_runner.py` |
| Panel görev API | `panel/scripts/panel_tasks_server.py` |
| Kontrollü yüzey | `packages/kando_runtime/src/kando_runtime/controlled_bridge.py` |

---

## Ne yapılmaz

- Kod, test veya recipe değişikliği
- Güvenlik gevşetmesi veya otomatik düzeltme
- `lumos-karar-sozlesmesi` alanlarında implementasyon

**Sonraki dar adım:** Gap #1 için “CLI `görev oluştur` → `lumos_gate` çağrısı yok” odaklı davranış testi taslağı (ayrı PR).
