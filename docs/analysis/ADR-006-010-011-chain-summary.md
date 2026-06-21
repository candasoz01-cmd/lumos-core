# ADR zinciri özeti — 006 → 010 → 011 → 012

Tek sayfa çapraz referans: guard/firewall, terminoloji, lock semantiği ve security codex omurgası.

| ADR | Katman | Karar (kısa) | Zincir ilişkisi |
|-----|--------|--------------|-----------------|
| [ADR-006](../decisions/ADR-006-ai-firewall-guard-layer.md) | Guard / AI Firewall | Birleşik firewall **yok**; parçalı guard; **Guard → Trust → Router** önceliği | Lock enforcement guard değil **trust** katmanında; `koruma_active` session_unlocked |
| [ADR-007](../decisions/ADR-007-trust-engine-layer.md) | Trust Engine | Birleşik motor **yok**; `locked`/`unlocked` trust durumları; koruma kilidi | `session_unlocked` canonical hassas işlem sinyali; Faz 4 hedefi |
| [ADR-010](../decisions/ADR-010-guard-policy-trust-terminology.md) | Terminoloji | `lock`/`trust`/`consent` sözlüğü; drift tablosu | Usage map lock drift'i ADR-011'i tetikledi; bağlam olmadan "lock" yasak |
| [ADR-011](../decisions/ADR-011-lock-semantics-decision.md) | Lock semantiği | **keystore_ready** ≠ **session_unlocked**; tek boolean yasak | Faz 1–3 #436–#438 tamam; Faz 4 trust motor bekliyor |
| [ADR-012](../decisions/ADR-012-lumos-security-codex.md) | Security Codex | C1–C6: tek kapı, onay/kanıt, trash, stop-on-risk | #440 docs; #441 panel şeffaflık; #443 panel policy enforcement |

## Öncelik sırası (sabit)

```
Guard (ADR-006) → Trust (ADR-007) → Router (ADR-004) → …
Terminoloji disiplini (ADR-010) tüm katmanlara tabidir.
Lock iki sinyal (ADR-011) trust tüketimine hazırlanır (Faz 4).
```

## Uygulama durumu (2026-06-21)

| PR | İçerik |
|----|--------|
| #435 | ADR-011 karar belgesi |
| #436 | Faz 1 — `keystore_ready` rename |
| #437 | Faz 2 — CLI `durum`/`hazir` etiket ayrımı |
| #438 | Faz 3 — panel keystore display honesty |
| #440 | ADR-012 Security Codex taslak paketi |
| #441 | Panel codex gate reason + UI warning |
| #443 | Panel `check_policy` enforcement (PR #2) |
| #444 | Panel `PUT /tasks.json` CREATE_TASK gate |
| #445 | Panel delete-permanent policy + confirm |
| #446 | Panel restore CREATE_TASK gate |
| #449 | Panel profil guard (`may_execute_step_at_runtime` 2. kapı) |
| #450 | Consent ≠ general_approval ayrımı |
| #451 | session_consent CLI (`consent oturum aç/kapat/durum`) |
| #452 | PR-C0 confirmation reason kodları (docs) |
| #453 | `confirmation_policy` modülü (PR-C1) |
| #454 | delete-permanent confirmation unify (PR-C2) |
| #455 | Trash modal UI (PR-UI-C2a) |
| #456 | Panel mutasyon confirmation gate (PR-C3, opt-in) |
| #457 | CU7 preview endpoint + modal (PR-C5) |
| #458 | CLI `onayla` confirmation (PR-C4) |
| #459 | CLI E2E confirmation (Faz-2 Phase A) |
| #460 | Panel+API confirmation E2E (Faz-2 Phase A) |
| #461 | Varsayılan-on kararı — opt-in korunur (docs, DL-C18) |
| #462 | PR-C6 köprü confirmation namespace — shadow adapter (**kısmi**) |
| #463 | P2 `SECURITY_NEVER_AUTO` engine branch (**dar kapsam**) |
| #464 | Faz-2 milestone docs sync (#460–#463) |
| #468 | Quantum Readiness Faz-2 yerel tarayıcı (`scan_quantum_readiness`) |
| #469 | Panel `GET /quantum-readiness` + kuantum sekmesi live fetch UI |
| #470 | ADR-001/013 Faz-2 kısmi durum senkronu |
| #471 | Panel/landing quantum copy — fetch vs local_scan ayrımı |
| #472 | DL-A25/DL-C20 + open-decisions quantum milestone kapanışı |
| #473 | Landing `quantumDetailBody` Faz-2 partial readiness wording |
| #474 | ADR-001 iskelet cross-ref + chain-summary #468–#472 rows |
| #475 | Panel `noLiveScan` fetch-failure copy clarify |
| #476 | open-decisions + decision-log + chain-summary #473–#475 milestone sync |
| #477 | ADR-013 GET fetch vs mock fallback wording clarify |
| #479 | `lumos quantum-readiness` CLI subcommand (JSON/summary) |
| #480 | Panel kuantum sekmesi live fields (`generated_at`, `evidenced_findings`, `entropy_lab`) |
| #482 | Panel kuantum sekmesi migration tables (`long_lived_data`, `hard_to_change_deps`, `prioritized_migration_plan`) |

## Sonraki checkpoint

- **ADR-011 Faz 4 — ONAY GEREKİYOR:** Merkezi trust sinyal modelinde `keystore_ready` ve `session_unlocked` ayrı alanlar; ADR-007 § Trust sinyalleri revizyonu.
- **ADR-012 takip:** P2 tam küme eşlemesi açık — engine branch **kısmi merge** #463; [analiz](security-never-auto-p2-and-helper-proposal.md).
- **PR-C6 — ONAY GEREKİYOR:** Köprü yürütmede `consume_confirmation` wiring; shadow adapter **merge** #462.
- **Gate ↔ `change_sensitivity` zinciri — ONAY GEREKİYOR:** ADR-006 kopukluk; CRITICAL path + düşük gate riski mümkün; karar kaydı only.
- ~~**Confirmation varsayılan-on / E2E**~~ — **Kapandı** #459+#460 (E2E); opt-in korunur #461 (DL-C18).
