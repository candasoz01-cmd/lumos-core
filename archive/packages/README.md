# Archived kando mirror packages (OD-027 Slice 3b)

These directories are **not live** Lumos Core code. Canonical implementations live under `src/`.

| Directory | Canonical location | Moved |
|-----------|-------------------|-------|
| `kando_core/` | `src/core/`, `src/lumos_core/` | PR #316 |
| `kando_memory/` | `src/memory/` | PR #316 |
| `kando_policy/` | `src/security/`, `src/policy/` | PR #316 |
| `kando_context/` | `src/context/` | PR #316 |

**Live packages** remain at repo root: `packages/kando_bridge`, `packages/kando_runtime`.

Decision: [`docs/memory/od-027-slice-3b-archive-decision.md`](../../docs/memory/od-027-slice-3b-archive-decision.md). Cutover: [`docs/memory/od-027-faz4-cutover-decision.md`](../../docs/memory/od-027-faz4-cutover-decision.md).

Rollback: reverse `git mv` from `archive/packages/<name>` back to `packages/<name>` (see Slice 3b decision §4).
