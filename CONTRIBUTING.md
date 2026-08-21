# Contributing to Lumos Core

Thanks for helping improve the open-source foundation. Keep changes focused and demo-safe.

## Before you start

- **Onboarding:** [docs/getting-started.md](docs/getting-started.md) — Katman A (UI only) vs Katman B (full local bridge)
- **Repo map:** [docs/project-map.md](docs/project-map.md) — layout, entry points, naming

## Local checks

From the repo root (Python deps installed; see getting-started):

```bash
ruff check .
pytest -q
```

Or: `make test` (runs pytest). Optional commit guard: `make setup-commit-guard`.

## Pull requests

- One clear theme per PR; keep diffs small
- Local checks (`ruff` + `pytest`) should pass before you open a PR
- Merge into `main` only when the [merge gate](#merge-gate) holds
- Link related docs when you change behavior or onboarding paths
- **Reporting issues:** pilot / destek raporları için ORAA şablonu — [docs/templates/support-report-oraa.md](docs/templates/support-report-oraa.md)

### Merge gate

Target architecture ([ADR-027](docs/decisions/ADR-027-controlled-core-writer.md),
[Constitution §11](docs/CONSTITUTION.md)): researchers and external agents
propose; Lumos evaluates; Lumos security/test gates run; a **single controlled
Lumos writer** lands `main`. Humans are the final authority on the constitution,
authority limits, and high-risk exceptions — not the merge button on every PR.

That writer does not exist yet. Until it does, `main` uses the **temporary
three-gate regime** below. “A human merges every PR” is the current safety
stand-in, not the permanent model.

`main` is merged only when **all three** gates hold on the **current head
SHA**. Missing, queued, in-progress, or non-success results are not a pass.
If the head changes, the counters reset. Human approval is SHA-bound: it is
asked only after gates 1–2 are SUCCESS on that SHA, and it does not carry
over to a later SHA.

1. **Required CI green** (today’s test gate). GitHub CheckRuns from
   [`.github/workflows/ci.yml`](.github/workflows/ci.yml): `test`, `rust`,
   `macos-app-build`, `ui-smoke`, `ui-e2e`.
2. **Security review complete and clean** (today’s security gate). This is a
   real CheckRun produced by the Cursor Security Reviewer automation, not only
   a PR review or comment. Verified name:
   `Cursor Security Agent: Security Reviewer` (GitHub app `cursor`;
   `candasoz01-cmd/lumos-core#755` head `596253e` and `#762` · Checks API ·
   2026-08-19T17:31Z). A missing run is pending. The marketplace template
   triggers are **PR Opened** and **PR Pushed**: opening a *draft* does not
   fire PR Opened; PR Pushed fires only on new commits to an *existing* PR.
3. **Explicit human approval** (temporary stand-in for the controlled writer
   plus high-risk authority). An agent, bot, or GitHub App review does not
   count. GitHub’s required-review counter cannot tell a human from an agent;
   this gate is a written norm. Tentative phrasing is not approval.

Agent-facing counterpart: [`AGENTS.md`](AGENTS.md).

Scheduled [`layer1a.yml`](.github/workflows/layer1a.yml) (`pulse`) and manual
[`prod-smoke.yml`](.github/workflows/prod-smoke.yml) are not pull-request merge
gates.

**Physical lock (GitHub Settings, not this file):** `main` is protected, but
`required_status_checks` is empty. Until the CheckRun names above are added as
required checks, GitHub will not block merge while the security reviewer is
still running. Adding them is an admin action; this repository cannot set
branch protection from a docs PR.

## Public repository boundary

This repo is the **public OSS foundation**. Do not add production secrets, private orchestration, commercial service logic, or operational backend infrastructure. Demo-safe code, docs, placeholders, and foundation tooling belong here; professional Lumos layers stay private unless explicitly approved for public exposure.
