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
- CI must pass (`ruff` + `pytest`)
- Link related docs when you change behavior or onboarding paths
- **Reporting issues:** pilot / destek raporları için ORAA şablonu — [docs/templates/support-report-oraa.md](docs/templates/support-report-oraa.md)

## AI agent permissions (`.claude/settings.json`)

The repo ships a shared permission policy for contributors developing with Claude Code. It is designed for project developers: routine actions (file edits, running tests, `git add`/`git commit`) run without prompts, while hard-to-reverse or outward-facing operations (`git push`, merge/rebase, `git reset --hard`, secrets, auth, and mutating `gh` calls) always ask for confirmation. It only affects Claude Code sessions — normal git and CI behavior is unchanged.

## Public repository boundary

This repo is the **public OSS foundation**. Do not add production secrets, private orchestration, commercial service logic, or operational backend infrastructure. Demo-safe code, docs, placeholders, and foundation tooling belong here; professional Lumos layers stay private unless explicitly approved for public exposure.
