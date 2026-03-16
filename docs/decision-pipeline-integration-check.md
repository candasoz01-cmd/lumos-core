# Decision pipeline — end-to-end entegrasyon denetimi

Tarih: 2026-03-16  
Kapsam: decision_explorer → decision_simulator → decision_ranker → decision_runner → evolution_tracker / user feedback → strategy_updater zinciri.  
Kural: Yeni özellik eklenmedi; sadece denetim ve gerekirse minimal bağlama.

---

## 1. End-to-end zincir

### Bu akış şu anda gerçekten çalışıyor mu?

**Hayır.** Zincir production’da hiçbir yerden tetiklenmiyor. Tüm modüller dosya olarak mevcut, birbirini import ediyor (tip/veri yapısı düzeyinde), ancak **tek bir orkestrasyon noktası yok**: ne CLI, ne task_engine, ne brain bu sırayı çağırmıyor.

### Hangi adım hangi fonksiyonu çağırıyor?

| Adım | Çağrılması gereken fonksiyon | Gerçekte kim çağırıyor? |
|------|-----------------------------|--------------------------|
| 1. Explorer | `generate_candidate_options`, `select_best_option` | Sadece **test** (`tests/test_decision_explorer.py`) |
| 2. Simulator | `simulate_option(option)` | **Kimse** (hiçbir modül/test çağırmıyor) |
| 3. Ranker | `rank_options(options, simulations)` | **Kimse** |
| 4. Runner | `execute_decision(option)` | **Kimse** |
| 5. Evolution / feedback | `evolution_tracker.record_execution(result)` | **Kimse** |
| 6. Strategy updater | `strategy_updater.analyze_evolution_log(...)` | **Kimse** |

Explorer’dan sonra plan iskeleti: `create_plan_from_option(goal, option)` → şu an boş patch ile `ChangePlan.new(goal, [])` çağrılırsa **ValueError** (ChangePlan en az bir patch istiyor).

### Hangi bağlantılar gerçek, hangileri sadece teorik?

- **Gerçek (kod bağı):**  
  - decision_ranker → decision_simulator (`SimulationResult` tipi)  
  - evolution_tracker → decision_runner (`DecisionExecutionResult` tipi)  
  - decision_explorer → evolution_log (`record_event`: DECISION_OPTIONS_GENERATED, DECISION_OPTION_SELECTED) — explorer **testte** çağrıldığında bu event’ler yazılıyor.

- **Teorik (tasarlanmış ama çağrılmıyor):**  
  - Explorer → Simulator (simulate_option hiç çağrılmıyor)  
  - Simulator → Ranker (rank_options hiç çağrılmıyor)  
  - Ranker → Runner (execute_decision hiç çağrılmıyor)  
  - Runner → Evolution tracker (record_execution hiç çağrılmıyor)  
  - Evolution / decision feedback → Strategy updater (strategy_updater `lumos_evolution.jsonl` okuyor; decision feedback `lumos_decision_feedback.jsonl`’da — iki ayrı dosya; strategy_updater decision feedback’i hiç okumuyor).

---

## 2. Aktif kullanılan modüller

| Modül | Aktif mi? | Kanıt |
|-------|-----------|--------|
| **Explorer** | Sadece testte | `test_decision_explorer.py` import ve `generate_candidate_options` / `select_best_option` çağrısı; CLI/engine’den çağrı yok. |
| **Simulator** | Hayır | `simulate_option` hiçbir yerde çağrılmıyor. |
| **Ranker** | Hayır | `rank_options` hiçbir yerde çağrılmıyor. |
| **Runner** | Hayır | `execute_decision` hiçbir yerde çağrılmıyor. |
| **Evolution tracker** | Hayır | `record_execution` hiçbir yerde çağrılmıyor; decision feedback log’a yazım yapılmıyor. |
| **User feedback katmanı** | Teorik | evolution_tracker bu rolü tasarlanmış şekilde karşılıyor (DecisionExecutionResult → JSONL), ancak runner çıktısı hiç record_execution’a gelmediği için fiilen kullanılmıyor. |
| **Strategy updater** | Hayır | `analyze_evolution_log` hiçbir yerde çağrılmıyor; StrategyReport hiç kullanılmıyor. |

Özet: **Aktif** olan sadece **explorer’ın testte kullanılması** ve explorer’ın **evolution_log**’a yazması (test akışında). Geri kalan modüller dosya olarak var, zincire **bağlı değil**.

---

## 3. Kopuk halkalar

### Hangi modül dosya olarak var ama zincire bağlı değil?

