# İletişim kanalları — private strategy notice (OD-031)

**Status:** Full strategy document moved to private layer (2026-06-20)

The complete OD-031 communication-channels automation model — permission levels,
rule engine, multi-channel roadmap, and implementation checklist — is **not
maintained in this public repository**.

## Where the full document lives

| Location | Access |
|----------|--------|
| `.lumos/internal/strategy-vault/` | Local, gitignored vault on operator machine |
| `<PRIVATE_MAIL_STRATEGY_DOC>` | Private repo copy (if synced) |

See vault README: `.lumos/internal/strategy-vault/README.md` (never commit).

## Public repo provides (demo-safe)

- **Onay ve güvenlik ilkeleri:** [`docs/decisions/ADR-002-mail-inbox-intelligence.md`](../decisions/ADR-002-mail-inbox-intelligence.md) — taslak; onaysız okuma/gönderim yok
- **Karar sözleşmesi üst sınırı:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md)
- **Boundary rule:** [`public-mail-strategy-boundary.md`](./public-mail-strategy-boundary.md)
- **Migration index:** [`../mail-strategy-migration-index.md`](../mail-strategy-migration-index.md)
- **Open decisions index (redacted):** [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) — OD-031 satırı

## High-level summary (public)

- Mail is the **first candidate channel** for inbox intelligence; other channels are future evaluation only.
- **Default closed:** no reading, sending, or external effect without explicit user permission.
- **Draft ADR-002 scope:** read + priority presentation + suggested actions (preview only); send/archive/delete require separate approval.
- Full automation, rule engine, provider selection, vault credential schema, and connector implementation → **private layer only**.
- No credentials, message content, production endpoints, or OAuth secrets in this repo.

## Related policies

- Workspace rule `public-github-boundary` — no private orchestration or production integration detail in public repos
- [`memory/security-architecture.md`](./security-architecture.md) — public repo secret/PII prohibition

## Revision history

| Date | Change |
|------|--------|
| 2026-06-20 | Full OD-031 strategy moved to strategy vault; this stub replaces public canonical |
