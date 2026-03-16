# Mimari bütünlük denetimi — decision / mutation / evolution katmanları

Tarih: 2026-03-16  
Kapsam: `src/core` içindeki decision, mutation, evolution ile ilgili modüller.  
Kural: Kanıtlanamayan ifadeler kesinmiş gibi yazılmadı; “muhtemel”, “stub”, “bağlı değil” ayrımı kullanıldı.

---

## 1. Mevcut mimari harita

### Hangi modülün görevi ne

| Modül | Görevi |
|-------|--------|
| **change_plan** | Çok patch’li değişiklik planı modeli (ChangePlan); plan oluşturma, validate_plan. Plan oluşturulunca evolution_log’a PLAN_CREATED yazar. |
| **decision_model** | MutationOption dataclass: aday seçenek modeli (risk, success, impact, sensitivity_summary, score, rationale). |
| **decision_explorer** | Hedef + target_paths → en az 3 MutationOption üretir; _compute_score ile skorlar; select_best_option ile en iyiyi seçer; create_plan_from_option ile seçenekten ChangePlan iskeleti (şu an boş patch ile — kırık). evolution_log’a DECISION_OPTIONS_GENERATED / DECISION_OPTION_SELECTED yazar. |
| **decision_simulator** | MutationOption → SimulationResult (stub: sadece option alanlarını kopyalar). |
| **decision_ranker** | options + simulations → final_score ile sıralı RankedOption listesi; sabit 0.4/0.3/0.3 ağırlık; adaptive_weights kullanmıyor. |
| **decision_runner** | MutationOption → DecisionExecutionResult (stub: sadece target_paths varlık kontrolü; gerçek apply yok). |
| **evolution_tracker** | DecisionExecutionResult → EvolutionRecord’a çevirip `logs/lumos_decision_feedback.jsonl`’a append eder (evolution_log’dan ayrı dosya; şema farkı). |
| **evolution_log** | Plan/patch/transaction lifecycle event’lerini EvolutionEvent şemasıyla `logs/lumos_evolution.jsonl`’a append eder; get_recent_events, get_failed_patches, get_rollbacks, get_conflict_stats. |
| **strategy_updater** | Aynı JSONL’ı okur; success oranı, ortalama risk, StrategyReport üretir; hiçbir modüle yazmaz; **hiçbir modül tarafından çağrılmıyor**. |
| **adaptive_weights** | `.lumos/weights.json`’dan DecisionWeights okur; yoksa varsayılan döner; **hiçbir modül tarafından kullanılmıyor**. |
| **patch_model** | PatchProposal, PatchFingerprint, PatchMetadata; diff üretimi. Dosyaya yazmaz. |
| **patch_pipeline** | propose_text_patch, validate_proposal_against_filesystem, run_sandbox_validation, apply_patch; registry + transaction + evolution_log; protected için ProtectedApplyForbidden. |
| **patch_registry** | Proposal → PatchRecord lifecycle (PROPOSED → … → APPLIED / FAILED vb.); in-memory. |
| **patch_transaction** | apply_with_transaction: path lock, fingerprint kontrolü, atomic write, registry güncelleme, evolution_log. |
| **write_interceptor** | core/protected path’e direct write’ı audit’leyip patch_pipeline’a yönlendirir; workspace_contract + guard_audit. **Çağrı: sadece testler (test_write_interceptor*, CLI/engine’den çağrı yok).** |
| **change_sensitivity** | Path → ChangeSensitivity (LOW/NORMAL/HIGH/CRITICAL). |
| **guard_audit** | GuardEvent alır; sadece logging (diske ek core dosyası yazmaz). |
| **workspace_contract** | Trash/sandbox path’leri, CORE_STATE_PATH_NAMES, is_core_state_path, allow_write_to_core, çekirdek yazıcılar (save_*_json), CoreWriteForbidden. |

### Hangi modül hangi modülü kullanıyor

