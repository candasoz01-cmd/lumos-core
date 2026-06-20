# Vault V1 — technology selection (OD-001–005) — private notice

**Status:** Full technology evaluation moved to private layer (2026-06-21)

The complete V1 vault technology selection — OSS/SaaS candidate tables, axis
scores, primary product choice, rollback plan, and private PoC sequence — is
**not maintained in this public repository**.

## Where the full document lives

| Location | Access |
|----------|--------|
| `.lumos/internal/strategy-vault/` | Local, gitignored vault on operator machine |
| `migration-2026-06-21/od-vault-v1-technology-selection.md` | Snapshot moved from public `docs/memory/` |

See vault README: `.lumos/internal/strategy-vault/README.md` (never commit).

## Public repo provides (demo-safe)

- **Principle decision:** [`vault-secret-token-decision.md`](./vault-secret-token-decision.md) — Lumos does not carry secrets; vault is a separate secure layer; Lumos is an authorized gate/orchestrator
- **Design framework:** [`od-vault-dar-v1-design.md`](./od-vault-dar-v1-design.md) — dar v1 UX outline and purpose-code skeleton (no product selection tables)
- **Roadmap index:** [`vault-implementation-roadmap.md`](./vault-implementation-roadmap.md) — phase labels only
- **Boundary rule:** [`public-mail-strategy-boundary.md`](./public-mail-strategy-boundary.md) — provider/vault product names must not appear in public strategy stubs
- **Migration index:** [`../mail-strategy-migration-index.md`](../mail-strategy-migration-index.md)
- **Open decisions index (redacted):** [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) — OD-001 row

## High-level summary (public)

| Topic | Public statement |
|-------|------------------|
| Direction | **Hybrid (harman)** — OSS self-host vault core + Lumos bridge adapter in **private layer** |
| Custom vault | **Rejected** — mature OSS options cover purpose-based access, segmentation, and self-host needs |
| Primary selection detail | **Private strategy vault only** — candidate tables, scores, and PoC steps are not committed here |
| Public code | Demo-safe stubs and interface references only; no production vault deploy or credential schema |
| Mail dependency | Connector credentials resolve via private vault bridge — not documented in this stub |

## Related policies

- [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — upper bound for all decisions
- Workspace rule `public-github-boundary` — no private orchestration or production integration detail in public repos
- [`security-architecture.md`](./security-architecture.md) — public repo secret/PII prohibition

**Do not** commit vault product names, candidate comparison tables, OAuth credential paths, or operator PoC procedures to this stub.

## Revision history

| Date | Change |
|------|--------|
| 2026-06-20 | V1 technology selection approved (full doc in public) |
| 2026-06-21 | OD-031 Phase 2 Step 2 — full evaluation moved to strategy vault; this stub replaces public canonical |
