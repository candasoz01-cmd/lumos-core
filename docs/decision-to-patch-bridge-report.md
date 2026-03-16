# Decision-to-patch bridge — sonuç raporu

## Amaç

Decision pipeline sonucunda seçilen en iyi `MutationOption`'dan gerçek dosyaya dokunmadan bir `PatchProposal` (veya birden fazla) üretmek. Apply yok; sadece proposal + isteğe bağlı validation/sandbox.

## Yeni akış

```
goal
  → explorer (generate_candidate_options)
  → simulator (simulate_option)
  → ranker (rank_options)
  → best option
  → PatchProposal(ler) — option_to_proposals / execute_decision
  → optional sandbox validation (run_sandbox_validation)
  → DecisionExecutionResult + proposal_summary
```

Apply aşaması hiç çağrılmaz.

## Bağlanan fonksiyonlar

| Yer | Fonksiyon | Rol |
|-----|-----------|-----|
| `decision_runner.py` | `option_to_proposals(option, base_dir)` | Best option'ın her `target_path`'i için mevcut içerikle (no-op) `propose_text_patch` çağırır; `PatchProposal` listesi döner. |
| `decision_runner.py` | `execute_decision(option, base_dir, run_validation, run_sandbox)` | `option_to_proposals` → `validate_proposal_against_filesystem` (isteğe bağlı) → `run_sandbox_validation` (isteğe bağlı). Apply yok. |
| `decision_pipeline.py` | `run_decision_pipeline(goal, target_paths, base_dir)` | `base_dir`'i `execute_decision`'a iletir; akış değişmedi, sadece runner artık proposal üretiyor. |

## Proposal nasıl üretildi

- Her `option.target_paths` öğesi için:
  - Dosya içeriği `_read_text_if_exists(path)` ile okunur.
  - `patch_pipeline.propose_text_patch(path, current_text, reason=option.description, caller="core.decision_runner.option_to_proposals", source="decision_pipeline", user_initiated=False, protected_target=is_core_state_path(base_dir, path))` çağrılır.
- Böylece “aynı içerikle değiştir” (no-op) proposal üretilir; pipeline (propose → register → event) çalışır. İleride option’a “önerilen içerik” eklendiğinde burada `new_content` olarak kullanılabilir.

## Apply neden yapılmadı

- İstek açık: “Sadece proposal üret”, “Autonomous apply yapma”.
- `apply_patch` hiç çağrılmıyor; `execute_decision` yalnızca proposal üretimi, `validate_proposal_against_filesystem` ve `run_sandbox_validation` ile sınırlı.
- Sandbox validation yalnızca önerilen içeriği geçici dosyaya yazar; gerçek hedefe yazılmaz.

## Güvenlik sınırları

- **Protected/core by-pass yok:** `protected_target`, `workspace_contract.is_core_state_path(base_dir, path)` ile belirleniyor; `base_dir` opsiyonel (None ise False).
- **Apply kapısı:** `apply_patch` çağrılmadığı için `ProtectedApplyForbidden` ve READY_FOR_APPLY kuralları değişmedi.
- **Guard/audit:** `propose_text_patch` ve `run_sandbox_validation` mevcut guard/audit kayıtlarını kullanıyor.

## Veri modeli (minimal)

- `DecisionExecutionResult` alanları: `option`, `success`, `notes`, `proposal_ids: Tuple[str, ...]`, `proposal_summary: str`.
- `MutationOption`’a alan eklenmedi; önerilen içerik ileride eklenirse `option_to_proposals` içinde kullanılabilir.

## Test sonucu

- `test_run_decision_pipeline_end_to_end`: Mevcut test; `DecisionExecutionResult` dönüyor, option ve target_paths doğru.
- `test_run_decision_pipeline_produces_proposal_no_apply`: Pipeline çalıştırılıyor; `result.proposal_ids` dolu, `result.proposal_summary` içinde “Proposals produced” ve “No apply” geçiyor; hedef dosya içeriği değişmeden kalıyor.

Her iki test geçiyor (`pytest tests/test_decision_pipeline.py -v`).
