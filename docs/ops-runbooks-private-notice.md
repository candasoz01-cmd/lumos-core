# Operational runbooks — private notice

**Status:** Active (2026-06-19, PR #252 revision)

Operational runbooks — server access, DNS with real origin IPs, SSH recovery, firewall rules, nginx/sshd configuration, live infra status, and deployment commands — are **not maintained in this public repository**.

## Where full runbooks live

| Location | Access |
|----------|--------|
| `.lumos/internal/ops-vault/` | Local, gitignored vault on operator machine |
| `migration-2026-06-19/` | Snapshot of runbooks moved from public `docs/` |

See vault README: `.lumos/internal/ops-vault/README.md` (never commit).

## Public repo provides

- **Stubs** for moved runbooks (title + high-level summary, no secrets)
- **Migration index:** [`ops-runbooks-migration-index.md`](ops-runbooks-migration-index.md)
- **Boundary rule:** [`memory/public-ops-runbook-boundary.md`](memory/public-ops-runbook-boundary.md)
- **Redacted planning docs** for panel/backend configuration (no IPs, no SSH)

## Placeholders in public docs

When public docs reference infrastructure, they use placeholders only:

- `<SERVER_IP>`
- `<SSH_PORT>`
- `<PRIVATE_OPS_RUNBOOK>`

Do not replace placeholders with real values in commits to this repo.

## Related policies

- [`memory/security-architecture.md`](memory/security-architecture.md) — public repo must not carry production secrets or operational infra detail
- Workspace rule `public-github-boundary` — no private orchestration, device control, or operational backend infrastructure in public repos

## Revision history

| Date | Change |
|------|--------|
| 2026-06-19 | PR #252 revision: 5 runbooks moved to ops vault; stubs + migration index + boundary rule added |
| 2026-06-19 | Initial notice (single line) replaced with this expanded notice |
