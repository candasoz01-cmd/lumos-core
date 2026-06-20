# Gmail Readonly Live Smoke — Operatör Runbook

**Status:** Moved to private ops vault (2026-06-21, OD-031 Phase 2 Step 1)

Full operator runbook: `<PRIVATE_OPS_RUNBOOK>` → `.lumos/internal/ops-vault/migration-2026-06-21/gmail-readonly-smoke-operator-runbook.md`

See also: [`ops-runbooks-private-notice.md`](../ops-runbooks-private-notice.md) · [`ops-runbooks-migration-index.md`](../ops-runbooks-migration-index.md)

---

## High-level summary (public)

- **Purpose:** Operator-only live Gmail readonly smoke after vault + OAuth integration merges (PR #413–#415).
- **CI default:** Live smoke is **skipped** in CI; runs only on operator machine with explicit env gate.
- **Prerequisites:** Self-host vault configured; OAuth token stored in private operator layer (not in public repo).
- **Related public docs:** [`gmail-oauth-callback-contract.md`](./gmail-oauth-callback-contract.md) — callback contract and types only.
- **Vault PoC companion:** Infisical operator steps moved to [`vault-infisical-poc-runbook.md`](./vault-infisical-poc-runbook.md) (stub; full content in vault).
- **Verification:** Pytest PASS alone is insufficient — operator must confirm live Gmail signatures (not mock fallback); details in `<PRIVATE_OPS_RUNBOOK>`.
- **Security:** No tokens, export blocks, or secret paths in public repo — vault copy only.