```
change_sensitivity   ← change_plan, decision_model, decision_explorer, write_interceptor
patch_model          ← change_plan, patch_pipeline, patch_registry, patch_transaction
evolution_log        ← change_plan, patch_pipeline, patch_registry, patch_transaction, write_interceptor, decision_explorer

change_plan          ← change_sensitivity, patch_model, evolution_log
decision_model       ← change_sensitivity
decision_explorer    ← change_sensitivity, decision_model, evolution_log, change_plan
decision_simulator   ← decision_model
decision_ranker      ← decision_model, decision_simulator
decision_runner      ← decision_model
evolution_tracker    ← decision_runner (sadece DecisionExecutionResult tipi)

patch_registry       ← patch_model, guard_audit, evolution_log
patch_transaction    ← guard_audit, patch_model, patch_registry, evolution_log
patch_pipeline       ← guard_audit, patch_model, evolution_log, patch_registry, patch_transaction
write_interceptor    ← guard_audit, change_sensitivity, patch_pipeline, evolution_log, workspace_contract
plan_registry        ← change_plan, guard_audit  [listelenen 16 dışında; change_plan ile kullanılıyor]
workspace_contract   ← guard_audit

strategy_updater     ← (sadece json, pathlib; hiçbir core modülü)
adaptive_weights     ← (sadece json, pathlib; hiçbir core modülü)
guard_audit          ← (logging; kimse import etmez, birçok modül kullanır)
```

### Akış şeması

**Patch/mutation (aktif — testler + pipeline hazır):**

```
write isteği
  → write_interceptor.intercept_write   [şu an sadece testlerden çağrılıyor]
  → (core/protected ise) patch_pipeline.propose_text_patch + validate + apply_patch (gate ile)
  → patch_registry (lifecycle) + patch_transaction (atomic apply) + evolution_log.record_event
```

**Decision (teorik zincir; production’da tek adım yok):**

```
goal + target_paths
  → decision_explorer.generate_candidate_options → options
  → decision_explorer.select_best_option (kendi score’una göre; ranker kullanılmıyor)
  → [hiçbir yer] decision_simulator.simulate_option
  → [hiçbir yer] decision_ranker.rank_options
  → [hiçbir yer] decision_runner.execute_decision
  → [hiçbir yer] evolution_tracker.record_execution
  → decision_explorer.create_plan_from_option → ChangePlan.new(goal, []) → ValueError (boş patch)
```

**Analiz / ağırlık (bağlı değil):**

```
lumos_evolution.jsonl → strategy_updater.analyze_evolution_log → StrategyReport  [hiçbir yer çağırmıyor]
.lumos/weights.json  → adaptive_weights.load_weights → DecisionWeights            [hiçbir yer kullanmıyor]
```

---

## 2. Gerçek akış mı, teorik akış mı

| Modül | Sınıf | Kanıt |
|-------|--------|-------|
| **change_plan** | Aktif (patch/mutation tarafında) | ChangePlan.new, validate_plan testlerde ve plan_registry ile kullanılıyor; patch_pipeline doğrudan proposal ile çalışıyor, plan’a zorunlu değil. |
| **decision_explorer** | Sadece testte | Sadece `tests/test_decision_explorer.py` import ediyor; CLI/panel/engine’den çağrı yok. |
| **decision_simulator** | Stub | Sadece option alanlarını SimulationResult’a kopyalıyor; gerçek simülasyon yok. |
| **decision_ranker** | Pipeline’a bağlı değil | Hiçbir modül veya test `rank_options` çağırmıyor. Explorer kendi _compute_score ile sıralıyor. |
| **decision_runner** | Stub | Sadece target_paths kontrolü; patch apply veya evolution_tracker çağrısı yok. |
| **evolution_tracker** | Bağlı değil | `record_execution` hiçbir yerde çağrılmıyor. Yazım ayrı dosyaya (lumos_decision_feedback.jsonl); şema çakışması kaldırıldı. |
| **evolution_log** | Aktif | change_plan, patch_*, write_interceptor, decision_explorer event yazıyor. |
| **strategy_updater** | Bağlı değil | Hiçbir modül `analyze_evolution_log` veya StrategyReport kullanmıyor. |
| **adaptive_weights** | Bağlı değil | Hiçbir modül `load_weights` kullanmıyor; decision_ranker sabit 0.4/0.3/0.3 kullanıyor. |
| **patch_*** | Aktif | patch_pipeline gerçek apply ile kullanılıyor; write_interceptor üzerinden (testlerde) veya doğrudan proposal ile. |
| **write_interceptor** | Hazır, giriş sadece test | intercept_write yalnızca test dosyalarından çağrılıyor; production write path’in (CLI/engine/panel) buraya bağlanıp bağlanmadığı bu denetimde doğrulanmadı. |

