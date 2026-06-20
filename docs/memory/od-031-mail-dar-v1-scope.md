# Mail — dar v1 scope (OD-031) — private notice

**Status:** Pilot scope definition moved to private layer (2026-06-20)

The dar v1 mail pilot scope — provider choice, permission subset, vault
dependency order, and implementation sequence — is **not maintained in
this public repository**.

## Where the full document lives

Full scope: `<PRIVATE_MAIL_DAR_V1_DOC>` → `.lumos/internal/strategy-vault/migration-2026-06-20/od-031-mail-dar-v1-scope.md`

Parent strategy: `<PRIVATE_MAIL_STRATEGY_DOC>` → `mail-integration-approval-decision.md` (same vault)

See also: [`mail-strategy-private-notice.md`](../mail-strategy-private-notice.md)

## Public summary (demo-safe)

| Topic | Public statement |
|-------|------------------|
| Status | Decision principles approved; **implementation not in public repo** |
| Scope | Mail inbox intelligence is a **future, permission-gated** capability (ADR-002 draft) |
| Permissions | Public code reflects **demo-safe grant stubs only** — no live OAuth, no send |
| Vault | Credentials live in a **separate private vault layer** — not documented here |
| Provider / sync / smoke | Private implementation package — details in vault |

## Canonical public references

- [`docs/decisions/ADR-002-mail-inbox-intelligence.md`](../decisions/ADR-002-mail-inbox-intelligence.md)
- [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) — stub + private notice
- [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) — OD-031 (redacted row)

**Do not** commit provider names, vault product choices, OAuth paths, or smoke procedures to this stub.
