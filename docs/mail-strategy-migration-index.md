# Mail strategy — public migration index

Mail and communication-channels strategy documents with implementation detail were
moved out of this public repository on **2026-06-20** (branch
`docs/od-031-mail-strategy-private-stub`).

Full content is maintained locally in **`.lumos/internal/strategy-vault/`**
(gitignored). Public docs below are **stubs only**.

Boundary rule: [`docs/memory/public-repo-boundary.md`](memory/public-repo-boundary.md) (canonical; mail § Bölüm A)

Legacy redirect: [`docs/memory/public-mail-strategy-boundary.md`](memory/public-mail-strategy-boundary.md)

Operator notice: [`docs/mail-strategy-private-notice.md`](mail-strategy-private-notice.md)

---

## Moved strategy documents

| Public stub (this repo) | Vault location | Topic |
|-------------------------|----------------|-------|
| [`memory/mail-integration-approval-decision.md`](memory/mail-integration-approval-decision.md) | `.lumos/internal/strategy-vault/migration-2026-06-20/mail-integration-approval-decision.md` | OD-031 communication-channels automation model (full strategy) |
| [`memory/od-031-mail-dar-v1-scope.md`](memory/od-031-mail-dar-v1-scope.md) | `.lumos/internal/strategy-vault/migration-2026-06-20/od-031-mail-dar-v1-scope.md` | Mail dar v1 pilot scope definition |
| [`memory/od-vault-v1-technology-selection.md`](memory/od-vault-v1-technology-selection.md) | `.lumos/internal/strategy-vault/migration-2026-06-21/od-vault-v1-technology-selection.md` | Vault V1 OSS/SaaS evaluation and technology selection (OD-001–005) |

---

## Public code surface (demo-safe stub)

Merged to `main` via PR #413–#415 — **foundation only**, not product:

| Path | Scope |
|------|-------|
| `src/integrations/mail/` | Grant model, OAuth callback contract types, vault credential ref, demo connector |
| `src/integrations/vault/` | Purpose codes, adapter interface, demo/read-only adapter |

Canonical boundary + code reality: [`memory/public-repo-boundary.md`](memory/public-repo-boundary.md) § Bölüm C. ADR: [`decisions/ADR-002-mail-inbox-intelligence.md`](decisions/ADR-002-mail-inbox-intelligence.md) § Public kod gerçeği.

---

## Public docs kept (demo-safe)

These files remain in public `docs/` at ADR-002 / boundary level:

| File | Scope |
|------|-------|
| [`decisions/ADR-002-mail-inbox-intelligence.md`](decisions/ADR-002-mail-inbox-intelligence.md) | Draft ADR — permission gates, demo-safe mail principles |
| [`memory/public-repo-boundary.md`](memory/public-repo-boundary.md) | Canonical public boundary (mail § A, ops § B, code § C) |
| [`memory/public-mail-strategy-boundary.md`](memory/public-mail-strategy-boundary.md) | Legacy redirect → canonical |
| [`memory/open-decisions-needs-review.md`](memory/open-decisions-needs-review.md) | OD index — OD-031 row redacted |

---

## Placeholders used in public docs

- `<PRIVATE_MAIL_STRATEGY_DOC>` — full OD-031 strategy (not committed)
- `<PRIVATE_MAIL_DAR_V1_DOC>` — dar v1 scope document (not committed)