Özet: **explorer → simulator → ranker → runner → evolution_tracker** zinciri teorik; production’da yalnızca **patch/mutation + evolution_log** tarafı gerçekten kullanılıyor. Decision tarafı stub / test-only. strategy_updater ve adaptive_weights hiç bağlı değil.

---

## 3. İsimlendirme ve dosya yerleşimi

- **Yanlış dosyaya eklenmiş mantık:** Tespit yok. Modüller sorumluluklarına göre ayrılmış.
- **Ayrı dosya olması gerekirken başka dosyada duran:** Tespit yok.
- **strategy_updater / adaptive_weights:** İkisi de `src/core/` altında; sadece okuma/analiz ve ağırlık okuma. Yerleşim uygun; **kayma yok**, sadece hiçbir yerde kullanılmıyor.
- **decision_ranker:** İsim “ranker” ama explorer kendi skorunu kullanıyor; rank_options çağrılmadığı için isim kullanım açısından yanıltıcı olabilir (mantık iki yerde: explorer _compute_score + ranker final_score).
- **create_plan_from_option:** decision_explorer’da; ChangePlan.new(goal_description, []) çağırıyor; ChangePlan.new en az bir patch istiyor → **çağrılırsa ValueError**. Kırık veya “ileride patch doldurulacak” iskelet.

---

## 4. Eksik bağlantılar

- **explorer → simulator → ranker → runner → evolution_tracker:**  
  Explorer sadece testte kullanılıyor; simulator/ranker/runner/tracker production’da hiç çağrılmıyor. Zincir **bağlı değil**.

- **strategy_updater çıktısı ranking’te kullanılıyor mu?**  
  Hayır. decision_ranker sabit 0.4/0.3/0.3 kullanıyor; adaptive_weights hiç import edilmiyor.

- **evolution_tracker ile evolution_log rolleri çakışıyor mu?**  
  Hayır (düzeltildi). evolution_tracker artık ayrı dosyaya yazıyor: `logs/lumos_decision_feedback.jsonl`. evolution_log `logs/lumos_evolution.jsonl`’da kalıyor. Şemalar farklı (EvolutionEvent vs EvolutionRecord) ama dosyalar ayrı; strategy_updater yalnızca lumos_evolution.jsonl’ı okumaya devam edebilir.

- **Patch/mutation ile decision birleşmiş mi?**  
  Hayır. Decision tarafı seçenek üretip (testte) plan iskeleti üretmeye çalışıyor ama create_plan_from_option boş patch ile kırık. apply_patch / patch_transaction sadece patch_pipeline ve write_interceptor üzerinden; decision_runner apply yapmıyor.

---

## 5. Fazlalık / çakışma / tekrar

- **Aynı JSONL’da iki şema:** Kaldırıldı. evolution_tracker `logs/lumos_decision_feedback.jsonl`’a yazıyor; evolution_log `logs/lumos_evolution.jsonl`’da.

- **İki skorlama formülü:** decision_explorer._compute_score (0.4 success, 0.3 impact, 0.2 risk, 0.1 complexity + penalty) ve decision_ranker final_score (0.4 success, 0.3 (1-risk), 0.3 impact). Ranker kullanılmadığı için şu an tekrara düşmüyor; ileride tek kaynak (örn. adaptive_weights) ve tek skorlama yeri olmalı.

- **Aynı işi yapan iki dosya:** Yok.  
- **Ayrı olması gereken ama tek dosyada sıkışmış:** Tespit yok.

---

## 6. Güvenlik ve sınır korunumu

- **Decision katmanı protected/core kurallarını bypass ediyor mu?**  
  Hayır. decision_runner sadece doğrulama stub’ı; dosyaya yazmıyor, patch_pipeline veya write_interceptor çağırmıyor.

