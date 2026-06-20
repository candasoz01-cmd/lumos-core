# Mail strategy — private notice

**Status:** Active (2026-06-20, OD-031 strategy migration)

Full mail and communication-channels strategy documents — permission matrices,
rule engine design, multi-channel roadmap, provider selection, vault credential
schema, and implementation checklists — are **not maintained in this public repository**.

## Where full documents live

| Location | Access |
|----------|--------|
| `.lumos/internal/strategy-vault/` | Local, gitignored vault on operator machine |
| `migration-2026-06-20/` | Snapshot of strategy docs moved from public `docs/memory/` |

See vault README: `.lumos/internal/strategy-vault/README.md` (never commit).

## Public repo provides

- **Stubs** for moved strategy docs (title + high-level summary, no secrets)
- **Migration index:** [`mail-strategy-migration-index.md`](mail-strategy-migration-index.md)
- **Boundary rule:** [`memory/public-mail-strategy-boundary.md`](memory/public-mail-strategy-boundary.md)
- **Demo-safe ADR:** [`decisions/ADR-002-mail-inbox-intelligence.md`](decisions/ADR-002-mail-inbox-intelligence.md)
- **Redacted open-decisions index** — OD-031 row without provider/vault impl detail

## Placeholders in public docs

When public docs reference private strategy content, they use placeholders only:

- `<PRIVATE_MAIL_STRATEGY_DOC>`
- `<PRIVATE_MAIL_DAR_V1_DOC>`

Do not replace placeholders with strategic implementation detail in commits to this repo.

## Related policies

- [`memory/security-architecture.md`](memory/security-architecture.md) — public repo must not carry production secrets or private orchestration detail
- Workspace rule `public-github-boundary` — no private orchestration, production integration detail, or operational backend infrastructure in public repos

## Revision history

| Date | Change |
|------|--------|
| 2026-06-20 | OD-031 migration: 2 strategy docs moved to strategy vault; stubs + migration index + boundary rule added |