- **decision_simulator** — Var, hiç çağrılmıyor.  
- **decision_ranker** — Var, hiç çağrılmıyor.  
- **decision_runner** — Var, hiç çağrılmıyor.  
- **evolution_tracker** — Var, `record_execution` hiç çağrılmıyor.  
- **strategy_updater** — Var, `analyze_evolution_log` hiç çağrılmıyor.  
- **adaptive_weights** — Var, `load_weights` hiçbir modül tarafından kullanılmıyor; ranker sabit 0.4/0.3/0.3 kullanıyor.

### Hangi sonuç üretiliyor ama başka katman tarafından kullanılmıyor?

- **Explorer** testte çalışınca: `MutationOption` listesi ve `evolution_log`’a DECISION_OPTIONS_GENERATED / DECISION_OPTION_SELECTED yazılıyor. Bu event’ler **strategy_updater** tarafından okunuyor (lumos_evolution.jsonl), ancak strategy_updater’ın kendisi hiç çağrılmadığı için analiz sonucu hiçbir yerde kullanılmıyor.  
- **SimulationResult**, **RankedOption**, **DecisionExecutionResult**: Sadece modül içi / tip bağı; bu sonuçları tüketen bir üst katman yok.  
- **StrategyReport**: Üretilmiyor (analyze_evolution_log çağrılmıyor); çağrılsa bile ranker/weights’e bağlanmıyor.

### User feedback ile evolution/strategy ilişkisi net mi?

- **Net değil / kopuk.**  
  - **Evolution log:** `lumos_evolution.jsonl` — plan/patch lifecycle (evolution_log).  
  - **Decision feedback (user feedback katmanı):** `lumos_decision_feedback.jsonl` — evolution_tracker bu dosyaya yazar (ExecutionResult → EvolutionRecord).  
  - **Strategy updater:** Sadece `lumos_evolution.jsonl` okuyor; `lumos_decision_feedback.jsonl`’ı okumuyor ve hiç çağrılmıyor.  
  - Sonuç: Decision execution sonuçları (user feedback) ne strategy_updater’a ne de ağırlık güncellemesine bağlı; evolution_tracker yazsa bile bu veri şu an kullanılmıyor.

---

## 4. Minimal entegrasyon düzeltmeleri

Yapılanlar (büyük refactor yok, davranışı bozmama):

1. **create_plan_from_option**  
   - Eski: Boş patch ile `ChangePlan.new(goal, [])` → ValueError.  
   - Yeni: Opsiyonel `patches` parametresi; `patches` yok veya boşsa `None` döner; verilirse `ChangePlan.new(goal, patches)` ile plan döner. Böylece çağrı yapan taraf patch’leri üst katmandan geçirebilir, çalışma zamanı hatası kalkar.

2. **decision_ranker ↔ adaptive_weights**  
   - Ranker artık `load_weights()` ile ağırlıkları okuyor; `.lumos/weights.json` yoksa varsayılan 0.4/0.3/0.3 kullanılıyor. Tek skorlama formülü ranker içinde; ileride strategy_updater çıktısı bu dosyaya yazılabilir.

Yapılmayanlar (kural: büyük refactor yok):

- Pipeline’ı tek noktadan çalıştıran orkestrasyon (yeni özellik sayıldı).  
- decision_runner içinden `record_execution` çağrısı (evolution_tracker ↔ decision_runner döngüsel import riski); ileride orkestrasyon katmanı `execute_decision` + `record_execution` çağırabilir.  
- strategy_updater’ın decision feedback dosyasını okuması veya otomatik weights güncellemesi.  
- Gereksiz import / stub / dead branch taraması bu turda sadece raporla sınırlı; ek temizlik yapılmadı.

---

## 5. Sonuç

- **Pipeline READY mı?**  
  **Hayır.** Modüller birbirine **veri tipi / import** düzeyinde bağlı; akış **orkestre edilmediği** ve production’da hiçbir adım tetiklenmediği için end-to-end “çalışan” bir pipeline yok.

- **Önce küçük bir entegrasyon temizliği daha mı lazım?**  
  Yapılan minimal düzeltmelerle:  
  - Plan tarafı güvenli (create_plan_from_option crash etmiyor).  
  - Ranker, adaptive_weights’e bağlandı.  
  Zincirin **tek yerden çalışması** ve **brain/task_engine’e bağlanması** için bir sonraki adım gerekli; bu “küçük temizlik” değil, bilinçli entegrasyon kararı.

---

## Sonraki tek adım önerisi

**Şu an en doğru sonraki adım:** Pipeline’ı tek bir fonksiyonla (örn. `run_decision_pipeline(goal, target_paths)` → explorer → simulator → ranker → runner → evolution_tracker.record_execution) orkestre edip, bu fonksiyonu önce test veya tek bir CLI komutundan çağırarak zincirin gerçekten uçtan uca çalıştığını doğrulamak; ardından istenirse brain/task_engine’de nerede ve ne zaman tetikleneceğine karar vermek.