- **Runner veya karar katmanı doğrudan write’a yaklaşıyor mu?**  
  Hayır. Hiçbir decision modülü doğrudan dosya yazmıyor; apply yalnızca patch_pipeline/patch_transaction üzerinden.

- **Mutation pipeline ile decision pipeline sınırları:**  
  Temiz. Mutation: write_interceptor → patch_pipeline → registry/transaction. Decision ayrı modüller ve pipeline’a bağlanmıyor. Tek karışan nokta: aynı evolution JSONL dosyası (farklı şema riski).

---

## 7. Teknik borç listesi (öncelik sırasıyla)

1. ~~**Aynı JSONL’da iki şema (evolution_log vs evolution_tracker):**~~  
   **Yapıldı.** Tracker ayrı dosyaya yazıyor: `logs/lumos_decision_feedback.jsonl`. strategy_updater lumos_evolution.jsonl’ı okumaya devam eder.

2. **decision_ranker + adaptive_weights bağlı değil:**  
   Ranker sabit ağırlık kullanıyor; strategy_updater/adaptive_weights hiç kullanılmıyor. İleride tek skorlama kaynağı (adaptive_weights) ve tek skorlama yeri (ranker veya explorer) olmalı.

3. **create_plan_from_option / ChangePlan.new uyumsuzluğu:**  
   create_plan_from_option boş patch ile ChangePlan.new çağırıyor; ChangePlan en az bir patch istiyor. Ya plan modeli “patch’siz plan”a izin verecek şekilde güncellenmeli ya da create_plan_from_option gerçek patch listesi alacak şekilde değişmeli.

4. **Decision zinciri production’da yok:**  
   Explorer/simulator/ranker/runner/tracker tek bir entry point’ten (CLI/panel/engine) çağrılmıyor. İstenen davranış “henüz açılmadı” ise dokümante; açılacaksa tek “decision pipeline” fonksiyonu ve nereden çağrılacağı netleştirilmeli.

5. **İki skorlama formülü:**  
   Explorer _compute_score ile ranker final_score benzer ama aynı değil; ileride tek formül ve mümkünse adaptive_weights ile tek parametre kaynağı.

---

## 8. Önerilen doğru yol haritası

- **Buradan sonra hangi sırayla:**  
  1) Evolution log şema/dosya ayrımı (tracker kullanılmadan önce).  
  2) create_plan_from_option / ChangePlan.new uyumunu düzelt (boş patch kabul veya API netleştirme).  
  3) decision_ranker’da adaptive_weights kullanımı (küçük bağlantı).  
  4) İstenirse tek “decision pipeline” fonksiyonu (explorer → ranker → runner → tracker); ilk aşamada test veya tek CLI komutu.

- **Hangi modül önce stabilize:**  
  evolution_log / evolution_tracker (dosya veya şema); ardından decision_explorer ↔ change_plan köprüsü.

- **Şimdilik ertelenebilir:**  
  strategy_updater çıktısının otomatik weights.json güncellemesi; simulator’ın gerçek simülasyonu; decision pipeline’ın tam production entegrasyonu (panel/engine); write_interceptor’ın production write path’e bağlanması (zaten testte kullanılıyor, nerede çağrılacağı netleştirilmeli).

---

## 9. Commit readiness

- **Mevcut durum:**  
  Yeni özellik eklenmedi; sadece denetim yapıldı. Kod tarafında değişiklik yok.

- **Stabilite:**  
  Patch/mutation + evolution_log tarafı testlerle kullanılıyor; decision tarafı stub/test-only. Bu haliyle commit edilebilir (denetim dokümanı güncellenmiş durumda).

- **Küçük temizlik (yapıldı):**  
  evolution_tracker ayrı dosyaya yazıyor: `DECISION_FEEDBACK_LOG_PATH = logs/lumos_decision_feedback.jsonl`. evolution_log lumos_evolution.jsonl’da kaldı.

---

## Sonraki tek adım önerisi

**Sonraki tek adım (önceki öneri uygulandı):**  
Decision feedback log ayrımı yapıldı: evolution_tracker `logs/lumos_decision_feedback.jsonl`’a yazıyor. Sıradaki öneri: create_plan_from_option / ChangePlan.new uyumunu düzeltmek veya decision_ranker’da adaptive_weights kullanımı.
