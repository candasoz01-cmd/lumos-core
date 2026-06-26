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

## Public repository boundary

This repo is the **public OSS foundation**. Do not add production secrets, private orchestration, commercial service logic, or operational backend infrastructure. Demo-safe code, docs, placeholders, and foundation tooling belong here; professional Lumos layers stay private unless explicitly approved for public exposure.
