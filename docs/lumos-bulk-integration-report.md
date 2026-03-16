# Lumos Toplu Entegrasyon Raporu

**Tarih:** 2026-03-16  
**Amaç:** decision / simulation / ranking / execution / feedback / strategy / patch proposal katmanlarını tek ve tutarlı akışta birleştirmek.  
**Kırmızı çizgiler:** autonomous apply yok, commit/push yok, büyük refactor yok, yeni bağımlılık yok, güvenlik sınırlarına dokunulmadı.

---

## 1. Bağlanan modüller

| Modül | Rol |
|-------|-----|
| `decision_explorer` | `generate_candidate_options(goal, target_paths)` → aday seçenekler |
| `decision_simulator` | `simulate_option(option)` → SimulationResult |
| `decision_ranker` | `rank_options(options, simulations)` → ağırlıklar `adaptive_weights.load_weights()` ile |
| `decision_runner` | `execute_decision(option)` → PatchProposal, validate, sandbox; apply yok |
| `evolution_tracker` | `record_execution(result)` → `logs/lumos_decision_feedback.jsonl` |
| `strategy_updater` | `apply_decision_feedback_updates()` → `lumos_decision_feedback.jsonl` okuyup `.lumos/weights.json` günceller |
| `evolution_log` | `record_event(...)` → `logs/lumos_evolution.jsonl` (explorer tarafı olaylar) |
| `patch_pipeline` | `validate_proposal_against_filesystem`, `run_sandbox_validation` (runner tarafından çağrılıyor) |
| `workspace_contract` | `is_core_state_path` → runner'da protected_target; apply kapalı |

---

## 2. Yapılan küçük entegrasyonlar

1. **Pipeline → feedback → weights**  
   `run_decision_pipeline` sonunda `record_execution(result)` ardından (varsayılan) `apply_decision_feedback_updates(feedback_log_path=DECISION_FEEDBACK_LOG_PATH)` çağrılıyor. Böylece bu run’ın sonucu aynı oturumda weights’a yansıyor; bir sonraki ranking `load_weights()` ile güncel ağırlıkları kullanıyor.

2. **Strategy updater – decision feedback log**  
   Yeni fonksiyon: `apply_decision_feedback_updates(feedback_log_path=..., weights_path=..., state_path=...)`.  
   `logs/lumos_decision_feedback.jsonl` (EvolutionRecord: option_id, success, risk, timestamp, notes) satır satır okunuyor; `last_processed_line` `.lumos/strategy_feedback_state.json` içinde tutuluyor; her kayıt için success/risk’e göre küçük delta (REWARD_DELTA/PENALTY_DELTA) ile `.lumos/weights.json` güncelleniyor.  
   `analyze_evolution_log` ve `apply_evolution_updates` hâlâ `lumos_evolution.jsonl` kullanıyor; execution sonuçları için tek kaynak `lumos_decision_feedback.jsonl`.

3. **DecisionExecutionResult.proposal_diff_preview**  
   Sadece görünürlük: `proposal_diff_preview` property eklendi; `proposal_diff` ile aynı değeri döndürüyor (API tutarlılığı).

4. **Pipeline parametresi**  
   `run_decision_pipeline(..., update_weights_after_run=True)`. False verilirse feedback sonrası weights güncellenmez (testlerde ve istenen durumlarda kullanım için).

---

## 3. Değişen dosyalar

| Dosya | Değişiklik |
|-------|------------|
| `src/core/decision_pipeline.py` | `apply_decision_feedback_updates` ve `DECISION_FEEDBACK_LOG_PATH` import; `update_weights_after_run` parametresi; run sonunda opsiyonel weights güncelleme çağrısı |
| `src/core/decision_runner.py` | `DecisionExecutionResult.proposal_diff_preview` property |
| `src/core/strategy_updater.py` | `DEFAULT_DECISION_FEEDBACK_LOG_PATH`, `DEFAULT_FEEDBACK_STATE_PATH`; `apply_decision_feedback_updates()` fonksiyonu |
| `tests/test_decision_pipeline.py` | İki mevcut testte `update_weights_after_run=False`; yeni testler: ranker weights, strategy updater weights yazımı, evolution_tracker feedback log, proposal_diff_preview, pipeline weights güncellemesi, protected core no-apply |

---

## 4. Eklenen testler

