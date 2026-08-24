# Contributing to Lumos Core

Thanks for helping improve the open-source foundation. Keep changes focused and demo-safe.

## Before you start

- **Onboarding:** [docs/getting-started.md](docs/getting-started.md) — Katman A (UI only) vs Katman B (full local bridge)
- **Repo map:** [docs/project-map.md](docs/project-map.md) — layout, entry points, naming

## Local checks

From the repo root (Python deps installed; see getting-started):

```bash
ruff check .
make test
```

`make test` is the CI-parity entry point: it sets `PYTHONPATH` and
`KANDO_MOCK=1`, which a bare `pytest` invocation does not. Optional commit
guard: `make setup-commit-guard`.

### Which interpreter runs the tests

CI runs bare `pytest` ([`ci.yml`](.github/workflows/ci.yml)), and that is
correct there: the workflow installs `requirements.txt` into the job's own
interpreter, so the test runner and the dependencies are the same environment
by construction.

Locally the same command is **not** interchangeable. Bare `pytest` resolves to
whichever `pytest` comes first on your `PATH` — often a system or Homebrew
install — which need not be the interpreter your project dependencies are
installed into. Nothing in the output announces the swap: both runs report the
same pytest version and both print green. The difference surfaces only as tests
that **skip** instead of run.

Using a virtualenv is optional, not required. If you have one, point the run at
it explicitly rather than relying on `PATH`:

```bash
make test PYTEST=".venv/bin/python -m pytest"
```

Measured 2026-08-24: the venv interpreter reported **3 skipped**; bare `pytest`
(Homebrew, Python 3.11) reported **4 skipped**, from the same working tree, with
both runs printing green and reporting the same pytest version. The extra skip
is `tests/test_representative_bot_rig.py::test_resample_ratio`, guarded by
`pytest.importorskip("numpy")`. numpy is an optional dependency, so that skip is
intended behaviour, not a defect; it is absent from `requirements.txt`, so CI
skips it as well. Absolute pass counts move as tests land — the skip difference
is the signal.

`pytest.ini` sets `addopts = -rs`, so every skip prints its reason instead of
collapsing into a bare count. That is what makes an environment difference like
the one above visible without having to go looking for it.

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

**Standing class (ADR-028 gate 0):** `python -m standing_merge.classify` on
changed paths. The CheckRun trust root is
`github.event.pull_request.base.sha`, not the PR checkout: extract
`src/standing_merge` from that SHA into a separate directory. If the
classifier is missing on the base SHA, fail closed (no fallback). Feed
paths NUL-delimited (`git diff -z`) after `--`. A path that starts with
`-` is excluded. Hard-exclusion (prefix, file, path token, leading dash)
first. Unlisted paths are excluded (fail-closed). Only allowlisted `docs/`
and `tests/` paths that miss the hariç rules can be eligible. CheckRun
`standing-class` fails when the class is excluded. That failure forbids
standing merge; it does not forbid a human merge. Do **not** add
`standing-class` to GitHub `required_status_checks` — that would block
human-approved excluded PRs too. Physical lock needs a separate
merge-authority model. Incident: `#777` / [TD-20](docs/TECHNICAL_DEBT.md).

## Public repository boundary

This repo is the **public OSS foundation**. Do not add production secrets, private orchestration, commercial service logic, or operational backend infrastructure. Demo-safe code, docs, placeholders, and foundation tooling belong here; professional Lumos layers stay private unless explicitly approved for public exposure.
