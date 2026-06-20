# Ops runbooks — public migration index

Operational runbooks with real infrastructure details were moved out of this public repository on **2026-06-19** (PR #252 revision, branch `docs/ops-runbook-visibility-cleanup`).

Full content is maintained locally in **`.lumos/internal/ops-vault/`** (gitignored). Public docs below are **stubs only**.

Boundary rule: [`docs/memory/public-ops-runbook-boundary.md`](memory/public-ops-runbook-boundary.md)

Operator notice: [`docs/ops-runbooks-private-notice.md`](ops-runbooks-private-notice.md)

---

## Moved runbooks

| Public stub (this repo) | Vault location | Topic |
|-------------------------|----------------|-------|
| [`panel-domain-https-runbook-2026-05-30.md`](panel-domain-https-runbook-2026-05-30.md) | `.lumos/internal/ops-vault/migration-2026-06-19/panel-domain-https-runbook-2026-05-30.md` | Panel domain, HTTPS, access control runbook |
| [`backend-domain-https-reverse-proxy-plan-2026-05-30.md`](backend-domain-https-reverse-proxy-plan-2026-05-30.md) | `.lumos/internal/ops-vault/migration-2026-06-19/backend-domain-https-reverse-proxy-plan-2026-05-30.md` | Backend domain + HTTPS + reverse proxy plan |
| [`digitalocean-ssh-recovery.md`](digitalocean-ssh-recovery.md) | `.lumos/internal/ops-vault/migration-2026-06-19/digitalocean-ssh-recovery.md` | SSH access recovery notes |
| [`digitalocean-test-server-status-2026-05-30.md`](digitalocean-test-server-status-2026-05-30.md) | `.lumos/internal/ops-vault/migration-2026-06-19/digitalocean-test-server-status-2026-05-30.md` | Test server live status |
| [`daily-status-2026-05-29.md`](daily-status-2026-05-29.md) | `.lumos/internal/ops-vault/migration-2026-06-19/daily-status-2026-05-29.md` | Daily ops status (2026-05-29) |
| [`memory/gmail-readonly-smoke-operator-runbook.md`](memory/gmail-readonly-smoke-operator-runbook.md) | `.lumos/internal/ops-vault/migration-2026-06-21/gmail-readonly-smoke-operator-runbook.md` | Gmail readonly live smoke — operator runbook |
| [`memory/vault-infisical-poc-runbook.md`](memory/vault-infisical-poc-runbook.md) | `.lumos/internal/ops-vault/migration-2026-06-21/vault-infisical-poc-runbook.md` | Infisical self-host PoC — operator runbook |

---

## Public docs kept (redacted summaries)

These files remain in public `docs/` with sensitive details removed; they describe product/config behavior at a high level:

| File | Scope |
|------|-------|
| [`panel-domain-https-plan-2026-05-30.md`](panel-domain-https-plan-2026-05-30.md) | Panel HTTPS service plan (placeholders only) |
| [`panel-live-backend-config-2026-05-30.md`](panel-live-backend-config-2026-05-30.md) | Feed API base URL configuration |
| [`panel-live-backend-connection-plan-2026-05-30.md`](panel-live-backend-connection-plan-2026-05-30.md) | Panel → backend connection plan |
| [`panel-api-usage-inventory-2026-05-30.md`](panel-api-usage-inventory-2026-05-30.md) | Panel API usage inventory (code references) |

---

## Placeholders used in public docs

- `<SERVER_IP>` — origin server address (not committed)
- `<SSH_PORT>` — SSH listen port (not committed)
- `<PRIVATE_OPS_RUNBOOK>` — pointer to vault copy
