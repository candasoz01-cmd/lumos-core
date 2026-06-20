# Infisical self-host PoC — operatör runbook

**Status:** Moved to private ops vault (2026-06-21, OD-031 Phase 2 Step 1)

Full operator runbook: `<PRIVATE_OPS_RUNBOOK>` → `.lumos/internal/ops-vault/migration-2026-06-21/vault-infisical-poc-runbook.md`

See also: [`ops-runbooks-private-notice.md`](../ops-runbooks-private-notice.md) · [`ops-runbooks-migration-index.md`](../ops-runbooks-migration-index.md)

---

## High-level summary (public)

- **Purpose:** Self-host Infisical PoC for Lumos vault credential resolution (V1a `implementation-partial`).
- **Public code surface:** `src/integrations/vault/adapter.py` — adapter fails closed when env not configured; purpose codes in `src/integrations/vault/purpose_codes.py`.
- **Health check script:** `./scripts/vault-infisical-poc-check.sh` — reachable check + optional secret probe (value never printed).
- **Private operator layer:** Infisical deploy, service tokens, secret storage, OAuth token write — not in public repo.
- **Gmail integration:** Read-only OAuth skeleton in `src/integrations/mail/providers/gmail_oauth.py`; live API gated by operator env — see Gmail smoke stub [`gmail-readonly-smoke-operator-runbook.md`](./gmail-readonly-smoke-operator-runbook.md).
- **Env variables, API paths, secret naming, export blocks:** `<PRIVATE_OPS_RUNBOOK>` only.
- **Rollback note:** Technology selection context in [`od-vault-v1-technology-selection.md`](./od-vault-v1-technology-selection.md) (strategy doc; separate migration scope).