- `test_decision_ranker_uses_adaptive_weights`: Ranker’ın `load_weights()` kullandığı ve özelleştirilmiş ağırlıklarla sıralamanın değiştiği.
- `test_strategy_updater_writes_weights`: `update_weights_from_outcome(True)` ile `.lumos/weights.json` oluşuyor ve alanlar 0–1 aralığında.
- `test_evolution_tracker_writes_decision_feedback_log`: `record_execution` sonrası `lumos_decision_feedback.jsonl`’a tek satır yazılıyor ve şema (option_id, success) doğru.
- `test_proposal_diff_preview_alias`: `proposal_diff_preview` == `proposal_diff`.
- `test_pipeline_updates_weights_from_feedback`: `update_weights_after_run=True` ve tmp path’lerle pipeline çalıştırıldığında feedback log ve (başarılı run’da) weights dosyası güncelleniyor.
- `test_protected_core_no_apply`: Hedef `base_dir` altında core path (örn. `.lumos/tasks.json`) olduğunda proposal üretiliyor, dosya içeriği değişmiyor, notlarda “no apply” geçiyor.

---

## 5. Test sonuçları

- `tests/test_decision_pipeline.py`: 9 test geçti.
- Tüm test suite: 252 test geçti.
- Ruff: ilgili dosyalarda lint hatası yok.

---

## 6. Kalan riskler

- **Path çözümleme:** `load_weights()` ve strategy updater path’leri CWD’ye göre (`.lumos/weights.json`, `logs/...`). Farklı CWD ile çalışan senaryolarda aynı repo için tek bir `.lumos` kullanımı test edilmedi.
- **Eşzamanlılık:** Aynı anda birden fazla process aynı `lumos_decision_feedback.jsonl` ve `.lumos/weights.json` kullanırsa race olabilir; tek process varsayımı devam ediyor.
- **Feedback state:** `strategy_feedback_state.json` ile satır bazlı takip var; log dosyası dışarıdan kesilirse/taşınırsa state sıfırlanmalı veya manuel ayarlanmalı.

---

## 7. Bilerek açılmayan şeyler

- **Autonomous apply:** Runner sadece proposal üretir, validate ve sandbox çalıştırır; apply hiçbir yerde otomatik açılmadı.
- **Commit/push:** Hiçbir entegrasyon commit veya push yapmıyor.
- **Büyük refactor:** Mevcut modül sınırları ve public API’ler korundu; sadece bağlantı ve bir property eklendi.
- **Yeni bağımlılık:** Projeye yeni paket eklenmedi.
- **workspace_contract / guard:** `is_core_state_path`, protected_target ve mevcut guard kuralları aynen kullanılıyor; by-pass yok.
- **apply_evolution_updates davranışı:** Evolution log (`lumos_evolution.jsonl`) hâlâ `apply_evolution_updates` ile işleniyor; execution sonuçları için tek kaynak decision feedback log. İleride evolution log’daki DECISION_OPTION_SELECTED ile feedback log’daki success eşleştirmesi eklenebilir; bu rapor kapsamı dışı.

---

## 8. Şu an sistemin yeni akışı

```
goal
  → generate_candidate_options(goal, target_paths)
  → [ her option için ] simulate_option(option)
  → rank_options(options, simulations)   # load_weights() ile .lumos/weights.json
  → execute_decision(best_option)
       → option_to_proposals → propose_text_patch (protected_target = is_core_state_path)
       → validate_proposal_against_filesystem(her proposal)
       → run_sandbox_validation(her proposal)
       → DecisionExecutionResult(proposal_ids, proposal_summary, proposal_diff, decision_explanation; proposal_diff_preview = proposal_diff)
  → record_execution(result)   # logs/lumos_decision_feedback.jsonl
  → [ update_weights_after_run=True ise ] apply_decision_feedback_updates()
       # lumos_decision_feedback.jsonl okunur, .lumos/weights.json küçük deltalarla güncellenir
  → return result
```

İsteğe bağlı üst katman: `analyze_evolution_log(lumos_evolution.jsonl)` ile rapor; bir sonraki pipeline run’ında `load_weights()` zaten güncel weights kullanır.

---

## 9. Son durum

**READY**

- End-to-end bağlantı kuruldu ve testlerle doğrulandı.
- Decision ranker adaptive weights kullanıyor (mevcut + test).
- Strategy updater decision feedback log’dan okuyup weights yazıyor; küçük oranlı güncelleme (0.01–0.05) ve 0–1 sınırları korunuyor.
- Runner proposal üretiyor, validate ve sandbox çalışıyor; apply yok; protected/core güvenliği korunuyor.
- Evolution ve decision feedback log’lar ayrı; strategy updater doğru logu kullanıyor.
- Açıklama katmanı (explain_decision) ve diff görünürlüğü (proposal_diff / proposal_diff_preview) mevcut ve deterministik.
- Tüm testler ve lint geçiyor; kırmızı çizgilere uyuldu.
