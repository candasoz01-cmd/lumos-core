# Journey quick wins — applied

**Date:** 2026-06-26  
**Source:** [`first-10-minutes-journey-report.md`](./first-10-minutes-journey-report.md) (QW-1..QW-6)  
**Scope:** Docs + navigation only — no core/security/code logic changes.

---

## Done

| ID | Item | PR | Files |
|----|------|-----|-------|
| **QW-1** | README Quick Start → Katman A / Katman B + runbook + #kurulum | [#539](https://github.com/candasoz01-cmd/lumos-core/pull/539) | `README.md` |
| **QW-2** | Fix broken `README.tr.md` / `docs/tr/` links (minimal stubs) | [#541](https://github.com/candasoz01-cmd/lumos-core/pull/541) | `README.tr.md`, `docs/tr/README.md` |
| **QW-3** | Prerequisites box (Node >= 22.12, optional Python, Vercel CLI) | #539 | `README.md` |
| **QW-4** | Canonical `docs/getting-started.md` | [#540](https://github.com/candasoz01-cmd/lumos-core/pull/540) | `docs/getting-started.md`, `README.md` |
| **QW-5** | Link `docs/project-map.md` after Developer Setup | #539 | `README.md` |

**CI:** All three PRs green (`test`, `ui-smoke`, `ui-e2e`) before squash merge.

---

## Deferred (out of scope)

| ID | Item | Reason |
|----|------|--------|
| **QW-6** | Landing `#kurulum` step 0 cross-link | User mandate: no `ui/src/pages/index.astro` changes |
| **B-P0-3** | Single golden path across 6+ legacy entry docs | Partially addressed by `getting-started.md`; full consolidation not in scope |
| **CONTRIBUTING.md** | Not in quick-win list | Still "later" per README |

---

## NA items — untouched

Per [`todo-fixme-sweep-report.md`](./todo-fixme-sweep-report.md), **NA-01..NA-08** were not implemented (docs-only sweep; no core/security/task_engine changes).

---

## Post-merge doc entry points (recommended order)

1. [`README.md`](../../README.md) — product + Katman A/B summary  
2. [`docs/getting-started.md`](../getting-started.md) — canonical onboarding  
3. [`docs/local-kando-dev-runbook.md`](../local-kando-dev-runbook.md) — full local bridge smoke  
4. [`docs/project-map.md`](../project-map.md) — repo layout  

---

*Generated after journey quick wins PR chain (2026-06-26).*
